# Analysis Tools - LinReg Baseline v3.0

**Version:** 3.0.0
**Last Updated:** November 18, 2025

---

## Overview

This document describes the analysis tools created for the LinReg Baseline strategy, beyond the core backtest pipeline.

---

## Trading Opportunity Analysis

### 1. Current Opportunities Scanner

**Script:** `analyze_current_opportunities.py`

**Purpose:** Identify the best current open positions to join based on multiple factors.

**Usage:**
```bash
python analyze_current_opportunities.py
```

**Output:** Console analysis across 6 factors

**Factors Analyzed:**

1. **Most Recent Entries** - Freshest signals (last 30 days)
2. **Highest Entry Slopes** - Strongest momentum at entry
3. **Highest Current P&L** - What's working now
4. **Best P&L Percentage** - Most efficient positions
5. **Composite Score** - Combined ranking (30% recency + 40% slope + 30% P&L)
6. **High Conviction Winners** - 2.0x positions with positive P&L

**Key Metrics Provided:**
- Entry date and days in trade
- Entry slope (% per 4-day bar)
- Current P&L (dollars and percentage)
- Position multiplier (1.0x to 2.0x)
- Position breakdown by conviction level

---

### 2. Opportunity Chart Generator

**Script:** `create_trading_opportunities_charts.py`

**Purpose:** Generate detailed charts for the top 30 trading opportunities across 3 categories.

**Usage:**
```bash
python create_trading_opportunities_charts.py
```

**Output:**
- 30 PNG charts in `results/opportunity_charts/`
- Interactive HTML viewer: `results/opportunity_charts/trading_opportunities.html`

**Categories (10 positions each):**

1. **High-Conviction Recent Entries**
   - 2.0x position multiplier (slope >= 5.0%)
   - Entered within last 30 days
   - Ranked by entry slope

2. **Long-Term Winners**
   - Held 100+ days
   - Currently profitable
   - Ranked by total P&L

3. **High-Conviction Winners**
   - 2.0x multiplier AND profitable
   - Best risk/reward opportunities
   - Ranked by total P&L

**Chart Features:**
- Dual panel: Natural 4-day candles + Heikin Ashi candles
- Entry and Exit LinReg lines plotted
- Entry point marked with green triangle
- Title shows: Entry date, current P&L, entry slope, current slope, position multiplier
- Date range: Last 90 days or from entry (whichever is longer)

---

## Core Backtest Pipeline

### Phase 1: Generate Baseline Trades

**Script:** `baseline_strategy.py`

**Usage:**
```bash
python baseline_strategy.py
```

**Output:** `results/baseline_trades_[timestamp].csv`

**Duration:** ~10 minutes for 269 symbols

**What It Does:**
- Runs full backtest on all symbols
- Uses Backtrader framework
- Implements dual LinReg strategy (13-period entry, 21-period exit)
- Generates trades with OPEN/CLOSED status
- Records entry/exit dates, prices, P&L

---

### Phase 2: Calculate Entry Slopes

**Script:** `calculate_all_slopes.py`

**Usage:**
```bash
python calculate_all_slopes.py
```

**Input:** Latest baseline trades CSV
**Output:** `results/trades_with_slopes_2.2a_[timestamp].csv`

**Duration:** ~15 minutes for 21,000+ trades

**What It Does:**
- Loads baseline trades
- For each trade, loads symbol's historical data
- Resamples to 4-day bars with `origin='epoch'`
- Calculates Heikin Ashi candles
- Computes 5-period LinReg slope at entry
- Adds slope column to trades dataframe

---

### Phase 3: Allocation Strategy Analysis

**Script:** `open_pnl_and_allocation.py`

**Usage:**
```bash
python open_pnl_and_allocation.py
```

**Input:** Trades with slopes CSV
**Output:**
- `results/allocation_trades_[timestamp].csv`
- `results/open_pnl_analysis_[timestamp].png`
- `results/allocation_strategy_[timestamp].png`

**Duration:** ~2 minutes

