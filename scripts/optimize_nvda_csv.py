"""
Optimize Supertrend parameters for NVDA using CSV data
Find the best configuration for the massive 2016-2025 bull run
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtrader as bt
from agents.agent_2_strategy_core.supertrend_strategy import SupertrendStrategy
import itertools

def load_nvda_csv():
    """Load NVDA data from CSV"""
    csv_path = 'data/raw/NVDA_daily.csv'
    df = pd.read_csv(csv_path, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
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

def run_backtest(df, params):
    """Run single backtest with given parameters"""
    cerebro = bt.Cerebro()

    data = PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(
        SupertrendStrategy,
        atr_period=params['atr_period'],
        atr_multiplier=params['atr_multiplier'],
        stop_loss_type=params['stop_loss_type'],
        stop_loss_value=params['stop_loss_value'],
        profit_target=params['profit_target'],
        log_trades=False
    )

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    strat = results[0]

    # Extract metrics
    trade_analysis = strat.analyzers.trades.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()

    num_trades = trade_analysis.get('total', {}).get('closed', 0)
    total_return = ((end_value - start_value) / start_value) * 100
    max_dd = drawdown.get('max', {}).get('drawdown', 0) if drawdown.get('max') else 0
    sharpe_ratio = sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0

    # Calculate win rate
    won = trade_analysis.get('won', {}).get('total', 0)
    lost = trade_analysis.get('lost', {}).get('total', 0)
    win_rate = (won / num_trades * 100) if num_trades > 0 else 0

    return {
        **params,
        'return': total_return,
        'trades': num_trades,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'sharpe': sharpe_ratio,
        'final_value': end_value
    }

def generate_parameter_grid():
    """Generate parameter combinations to test"""

    # Focus on trend-following parameters
    param_grid = {
        'atr_period': [10, 14, 20, 30],
        'atr_multiplier': [2.0, 3.0, 4.0, 5.0, 6.0],
        'stop_loss_type': ['none', 'fixed_pct'],
        'stop_loss_value': [None, -0.10, -0.15],  # 10% and 15% stops
        'profit_target': [None, 0.50, 1.00, 2.00],  # 50%, 100%, 200% targets
    }

    combinations = []

    # Generate all combos
    for period, mult, pt in itertools.product(
        param_grid['atr_period'],
        param_grid['atr_multiplier'],
        param_grid['profit_target']
    ):
        # No stop loss
        combinations.append({
            'atr_period': period,
            'atr_multiplier': mult,
            'stop_loss_type': 'none',
            'stop_loss_value': None,
            'profit_target': pt
        })

        # With stop loss
        for sl in param_grid['stop_loss_value']:
            if sl is not None:
                combinations.append({
                    'atr_period': period,
                    'atr_multiplier': mult,
                    'stop_loss_type': 'fixed_pct',
                    'stop_loss_value': sl,
                    'profit_target': pt
                })

    return combinations

def main():
    print("="*80)
    print("NVDA SUPERTREND PARAMETER OPTIMIZATION")
    print("="*80)
    print()

    # Load data
    print("Loading NVDA data...")
    df = load_nvda_csv()
    print(f"Loaded {len(df)} candles from {df['date'].min()} to {df['date'].max()}")
    print(f"Price: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f} ({((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.1f}% total return)")
    print()

    # Generate parameter grid
    param_combos = generate_parameter_grid()
    print(f"Testing {len(param_combos)} parameter combinations...")
    print()

    # Run optimization
    results = []
    for i, params in enumerate(param_combos, 1):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(param_combos)} ({i/len(param_combos)*100:.1f}%)")

        try:
            result = run_backtest(df, params)
            results.append(result)
        except Exception as e:
            print(f"Error with params {params}: {e}")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Sort by return
    results_df = results_df.sort_values('return', ascending=False)

    # Display top 10
    print("\n" + "="*80)
    print("TOP 10 CONFIGURATIONS (by Return)")
    print("="*80)
    print()

    for i, row in results_df.head(10).iterrows():
        print(f"\n#{i+1} - Return: {row['return']:.2f}%")
        print(f"   ATR Period: {row['atr_period']}, Multiplier: {row['atr_multiplier']}")
        print(f"   Stop Loss: {row['stop_loss_type']} ({row['stop_loss_value']})")
        print(f"   Profit Target: {row['profit_target']}")
        print(f"   Trades: {row['trades']}, Win Rate: {row['win_rate']:.1f}%")
        print(f"   Max DD: {row['max_dd']:.2f}%, Sharpe: {row['sharpe']:.2f}")

    # Save full results
    output_file = 'data/results/nvda_optimization_results.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ Full results saved to {output_file}")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
