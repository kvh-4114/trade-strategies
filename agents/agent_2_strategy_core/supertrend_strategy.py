"""
Supertrend Trading Strategy
Trend-following strategy using Supertrend indicator
"""

import backtrader as bt
from agents.agent_2_strategy_core.supertrend import Supertrend


class SupertrendStrategy(bt.Strategy):
    """
    Supertrend Trend-Following Strategy

    Entry:
        - BUY: When Supertrend direction changes from -1 to 1 (uptrend starts)
        - Close is above Supertrend line

    Exit:
        - SELL: When Supertrend direction changes from 1 to -1 (downtrend starts)
        - Or when price crosses below Supertrend line
        - Optional: Stop loss or profit target

    Parameters:
        - atr_period: Period for ATR calculation (default: 10)
        - atr_multiplier: Multiplier for Supertrend bands (default: 3.0)
        - position_size: Dollar amount per position (default: 10000)
        - stop_loss_type: Type of stop loss ('none', 'fixed_pct', 'atr')
        - stop_loss_value: Stop loss value (% or ATR multiplier)
        - profit_target: Optional profit target in % (default: None)
    """

    params = (
        # Supertrend parameters
        ('atr_period', 10),
        ('atr_multiplier', 3.0),

        # Position sizing
        ('position_sizing', 'fixed'),
        ('position_size', 10000),

        # Risk management
        ('stop_loss_type', 'none'),      # 'none', 'fixed_pct', 'atr'
        ('stop_loss_value', None),       # -0.05 for -5%, or 2.0 for 2×ATR
        ('profit_target', None),         # 0.10 for +10% profit target

        # Logging
        ('log_trades', True),
    )

    def __init__(self):
        """Initialize strategy indicators and state"""

        # Supertrend indicator
        self.supertrend = Supertrend(
            self.data,
            period=self.params.atr_period,
            multiplier=self.params.atr_multiplier
        )

        # ATR for stop loss calculations
        if self.params.stop_loss_type == 'atr':
            self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

        # Track trade state
        self.entry_price = None
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

        # Check if we have a position
        if not self.position:
            # Entry logic: Enter when in uptrend (direction = 1)
            # Supertrend direction=1 means price is in uptrend above the indicator line
            if self.supertrend.direction[0] == 1:
                # Calculate position size
                size = self._calculate_position_size()

                # Place buy order
                self.order = self.buy(size=size)
                self.entry_price = self.data.close[0]

                if self.params.log_trades:
                    self.log(f'BUY SIGNAL: Supertrend uptrend (dir=1)')

        else:
            # Exit logic
            exit_signal = self._check_exit_conditions()

            if exit_signal:
                self.order = self.sell(size=self.position.size)

                if self.params.log_trades:
                    self.log(f'SELL SIGNAL: {exit_signal}')

    def _check_exit_conditions(self):
        """
        Check various exit conditions.

        Returns:
            String describing exit reason, or None
        """
        close = self.data.close[0]
        supertrend_value = self.supertrend.supertrend[0]
        direction = self.supertrend.direction[0]

        # Exit 1: Trend reversal (direction changes to downtrend)
        if len(self) > 1 and direction == -1 and self.supertrend.direction[-1] == 1:
            return "Trend reversal (downtrend started)"

        # Exit 2: Price crosses below Supertrend line
        if close < supertrend_value:
            return "Price below Supertrend"

        # Exit 3: Profit target
        if self.params.profit_target and self.entry_price:
            profit_pct = (close - self.entry_price) / self.entry_price
            if profit_pct >= self.params.profit_target:
                return f"Profit target reached ({profit_pct:.1%})"

        # Exit 4: Stop loss
        if self.entry_price:
            loss_pct = (close - self.entry_price) / self.entry_price

            if self.params.stop_loss_type == 'fixed_pct':
                if self.params.stop_loss_value and loss_pct <= self.params.stop_loss_value:
                    return f"Stop loss hit ({loss_pct:.1%})"

            elif self.params.stop_loss_type == 'atr':
                if self.params.stop_loss_value:
                    stop_distance = self.params.stop_loss_value * self.atr[0]
                    if close <= (self.entry_price - stop_distance):
                        return f"ATR stop loss hit"

        return None

    def _calculate_position_size(self):
        """
        Calculate position size based on sizing method.

        Returns:
            Number of shares to buy
        """
        price = self.data.close[0]

        if self.params.position_sizing == 'fixed':
            # Fixed dollar amount
            if price > 0:
                return int(self.params.position_size / price)
            return 0

        # Add other sizing methods here if needed
        return 0

    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                if self.params.log_trades:
                    self.log(
                        f'BUY EXECUTED: Price=${order.executed.price:.2f}, '
                        f'Cost=${order.executed.value:.2f}, '
                        f'Comm=${order.executed.comm:.2f}'
                    )
                self.entry_price = order.executed.price

            elif order.issell():
                if self.params.log_trades:
                    self.log(
                        f'SELL EXECUTED: Price=${order.executed.price:.2f}, '
                        f'Value=${order.executed.value:.2f}, '
                        f'Comm=${order.executed.comm:.2f}'
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
                f'TRADE #{self.trade_count} CLOSED: '
                f'PnL=${trade.pnl:.2f}, '
                f'Net=${trade.pnlcomm:.2f}'
            )

    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def stop(self):
        """Called when strategy finishes"""
        if self.params.log_trades:
            final_value = self.broker.getvalue()
            win_rate = self.winning_trades / max(self.trade_count, 1) * 100
            self.log(
                f'FINAL: Value=${final_value:.2f}, '
                f'Trades={self.trade_count}, '
                f'Win Rate={win_rate:.1f}%'
            )
