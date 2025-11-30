# AWS RDS Setup Guide for Mean Reversion Trading Framework

## Overview
This guide walks you through setting up a PostgreSQL 15 RDS instance in your new AWS account for the mean reversion trading framework.

## Prerequisites
- AWS Account (freshly created)
- AWS CLI installed and configured
- Terraform installed (optional, for Infrastructure-as-Code approach)
- Basic understanding of AWS services

---

## Option 1: Quick Setup via AWS Console (Recommended for Beginners)

### Step 1: Access RDS Console
1. Log into your AWS Console: https://console.aws.amazon.com/
2. Navigate to **RDS** service (search for "RDS" in the top search bar)
3. Select your preferred region (e.g., `us-east-1`)

### Step 2: Create Database
1. Click **"Create database"**
2. Choose **"Standard create"**

### Step 3: Engine Configuration
- **Engine type:** PostgreSQL
- **Engine version:** PostgreSQL 15.x (latest 15.x version available)
- **Templates:** Choose based on your use case:
  - **Production:** For live trading (Multi-AZ, automated backups)
  - **Dev/Test:** For development and backtesting (cheaper, single AZ)

### Step 4: Settings
- **DB instance identifier:** `mean-reversion-db`
- **Master username:** `trader`
- **Master password:** Create a strong password (save this securely!)
  - Example: Use AWS Secrets Manager or save in password manager
  - **IMPORTANT:** You'll need this for connection strings

### Step 5: Instance Configuration
**For Development/Testing:**
- **DB instance class:** `db.t3.medium` or `db.t3.large`
  - vCPUs: 2-4
  - RAM: 4-8 GB
  - Cost: ~$60-120/month

**For Production:**
- **DB instance class:** `db.r6g.xlarge` or larger
  - vCPUs: 4+
  - RAM: 32+ GB
  - Cost: ~$300+/month

### Step 6: Storage
- **Storage type:** General Purpose SSD (gp3)
- **Allocated storage:** 100 GB (minimum recommended)
- **Storage autoscaling:** Enable
  - Maximum: 500 GB
- **IOPS:** 3000 (default for gp3)
- **Throughput:** 125 MB/s (default for gp3)

### Step 7: Connectivity
- **Virtual Private Cloud (VPC):** Default VPC
- **Subnet group:** default
- **Public access:**
  - **Yes** - If connecting from your local machine for development
  - **No** - If running on EC2 instances in same VPC (more secure)
- **VPC security group:** Create new
  - Name: `mean-reversion-db-sg`
- **Availability Zone:** No preference

### Step 8: Database Authentication
- **Database authentication:** Password authentication
- (Optional) Enable IAM database authentication for enhanced security

### Step 9: Additional Configuration
**Database options:**
- **Initial database name:** `mean_reversion`
- **DB parameter group:** default.postgres15
- **Option group:** default:postgres-15

**Backup:**
- **Enable automated backups:** Yes
- **Backup retention period:** 7 days (adjust as needed)
- **Backup window:** Choose a time (e.g., 03:00-04:00 UTC)
- **Copy tags to snapshots:** Yes

**Encryption:**
- **Enable encryption:** Yes (recommended)
- **AWS KMS key:** (default) aws/rds

**Monitoring:**
- **Enable Enhanced Monitoring:** Yes
- **Granularity:** 60 seconds
- **Monitoring Role:** Create new role

**Maintenance:**
- **Enable auto minor version upgrade:** Yes
- **Maintenance window:** Choose a time (e.g., Sun:04:00-Sun:05:00 UTC)

**Deletion protection:**
- **Enable deletion protection:** Yes (for production)

### Step 10: Create Database
1. Review all settings
2. Click **"Create database"**
3. Wait 10-15 minutes for the database to be created
4. **Status will change from "Creating" → "Available"**

### Step 11: Configure Security Group
1. Once database is available, click on the database name
2. Scroll to **"Connectivity & security"** tab
3. Click on the **VPC security group** link
4. Click **"Edit inbound rules"**
5. Add rule:
   - **Type:** PostgreSQL
   - **Protocol:** TCP
   - **Port:** 5432
   - **Source:**
     - For development: **My IP** (your current IP address)
     - For EC2 access: Security group of your EC2 instances
     - For broader access: **Custom** - specify CIDR block
