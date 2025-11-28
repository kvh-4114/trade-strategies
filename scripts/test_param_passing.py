"""
Test if strategy parameters are actually being varied across runs
"""

import sys
import os

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# Import from the same directory
sys.path.insert(0, script_dir)
from run_phase_3_supertrend import run_supertrend_backtest, load_candle_data

# Load NVDA data
print("Loading NVDA data...")
candle_df = load_candle_data('NVDA', start_date='2020-01-01', end_date='2025-11-28')
print(f"Loaded {len(candle_df)} bars")

# Test Config 1: ATR 14, Multiplier 3.0, No exits
print("\n" + "="*80)
print("CONFIG 1: ATR Period 14, Multiplier 3.0, No Stop Loss, No Profit Target")
print("="*80)

params1 = {
    'atr_period': 14,
    'atr_multiplier': 3.0,
    'stop_loss_type': 'none',
    'stop_loss_value': None,
    'profit_target': None,
    'position_sizing': 'fixed',
    'position_size': 10000
}

result1 = run_supertrend_backtest(
    candle_df=candle_df,
    symbol='NVDA',
    strategy_params=params1,
    initial_capital=100000,
    commission=0.001
)

print(f"\nRESULT 1: Return={result1['total_return']*100:.2f}%, Trades={result1['total_trades']}")

# Test Config 2: ATR 30, Multiplier 6.0, No exits
print("\n" + "="*80)
print("CONFIG 2: ATR Period 30, Multiplier 6.0, No Stop Loss, No Profit Target")
print("="*80)

params2 = {
    'atr_period': 30,
    'atr_multiplier': 6.0,
    'stop_loss_type': 'none',
    'stop_loss_value': None,
    'profit_target': None,
    'position_sizing': 'fixed',
    'position_size': 10000
}

result2 = run_supertrend_backtest(
    candle_df=candle_df,
    symbol='NVDA',
    strategy_params=params2,
    initial_capital=100000,
    commission=0.001
)

print(f"\nRESULT 2: Return={result2['total_return']*100:.2f}%, Trades={result2['total_trades']}")

# Compare
print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"Config 1 (ATR 14, Mult 3.0): {result1['total_return']*100:.2f}% return, {result1['total_trades']} trades")
print(f"Config 2 (ATR 30, Mult 6.0): {result2['total_return']*100:.2f}% return, {result2['total_trades']} trades")

if result1['total_trades'] == result2['total_trades']:
    print("\n⚠️  WARNING: IDENTICAL trade counts! Parameters are NOT affecting Supertrend!")
else:
    print("\n✅ Different trade counts - parameters ARE working")
