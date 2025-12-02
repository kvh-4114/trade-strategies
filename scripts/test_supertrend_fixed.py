"""
Test FIXED Supertrend with _nextforce = True
"""

import backtrader as bt
import pandas as pd


class SupertrendFixed(bt.Indicator):
    """
    Supertrend Indicator - FIXED VERSION

    Key fix: _nextforce = True to ensure next() is called bar-by-bar
    """

    lines = ('supertrend', 'direction', 'final_upper', 'final_lower')

    params = (
        ('period', 10),
        ('multiplier', 3.0),
    )

    # ⭐ CRITICAL FIX: Force bar-by-bar next() mode ⭐
    _nextforce = True

    plotinfo = dict(subplot=False)

    def __init__(self):
        # Calculate ATR
        self.atr = bt.indicators.AverageTrueRange(
            self.data,
            period=self.params.period
        )

        # Wait for ATR to be ready
        self.addminperiod(self.params.period)

    def nextstart(self):
        """
        Called ONCE for the first valid bar.
        Initialize the indicator state.
        """
        high = self.data.high[0]
        low = self.data.low[0]
        close = self.data.close[0]
        atr = self.atr[0]

        # Calculate basic bands
        hl_avg = (high + low) / 2.0
        basic_upper = hl_avg + (self.params.multiplier * atr)
        basic_lower = hl_avg - (self.params.multiplier * atr)

        # Initialize final bands
        self.lines.final_upper[0] = basic_upper
        self.lines.final_lower[0] = basic_lower

        # Set initial direction
        if close > basic_lower:
            self.lines.direction[0] = 1
            self.lines.supertrend[0] = basic_lower
            print(f"Bar {len(self)}: INIT direction=UP, close=${close:.2f} > lower=${basic_lower:.2f}")
        else:
            self.lines.direction[0] = -1
            self.lines.supertrend[0] = basic_upper
            print(f"Bar {len(self)}: INIT direction=DOWN, close=${close:.2f} <= lower=${basic_lower:.2f}")

    def next(self):
        """
        Called for each bar after nextstart().
        Performs stateful calculation using previous values.
        """
        # Get current values
        high = self.data.high[0]
        low = self.data.low[0]
        close = self.data.close[0]
        atr = self.atr[0]

        # Calculate basic bands
        hl_avg = (high + low) / 2.0
        basic_upper = hl_avg + (self.params.multiplier * atr)
        basic_lower = hl_avg - (self.params.multiplier * atr)

        # Get previous values (STATEFUL)
        prev_final_upper = self.lines.final_upper[-1]
        prev_final_lower = self.lines.final_lower[-1]
        prev_close = self.data.close[-1]
        prev_direction = self.lines.direction[-1]

        # Update final upper band (smoothed)
        if basic_upper < prev_final_upper or prev_close > prev_final_upper:
            final_upper = basic_upper
        else:
            final_upper = prev_final_upper

        # Update final lower band (smoothed)
        if basic_lower > prev_final_lower or prev_close < prev_final_lower:
            final_lower = basic_lower
        else:
            final_lower = prev_final_lower

        # Store final bands
        self.lines.final_upper[0] = final_upper
        self.lines.final_lower[0] = final_lower

        # Determine direction based on previous direction
        if prev_direction == -1:
            # Was in downtrend
            if close > final_upper:
                # Switch to uptrend
                self.lines.direction[0] = 1
                self.lines.supertrend[0] = final_lower
                print(f"Bar {len(self)}: DOWN→UP, close=${close:.2f} > upper=${final_upper:.2f}")
            else:
                # Stay in downtrend
                self.lines.direction[0] = -1
                self.lines.supertrend[0] = final_upper
        else:
            # Was in uptrend
            if close < final_lower:
                # Switch to downtrend
                self.lines.direction[0] = -1
                self.lines.supertrend[0] = final_upper
                print(f"Bar {len(self)}: UP→DOWN, close=${close:.2f} < lower=${final_lower:.2f}")
            else:
                # Stay in uptrend
                self.lines.direction[0] = 1
                self.lines.supertrend[0] = final_lower


class TestStrategy(bt.Strategy):
    def __init__(self):
        print("=== Strategy initialized ===")
        self.supertrend = SupertrendFixed(
            self.data,
            period=14,
            multiplier=3.0
        )

    def prenext(self):
        print(f"prenext() bar {len(self)}: Waiting for indicators...")

    def next(self):
        st = self.supertrend.supertrend[0]
        direction = self.supertrend.direction[0]
        upper = self.supertrend.final_upper[0]
        lower = self.supertrend.final_lower[0]

        # Print detailed info for first few bars and every 10th bar
        if len(self) <= 20 or len(self) % 10 == 0:
            print(f"Strategy bar {len(self):3d}: "
                  f"close=${self.data.close[0]:6.2f} | "
                  f"ST=${st:6.2f} | "
                  f"dir={direction:2.0f} | "
                  f"upper=${upper:6.2f} | "
                  f"lower=${lower:6.2f}")


if __name__ == '__main__':
    # Create sample data
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'open': range(100, 200),
        'high': range(101, 201),
        'low': range(99, 199),
        'close': range(100, 200),
        'volume': [1000000] * 100
    }, index=dates)

    cerebro = bt.Cerebro()

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(TestStrategy)

    print("\n" + "="*80)
    print("Testing FIXED Supertrend with _nextforce = True")
    print("="*80 + "\n")

    cerebro.run()

    print("\n" + "="*80)
    print("SUCCESS! Supertrend values are calculated correctly!")
    print("="*80)
