#!/usr/bin/env python3
"""
Portfolio-Level Analysis for Phase 1 Results
Shows aggregated metrics across all stocks and configurations
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager


def analyze_portfolio_metrics():
    """Analyze portfolio-level metrics from Phase 1 results."""

    db = DatabaseManager()

    print("=" * 80)
    print("PHASE 1 PORTFOLIO ANALYSIS")
    print("=" * 80)

    # 1. Overall portfolio statistics
    query = """
        SELECT
            COUNT(*) as total_backtests,
            COUNT(DISTINCT br.symbol) as total_stocks,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.max_drawdown) as avg_drawdown,
            SUM(br.total_trades) as total_trades,
            AVG(br.win_rate) as portfolio_win_rate,
            SUM(CASE WHEN br.total_return > 0 THEN 1 ELSE 0 END) as profitable_configs,
            SUM(CASE WHEN br.total_return <= 0 THEN 1 ELSE 0 END) as losing_configs
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
    """

    result = db.execute_query(query)
    stats = result[0]

    print(f"\n📊 OVERALL PORTFOLIO METRICS")
    print("-" * 80)
    print(f"Total backtests:        {stats[0]:,}")
    print(f"Unique stocks:          {stats[1]}")
    print(f"Average return:         {stats[2]:.2%}")
    print(f"Average Sharpe ratio:   {stats[3]:.3f}")
    print(f"Average max drawdown:   {stats[4]:.2%}")
    print(f"Total trades executed:  {stats[5]:,}")
    print(f"Portfolio win rate:     {stats[6]:.2f}%")
    print(f"Profitable configs:     {stats[7]} ({stats[7]/stats[0]*100:.1f}%)")
    print(f"Losing configs:         {stats[8]} ({stats[8]/stats[0]*100:.1f}%)")

    # 2. By candle type and aggregation
    query = """
        SELECT
            sc.candle_type,
            sc.aggregation_days,
            COUNT(*) as num_stocks,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            AVG(br.max_drawdown) as avg_drawdown,
            AVG(br.total_trades) as avg_trades,
            AVG(br.win_rate) as avg_win_rate,
            SUM(CASE WHEN br.total_return > 0 THEN 1 ELSE 0 END) as profitable_stocks
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
        GROUP BY sc.candle_type, sc.aggregation_days
        ORDER BY avg_return DESC
    """

    results = db.execute_query(query)

    print(f"\n🕯️  PERFORMANCE BY CANDLE CONFIGURATION")
    print("-" * 80)
    print(f"{'Type':<20} {'Agg':>3} {'Stocks':>7} {'Avg Return':>11} {'Avg Sharpe':>11} {'Avg DD':>11} {'Win Rate':>9} {'Profitable':>11}")
    print("-" * 80)

    for row in results:
        candle_type, agg, num_stocks, avg_ret, avg_sharpe, avg_dd, avg_trades, win_rate, profitable = row
        print(f"{candle_type:<20} {agg:>3}d {num_stocks:>7} {avg_ret:>10.2%} {avg_sharpe:>11.3f} {avg_dd:>10.2%} {win_rate:>8.1f}% {profitable:>4}/{num_stocks:<4}")

    # 3. Top performing stocks (across all configs)
    query = """
        SELECT
            br.symbol,
            sc.candle_type,
            sc.aggregation_days,
            br.total_return,
            br.sharpe_ratio,
            br.max_drawdown,
            br.total_trades,
            br.win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
        ORDER BY br.total_return DESC
        LIMIT 20
    """

    results = db.execute_query(query)

    print(f"\n🏆 TOP 20 PERFORMING CONFIGURATIONS")
    print("-" * 80)
    print(f"{'Symbol':<8} {'Type':<15} {'Agg':>3} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'Trades':>7} {'WinRate':>9}")
    print("-" * 80)

    for row in results:
        symbol, ctype, agg, ret, sharpe, dd, trades, wr = row
        print(f"{symbol:<8} {ctype:<15} {agg:>3}d {ret:>9.2%} {sharpe:>8.2f} {dd:>9.2%} {trades:>7} {wr:>8.1f}%")

    # 4. Worst performing stocks
    query = """
        SELECT
            br.symbol,
            sc.candle_type,
            sc.aggregation_days,
            br.total_return,
            br.sharpe_ratio,
            br.max_drawdown,
            br.total_trades,
            br.win_rate
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
        ORDER BY br.total_return ASC
        LIMIT 20
    """

    results = db.execute_query(query)

    print(f"\n⚠️  BOTTOM 20 PERFORMING CONFIGURATIONS")
    print("-" * 80)
    print(f"{'Symbol':<8} {'Type':<15} {'Agg':>3} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'Trades':>7} {'WinRate':>9}")
    print("-" * 80)

    for row in results:
        symbol, ctype, agg, ret, sharpe, dd, trades, wr = row
        print(f"{symbol:<8} {ctype:<15} {agg:>3}d {ret:>9.2%} {sharpe:>8.2f} {dd:>9.2%} {trades:>7} {wr:>8.1f}%")

    # 5. Win rate distribution
    query = """
        SELECT
            CASE
                WHEN br.win_rate = 0 THEN '0%'
                WHEN br.win_rate > 0 AND br.win_rate <= 25 THEN '1-25%'
                WHEN br.win_rate > 25 AND br.win_rate <= 50 THEN '26-50%'
                WHEN br.win_rate > 50 AND br.win_rate <= 75 THEN '51-75%'
                ELSE '76-100%'
            END as win_rate_bucket,
            COUNT(*) as count
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
        GROUP BY win_rate_bucket
        ORDER BY win_rate_bucket
    """

    results = db.execute_query(query)

    print(f"\n📈 WIN RATE DISTRIBUTION")
    print("-" * 80)
    print(f"{'Win Rate Range':<15} {'Count':>10} {'Percentage':>12}")
    print("-" * 80)

    total = sum(row[1] for row in results)
    for row in results:
        bucket, count = row
        pct = count / total * 100
        print(f"{bucket:<15} {count:>10} {pct:>11.1f}%")

    # 6. Configuration recommendations
    print(f"\n💡 RECOMMENDATIONS FOR PHASE 2")
    print("-" * 80)

    query = """
        SELECT
            sc.candle_type,
            sc.aggregation_days,
            AVG(br.total_return) as avg_return,
            AVG(br.sharpe_ratio) as avg_sharpe,
            COUNT(*) as num_stocks,
            SUM(CASE WHEN br.total_return > 0 THEN 1 ELSE 0 END) as profitable
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
        GROUP BY sc.candle_type, sc.aggregation_days
        HAVING AVG(br.sharpe_ratio) > 0.5 AND AVG(br.total_return) > 0
        ORDER BY avg_return DESC, avg_sharpe DESC
        LIMIT 5
    """

    results = db.execute_query(query)

    if results:
        print(f"\nTop 5 configurations to advance to Phase 2:")
        print(f"(Based on Sharpe > 0.5 and positive returns)\n")

        for i, row in enumerate(results, 1):
            ctype, agg, avg_ret, avg_sharpe, num_stocks, profitable = row
            print(f"{i}. {ctype} {agg}d: {avg_ret:.2%} avg return, {avg_sharpe:.2f} Sharpe, {profitable}/{num_stocks} profitable")
    else:
        print("No configurations met the advancement criteria (Sharpe > 0.5, positive returns)")

    print("\n" + "=" * 80)

    db.close()


if __name__ == '__main__':
    analyze_portfolio_metrics()
