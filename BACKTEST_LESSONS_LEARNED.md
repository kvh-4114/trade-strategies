# Backtesting Lessons Learned: Critical Bugs and Best Practices

**Date:** 2025-11-30
**Session:** Buy-and-Hold vs Supertrend Analysis
**Status:** 🔴 CRITICAL - Multiple bugs found that invalidated initial results

---

## Executive Summary

During analysis of Supertrend strategy vs buy-and-hold, we discovered **TWO CRITICAL BUGS** that completely invalidated initial results and led to incorrect conclusions. This document catalogs these bugs and establishes best practices to prevent similar issues in future backtests.

**Impact:** Initial analysis showed Supertrend captured 80% of buy-hold returns. After fixing bugs, actual capture was **1.2%** - a 67x difference!

---

## Bug #1: Buy-and-Hold Commission Calculation Error

### The Bug

**File:** `scripts/analyze_buy_hold_vs_supertrend.py` (BuyAndHold strategy)

**Broken Code:**
```python
def next(self):
    if not self.position:
        cash = self.broker.get_cash()
        size = int(cash / self.data.close[0])
        self.order = self.buy(size=size)  # ❌ FAILS - doesn't account for commission
```

**What Happened:**
- Tried to buy $100,000 worth of stock with $100,000 cash
- Commission of $100 (0.1%) required total $100,100
- Order rejected due to insufficient funds
- Strategy kept retrying every bar for **8+ years**
- Finally executed in 2024 when an order fit
- NVDA bought at $113 instead of $0.63!

**Impact:**
- NVDA buy-hold showed **57.6%** return
- Should have been **28,267%** return
- Off by **490x**!

**The Fix:**
```python
def next(self):
    if not self.position:
        cash = self.broker.get_cash()
        close = self.data.close[0]
        # Account for commission: total cost = size * close * (1 + commission_rate)
        size = int(cash / (close * 1.001))  # Reserve for 0.1% commission
        if size > 0:
            self.order = self.buy(size=size)
```

**Alternative Fix (if no commission):**
```python
cerebro.broker.setcommission(commission=0.0)  # Zero commission for testing
size = int(cash / close)  # Simple calculation
```

### How We Found It

