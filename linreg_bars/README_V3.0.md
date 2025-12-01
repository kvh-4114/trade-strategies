# LinReg Baseline - Production Version 3.0

**Official Production-Ready Trading Strategy Backtest**

---

## Quick Start

**Current Version:** 3.0.0 (Released: November 18, 2025)

**Performance:** 1,067.52% total return | 29.50% annualized | -7.09% max drawdown

**Read This First:** `V3.0_RELEASE_SUMMARY.md` (5-minute overview)

**Full Documentation:** `PRODUCTION_BASELINE_V3.0.md` (complete reference)

---

## What is This?

This is the official, verified backtest of the LinReg Baseline trading strategy - a long-only momentum strategy using:
- 4-day Heikin Ashi bars
- Linear regression trend following
- Conservative slope-based position sizing
- 270-symbol diversified portfolio

**Conservative Allocation Strategy Results (v3.0):**
- 16,185 trades over 9.5 years (Apr 2016 - Nov 2025)
- $1,000,000 → $11,675,243 (1,067.52% gain)
- 29.50% annualized return
- -7.09% maximum drawdown
- 98.5% of symbols profitable
- 2025 YTD: +9.95%

---

## Version 3.0 - What's New

### Critical Fix: Bar Synchronization

v3.0 fixes a systematic error where different symbols had misaligned 4-day bar boundaries. The fix ensures all symbols trade on identical calendar dates.

**Before (v2.x):** Recent trades exited on Nov 5, 6, and 7
**After (v3.0):** All recent trades exit on Nov 4

**Why This Matters:**
- More accurate portfolio-level metrics
- Proper risk management calculations
- Elimination of potential lookahead bias
- Synchronized across all 270 symbols

**Do NOT use v2.x results for production decisions.**

---

## Documentation Structure

C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_14_2025_daily

```
LinReg_baseline/
├── README_V3.0.md ← You are here
├── VERSION.txt ← Quick version check
├── V3.0_RELEASE_SUMMARY.md ← 5-min overview
├── PRODUCTION_BASELINE_V3.0.md ← Full documentation (27 pages)
│
├── Core Strategy Files:
│   ├── baseline_strategy.py ← Main backtest engine
│   ├── calculate_slope.py ← Entry slope calculation
│   └── (other analysis scripts)
│
├── v3.0 Verification:
│   └── slope_threshold_experiments/
│       ├── RERUN_PLAN.md ← 9-phase execution plan
│       ├── RESYNC_RESULTS_COMPARISON.md ← Before/after analysis
│       ├── verify_bar_consistency.py ← Bar sync verification
│       ├── verify_trading_days_only.py ← Trading days check
│       └── results/ ← All v3.0 data files
│
└── Historical Data:
    └── historical_data/11_8_2025_daily/ ← 270 symbol CSVs
```

---

## Key Data Files (v3.0)

All files timestamped 20251118 (November 18, 2025):

**Trade Data:**
- `baseline_trades_20251118_075140.csv` - All 21,241 trades
- `trades_with_slopes_2.2a_20251118_082119.csv` - With entry slopes
- `allocation_trades_20251118_085133.csv` - Conservative subset (16,185 trades)

**Portfolio Analysis:**
- `conservative_portfolio_data_20251118_085203.csv` - Weekly timeline
- `annual_returns_20251118_085417.csv` - Year-by-year
- `monthly_returns_20251118_085417.csv` - Monthly patterns

**Symbol Performance:**
- `all_symbols_performance_20251118_085605.csv` - All 270 symbols
- `top25_symbols_20251118_085605.csv` - Best performers
- `bottom25_symbols_20251118_085605.csv` - Worst performers

**Charts:**
- Portfolio equity curves (full period + 2025 YTD)
- 25 trade visualizations + HTML viewer
- Returns analysis (annual/monthly)
- Symbol performance analysis

