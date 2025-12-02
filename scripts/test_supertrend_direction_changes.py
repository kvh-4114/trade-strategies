"""
Test that Supertrend direction changes are happening
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from agents.agent_2_strategy_core.supertrend import Supertrend
import pandas as pd
import numpy as np

# Create data with trend changes (uptrend, then downtrend, then uptrend)
np.random.seed(42)
dates = pd.date_range('2020-01-01', periods=100, freq='D')

# Simulate price movement with trend changes
prices = []
base = 100
for i in range(100):
    if i < 30:
        # Uptrend
        base += np.random.uniform(0.5, 1.5)
    elif i < 60:
        # Downtrend
        base -= np.random.uniform(0.5, 1.5)
    else:
        # Uptrend again
        base += np.random.uniform(0.5, 1.5)

    prices.append(base)

df = pd.DataFrame({
    'date': dates,
    'open': prices,
    'high': [p * 1.01 for p in prices],
    'low': [p * 0.99 for p in prices],
    'close': prices,
    'volume': [1000000] * 100
})

class PandasData(bt.feeds.PandasData):
    params = (
        ('datetime', 'date'),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )

class TestStrategy(bt.Strategy):
    def __init__(self):
        self.st = Supertrend(self.data, period=14, multiplier=3.0)
        self.direction_changes = 0
        self.prev_direction = None

    def next(self):
        current_direction = self.st.direction[0]

        if self.prev_direction is not None and current_direction != self.prev_direction:
            self.direction_changes += 1
            dir_str = "UP" if current_direction == 1 else "DOWN"
            prev_str = "UP" if self.prev_direction == 1 else "DOWN"
            print(f"Bar {len(self):3d}: Direction change {prev_str} -> {dir_str} (close=${self.data.close[0]:.2f})")

        self.prev_direction = current_direction

cerebro = bt.Cerebro()
data = PandasData(dataname=df)
cerebro.adddata(data)
cerebro.addstrategy(TestStrategy)

print("="*80)
print("Testing Supertrend Direction Changes")
print("="*80)
results = cerebro.run()
strat = results[0]

print("\n" + "="*80)
print(f"Total direction changes: {strat.direction_changes}")
print("="*80)

if strat.direction_changes > 0:
    print("✅ SUCCESS: Supertrend is detecting direction changes!")
else:
    print("❌ FAIL: No direction changes detected")
