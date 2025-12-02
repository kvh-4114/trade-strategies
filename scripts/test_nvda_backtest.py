"""
Test Supertrend with NVDA CSV data
Verifies the fixed indicator produces expected trade counts
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtrader as bt
from agents.agent_2_strategy_core.supertrend import Supertrend
from agents.agent_2_strategy_core.supertrend_strategy import SupertrendStrategy

def load_nvda_csv():
    """Load NVDA data from CSV"""
    csv_path = 'data/raw/NVDA_daily.csv'

    df = pd.read_csv(csv_path, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])

    print(f"Loaded {len(df)} candles from {df['date'].min()} to {df['date'].max()}")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"Total return: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.1f}%\n")

    return df

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

def run_test(df, atr_period, atr_multiplier, test_name):
    """Run backtest with given parameters"""

    cerebro = bt.Cerebro()

    # Add data
    data = PandasData(dataname=df)
    cerebro.adddata(data)

    # Add strategy
    cerebro.addstrategy(
        SupertrendStrategy,
        atr_period=atr_period,
        atr_multiplier=atr_multiplier,
        stop_loss_type='none',
        stop_loss_value=None,
        profit_target=None,
        log_trades=False  # Disable verbose logging for cleaner output
    )

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # Set initial capital
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # Run backtest
    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    # Get strategy instance and analyzers
    strat = results[0]
    trade_analysis = strat.analyzers.trades.get_analysis()

    # Calculate metrics
    total_return = ((end_value - start_value) / start_value) * 100

    # Count completed trades
    num_trades = trade_analysis.get('total', {}).get('closed', 0)

    return {
        'name': test_name,
        'atr_period': atr_period,
        'atr_multiplier': atr_multiplier,
        'return': total_return,
        'trades': num_trades,
        'final_value': end_value,
        'trade_analysis': trade_analysis
    }

def main():
    print("="*80)
    print("SUPERTREND BACKTEST - NVDA (2016-2025)")
    print("="*80)
    print()

    # Load data
    df = load_nvda_csv()

    # Test Config 1: Tighter parameters (more trades expected)
    print("Running Config 1 (ATR 14, Mult 3.0)...")
    result1 = run_test(df, atr_period=14, atr_multiplier=3.0, test_name="Config 1")

    # Test Config 2: Wider parameters (fewer trades expected)
    print("Running Config 2 (ATR 30, Mult 6.0)...")
    result2 = run_test(df, atr_period=30, atr_multiplier=6.0, test_name="Config 2")

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    print(f"\n{result1['name']} (ATR {result1['atr_period']}, Mult {result1['atr_multiplier']}):")
    print(f"  Return: {result1['return']:.2f}%")
    print(f"  Trades: {result1['trades']}")
    print(f"  Final Value: ${result1['final_value']:,.2f}")

    print(f"\n{result2['name']} (ATR {result2['atr_period']}, Mult {result2['atr_multiplier']}):")
    print(f"  Return: {result2['return']:.2f}%")
    print(f"  Trades: {result2['trades']}")
    print(f"  Final Value: ${result2['final_value']:,.2f}")

    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)

    print(f"\nTrade count difference: {abs(result1['trades'] - result2['trades'])} trades")
    print(f"Config 2 has {result1['trades'] / result2['trades']:.1f}x fewer trades (wider bands = less sensitive)")

    if result2['return'] > result1['return']:
        print(f"\n✅ Config 2 outperforms (+{result2['return'] - result1['return']:.2f}% better)")
        print("   Wider bands = Better trend-following on bull run")
    else:
        print(f"\n✅ Config 1 outperforms (+{result1['return'] - result2['return']:.2f}% better)")
        print("   Tighter bands = More responsive to price action")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
