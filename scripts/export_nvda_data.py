"""
Export NVDA price data from database to CSV for testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from agents.agent_5_infrastructure.database_manager import DatabaseManager
from agents.agent_3_optimization.candle_loader import CandleLoader

def export_nvda_data():
    """Export NVDA regular candles to CSV"""

    print("Connecting to database...")
    db = DatabaseManager()
    loader = CandleLoader(db)

    print("Loading NVDA candles (regular, 1-day)...")
    df = loader.load_candles(
        symbol='NVDA',
        candle_type='regular',
        aggregation_days=1
    )

    if df.empty:
        print("ERROR: No data found!")
        return

    # Reset index to make date a column
    df = df.reset_index()

    print(f"Loaded {len(df)} candles from {df['date'].min()} to {df['date'].max()}")

    # Save to CSV
    output_file = 'data/raw/NVDA_daily.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    df.to_csv(output_file, index=False)
    print(f"✅ Exported to {output_file}")

    # Print sample
    print("\nFirst 5 rows:")
    print(df.head())
    print("\nLast 5 rows:")
    print(df.tail())

    print(f"\nPrice range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"Total return: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.1f}%")

if __name__ == '__main__':
    export_nvda_data()
