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

    lines = ('supertrend', 'direction', 'final_upper', 'final_lower')

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
        """Calculate Supertrend value for current bar using standard algorithm."""

        # Step 1: Calculate basic bands
        basic_upper = self.basic_band[0] + (self.params.multiplier * self.atr[0])
        basic_lower = self.basic_band[0] - (self.params.multiplier * self.atr[0])

        # Step 2: Calculate final bands (with smoothing)
        if len(self) == 1:
            # First bar - initialize
            self.final_upper[0] = basic_upper
            self.final_lower[0] = basic_lower
        else:
            prev_close = self.data.close[-1]

            # Final upper band: use new band if it decreased OR if previous close broke above previous final upper
            if basic_upper < self.final_upper[-1] or prev_close > self.final_upper[-1]:
                self.final_upper[0] = basic_upper
            else:
                self.final_upper[0] = self.final_upper[-1]

            # Final lower band: use new band if it increased OR if previous close broke below previous final lower
            if basic_lower > self.final_lower[-1] or prev_close < self.final_lower[-1]:
                self.final_lower[0] = basic_lower
            else:
                self.final_lower[0] = self.final_lower[-1]

        # Step 3: Determine direction based on current close vs final bands
        close = self.data.close[0]

        if len(self) == 1:
            # First bar - assume uptrend
            if close >= self.final_lower[0]:
                self.direction[0] = 1
                self.supertrend[0] = self.final_lower[0]
            else:
                self.direction[0] = -1
                self.supertrend[0] = self.final_upper[0]
        else:
            prev_direction = self.direction[-1]

            if prev_direction == 1:
                # Was in uptrend
                if close <= self.final_lower[0]:
                    # Close dropped below lower band - switch to downtrend
                    self.direction[0] = -1
                    self.supertrend[0] = self.final_upper[0]
                else:
                    # Stay in uptrend
                    self.direction[0] = 1
                    self.supertrend[0] = self.final_lower[0]
            else:
                # Was in downtrend
                if close >= self.final_upper[0]:
                    # Close rose above upper band - switch to uptrend
                    self.direction[0] = 1
                    self.supertrend[0] = self.final_lower[0]
                else:
                    # Stay in downtrend
                    self.direction[0] = -1
                    self.supertrend[0] = self.final_upper[0]
