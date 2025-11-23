"""
Linear Regression Candle Generation
Candles based on linear regression of price data
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class LinearRegressionCandleGenerator:
    """
    Generate Linear Regression candles.

    For each period, fits linear regression to close prices over a window.
    - LR_Close = predicted value from regression
    - LR_Open = LR value from previous period
    - LR_High = max of actual high and LR values
    - LR_Low = min of actual low and LR values
    """

    def __init__(self, window: int = 5):
        """
        Initialize Linear Regression candle generator.

        Args:
            window: Window size for linear regression (default: 5)
        """
        self.window = window
        self.logger = logging.getLogger(__name__)

    def generate(
        self,
        df: pd.DataFrame,
        aggregation_days: int = 1
    ) -> pd.DataFrame:
        """
        Generate Linear Regression candles.

        Args:
            df: DataFrame with columns [date, open, high, low, close, volume]
            aggregation_days: Number of days to aggregate (1, 2, 3, 4, 5)

        Returns:
            DataFrame with Linear Regression candles
        """
        if aggregation_days < 1:
            raise ValueError("aggregation_days must be >= 1")

        # Ensure date index
        if 'date' in df.columns:
            df = df.set_index('date')

        # First generate base LR candles
        lr_df = self._calculate_linear_regression(df.copy())

        # Then apply aggregation if needed
        if aggregation_days > 1:
            lr_df = self._aggregate(lr_df, aggregation_days)

        return lr_df

    def _calculate_linear_regression(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Linear Regression candles from regular OHLC data.

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with Linear Regression candles
        """
        lr_df = pd.DataFrame(index=df.index)

        # Calculate rolling linear regression on close prices
        lr_values = self._rolling_linear_regression(df['close'], self.window)

        # LR_Close = predicted value from regression
        lr_df['close'] = lr_values

        # LR_Open = LR value from previous period
        lr_df['open'] = lr_values.shift(1)

        # For first candle, use actual open
        lr_df.loc[lr_df.index[0], 'open'] = df.loc[df.index[0], 'open']

        # LR_High = max of actual high and LR values
        lr_df['high'] = pd.concat([
            df['high'],
            lr_df['open'],
            lr_df['close']
        ], axis=1).max(axis=1)

        # LR_Low = min of actual low and LR values
        lr_df['low'] = pd.concat([
            df['low'],
            lr_df['open'],
            lr_df['close']
        ], axis=1).min(axis=1)

        # Volume stays the same
        lr_df['volume'] = df['volume']

        # Reorder columns
        lr_df = lr_df[['open', 'high', 'low', 'close', 'volume']]

        # Drop initial NaN rows from regression window
        lr_df = lr_df.dropna()

        self.logger.info(
            f"Generated {len(lr_df)} Linear Regression candles "
            f"(window={self.window})"
        )

        return lr_df

    def _rolling_linear_regression(
        self,
        series: pd.Series,
        window: int
    ) -> pd.Series:
        """
        Calculate rolling linear regression values.

        For each window, fits a line to the data and returns the predicted
        value at the end of the window.

        Args:
            series: Price series to fit
            window: Window size for regression

        Returns:
            Series with regression predictions
        """
        predictions = []

        for i in range(len(series)):
            if i < window - 1:
                # Not enough data yet
                predictions.append(np.nan)
            else:
                # Get window of data
                window_data = series.iloc[i - window + 1:i + 1].values

                # Fit linear regression
                x = np.arange(window)
                slope, intercept, _, _, _ = stats.linregress(x, window_data)

                # Predict value at end of window (last position)
                prediction = slope * (window - 1) + intercept

                predictions.append(prediction)

        return pd.Series(predictions, index=series.index)

    def _aggregate(self, df: pd.DataFrame, n_days: int) -> pd.DataFrame:
        """
        Aggregate Linear Regression candles over N-day periods.

        Args:
            df: DataFrame with LR candles
            n_days: Number of days to aggregate

        Returns:
            Aggregated DataFrame
        """
        # Create rolling windows manually since 'first'/'last' don't work with pandas rolling
        rolling = df.rolling(window=n_days, min_periods=n_days)

        result = pd.DataFrame(index=df.index)
        result['open'] = rolling['open'].apply(lambda x: x.iloc[0], raw=False)
        result['high'] = rolling['high'].max()
        result['low'] = rolling['low'].min()
        result['close'] = rolling['close'].apply(lambda x: x.iloc[-1], raw=False)
        result['volume'] = rolling['volume'].sum()

        result = result.dropna()

        self.logger.info(
            f"Aggregated {len(result)} {n_days}-day Linear Regression candles "
            f"from {len(df)} daily candles"
        )

        return result


def generate_linear_regression_candles(
    df: pd.DataFrame,
    aggregation_days: int = 1,
    window: int = 5
) -> pd.DataFrame:
    """
    Convenience function to generate Linear Regression candles.

    Args:
        df: DataFrame with OHLC data
        aggregation_days: Number of days to aggregate
        window: Window size for linear regression

    Returns:
        DataFrame with Linear Regression candles
    """
    generator = LinearRegressionCandleGenerator(window=window)
    return generator.generate(df, aggregation_days)
