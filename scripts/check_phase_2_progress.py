"""
Quick Phase 2 Progress Check
Simple script to check Phase 2 completion status
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_5_infrastructure.database_manager import DatabaseManager


def check_progress():
    """Check Phase 2 progress."""

    db = DatabaseManager()

    try:
        # Get Phase 2 count
        query = """
            SELECT COUNT(*)
            FROM backtest_results
            WHERE config_id IN (SELECT id FROM strategy_configs WHERE phase = 2)
        """
        phase2_count = db.execute_query(query)[0][0]

        # Expected total
        expected = 34200  # 190 stocks × 180 params

        # Calculate progress
        progress_pct = (phase2_count / expected) * 100

        # Estimate remaining
        if phase2_count > 0:
            remaining = expected - phase2_count
            print(f"\n{'='*60}")
            print(f"PHASE 2 PROGRESS")
            print(f"{'='*60}")
            print(f"Completed:  {phase2_count:>6,} / {expected:,} backtests")
            print(f"Progress:   {progress_pct:>6.1f}%")
            print(f"Remaining:  {remaining:>6,} backtests")
            print(f"{'='*60}\n")
        else:
            print("\nNo Phase 2 results found yet.\n")

        # Get latest results timestamp
        query = """
            SELECT MAX(created_at)
            FROM backtest_results
            WHERE config_id IN (SELECT id FROM strategy_configs WHERE phase = 2)
        """
        result = db.execute_query(query)
        if result and result[0][0]:
            latest_time = result[0][0]
            print(f"Latest result: {latest_time}")

    finally:
        db.close()


if __name__ == '__main__':
    check_progress()