**What It Does:**
- Compares baseline vs slope-filtered strategies
- Applies conservative allocation (>= 1.0% slope filter)
- Applies variable position sizing based on slope
- Generates comparison charts

---

### Phase 4: Portfolio Timeline Analysis

**Script:** `conservative_portfolio_fast.py`

**Usage:**
```bash
python conservative_portfolio_fast.py
```

**Input:** Allocation trades CSV
**Output:**
- `results/conservative_portfolio_data_[timestamp].csv`
- `results/conservative_portfolio_full_[timestamp].png`
- `results/conservative_portfolio_2025_[timestamp].png`

**Duration:** ~2 minutes

**What It Does:**
- Creates weekly portfolio mark-to-market timeline
- Calculates realized + unrealized P&L
- Tracks concurrent positions over time
- Generates equity curve with drawdown
- Creates 2025 YTD specific chart

---

### Phase 5: Returns Analysis

**Script:** `conservative_returns_analysis.py`

**Usage:**
```bash
python conservative_returns_analysis.py
```

**Input:** Portfolio data CSV
**Output:**
- `results/annual_returns_[timestamp].csv`
- `results/monthly_returns_[timestamp].csv`
- `results/conservative_returns_analysis_[timestamp].png`

**Duration:** ~1 minute

**What It Does:**
- Analyzes returns by year (2016-2025)
- Analyzes returns by month (averaged across years)
- Calculates average, median, std dev
- Generates combined visualization

---

### Phase 6: Symbol Performance Analysis

**Script:** `conservative_symbol_analysis.py`

**Usage:**
```bash
python conservative_symbol_analysis.py
```

**Input:** Allocation trades CSV
**Output:**
- `results/all_symbols_performance_[timestamp].csv`
- `results/top25_symbols_[timestamp].csv`
- `results/bottom25_symbols_[timestamp].csv`
- `results/conservative_symbol_analysis_[timestamp].png`

**Duration:** ~1 minute

**What It Does:**
- Calculates per-symbol statistics (total P&L, trade count, win rate, etc.)
- Identifies top 25 and bottom 25 performers
- Generates scatter plot and tables
- Shows contribution percentages

---

### Phase 7: Trade Visualizations

**Script:** `visualize_last_trades.py`

**Usage:**
```bash
python visualize_last_trades.py
```

**Input:** Trades with slopes CSV
**Output:** 25 PNG charts in `results/trade_charts/`

**Duration:** ~3 minutes

**What It Does:**
- Selects 25 most recent trades (by exit date)
- Generates detailed chart for each trade
- Shows natural + Heikin Ashi candles
- Marks entry/exit points
- Plots LinReg lines

---

### Phase 8: HTML Trade Viewer

**Script:** `create_trade_viewer.py`

**Usage:**
```bash
python create_trade_viewer.py
```

**Input:** Trade charts PNGs
**Output:** `results/trade_charts/trade_viewer.html`

**Duration:** ~30 seconds

**What It Does:**
- Creates interactive HTML gallery
- Displays all 25 trade charts
- Sortable by various metrics
- Opens in web browser for easy browsing

---

## Verification Tools

### Bar Consistency Checker

**Script:** `verify_bar_consistency.py`

**Usage:**
```bash
python verify_bar_consistency.py
```

**Purpose:** Verify all symbols share identical 4-day bar boundaries

**Tests Performed:**
1. All recent trades exit on same date
2. Sampled symbols share common bar dates
3. All bars are exactly 4 days apart
4. Day-of-week rotation is correct
5. Bar boundaries align to Unix epoch

**Output:** Console report + verification text file

---

### Trading Days Verification

**Script:** `verify_trading_days_only.py`

**Usage:**
```bash
python verify_trading_days_only.py
```

**Purpose:** Confirm daily data contains only Monday-Friday trading days

**Output:** Console report showing any weekend data issues

---

## Helper Scripts

### Slope Calculator Module

**File:** `calculate_slope.py`

**Purpose:** Reusable functions for slope calculation

**Key Functions:**
- `calculate_slope()` - LinReg slope as % per bar
- `calculate_slope_from_ha()` - Slope from Heikin Ashi closes
- `load_symbol_data()` - Load and prepare symbol data
- `resample_to_4day()` - Resample with epoch origin

