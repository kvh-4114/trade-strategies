# Quick Start Guide - Claude Code Web

**100% cloud-based workflow - no local installation required!**

## ✅ What's Already Done

- ✅ 268 stocks loaded into RDS (658K rows)
- ✅ Candle generation running on EC2 (in progress)
- ✅ Agent 3 built (backtesting framework)
- ✅ Phase 1 runner script ready
- ✅ Cloud automation system created

## 🚀 Next: One-Time Setup (5 minutes)

### From Your Phone/Browser

1. **Open AWS Console** → [Systems Manager](https://console.aws.amazon.com/systems-manager)
2. **Click** Session Manager → Start Session
3. **Select** your EC2 instance → Start Session
4. **Run these commands** in the web terminal:

```bash
cd ~/trade-strategies
git pull origin main
bash scripts/setup_auto_deploy.sh
```

5. **Done!** EC2 now auto-pulls from GitHub every 5 minutes

## 📱 How It Works

### Triggering Tasks (I do this automatically)

```
1. I create: tasks/check_progress.task
2. I commit to GitHub
3. EC2 auto-pulls (within 5 min)
4. EC2 runs: check_db_progress.py
5. EC2 commits: logs/progress_TIMESTAMP.log
6. I pull and show you results
```

### Available Tasks

| Task File | Action |
|-----------|--------|
| `tasks/check_progress.task` | Check candle generation progress |
| `tasks/install_deps.task` | Install Python dependencies |
| `tasks/run_phase_1.task` | Run Phase 1 backtesting |

## 📊 Current Status

**Just triggered:** Database progress check
- Task file committed to GitHub
- EC2 will pick it up within 5 minutes
- Results will appear in `logs/` directory

## 🎯 What's Next

1. **You:** Run one-time setup (AWS Session Manager - 5 min)
2. **Me:** Monitor progress check results
3. **Me:** Trigger dependency installation
4. **Me:** Run validation test (1-2 stocks)
5. **Me:** Launch Phase 1 when candles complete

## 🔧 Manual Alternative (If Needed)

If cron doesn't work, use **AWS Systems Manager Run Command**:

1. AWS Console → Systems Manager → Run Command
2. Document: `AWS-RunShellScript`
3. Select your EC2 instance
4. Commands:
```bash
cd /home/ec2-user/trade-strategies
git pull origin main
python3 scripts/check_db_progress.py
```

---

**Everything is ready!** Just run the one-time setup and we're fully automated. 🚀
