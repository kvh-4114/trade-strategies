"""
Standard Deviation Bands for Mean Reversion
Calculates upper and lower bands based on mean ± (threshold × stddev)
"""

import backtrader as bt


class StdDevBands(bt.Indicator):
    """
    Standard Deviation Bands

    Calculates:
    - Upper Band = Mean + (threshold × stddev)
    - Lower Band = Mean - (threshold × stddev)

    Lines:
        - upper: Upper band
        - lower: Lower band
        - middle: Mean line
    """
    lines = ('upper', 'lower', 'middle',)

    params = (
        ('mean', None),           # Mean indicator (required)
        ('stddev_period', 20),    # Period for standard deviation
        ('threshold', 2.0),       # Number of standard deviations
    )

    def __init__(self):
        # Mean line (from provided mean indicator)
        if self.params.mean is None:
            raise ValueError("mean parameter is required")

        self.lines.middle = self.params.mean

        # Calculate standard deviation
        self.stddev = bt.indicators.StandardDeviation(
            self.data.close,
            period=self.params.stddev_period
        )

        # Calculate bands
        deviation = self.stddev * self.params.threshold
        self.lines.upper = self.lines.middle + deviation
        self.lines.lower = self.lines.middle - deviation


class BollingerBands(bt.Indicator):
    """
    Bollinger Bands (standard implementation)

    Special case of StdDevBands using SMA as mean
    """
    lines = ('upper', 'lower', 'middle',)

    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )

    def __init__(self):
        self.lines.middle = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.period
        )

        self.stddev = bt.indicators.StandardDeviation(
            self.data.close,
            period=self.params.period
        )

        deviation = self.stddev * self.params.devfactor
        self.lines.upper = self.lines.middle + deviation
        self.lines.lower = self.lines.middle - deviation


def create_bands(mean_indicator, stddev_period: int = 20, threshold: float = 2.0):
    """
    Factory function to create standard deviation bands.

    Args:
        mean_indicator: Mean indicator instance (SMA, EMA, LinReg, VWAP)
        stddev_period: Period for standard deviation calculation
        threshold: Number of standard deviations for bands

    Returns:
        StdDevBands indicator
    """
    return StdDevBands(
        mean=mean_indicator,
        stddev_period=stddev_period,
        threshold=threshold
    )
