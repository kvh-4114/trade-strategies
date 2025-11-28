# Phase 2 Partial Results Analysis

## Overview

This document explains how to analyze Phase 2 results while the optimization is still running.

The analysis script provides:
- **Progress tracking** - How many backtests completed, which configs/stocks tested
- **Parameter distribution** - Which parameter combinations have been tested most
- **Parameter sensitivity** - How individual parameters affect performance
- **Top performers** - Best configs by Sharpe ratio, return, and win rate

## Running the Analysis on EC2

### 1. Connect to EC2 and navigate to project:

```bash
# SSH to EC2
ssh ec2-user@<your-ec2-ip>

# Navigate to project
cd ~/trade-strategies
```

### 2. Pull latest code:

```bash
# Fetch and pull latest changes
git fetch origin claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ
git pull origin claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ
```

### 3. Run the analysis:

```bash
# Activate virtual environment (if needed)
source venv/bin/activate

# Run analysis
python3 scripts/analyze_phase_2_partial.py
```

### 4. Check Phase 2 process:

```bash
# Check if Phase 2 is still running
ps aux | grep run_phase_2

# Follow Phase 2 logs
tail -f logs/phase_2.log
```

## What the Analysis Shows

### 1. Progress Statistics
- Total backtests completed (target: 34,200)
- Unique parameter configurations tested (target: 180)
- Unique stocks tested (target: 190)
- Completion percentage

### 2. Parameter Distribution
Top 50 parameter combinations by number of tests, showing:
- Mean lookback
- StdDev lookback
- Entry threshold
- Exit type (mean, opposite_band, profit_target)
- Stop loss type
- Number of stocks tested with this config
- Average performance metrics

### 3. Parameter Sensitivity
Individual parameter effects:
- **Mean Lookback** (10, 15, 20, 25, 30) - How lookback period affects performance
- **Entry Threshold** (1.5, 2.0, 2.5, 3.0) - How threshold affects performance
- **Exit Type** - Which exit strategy works best
- **Stop Loss Type** - Whether stop losses help or hurt

### 4. Top Performers
Top 10 configurations by:
- **Sharpe Ratio** - Best risk-adjusted returns
- **Total Return** - Highest absolute returns
- **Win Rate** - Highest percentage of winning trades

## Interpreting Results

### Early in Phase 2 (< 30% complete):
- Parameter distribution will be uneven (some configs tested more than others)
- Top performers may not be statistically significant yet
- Focus on parameter sensitivity to see trends

### Mid-Phase 2 (30-70% complete):
- More balanced parameter distribution
- Top performers become more reliable
- Can start identifying winning patterns

### Late Phase 2 (> 70% complete):
- Most configs tested on most stocks
- Top performers highly reliable
- Ready to make deployment decisions

## Key Metrics

### Sharpe Ratio
- **> 1.0** - Excellent risk-adjusted returns
- **0.5 - 1.0** - Good risk-adjusted returns
- **0 - 0.5** - Acceptable but suboptimal
- **< 0** - Poor risk-adjusted returns (losing money or too volatile)

### Total Return
- **> 20%** - Excellent (for multi-year backtest)
- **10-20%** - Good
- **5-10%** - Acceptable
- **< 5%** - Poor

### Win Rate
- **> 70%** - Excellent (mean reversion typically high win rate)
- **60-70%** - Good
- **50-60%** - Acceptable
- **< 50%** - Poor (losing more often than winning)

## Expected Insights

Based on Phase 1, we expect:
- **Lookback 20** performed well in baseline
- **Threshold 2.0** was the baseline
- Parameter optimization should improve on baseline 3.98% return

Key questions:
1. Do shorter/longer lookbacks improve performance?
2. Do tighter/wider thresholds improve performance?
3. Which exit strategy works best? (mean, opposite_band, profit_target)
4. Do stop losses improve or hurt performance?

## Next Steps After Analysis

1. **If clear winners emerge** - Document top 5-10 configs for deployment
2. **If results are mixed** - Wait for Phase 2 to complete for more data
3. **If baseline still best** - Consider Phase 1 baseline is already optimal
4. **If new configs better** - Recommend parameter updates for live trading
