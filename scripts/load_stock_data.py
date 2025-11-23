"""
Process and Load Stock Data from Multiple CSV Files
Combines individual stock CSV files and loads into RDS
"""

import os
import glob
import pandas as pd
from datetime import datetime
import logging
from tqdm import tqdm
import sys

# Add parent directory to path
sys.path.insert(0, '/home/user/trade-strategies')
from agents.agent_5_infrastructure.database_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_stock_csv(file_path):
    """
    Process a single stock CSV file.

    Args:
        file_path: Path to CSV file

    Returns:
        DataFrame with processed data
    """
    try:
        # Read CSV
        df = pd.read_csv(file_path)

        # Keep only needed columns
        columns_needed = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        df = df[columns_needed]

        # Parse dates (format: MM/DD/YYYY)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')

        # Remove any NaN values
        df = df.dropna()

        return df

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return pd.DataFrame()


def load_all_stock_data(data_dir, db_manager, limit=None):
    """
    Load all stock CSV files and insert into database.

    Args:
        data_dir: Directory containing CSV files
        db_manager: DatabaseManager instance
        limit: Limit number of stocks to process (for testing)

    Returns:
        Total rows loaded
    """
    # Find all CSV files
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))

    if limit:
        csv_files = csv_files[:limit]

    logger.info(f"Found {len(csv_files)} CSV files to process")

    total_rows = 0
    successful_stocks = 0
    failed_stocks = 0

    # Process each file
    for csv_file in tqdm(csv_files, desc="Loading stock data"):
        try:
            # Extract symbol from filename
            filename = os.path.basename(csv_file)
            symbol = filename.split('_')[0]

            # Process CSV
            df = process_stock_csv(csv_file)

            if df.empty:
                logger.warning(f"No data for {symbol}")
                failed_stocks += 1
                continue

            # Load to database
            rows_inserted = db_manager.save_stock_data(df, symbol)
            total_rows += rows_inserted
            successful_stocks += 1

            logger.info(f"✅ {symbol}: {len(df)} rows loaded")

        except Exception as e:
            logger.error(f"❌ Failed to load {csv_file}: {e}")
            failed_stocks += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY:")
    logger.info(f"  Total stocks processed: {len(csv_files)}")
    logger.info(f"  Successful: {successful_stocks}")
    logger.info(f"  Failed: {failed_stocks}")
    logger.info(f"  Total rows loaded: {total_rows}")
    logger.info(f"{'='*60}\n")

    return total_rows


def verify_loaded_data(db_manager):
    """
    Verify data was loaded correctly.

    Args:
        db_manager: DatabaseManager instance
    """
    logger.info("Verifying loaded data...")

    # Get symbol count
    query = "SELECT COUNT(DISTINCT symbol) FROM stock_data"
    result = db_manager.execute_query(query)
    symbol_count = result[0][0] if result else 0

    # Get total rows
    query = "SELECT COUNT(*) FROM stock_data"
    result = db_manager.execute_query(query)
    total_rows = result[0][0] if result else 0

    # Get date range
    query = "SELECT MIN(date), MAX(date) FROM stock_data"
    result = db_manager.execute_query(query)
    min_date, max_date = result[0] if result else (None, None)

    # Sample data
    query = """
        SELECT symbol, COUNT(*) as row_count, MIN(date) as start_date, MAX(date) as end_date
        FROM stock_data
        GROUP BY symbol
        ORDER BY symbol
        LIMIT 10
    """
    sample = db_manager.execute_query(query)

    print("\n" + "="*60)
    print("DATABASE VERIFICATION")
    print("="*60)
    print(f"Total symbols: {symbol_count}")
    print(f"Total rows: {total_rows:,}")
    print(f"Date range: {min_date} to {max_date}")
    print(f"\nSample stocks:")
    print(f"{'Symbol':<10} {'Rows':<10} {'Start Date':<15} {'End Date'}")
    print("-"*60)
    for row in sample:
        print(f"{row[0]:<10} {row[1]:<10} {str(row[2]):<15} {str(row[3])}")
    print("="*60)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load stock data from CSV files into RDS')
    parser.add_argument('--data-dir', type=str, required=True,
                        help='Directory containing stock CSV files')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of stocks to load (for testing)')
    parser.add_argument('--verify', action='store_true',
                        help='Verify loaded data after loading')

    args = parser.parse_args()

    # Initialize database
    logger.info("Connecting to RDS...")
    db = DatabaseManager()

    # Load data
    logger.info(f"Loading data from: {args.data_dir}")
    total_rows = load_all_stock_data(args.data_dir, db, limit=args.limit)

    # Verify if requested
    if args.verify:
        verify_loaded_data(db)

    db.close()
    logger.info("✅ Complete!")
