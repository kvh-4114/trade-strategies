#!/bin/bash
# One-time setup script for automated cloud deployment
# Run this ONCE on EC2, then everything is automated

set -e

echo "=========================================="
echo "Setting up automated cloud deployment"
echo "=========================================="

cd /home/ec2-user/trade-strategies

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt --user

# Create auto-deploy script
echo "Creating auto-deploy script..."
cat > /home/ec2-user/auto_deploy.sh << 'EOF'
#!/bin/bash
# Auto-deploy script - pulls latest code and runs pending tasks

cd /home/ec2-user/trade-strategies

# Pull latest code
git pull origin main

# Check for task files and run them
if [ -f "tasks/check_progress.task" ]; then
    echo "Running database progress check..."
    python3 scripts/check_db_progress.py > logs/progress_$(date +%Y%m%d_%H%M%S).log 2>&1
    rm tasks/check_progress.task
fi

if [ -f "tasks/install_deps.task" ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt --user > logs/install_$(date +%Y%m%d_%H%M%S).log 2>&1
    rm tasks/install_deps.task
fi

if [ -f "tasks/generate_candles.task" ]; then
    echo "Generating candles..."
    nohup python3 scripts/generate_candles.py > logs/candles_$(date +%Y%m%d_%H%M%S).log 2>&1 &
    rm tasks/generate_candles.task
fi

if [ -f "tasks/run_phase_1.task" ]; then
    echo "Running Phase 1..."
    python3 scripts/run_phase_1.py > logs/phase1_$(date +%Y%m%d_%H%M%S).log 2>&1
    rm tasks/run_phase_1.task
fi

# Commit logs back to git (optional)
if [ -n "$(git status --porcelain logs/)" ]; then
    git add logs/
    git commit -m "Auto-update: logs from $(date)"
    git push origin main
fi
EOF

chmod +x /home/ec2-user/auto_deploy.sh

# Create tasks and logs directories
mkdir -p /home/ec2-user/trade-strategies/tasks
mkdir -p /home/ec2-user/trade-strategies/logs

# Set up cron job to run every 5 minutes
echo "Setting up cron job..."
(crontab -l 2>/dev/null || echo "") | grep -v "auto_deploy.sh" > /tmp/mycron
echo "*/5 * * * * /home/ec2-user/auto_deploy.sh >> /home/ec2-user/trade-strategies/logs/cron.log 2>&1" >> /tmp/mycron
crontab /tmp/mycron
rm /tmp/mycron

echo ""
echo "=========================================="
echo "✅ Auto-deploy setup complete!"
echo "=========================================="
echo ""
echo "How it works:"
echo "1. Every 5 minutes, EC2 auto-pulls from git"
echo "2. To trigger tasks, commit empty files to tasks/"
echo "   - tasks/check_progress.task → runs progress check"
echo "   - tasks/install_deps.task → installs dependencies"
echo "   - tasks/generate_candles.task → generates candles"
echo "   - tasks/run_phase_1.task → runs Phase 1"
echo "3. Results are logged to logs/ and auto-committed back to git"
echo ""
echo "Example: From Claude Code, create tasks/check_progress.task"
echo "Then EC2 will automatically run it within 5 minutes!"
echo ""
