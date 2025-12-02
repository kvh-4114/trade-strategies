# Phase 2 Analysis - Quick Reference

## Analysis Scripts Created

I've created three analysis scripts to examine Phase 2 results:

### 1. Quick Progress Check
**Purpose:** Check how much of Phase 2 is complete

```bash
python3 scripts/check_phase_2_progress.py
```

**Output:**
- Number of backtests completed (target: 34,200)
- Percentage complete
- Remaining backtests
- Latest result timestamp

---

### 2. Top Configurations
**Purpose:** See the best performing parameter combinations

```bash
# Default: Top 20 configs with at least 50 tests
python3 scripts/phase_2_top_configs.py

# Custom: Top 30 configs with at least 100 tests
python3 scripts/phase_2_top_configs.py --limit 30 --min-tests 100

# Early in Phase 2: Lower threshold to see results
python3 scripts/phase_2_top_configs.py --min-tests 10
```

**Output:**
- Top N configurations ranked by Sharpe ratio
- Shows: lookback, threshold, exit type, stop loss, returns, Sharpe, win rate
- Comparison to Phase 1 baseline (20/2.0)
- Improvement metrics

---

### 3. Comprehensive Analysis
**Purpose:** Deep dive into parameter sensitivity and distribution

```bash
python3 scripts/analyze_phase_2_partial.py
```

**Output:**
- Progress statistics
- Top 50 parameter combinations by test count
- Parameter sensitivity analysis (how each param affects performance)
- Top 10 performers by Sharpe, return, and win rate

---

## Running on EC2

### Step 1: SSH to EC2
```bash
ssh ec2-user@<your-ec2-ip>
cd ~/trade-strategies
```

### Step 2: Pull latest code
```bash
git fetch origin claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ
git pull origin claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ
```

### Step 3: Run any script
```bash
# Quick check
python3 scripts/check_phase_2_progress.py

# Top configs
python3 scripts/phase_2_top_configs.py

# Full analysis
python3 scripts/analyze_phase_2_partial.py
```

---

## What to Look For

### Early Phase 2 (< 30% complete)
- Use `--min-tests 10` for top_configs to see early results
- Focus on parameter sensitivity trends
- Don't make final decisions yet

### Mid Phase 2 (30-70% complete)
- Use default settings (`--min-tests 50`)
- Start identifying promising configurations
- Compare to Phase 1 baseline

### Late Phase 2 (> 70% complete)
- Increase `--min-tests 100` for high confidence
- Make deployment recommendations
- Focus on Sharpe ratio for risk-adjusted returns

---

## Key Metrics to Watch

### Sharpe Ratio (Primary)
- **> 1.0** = Excellent (deploy immediately)
- **0.5-1.0** = Good (consider deploying)
- **0-0.5** = Acceptable (evaluate trade-offs)
- **< 0** = Poor (reject)

### Total Return
- **> 20%** = Excellent
- **10-20%** = Good
- **< 10%** = Needs improvement

### Win Rate
- **> 70%** = Excellent
- **60-70%** = Good
- **< 60%** = Concerning for mean reversion

---

## Quick Decisions

### If Phase 2 finds better configs:
1. Run `phase_2_top_configs.py` to see improvements
2. Document top 5 configs
3. Prepare for deployment

### If Phase 1 baseline still best:
1. Phase 1 parameters (20/2.0) are already optimal
2. No parameter changes needed
3. Focus on deployment of baseline

### If results are unclear:
1. Wait for Phase 2 to complete
2. Run comprehensive analysis
3. Consider additional parameter ranges

---

## Monitoring Phase 2

### Check if Phase 2 is running:
```bash
ps aux | grep run_phase_2
```

### Follow Phase 2 logs:
```bash
tail -f logs/phase_2.log
```

### Kill Phase 2 if needed:
```bash
# Find PID
ps aux | grep run_phase_2

# Kill
kill <PID>
```

---

## Expected Timeline

- **Phase 2 started:** From previous session
- **Last known progress:** 61.3% (21,182 / 34,200)
- **Estimated remaining:** ~1-2 hours (depends on EC2 performance)
- **Expected completion:** Check with progress script

---

## Next Steps

1. **SSH to EC2** and pull latest code
2. **Run progress check** to see current status
3. **Run top configs** to see if clear winners emerged
4. **If < 70% complete:** Wait for more results
5. **If > 70% complete:** Run full analysis and make recommendations
