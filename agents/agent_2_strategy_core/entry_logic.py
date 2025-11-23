"""
Entry Logic for Mean Reversion Strategy
Different methods to trigger entry signals
"""


class EntryLogic:
    """Entry logic variations for mean reversion"""

    @staticmethod
    def close_below_band(close, lower_band):
        """
        Entry when close is below lower band.

        Args:
            close: Current close price
            lower_band: Lower band value

        Returns:
            True if entry signal triggered
        """
        return close < lower_band

    @staticmethod
    def touch_band(close, lower_band, tolerance=0.001):
        """
        Entry when close touches or crosses lower band.

        Args:
            close: Current close price
            lower_band: Lower band value
            tolerance: Tolerance for "touching" (fraction)

        Returns:
            True if entry signal triggered
        """
        threshold = lower_band * (1 + tolerance)
        return close <= threshold

    @staticmethod
    def consecutive_below(closes, lower_bands, n_periods=2):
        """
        Entry after N consecutive periods below band.

        Args:
            closes: List of recent close prices
            lower_bands: List of recent lower band values
            n_periods: Number of consecutive periods required

        Returns:
            True if entry signal triggered
        """
        if len(closes) < n_periods or len(lower_bands) < n_periods:
            return False

        for i in range(n_periods):
            if closes[-(i+1)] >= lower_bands[-(i+1)]:
                return False

        return True

    @staticmethod
    def percent_below_band(close, lower_band, min_percent=1.0):
        """
        Entry when price is at least X% below band.

        Args:
            close: Current close price
            lower_band: Lower band value
            min_percent: Minimum percent below band required

        Returns:
            True if entry signal triggered
        """
        if lower_band == 0:
            return False

        percent_below = ((lower_band - close) / lower_band) * 100
        return percent_below >= min_percent


class EntryManager:
    """
    Manages entry logic for strategies.

    Supports multiple entry types:
    - 'close_below': Close below lower band
    - 'touch': Touch or cross lower band
    - 'consecutive_2': 2 consecutive periods below
    - 'consecutive_3': 3 consecutive periods below
    - 'percent_below': X% below band
    """

    def __init__(self, entry_type='close_below', **kwargs):
        """
        Initialize entry manager.

        Args:
            entry_type: Type of entry logic
            **kwargs: Additional parameters for entry logic
        """
        self.entry_type = entry_type
        self.params = kwargs

    def check_entry(self, close, lower_band, history=None):
        """
        Check if entry conditions are met.

        Args:
            close: Current close price
            lower_band: Current lower band value
            history: Historical data (for consecutive checks)

        Returns:
            True if entry signal triggered
        """
        if self.entry_type == 'close_below':
            return EntryLogic.close_below_band(close, lower_band)

        elif self.entry_type == 'touch':
            tolerance = self.params.get('tolerance', 0.001)
            return EntryLogic.touch_band(close, lower_band, tolerance)

        elif self.entry_type == 'consecutive_2':
            if history is None:
                return False
            return EntryLogic.consecutive_below(
                history['closes'],
                history['lower_bands'],
                n_periods=2
            )

        elif self.entry_type == 'consecutive_3':
            if history is None:
                return False
            return EntryLogic.consecutive_below(
                history['closes'],
                history['lower_bands'],
                n_periods=3
            )

        elif self.entry_type == 'percent_below':
            min_percent = self.params.get('min_percent', 1.0)
            return EntryLogic.percent_below_band(close, lower_band, min_percent)

        else:
            raise ValueError(f"Unknown entry type: {self.entry_type}")
