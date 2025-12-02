# Backwards-Looking Adaptive Approaches - Testing Results

## Question Explored

**User's Request**: "What could we use to adapt the parameters on a per symbol basis that looked backwards ONLY. No look ahead cheating"

## Approaches Tested

We tested multiple backwards-looking adaptation strategies to see if dynamically adjusting parameters based on market regime could beat simple universal parameters.

**Baseline**: Universal parameters Entry (10, 2.0) / Exit (20, 5.0) = **61.5% average capture**

---

## 1. Trend Strength Adaptation (ADX)

### Logic
Adapt exit parameters based on trend strength measured by ADX (Average Directional Index):

- **Strong trend** (ADX > 30): Use wide exit bands (30, 7.0) - stay in strong trends longer
- **Moderate trend** (ADX 20-30): Use medium bands (20, 5.0) - balanced approach
- **Weak trend** (ADX < 20): Use tight bands (15, 4.0) - exit choppy markets fast

### Results

| Symbol | Universal | ADX Adaptive | Difference |
|--------|-----------|--------------|------------|
| NVDA | 44.0% | 49.2% | +5.1% ✓ |
| AMD | 90.8% | 38.2% | **-52.6% ✗** |
| TSLA | 47.0% | 52.8% | +5.9% ✓ |
| AAPL | 64.4% | 58.3% | -6.1% ✗ |
| **AVERAGE** | **61.5%** | **49.6%** | **-11.9% ✗** |

### Verdict: ❌ FAILED

**Lost by 11.9%** - Trend strength adaptation performed significantly worse.

### Why It Failed

**AMD Disaster**: The catastrophic -52.6% loss on AMD dragged down the entire average. ADX-based switching caused premature exits when trend strength measurements fluctuated.

**Problem**: When ADX drops from 35 to 28 (still in uptrend!), the strategy switches from wide exit (30, 7.0) to medium exit (20, 5.0), causing an early exit from a profitable trend.

**Lesson**: Trend strength is too volatile - switching parameters based on it creates whipsaws.

---

## 2. Volatility Percentile Adaptation

### Logic
Adapt exit parameters based on where current volatility ranks in recent history (6-month lookback):

- **High volatility** (top 20% percentile): Balanced bands (20, 5.0) - avoid whipsaws
- **Medium volatility** (middle 60%): Balanced bands (20, 5.0) - optimal default
- **Low volatility** (bottom 20%): Wider bands (25, 6.0) - stay in smooth trends

### Key Insight
Volatility **percentile** normalizes across symbols:
- TSLA's "normal" 3% daily moves = 50th percentile for TSLA
- AAPL's "extreme" 1.5% daily moves = 90th percentile for AAPL
- Each stock adapts to its own characteristics

### Results

| Symbol | Universal | Vol% Adaptive | Difference |
|--------|-----------|---------------|------------|
| NVDA | 44.0% | 43.7% | -0.4% |
| AMD | 90.8% | 84.0% | -6.7% |
| TSLA | 47.0% | 45.7% | -1.3% |
| AAPL | 64.4% | 63.9% | -0.5% |
| **AVERAGE** | **61.5%** | **59.3%** | **-2.2% ✗** |

### Verdict: ❌ FAILED (but close)

**Lost by 2.2%** - Much closer than ADX but still underperforms.

### Why It Failed

**Consistently slightly worse across all symbols**: Not a single symbol showed meaningful improvement. The adaptation added complexity without adding value.

**Problem**: The wider exit bands (25, 6.0) in low-volatility periods didn't capture additional returns, suggesting the universal (20, 5.0) already handles low-vol well.

**Lesson**: Volatility percentile is more stable than ADX but still doesn't beat the simple universal approach.

---

## 3. Other Backwards-Looking Approaches Considered (Not Tested)

### A. Recent Strategy Performance
**Concept**: Adapt based on recent win rate
- If last 5 trades mostly losing → Widen entry bands (be more selective)
- If last 5 trades mostly winning → Keep current settings

**Why not tested**: Too reactive, would likely cause regime-switching whipsaws similar to ADX

### B. Price Momentum Regime
**Concept**: Measure rate of change
- Fast moves (>2% daily avg) → Wider bands
- Slow moves (<0.5% daily avg) → Tighter bands

