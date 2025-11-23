"""
Exit Logic for Mean Reversion Strategy
Different methods to trigger exit signals
"""


class ExitLogic:
    """Exit logic variations for mean reversion"""

    @staticmethod
    def return_to_mean(close, mean):
        """
        Exit when price returns to mean (0 standard deviations).

        Args:
            close: Current close price
            mean: Mean value

        Returns:
            True if exit signal triggered
        """
        return close >= mean

    @staticmethod
    def opposite_band(close, upper_band):
        """
        Exit when price reaches opposite (upper) band.

        Args:
            close: Current close price
            upper_band: Upper band value

        Returns:
            True if exit signal triggered
        """
        return close >= upper_band

    @staticmethod
    def profit_target(entry_price, close, target_percent):
        """
        Exit when profit target reached.

        Args:
            entry_price: Entry price
            close: Current close price
            target_percent: Target profit percentage (e.g., 5.0 for 5%)

        Returns:
            True if exit signal triggered
        """
        if entry_price == 0:
            return False

        profit_pct = ((close - entry_price) / entry_price) * 100
        return profit_pct >= target_percent

    @staticmethod
    def time_based(bars_in_trade, max_bars):
        """
        Exit after maximum holding period.

        Args:
            bars_in_trade: Number of bars in current trade
            max_bars: Maximum bars to hold

        Returns:
            True if exit signal triggered
        """
        return bars_in_trade >= max_bars


class ExitManager:
    """
    Manages exit logic for strategies.

    Supports multiple exit types:
    - 'mean': Return to mean (0 StdDev)
    - 'opposite_band': Reach opposite (upper) band
    - 'profit_target': Fixed profit percentage
    - 'time_based': Maximum holding period
    """

    def __init__(self, exit_type='mean', **kwargs):
        """
        Initialize exit manager.

        Args:
            exit_type: Type of exit logic
            **kwargs: Additional parameters for exit logic
        """
        self.exit_type = exit_type
        self.params = kwargs

    def check_exit(self, close, mean, upper_band, entry_price=None, bars_in_trade=None):
        """
        Check if exit conditions are met.

        Args:
            close: Current close price
            mean: Current mean value
            upper_band: Current upper band value
            entry_price: Entry price (for profit target)
            bars_in_trade: Bars in trade (for time-based)

        Returns:
            True if exit signal triggered
        """
        if self.exit_type == 'mean':
            return ExitLogic.return_to_mean(close, mean)

        elif self.exit_type == 'opposite_band':
            return ExitLogic.opposite_band(close, upper_band)

        elif self.exit_type == 'profit_target':
            if entry_price is None:
                raise ValueError("entry_price required for profit_target exit")
            target_pct = self.params.get('target_percent', 5.0)
            return ExitLogic.profit_target(entry_price, close, target_pct)

        elif self.exit_type == 'time_based':
            if bars_in_trade is None:
                raise ValueError("bars_in_trade required for time_based exit")
            max_bars = self.params.get('max_bars', 20)
            return ExitLogic.time_based(bars_in_trade, max_bars)

        else:
            raise ValueError(f"Unknown exit type: {self.exit_type}")
