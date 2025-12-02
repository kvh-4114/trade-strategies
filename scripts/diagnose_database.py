"""
Database Diagnostic Script
Check what's actually in the database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_5_infrastructure.database_manager import DatabaseManager


def diagnose():
    """Run diagnostic queries."""

    db = DatabaseManager()

    try:
        print("\n" + "="*80)
        print("DATABASE DIAGNOSTIC")
        print("="*80)

        # 1. Total backtest results
        print("\n1. TOTAL BACKTEST RESULTS:")
        query = "SELECT COUNT(*) FROM backtest_results"
        total = db.execute_query(query)[0][0]
        print(f"   Total results: {total:,}")

        # 2. Results by phase
        print("\n2. RESULTS BY PHASE:")
        query = """
            SELECT
                COALESCE(sc.phase, -1) as phase,
                COUNT(*) as count
            FROM backtest_results br
            LEFT JOIN strategy_configs sc ON br.config_id = sc.id
            GROUP BY sc.phase
            ORDER BY sc.phase
        """
        results = db.execute_query(query)
        for phase, count in results:
            if phase == -1:
                print(f"   Phase NULL/Unknown: {count:,} results")
            else:
                print(f"   Phase {phase}: {count:,} results")

        # 3. Strategy configs by phase
        print("\n3. STRATEGY CONFIGS BY PHASE:")
        query = """
            SELECT phase, COUNT(*) as count
            FROM strategy_configs
            GROUP BY phase
            ORDER BY phase
        """
        results = db.execute_query(query)
        for phase, count in results:
            print(f"   Phase {phase}: {count} configs")

        # 4. Recent results
        print("\n4. MOST RECENT RESULTS:")
        query = """
            SELECT
                br.id,
                br.symbol,
                br.created_at,
                sc.phase,
                sc.config_name
            FROM backtest_results br
            JOIN strategy_configs sc ON br.config_id = sc.id
            ORDER BY br.created_at DESC
            LIMIT 10
        """
        results = db.execute_query(query)
        print(f"   {'ID':<8} {'Symbol':<8} {'Created':<20} {'Phase':<6} {'Config':<40}")
        print("   " + "-"*90)
        for row in results:
            result_id, symbol, created, phase, config = row
            print(f"   {result_id:<8} {symbol:<8} {str(created):<20} {phase:<6} {config:<40}")

        # 5. Check for Phase 2 configs specifically
        print("\n5. PHASE 2 CONFIGS:")
        query = """
            SELECT id, config_name, mean_lookback, entry_threshold
            FROM strategy_configs
            WHERE phase = 2
            LIMIT 10
        """
        results = db.execute_query(query)
        if results:
            print(f"   {'ID':<8} {'Config Name':<50} {'Lookback':<10} {'Threshold':<10}")
            print("   " + "-"*80)
            for row in results:
                config_id, name, lookback, threshold = row
                print(f"   {config_id:<8} {name:<50} {lookback:<10} {threshold:<10}")
        else:
            print("   ⚠️  NO PHASE 2 CONFIGS FOUND!")

        # 6. Check for orphaned results (no config)
        print("\n6. ORPHANED RESULTS (no matching config):")
        query = """
            SELECT COUNT(*)
            FROM backtest_results br
            WHERE NOT EXISTS (
                SELECT 1 FROM strategy_configs sc WHERE sc.id = br.config_id
            )
        """
        orphaned = db.execute_query(query)[0][0]
        print(f"   Orphaned results: {orphaned:,}")

        # 7. Date range of results
        print("\n7. RESULTS DATE RANGE:")
        query = "SELECT MIN(created_at), MAX(created_at) FROM backtest_results"
        min_date, max_date = db.execute_query(query)[0]
        print(f"   Earliest: {min_date}")
        print(f"   Latest:   {max_date}")

        print("\n" + "="*80 + "\n")

    finally:
        db.close()


if __name__ == '__main__':
    diagnose()
