# Complementary Trading Strategies

## Overview

The LinReg Baseline v3.0 is a **momentum/trend-following** strategy that goes long when price crosses above a linear regression line. To build a robust portfolio, we should consider strategies that:

1. **Complement** momentum (perform well when momentum doesn't)
2. **Diversify** across different market regimes
3. **Reduce correlation** between strategy returns

---

## Strategy Categories

### 1. Mean Reversion Strategies (Counter-Trend)

**Rationale:** When momentum strategies struggle (choppy/sideways markets), mean reversion tends to outperform.

#### A. Bollinger Band Mean Reversion
```
Entry: Price closes below lower Bollinger Band (2 std dev)
Exit: Price returns to middle band (SMA)
Filter: RSI < 30 for confirmation
Timeframe: Daily or 4-day bars
```

**Expected Characteristics:**
- Win Rate: 55-65% (higher than momentum)
- Profit Factor: 1.5-1.8
- Avg Hold: 5-15 days (shorter than LinReg)
- Correlation to LinReg: Low/Negative

#### B. RSI Oversold Bounce
```
Entry: RSI(14) < 25 AND price > 200 SMA (uptrend filter)
Exit: RSI > 50 OR 10-day time limit
Position Size: Fixed $10,000
```

---

### 2. Momentum Variants (Trend Enhancement)

#### A. Dual Momentum (Absolute + Relative)

**Concept:** Combine absolute momentum (is the asset trending up?) with relative momentum (is it outperforming peers?).

```
Entry Criteria:
  1. Absolute: 12-month return > 0 (or > T-bill rate)
  2. Relative: Asset in top 20% of universe by 12-month return

Exit:
  - Absolute momentum turns negative
  - OR drops out of top 30% relative

Rebalance: Monthly
```

**Expected Performance:**
- Annualized Return: 12-18%
- Max Drawdown: -15 to -25%
- Lower turnover than LinReg baseline

#### B. Breakout Momentum
```
Entry: Price breaks above 52-week high
Exit: Price drops below 20-day SMA
Filter: Volume > 1.5x average on breakout day
```

#### C. Sector Momentum Rotation
```
Universe: 11 sector ETFs (XLK, XLV, XLF, etc.)
Signal: Rank sectors by 3-month return
Action: Hold top 3 sectors, rotate monthly
```

---

### 3. Volatility-Based Strategies

#### A. Low Volatility Anomaly
```
Universe: Same 268 stocks as LinReg
Signal: Rank by 60-day realized volatility
Action: Hold lowest 20% volatility stocks
Rebalance: Monthly
```

**Rationale:** Low volatility stocks historically outperform on risk-adjusted basis.

#### B. Volatility Regime Switching
```
Regime Detection: VIX level or 20-day ATR percentile
  - Low Vol (VIX < 15): Full momentum exposure
  - Medium Vol (VIX 15-25): 50% momentum, 50% cash
  - High Vol (VIX > 25): 100% cash or short
```

---

### 4. Short-Side Strategies (Hedge)

#### A. LinReg Short (Mirror Strategy)
```
Entry: LinReg goes RED (lr_close < lr_open) AND price < lr_low
Exit: LinReg goes GREEN
Position: Short $7,000 per signal
```

**Use Case:** Hedge long exposure during downtrends.

#### B. Weak Momentum Shorts
```
Entry: 6-month return in bottom 10% of universe
Exit: Returns to bottom 30% OR 30-day limit
Filter: Only during market downtrends (SPY < 200 SMA)
```

---

## Recommended Portfolio Allocation

### Conservative Portfolio
| Strategy | Allocation | Expected Return | Max DD |
|----------|------------|-----------------|--------|
| LinReg Baseline (Long) | 60% | 25-30% | -10% |
| Mean Reversion (RSI) | 20% | 12-15% | -8% |
| Cash/T-Bills | 20% | 4-5% | 0% |
| **Portfolio** | **100%** | **~20%** | **-8%** |

### Aggressive Portfolio
| Strategy | Allocation | Expected Return | Max DD |
|----------|------------|-----------------|--------|
| LinReg Baseline (Long) | 50% | 25-30% | -10% |
| Dual Momentum | 25% | 15-18% | -20% |
| Breakout Momentum | 15% | 20-25% | -15% |
| LinReg Short (Hedge) | 10% | 5-10% | -15% |
| **Portfolio** | **100%** | **~22%** | **-12%** |

---

## Implementation Priority

### Phase 1: Mean Reversion (Complement LinReg)
1. Implement Bollinger Band mean reversion
2. Backtest on same 268 symbols
3. Calculate correlation to LinReg returns
4. Target: Negative correlation during LinReg drawdowns

### Phase 2: Enhanced Momentum
1. Implement Dual Momentum (monthly rotation)
2. Add sector rotation overlay
3. Compare risk-adjusted returns

### Phase 3: Volatility & Hedging
1. Add volatility regime detection
2. Implement LinReg Short strategy
3. Build portfolio-level risk management

---

## Key Metrics to Track

For each strategy, calculate:
- **Correlation to LinReg**: Target < 0.3
- **Sharpe Ratio**: Target > 1.0
- **Calmar Ratio**: Return / Max DD > 2.0
- **Win Rate**: Varies by strategy type
- **Avg Hold Period**: For position sizing

---

## Data Requirements

All strategies can use the existing database:
- `stock_data`: 268 symbols, 2016-2025
- `candles`: Pre-generated for multiple timeframes

Additional data needed:
- VIX daily closes (for regime detection)
- Sector ETF prices (for rotation)
- T-Bill rates (for absolute momentum threshold)

---

## Next Steps

1. **Choose strategy to implement next**
2. Create validation script (like LinReg validation)
3. Calculate correlation matrix with LinReg
4. Optimize parameters using walk-forward
5. Combine into portfolio-level backtest
