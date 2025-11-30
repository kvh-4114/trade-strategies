#!/bin/bash

# Mean Reversion Trading Framework - RDS Setup Script
# Automated setup for AWS RDS PostgreSQL instance

set -e  # Exit on error

echo "========================================"
echo "Mean Reversion RDS Setup Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."
echo "----------------------------------------"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found"
    echo "  Install: https://aws.amazon.com/cli/"
    exit 1
fi
print_success "AWS CLI installed"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found"
    echo "  Install: https://www.terraform.io/downloads"
    exit 1
fi
print_success "Terraform installed"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found"
    exit 1
fi
print_success "Python 3 installed"

# Check jq
if ! command -v jq &> /dev/null; then
    print_error "jq not found (required for JSON parsing)"
    echo "  Install: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi
print_success "jq installed"

# Verify AWS credentials
echo ""
echo "Verifying AWS credentials..."
echo "----------------------------------------"

if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured"
    echo "  Run: aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")
print_success "AWS credentials configured"
print_info "Account: $AWS_ACCOUNT"
print_info "Region: $AWS_REGION"

# Get user confirmation
echo ""
echo "========================================"
echo "Setup Options"
echo "========================================"
echo ""
echo "This script will:"
echo "  1. Deploy RDS PostgreSQL instance using Terraform"
echo "  2. Create database credentials in Secrets Manager"
echo "  3. Configure security groups"
echo "  4. Set up CloudWatch alarms"
echo "  5. Initialize database schema"
echo "  6. Create .env configuration file"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Navigate to Terraform directory
cd infrastructure/terraform

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_info "Creating terraform.tfvars from template..."
    cp terraform.tfvars.example terraform.tfvars

    echo ""
    print_info "Please edit terraform.tfvars and update:"
    echo "  - allowed_cidr_blocks (your IP address)"
    echo "  - db_instance_class (if different from default)"
    echo "  - Other settings as needed"
    echo ""
    read -p "Press Enter when ready to continue..."
fi

# Initialize Terraform
echo ""
echo "========================================"
echo "Initializing Terraform"
echo "========================================"
terraform init

# Plan
echo ""
echo "========================================"
echo "Reviewing Terraform Plan"
echo "========================================"
terraform plan

echo ""
read -p "Apply this plan? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Apply
echo ""
echo "========================================"
echo "Deploying RDS Infrastructure"
echo "========================================"
echo "This will take 10-15 minutes..."
echo ""

terraform apply -auto-approve

if [ $? -ne 0 ]; then
    print_error "Terraform deployment failed"
    exit 1
fi

print_success "RDS infrastructure deployed successfully!"

# Extract outputs
echo ""
echo "========================================"
echo "Extracting Connection Details"
echo "========================================"

DB_HOST=$(terraform output -raw db_address)
DB_PORT=$(terraform output -raw db_port)
DB_NAME=$(terraform output -raw db_name)
DB_USER=$(terraform output -raw db_username)
SECRET_NAME=$(terraform output -raw secrets_manager_name)

print_info "Endpoint: $DB_HOST:$DB_PORT"
print_info "Database: $DB_NAME"
print_info "User: $DB_USER"
print_info "Secret: $SECRET_NAME"

# Retrieve password from Secrets Manager
echo ""
echo "Retrieving password from Secrets Manager..."
DB_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --query SecretString \
    --output text | jq -r .password)

if [ -z "$DB_PASSWORD" ]; then
    print_error "Failed to retrieve password"
    exit 1
fi
print_success "Password retrieved"

# Go back to repository root
cd ../..

# Create .env file
echo ""
echo "========================================"
echo "Creating .env Configuration"
echo "========================================"

cat > .env << EOF
# Mean Reversion Trading Framework - Environment Configuration
# Auto-generated by setup_rds.sh

# Database Configuration
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_SSL_MODE=require

# AWS Configuration
AWS_REGION=$AWS_REGION
DB_SECRET_NAME=$SECRET_NAME
USE_SECRETS_MANAGER=false

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
N_JOBS=8
EOF

print_success ".env file created"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "========================================"
    echo "Creating Python Virtual Environment"
    echo "========================================"

    python3 -m venv venv
    print_success "Virtual environment created"

    # Activate and install dependencies
    source venv/bin/activate

    echo ""
    echo "Installing Python dependencies..."
    pip install --upgrade pip > /dev/null
    pip install -r requirements.txt

    print_success "Python dependencies installed"
else
    print_info "Virtual environment already exists"
    source venv/bin/activate
fi

# Test connection
echo ""
echo "========================================"
echo "Testing Database Connection"
echo "========================================"

python scripts/test_connection.py

if [ $? -ne 0 ]; then
    print_error "Connection test failed"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check security group allows your IP"
    echo "  2. Verify RDS is in 'available' state"
    echo "  3. Check .env file has correct credentials"
    exit 1
fi

# Initialize database schema
echo ""
echo "========================================"
echo "Initializing Database Schema"
echo "========================================"

read -p "Initialize database schema now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/initialize_database.py

    if [ $? -ne 0 ]; then
        print_error "Schema initialization failed"
        exit 1
    fi

    print_success "Database schema initialized"
fi

# Final summary
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
print_success "RDS instance is ready for use"
echo ""
echo "Connection details saved to .env"
echo ""
echo "Next steps:"
echo "  1. Load stock data"
echo "  2. Generate candles (Agent 1)"
echo "  3. Build strategy core (Agent 2)"
echo "  4. Run backtests (Agent 3)"
echo ""
echo "Quick commands:"
echo "  Test connection:     python scripts/test_connection.py"
echo "  Access database:     psql -h $DB_HOST -U $DB_USER -d $DB_NAME"
echo "  Stop RDS (save \$\$):  aws rds stop-db-instance --db-instance-identifier mean-reversion-db"
echo ""
echo "Documentation:"
echo "  AWS RDS Guide:       cat AWS_RDS_SETUP_GUIDE.md"
echo "  Terraform Guide:     cat infrastructure/terraform/README.md"
echo "  Full Blueprint:      cat mean_reversion/Mean\\ Reversion\\ Strategy\\ Testing\\ Framework.md"
echo ""
echo "========================================"