1. Initial results seemed wrong (57.6% on NVDA's massive bull run?)
2. Created debug script to trace actual buy execution
3. Discovered buy happened on 2024-05-29 @ $113.05, not 2016-02-08 @ $0.63
4. Traced root cause to commission calculation

### Debugging Script

**File:** `scripts/debug_nvda_buyhold.py`

Key features:
- Logs every buy attempt
- Shows cash available, size calculated, cost, commission
- Tracks order rejections with status
- Compares "with commission adjustment" vs "without"

**Critical output:**
```
2016-02-08: BUY ORDER - Cash: $100,000.00, Close: $0.63, Size: 158,730 shares
2016-02-09: ORDER REJECTED - Status: Margin, Size: 158,730
...
(repeated for 8 years)
...
2024-05-29: BUY EXECUTED - Price: $113.05, Size: 877
```

---

## Bug #2: Fixed Position Sizing Instead of Portfolio Percentage

### The Bug

**File:** `agents/agent_2_strategy_core/supertrend_strategy.py`

**Broken Code:**
```python
params = (
    ('position_size', 10000),  # ❌ FIXED $10k regardless of portfolio size
)

def _calculate_position_size(self):
    price = self.data.close[0]
    if self.params.position_sizing == 'fixed':
        return int(self.params.position_size / price)
```

**What Happened:**
- Strategy always buys $10,000 worth of stock
- Portfolio grows from $100k → $142k → $211k
- But still only investing $10k per trade
- **90-95% of capital sits idle in cash earning ZERO**

**Impact on NVDA Trade #12:**
- Entry: $14.40 (portfolio = $142,419)
- Exit: $112.90 (620% gain!)
- Position size: **$10,000** (only 7% of portfolio)
- Wasted capital: **$132,419** (93% idle)

**If full portfolio used:**
- Would have made: **$1,025,416**
- Actually made: **$204,419**
- **Left $821k on table from ONE TRADE!**

**Capital Utilization Degradation:**
- Start: 10% ($10k / $100k)
- Mid-run: 7% ($10k / $142k)
- End: 5% ($10k / $211k)

**The Fix:**
```python
def _calculate_position_size(self):
    """Use percentage of portfolio instead of fixed dollars"""
    cash = self.broker.get_cash()
    price = self.data.close[0]

    # Use 95% of cash (keep 5% buffer for commissions/slippage)
    position_value = cash * 0.95

    if price > 0:
        return int(position_value / price)
    return 0
```

### How We Found It

1. User questioned why we're "leaving so much on the table"
2. Reviewed Supertrend code step-by-step for bugs
3. Found no commission issues (all trades executed successfully)
4. Noticed position size stayed at $10k while portfolio grew
5. Created debug script showing capital utilization per trade
6. Calculated impact: $821k left on table from one 620% winner

### Debugging Script

**File:** `scripts/debug_supertrend_nvda.py`

Key features:
- Shows cash available vs position size for each trade
- Calculates capital utilization %
- Displays wasted capital
- Logs entry/exit with profit %

**Critical output:**
```
2022-12-28: BUY SIGNAL - Cash: $142,418.90, Close: $14.04
  NO COMM ADJ: size=712, cost=$9,996.48, total=$10,006.48
  Capital utilization: 7.0%
  Wasted: $132,418.90 (93.0%)

2024-07-30: SELL SIGNAL - Position: 712 shares, Value: $73,855.76, Profit: 620.3%
```

---

## Bug #3 Investigation: Commission Impact (FALSE ALARM)

### The Hypothesis

After finding bugs #1 and #2, we suspected commissions might also be significantly impacting returns.

### The Test

Re-ran full analysis with:
- Commission = 0.0 (zero)
- Position size = $10,000 (fixed)
- All 4 symbols (NVDA, AMD, TSLA, AAPL)

### The Results

**Return comparison:**

| Symbol | With 0.1% Comm | With 0% Comm | Difference |
|--------|----------------|--------------|------------|
| **NVDA B&H** | 28,267% | 28,295% | +0.1% |
| **NVDA ST** | 114.5% | 114.9% | +0.3% |
| **AMD B&H** | 10,450% | 10,460% | +0.1% |
| **AMD ST** | 60.1% | 60.5% | +0.7% |
| **TSLA B&H** | 3,862% | 3,866% | +0.1% |
| **TSLA ST** | 54.6% | 55.4% | +1.5% |
| **AAPL B&H** | 1,043% | 1,044% | +0.1% |
| **AAPL ST** | 25.7% | 27.1% | +5.4% |

**Average capture rate:**
- With commission: 1.2%
- Without commission: 1.3%
- Difference: **+0.1%** (negligible)

### The Conclusion

**Commissions are NOT a significant factor** in the poor Supertrend performance.

The 0.1% commission only reduces returns by ~1% on average. The real problems are:
1. Fixed position sizing (90-95% capital idle)
2. Stop losses exiting on normal volatility
3. Profit targets cutting winners short
4. Excessive trade frequency

---

## Best Practices for Future Backtests

### 1. Always Debug Position Execution

**DO:**
- Create a debug version of your strategy that logs:
  - Every entry signal with cash available
  - Calculated position size and cost
  - Order execution status (or rejection reason)
  - Portfolio value after execution
  - Exit signals with profit/loss %

**Example:**
```python
def notify_order(self, order):
    if order.status in [order.Completed]:
        self.log(f'BUY EXECUTED: Price=${order.executed.price:.2f}, '
                f'Size={order.executed.size:,}, Cost=${order.executed.value:,.2f}')
        self.log(f'Portfolio: ${self.broker.getvalue():,.2f}')
    elif order.status in [order.Rejected, order.Margin]:
        self.log(f'❌ ORDER REJECTED: {order.getstatusname()}')
```

**DON'T:**
- Assume orders execute as expected
- Trust final returns without checking trade-by-trade execution
- Skip logging in production backtests

### 2. Verify First Trade Execution

**DO:**
- Manually verify the first trade executed at the expected time/price
- Check that position size matches your calculation
- Confirm sufficient cash was available
- Validate commission was applied correctly

**Example check:**
```python
# After backtest
print(f"First trade date: {first_trade_date}")
print(f"Expected: {data_start_date}")
print(f"Entry price: ${first_entry_price:.2f}")
print(f"Expected: ${first_close_price:.2f}")

# Should match!
```

**DON'T:**
- Only check final portfolio value
- Assume the strategy started trading immediately
- Skip validation of early trades

### 3. Account for Commissions in Position Sizing

**DO:**
```python
# Option 1: Adjust size calculation
cash = self.broker.get_cash()
price = self.data.close[0]
commission_rate = 0.001  # 0.1%
size = int(cash / (price * (1 + commission_rate)))

# Option 2: Use zero commission for initial testing
cerebro.broker.setcommission(commission=0.0)
size = int(cash / price)

# Option 3: Leave buffer
size = int((cash * 0.99) / price)  # Use 99% of cash
```

**DON'T:**
```python
# ❌ This can fail due to commission
size = int(cash / price)
cerebro.broker.setcommission(commission=0.001)
```

### 4. Use Portfolio-Percentage Position Sizing

**DO:**
```python
def _calculate_position_size(self):
    cash = self.broker.get_cash()
    price = self.data.close[0]

    # Use 95% of available cash
    position_pct = 0.95
    position_value = cash * position_pct

    if price > 0:
        return int(position_value / price)
    return 0
```

**Benefits:**
- Scales with portfolio growth
- Always maximizes capital utilization
- Compounds gains effectively

**DON'T:**
```python
# ❌ Fixed dollar amount doesn't scale
position_size = 10000  # Always $10k regardless of portfolio
```

**Exception:** Fixed position sizing is acceptable if:
- Testing multiple uncorrelated strategies in parallel
- Deliberately sizing conservatively for risk management
- Comparing strategies on equal footing (same $ per trade)

### 5. Compare Against Realistic Baseline

**DO:**
- Always run buy-and-hold on the same data
- Use same commission settings
- Verify buy-hold executes on first bar
- Calculate theoretical max (first price → last price)

**Example:**
```python
# Theoretical max
first_close = df.iloc[0]['close']
last_close = df.iloc[-1]['close']
theoretical_return = ((last_close - first_close) / first_close) * 100

# Buy-hold backtest
bh_return = ((bh_end_value - bh_start_value) / bh_start_value) * 100

# Should be very close!
print(f"Theoretical: {theoretical_return:.2f}%")
print(f"Buy-hold: {bh_return:.2f}%")
print(f"Difference: {abs(theoretical_return - bh_return):.2f}%")

# If difference > 0.5%, investigate!
```

**DON'T:**
- Compare against theoretical max without testing it
- Assume buy-hold is trivial and doesn't need testing
- Use different commission settings for baseline vs strategy

### 6. Test Commission Impact Independently

**DO:**
- Run backtests with both 0% and realistic commissions
- Calculate commission cost as % of total return
- Verify it matches expectations

**Example:**
```python
# Run with commission
returns_with_comm = run_backtest(commission=0.001)

# Run without commission
returns_no_comm = run_backtest(commission=0.0)

# Calculate impact
comm_impact = returns_no_comm - returns_with_comm
comm_pct = (comm_impact / returns_no_comm) * 100

print(f"Commission impact: {comm_pct:.1f}% of returns")

# For 40 trades at 0.1% each side:
# Expected: ~8% impact (40 * 2 * 0.1%)
```

**DON'T:**
- Assume commission impact without testing
- Use unrealistic commission rates
- Ignore commission in position sizing

### 7. Monitor Capital Utilization

**DO:**
- Track % of portfolio invested on each trade
- Log cash balance alongside position value
- Alert if utilization drops below threshold

**Example:**
```python
def next(self):
    portfolio_value = self.broker.getvalue()
    cash = self.broker.get_cash()

    if self.position:
        position_value = self.position.size * self.data.close[0]
        utilization = (position_value / portfolio_value) * 100

        if utilization < 50:
            self.log(f'⚠️  Low utilization: {utilization:.1f}%')
```

**Target utilization:**
- Aggressive: 90-95%
- Moderate: 70-80%
- Conservative: 50-60%

**DON'T:**
- Let capital sit idle unintentionally
- Assume fixed position sizes scale properly
- Ignore declining utilization over time

### 8. Create Reusable Debug Scripts

**DO:**
- Build a library of debug scripts for common scenarios:
  - `debug_first_trade.py` - Verify first execution
  - `debug_position_sizing.py` - Check size calculations
  - `debug_commission_impact.py` - Test with/without commissions
  - `debug_capital_utilization.py` - Track cash vs invested
  - `debug_order_rejections.py` - Find failed orders

**Template:**
```python
"""
Debug script: [What it checks]
Usage: python debug_xxx.py SYMBOL CSV_FILE
"""
import backtrader as bt

class DebugStrategy(bt.Strategy):
    def log(self, txt):
        print(f'{self.data.datetime.date(0)}: {txt}')

    def notify_order(self, order):
        # Log all order events
        pass

    def next(self):
        # Log relevant state
        pass

# Run and analyze
cerebro = bt.Cerebro()
# ... setup ...
results = cerebro.run()

# Print summary
print(f"\nSUMMARY:")
print(f"Expected: [what should happen]")
print(f"Actual: [what happened]")
print(f"Match: [✓ or ✗]")
```

**DON'T:**
- Debug inside production backtest code
- Delete debug scripts after use
- Skip documenting what each script checks

### 9. Document Assumptions and Constraints

**DO:**
- Document in strategy file:
  - Position sizing method and why
  - Commission assumptions
  - Minimum trade size constraints
  - Cash buffer requirements

**Example:**
```python
"""
SupertrendStrategy - Trend-following with ATR bands

POSITION SIZING:
  - Method: 95% of available cash
  - Rationale: Maximize capital utilization while leaving buffer
  - Constraint: Minimum 1 share (no fractional shares)

COMMISSIONS:
  - Assumed: 0.1% per trade ($10 minimum)
  - Impact: ~8% of returns for 40 round-trip trades

CASH MANAGEMENT:
  - Buffer: 5% uninvested (for commissions, slippage)
  - Minimum cash: Max($500, 5% of portfolio)
"""
```

**DON'T:**
- Leave assumptions implicit
- Use hardcoded values without explanation
- Forget to update docs when code changes

### 10. Validate Results Against Intuition

**DO:**
- Sanity check every result:
  - "Does this make sense?"
  - "Is this too good to be true?"
  - "Why would this underperform so badly?"

- If results seem wrong, ASSUME THEY ARE until proven otherwise
- Investigate aggressively

**Red flags:**
- Buy-hold underperforms theoretical max by >1%
- Strategy captures <10% of buy-hold on strong trend
- Commission impact >2% per trade
- Drawdown >100%
- Sharpe ratio >3.0 (suspicious)
- Win rate >90% (likely overfit)

**DON'T:**
- Accept results that seem "off"
- Assume bugs only exist in complex code
- Skip validation because "it's just a backtest"

---

## Checklist for New Backtests

Before trusting any backtest results, verify:

- [ ] First trade executed on expected date at expected price
- [ ] Buy-and-hold baseline matches theoretical max (<0.5% diff)
- [ ] Position sizing accounts for commissions OR commission = 0
- [ ] Capital utilization >80% throughout (unless intentionally conservative)
- [ ] No order rejections in logs (check for "Margin" or "Rejected")
- [ ] Commission impact matches expectation (trades × rate × 2)
- [ ] Results pass sanity check (not too good, not inexplicably bad)
- [ ] Debug script created and run for key scenarios
- [ ] Assumptions documented in code
- [ ] Results make intuitive sense given market conditions

**Time investment:** 30-60 minutes of validation can save hours of chasing false conclusions!

---

## Summary: What We Learned

### Bug Impact

| Bug | Initial Result | Actual Result | Error Factor |
|-----|----------------|---------------|--------------|
| **Buy-hold commission** | 57.6% NVDA | 28,267% NVDA | 490x |
| **Fixed position sizing** | $204k final | $1.0M possible | 5x |
| **Combined effect** | 80% capture | 1.2% capture | 67x |

### Key Takeaways

1. **Commission bugs are subtle** - Order rejection happens silently, strategy retries for years
2. **Position sizing is critical** - 10x returns don't matter if only 10% of capital is invested
3. **Validate early trades** - Most bugs reveal themselves in the first few executions
4. **Trust nothing** - If results seem wrong, they probably are
5. **Debug systematically** - Build reusable scripts for common validations
6. **Document everything** - Future you will thank present you

### Prevention

- Use checklist on every backtest
- Build debug script library
- Validate against realistic baseline
- Question unintuitive results
- Test commission impact independently

---

**Never forget:** A backtest is only as good as the bugs it doesn't have.

**Created:** 2025-11-30
**Last Updated:** 2025-11-30
**Status:** Living document - update with new learnings
