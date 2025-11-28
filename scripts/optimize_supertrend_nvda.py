"""
Optimize Supertrend Parameters for NVDA
Find the best Supertrend configuration on a strong trending stock
"""

import os
import sys
import pandas as pd
import itertools
from datetime import datetime
from tqdm import tqdm

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager
from agents.agent_3_optimization.candle_loader import CandleLoader
from scripts.run_phase_3_supertrend import run_supertrend_backtest, save_results_to_db


def generate_parameter_grid():
    """Generate comprehensive parameter grid for optimization."""

    # More granular parameter ranges for optimization
    param_grid = {
        'atr_period': [7, 10, 14, 20],
        'atr_multiplier': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        'stop_loss_type': ['none', 'atr'],
        'stop_loss_value': [None, 1.5, 2.0, 3.0],
        'profit_target': [None, 0.10, 0.15, 0.20, 0.30],
    }

    combinations = []

    for period, multiplier, profit_target in itertools.product(
        param_grid['atr_period'],
        param_grid['atr_multiplier'],
        param_grid['profit_target']
    ):
        # No stop loss
        combinations.append({
            'atr_period': period,
            'atr_multiplier': multiplier,
            'stop_loss_type': 'none',
            'stop_loss_value': None,
            'profit_target': profit_target,
            'position_sizing': 'fixed',
            'position_size': 10000
        })

        # ATR-based stop loss
        for sl_value in param_grid['stop_loss_value']:
            if sl_value is not None:
                combinations.append({
                    'atr_period': period,
                    'atr_multiplier': multiplier,
                    'stop_loss_type': 'atr',
                    'stop_loss_value': sl_value,
                    'profit_target': profit_target,
                    'position_sizing': 'fixed',
                    'position_size': 10000
                })

    return combinations


def optimize_nvda():
    """Run parameter optimization on NVDA."""

    print("\n" + "="*100)
    print("SUPERTREND PARAMETER OPTIMIZATION - NVDA")
    print("="*100)

    # Initialize
    db = DatabaseManager()
    candle_loader = CandleLoader(db)

    # Load NVDA candles
    print("\n1. Loading NVDA candles...")
    candle_df = candle_loader.load_candles(
        symbol='NVDA',
        candle_type='regular',
        aggregation_days=1
    )

    if candle_df is None or len(candle_df) == 0:
        print("❌ No candles found for NVDA")
        db.close()
        return

    print(f"✅ Loaded {len(candle_df)} candles ({candle_df.index[0]} to {candle_df.index[-1]})")

    # Generate parameter combinations
    print("\n2. Generating parameter combinations...")
    param_combinations = generate_parameter_grid()
    print(f"✅ Generated {len(param_combinations)} parameter combinations")

    # Run backtests
    print("\n3. Running backtests...")
    print(f"   Total: {len(param_combinations)} backtests")

    results = []
    start_time = datetime.now()

    for i, params in enumerate(tqdm(param_combinations, desc="Optimizing"), 1):
        try:
            # Run backtest
            result = run_supertrend_backtest(
                candle_df=candle_df,
                symbol='NVDA',
                strategy_params=params,
                initial_capital=100000,
                commission=0.001
            )

            # Save to database
            if 'error' not in result:
                save_results_to_db(result, db)
                results.append(result)

        except Exception as e:
            print(f"\n❌ Error with params {params}: {e}")

    # Analysis
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*100)
    print("OPTIMIZATION COMPLETE")
    print("="*100)
    print(f"Completed: {len(results)} / {len(param_combinations)} backtests")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Rate: {len(results)/elapsed:.1f} backtests/sec")

    # Sort results
    if results:
        print("\n" + "="*100)
        print("TOP 10 CONFIGURATIONS BY SHARPE RATIO")
        print("="*100)

        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('sharpe_ratio', ascending=False)

        print(f"\n{'Rank':<5} {'ATR':<4} {'Mult':<5} {'StopLoss':<10} {'ProfitTgt':<10} "
              f"{'Return':<8} {'Sharpe':<7} {'Trades':<7} {'WinRate':<8}")
        print("-"*90)

        for i, row in df_results.head(10).iterrows():
            params = row['strategy_params']
            sl_display = f"{params['stop_loss_type'][:3]}" if params['stop_loss_type'] != 'none' else 'none'
            if params['stop_loss_value']:
                sl_display += f":{params['stop_loss_value']:.1f}"

            pt_display = f"{params['profit_target']*100:.0f}%" if params['profit_target'] else 'none'

            print(f"{i+1:<5} {params['atr_period']:<4} {params['atr_multiplier']:<5.1f} "
                  f"{sl_display:<10} {pt_display:<10} "
                  f"{row['total_return']*100:>7.2f}% {row['sharpe_ratio']:>6.2f} "
                  f"{row['total_trades']:>6} {row['win_rate']:>7.1f}%")

        # Best configuration
        best = df_results.iloc[0]
        print("\n" + "="*100)
        print("🏆 BEST CONFIGURATION")
        print("="*100)
        print(f"ATR Period:      {best['strategy_params']['atr_period']}")
        print(f"ATR Multiplier:  {best['strategy_params']['atr_multiplier']}")
        print(f"Stop Loss:       {best['strategy_params']['stop_loss_type']} "
              f"({best['strategy_params']['stop_loss_value']} if applicable)")
        print(f"Profit Target:   {best['strategy_params']['profit_target']*100:.0f}% "
              f"if best['strategy_params']['profit_target'] else 'None'")
        print(f"\nReturn:          {best['total_return']*100:.2f}%")
        print(f"Sharpe Ratio:    {best['sharpe_ratio']:.2f}")
        print(f"Max Drawdown:    {best['max_drawdown']*100:.1f}%")
        print(f"Total Trades:    {best['total_trades']}")
        print(f"Win Rate:        {best['win_rate']:.1f}%")
        print(f"Avg Trade:       {best['total_return']/best['total_trades']*100:.2f}%")
        print("="*100)

        # Top by return
        print("\n" + "="*100)
        print("TOP 10 BY TOTAL RETURN")
        print("="*100)
        df_by_return = df_results.sort_values('total_return', ascending=False)

        print(f"\n{'Rank':<5} {'ATR':<4} {'Mult':<5} {'StopLoss':<10} {'ProfitTgt':<10} "
              f"{'Return':<8} {'Sharpe':<7} {'Trades':<7} {'WinRate':<8}")
        print("-"*90)

        for i, row in df_by_return.head(10).iterrows():
            params = row['strategy_params']
            sl_display = f"{params['stop_loss_type'][:3]}" if params['stop_loss_type'] != 'none' else 'none'
            if params['stop_loss_value']:
                sl_display += f":{params['stop_loss_value']:.1f}"

            pt_display = f"{params['profit_target']*100:.0f}%" if params['profit_target'] else 'none'

            print(f"{i+1:<5} {params['atr_period']:<4} {params['atr_multiplier']:<5.1f} "
                  f"{sl_display:<10} {pt_display:<10} "
                  f"{row['total_return']*100:>7.2f}% {row['sharpe_ratio']:>6.2f} "
                  f"{row['total_trades']:>6} {row['win_rate']:>7.1f}%")

    db.close()
    print("\n✅ Optimization complete! Results saved to database.")


if __name__ == '__main__':
    optimize_nvda()
