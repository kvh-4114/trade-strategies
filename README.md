# Mean Reversion Trading Framework

A comprehensive multi-agent backtesting framework for testing mean reversion trading strategies across 250 stocks using PostgreSQL RDS on AWS.

## 🚀 Quick Start

### 1. Prerequisites

- AWS Account (with credentials configured)
- Python 3.10+
- Terraform (for infrastructure deployment)
- PostgreSQL client (psql)

### 2. Setup RDS Database

**Option A: Using Terraform (Recommended)**

```bash
# Configure AWS credentials
aws configure

# Navigate to Terraform directory
cd infrastructure/terraform

# Copy and customize configuration
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings (especially allowed_cidr_blocks!)

# Deploy infrastructure
terraform init
terraform plan
terraform apply

# Get connection details
terraform output
```

**Option B: Manual AWS Console Setup**

See [AWS_RDS_SETUP_GUIDE.md](./AWS_RDS_SETUP_GUIDE.md) for detailed step-by-step instructions.

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your RDS connection details
# (Use terraform output to get the values)
nano .env
```

If using Terraform, you can auto-populate the .env file:

```bash
cd infrastructure/terraform
cat > ../../.env << EOF
DB_HOST=$(terraform output -raw db_address)
DB_PORT=$(terraform output -raw db_port)
DB_NAME=$(terraform output -raw db_name)
DB_USER=$(terraform output -raw db_username)
DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id $(terraform output -raw secrets_manager_name) --query SecretString --output text | jq -r .password)
AWS_REGION=us-east-1
EOF
cd ../..
```

### 4. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
# Test connection
python scripts/test_connection.py

# Initialize schema
python scripts/initialize_database.py
```

### 6. Verify Setup

```bash
# Should show all tables created
python scripts/test_connection.py
```

## 📊 Project Structure

```
trade-strategies/
├── database/
│   └── init.sql                    # Database schema
├── infrastructure/
│   └── terraform/                  # Infrastructure-as-Code
│       ├── main.tf                 # RDS configuration
│       ├── variables.tf            # Configurable parameters
│       ├── outputs.tf              # Connection details
│       └── README.md               # Terraform guide
├── scripts/
│   ├── database_manager.py         # Database connection utilities
│   ├── test_connection.py          # Test RDS connectivity
│   └── initialize_database.py      # Initialize schema
├── mean_reversion/
│   └── Mean Reversion Strategy Testing Framework.md  # Full blueprint
├── .env.example                    # Environment template
├── requirements.txt                # Python dependencies
├── AWS_RDS_SETUP_GUIDE.md         # Detailed AWS setup guide
└── README.md                       # This file
```

## 🗄️ Database Schema

The PostgreSQL database includes:

### Tables
- `stock_data` - Raw OHLCV stock data
- `candles` - Generated candles (regular, Heiken Ashi, linear regression)
- `strategy_configs` - Strategy parameter configurations
- `backtest_results` - Backtest performance metrics
- `walk_forward_results` - Walk-forward validation results
- `phase_execution` - Pipeline phase tracking
- `agent_logs` - System logging

### Views
- `v_top_configs_by_phase` - Top performing strategies per phase
- `v_portfolio_performance` - Portfolio-level performance
- `v_walk_forward_comparison` - In-sample vs out-of-sample comparison
- `v_phase_summary` - Phase execution summary

### Functions
- `calculate_sharpe_ratio()` - Sharpe ratio calculation
- `log_agent_activity()` - Agent logging helper

## 🔧 Database Operations

### Using the Database Manager

```python
from scripts.database_manager import DatabaseManager

# Initialize
db = DatabaseManager()

# Test connection
db.test_connection()

# Execute queries
results = db.execute_query("SELECT * FROM strategy_configs LIMIT 10")

# Use context manager
with db.get_cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM stock_data")
    count = cursor.fetchone()

# Close pool
db.close_pool()
```

### Using AWS Secrets Manager

```python
# Set in .env
USE_SECRETS_MANAGER=true
DB_SECRET_NAME=mean-reversion-db-password-dev

# Database manager will automatically retrieve credentials
db = DatabaseManager(use_secrets_manager=True)
```

### Direct SQL Access

