#!/bin/bash
# One-command setup: Merge latest code and run setup
# Run this on EC2 via AWS Session Manager (just copy-paste one line)

set -e

echo "=========================================="
echo "Merging latest code and running setup..."
echo "=========================================="

cd ~/trade-strategies

# Configure git
git config pull.rebase false

# Fetch all branches
git fetch --all

# Checkout main
git checkout main

# Merge the feature branch with all the latest code
git merge origin/claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ --no-edit

echo ""
echo "✅ Code merged! Now running setup..."
echo ""

# Run setup
bash scripts/setup_auto_deploy.sh

echo ""
echo "=========================================="
echo "✅ ALL DONE! System is now automated."
echo "=========================================="
