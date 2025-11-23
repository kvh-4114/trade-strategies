# Cloud Automation Setup

This project uses a **100% cloud-based automated workflow** - no SSH or local development required!

## Architecture

```
Claude Code (Web) → GitHub → EC2 Auto-Deploy → RDS Database
                      ↓
                   Results logged back to GitHub
```

## How It Works

### 1️⃣ One-Time Setup (Run Once on EC2)

From AWS Console → Systems Manager → Session Manager, connect to your EC2 and run:

```bash
cd ~/trade-strategies
git pull origin main
bash scripts/setup_auto_deploy.sh
```

This sets up:
- Auto-pull from GitHub every 5 minutes
- Task-based execution system
- Automatic logging back to git

### 2️⃣ Trigger Tasks from Claude Code (Anywhere!)

From Claude Code web interface, I can trigger tasks by committing task files:

```bash
# Check database progress
touch tasks/check_progress.task
git add tasks/ && git commit -m "Check DB progress" && git push

# Install dependencies
touch tasks/install_deps.task
git add tasks/ && git commit -m "Install deps" && git push

# Generate candles
touch tasks/generate_candles.task
git add tasks/ && git commit -m "Generate candles" && git push

# Run Phase 1 testing
touch tasks/run_phase_1.task
git add tasks/ && git commit -m "Run Phase 1" && git push
```

### 3️⃣ EC2 Auto-Executes (Within 5 Minutes)

EC2's cron job:
1. Pulls latest code from GitHub
2. Detects task files in `tasks/`
3. Executes the corresponding script
4. Logs results to `logs/`
5. Commits logs back to GitHub
6. Deletes the task file

### 4️⃣ View Results from Claude Code

```bash
git pull origin main
cat logs/progress_*.log
cat logs/phase1_*.log
```

## Available Tasks

| Task File | Action | Script |
|-----------|--------|--------|
| `tasks/check_progress.task` | Check DB progress | `scripts/check_db_progress.py` |
| `tasks/install_deps.task` | Install Python deps | `pip install -r requirements.txt` |
| `tasks/generate_candles.task` | Generate candles | `scripts/generate_candles.py` |
| `tasks/run_phase_1.task` | Run Phase 1 testing | `scripts/run_phase_1.py` |

## Helper Script (Optional)

For convenience, use the trigger script:

```bash
./scripts/trigger_task.sh check_progress
./scripts/trigger_task.sh install_deps
./scripts/trigger_task.sh run_phase_1
```

## Monitoring

- **Live logs on EC2**: Check `logs/cron.log` via Session Manager
- **Results in git**: Pull latest and check `logs/` directory
- **CloudWatch**: Set up CloudWatch Logs for real-time monitoring (optional)

## AWS Systems Manager Alternative

For immediate execution (no 5-minute wait), use AWS Systems Manager:

1. Go to AWS Console → Systems Manager → Run Command
2. Select document: `AWS-RunShellScript`
3. Select your EC2 instance
4. Command:
   ```bash
   cd /home/ec2-user/trade-strategies
   git pull origin main
   python3 scripts/check_db_progress.py
   ```

## Benefits

✅ **Zero SSH required** - Everything via web interfaces
✅ **Mobile-friendly** - Trigger tasks from phone via GitHub web
✅ **Automated** - Set and forget, EC2 handles execution
✅ **Logged** - All results committed back to git
✅ **Scalable** - Easy to add new tasks

## Workflow Example

```
1. Claude Code: "Let's check database progress"
2. Claude commits: tasks/check_progress.task
3. EC2 auto-pulls (within 5 min)
4. EC2 runs: check_db_progress.py
5. EC2 commits: logs/progress_20250123_143022.log
6. Claude pulls and reads results
7. Claude: "Progress is at 45%, let's continue..."
```

## Next Steps

1. Run one-time setup: `bash scripts/setup_auto_deploy.sh`
2. Test by triggering: `tasks/check_progress.task`
3. Wait 5 minutes and check `logs/` directory
4. Start Phase 1 once candles complete!
