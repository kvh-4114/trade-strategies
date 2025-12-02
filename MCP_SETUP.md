# AWS MCP Server Setup Guide

This enables Claude Code to **directly access AWS services** without SSH or manual intervention!

## What This Unlocks

✅ **Direct RDS queries** - Check database progress instantly
✅ **EC2 command execution** - Run scripts via Systems Manager
✅ **AWS resource management** - List instances, create resources, etc.
✅ **100% web-based** - No local tools required

## Prerequisites

1. **AWS CLI installed** (if using Claude Code Desktop)
2. **AWS credentials configured** (Access Key + Secret Key)
3. **Python 3.10+** with `uv` or `uvx` package manager

## Setup Steps

### 1️⃣ Install UV Package Manager

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uvx --version
```

### 2️⃣ Configure AWS Credentials

**Option A: AWS CLI (Recommended)**
```bash
aws configure
# AWS Access Key ID: [Your Key]
# AWS Secret Access Key: [Your Secret]
# Default region: us-east-1
# Default output format: json
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

**Option C: AWS SSO (Enterprise)**
```bash
aws configure sso
# Follow the prompts to authenticate
```

### 3️⃣ Verify AWS Access

```bash
# Test credentials
aws sts get-caller-identity
aws ec2 describe-instances --region us-east-1
aws rds describe-db-instances --region us-east-1
```

### 4️⃣ Configure IAM Permissions

Your AWS user/role needs these permissions:

**For RDS Access:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:Describe*",
        "rds:List*",
        "rds-data:ExecuteStatement",
        "rds-data:BatchExecuteStatement"
      ],
      "Resource": "*"
    }
  ]
}
```

**For EC2/Systems Manager Access:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
        "ssm:ListCommands",
        "ssm:DescribeInstanceInformation"
      ],
      "Resource": "*"
    }
  ]
}
```

**Quick Start: Use AWS Managed Policies**
- `ReadOnlyAccess` - For safe testing (recommended to start)
- `PowerUserAccess` - For full management (after testing)

### 5️⃣ Enable MCP Servers in Claude Code

**For Claude Code Desktop:**
1. Go to Settings → MCP Servers
2. MCP config should auto-detect `.mcp.json` in this directory
3. Restart Claude Code to load the servers

**For Claude Code Web:**
1. MCP servers run in the cloud workspace
2. Credentials are configured via environment variables
3. Contact support if MCP servers don't appear

### 6️⃣ Verify MCP Connection

Once configured, you should see these MCP servers available:
- `aws-rds` - RDS Management (30+ database tools)
- `aws-cloudcontrol` - AWS Resource Management (1200+ resources)

Test by asking Claude:
```
"List all RDS instances in us-east-1"
"Show me EC2 instance information for instance i-xxxxx"
```

## Usage Examples

### Check Database Progress (Direct RDS Query)

```
Claude: "Query the candles table in RDS and show me the count by candle_type and aggregation_days"
```

MCP server will:
1. Connect to RDS using your credentials
2. Execute the SQL query
3. Return formatted results instantly

### Run Commands on EC2 (Systems Manager)

```
Claude: "Run the check_db_progress.py script on my EC2 instance via Systems Manager"
```

MCP server will:
1. Use Systems Manager Send Command API
2. Execute the Python script on EC2
3. Return the output

### Manage AWS Resources

```
Claude: "List all running EC2 instances in my account"
Claude: "Show me the configuration of my RDS database"
Claude: "Create a snapshot of my database"
```

## Security Best Practices

⚠️ **Important Security Notes:**

1. **Use IAM Roles**: Prefer EC2 instance roles over access keys
2. **Least Privilege**: Start with ReadOnlyAccess, add permissions as needed
3. **Rotate Credentials**: Use temporary credentials (AWS SSO) when possible
4. **Monitor Activity**: Enable CloudTrail to audit all MCP API calls
5. **Never Commit Credentials**: Keep `.aws/credentials` out of git
6. **Use Named Profiles**: Separate dev/staging/prod credentials

## Troubleshooting

### MCP Server Not Appearing
- Check if `uv` or `uvx` is installed: `uvx --version`
- Verify `.mcp.json` syntax with a JSON validator
- Restart Claude Code to reload MCP configuration

### Authentication Errors
- Run `aws sts get-caller-identity` to verify credentials
- Check `~/.aws/credentials` file exists and has correct profile
- Ensure `AWS_PROFILE` in `.mcp.json` matches your profile name

### Permission Denied Errors
- Review IAM policies attached to your user/role
- Use `ReadOnlyAccess` managed policy for testing
- Check CloudTrail logs for specific denied actions

### Connection Timeouts
- Verify security groups allow outbound HTTPS (port 443)
- Check VPC/subnet routing if using VPC endpoints
- Increase `timeout` value in `.mcp.json` (default: 60s)

## What Changes with MCP Servers

### Before (Cron-based automation):
```
Claude Code → Git commit → Wait 5 min → EC2 pulls → Script runs → Git commit logs
```

### After (MCP direct access):
```
Claude Code → MCP Server → AWS API → Instant results
```

**Benefits:**
- ⚡ **Instant execution** - No waiting for cron
- 🎯 **Direct queries** - Real-time database access
- 🔒 **Secure** - Uses AWS IAM, no SSH keys
- 📱 **Mobile-friendly** - Works from Claude Code web

## Next Steps

1. ✅ Install `uv` package manager
2. ✅ Configure AWS credentials (`aws configure`)
3. ✅ Test AWS access (`aws ec2 describe-instances`)
4. ✅ Restart Claude Code to load MCP servers
5. ✅ Ask Claude to list RDS instances (test connection)
6. ✅ Check database progress via MCP (instant results!)

---

**Ready?** Once you configure AWS credentials and restart Claude Code, I'll be able to directly query your RDS database and execute commands on EC2 instantly! 🚀