6. Click **"Save rules"**

### Step 12: Get Connection Details
1. Go back to RDS dashboard
2. Click on your database: `mean-reversion-db`
3. Note the **Endpoint** and **Port**:
   - Example: `mean-reversion-db.c9abc123xyz.us-east-1.rds.amazonaws.com:5432`
4. Save these details - you'll need them for connection

---

## Option 2: Terraform Setup (Infrastructure-as-Code)

### Prerequisites
```bash
# Install Terraform
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform --version
```

### Setup Steps
1. Configure AWS credentials:
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

2. Use the Terraform configuration in `infrastructure/terraform/`:
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

3. Terraform will output the RDS endpoint and connection details

---

## Post-Setup: Initialize Database Schema

### Step 1: Install PostgreSQL Client
```bash
# macOS
brew install postgresql@15

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-client-15

# Amazon Linux 2
sudo amazon-linux-extras install postgresql14
sudo yum install postgresql
```

### Step 2: Test Connection
```bash
psql -h <RDS_ENDPOINT> -U trader -d mean_reversion

# Example:
psql -h mean-reversion-db.c9abc123xyz.us-east-1.rds.amazonaws.com -U trader -d mean_reversion

# Enter password when prompted
```

### Step 3: Initialize Schema
```bash
# From the repository root
psql -h <RDS_ENDPOINT> -U trader -d mean_reversion -f database/init.sql

# Or run the Python script
python scripts/initialize_database.py
```

---

## Connection Strings

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="mean-reversion-db.c9abc123xyz.us-east-1.rds.amazonaws.com",
    port=5432,
    database="mean_reversion",
    user="trader",
    password="YOUR_PASSWORD"
)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://trader:YOUR_PASSWORD@mean-reversion-db.c9abc123xyz.us-east-1.rds.amazonaws.com:5432/mean_reversion"
)
```

### Environment Variables (.env file)
```bash
DB_HOST=mean-reversion-db.c9abc123xyz.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=mean_reversion
DB_USER=trader
DB_PASSWORD=YOUR_PASSWORD
```

---

## Cost Optimization Tips

### Development Phase
1. **Use db.t3.medium** ($60/month) instead of larger instances
2. **Single AZ deployment** (no Multi-AZ)
3. **Reduce backup retention** to 1-3 days
4. **Stop the database** when not in use (saves ~90% cost)
   - Go to RDS → Select database → Actions → Stop

### Production Phase
1. **Use Reserved Instances** (1 or 3 year) for ~40% savings
2. **Enable Storage Autoscaling** to avoid over-provisioning
3. **Use gp3 instead of io1** storage (better price/performance)
4. **Monitor with CloudWatch** to right-size instance

### Stopping RDS (Development Only)
```bash
# Stop via CLI
aws rds stop-db-instance --db-instance-identifier mean-reversion-db

# Start when needed
aws rds start-db-instance --db-instance-identifier mean-reversion-db
```

**Note:** RDS automatically starts after 7 days of being stopped

---

## Security Best Practices

### 1. Use AWS Secrets Manager
Store database credentials securely:
```bash
aws secretsmanager create-secret \
    --name mean-reversion-db-password \
    --secret-string '{"username":"trader","password":"YOUR_PASSWORD"}'
```

Retrieve in Python:
```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-1')
secret = client.get_secret_value(SecretId='mean-reversion-db-password')
creds = json.loads(secret['SecretString'])

# Use creds['username'] and creds['password']
```

### 2. Enable SSL/TLS Connections
```python
import psycopg2

