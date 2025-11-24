#!/usr/bin/env python3
"""
Manual task runner - use when cron isn't available
Run via: python3 scripts/manual_task_runner.py <task_name>
"""

import sys
import os
import subprocess
from datetime import datetime

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)


def run_task(task_name):
    """Run a specific task manually."""

    log_dir = os.path.join(parent_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    tasks = {
        'check_progress': {
            'script': 'scripts/check_db_progress.py',
            'log': f'logs/progress_{timestamp}.log'
        },
        'install_deps': {
            'cmd': 'pip3 install -r requirements.txt --user',
            'log': f'logs/install_{timestamp}.log'
        },
        'generate_candles': {
            'script': 'scripts/generate_candles.py',
            'log': f'logs/candles_{timestamp}.log'
        },
        'run_phase_1': {
            'script': 'scripts/run_phase_1.py',
            'log': f'logs/phase1_{timestamp}.log'
        }
    }

    if task_name not in tasks:
        print(f"Unknown task: {task_name}")
        print(f"Available tasks: {', '.join(tasks.keys())}")
        return 1

    task = tasks[task_name]
    log_file = os.path.join(parent_dir, task['log'])

    print(f"Running task: {task_name}")
    print(f"Log file: {log_file}")

    try:
        with open(log_file, 'w') as log:
            if 'script' in task:
                cmd = ['python3', os.path.join(parent_dir, task['script'])]
            else:
                cmd = task['cmd'].split()

            result = subprocess.run(
                cmd,
                cwd=parent_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ Task completed successfully!")
                print(f"Check log: {log_file}")
                return 0
            else:
                print(f"❌ Task failed with exit code {result.returncode}")
                print(f"Check log: {log_file}")
                return result.returncode

    except Exception as e:
        print(f"❌ Error running task: {e}")
        return 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/manual_task_runner.py <task_name>")
        print("\nAvailable tasks:")
        print("  check_progress  - Check database progress")
        print("  install_deps    - Install Python dependencies")
        print("  generate_candles - Generate candles")
        print("  run_phase_1     - Run Phase 1 testing")
        sys.exit(1)

    task_name = sys.argv[1]
    sys.exit(run_task(task_name))
