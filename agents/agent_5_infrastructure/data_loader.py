"""
Data Loader for Mean Reversion Framework
Loads stock data from CSV files into AWS RDS PostgreSQL database
"""

import os
import argparse
import pandas as pd
from typing import List, Optional
from pathlib import Path
import logging
from tqdm import tqdm

from agents.agent_5_infrastructure.database_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataLoader:
    """Load stock data from CSV files into database"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize data loader.

        Args:
            db_manager: Database manager instance (creates new if None)
        """
        self.db = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)

    def load_csv(
        self,
        file_path: str,
        symbol_column: str = 'symbol',
        date_column: str = 'date',
        required_columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load stock data from CSV file.

        Expected CSV format:
        symbol,date,open,high,low,close,volume
        AAPL,2020-01-02,300.35,301.00,298.50,300.95,32850000

        Args:
            file_path: Path to CSV file
            symbol_column: Name of symbol column
            date_column: Name of date column
            required_columns: List of required columns

        Returns:
            DataFrame with stock data
        """
        if required_columns is None:
            required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']

        self.logger.info(f"Loading data from {file_path}")

        # Read CSV
        df = pd.read_csv(file_path)

        # Validate columns
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Parse dates
        df[date_column] = pd.to_datetime(df[date_column])

        # Sort by symbol and date
        df = df.sort_values([symbol_column, date_column])

        self.logger.info(f"Loaded {len(df)} rows for {df[symbol_column].nunique()} symbols")

        return df

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean stock data.

        Args:
            df: Raw stock data DataFrame

        Returns:
            Cleaned DataFrame
        """
        initial_rows = len(df)

        # Remove rows with missing OHLCV data
        df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])

        # Validate OHLC relationships
        invalid_ohlc = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        )

        if invalid_ohlc.any():
            self.logger.warning(f"Found {invalid_ohlc.sum()} rows with invalid OHLC relationships")
            df = df[~invalid_ohlc]

        # Remove negative prices or volume
        invalid_values = (
            (df['open'] <= 0) |
            (df['high'] <= 0) |
            (df['low'] <= 0) |
            (df['close'] <= 0) |
            (df['volume'] < 0)
        )

        if invalid_values.any():
            self.logger.warning(f"Found {invalid_values.sum()} rows with invalid values")
            df = df[~invalid_values]

        # Remove duplicate (symbol, date) pairs
        duplicates = df.duplicated(subset=['symbol', 'date'], keep='first')
        if duplicates.any():
            self.logger.warning(f"Found {duplicates.sum()} duplicate rows")
            df = df[~duplicates]

        removed_rows = initial_rows - len(df)
        if removed_rows > 0:
            self.logger.info(f"Removed {removed_rows} invalid rows ({removed_rows/initial_rows*100:.2f}%)")

        return df

    def load_to_database(
        self,
        df: pd.DataFrame,
        batch_size: int = 1000,
        validate: bool = True
    ) -> int:
        """
        Load stock data into database.

        Args:
            df: DataFrame with stock data
            batch_size: Number of rows to insert per batch
            validate: Whether to validate data before loading

        Returns:
            Total number of rows inserted
        """
        if validate:
            df = self.validate_data(df)

        # Get unique symbols
        symbols = df['symbol'].unique()
        self.logger.info(f"Loading data for {len(symbols)} symbols")

        total_inserted = 0

        # Process each symbol
        for symbol in tqdm(symbols, desc="Loading symbols"):
            symbol_df = df[df['symbol'] == symbol].copy()

            try:
                rows_inserted = self.db.save_stock_data(symbol_df, symbol)
                total_inserted += rows_inserted

                # Log to database
                self.db.log_agent_activity(
                    agent_name='data_loader',
                    phase=0,
                    level='INFO',
                    message=f"Loaded {rows_inserted} rows for {symbol}",
                    context={'symbol': symbol, 'rows': rows_inserted}
                )

            except Exception as e:
                self.logger.error(f"Failed to load {symbol}: {e}")
                self.db.log_agent_activity(
                    agent_name='data_loader',
                    phase=0,
                    level='ERROR',
                    message=f"Failed to load {symbol}",
                    context={'symbol': symbol, 'error': str(e)}
                )

        self.logger.info(f"Successfully loaded {total_inserted} total rows")
        return total_inserted

    def get_data_summary(self) -> pd.DataFrame:
        """
        Get summary of data in database.

        Returns:
            DataFrame with summary statistics per symbol
        """
        query = """
            SELECT
                symbol,
                COUNT(*) as num_records,
                MIN(date) as start_date,
                MAX(date) as end_date,
                AVG(volume) as avg_volume,
                AVG(close) as avg_close
            FROM stock_data
            GROUP BY symbol
            ORDER BY symbol
        """

        results = self.db.execute_query(query)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(
            results,
            columns=['symbol', 'num_records', 'start_date', 'end_date', 'avg_volume', 'avg_close']
        )

        return df


def main():
    """Command-line interface for data loader"""
    parser = argparse.ArgumentParser(
        description='Load stock data from CSV into database'
    )

    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to input CSV file'
    )

    parser.add_argument(
        '--symbols-count',
        type=int,
        help='Limit to first N symbols (for testing)'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate data before loading (default: True)'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary of loaded data'
    )

    args = parser.parse_args()

    # Initialize loader
    loader = DataLoader()

    # Load CSV
    df = loader.load_csv(args.input)

    # Limit symbols if requested
    if args.symbols_count:
        symbols = df['symbol'].unique()[:args.symbols_count]
        df = df[df['symbol'].isin(symbols)]
        logger.info(f"Limited to {len(symbols)} symbols")

    # Load to database
    total_rows = loader.load_to_database(df, validate=args.validate)
    logger.info(f"Data load complete: {total_rows} rows inserted")

    # Show summary if requested
    if args.summary:
        summary = loader.get_data_summary()
        print("\n" + "="*80)
        print("DATA SUMMARY")
        print("="*80)
        print(summary.to_string(index=False))
        print(f"\nTotal symbols: {len(summary)}")
        print(f"Total records: {summary['num_records'].sum()}")
        print(f"Date range: {summary['start_date'].min()} to {summary['end_date'].max()}")


if __name__ == '__main__':
    main()