conn = psycopg2.connect(
    host="...",
    database="mean_reversion",
    user="trader",
    password="...",
    sslmode='require'  # Force SSL
)
```

### 3. Regular Security Group Audits
- Restrict source IPs to only necessary locations
- Remove public access when not needed
- Use VPN or bastion host for access

### 4. Enable CloudWatch Alarms
- High CPU usage
- Low free storage space
- High number of connections
- Failed login attempts

---

## Troubleshooting

### Can't Connect to RDS
1. **Check security group rules** - ensure port 5432 is open to your IP
2. **Verify public accessibility** - must be "Yes" for external access
3. **Check VPC/subnet** - ensure proper VPC configuration
4. **Verify credentials** - username and password are correct
5. **Test with psql** before application code

### Connection Timeout
```bash
# Test network connectivity
nc -zv <RDS_ENDPOINT> 5432

# Test DNS resolution
nslookup <RDS_ENDPOINT>

# Check security group via CLI
aws ec2 describe-security-groups --group-ids sg-xxxxx
```

### Slow Query Performance
1. Enable **Enhanced Monitoring**
2. Check **Performance Insights**
3. Review slow query logs
4. Consider upgrading instance class
5. Optimize indexes (see database/indexes.sql)

---

## Monitoring & Maintenance

### CloudWatch Metrics to Monitor
- **DatabaseConnections** - track connection pool usage
- **CPUUtilization** - should be <80% normally
- **FreeStorageSpace** - ensure adequate space
- **ReadLatency / WriteLatency** - track performance
- **NetworkThroughput** - monitor data transfer

### Setting Up Alerts
```bash
# Create SNS topic for alerts
aws sns create-topic --name rds-alerts

# Subscribe your email
aws sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:rds-alerts \
    --protocol email \
    --notification-endpoint your-email@example.com

# Create CloudWatch alarm for high CPU
aws cloudwatch put-metric-alarm \
    --alarm-name rds-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/RDS \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=DBInstanceIdentifier,Value=mean-reversion-db \
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:rds-alerts
```

---

## Backup & Recovery

### Manual Snapshot
```bash
# Create snapshot
aws rds create-db-snapshot \
    --db-instance-identifier mean-reversion-db \
    --db-snapshot-identifier mean-reversion-snapshot-$(date +%Y%m%d)

# List snapshots
aws rds describe-db-snapshots --db-instance-identifier mean-reversion-db

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier mean-reversion-db-restored \
    --db-snapshot-identifier mean-reversion-snapshot-20240101
```

### Export to S3
```bash
# Useful for data migration or analysis
aws rds start-export-task \
    --export-task-identifier export-$(date +%Y%m%d) \
    --source-arn arn:aws:rds:us-east-1:ACCOUNT_ID:snapshot:mean-reversion-snapshot-20240101 \
    --s3-bucket-name mean-reversion-backups \
    --iam-role-arn arn:aws:iam::ACCOUNT_ID:role/rds-s3-export-role \
    --kms-key-id arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID
```

---

## Next Steps

1. ✅ RDS instance created and accessible
2. ✅ Security group configured
3. ✅ Database schema initialized
4. ⏭️ Install Python dependencies
5. ⏭️ Configure application connection
6. ⏭️ Load stock data
7. ⏭️ Begin backtesting framework development

---

## Quick Reference Commands

```bash
# Test connection
psql -h <ENDPOINT> -U trader -d mean_reversion

# Run schema
psql -h <ENDPOINT> -U trader -d mean_reversion -f database/init.sql

# Connect via Python
python scripts/test_connection.py

# Check RDS status
aws rds describe-db-instances --db-instance-identifier mean-reversion-db

# Stop RDS (dev only)
aws rds stop-db-instance --db-instance-identifier mean-reversion-db

# Start RDS
aws rds start-db-instance --db-instance-identifier mean-reversion-db
```

---

## Support Resources

- **AWS RDS Documentation:** https://docs.aws.amazon.com/rds/
- **PostgreSQL Documentation:** https://www.postgresql.org/docs/15/
- **AWS Cost Calculator:** https://calculator.aws/
- **AWS Support:** https://console.aws.amazon.com/support/

---

**Ready to proceed? Start with Option 1 (AWS Console) if you're new to AWS, or Option 2 (Terraform) if you prefer infrastructure-as-code!**
