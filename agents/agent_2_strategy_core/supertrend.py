"""
Supertrend Indicator
Combines ATR (Average True Range) with price to create trend-following signals
"""

import backtrader as bt


class Supertrend(bt.Indicator):
    """
    Supertrend Trend-Following Indicator

    Uses ATR to create dynamic support/resistance bands.
    Direction: 1 = uptrend, -1 = downtrend

    Parameters:
        period: ATR calculation period (default: 10)
        multiplier: ATR multiplier for band width (default: 3.0)
    """

    lines = ('supertrend', 'direction', 'final_upper', 'final_lower')

    params = (
        ('period', 10),
        ('multiplier', 3.0),
    )

    def __init__(self):
        # Calculate ATR
        self.atr = bt.indicators.AverageTrueRange(self.data, period=self.params.period)

        # Wait for ATR to be ready
        self.addminperiod(self.params.period)

    def next(self):
        """Calculate Supertrend using proven algorithm."""

        # Get current values
        high = self.data.high[0]
        low = self.data.low[0]
        close = self.data.close[0]
        atr = self.atr[0]

        # Calculate basic bands
        hl_avg = (high + low) / 2.0
        basic_upper = hl_avg + (self.params.multiplier * atr)
        basic_lower = hl_avg - (self.params.multiplier * atr)

        # Calculate final bands (with smoothing)
        if len(self) == 1:
            # First bar - initialize
            final_upper = basic_upper
            final_lower = basic_lower
        else:
            # Smooth the bands
            prev_final_upper = self.final_upper[-1]
            prev_final_lower = self.final_lower[-1]
            prev_close = self.data.close[-1]

            # Update final upper band
            if basic_upper < prev_final_upper or prev_close > prev_final_upper:
                final_upper = basic_upper
            else:
                final_upper = prev_final_upper

            # Update final lower band
            if basic_lower > prev_final_lower or prev_close < prev_final_lower:
                final_lower = basic_lower
            else:
                final_lower = prev_final_lower

        # Store final bands
        self.final_upper[0] = final_upper
        self.final_lower[0] = final_lower

        # Determine direction
        if len(self) == 1:
            # First bar - start in uptrend if close above lower band
            if close > final_lower:
                self.direction[0] = 1
                self.supertrend[0] = final_lower
                print(f"Bar 1: Initial direction = UP, close=${close:.2f} > final_lower=${final_lower:.2f}")
            else:
                self.direction[0] = -1
                self.supertrend[0] = final_upper
                print(f"Bar 1: Initial direction = DOWN, close=${close:.2f} <= final_lower=${final_lower:.2f}")
        else:
            # Use previous direction
            prev_direction = self.direction[-1]

            if prev_direction == -1:
                # Was in downtrend - switch to uptrend if close crosses above upper band
                if close > final_upper:
                    self.direction[0] = 1
                    self.supertrend[0] = final_lower
                    print(f"Bar {len(self)}: DOWN -> UP, close=${close:.2f} > upper=${final_upper:.2f}")
                else:
                    self.direction[0] = -1
                    self.supertrend[0] = final_upper
            else:
                # Was in uptrend - switch to downtrend if close crosses below lower band
                if close < final_lower:
                    self.direction[0] = -1
                    self.supertrend[0] = final_upper
                    print(f"Bar {len(self)}: UP -> DOWN, close=${close:.2f} < lower=${final_lower:.2f}")
                else:
                    self.direction[0] = 1
                    self.supertrend[0] = final_lower
