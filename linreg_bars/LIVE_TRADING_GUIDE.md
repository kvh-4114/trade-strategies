# Live Trading Guide - LinReg Baseline v3.0

**Status:** Production Ready
**Last Updated:** November 18, 2025
**For:** Transitioning from backtest to live trading

---

## Overview

This guide helps you transition from backtesting to live trading using the LinReg Baseline v3.0 strategy with Conservative Allocation.

**Key Stats (Backtested 2016-2025):**
- Annualized Return: 29.49%
- Max Drawdown: -7.06%
- Win Rate: 46.29%
- Profitable Symbols: 98.1%

---

## Pre-Trading Checklist

### ✅ Account Setup
- [ ] Minimum capital: $1,000,000 (for proper diversification)
- [ ] Recommended: $2,000,000+ (to handle 200+ concurrent positions)
- [ ] Cash reserve: 20% buffer for volatility
- [ ] Commission structure verified (backtest assumes 0.1%)

### ✅ Data Requirements
- [ ] Daily OHLC data feed for all 269 symbols
- [ ] Data provider with good fill quality
- [ ] Historical data for calculating slopes (minimum 100 days)

### ✅ Technical Setup
- [ ] Bar resampling uses `origin='epoch'`
- [ ] 4-day bars synchronized across all symbols
- [ ] Entry/exit signals match backtest logic
- [ ] Position sizing calculator working

---

## Position Selection Framework

### How to Choose Which Stocks to Trade

Use the **Trading Opportunities Analysis** to identify the best current positions:

```bash
python analyze_current_opportunities.py
python create_trading_opportunities_charts.py
```

This generates:
- Analysis across 6 key factors
- Top 30 position charts in `results/opportunity_charts/`
- Interactive HTML viewer for browsing opportunities

### Selection Factors (Ranked by Importance)

**1. Entry Slope Quality (40% weight)**
- Target: >= 5.0% for high conviction (2.0x position)
- Minimum: >= 1.0% for entry
- Current vs Entry slope trend

**2. Entry Recency (30% weight)**
- Fresh signals more likely to continue
- Positions entered in last 30 days preferred
- Avoid chasing positions already up significantly

**3. Current Performance (30% weight)**
- Verify position is currently profitable
- Check if still trending (current slope positive)
- Confirm no exit signal triggered

### Three Categories of Opportunities

**Category 1: High-Conviction Recent Entries**
- 2.0x position multiplier (slope >= 5.0%)
- Entered within last 30 days
- Fresh momentum signals
- **Risk:** Higher volatility, shorter track record
- **Reward:** Strongest momentum, highest conviction

**Category 2: Long-Term Winners**
- Held 100+ days
- Still profitable
- Proven staying power
- **Risk:** May be extended, less room to run
- **Reward:** Demonstrated trend strength, lower volatility

**Category 3: High-Conviction Winners**
- 2.0x multiplier AND currently profitable
- Best of both worlds
- **Risk:** Moderate
- **Reward:** Strong momentum + proven profitability

---

## Position Sizing Rules (Conservative Allocation)

| Entry Slope | Position Size | Multiplier | Risk Level |
|-------------|---------------|------------|------------|
| >= 5.0% | $20,000 | 2.0x | High Conviction |
| >= 3.0% | $15,000 | 1.5x | Above Average |
| >= 2.0% | $12,000 | 1.2x | Average |
| >= 1.0% | $10,000 | 1.0x | Base |
| < 1.0% | $0 | Skip | Insufficient Quality |

**Important Notes:**
- These are PER ENTRY sizes (strategy uses pyramiding)
- Base position: $7,000 initial + $5,000 pyramid = $12,000 total
- Scale sizes proportionally if using different capital base

---

## Entry Rules

### Signal Requirements (ALL must be true)

**On 4-Day Bar Close:**
1. Heikin Ashi close > Heikin Ashi open (green HA candle)
2. HA close > Entry LinReg line (13-period, 0 lookahead)
3. Entry slope >= 1.0% (calculated from 5-period LinReg on HA close)

**Position Sizing:**
1. Calculate entry slope at time of entry
2. Determine multiplier based on slope threshold
3. Enter with calculated position size

### Pyramid Rules
- If already in position AND signal still valid
- Add pyramid position ($5,000 in backtest, scale accordingly)
- Only pyramid ONCE per position
- Mark position as "pyramided" to prevent additional entries

---

## Exit Rules

### Signal Requirements (ANY triggers exit)

**On 4-Day Bar Close:**
1. Heikin Ashi close < Heikin Ashi open (red HA candle) **OR**
2. HA close < Exit LinReg line (21-period, -3 lookahead)