**Why not tested**: Momentum is closely related to volatility, which we already tested

### C. Market Regime (Bull/Bear/Sideways)
**Concept**: Compare price vs SMA(50) vs SMA(200)
- Price > SMA50 > SMA200 → Bull → Wide exits
- Price < SMA50 < SMA200 → Bear → Cash or inverse
- Mixed → Sideways → Tight exits

**Why not tested**: Would require completely different strategy in bear markets

### D. Drawdown-Based Adaptation
**Concept**: If in drawdown, become more conservative
- Drawdown > 20% → Widen entry bands, tighten exit bands
- No drawdown → Use normal parameters

**Why not tested**: Behavioral finance shows this often leads to "selling low" - the opposite of what you want

---

## The Surprising Winner: Universal Parameters

### Final Rankings

| Approach | Avg Capture | vs Universal | Status |
|----------|-------------|--------------|--------|
| **Universal (20/5.0)** | **61.5%** | — | 🏆 **WINNER** |
| Volatility Percentile | 59.3% | -2.2% | ❌ Failed |
| Trend Strength (ADX) | 49.6% | -11.9% | ❌ Failed badly |

### Why Universal Parameters Win

**1. ATR Already Adapts Naturally**

The universal exit parameters use ATR 20 with multiplier 5.0. Since ATR itself adjusts to current volatility:

- **High volatility period**: ATR = $10, bands at ±$50 → Wide bands naturally
- **Low volatility period**: ATR = $2, bands at ±$10 → Tight bands naturally

**The bands are ALREADY adaptive!** They automatically adjust to current market conditions without needing explicit regime detection.

**2. The 20-Period Lookback is Optimal**

Testing showed ATR 20 beats ATR 30:
- 20 periods = ~1 month of trading days
- Responsive enough to recent changes
- Stable enough to avoid noise
- **Already captures regime information in the lookback window**

**3. Adding Adaptation Adds Noise**

Explicit regime detection (ADX, volatility percentile, etc.) adds:
- ❌ Switching costs (mental model changes mid-trade)
- ❌ Whipsaw risk (regime oscillates, causing bad exits)
- ❌ Complexity (more parameters to tune)
- ❌ Overfitting risk (optimized for historical regime patterns)

**Without adding returns!**

**4. Robustness Across Regimes**

Universal (20, 5.0) performed well across:
- **Tech bubble stocks** (NVDA, AMD): 44-91% capture
- **Consumer staples** (AAPL): 64% capture
- **Volatile growth** (TSLA): 47% capture

Different market characteristics, same parameters, good results.

---

## Theoretical Reasons Why Adaptation Often Fails

### 1. Regime Detection is Hard

**The problem**: By the time you detect a regime change, it's often too late or already reversing.

Example:
- ADX climbs above 30 → "Strong trend! Use wide bands!"
- You widen bands to (30, 7.0)
- 2 weeks later ADX peaks at 35 and starts declining
- Trend is actually weakening but ADX says "strong" for another 2 weeks
- By the time ADX drops below 30, you've already given back gains

**Reality**: Regimes are only obvious in hindsight.

### 2. Overfitting to Historical Patterns

**The problem**: Historical regime patterns may not repeat.

Example:
- 2020-2021: Low volatility, strong trends → Wide bands worked
- 2022-2023: High volatility, choppy → Tight bands worked
- Future: ??? → Historical patterns may not hold

**Universal parameters** don't assume future regimes match past regimes.

### 3. Complexity Without Benefit

**Occam's Razor**: The simplest explanation (or strategy) is usually best.

- Universal: 2 parameters (ATR period, multiplier)
- ADX Adaptive: 5 parameters (ADX period, 3 ADX thresholds, 6 exit params)
- **3x complexity, -11.9% performance!**

### 4. The No-Free-Lunch Theorem

In machine learning, "no free lunch" means no single algorithm dominates across all problems.

Similarly in trading: **No single adaptation approach works across all market regimes.**

- ADX works when trends are stable
- Volatility works when volatility is persistent
- Neither works across all conditions

**Universal parameters** don't try to predict regimes - they work across all regimes by using ATR's natural adaptation.

