#!/usr/bin/env python3
"""
Quick script to check RDS database progress
Run this on EC2 to see candle generation status
"""

import os
import sys

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager


def check_progress():
    """Check candle generation progress in database."""

    db = DatabaseManager()

    print("=" * 80)
    print("DATABASE PROGRESS CHECK")
    print("=" * 80)

    # Check stock data
    query = "SELECT COUNT(*), COUNT(DISTINCT symbol) FROM stock_data"
    result = db.execute_query(query)
    total_rows, total_symbols = result[0]
    print(f"\n📊 Stock Data:")
    print(f"   Total rows: {total_rows:,}")
    print(f"   Total symbols: {total_symbols}")

    # Check candles by type and aggregation
    query = """
        SELECT
            candle_type,
            aggregation_days,
            COUNT(*) as candle_count,
            COUNT(DISTINCT symbol) as symbol_count
        FROM candles
        GROUP BY candle_type, aggregation_days
        ORDER BY candle_type, aggregation_days
    """

    results = db.execute_query(query)

    print(f"\n🕯️  Candles Generated:")
    print(f"{'Type':<20} {'Agg':<5} {'Candles':<12} {'Symbols'}")
    print("-" * 80)

    total_candles = 0
    for row in results:
        candle_type, agg_days, candle_count, symbol_count = row
        print(f"{candle_type:<20} {agg_days:<5} {candle_count:>11,} {symbol_count:>8}")
        total_candles += candle_count

    print("-" * 80)
    print(f"{'TOTAL':<20} {'':<5} {total_candles:>11,}")

    # Expected totals
    print(f"\n📈 Expected Progress:")

    # Get date range from stock_data
    query = "SELECT MIN(date), MAX(date) FROM stock_data"
    result = db.execute_query(query)
    min_date, max_date = result[0]

    if min_date and max_date:
        from datetime import datetime
        start = datetime.strptime(str(min_date), '%Y-%m-%d')
        end = datetime.strptime(str(max_date), '%Y-%m-%d')
        days_in_data = (end - start).days + 1

        print(f"   Date range: {min_date} to {max_date}")
        print(f"   Days in data: {days_in_data:,}")

        # Expected candles per combination (roughly)
        # Note: aggregated candles will have fewer rows
        expected_per_1day = total_symbols * days_in_data

        print(f"   Expected 1-day candles per type: ~{expected_per_1day:,}")
        print(f"   Expected 2-day candles per type: ~{expected_per_1day//2:,}")
        print(f"   Expected 3-day candles per type: ~{expected_per_1day//3:,}")
        print(f"   Expected 4-day candles per type: ~{expected_per_1day//4:,}")
        print(f"   Expected 5-day candles per type: ~{expected_per_1day//5:,}")

    # Completion percentage
    query = "SELECT COUNT(*) FROM candles"
    result = db.execute_query(query)
    total_candles_db = result[0][0]

    # Expected total (rough estimate)
    # 3 types: regular (1-5d), heiken_ashi (1-5d), linreg (1-3d)
    # = 5 + 5 + 3 = 13 combinations
    # Average aggregation factor ~= 3 days (rough estimate)
    if min_date and max_date:
        expected_total = total_symbols * days_in_data * 13 / 3
        completion_pct = (total_candles_db / expected_total) * 100

        print(f"\n⏳ Estimated Completion:")
        print(f"   Current: {total_candles_db:,} candles")
        print(f"   Expected: ~{expected_total:,.0f} candles")
        print(f"   Progress: ~{completion_pct:.1f}%")

    print("\n" + "=" * 80)

    db.close()


if __name__ == '__main__':
    check_progress()