```bash
# Get password
PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id <SECRET_NAME> \
  --query SecretString \
  --output text | jq -r .password)

# Connect via psql
psql -h <RDS_ENDPOINT> -U trader -d mean_reversion
```

## 📈 Framework Overview

### Phase-Based Testing Pipeline

1. **Phase 1: Candle Type Baseline** - Test 13 candle combinations
2. **Phase 2: Mean & StdDev Optimization** - Optimize statistical parameters
3. **Phase 3: Entry/Exit Logic** - Refine entry and exit rules
4. **Phase 4: Filter Integration** - Add robustness filters
5. **Phase 5: Risk Management** - Optimize position sizing and stops
6. **Phase 6: Final Validation** - Stress testing and validation

See [Mean Reversion Strategy Testing Framework.md](./mean_reversion/Mean%20Reversion%20Strategy%20Testing%20Framework.md) for complete details.

## 🔒 Security Best Practices

1. **Never commit .env files** - Already in .gitignore
2. **Use Secrets Manager** for production credentials
3. **Restrict security groups** to your IP only:
   ```hcl
   allowed_cidr_blocks = ["YOUR_IP/32"]
   ```
4. **Enable deletion protection** for production databases
5. **Use SSL connections** - enabled by default (sslmode=require)
6. **Rotate passwords** regularly via Secrets Manager

## 💰 Cost Management

### Development
- **db.t3.medium**: ~$60/month
- **Stop when not in use**: Saves 90% of costs
  ```bash
  aws rds stop-db-instance --db-instance-identifier mean-reversion-db
  ```

### Production
- **Use Reserved Instances**: 40% savings
- **Enable storage autoscaling**: Prevent over-provisioning
- **Monitor with CloudWatch**: Right-size instance

## 📊 Monitoring

### CloudWatch Alarms

Terraform automatically creates alarms for:
- CPU utilization > 80%
- Free storage < 10 GB
- Database connections > 80

### Performance Insights

View query performance in AWS Console:
1. RDS → Databases → mean-reversion-db
2. Performance Insights tab
3. Analyze slow queries and bottlenecks

## 🧪 Testing

```bash
# Test database connection
python scripts/test_connection.py

# Test specific queries
python -c "from scripts.database_manager import quick_query; \
           print(quick_query('SELECT version()'))"
```

## 📝 Next Steps

After RDS setup is complete:

1. **Load Stock Data** - Import historical data
2. **Generate Candles** - Create all candle types (Agent 1)
3. **Build Strategy Core** - Implement mean reversion logic (Agent 2)
4. **Run Backtests** - Execute optimization pipeline (Agent 3)
5. **Analyze Results** - Generate reports (Agent 4)

See the full blueprint for implementation details.

## 🆘 Troubleshooting

### Cannot connect to RDS

1. **Check security group**:
   ```bash
   aws ec2 describe-security-groups --group-ids <SG_ID>
   ```

2. **Verify your IP**:
   ```bash
   curl ifconfig.me
   ```

3. **Test network connectivity**:
   ```bash
   nc -zv <RDS_ENDPOINT> 5432
   ```

4. **Check RDS status**:
   ```bash
   aws rds describe-db-instances --db-instance-identifier mean-reversion-db
   ```

### psql command not found

Install PostgreSQL client:
```bash
# macOS
brew install postgresql@15

# Ubuntu
sudo apt-get install postgresql-client-15

# Amazon Linux
sudo yum install postgresql
```

### Permission denied

Ensure your AWS credentials have the required permissions:
- RDS: Full access or read/write
- Secrets Manager: Read access
- EC2: Describe security groups (for troubleshooting)

## 📚 Additional Resources

- [AWS RDS Setup Guide](./AWS_RDS_SETUP_GUIDE.md) - Detailed setup instructions
- [Terraform Documentation](./infrastructure/terraform/README.md) - Infrastructure guide
- [Framework Blueprint](./mean_reversion/Mean%20Reversion%20Strategy%20Testing%20Framework.md) - Complete framework details
- [AWS RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)

## 📄 License

This is a private trading framework. All rights reserved.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review AWS RDS documentation
3. Check CloudWatch logs for database errors
4. Review agent logs in the database

---

**Ready to get started?** Follow the Quick Start guide above!
