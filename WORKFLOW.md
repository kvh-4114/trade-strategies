# Supertrend Strategy Development Workflow

## Overview

This document outlines our two-phase approach for developing and optimizing the Supertrend trading strategy.

## Development Philosophy

**Test with sample data → Optimize with full portfolio**

We use a staged approach to balance development speed with comprehensive testing:
1. **Phase 1: Development & Testing** - Use CSV data in git for rapid iteration
2. **Phase 2: Production Optimization** - Use EC2 + database for full portfolio analysis

---

## Phase 1: Development & Testing (Current)

### Purpose
Rapid development and testing with representative sample data, without requiring database access.

### Workflow

1. **Export Sample Data (EC2)**
   ```bash
   # On EC2 where database is accessible
   python3 scripts/export_nvda_data.py
   git add -f data/raw/NVDA_daily.csv
   git commit -m "Add NVDA test data"
   git push
   ```

2. **Development & Testing (Local/Claude)**
   - Pull CSV data from git
   - Run tests with CSV-based data loading
   - Iterate on strategy logic and parameters
   - Verify results match expected behavior

3. **Test Symbols**
   - **Primary:** NVDA (exported, 2464 candles, 28,293% return)
   - **Additional:** 1-2 more symbols for validation
   - Criteria: High-growth stocks that benefit from trend-following

### Advantages
- ✅ No database connection required
- ✅ Fast iteration cycles
- ✅ Reproducible tests (data in git)
- ✅ Can be run from any environment
- ✅ Easy to share and collaborate

### Limitations
- ⚠️ Limited to sample symbols
- ⚠️ Can't test full portfolio diversity
- ⚠️ CSV files add to repo size

---

## Phase 2: Production Optimization (Future)

### Purpose
Comprehensive portfolio-wide optimization with full historical data.

### When to Use
- Strategy logic is finalized and tested
- Ready to find optimal parameters across entire portfolio
- Need to analyze correlations and portfolio-level metrics

### Workflow

1. **Run on EC2**
   ```bash
   # Full portfolio optimization with database access
   python3 scripts/optimize_supertrend_portfolio.py
   ```

2. **Analyze Results**
   - Compare performance across all symbols
   - Identify best parameters for each asset class
   - Calculate portfolio-level metrics (Sharpe, drawdown, etc.)

3. **Document Findings**
   - Optimal parameters per symbol/sector
   - Performance characteristics
   - Risk metrics

### Advantages
- ✅ Full portfolio analysis
- ✅ Production-ready results
- ✅ Comprehensive backtesting
- ✅ Database performance for large datasets

---

## Current Status

### ✅ Completed
- Fixed critical Supertrend bug (`_nextforce = True`)
- Verified indicator calculates correctly
- Tested parameter sensitivity (39 vs 9 trades)
- Created data export script
- Exported NVDA data (2016-2025, 2464 candles)

### 🔄 In Progress
- Waiting for NVDA CSV to be pushed to git
- Need to update test scripts for CSV loading

### ⏭️ Next Steps
1. Pull NVDA CSV from git
2. Update test scripts to load from CSV
3. Run full Supertrend tests
4. Run parameter optimization on NVDA
5. Export 1-2 more symbols for validation
6. Document optimal parameters
7. Move to EC2 for full portfolio optimization

---

## Files & Scripts

### Data Export
- `scripts/export_nvda_data.py` - Export NVDA from database to CSV

### Testing
- `scripts/test_supertrend_direction_changes.py` - Verify direction changes work
- `scripts/test_param_passing.py` - Test with 2 different parameter configs
- `scripts/test_supertrend_manual.py` - Manual calculation baseline

### Optimization
- `scripts/optimize_supertrend_nvda.py` - NVDA parameter grid search
- `scripts/run_phase_3_supertrend.py` - Backtest runner function

### Core Implementation
- `agents/agent_2_strategy_core/supertrend.py` - Fixed indicator
- `agents/agent_2_strategy_core/supertrend_strategy.py` - Strategy logic

---

## Key Learnings

### Supertrend Bug Fix
**Problem:** Indicator's `next()` method never called, all values were NaN
**Solution:** Added `_nextforce = True` and split into `nextstart()/next()`
**Reference:** `SUPERTREND_FIX_SUMMARY.md`

### Testing Approach
- Always verify with manual calculation first
- Use CSV data for rapid development iterations
- Reserve full database runs for production optimization

---

## Branch

**Current:** `claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ`

---

## Contact / Notes

Development paused: Waiting for NVDA CSV push to git
Resume: Pull CSV → Update scripts → Run tests → Optimize

Last updated: 2025-11-28
