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
        hl_avg = (self.data.high[0] + self.data.low[0]) / 2.0
        atr = self.atr[0]

        basic_upper = hl_avg + (self.params.multiplier * atr)
        basic_lower = hl_avg - (self.params.multiplier * atr)

        # Step 2: Calculate final bands
        if len(self) == 1:
            # First bar - initialize
            final_upper = basic_upper
            final_lower = basic_lower
        else:
            # Update final upper band
            final_upper = basic_upper if (basic_upper < self.final_upper[-1] or
                                          self.data.close[-1] > self.final_upper[-1]) else self.final_upper[-1]

            # Update final lower band
            final_lower = basic_lower if (basic_lower > self.final_lower[-1] or
                                          self.data.close[-1] < self.final_lower[-1]) else self.final_lower[-1]

        # Store final bands
        self.final_upper[0] = final_upper
        self.final_lower[0] = final_lower

        # Debug: Print direction changes to verify they match manual calculation
        if len(self) > 1:
            if self.direction[0] != self.direction[-1]:
                print(f"Bar {len(self)}: DIRECTION CHANGE {self.direction[-1]:.0f} -> {self.direction[0]:.0f}, "
                      f"close=${close:.2f}, final_lower=${final_lower:.2f}, final_upper=${final_upper:.2f}")

        # Step 3: Determine Supertrend value and direction
        close = self.data.close[0]

        if len(self) == 1:
            # First bar - start in uptrend if close is above lower band
            if close > final_lower:
                self.direction[0] = 1
                self.supertrend[0] = final_lower
            else:
                self.direction[0] = -1
                self.supertrend[0] = final_upper
        else:
            # Use previous direction
            prev_direction = self.direction[-1]

            if prev_direction == -1:
                # Was in downtrend - switch to uptrend if close crosses above final_upper
                if close > final_upper:
                    self.direction[0] = 1
                    self.supertrend[0] = final_lower
                else:
                    self.direction[0] = -1
                    self.supertrend[0] = final_upper
            else:
                # Was in uptrend - switch to downtrend if close crosses below final_lower
                if close < final_lower:
                    self.direction[0] = -1
                    self.supertrend[0] = final_upper
                else:
                    self.direction[0] = 1
                    self.supertrend[0] = final_lower