**Exit Actions:**
- Close ENTIRE position (both initial and pyramid if present)
- Exit at close of 4-day bar
- No partial exits (strategy is binary: all-in or all-out)

### Important: No Manual Exits
- Strategy has no stop-loss
- Hold positions until exit signal triggers
- Do NOT exit based on:
  - Unrealized losses
  - Time in trade
  - Gut feeling
  - News events (unless affecting data quality)

---

## Risk Management

### Portfolio Heat Limits

**Maximum Concurrent Positions:**
- Backtest Average: 221 positions
- Backtest Maximum: 411 positions
- **Recommended Limit:** 250 positions (safety buffer)

**When to Reduce Exposure:**
- Approaching 250 concurrent positions
- Portfolio drawdown > -5%
- Significant market volatility event

### Drawdown Management

**Historical Drawdowns:**
- Maximum: -7.06% (over 9.5 years)
- Typical: -2% to -4%
- 2025 Max: -1.58%
- Recovery Time: 2-4 months typically

**Action Triggers:**
- At -5%: Review position quality, reduce new entries
- At -7%: Stop new entries, hold existing
- At -10%: Emergency review (not seen in backtest)

---

## Daily Workflow

### Market Open
1. Download overnight data for all symbols
2. Resample daily data to 4-day bars (with `origin='epoch'`)
3. Check for new 4-day bar closes
4. If no new bar close, no action needed

### When 4-Day Bar Closes

**For Each Symbol:**

1. **Calculate Current Indicators:**
   - Heikin Ashi OHLC
   - Entry LinReg (13-period, 0 lookahead)
   - Exit LinReg (21-period, -3 lookahead)
   - Entry slope (if entry signal present)

2. **Check Exit Signals First:**
   - For existing positions, check if exit triggered
   - Execute exits BEFORE entries

3. **Check Entry Signals:**
   - For non-positioned symbols, check for entry signal
   - Calculate entry slope
   - Apply position sizing
   - Execute entries

4. **Check Pyramid Signals:**
   - For existing non-pyramided positions
   - Check if entry signal still valid
   - Execute pyramid if conditions met

### End of Day
1. Reconcile all positions
2. Update portfolio tracking
3. Calculate unrealized P&L
4. Monitor concurrent position count
5. Update opportunity analysis weekly

---

## Monitoring & Maintenance

### Daily Monitoring
- [ ] Position count (target < 250)
- [ ] Portfolio P&L vs backtest expectations
- [ ] Any failed data feeds
- [ ] Execution quality (slippage tracking)

### Weekly Analysis
```bash
# Run opportunity analysis
python analyze_current_opportunities.py

# Generate fresh opportunity charts
python create_trading_opportunities_charts.py

# Review HTML viewer for best current opportunities
# Open: results/opportunity_charts/trading_opportunities.html
```

### Monthly Review
- Compare live performance to backtest metrics
- Analyze win rate by position size tier
- Review most/least profitable symbols
- Check for any systematic execution issues

### Quarterly Deep Dive
- Re-run full backtest with updated data
- Compare live vs backtest performance
- Update symbol universe if needed
- Review risk parameters

---

## Common Issues & Solutions

### Issue: Bars Not Synchronized
**Symptom:** Different symbols showing different bar close dates
**Solution:** Ensure `origin='epoch'` in ALL resample calls
**Verification:** Run `verify_bar_consistency.py`

### Issue: Too Many Concurrent Positions
**Symptom:** Approaching or exceeding 250 positions
**Solution:**
- Increase slope threshold temporarily (e.g., 1.5% minimum instead of 1.0%)
- Skip lower-conviction entries (1.0x positions)
- Wait for natural exits before new entries

### Issue: Performance Diverging from Backtest
**Symptom:** Live returns significantly different from expected
**Check:**
- Execution slippage (should be minimal on 4-day bars)
- Data quality (missing bars, bad prices)
- Signal calculation (entry/exit logic matches backtest)
- Position sizing (using correct multipliers)

### Issue: Missed Entries/Exits
**Symptom:** Signals not executing when expected
**Solution:**
- Set up automated alerts for bar closes
- Use end-of-day processing (not intraday)
- Double-check 4-day bar boundary calculation

---

## Performance Expectations

### Realistic Targets (Based on 9.5 Year Backtest)

**Annual Returns:**
- Average: 30.21%
- Good Year: 40-50%
- Great Year: 90%+ (like 2020)
- Bad Year: -2% to +10% (like 2022)

