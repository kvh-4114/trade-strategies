# Production Baseline Version 3.0

**Official Release Date:** November 18, 2025
**Status:** Production Ready
**Previous Version:** v2.x (Bar synchronization issue)

---

## Executive Summary

Production Baseline v3.0 is the official, verified backtest of the LinReg baseline trading strategy with **corrected bar synchronization**. This version eliminates a critical systematic error where different symbols had misaligned 4-day bar boundaries, ensuring all symbols trade on identical calendar dates.

### Key Performance Metrics

**Baseline Strategy (All Trades):**
- Total Trades: 21,241
- Total Return: 681.58%
- Final Value: $7,815,819
- Max Drawdown: -9.88%
- Win Rate: 46.29%
- Profit Factor: 2.03
- Date Range: April 2016 - November 2025 (9.5 years)

**Conservative Allocation Strategy (>= 1.0% slope filter):**
- Total Trades: 16,185
- Total Return: 1,067.52%
- Final Portfolio Value: $11,675,243
- Max Drawdown: -7.09%
- Annualized Return: 29.50%
- Win Rate: 46.29%
- Profitable Symbols: 266/270 (98.5%)
- 2025 YTD Return: +9.95%

---

## Version History

### v3.0 (November 18, 2025) - **CURRENT**
**Major Fix: Bar Synchronization**

**Problem Identified:**
- Without `origin='epoch'` in resample calls, different symbols had misaligned 4-day bar boundaries
- Symbols were exiting on different calendar dates (Nov 5, 6, 7) when they should all exit on the same bar
- Portfolio-level calculations were inaccurate due to symbol misalignment
- Potential for lookahead bias in portfolio construction

**Solution Applied:**
- Added `origin='epoch'` to all `df.resample('4D')` calls
- Ensures all symbols share identical bar boundaries synchronized to Unix epoch (1970-01-01)
- All symbols now trade on the same calendar dates

**Files Modified:**
- `baseline_strategy.py:332` - Added `origin='epoch'` to resample function
- `calculate_slope.py:113` - Added `origin='epoch'` to resample function
- `visualize_last_trades.py:44` - Added `origin='epoch'` to resample function

**Verification:**
- All 30 recent trades now exit on Nov 4, 2025 (previously Nov 5, 6, 7)
- 10 sampled symbols confirmed to share 894 common bar dates
- All bars verified to be exactly 4 days apart
- Day-of-week rotation confirmed (Sun→Thu→Mon→Fri→Tue→Sat→Wed cycle)

**Performance Impact:**
- Total P&L: +$514 (+0.005%)
- Final Portfolio Value: +$297,108 (+2.6%)
- Max Drawdown: -7.09% vs -5.49% (more accurate measurement)
- Trade Count: +63 trades (+0.4%)

### v2.x (Prior to November 18, 2025)
- Bar synchronization issue present
- Results not directly comparable to v3.0
- **DO NOT USE FOR PRODUCTION**

---

## Strategy Specification

### Core Parameters

**Entry Signal:**
- Timeframe: 4-day bars (resampled from daily data)
- Candle Type: Heikin Ashi
- Indicator: Linear Regression (13-period, 0 lookahead)
- Entry Condition: HA close crosses above LinReg line
- Entry Price: Close of 4-day bar

**Exit Signal:**
- Indicator: Linear Regression (21-period, -3 lookahead)
- Exit Condition: HA close crosses below LinReg line
- Exit Price: Close of 4-day bar

**Quality Filter (Conservative Allocation):**
- Slope Calculation: 5-period LinReg on HA close at entry
- Slope Metric: Percentage per bar, normalized by average price

**Position Sizing (Conservative Allocation):**
| Entry Slope | Position Size | Multiplier |
|------------|---------------|------------|
| >= 5.0% | $20,000 | 2.0x |
| >= 3.0% | $15,000 | 1.5x |
| >= 2.0% | $12,000 | 1.2x |
| >= 1.0% | $10,000 | 1.0x |
| < 1.0% | $0 | Skip |

**Trading Universe:**
- Total Symbols: 270 (large and mid-cap stocks)
- Symbol Universe Files: `lrg_2013_files.csv`, `mid_2013_files.csv`
- Data Source: Daily OHLC from 2013-01-01 to 2025-11-08

---

## Production Data Files (v3.0)

### Core Strategy Outputs

**Trade Data:**
- `baseline_trades_20251118_075140.csv` - All 21,241 trades with synchronized dates
- `trades_with_slopes_2.2a_20251118_082119.csv` - All trades with entry slopes
- `allocation_trades_20251118_085133.csv` - Conservative allocation subset (16,185 trades)

**Portfolio Analysis:**
- `conservative_portfolio_data_20251118_085203.csv` - Weekly mark-to-market timeline
- `annual_returns_20251118_085417.csv` - Year-by-year breakdown
- `monthly_returns_20251118_085417.csv` - Monthly pattern analysis