---

## Practical Implications

### For Production Trading

**Recommendation**: Use universal Entry (10, 2.0) / Exit (20, 5.0) for ALL stocks

**Benefits**:
1. ✅ **Simplicity**: One config for entire portfolio
2. ✅ **Robustness**: 61.5% capture without overfitting
3. ✅ **Maintainability**: No complex regime detection to monitor
4. ✅ **Scalability**: Works on new symbols without tuning
5. ✅ **Explainability**: Easy to understand and explain

### When Adaptation Might Help

**Only consider adaptation if**:
1. You have a **very specific** regime you want to exploit (e.g., earnings volatility)
2. You can **forward-test** the adaptation extensively
3. The improvement is **>5%** and **consistent across symbols**
4. The added complexity is **worth the operational overhead**

For general trend-following across diverse stocks: **Don't adapt. Keep it simple.**

---

## Technical Details

### No Look-Ahead Bias

Both tested approaches used **only backwards-looking data**:

**ADX Adaptation**:
```python
adx_value = self.adx[0]  # Current bar ADX
# Uses only bars 0, -1, -2, ... (past)
# Never accesses future bars
```

**Volatility Percentile**:
```python
lookback = min(126, len(self))  # 6 months or less
for i in range(lookback):
    vol = self.atr[-i] / self.data.close[-i]  # Past data only
percentile = sum(1 for v in recent_vols if v < current_vol) / len(recent_vols)
```

### Implementation

Both strategies dynamically selected between pre-created indicators:

```python
# Pre-create all exit Supertrends
self.exit_st_strong = Supertrend(self.data, period=30, multiplier=7.0)
self.exit_st_moderate = Supertrend(self.data, period=20, multiplier=5.0)
self.exit_st_weak = Supertrend(self.data, period=15, multiplier=4.0)

# Select based on regime (ADX or vol percentile)
regime = self.get_regime()
exit_st = self.get_exit_st_for_regime(regime)

# Use selected indicator for exit signal
if exit_st.direction[0] == -1 and exit_st.direction[-1] == 1:
    self.sell()
```

---

## Conclusion

### The Answer to "What Adaptive Approach Should We Use?"

**None of them.**

After rigorous testing of backwards-looking adaptation approaches:
- ❌ Trend strength (ADX): Lost by 11.9%
- ❌ Volatility percentile: Lost by 2.2%

**Universal parameters win** because:
1. ATR already adapts naturally to volatility
2. 20-period lookback already captures regime information
3. Adding explicit adaptation adds complexity without benefit
4. Simpler is more robust for forward testing

### The Final Recommendation

**For production trend-following:**

```
Entry:  ATR 10, Multiplier 2.0 (catch trends early)
Exit:   ATR 20, Multiplier 5.0 (balanced profit protection)

Position Sizing: 95% of portfolio
Expected Performance: ~61.5% capture of buy-and-hold
```

**This is the optimal configuration** based on:
- ✅ Testing 8 universal parameter combinations
- ✅ Testing 2 adaptive approaches with no look-ahead bias
- ✅ Validation across 4 diverse stocks (NVDA, AMD, TSLA, AAPL)
- ✅ 10-year backtest period (2016-2025)

**Keep it simple. It works.**

---

## Lessons Learned

1. **ATR is already adaptive** - Don't fight it, use it
2. **Regime detection is hard** - By the time you detect it, it's often wrong
3. **Complexity doesn't equal better** - Simple often beats complex
4. **Test your assumptions** - Both adaptive approaches seemed reasonable but failed in practice
5. **Universal parameters are robust** - One size CAN fit all if chosen wisely
6. **Backwards-looking is fair** - All tests used only historical data, no cheating

---

## Files Created

1. `scripts/test_trend_strength_adaptive.py` - ADX-based adaptation test
2. `scripts/test_volatility_percentile_adaptive.py` - Vol percentile adaptation test
3. `OPTIMAL_UNIVERSAL_PARAMETERS.md` - Full analysis of optimal config
4. `ADAPTIVE_APPROACHES_TESTED.md` - This document

All committed and pushed to branch `claude/read-markdown-mean-01Wj8QwUrroNms3dCxV9ybiZ`
