"""
Main Candle Generator
Orchestrates generation of all candle types (Regular, Heiken Ashi, Linear Regression)
for all aggregation periods (1-5 days)
"""

import pandas as pd
from typing import List, Tuple, Optional, Dict
import logging
from tqdm import tqdm

from agents.agent_1_data_candles.regular_candles import generate_regular_candles
from agents.agent_1_data_candles.heiken_ashi import generate_heiken_ashi_candles
from agents.agent_1_data_candles.linear_regression import generate_linear_regression_candles
from agents.agent_5_infrastructure.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class CandleGenerator:
    """
    Main candle generator for all types and aggregation periods.

    Generates 13 candle combinations per stock:
    - Regular: 1, 2, 3, 4, 5 day (5 combinations)
    - Heiken Ashi: 1, 2, 3, 4, 5 day (5 combinations)
    - Linear Regression: 1, 2, 3 day (3 combinations)
    """

    CANDLE_TYPES = ['regular', 'heiken_ashi', 'linear_regression']
    AGGREGATION_PERIODS = {
        'regular': [1, 2, 3, 4, 5],
        'heiken_ashi': [1, 2, 3, 4, 5],
        'linear_regression': [1, 2, 3, 4, 5]  # Using all 5 for completeness
    }

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize candle generator.

        Args:
            db_manager: Database manager instance (creates new if None)
        """
        self.db = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)

    def generate_all_candles(
        self,
        symbol: str,
        df: Optional[pd.DataFrame] = None,
        save_to_db: bool = True
    ) -> Dict[Tuple[str, int], pd.DataFrame]:
        """
        Generate all candle types and aggregations for a symbol.

        Args:
            symbol: Stock ticker symbol
            df: DataFrame with OHLC data (loads from DB if None)
            save_to_db: Whether to save results to database

        Returns:
            Dictionary mapping (candle_type, aggregation_days) to DataFrame
        """
        # Load data if not provided
        if df is None:
            self.logger.info(f"Loading data for {symbol} from database")
            df = self.db.load_stock_data(symbol)

            if df.empty:
                self.logger.warning(f"No data found for {symbol}")
                return {}

        self.logger.info(
            f"Generating all candles for {symbol} "
            f"({len(df)} daily records)"
        )

        results = {}

        # Generate each candle type
        for candle_type in self.CANDLE_TYPES:
            for agg_days in self.AGGREGATION_PERIODS[candle_type]:
                try:
                    # Generate candles
                    candles = self.generate_candles(
                        df=df,
                        candle_type=candle_type,
                        aggregation_days=agg_days
                    )

                    # Store result
                    results[(candle_type, agg_days)] = candles

                    # Save to database if requested
                    if save_to_db and not candles.empty:
                        rows = self.db.save_candles(
                            df=candles,
                            symbol=symbol,
                            candle_type=candle_type,
                            aggregation_days=agg_days
                        )
                        self.logger.info(
                            f"Saved {rows} {candle_type} "
                            f"{agg_days}-day candles for {symbol}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Failed to generate {candle_type} "
                        f"{agg_days}-day candles for {symbol}: {e}"
                    )
                    self.db.log_agent_activity(
                        agent_name='candle_generator',
                        phase=1,
                        level='ERROR',
                        message=f"Failed to generate candles",
                        context={
                            'symbol': symbol,
                            'candle_type': candle_type,
                            'aggregation_days': agg_days,
                            'error': str(e)
                        }
                    )

        self.logger.info(
            f"Generated {len(results)} candle combinations for {symbol}"
        )

        return results

    def generate_candles(
        self,
        df: pd.DataFrame,
        candle_type: str,
        aggregation_days: int
    ) -> pd.DataFrame:
        """
        Generate specific candle type.

        Args:
            df: DataFrame with OHLC data
            candle_type: 'regular', 'heiken_ashi', or 'linear_regression'
            aggregation_days: Number of days to aggregate (1-5)

        Returns:
            DataFrame with generated candles
        """
        if candle_type == 'regular':
            return generate_regular_candles(df, aggregation_days)

        elif candle_type == 'heiken_ashi':
            return generate_heiken_ashi_candles(df, aggregation_days)

        elif candle_type == 'linear_regression':
            return generate_linear_regression_candles(
                df,
                aggregation_days,
                window=5
            )

        else:
            raise ValueError(f"Unknown candle type: {candle_type}")

    def generate_for_all_symbols(
        self,
        symbols: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> int:
        """
        Generate all candles for multiple symbols.

        Args:
            symbols: List of symbols (loads from DB if None)
            limit: Limit to first N symbols (for testing)

        Returns:
            Number of symbols processed
        """
        # Get symbols if not provided
        if symbols is None:
            self.logger.info("Loading available symbols from database")
            symbols = self.db.get_available_symbols()

        if limit:
            symbols = symbols[:limit]

        self.logger.info(f"Generating candles for {len(symbols)} symbols")

        processed = 0
        failed = 0

        # Process each symbol
        for symbol in tqdm(symbols, desc="Generating candles"):
            try:
                self.generate_all_candles(symbol, save_to_db=True)
                processed += 1

                # Log success
                self.db.log_agent_activity(
                    agent_name='candle_generator',
                    phase=1,
                    level='INFO',
                    message=f"Generated all candles for {symbol}",
                    context={'symbol': symbol, 'success': True}
                )

            except Exception as e:
                failed += 1
                self.logger.error(f"Failed to process {symbol}: {e}")

                # Log failure
                self.db.log_agent_activity(
                    agent_name='candle_generator',
                    phase=1,
                    level='ERROR',
                    message=f"Failed to generate candles for {symbol}",
                    context={'symbol': symbol, 'error': str(e)}
                )

        self.logger.info(
            f"Candle generation complete: "
            f"{processed} successful, {failed} failed"
        )

        return processed

    def get_candle_summary(self) -> pd.DataFrame:
        """
        Get summary of generated candles in database.

        Returns:
            DataFrame with summary statistics
        """
        query = """
            SELECT
                candle_type,
                aggregation_days,
                COUNT(DISTINCT symbol) as num_symbols,
                COUNT(*) as num_candles,
                MIN(date) as start_date,
                MAX(date) as end_date
            FROM candles
            GROUP BY candle_type, aggregation_days
            ORDER BY candle_type, aggregation_days
        """

        results = self.db.execute_query(query)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(
            results,
            columns=[
                'candle_type', 'aggregation_days', 'num_symbols',
                'num_candles', 'start_date', 'end_date'
            ]
        )

        return df


# Convenience functions
def generate_all_candles_for_symbol(
    symbol: str,
    df: Optional[pd.DataFrame] = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[Tuple[str, int], pd.DataFrame]:
    """
    Generate all candle types for a symbol.

    Args:
        symbol: Stock ticker symbol
        df: DataFrame with OHLC data (loads from DB if None)
        db_manager: Database manager instance

    Returns:
        Dictionary of candle DataFrames
    """
    generator = CandleGenerator(db_manager)
    return generator.generate_all_candles(symbol, df)


if __name__ == '__main__':
    # Command-line interface
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate candles for stocks'
    )

    parser.add_argument(
        '--symbol',
        type=str,
        help='Single symbol to process'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all symbols in database'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit to first N symbols'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary of generated candles'
    )

    args = parser.parse_args()

    generator = CandleGenerator()

    if args.summary:
        summary = generator.get_candle_summary()
        print("\n" + "="*80)
        print("CANDLE GENERATION SUMMARY")
        print("="*80)
        print(summary.to_string(index=False))

    elif args.symbol:
        generator.generate_all_candles(args.symbol)

    elif args.all:
        generator.generate_for_all_symbols(limit=args.limit)

    else:
        parser.print_help()
