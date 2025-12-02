"""
Analyze Partial Phase 2 Results
Comprehensive analysis of Phase 2 parameter optimization while running
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_5_infrastructure.database_manager import DatabaseManager
import pandas as pd


def analyze_parameter_distribution(db):
    """Analyze which parameter combinations have been tested."""

    print("\n" + "="*80)
    print("PARAMETER DISTRIBUTION ANALYSIS")
    print("="*80)

    # Get parameter distribution
    query = """
        SELECT
            sc.mean_lookback,
            sc.stddev_lookback,
            sc.entry_threshold,
            sc.parameters->>'exit_type' as exit_type,
            sc.parameters->>'stop_loss_type' as stop_loss_type,
            COUNT(DISTINCT br.symbol) as stocks_tested,
            COUNT(*) as total_tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate,
            AVG(br.total_trades) as avg_trades
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY
            sc.mean_lookback,
            sc.stddev_lookback,
            sc.entry_threshold,
            sc.parameters->>'exit_type',
            sc.parameters->>'stop_loss_type'
        ORDER BY total_tests DESC
        LIMIT 50
    """

    results = db.execute_query(query)

    print(f"\nTop 50 Parameter Combinations by Test Count:\n")
    print(f"{'Lookback':<8} {'StdDev':<8} {'Thresh':<8} {'Exit Type':<15} {'StopLoss':<10} "
          f"{'Stocks':<7} {'Tests':<7} {'Return':<8} {'Sharpe':<8} {'WinRate':<8} {'Trades':<7}")
    print("-" * 120)

    for row in results:
        lookback, stddev, thresh, exit_type, stop_loss, stocks, tests, ret, sharpe, wr, trades = row
        print(f"{lookback:<8} {stddev:<8} {thresh:<8.1f} {exit_type:<15} {stop_loss:<10} "
              f"{stocks:<7} {tests:<7} {ret*100:>7.2f}% {sharpe:>7.2f} {wr:>7.1f}% {trades:>7.1f}")


def analyze_by_individual_params(db):
    """Analyze performance by individual parameters."""

    print("\n" + "="*80)
    print("PARAMETER SENSITIVITY ANALYSIS")
    print("="*80)

    # By lookback
    print("\n1. By Mean Lookback:")
    query = """
        SELECT
            sc.mean_lookback,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.mean_lookback
        ORDER BY sc.mean_lookback
    """
    results = db.execute_query(query)
    print(f"{'Lookback':<10} {'Tests':<10} {'Avg Return':<12} {'Avg Sharpe':<12} {'Avg WinRate':<12}")
    print("-" * 60)
    for lookback, tests, ret, sharpe, wr in results:
        print(f"{lookback:<10} {tests:<10} {ret*100:>11.2f}% {sharpe:>11.2f} {wr:>11.1f}%")

    # By threshold
    print("\n2. By Entry Threshold:")
    query = """
        SELECT
            sc.entry_threshold,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.entry_threshold
        ORDER BY sc.entry_threshold
    """
    results = db.execute_query(query)
    print(f"{'Threshold':<10} {'Tests':<10} {'Avg Return':<12} {'Avg Sharpe':<12} {'Avg WinRate':<12}")
    print("-" * 60)
    for thresh, tests, ret, sharpe, wr in results:
        print(f"{thresh:<10.1f} {tests:<10} {ret*100:>11.2f}% {sharpe:>11.2f} {wr:>11.1f}%")

    # By exit type
    print("\n3. By Exit Type:")
    query = """
        SELECT
            sc.parameters->>'exit_type' as exit_type,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.parameters->>'exit_type'
        ORDER BY tests DESC
    """
    results = db.execute_query(query)
    print(f"{'Exit Type':<15} {'Tests':<10} {'Avg Return':<12} {'Avg Sharpe':<12} {'Avg WinRate':<12}")
    print("-" * 65)
    for exit_type, tests, ret, sharpe, wr in results:
        print(f"{exit_type:<15} {tests:<10} {ret*100:>11.2f}% {sharpe:>11.2f} {wr:>11.1f}%")

    # By stop loss
    print("\n4. By Stop Loss Type:")
    query = """
        SELECT
            sc.parameters->>'stop_loss_type' as stop_loss_type,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.parameters->>'stop_loss_type'
        ORDER BY tests DESC
    """
    results = db.execute_query(query)
    print(f"{'Stop Loss':<15} {'Tests':<10} {'Avg Return':<12} {'Avg Sharpe':<12} {'Avg WinRate':<12}")
    print("-" * 65)
    for sl_type, tests, ret, sharpe, wr in results:
        print(f"{sl_type:<15} {tests:<10} {ret*100:>11.2f}% {sharpe:>11.2f} {wr:>11.1f}%")


def analyze_top_performers(db):
    """Find top performing configurations so far."""

    print("\n" + "="*80)
    print("TOP PERFORMERS (Minimum 50 tests per config)")
    print("="*80)

    # Top by Sharpe
    print("\n1. Top 10 by Sharpe Ratio:")
    query = """
        SELECT
            sc.mean_lookback,
            sc.entry_threshold,
            sc.parameters->>'exit_type' as exit_type,
            sc.parameters->>'stop_loss_type' as stop_loss_type,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.mean_lookback, sc.entry_threshold,
                 sc.parameters->>'exit_type', sc.parameters->>'stop_loss_type'
        HAVING COUNT(*) >= 50
        ORDER BY avg_sharpe DESC
        LIMIT 10
    """
    results = db.execute_query(query)
    print(f"{'Lookback':<10} {'Thresh':<8} {'Exit':<15} {'StopLoss':<10} {'Tests':<7} {'Return':<10} {'Sharpe':<10} {'WinRate':<10}")
    print("-" * 90)
    for lookback, thresh, exit_t, sl_t, tests, ret, sharpe, wr in results:
        print(f"{lookback:<10} {thresh:<8.1f} {exit_t:<15} {sl_t:<10} {tests:<7} "
              f"{ret*100:>9.2f}% {sharpe:>9.2f} {wr:>9.1f}%")

    # Top by return
    print("\n2. Top 10 by Total Return:")
    query = """
        SELECT
            sc.mean_lookback,
            sc.entry_threshold,
            sc.parameters->>'exit_type' as exit_type,
            sc.parameters->>'stop_loss_type' as stop_loss_type,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.mean_lookback, sc.entry_threshold,
                 sc.parameters->>'exit_type', sc.parameters->>'stop_loss_type'
        HAVING COUNT(*) >= 50
        ORDER BY avg_return DESC
        LIMIT 10
    """
    results = db.execute_query(query)
    print(f"{'Lookback':<10} {'Thresh':<8} {'Exit':<15} {'StopLoss':<10} {'Tests':<7} {'Return':<10} {'Sharpe':<10} {'WinRate':<10}")
    print("-" * 90)
    for lookback, thresh, exit_t, sl_t, tests, ret, sharpe, wr in results:
        print(f"{lookback:<10} {thresh:<8.1f} {exit_t:<15} {sl_t:<10} {tests:<7} "
              f"{ret*100:>9.2f}% {sharpe:>9.2f} {wr:>9.1f}%")

    # Top by win rate
    print("\n3. Top 10 by Win Rate:")
    query = """
        SELECT
            sc.mean_lookback,
            sc.entry_threshold,
            sc.parameters->>'exit_type' as exit_type,
            sc.parameters->>'stop_loss_type' as stop_loss_type,
            COUNT(*) as tests,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.win_rate) as avg_win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 2
        GROUP BY sc.mean_lookback, sc.entry_threshold,
                 sc.parameters->>'exit_type', sc.parameters->>'stop_loss_type'
        HAVING COUNT(*) >= 50
        ORDER BY avg_win_rate DESC
        LIMIT 10
    """
    results = db.execute_query(query)
    print(f"{'Lookback':<10} {'Thresh':<8} {'Exit':<15} {'StopLoss':<10} {'Tests':<7} {'Return':<10} {'Sharpe':<10} {'WinRate':<10}")
    print("-" * 90)
    for lookback, thresh, exit_t, sl_t, tests, ret, sharpe, wr in results:
        print(f"{lookback:<10} {thresh:<8.1f} {exit_t:<15} {sl_t:<10} {tests:<7} "
              f"{ret*100:>9.2f}% {sharpe:>9.2f} {wr:>9.1f}%")


def get_progress_stats(db):
    """Get current progress statistics."""

    print("\n" + "="*80)
    print("PHASE 2 PROGRESS")
    print("="*80)

    # Total results
    query = "SELECT COUNT(*) FROM backtest_results WHERE config_id IN (SELECT id FROM strategy_configs WHERE phase = 2)"
    total_results = db.execute_query(query)[0][0]

    # Unique configs tested
    query = "SELECT COUNT(DISTINCT config_id) FROM backtest_results WHERE config_id IN (SELECT id FROM strategy_configs WHERE phase = 2)"
    unique_configs = db.execute_query(query)[0][0]

    # Unique stocks tested
    query = "SELECT COUNT(DISTINCT symbol) FROM backtest_results WHERE config_id IN (SELECT id FROM strategy_configs WHERE phase = 2)"
    unique_stocks = db.execute_query(query)[0][0]

    # Expected total
    expected_total = 34200  # From config: 190 stocks × 180 params

    print(f"\nTotal backtests completed: {total_results:,} / {expected_total:,} ({total_results/expected_total*100:.1f}%)")
    print(f"Unique configs tested: {unique_configs}")
    print(f"Unique stocks tested: {unique_stocks}")
    print(f"\nExpected configs: 180")
    print(f"Expected stocks: 190")


def main():
    """Run all analyses."""

    print("\n" + "="*80)
    print("PHASE 2 PARTIAL RESULTS ANALYSIS")
    print("="*80)

    db = DatabaseManager()

    try:
        # Progress
        get_progress_stats(db)

        # Parameter distribution
        analyze_parameter_distribution(db)

        # Individual parameter effects
        analyze_by_individual_params(db)

        # Top performers
        analyze_top_performers(db)

    finally:
        db.close()

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
