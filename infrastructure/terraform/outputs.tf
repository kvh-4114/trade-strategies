output "db_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.mean_reversion_db.id
}

output "db_instance_arn" {
  description = "ARN of the RDS instance"
  value       = aws_db_instance.mean_reversion_db.arn
}

output "db_endpoint" {
  description = "Connection endpoint for the database"
  value       = aws_db_instance.mean_reversion_db.endpoint
}

output "db_address" {
  description = "Hostname of the RDS instance"
  value       = aws_db_instance.mean_reversion_db.address
}

output "db_port" {
  description = "Port of the RDS instance"
  value       = aws_db_instance.mean_reversion_db.port
}

output "db_name" {
  description = "Name of the initial database"
  value       = aws_db_instance.mean_reversion_db.db_name
}

output "db_username" {
  description = "Master username"
  value       = aws_db_instance.mean_reversion_db.username
  sensitive   = true
}

output "security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "secrets_manager_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.db_password.name
}

output "connection_string_template" {
  description = "Connection string template (password needs to be retrieved from Secrets Manager)"
  value       = "postgresql://${var.db_username}:<PASSWORD>@${aws_db_instance.mean_reversion_db.address}:${aws_db_instance.mean_reversion_db.port}/${var.db_name}"
}

output "psql_command" {
  description = "psql command to connect to the database"
  value       = "psql -h ${aws_db_instance.mean_reversion_db.address} -p ${aws_db_instance.mean_reversion_db.port} -U ${var.db_username} -d ${var.db_name}"
}

output "connection_details" {
  description = "Complete connection details"
  value = {
    host     = aws_db_instance.mean_reversion_db.address
    port     = aws_db_instance.mean_reversion_db.port
    database = var.db_name
    username = var.db_username
    secret   = aws_secretsmanager_secret.db_password.name
  }
}

# Instructions for retrieving password
output "retrieve_password_command" {
  description = "AWS CLI command to retrieve database password"
  value       = "aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.db_password.name} --query SecretString --output text | jq -r .password"
}

output "setup_instructions" {
  description = "Next steps after Terraform deployment"
  value = <<-EOT

  ========================================
  RDS Instance Created Successfully!
  ========================================

  Instance Endpoint: ${aws_db_instance.mean_reversion_db.address}:${aws_db_instance.mean_reversion_db.port}
  Database Name: ${var.db_name}
  Username: ${var.db_username}

  NEXT STEPS:

  1. Retrieve database password:
     aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.db_password.name} --query SecretString --output text | jq -r .password

  2. Test connection:
     psql -h ${aws_db_instance.mean_reversion_db.address} -p ${aws_db_instance.mean_reversion_db.port} -U ${var.db_username} -d ${var.db_name}

  3. Initialize database schema:
     cd ../../
     psql -h ${aws_db_instance.mean_reversion_db.address} -p ${aws_db_instance.mean_reversion_db.port} -U ${var.db_username} -d ${var.db_name} -f database/init.sql

  4. Update .env file with connection details

  5. Run Python connection test:
     python scripts/test_connection.py

  ========================================
  EOT
}
