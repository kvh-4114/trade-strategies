"""
Backtrader Data Feed - Agent 3 Component
Wraps candle data for use with Backtrader
"""

import backtrader as bt
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PandasDataFeed(bt.feeds.PandasData):
    """
    Custom Backtrader data feed from pandas DataFrame.

    Handles candle data loaded from database.
    """

    params = (
        ('datetime', None),  # Use index as datetime
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),  # Not used for stocks
    )


def create_data_feed(
    candle_df: pd.DataFrame,
    name: str = "Data",
    **kwargs
) -> PandasDataFeed:
    """
    Create a Backtrader data feed from candle DataFrame.

    Args:
        candle_df: DataFrame with candle data (date index, OHLCV columns)
        name: Name for the data feed
        **kwargs: Additional parameters for data feed

    Returns:
        BacktraderData

 feed instance
    """
    if candle_df.empty:
        raise ValueError("Cannot create data feed from empty DataFrame")

    # Ensure index is datetime
    if not isinstance(candle_df.index, pd.DatetimeIndex):
        logger.warning("Index is not DatetimeIndex, attempting conversion")
        candle_df.index = pd.to_datetime(candle_df.index)

    # Ensure required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in candle_df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Create data feed
    data = PandasDataFeed(
        dataname=candle_df,
        name=name,
        **kwargs
    )

    logger.info(f"Created data feed '{name}' with {len(candle_df)} bars")

    return data


def create_multiple_feeds(
    candles_dict: dict,
    **kwargs
) -> dict:
    """
    Create multiple data feeds from dictionary of candle DataFrames.

    Args:
        candles_dict: Dictionary mapping symbol -> DataFrame
        **kwargs: Additional parameters for data feeds

    Returns:
        Dictionary mapping symbol -> DataFeed
    """
    feeds = {}

    for symbol, candle_df in candles_dict.items():
        try:
            feed = create_data_feed(
                candle_df=candle_df,
                name=symbol,
                **kwargs
            )
            feeds[symbol] = feed

        except Exception as e:
            logger.error(f"Error creating data feed for {symbol}: {e}")

    logger.info(f"Created {len(feeds)} data feeds")

    return feeds


class MultiDataStrategy(bt.Strategy):
    """
    Base strategy class that can handle multiple data feeds.

    Useful for testing across multiple symbols simultaneously.
    """

    def __init__(self):
        super().__init__()
        self.data_names = [d._name for d in self.datas]
        logger.info(f"Initialized strategy with {len(self.datas)} data feeds")

    def get_data_by_name(self, name: str):
        """Get data feed by name."""
        for data in self.datas:
            if data._name == name:
                return data
        return None

    def log(self, txt, dt=None):
        """Logging function for strategy."""
        dt = dt or self.datas[0].datetime.date(0)
        logger.debug(f'{dt.isoformat()}: {txt}')
