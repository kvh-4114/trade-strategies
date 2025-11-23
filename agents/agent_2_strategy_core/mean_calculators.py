"""
Mean Calculators for Mean Reversion Strategy
Implements: SMA, EMA, Linear Regression, and VWAP
"""

import backtrader as bt
import numpy as np
from scipy import stats


class SMA(bt.Indicator):
    """Simple Moving Average"""
    lines = ('sma',)
    params = (('period', 20),)

    def __init__(self):
        self.lines.sma = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.period
        )


class EMA(bt.Indicator):
    """Exponential Moving Average"""
    lines = ('ema',)
    params = (('period', 20),)

    def __init__(self):
        self.lines.ema = bt.indicators.ExponentialMovingAverage(
            self.data.close,
            period=self.params.period
        )


class LinRegMean(bt.Indicator):
    """
    Linear Regression Mean
    Calculates the linear regression line over a lookback period
    """
    lines = ('linreg',)
    params = (('period', 20),)

    def __init__(self):
        self.lines.linreg = bt.indicators.LinearRegression(
            self.data.close,
            period=self.params.period
        )


class VWAP(bt.Indicator):
    """
    Volume Weighted Average Price
    VWAP = Sum(Price × Volume) / Sum(Volume)
    Using typical price: (High + Low + Close) / 3
    """
    lines = ('vwap',)
    params = (('period', 20),)

    def __init__(self):
        # Calculate typical price
        typical_price = (self.data.high + self.data.low + self.data.close) / 3.0

        # Calculate VWAP using SumN for rolling window
        pv = typical_price * self.data.volume
        self.lines.vwap = bt.indicators.SumN(pv, period=self.params.period) / \
                          bt.indicators.SumN(self.data.volume, period=self.params.period)


def get_mean_indicator(mean_type: str, period: int):
    """
    Factory function to get the appropriate mean indicator.

    Args:
        mean_type: 'SMA', 'EMA', 'LinReg', or 'VWAP'
        period: Lookback period

    Returns:
        Mean indicator class with period set
    """
    indicators = {
        'SMA': SMA,
        'EMA': EMA,
        'LinReg': LinRegMean,
        'VWAP': VWAP
    }

    if mean_type not in indicators:
        raise ValueError(f"Unknown mean type: {mean_type}. Choose from {list(indicators.keys())}")

    return indicators[mean_type]