**Usage:** Import into other scripts
```python
from calculate_slope import calculate_slope, resample_to_4day
```

---

## Output File Naming Convention

All outputs use timestamp format: `YYYYMMDD_HHMMSS`

**Examples:**
- `baseline_trades_20251118_075140.csv`
- `conservative_portfolio_full_20251118_085203.png`

**Benefits:**
- Prevents overwriting previous runs
- Easy to identify latest results
- Maintains history of analysis runs

---

## Running Complete Analysis Pipeline

**To regenerate all results from scratch:**

```bash
# Phase 1: Backtest (10 min)
python baseline_strategy.py

# Phase 2: Calculate slopes (15 min)
python calculate_all_slopes.py

# Phase 3-6: Analysis pipeline (5 min total)
python open_pnl_and_allocation.py
python conservative_portfolio_fast.py
python conservative_returns_analysis.py
python conservative_symbol_analysis.py

# Phase 7-8: Visualizations (3-4 min)
python visualize_last_trades.py
python create_trade_viewer.py

# Optional: Trading opportunities analysis (5 min)
python analyze_current_opportunities.py
python create_trading_opportunities_charts.py

# Total time: ~40-45 minutes
```

---

## Data Dependencies

All scripts expect:

**Historical Data Location:**
```
C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_14_2025_daily\
```

**File Pattern:**
```
{SYMBOL}_trades_[11_14_2025].csv
```

**Required Columns in Daily Data:**
- `date` (YYYY-MM-DD format)
- `open`
- `high`
- `low`
- `close`
- `volume`

---

## Common Issues & Solutions

### Issue: "No trades file found"
**Solution:** Run earlier phases first (baseline_strategy.py, calculate_all_slopes.py)

### Issue: "Historical data directory not found"
**Solution:** Update `HIST_DATA_DIR` path in scripts to match your data location

### Issue: Charts show wrong dates
**Solution:** Verify `origin='epoch'` is used in all resample calls

### Issue: Slow performance
**Solution:**
- Use SSD for data files
- Close other applications
- Consider multiprocessing for large symbol counts

---

## Customization Guide

### Changing Data Date

In each script, update:
```python
HIST_DATA_DIR = Path(r"C:\...\11_14_2025_daily")  # Change date here
csv_file = hist_data_dir / f"{symbol}_trades_[11_14_2025].csv"  # And here
```

### Changing Symbol Universe

Modify in `baseline_strategy.py`:
```python
pattern = os.path.join(DAILY_DATA_PATH, '*_trades_*.csv')
files = glob.glob(pattern)
```

### Changing Slope Thresholds

In allocation scripts:
```python
# Current conservative allocation
if entry_slope >= 1.0:
    # Include trade

# More aggressive
if entry_slope >= 0.5:
    # Include trade

# More conservative
if entry_slope >= 2.0:
    # Include trade
```

### Changing Position Sizes

In opportunity analysis:
```python
def get_multiplier(slope):
    if slope >= 5.0: return 2.0   # Change multipliers here
    elif slope >= 3.0: return 1.5
    elif slope >= 2.0: return 1.2
    else: return 1.0
```

---

## Future Enhancements

**Potential Additions:**
- Real-time data integration
- Automated email/SMS alerts for new signals
- Portfolio rebalancing suggestions
- Risk parity position sizing
- Sector/industry analysis
- Correlation matrix for position diversification
- Machine learning for slope threshold optimization

---

## Version History

**v3.0.0 (2025-11-18)**
- Added trading opportunities analysis tools
- Created opportunity chart generator
- Added 6-factor position selection framework
- Enhanced HTML viewers

**v2.0 (Prior)**
- Original backtest pipeline
- Basic visualization tools

---

**For questions or issues with analysis tools, refer to:**
- Live Trading Guide: `LIVE_TRADING_GUIDE.md`
- Strategy Documentation: `PRODUCTION_BASELINE_V3.0.md`
- Quick Start: `README_V3.0.md`