**Verification:**
- `bar_consistency_verification_20251118_105309.txt` - All tests passed

---

## How to Use This

### For Strategy Review:
1. Read `V3.0_RELEASE_SUMMARY.md` for quick overview
2. Review `PRODUCTION_BASELINE_V3.0.md` for full details
3. Check charts in `slope_threshold_experiments/results/`

### For Production Implementation:
1. Review strategy parameters in `PRODUCTION_BASELINE_V3.0.md`
2. Follow production checklist
3. Verify code has `origin='epoch'` in all resample calls
4. Test with paper trading first

### To Verify Results:
```bash
cd slope_threshold_experiments
python verify_bar_consistency.py
python verify_trading_days_only.py
```

### To Re-run Full Backtest (~70 minutes):
```bash
cd slope_threshold_experiments
python baseline_strategy.py
python calculate_all_slopes.py
python open_pnl_and_allocation.py
python conservative_portfolio_fast.py
python conservative_returns_analysis.py
python conservative_symbol_analysis.py
python visualize_last_trades.py
python create_trade_viewer.py
```

---

## Strategy Overview

### Entry Signal
- **Timeframe:** 4-day bars (resampled from daily)
- **Candle Type:** Heikin Ashi
- **Indicator:** 13-period Linear Regression (0 lookahead)
- **Trigger:** HA close crosses above LinReg line
- **Entry Price:** Close of 4-day bar

### Exit Signal
- **Indicator:** 21-period Linear Regression (-3 lookahead)
- **Trigger:** HA close crosses below LinReg line
- **Exit Price:** Close of 4-day bar

### Position Sizing (Conservative)
- **Slope >= 5.0%:** $20,000 (2.0x base)
- **Slope >= 3.0%:** $15,000 (1.5x base)
- **Slope >= 2.0%:** $12,000 (1.2x base)
- **Slope >= 1.0%:** $10,000 (1.0x base)
- **Slope < 1.0%:** Skip trade

**Slope Calculation:** 5-period LinReg on HA close at entry, % per bar

---

## Performance Summary

### Annual Returns
| Year | Return | Trades |
|------|--------|--------|
| 2016 | +27.21% | 1,383 |
| 2017 | +47.35% | 1,582 |
| 2018 | +40.57% | 1,713 |
| 2019 | +29.41% | 1,756 |
| 2020 | +96.90% | 2,143 |
| 2021 | +28.35% | 1,890 |
| 2022 | -2.33% | 1,668 |
| 2023 | +12.31% | 1,847 |
| 2024 | +12.22% | 1,882 |
| 2025 | +10.07% | 321 (YTD) |

**Average:** 30.21% per year

### Key Metrics
- **Win Rate:** 46.29%
- **Profit Factor:** 2.03
- **Max Drawdown:** -7.09%
- **Profitable Symbols:** 266/270 (98.5%)
- **Average Concurrent Positions:** 221
- **Max Concurrent Positions:** 411

---

## Risk Management

**Drawdown Profile:**
- Historical max: -7.09%
- Typical range: -2% to -4%
- 2025 YTD max: -1.58%
- Recovery time: 2-4 months typical

**Capital Requirements:**
- Minimum: $1,000,000 (for proper diversification)
- Recommended: $2,000,000+ (to handle 200+ positions)
- Cash reserve: 20% buffer recommended

**Known Limitations:**
- No slippage or transaction costs modeled
- Perfect fills assumed at bar close
- No stop-loss mechanism (hold until exit signal)
- Performance in extreme volatility not extensively tested

---

## Top 10 Symbols (v3.0)