**Monthly Volatility:**
- Typical month: +2% to +3%
- Best months: January (+2.91%), November (+3.07%)
- Weakest month: October (+1.05%)
- All months historically positive on average

**Position Statistics:**
- Win Rate: ~46% (expect to lose more often than win)
- Profit Factor: ~2.0 (winners 2x size of losers)
- Average Hold: ~45 days per position

### Red Flags (When to Pause)

**Strategy May Be Breaking:**
- Win rate drops below 40% for 6+ months
- Profit factor drops below 1.5
- Maximum drawdown exceeds -10%
- Correlation between symbols increases sharply

---

## Capital Scaling Guide

The backtest uses $1M starting capital. To scale:

**For $500K Account:**
- Divide all position sizes by 2
- Example: 1.0x position = $5,000 instead of $10,000
- Maximum positions: ~110 instead of 220

**For $2M Account:**
- Multiply all position sizes by 2
- Example: 1.0x position = $20,000 instead of $10,000
- Maximum positions: ~440 instead of 220

**For $5M Account:**
- Multiply all position sizes by 5
- May need to consider liquidity constraints
- Test execution on small-cap symbols first

---

## Regulatory & Compliance

### Pattern Day Trading (PDT)
- **Not Applicable** - Strategy uses 4-day bars
- Positions typically held 40+ days
- Well above 3-trades-per-5-days threshold

### Tax Considerations
- Most positions held > 30 days (avoid wash sales)
- Some positions held > 1 year (long-term capital gains)
- Track entry/exit dates for tax reporting
- Consider tax-loss harvesting in December

### Record Keeping
- Maintain trade log with all entry/exit signals
- Document any manual interventions
- Keep backtest results for audit trail
- Archive daily bar data for reproducibility

---

## Advanced Topics

### Optimizing Entry Timing
- Current strategy: Enter at 4-day bar close
- Alternative: Enter next trading day at open (slight slippage)
- Backtest assumes perfect fill at bar close (optimistic)

### Handling Corporate Actions
- Stock splits: Adjust historical prices
- Dividends: Generally ignored (price-adjusted data)
- Mergers: Exit position before merger date
- Delistings: Should trigger exit signal naturally

### Market Regime Adaptation
- Bull markets: Full allocation, accept all 1.0x+ positions
- Bear markets: Increase threshold to 1.5x+ minimum
- High volatility: Reduce position sizes by 50%
- Low volatility: Consider increasing slightly

---

## Appendix: Key Script Reference

### Analysis Scripts
- `analyze_current_opportunities.py` - Identify best current positions
- `create_trading_opportunities_charts.py` - Generate opportunity charts
- `baseline_strategy.py` - Run full backtest
- `calculate_all_slopes.py` - Calculate entry slopes for all trades

### Verification Scripts
- `verify_bar_consistency.py` - Check bar synchronization
- `verify_trading_days_only.py` - Verify no weekend data

### Analysis Scripts (Generated Results)
- `open_pnl_and_allocation.py` - Allocation strategy comparison
- `conservative_portfolio_fast.py` - Portfolio timeline analysis
- `conservative_returns_analysis.py` - Annual/monthly returns
- `conservative_symbol_analysis.py` - Symbol performance rankings

### Output Locations
- Trade data: `results/*.csv`
- Charts: `results/*.png`
- Opportunity charts: `results/opportunity_charts/*.png`
- HTML viewers: `results/trade_charts/trade_viewer.html`, `results/opportunity_charts/trading_opportunities.html`

---

## Support & Resources

**Documentation:**
- Full Strategy Specs: `PRODUCTION_BASELINE_V3.0.md`
- Quick Start: `README_V3.0.md`
- Release Notes: `V3.0_RELEASE_SUMMARY.md`
- This Guide: `LIVE_TRADING_GUIDE.md`

**Analysis Tools:**
- Opportunity analysis with 6 factors
- Top 30 position charts (3 categories × 10 positions)
- Interactive HTML viewers for browsing

**Best Practices:**
- Start with paper trading for 1-2 months
- Begin with 25% of capital, scale up gradually
- Monitor closely for first quarter
- Keep detailed journal of any issues

---

**Version:** 3.0.0
**Status:** Production Ready
**Risk Level:** Moderate (backtested through multiple market cycles)
**Skill Level Required:** Intermediate (requires Python, data management, systematic execution)

---

**DISCLAIMER:** Past performance does not guarantee future results. This strategy involves substantial risk. Trade at your own risk. The -7% maximum drawdown is based on historical data and could be exceeded in future market conditions.
