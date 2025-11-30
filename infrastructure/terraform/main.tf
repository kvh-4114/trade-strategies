terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "MeanReversionTrading"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Generate random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}-db-password-${var.environment}"
  description             = "Database password for Mean Reversion Trading Framework"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = aws_db_instance.mean_reversion_db.address
    port     = aws_db_instance.mean_reversion_db.port
    dbname   = var.db_name
  })
}

# VPC for RDS (use default VPC or create new one)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "mean_reversion" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for Mean Reversion RDS instance"
  vpc_id      = data.aws_vpc.default.id

  # PostgreSQL access
  ingress {
    description = "PostgreSQL from allowed IPs"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# DB Parameter Group
resource "aws_db_parameter_group" "mean_reversion" {
  name   = "${var.project_name}-postgres15-params"
  family = "postgres15"

  # Optimize for analytical workload
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4096}"  # 25% of instance memory
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory/2048}"  # 50% of instance memory
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "2097152"  # 2GB for maintenance operations
  }

  parameter {
    name  = "work_mem"
    value = "65536"  # 64MB per operation
  }

  parameter {
    name  = "random_page_cost"
    value = "1.1"  # SSD optimization
  }

  parameter {
    name  = "effective_io_concurrency"
    value = "200"  # SSD optimization
  }

  parameter {
    name  = "max_connections"
    value = var.max_db_connections
  }

  # Enable query logging for optimization
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking > 1 second
  }

  parameter {
    name  = "log_statement"
    value = "mod"  # Log all DDL and data-modifying statements
  }

  tags = {
    Name = "${var.project_name}-postgres15-params"
  }
}

# RDS Instance
resource "aws_db_instance" "mean_reversion_db" {
  # Instance identification
  identifier = "${var.project_name}-db"

  # Engine configuration
  engine               = "postgres"
  engine_version       = var.postgres_version
  instance_class       = var.db_instance_class
  allocated_storage    = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type         = "gp3"
  iops                 = var.db_iops
  storage_throughput   = var.db_storage_throughput
  storage_encrypted    = true

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result
  port     = 5432

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.mean_reversion.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.publicly_accessible
  multi_az               = var.multi_az

  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.mean_reversion.name

  # Backup configuration
  backup_retention_period   = var.backup_retention_period
  backup_window             = var.backup_window
  maintenance_window        = var.maintenance_window
  copy_tags_to_snapshot     = true
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.project_name}-final-snapshot-${formatdate("YYYYMMDD-hhmmss", timestamp())}"

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = var.enhanced_monitoring_interval
  monitoring_role_arn             = var.enhanced_monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  # Performance Insights
  performance_insights_enabled    = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? var.performance_insights_retention : null

  # Maintenance
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  deletion_protection        = var.deletion_protection

  tags = {
    Name = "${var.project_name}-database"
  }

  lifecycle {
    ignore_changes = [
      password,  # Password managed via Secrets Manager
      final_snapshot_identifier
    ]
  }
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  count = var.enhanced_monitoring_interval > 0 ? 1 : 0
  name  = "${var.project_name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.enhanced_monitoring_interval > 0 ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "${var.project_name}-db-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.mean_reversion_db.id
  }
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.project_name}-db-free-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10737418240"  # 10 GB in bytes
  alarm_description   = "This metric monitors RDS free storage space"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.mean_reversion_db.id
  }
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "${var.project_name}-db-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.max_db_connections * 0.8
  alarm_description   = "This metric monitors RDS database connections"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.mean_reversion_db.id
  }
}
