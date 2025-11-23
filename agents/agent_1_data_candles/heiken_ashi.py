"""
Heiken Ashi Candle Generation
Smoothed candles that reduce noise and highlight trends
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class HeikenAshiCandleGenerator:
    """
    Generate Heiken Ashi candles.

    Heiken Ashi formulas (from blueprint):
    HA_Close = (Open + High + Low + Close) / 4
    HA_Open = (Previous HA_Open + Previous HA_Close) / 2
    HA_High = max(High, HA_Open, HA_Close)
    HA_Low = min(Low, HA_Open, HA_Close)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate(
        self,
        df: pd.DataFrame,
        aggregation_days: int = 1
    ) -> pd.DataFrame:
        """
        Generate Heiken Ashi candles.

        Args:
            df: DataFrame with columns [date, open, high, low, close, volume]
            aggregation_days: Number of days to aggregate (1, 2, 3, 4, 5)

        Returns:
            DataFrame with Heiken Ashi candles
        """
        if aggregation_days < 1:
            raise ValueError("aggregation_days must be >= 1")

        # Ensure date index
        if 'date' in df.columns:
            df = df.set_index('date')

        # First generate base HA candles
        ha_df = self._calculate_heiken_ashi(df.copy())

        # Then apply aggregation if needed
        if aggregation_days > 1:
            ha_df = self._aggregate(ha_df, aggregation_days)

        return ha_df

    def _calculate_heiken_ashi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Heiken Ashi candles from regular OHLC data.

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with Heiken Ashi candles
        """
        ha_df = pd.DataFrame(index=df.index)

        # HA_Close = (Open + High + Low + Close) / 4
        ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

        # Initialize HA_Open for first row
        # Common practice: use regular candle's open for first HA candle
        ha_df['open'] = np.nan
        ha_df.loc[ha_df.index[0], 'open'] = df.loc[df.index[0], 'open']

        # HA_Open = (Previous HA_Open + Previous HA_Close) / 2
        for i in range(1, len(ha_df)):
            ha_df.iloc[i, ha_df.columns.get_loc('open')] = (
                (ha_df.iloc[i-1]['open'] + ha_df.iloc[i-1]['close']) / 2
            )

        # HA_High = max(High, HA_Open, HA_Close)
        ha_df['high'] = df[['high']].join(ha_df[['open', 'close']]).max(axis=1)

        # HA_Low = min(Low, HA_Open, HA_Close)
        ha_df['low'] = df[['low']].join(ha_df[['open', 'close']]).min(axis=1)

        # Volume stays the same
        ha_df['volume'] = df['volume']

        # Reorder columns to match standard OHLCV
        ha_df = ha_df[['open', 'high', 'low', 'close', 'volume']]

        self.logger.info(f"Generated {len(ha_df)} Heiken Ashi candles")

        return ha_df

    def _aggregate(self, df: pd.DataFrame, n_days: int) -> pd.DataFrame:
        """
        Aggregate Heiken Ashi candles over N-day periods.

        Args:
            df: DataFrame with HA candles
            n_days: Number of days to aggregate

        Returns:
            Aggregated DataFrame
        """
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        result = df.rolling(window=n_days, min_periods=n_days).agg(agg_dict)
        result = result.dropna()

        self.logger.info(
            f"Aggregated {len(result)} {n_days}-day Heiken Ashi candles "
            f"from {len(df)} daily candles"
        )

        return result


def generate_heiken_ashi_candles(
    df: pd.DataFrame,
    aggregation_days: int = 1
) -> pd.DataFrame:
    """
    Convenience function to generate Heiken Ashi candles.

    Args:
        df: DataFrame with OHLC data
        aggregation_days: Number of days to aggregate

    Returns:
        DataFrame with Heiken Ashi candles
    """
    generator = HeikenAshiCandleGenerator()
    return generator.generate(df, aggregation_days)
