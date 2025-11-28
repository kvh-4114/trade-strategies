"""
Manual Supertrend calculation to verify ATR and band width differences
"""

import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_3_optimization.candle_loader import CandleLoader
from agents.agent_5_infrastructure.database_manager import DatabaseManager


def calculate_atr(df, period):
    """Calculate ATR manually"""
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    # True Range
    tr = np.zeros(len(df))
    for i in range(1, len(df)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    # ATR (simple moving average of TR)
    atr = np.zeros(len(df))
    for i in range(period, len(df)):
        atr[i] = np.mean(tr[i-period+1:i+1])

    return atr


def calculate_supertrend(df, atr_period, multiplier):
    """Calculate Supertrend manually"""

    # Calculate ATR
    atr = calculate_atr(df, atr_period)

    # Calculate basic bands
    hl_avg = (df['high'].values + df['low'].values) / 2.0
    basic_upper = hl_avg + (multiplier * atr)
    basic_lower = hl_avg - (multiplier * atr)

    # Calculate final bands (with smoothing logic)
    final_upper = np.zeros(len(df))
    final_lower = np.zeros(len(df))
    direction = np.zeros(len(df))

    close = df['close'].values

    for i in range(atr_period, len(df)):
        if i == atr_period:
            # First valid bar after ATR warmup
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
        else:
            # Update final upper band
            if basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
                final_upper[i] = basic_upper[i]
            else:
                final_upper[i] = final_upper[i-1]

            # Update final lower band
            if basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
                final_lower[i] = basic_lower[i]
            else:
                final_lower[i] = final_lower[i-1]

        # Determine direction
        if i == atr_period:
            # First bar - start in uptrend if close above lower band
            if close[i] > final_lower[i]:
                direction[i] = 1
            else:
                direction[i] = -1
        else:
            prev_dir = direction[i-1]
            if prev_dir == -1:
                # Was in downtrend
                if close[i] > final_upper[i]:
                    direction[i] = 1  # Switch to uptrend
                else:
                    direction[i] = -1  # Stay in downtrend
            else:
                # Was in uptrend
                if close[i] < final_lower[i]:
                    direction[i] = -1  # Switch to downtrend
                else:
                    direction[i] = 1  # Stay in uptrend

    return atr, basic_upper, basic_lower, final_upper, final_lower, direction


def count_direction_changes(direction):
    """Count how many times direction changes"""
    changes = 0
    for i in range(1, len(direction)):
        if direction[i] != direction[i-1] and direction[i] != 0:
            changes += 1
    return changes


# Load NVDA data
print("Loading NVDA data...")
db = DatabaseManager()
candle_loader = CandleLoader(db)
df = candle_loader.load_candles('NVDA', candle_type='regular', aggregation_days=1)
print(f"Loaded {len(df)} bars\n")

# Test Config 1: ATR 14, Multiplier 3.0
print("="*80)
print("CONFIG 1: ATR Period 14, Multiplier 3.0")
print("="*80)

atr1, basic_upper1, basic_lower1, final_upper1, final_lower1, direction1 = calculate_supertrend(df, 14, 3.0)

# Print first 20 bars after warmup
start_idx = 14
end_idx = min(34, len(df))

print("\nFirst 20 bars after ATR warmup:")
print(f"{'Bar':<5} {'Close':<8} {'ATR':<8} {'Band Width':<12} {'Direction':<10}")
print("-" * 60)

for i in range(start_idx, end_idx):
    band_width = basic_upper1[i] - basic_lower1[i]
    dir_str = "UP" if direction1[i] == 1 else "DOWN"
    print(f"{i:<5} ${df['close'].iloc[i]:<7.2f} ${atr1[i]:<7.4f} ${band_width:<11.4f} {dir_str:<10}")

direction_changes1 = count_direction_changes(direction1)
print(f"\nTotal direction changes: {direction_changes1}")
print(f"Average band width: ${np.mean(basic_upper1[start_idx:] - basic_lower1[start_idx:]):.4f}")

# Test Config 2: ATR 30, Multiplier 6.0
print("\n" + "="*80)
print("CONFIG 2: ATR Period 30, Multiplier 6.0")
print("="*80)

atr2, basic_upper2, basic_lower2, final_upper2, final_lower2, direction2 = calculate_supertrend(df, 30, 6.0)

# Print first 20 bars after warmup
start_idx = 30
end_idx = min(50, len(df))

print("\nFirst 20 bars after ATR warmup:")
print(f"{'Bar':<5} {'Close':<8} {'ATR':<8} {'Band Width':<12} {'Direction':<10}")
print("-" * 60)

for i in range(start_idx, end_idx):
    band_width = basic_upper2[i] - basic_lower2[i]
    dir_str = "UP" if direction2[i] == 1 else "DOWN"
    print(f"{i:<5} ${df['close'].iloc[i]:<7.2f} ${atr2[i]:<7.4f} ${band_width:<11.4f} {dir_str:<10}")

direction_changes2 = count_direction_changes(direction2)
print(f"\nTotal direction changes: {direction_changes2}")
print(f"Average band width: ${np.mean(basic_upper2[start_idx:] - basic_lower2[start_idx:]):.4f}")

# Compare
print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"Config 1 (ATR 14, Mult 3.0): {direction_changes1} direction changes")
print(f"Config 2 (ATR 30, Mult 6.0): {direction_changes2} direction changes")
print(f"\nExpected: Config 2 should have MUCH fewer direction changes (wider bands)")

if abs(direction_changes1 - direction_changes2) < 50:
    print("⚠️  WARNING: Direction changes are too similar! Should be very different.")
else:
    print("✅ Direction changes are significantly different - parameters are working!")

# Print average ATR comparison
avg_atr1 = np.mean(atr1[14:])
avg_atr2 = np.mean(atr2[30:])
print(f"\nAverage ATR - Config 1: ${avg_atr1:.4f}")
print(f"Average ATR - Config 2: ${avg_atr2:.4f}")
print(f"Ratio: {avg_atr2/avg_atr1:.2f}x (should be ~2x due to longer period)")

# Print average band width comparison
avg_bw1 = np.mean(basic_upper1[14:] - basic_lower1[14:])
avg_bw2 = np.mean(basic_upper2[30:] - basic_lower2[30:])
print(f"\nAverage Band Width - Config 1: ${avg_bw1:.4f}")
print(f"Average Band Width - Config 2: ${avg_bw2:.4f}")
print(f"Ratio: {avg_bw2/avg_bw1:.2f}x (should be ~4x: 2x from period, 2x from multiplier)")