| Symbol | Total P&L | Trades | Avg Slope | PF |
|--------|-----------|--------|-----------|-----|
| APLD | $821,503 | 57 | 8.52% | 10.61 |
| NVAX | $368,507 | 66 | 5.67% | 4.76 |
| TNDM | $208,790 | 68 | 3.63% | 4.42 |
| TBCH | $202,821 | 61 | 3.89% | 5.07 |
| FCEL | $189,796 | 67 | 6.31% | 3.50 |
| MARA | $188,733 | 60 | 7.41% | 4.39 |
| PACB | $186,925 | 68 | 4.66% | 3.73 |
| NKTR | $186,321 | 66 | 4.24% | 4.01 |
| CIEN | $183,574 | 72 | 3.94% | 4.18 |
| RARE | $178,464 | 66 | 4.58% | 3.92 |

**Top 25 contribute:** $4.03M (37.7% of total P&L)

---

## Verification Status

**Bar Synchronization:**
- [PASS] All recent trades exit on same date
- [PASS] All symbols share common bar dates
- [PASS] All trades align to bar boundaries
- [PASS] All bars exactly 4 days apart
- [PASS] Day-of-week rotation confirmed

**Trading Days:**
- [PASS] Daily data contains only Mon-Fri
- [PASS] No weekend price data in OHLC
- [NOTE] Bar timestamps can fall on weekends (window boundaries only)

**Full Report:** `bar_consistency_verification_20251118_105309.txt`

---

## Support and Maintenance

**Current Version:** 3.0.0
**Status:** Production Ready - Verified
**Next Review:** Quarterly (February 2026)

**For Issues or Questions:**
- Check full documentation: `PRODUCTION_BASELINE_V3.0.md`
- Review verification results in `slope_threshold_experiments/results/`
- Re-run verification scripts to confirm setup

**Maintenance Schedule:**
- Quarterly backtest re-run with updated data
- Annual symbol universe review
- Monthly performance monitoring vs backtest

---

## Quick Reference

**Good for:**
- Long-only momentum strategies
- Diversified multi-symbol portfolios
- Trend-following with quality filter
- Conservative risk management

**Not suitable for:**
- Short-term trading (uses 4-day bars)
- Mean reversion strategies
- High-frequency trading
- Strategies requiring stop-losses

**Best Use Cases:**
- Baseline for strategy comparison
- Conservative long-only allocation
- Diversified trend following
- Quality-filtered momentum

---

## Trading & Analysis Tools

### For Live Trading
See `LIVE_TRADING_GUIDE.md` for:
- Position selection framework (6 factors)
- Daily workflow and execution
- Risk management guidelines
- Common issues and solutions

### Analysis Tools
See `ANALYSIS_TOOLS.md` for:
- Trading opportunities scanner
- Opportunity chart generator (top 30 positions)
- Complete analysis pipeline reference
- Verification tools

### Quick Analysis Commands

**Identify Best Current Positions:**
```bash
python analyze_current_opportunities.py
python create_trading_opportunities_charts.py
# Open: results/opportunity_charts/trading_opportunities.html
```

**Re-run Full Analysis:**
```bash
python baseline_strategy.py                    # 10 min
python calculate_all_slopes.py                 # 15 min
python open_pnl_and_allocation.py              # 2 min
python conservative_portfolio_fast.py          # 2 min
python conservative_returns_analysis.py        # 1 min
python conservative_symbol_analysis.py         # 1 min
python visualize_last_trades.py                # 3 min
python create_trade_viewer.py                  # 30 sec
# Total: ~35 minutes
```

---

## Documentation Index

**Version 3.0 is the official production baseline.**

- **Complete Strategy Specs:** `PRODUCTION_BASELINE_V3.0.md` (27 pages)
- **Quick Overview:** `V3.0_RELEASE_SUMMARY.md` (5 min read)
- **Live Trading Guide:** `LIVE_TRADING_GUIDE.md` (NEW - practical trading)
- **Analysis Tools Reference:** `ANALYSIS_TOOLS.md` (NEW - tool documentation)
- **Quick Start:** `README_V3.0.md` (this file)
- **Version Info:** `VERSION.txt`

---

**Released:** November 18, 2025
**Status:** Production Ready - Verified
