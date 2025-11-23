"""
Generate All Candle Types for Loaded Stock Data
Creates Regular, Heiken Ashi, and Linear Regression candles
"""

import os
import sys
import pandas as pd
import logging
from tqdm import tqdm
from datetime import datetime

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager
from agents.agent_1_data_candles.regular_candles import generate_regular_candles
from agents.agent_1_data_candles.heiken_ashi import generate_heiken_ashi_candles
from agents.agent_1_data_candles.linreg_candles import generate_linreg_candles

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_symbols(db_manager):
    """Get list of all symbols in database."""
    query = "SELECT DISTINCT symbol FROM stock_data ORDER BY symbol"
    results = db_manager.execute_query(query)
    return [row[0] for row in results]


def get_stock_data(db_manager, symbol):
    """
    Get stock data for a symbol from database.

    Args:
        db_manager: DatabaseManager instance
        symbol: Stock symbol

    Returns:
        DataFrame with OHLCV data
    """
    query = """
        SELECT date, open, high, low, close, volume
        FROM stock_data
        WHERE symbol = %s
        ORDER BY date
    """
    results = db_manager.execute_query(query, (symbol,))

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    return df


def save_candles_to_db(db_manager, symbol, candle_type, aggregation_days, candle_df):
    """
    Save candles to database.

    Args:
        db_manager: DatabaseManager instance
        symbol: Stock symbol
        candle_type: Type of candle (regular, heiken_ashi, linreg)
        aggregation_days: Number of days aggregated
        candle_df: DataFrame with candle data
    """
    if candle_df.empty:
        return 0

    # Reset index to get date as column
    df = candle_df.reset_index()

    inserted = 0
    for _, row in df.iterrows():
        query = """
            INSERT INTO candles (symbol, candle_type, aggregation_days, date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, candle_type, aggregation_days, date) DO UPDATE
            SET open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """

        params = (
            symbol,
            candle_type,
            aggregation_days,
            row['date'],
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            int(row['volume']) if 'volume' in row and pd.notna(row['volume']) else 0
        )

        db_manager.execute_query(query, params, fetch=False)
        inserted += 1

    return inserted


def generate_all_candles_for_symbol(db_manager, symbol, aggregation_days=[1, 2, 3, 4, 5]):
    """
    Generate all candle types for a single symbol.

    Args:
        db_manager: DatabaseManager instance
        symbol: Stock symbol
        aggregation_days: List of aggregation periods

    Returns:
        Dictionary with candle counts
    """
    # Get stock data
    stock_df = get_stock_data(db_manager, symbol)

    if stock_df.empty:
        logger.warning(f"No data for {symbol}")
        return {}

    results = {}

    # Generate each candle type
    for agg_days in aggregation_days:
        # Regular candles
        try:
            regular_df = generate_regular_candles(stock_df, aggregation_days=agg_days)
            count = save_candles_to_db(db_manager, symbol, 'regular', agg_days, regular_df)
            results[f'regular_{agg_days}d'] = count
        except Exception as e:
            logger.error(f"Error generating regular candles for {symbol} ({agg_days}d): {e}")
            results[f'regular_{agg_days}d'] = 0

        # Heiken Ashi candles
        try:
            ha_df = generate_heiken_ashi_candles(stock_df, aggregation_days=agg_days)
            count = save_candles_to_db(db_manager, symbol, 'heiken_ashi', agg_days, ha_df)
            results[f'heiken_ashi_{agg_days}d'] = count
        except Exception as e:
            logger.error(f"Error generating Heiken Ashi candles for {symbol} ({agg_days}d): {e}")
            results[f'heiken_ashi_{agg_days}d'] = 0

        # Linear Regression candles
        try:
            linreg_df = generate_linreg_candles(stock_df, aggregation_days=agg_days, window=14)
            count = save_candles_to_db(db_manager, symbol, 'linreg', agg_days, linreg_df)
            results[f'linreg_{agg_days}d'] = count
        except Exception as e:
            logger.error(f"Error generating LinReg candles for {symbol} ({agg_days}d): {e}")
            results[f'linreg_{agg_days}d'] = 0

    return results


def generate_all_candles(db_manager, symbols=None, aggregation_days=[1, 2, 3, 4, 5]):
    """
    Generate all candle types for all symbols.

    Args:
        db_manager: DatabaseManager instance
        symbols: List of symbols (if None, process all)
        aggregation_days: List of aggregation periods
    """
    # Get symbols
    if symbols is None:
        symbols = get_all_symbols(db_manager)

    logger.info(f"Generating candles for {len(symbols)} symbols")
    logger.info(f"Aggregation days: {aggregation_days}")
    logger.info(f"Candle types: Regular, Heiken Ashi, Linear Regression")

    total_candles = 0
    successful = 0
    failed = 0

    # Process each symbol
    for symbol in tqdm(symbols, desc="Generating candles"):
        try:
            results = generate_all_candles_for_symbol(db_manager, symbol, aggregation_days)

            if results:
                symbol_total = sum(results.values())
                total_candles += symbol_total
                successful += 1
                logger.info(f"✅ {symbol}: {symbol_total} candles generated")
            else:
                failed += 1
                logger.warning(f"⚠️  {symbol}: No candles generated")

        except Exception as e:
            logger.error(f"❌ {symbol}: {e}")
            failed += 1

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"CANDLE GENERATION SUMMARY:")
    logger.info(f"  Symbols processed: {len(symbols)}")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total candles generated: {total_candles:,}")
    logger.info(f"{'='*60}\n")

    return total_candles


def verify_candles(db_manager):
    """Verify candles were generated correctly."""
    logger.info("Verifying candles...")

    # Count by candle type
    query = """
        SELECT candle_type, aggregation_days, COUNT(*) as count
        FROM candles
        GROUP BY candle_type, aggregation_days
        ORDER BY candle_type, aggregation_days
    """
    results = db_manager.execute_query(query)

    print("\n" + "="*60)
    print("CANDLE VERIFICATION")
    print("="*60)
    print(f"{'Candle Type':<20} {'Aggregation':<15} {'Count'}")
    print("-"*60)

    for row in results:
        candle_type, agg_days, count = row
        print(f"{candle_type:<20} {agg_days}d{'':<12} {count:,}")

    # Count symbols
    query = "SELECT COUNT(DISTINCT symbol) FROM candles"
    result = db_manager.execute_query(query)
    symbol_count = result[0][0] if result else 0

    # Total candles
    query = "SELECT COUNT(*) FROM candles"
    result = db_manager.execute_query(query)
    total_candles = result[0][0] if result else 0

    print("-"*60)
    print(f"Total unique symbols: {symbol_count}")
    print(f"Total candles: {total_candles:,}")
    print("="*60 + "\n")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate candles for all stocks')
    parser.add_argument('--symbols', type=str, nargs='+', default=None,
                        help='Specific symbols to process (default: all)')
    parser.add_argument('--aggregation', type=int, nargs='+',
                        default=[1, 2, 3, 4, 5],
                        help='Aggregation days (default: 1 2 3 4 5)')
    parser.add_argument('--verify', action='store_true',
                        help='Verify candles after generation')

    args = parser.parse_args()

    # Initialize database
    logger.info("Connecting to RDS...")
    db = DatabaseManager()

    # Generate candles
    total = generate_all_candles(db, symbols=args.symbols, aggregation_days=args.aggregation)

    # Verify if requested
    if args.verify:
        verify_candles(db)

    db.close()
    logger.info("✅ Complete!")