**Symbol Performance:**
- `all_symbols_performance_20251118_085605.csv` - All 270 symbols
- `top25_symbols_20251118_085605.csv` - Best performers
- `bottom25_symbols_20251118_085605.csv` - Worst performers

### Analysis Charts

**Portfolio Performance:**
- `conservative_portfolio_full_20251118_085203.png` - Full 9.5-year equity curve with drawdown
- `conservative_portfolio_2025_20251118_085203.png` - 2025 YTD performance

**Strategy Comparison:**
- `open_pnl_analysis_20251118_085133.png` - Baseline vs filtered strategies
- `allocation_strategy_20251118_085133.png` - Position size distribution

**Returns Analysis:**
- `conservative_returns_analysis_20251118_085417.png` - Annual and monthly returns
- `conservative_symbol_analysis_20251118_085605.png` - Top/bottom performers

**Trade Visualizations:**
- 25 individual trade charts in `results/trade_charts/`
- `trade_viewer.html` - Interactive HTML viewer for all trade charts

### Verification Documentation

**Synchronization Fix:**
- `RESYNC_RESULTS_COMPARISON.md` - Before/after comparison
- `RERUN_PLAN.md` - 9-phase re-run execution plan
- `bar_consistency_verification_20251118_105309.txt` - Verification test results

---

## Annual Performance Breakdown

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
| 2025 YTD | +10.07% | 321 |
| **Average** | **30.21%** | **1,619/yr** |

---

## Monthly Performance Pattern

All 12 months show positive average returns:

| Month | Avg Return | Best Feature |
|-------|------------|--------------|
| January | +2.91% | Best month |
| February | +2.73% | Consistent |
| March | +2.25% | Stable |
| April | +2.84% | Strong |
| May | +2.52% | Solid |
| June | +2.16% | Steady |
| July | +2.41% | Reliable |
| August | +2.19% | Positive |
| September | +1.69% | Lower variance |
| October | +1.05% | Weakest (still positive) |
| November | +3.07% | Second best |
| December | +2.58% | Year-end strength |

---

## Top 10 Performing Symbols

| Rank | Symbol | Total P&L | Trades | Avg Slope | Profit Factor |
|------|--------|-----------|--------|-----------|---------------|
| 1 | APLD | $821,503 | 57 | 8.52% | 10.61 |
| 2 | NVAX | $368,507 | 66 | 5.67% | 4.76 |
| 3 | TNDM | $208,790 | 68 | 3.63% | 4.42 |
| 4 | TBCH | $202,821 | 61 | 3.89% | 5.07 |
| 5 | FCEL | $189,796 | 67 | 6.31% | 3.50 |
| 6 | MARA | $188,733 | 60 | 7.41% | 4.39 |
| 7 | PACB | $186,925 | 68 | 4.66% | 3.73 |
| 8 | NKTR | $186,321 | 66 | 4.24% | 4.01 |
| 9 | CIEN | $183,574 | 72 | 3.94% | 4.18 |
| 10 | RARE | $178,464 | 66 | 4.58% | 3.92 |

**Top 25 Contribution:** $4.03M (37.7% of total P&L)

---

## Risk Management Guidelines

### Drawdown Characteristics

**Historical Drawdowns:**
- Maximum Drawdown: -7.09% (v3.0 corrected measurement)
- Typical Drawdown: -2% to -4%
- Recovery Time: Typically 2-4 months
- 2025 Max DD: -1.58%

**Position Sizing Recommendations:**
- Base Position: $10,000 (1.0x)
- Maximum Position: $20,000 (2.0x for slope >= 5.0%)
- Portfolio Heat: Managed by quality filter (skipping weak setups)
- Concurrent Positions: Average 221, Max 411

### Portfolio Construction

**Diversification:**
- 98.5% of symbols profitable over full period
- Average 24.7 trades per exit date
- Spread across 270 symbols reduces single-stock risk

**Capital Requirements:**
- Minimum: $1,000,000 for proper diversification
- Recommended: $2,000,000+ to handle 200+ concurrent positions
- Reserve: 20% cash buffer for volatility

---

## Production Implementation Checklist

### Data Requirements
- [ ] Daily OHLC data for all 270 symbols
- [ ] Data synchronized to Unix epoch for bar alignment
- [ ] Minimum 4-day bars available for entry signal
- [ ] Minimum 21-day bars available for exit signal

### Code Verification
- [ ] Verify `origin='epoch'` in all resample calls
- [ ] Confirm bar boundaries match across all symbols
- [ ] Validate entry/exit signals match backtest logic
- [ ] Test position sizing calculations

### Risk Management
- [ ] Set maximum portfolio heat limits
- [ ] Implement concurrent position limits (recommend 250 max)
- [ ] Configure stop-loss if desired (not in baseline)
- [ ] Set up real-time drawdown monitoring

### Monitoring
- [ ] Daily reconciliation of open positions
- [ ] Weekly P&L analysis vs backtest expectations
- [ ] Monthly performance attribution by symbol
- [ ] Quarterly strategy review

---

## Known Limitations

