# Terraform RDS Infrastructure

This directory contains Terraform configuration for deploying the PostgreSQL RDS instance for the Mean Reversion Trading Framework.

## Prerequisites

1. **Install Terraform**
   ```bash
   # macOS
   brew install terraform

   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

2. **Configure AWS Credentials**
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: us-east-1
   # Default output format: json
   ```

3. **Verify AWS Access**
   ```bash
   aws sts get-caller-identity
   ```

## Quick Start

### 1. Configure Variables

Copy the example tfvars file and customize it:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and update:
- `allowed_cidr_blocks` - Your IP address or VPC CIDR
- `db_instance_class` - Instance size based on your needs
- Other settings as needed

### 2. Initialize Terraform

```bash
terraform init
```

This will download the required providers (AWS, Random).

### 3. Review the Plan

```bash
terraform plan
```

Review the resources that will be created:
- RDS PostgreSQL instance
- Security group
- DB subnet group
- DB parameter group
- Secrets Manager secret
- IAM role for monitoring
- CloudWatch alarms

### 4. Deploy

```bash
terraform apply
```

Type `yes` when prompted. Deployment takes 10-15 minutes.

### 5. Get Connection Details

```bash
terraform output
```

Save these details for database connection.

## Important Outputs

After deployment, Terraform will display:

- **db_endpoint** - Connection endpoint
- **db_address** - Hostname only
- **db_port** - Port (5432)
- **secrets_manager_name** - Name of the secret containing the password
- **psql_command** - Command to connect via psql

## Retrieving Database Password

The database password is stored in AWS Secrets Manager:

```bash
# Get the secret name
terraform output secrets_manager_name

# Retrieve the password
aws secretsmanager get-secret-value \
  --secret-id <SECRET_NAME> \
  --query SecretString \
  --output text | jq -r .password
```

Or retrieve complete connection details:

```bash
aws secretsmanager get-secret-value \
  --secret-id <SECRET_NAME> \
  --query SecretString \
  --output text | jq .
```

## Post-Deployment Steps

### 1. Test Connection

```bash
# Get connection command
terraform output psql_command

# Retrieve password
PASSWORD=$(aws secretsmanager get-secret-value --secret-id $(terraform output -raw secrets_manager_name) --query SecretString --output text | jq -r .password)

# Test connection
psql -h $(terraform output -raw db_address) \
     -p $(terraform output -raw db_port) \
     -U $(terraform output -raw db_username) \
     -d $(terraform output -raw db_name)
```

### 2. Initialize Database Schema

```bash
# From repository root
cd ../../

# Run initialization script
psql -h $(cd infrastructure/terraform && terraform output -raw db_address) \
     -p $(cd infrastructure/terraform && terraform output -raw db_port) \
     -U $(cd infrastructure/terraform && terraform output -raw db_username) \
     -d $(cd infrastructure/terraform && terraform output -raw db_name) \
     -f database/init.sql
```

### 3. Update Application Configuration

Create `.env` file in repository root:

```bash
# Get values from Terraform
cd infrastructure/terraform
terraform output connection_details

# Create .env file
cat > ../../.env << EOF
DB_HOST=$(terraform output -raw db_address)
DB_PORT=$(terraform output -raw db_port)
DB_NAME=$(terraform output -raw db_name)
DB_USER=$(terraform output -raw db_username)
DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id $(terraform output -raw secrets_manager_name) --query SecretString --output text | jq -r .password)
AWS_REGION=us-east-1
EOF
```

## Configuration Options

### Instance Classes

**Development/Testing:**
- `db.t3.medium` - 2 vCPU, 4 GB RAM (~$60/month)
- `db.t3.large` - 2 vCPU, 8 GB RAM (~$120/month)

**Production:**
- `db.r6g.xlarge` - 4 vCPU, 32 GB RAM (~$300/month)
- `db.r6g.2xlarge` - 8 vCPU, 64 GB RAM (~$600/month)

### Environment-Specific Settings

**Development:**
```hcl
environment                = "dev"
multi_az                   = false
deletion_protection        = false
skip_final_snapshot        = true
publicly_accessible        = true
backup_retention_period    = 1
```

**Production:**
```hcl
environment                = "prod"
multi_az                   = true
deletion_protection        = true
skip_final_snapshot        = false
publicly_accessible        = false
backup_retention_period    = 30
```

## Managing the Infrastructure

### View Current State

```bash
terraform show
```

### Modify Configuration

1. Edit `terraform.tfvars`
2. Run `terraform plan` to see changes
3. Run `terraform apply` to apply changes

### Destroy Infrastructure

```bash
terraform destroy
```

**WARNING:** This will delete the RDS instance and all data (unless final snapshot is enabled).

## Cost Optimization

### Development Phase

1. **Stop the database when not in use:**
   ```bash
   aws rds stop-db-instance --db-instance-identifier mean-reversion-db
   ```

2. **Use smaller instance:**
   ```hcl
   db_instance_class = "db.t3.medium"
   ```

3. **Reduce backup retention:**
   ```hcl
   backup_retention_period = 1
   ```

### Production Phase

1. **Use Reserved Instances** (40% savings)
2. **Enable storage autoscaling** (avoid over-provisioning)
3. **Use gp3 storage** (included - better price/performance than gp2)

## Security Best Practices

1. **Restrict CIDR blocks:**
   ```hcl
   allowed_cidr_blocks = ["123.45.67.89/32"]  # Your IP only
   ```

2. **Use private subnet for production:**
   ```hcl
   publicly_accessible = false
   ```

3. **Enable deletion protection:**
   ```hcl
   deletion_protection = true
   ```

4. **Enable automated backups:**
   ```hcl
   backup_retention_period = 30
   skip_final_snapshot    = false
   ```

5. **Rotate passwords regularly** via Secrets Manager

## Monitoring

### CloudWatch Alarms

The configuration creates alarms for:
- CPU utilization > 80%
- Free storage < 10 GB
- Database connections > 80 connections

To receive notifications:

1. Create SNS topic:
   ```bash
   aws sns create-topic --name rds-alerts
   ```

2. Subscribe your email:
   ```bash
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:rds-alerts \
     --protocol email \
     --notification-endpoint your-email@example.com
   ```

3. Update `terraform.tfvars`:
   ```hcl
   alarm_actions = ["arn:aws:sns:us-east-1:ACCOUNT_ID:rds-alerts"]
   ```

4. Apply changes:
   ```bash
   terraform apply
   ```

### Performance Insights

Access Performance Insights in AWS Console:
1. Go to RDS → Databases → mean-reversion-db
2. Click "Performance Insights" tab
3. Analyze query performance and resource utilization

## Troubleshooting

### Can't connect to RDS

1. **Check security group:**
   ```bash
   terraform output security_group_id
   aws ec2 describe-security-groups --group-ids <SG_ID>
   ```

2. **Verify your IP:**
   ```bash
   curl ifconfig.me
   ```

3. **Test network connectivity:**
   ```bash
   nc -zv $(terraform output -raw db_address) 5432
   ```

### Terraform errors

1. **State lock error:**
   ```bash
   # If using S3 backend
   terraform force-unlock <LOCK_ID>
   ```

2. **Provider version issues:**
   ```bash
   terraform init -upgrade
   ```

3. **Authentication issues:**
   ```bash
   aws sts get-caller-identity
   ```

## Additional Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [PostgreSQL on RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
