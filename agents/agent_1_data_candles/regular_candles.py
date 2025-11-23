"""
Regular OHLC Candle Generation
Passthrough from stock_data with optional aggregation
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RegularCandleGenerator:
    """Generate regular OHLC candles from stock data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate(
        self,
        df: pd.DataFrame,
        aggregation_days: int = 1
    ) -> pd.DataFrame:
        """
        Generate regular OHLC candles.

        For aggregation_days=1, this is a passthrough.
        For aggregation_days>1, aggregates N-day periods.

        Args:
            df: DataFrame with columns [date, open, high, low, close, volume]
            aggregation_days: Number of days to aggregate (1, 2, 3, 4, 5)

        Returns:
            DataFrame with regular OHLC candles
        """
        if aggregation_days < 1:
            raise ValueError("aggregation_days must be >= 1")

        # Ensure date index
        if 'date' in df.columns:
            df = df.set_index('date')

        if aggregation_days == 1:
            # No aggregation needed - passthrough
            return df[['open', 'high', 'low', 'close', 'volume']].copy()

        # Aggregate multiple days
        return self._aggregate(df, aggregation_days)

    def _aggregate(self, df: pd.DataFrame, n_days: int) -> pd.DataFrame:
        """
        Aggregate OHLC data over N-day periods.

        Rules:
        - Open: First open in period
        - High: Maximum high in period
        - Low: Minimum low in period
        - Close: Last close in period
        - Volume: Sum of volume in period

        Args:
            df: DataFrame with OHLC data
            n_days: Number of days to aggregate

        Returns:
            Aggregated DataFrame
        """
        # Resample to N-day periods
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        # Use rolling window to create overlapping N-day candles
        # This maintains daily granularity but each candle represents N days
        result = df.rolling(window=n_days, min_periods=n_days).agg(agg_dict)

        # Drop NaN rows from initial periods
        result = result.dropna()

        self.logger.info(
            f"Generated {len(result)} {n_days}-day regular candles "
            f"from {len(df)} daily candles"
        )

        return result


def generate_regular_candles(
    df: pd.DataFrame,
    aggregation_days: int = 1
) -> pd.DataFrame:
    """
    Convenience function to generate regular candles.

    Args:
        df: DataFrame with OHLC data
        aggregation_days: Number of days to aggregate

    Returns:
        DataFrame with regular candles
    """
    generator = RegularCandleGenerator()
    return generator.generate(df, aggregation_days)