1. **Backtest Assumptions:**
   - Perfect fill at bar close
   - No slippage modeled
   - No transaction costs included
   - No impact from trading size

2. **Market Conditions:**
   - Strategy tested through 2022 bear market (-2.33%)
   - Performance in extreme volatility not extensively tested
   - Concentration risk in high-slope periods (more aggressive sizing)

3. **Data Quality:**
   - Assumes clean, adjusted OHLC data
   - Corporate actions (splits, dividends) should be pre-adjusted
   - Missing data could affect bar alignment

4. **Strategy Evolution:**
   - No stop-loss mechanism (positions held until exit signal)
   - No take-profit targets
   - Binary position sizing (all-in or all-out per signal)

---

## Version Comparison

### v3.0 vs v2.x

| Metric | v2.x (Misaligned) | v3.0 (Synchronized) | Change |
|--------|-------------------|---------------------|--------|
| Total Trades | 16,122 | 16,185 | +63 |
| Total Return | 1,037.81% | 1,067.52% | +29.71 pp |
| Final Value | $11,378,135 | $11,675,243 | +$297,108 |
| Max Drawdown | -5.49% | -7.09% | -1.60 pp* |
| Annual Return | 29.15% | 29.50% | +0.35 pp |

*More accurate measurement due to proper synchronization

**Recommendation:** Always use v3.0 results for production decisions. v2.x results are systematically biased due to bar misalignment.

---

## File Organization

```
LinReg_baseline/
├── PRODUCTION_BASELINE_V3.0.md (this file)
├── baseline_strategy.py (core backtest engine)
├── calculate_slope.py (slope calculation for filtering)
├── slope_threshold_experiments/
│   ├── RERUN_PLAN.md
│   ├── RESYNC_RESULTS_COMPARISON.md
│   ├── verify_bar_consistency.py
│   ├── baseline_trades_20251118_075140.csv
│   └── results/
│       ├── trades_with_slopes_2.2a_20251118_082119.csv
│       ├── allocation_trades_20251118_085133.csv
│       ├── conservative_portfolio_data_20251118_085203.csv
│       ├── annual_returns_20251118_085417.csv
│       ├── monthly_returns_20251118_085417.csv
│       ├── all_symbols_performance_20251118_085605.csv
│       ├── bar_consistency_verification_20251118_105309.txt
│       └── trade_charts/ (25 visualization PNGs + HTML viewer)
└── historical_data/
    └── 11_8_2025_daily/ (270 symbol CSV files)
```

---

## Technical Support

### Verification Steps

If you need to verify the v3.0 results:

1. **Run bar consistency verification:**
   ```bash
   python verify_bar_consistency.py
   ```
   Expected: All tests pass

2. **Re-run full backtest (70 minutes):**
   ```bash
   python baseline_strategy.py
   python calculate_all_slopes.py
   python open_pnl_and_allocation.py
   python conservative_portfolio_fast.py
   python conservative_returns_analysis.py
   python conservative_symbol_analysis.py
   python visualize_last_trades.py
   python create_trade_viewer.py
   ```

3. **Compare results to documented metrics**

### Troubleshooting

**Issue:** Different number of trades than documented
- **Check:** Verify data files are from 2025-11-08
- **Check:** Confirm `origin='epoch'` in all resample calls
- **Check:** Ensure symbol universe matches (270 symbols)

**Issue:** Different exit dates for recent trades
- **Check:** Bar alignment - all should exit on 2025-11-04
- **Check:** `origin='epoch'` parameter in resample
- **Run:** `verify_bar_consistency.py` to diagnose

**Issue:** Performance metrics don't match
- **Check:** Using Conservative Allocation strategy (>= 1.0% filter)
- **Check:** Position sizing logic matches specification
- **Check:** Weekly sampling for portfolio calculations

---

## Changelog

### v3.0.0 (2025-11-18)
- **[CRITICAL FIX]** Bar synchronization using `origin='epoch'`
- **[IMPROVEMENT]** More accurate portfolio-level metrics
- **[IMPROVEMENT]** Eliminated potential lookahead bias
- **[VERIFICATION]** Added comprehensive bar consistency tests
- **[DOCUMENTATION]** Created PRODUCTION_BASELINE_V3.0.md
- **[DOCUMENTATION]** Created RESYNC_RESULTS_COMPARISON.md
- **[DOCUMENTATION]** Created RERUN_PLAN.md
- **[DATA]** Generated new synchronized trade data files
- **[CHARTS]** Regenerated all analysis charts with corrected data

---

## Contact and Maintenance

**Version:** 3.0.0
**Release Date:** November 18, 2025
**Next Review:** Quarterly (February 2026)
**Status:** Production Ready - Verified

**Maintenance Notes:**
- Re-run full backtest quarterly with updated data
- Verify bar synchronization with each data update
- Monitor live trading performance vs backtest expectations
- Update symbol universe annually

---

**END OF DOCUMENT**

Production Baseline v3.0 is the official, verified, production-ready version of the LinReg baseline trading strategy.
