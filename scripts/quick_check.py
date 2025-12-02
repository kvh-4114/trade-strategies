#!/usr/bin/env python3
"""
Fast database progress check - shows counts only, no heavy calculations
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager

def quick_check():
    """Quick check - just show totals."""

    db = DatabaseManager()

    print("="* 60)
    print("QUICK DATABASE CHECK")
    print("=" * 60)

    # Total candles
    query = "SELECT COUNT(*) FROM candles"
    result = db.execute_query(query)
    total = result[0][0]

    print(f"\n🕯️  Total Candles: {total:,}")

    # By type (faster query - just counts)
    query = """
        SELECT candle_type, COUNT(*) as count
        FROM candles
        GROUP BY candle_type
        ORDER BY candle_type
    """
    results = db.execute_query(query)

    print(f"\nBy Type:")
    for row in results:
        print(f"  {row[0]:<15} {row[1]:>12,}")

    # Symbols with complete data (all 13 combinations)
    query = """
        SELECT symbol, COUNT(DISTINCT candle_type || '_' || aggregation_days) as combos
        FROM candles
        GROUP BY symbol
        HAVING COUNT(DISTINCT candle_type || '_' || aggregation_days) = 13
    """
    results = db.execute_query(query)
    complete_symbols = len(results)

    print(f"\n📊 Symbols with complete data (all 13 combos): {complete_symbols} / 268")

    print("=" * 60)

    db.close()

if __name__ == '__main__':
    quick_check()
