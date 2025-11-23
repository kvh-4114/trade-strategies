"""
Candle Loader - Agent 3 Component
Loads candle data from RDS and prepares it for backtesting
"""

import pandas as pd
import logging
from typing import List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CandleLoader:
    """
    Loads candle data from database for backtesting.

    Handles fetching specific candle types and symbols for strategy testing.
    """

    def __init__(self, db_manager):
        """
        Initialize candle loader.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    def load_candles(
        self,
        symbol: str,
        candle_type: str,
        aggregation_days: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load candles for a specific symbol and type.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            candle_type: Type of candle ('regular', 'heiken_ashi', 'linreg')
            aggregation_days: Aggregation period (1, 2, 3, 4, 5)
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            DataFrame with columns [date, open, high, low, close, volume]
        """
        # Build query
        query = """
            SELECT date, open, high, low, close, volume
            FROM candles
            WHERE symbol = %s
              AND candle_type = %s
              AND aggregation_days = %s
        """

        params = [symbol, candle_type, aggregation_days]

        # Add date filters if provided
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date"

        # Execute query
        results = self.db_manager.execute_query(query, tuple(params))

        if not results:
            self.logger.warning(
                f"No candles found for {symbol} "
                f"(type={candle_type}, agg={aggregation_days})"
            )
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(
            results,
            columns=['date', 'open', 'high', 'low', 'close', 'volume']
        )

        # Convert types
        df['date'] = pd.to_datetime(df['date'])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(int)

        # Set date as index
        df = df.set_index('date')

        self.logger.info(
            f"Loaded {len(df)} candles for {symbol} "
            f"({candle_type}, {aggregation_days}d)"
        )

        return df

    def load_multiple_symbols(
        self,
        symbols: List[str],
        candle_type: str,
        aggregation_days: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Load candles for multiple symbols.

        Args:
            symbols: List of stock symbols
            candle_type: Type of candle
            aggregation_days: Aggregation period
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dictionary mapping symbol -> DataFrame
        """
        results = {}

        for symbol in symbols:
            try:
                df = self.load_candles(
                    symbol=symbol,
                    candle_type=candle_type,
                    aggregation_days=aggregation_days,
                    start_date=start_date,
                    end_date=end_date
                )

                if not df.empty:
                    results[symbol] = df

            except Exception as e:
                self.logger.error(f"Error loading candles for {symbol}: {e}")

        self.logger.info(
            f"Loaded candles for {len(results)}/{len(symbols)} symbols"
        )

        return results

    def get_available_symbols(
        self,
        candle_type: Optional[str] = None,
        aggregation_days: Optional[int] = None
    ) -> List[str]:
        """
        Get list of symbols with available candles.

        Args:
            candle_type: Optional filter by candle type
            aggregation_days: Optional filter by aggregation

        Returns:
            List of available symbols
        """
        query = "SELECT DISTINCT symbol FROM candles"
        params = []

        conditions = []
        if candle_type:
            conditions.append("candle_type = %s")
            params.append(candle_type)

        if aggregation_days:
            conditions.append("aggregation_days = %s")
            params.append(aggregation_days)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY symbol"

        results = self.db_manager.execute_query(query, tuple(params) if params else None)

        symbols = [row[0] for row in results]

        self.logger.info(f"Found {len(symbols)} symbols with candles")

        return symbols

    def get_date_range(
        self,
        symbol: str,
        candle_type: str,
        aggregation_days: int
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Get date range for a specific candle series.

        Args:
            symbol: Stock symbol
            candle_type: Type of candle
            aggregation_days: Aggregation period

        Returns:
            Tuple of (min_date, max_date)
        """
        query = """
            SELECT MIN(date), MAX(date)
            FROM candles
            WHERE symbol = %s
              AND candle_type = %s
              AND aggregation_days = %s
        """

        results = self.db_manager.execute_query(
            query,
            (symbol, candle_type, aggregation_days)
        )

        if results and results[0][0]:
            return results[0]

        return None, None
