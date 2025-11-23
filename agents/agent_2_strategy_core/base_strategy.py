"""
Base Mean Reversion Strategy
Main Backtrader strategy implementing mean reversion logic
"""

import backtrader as bt
from agents.agent_2_strategy_core.mean_calculators import get_mean_indicator
from agents.agent_2_strategy_core.stddev_bands import StdDevBands


class MeanReversionStrategy(bt.Strategy):
    """
    Mean Reversion Trading Strategy

    Buys when price falls below lower band (mean - N×stddev)
    Sells when price returns to target level

    Configurable parameters for all strategy components
    """

    params = (
        # Candle configuration
        ('candle_type', 'regular'),
        ('aggregation_days', 1),

        # Mean calculation
        ('mean_type', 'SMA'),          # 'SMA', 'EMA', 'LinReg', 'VWAP'
        ('mean_lookback', 20),
        ('stddev_lookback', 20),
        ('entry_threshold', 2.0),       # StdDev for entry

        # Exit configuration
        ('exit_type', 'mean'),          # 'mean', 'opposite_band', 'profit_target', 'time_based'
        ('exit_threshold', None),       # For profit_target (%)
        ('exit_time_days', None),       # For time_based exit

        # Filters (for later phases)
        ('use_volume_filter', False),
        ('volume_threshold', 1.2),
        ('use_rsi_filter', False),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('use_trend_filter', False),
        ('trend_ma_period', 200),
        ('use_volatility_filter', False),

        # Position sizing & risk
        ('position_sizing', 'fixed'),   # 'fixed', 'volatility_adjusted', 'kelly'
        ('position_size', 10000),       # Dollar amount for fixed sizing
        ('stop_loss_type', 'none'),     # 'none', 'fixed_pct', 'atr', 'trailing'
        ('stop_loss_value', None),      # Percentage or ATR multiplier

        # Logging
        ('log_trades', True),
    )

    def __init__(self):
        """Initialize strategy indicators and state"""

        # Mean indicator
        mean_indicator_class = get_mean_indicator(
            self.params.mean_type,
            self.params.mean_lookback
        )
        self.mean = mean_indicator_class(
            self.data,
            period=self.params.mean_lookback
        )

        # Standard deviation bands
        self.bands = StdDevBands(
            mean=self.mean,
            stddev_period=self.params.stddev_lookback,
            threshold=self.params.entry_threshold
        )

        # Additional indicators for filters (if enabled)
        if self.params.use_rsi_filter:
            self.rsi = bt.indicators.RSI(self.data.close, period=14)

        if self.params.use_trend_filter:
            self.trend_ma = bt.indicators.SimpleMovingAverage(
                self.data.close,
                period=self.params.trend_ma_period
            )

        if self.params.use_volatility_filter:
            self.atr = bt.indicators.ATR(self.data, period=14)

        if self.params.use_volume_filter:
            self.volume_ma = bt.indicators.SimpleMovingAverage(
                self.data.volume,
                period=20
            )

        # Track trade state
        self.entry_price = None
        self.bars_in_trade = 0
        self.order = None

        # Track performance
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def next(self):
        """Main strategy logic called for each bar"""

        # Check for pending orders
        if self.order:
            return

        # Update bars in trade
        if self.position:
            self.bars_in_trade += 1

        # Check filters (if no position)
        if not self.position:
            if not self._check_filters():
                return

            # Entry logic: Buy when price below lower band
            if self.data.close[0] < self.bands.lower[0]:
                # Calculate position size
                size = self._calculate_position_size()

                # Place buy order
                self.order = self.buy(size=size)
                self.entry_price = self.data.close[0]
                self.bars_in_trade = 0

                if self.params.log_trades:
                    self.log(f'BUY CREATE, Price: {self.data.close[0]:.2f}, Size: {size}')

        # Exit logic
        else:
            exit_signal = self._check_exit_conditions()

            if exit_signal:
                self.order = self.sell(size=self.position.size)

                if self.params.log_trades:
                    self.log(f'SELL CREATE, Price: {self.data.close[0]:.2f}')

    def _check_filters(self):
        """
        Check if all filters pass.

        Returns:
            True if all active filters pass, False otherwise
        """
        # Volume filter
        if self.params.use_volume_filter:
            if self.data.volume[0] < self.volume_ma[0] * self.params.volume_threshold:
                return False

        # RSI filter (oversold for mean reversion)
        if self.params.use_rsi_filter:
            if self.rsi[0] > self.params.rsi_oversold:
                return False

        # Trend filter (only trade in direction of trend)
        if self.params.use_trend_filter:
            # For mean reversion, might want to trade against trend
            # or only in sideways markets
            # Simple version: only trade if near trend line
            pass

        return True

    def _check_exit_conditions(self):
        """
        Check exit conditions based on exit_type.

        Returns:
            True if exit conditions met
        """
        close = self.data.close[0]
        mean = self.bands.middle[0]
        upper_band = self.bands.upper[0]

        if self.params.exit_type == 'mean':
            # Exit when price returns to mean
            return close >= mean

        elif self.params.exit_type == 'opposite_band':
            # Exit when price reaches upper band
            return close >= upper_band

        elif self.params.exit_type == 'profit_target':
            # Exit at profit target
            if self.entry_price and self.params.exit_threshold:
                profit_pct = ((close - self.entry_price) / self.entry_price) * 100
                return profit_pct >= self.params.exit_threshold
            return False

        elif self.params.exit_type == 'time_based':
            # Exit after max holding period
            if self.params.exit_time_days:
                return self.bars_in_trade >= self.params.exit_time_days
            return False

        return False

    def _calculate_position_size(self):
        """
        Calculate position size based on sizing method.

        Returns:
            Number of shares to buy
        """
        if self.params.position_sizing == 'fixed':
            # Fixed dollar amount
            price = self.data.close[0]
            if price > 0:
                return int(self.params.position_size / price)
            return 0

        elif self.params.position_sizing == 'volatility_adjusted':
            # Adjust size based on volatility (ATR)
            # Higher volatility = smaller position
            if hasattr(self, 'atr'):
                price = self.data.close[0]
                atr_pct = (self.atr[0] / price) * 100
                adjusted_size = self.params.position_size / (1 + atr_pct/10)
                return int(adjusted_size / price)
            return int(self.params.position_size / self.data.close[0])

        elif self.params.position_sizing == 'kelly':
            # Kelly Criterion (simplified)
            # Would need historical win rate and avg win/loss
            # For now, use fixed sizing
            return int(self.params.position_size / self.data.close[0])

        return 0

    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                if self.params.log_trades:
                    self.log(
                        f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}'
                    )
                self.entry_price = order.executed.price

            elif order.issell():
                if self.params.log_trades:
                    self.log(
                        f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}'
                    )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.params.log_trades:
                self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """Handle trade notifications"""
        if not trade.isclosed:
            return

        self.trade_count += 1

        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        if self.params.log_trades:
            self.log(
                f'TRADE #{self.trade_count} CLOSED, '
                f'PnL: {trade.pnl:.2f}, '
                f'Net: {trade.pnlcomm:.2f}'
            )

    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def stop(self):
        """Called when strategy finishes"""
        if self.params.log_trades:
            final_value = self.broker.getvalue()
            self.log(
                f'FINAL VALUE: {final_value:.2f}, '
                f'Trades: {self.trade_count}, '
                f'Win Rate: {self.winning_trades/max(self.trade_count, 1)*100:.1f}%'
            )
