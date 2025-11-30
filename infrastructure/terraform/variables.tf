variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mean-reversion"
}

# Database Configuration
variable "db_name" {
  description = "Name of the initial database"
  type        = string
  default     = "mean_reversion"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "trader"
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15.4"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"

  # Common options:
  # Development: db.t3.medium (2 vCPU, 4 GB RAM) - ~$60/month
  # Testing: db.t3.large (2 vCPU, 8 GB RAM) - ~$120/month
  # Production: db.r6g.xlarge (4 vCPU, 32 GB RAM) - ~$300/month
}

variable "db_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling (GB)"
  type        = number
  default     = 500
}

variable "db_iops" {
  description = "Provisioned IOPS for gp3 storage"
  type        = number
  default     = 3000
}

variable "db_storage_throughput" {
  description = "Storage throughput in MB/s for gp3"
  type        = number
  default     = 125
}

variable "max_db_connections" {
  description = "Maximum number of database connections"
  type        = string
  default     = "100"
}

# Network Configuration
variable "publicly_accessible" {
  description = "Whether the database should be publicly accessible"
  type        = bool
  default     = true  # Set to false for production with VPN/bastion

  # IMPORTANT: Set to false for production and use VPN or bastion host
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the database"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # CHANGE THIS! Use your specific IP or VPC CIDR

  # Examples:
  # ["123.45.67.89/32"]  # Single IP
  # ["10.0.0.0/16"]      # VPC CIDR
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment for high availability"
  type        = bool
  default     = false  # Set to true for production
}

# Backup Configuration
variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_period >= 1 && var.backup_retention_period <= 35
    error_message = "Backup retention period must be between 1 and 35 days."
  }
}

variable "backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot when deleting (NOT recommended for production)"
  type        = bool
  default     = true  # Set to false for production
}

# Monitoring Configuration
variable "enhanced_monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0, 1, 5, 10, 15, 30, 60)"
  type        = number
  default     = 60

  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.enhanced_monitoring_interval)
    error_message = "Enhanced monitoring interval must be 0, 1, 5, 10, 15, 30, or 60."
  }
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention" {
  description = "Performance Insights retention period in days (7 or 731)"
  type        = number
  default     = 7

  validation {
    condition     = contains([7, 731], var.performance_insights_retention)
    error_message = "Performance Insights retention must be 7 or 731 days."
  }
}

variable "alarm_actions" {
  description = "SNS topic ARNs for CloudWatch alarms"
  type        = list(string)
  default     = []

  # Example: ["arn:aws:sns:us-east-1:123456789012:rds-alerts"]
}

# Maintenance Configuration
variable "auto_minor_version_upgrade" {
  description = "Enable automatic minor version upgrades"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false  # Set to true for production
}
