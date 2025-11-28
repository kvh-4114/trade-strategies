"""
Phase 2 Top Configurations
Shows the best performing parameter combinations from Phase 2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_5_infrastructure.database_manager import DatabaseManager


def show_top_configs(min_tests=50, limit=20):
    """
    Show top performing configurations.

    Args:
        min_tests: Minimum number of tests required for a config to be included
        limit: Number of top configs to show
    """

    db = DatabaseManager()

    try:
        print("\n" + "="*100)
        print(f"TOP {limit} CONFIGURATIONS BY SHARPE RATIO (minimum {min_tests} tests)")
        print("="*100)

        query = """
            SELECT
                sc.mean_lookback,
                sc.stddev_lookback,
                sc.entry_threshold,
                sc.parameters->>'exit_type' as exit_type,
                sc.parameters->>'stop_loss_type' as stop_loss_type,
                sc.parameters->>'stop_loss_value' as stop_loss_value,
                COUNT(*) as tests,
                COUNT(DISTINCT br.symbol) as stocks,
                AVG(br.total_return) * 100 as avg_return_pct,
                AVG(br.sharpe_ratio) as avg_sharpe,
                AVG(br.max_drawdown) * 100 as avg_drawdown_pct,
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
                sc.parameters->>'stop_loss_type',
                sc.parameters->>'stop_loss_value'
            HAVING COUNT(*) >= %s
            ORDER BY avg_sharpe DESC
            LIMIT %s
        """

        results = db.execute_query(query, (min_tests, limit))

        if not results:
            print(f"\nNo configurations found with at least {min_tests} tests.")
            print("Try lowering min_tests or wait for more Phase 2 results.\n")
            return

        # Print header
        print(f"\n{'Rank':<5} {'Look':<5} {'Std':<5} {'Thresh':<7} {'Exit Type':<15} "
              f"{'StopLoss':<10} {'Tests':<6} {'Stocks':<6} {'Return':<8} {'Sharpe':<7} "
              f"{'DD':<7} {'WinRate':<7} {'Trades':<6}")
        print("-" * 100)

        # Print results
        for i, row in enumerate(results, 1):
            lookback, stddev, thresh, exit_type, sl_type, sl_value, tests, stocks, ret, sharpe, dd, wr, trades = row

            # Format stop loss display
            if sl_type == 'none':
                sl_display = 'none'
            else:
                sl_display = f"{sl_type}:{sl_value}" if sl_value else sl_type

            print(f"{i:<5} {lookback:<5} {stddev:<5} {thresh:<7.1f} {exit_type:<15} "
                  f"{sl_display:<10} {tests:<6} {stocks:<6} "
                  f"{ret:>7.2f}% {sharpe:>6.2f} {dd:>6.1f}% {wr:>6.1f}% {trades:>6.1f}")

        print("-" * 100)

        # Summary stats
        print(f"\nTotal configurations shown: {len(results)}")

        # Best config details
        if results:
            best = results[0]
            print(f"\n🏆 BEST CONFIGURATION:")
            print(f"   Lookback: {best[0]}, StdDev: {best[1]}, Threshold: {best[2]:.1f}")
            print(f"   Exit: {best[3]}, Stop Loss: {best[4]}")
            print(f"   Tested on {best[7]} stocks ({best[6]} tests)")
            print(f"   Avg Return: {best[8]:.2f}%, Sharpe: {best[9]:.2f}, Win Rate: {best[11]:.1f}%")

        print("\n" + "="*100 + "\n")

        # Show comparison to Phase 1 baseline
        print("\n" + "="*100)
        print("COMPARISON TO PHASE 1 BASELINE (Lookback=20, Threshold=2.0)")
        print("="*100)

        baseline_query = """
            SELECT
                AVG(br.total_return) * 100 as avg_return_pct,
                AVG(br.sharpe_ratio) as avg_sharpe,
                AVG(br.win_rate) as avg_win_rate,
                COUNT(*) as tests
            FROM backtest_results br
            JOIN strategy_configs sc ON br.config_id = sc.id
            WHERE sc.phase = 1
              AND sc.mean_lookback = 20
              AND sc.entry_threshold = 2.0
        """

        baseline = db.execute_query(baseline_query)
        if baseline and baseline[0][3] > 0:
            bl_ret, bl_sharpe, bl_wr, bl_tests = baseline[0]
            print(f"\nPhase 1 Baseline Performance:")
            print(f"   Return: {bl_ret:.2f}%, Sharpe: {bl_sharpe:.2f}, Win Rate: {bl_wr:.1f}%")
            print(f"   ({bl_tests} tests)")

            if results:
                best = results[0]
                improvement_ret = best[8] - bl_ret
                improvement_sharpe = best[9] - bl_sharpe
                improvement_wr = best[11] - bl_wr

                print(f"\nPhase 2 Best vs Baseline:")
                print(f"   Return:    {improvement_ret:+.2f}% {'✅' if improvement_ret > 0 else '❌'}")
                print(f"   Sharpe:    {improvement_sharpe:+.2f} {'✅' if improvement_sharpe > 0 else '❌'}")
                print(f"   Win Rate:  {improvement_wr:+.1f}% {'✅' if improvement_wr > 0 else '❌'}")

        print("\n" + "="*100 + "\n")

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Show top Phase 2 configurations')
    parser.add_argument(
        '--min-tests',
        type=int,
        default=50,
        help='Minimum number of tests required (default: 50)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Number of top configs to show (default: 20)'
    )

    args = parser.parse_args()

    show_top_configs(min_tests=args.min_tests, limit=args.limit)
