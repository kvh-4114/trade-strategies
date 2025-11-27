"""
Supertrend Indicator
Combines ATR (Average True Range) with price to create trend-following signals
"""

import backtrader as bt


class Supertrend(bt.Indicator):
    """
    Supertrend Indicator

    Trend-following indicator that uses ATR to create dynamic support/resistance bands.

    Buy Signal: Price crosses above Supertrend line (uptrend begins)
    Sell Signal: Price crosses below Supertrend line (downtrend begins)

    Formula:
        Basic Band = (High + Low) / 2
        Upper Band = Basic Band + (Multiplier × ATR)
        Lower Band = Basic Band - (Multiplier × ATR)

        Supertrend = Lower Band (in uptrend) or Upper Band (in downtrend)

    Parameters:
        period: ATR calculation period (default: 10)
        multiplier: ATR multiplier for band width (default: 3.0)
    """

    lines = ('supertrend', 'direction')  # direction: 1 = uptrend, -1 = downtrend

    params = (
        ('period', 10),        # ATR period
        ('multiplier', 3.0),   # ATR multiplier
    )

    plotinfo = dict(
        subplot=False,
        plotlinelabels=True
    )

    plotlines = dict(
        supertrend=dict(
            _name='Supertrend',
            color='green',
            width=2.0
        )
    )

    def __init__(self):
        # Calculate ATR
        self.atr = bt.indicators.AverageTrueRange(
            self.data,
            period=self.params.period
        )

        # Basic band (HL/2)
        self.basic_band = (self.data.high + self.data.low) / 2

        # Initialize for calculation
        self.addminperiod(self.params.period)

    def next(self):
        """Calculate Supertrend value for current bar."""

        # Calculate upper and lower bands
        upper_band = self.basic_band[0] + (self.params.multiplier * self.atr[0])
        lower_band = self.basic_band[0] - (self.params.multiplier * self.atr[0])

        # Get previous values (or initialize)
        if len(self) == 1:
            # First bar - initialize
            prev_supertrend = lower_band
            prev_direction = 1
        else:
            prev_supertrend = self.supertrend[-1]
            prev_direction = self.direction[-1]

        # Determine current direction and supertrend value
        # Uptrend logic
        if prev_direction == 1:
            # Stay in uptrend if price stays above lower band
            if self.data.close[0] > lower_band:
                self.direction[0] = 1
                # Keep supertrend at lower band, but don't let it decrease
                self.supertrend[0] = max(lower_band, prev_supertrend)
            else:
                # Switch to downtrend
                self.direction[0] = -1
                self.supertrend[0] = upper_band

        # Downtrend logic
        else:
            # Stay in downtrend if price stays below upper band
            if self.data.close[0] < upper_band:
                self.direction[0] = -1
                # Keep supertrend at upper band, but don't let it increase
                self.supertrend[0] = min(upper_band, prev_supertrend)
            else:
                # Switch to uptrend
                self.direction[0] = 1
                self.supertrend[0] = lower_band
