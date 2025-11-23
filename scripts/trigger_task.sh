#!/bin/bash
# Helper script to trigger tasks on EC2 from Claude Code
# Usage: ./trigger_task.sh <task_name>

TASK_NAME=$1

if [ -z "$TASK_NAME" ]; then
    echo "Usage: ./trigger_task.sh <task_name>"
    echo ""
    echo "Available tasks:"
    echo "  check_progress  - Check database progress"
    echo "  install_deps    - Install Python dependencies"
    echo "  generate_candles - Generate candles"
    echo "  run_phase_1     - Run Phase 1 testing"
    exit 1
fi

# Create task file
mkdir -p tasks
touch "tasks/${TASK_NAME}.task"

# Commit and push
git add "tasks/${TASK_NAME}.task"
git commit -m "Trigger task: ${TASK_NAME}"
git push origin main

echo "✅ Task '${TASK_NAME}' triggered!"
echo "EC2 will pick it up within 5 minutes and run it automatically."
echo ""
echo "To see results, check logs/ directory after a few minutes:"
echo "  git pull origin main"
echo "  cat logs/latest.log"
