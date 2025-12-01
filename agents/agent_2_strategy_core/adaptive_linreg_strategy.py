"""
Adaptive Linear Regression Strategy

Multi-regime strategy that:
1. Detects market regime (trending vs choppy) using R²
2. Measures trend strength using multi-timeframe slopes
3. Sizes positions based on confidence
4. Uses dynamic stops based on regime
5. Exits early when momentum fades

Designed to work in 2023-2025 markets (rapid regime changes).
"""
import backtrader as bt
from .linear_regression_indicators import (
    LinearRegressionSlope,
    LinearRegressionR2,
    MultiTimeframeSlope
)


class AdaptiveLinRegStrategy(bt.Strategy):
    """
    Adaptive strategy using linear regression for regime detection and timing.

    Key features:
    - R² regime detection (strong trend / weak trend / choppy)
    - Multi-timeframe slope alignment
    - Acceleration detection (slope increasing)
    - Adaptive position sizing (full / half / zero)
    - Dynamic stop losses (regime-dependent)
    """

    params = (
        # Linear regression periods
        ('lr_short', 10),      # Short-term slope
        ('lr_medium', 20),     # Medium-term slope
        ('lr_long', 50),       # Long-term slope

        # Regime detection thresholds (R²)
        ('r2_strong_trend', 0.7),   # R² > 0.7 = strong trend
        ('r2_weak_trend', 0.4),     # R² > 0.4 = weak trend
                                    # R² < 0.4 = choppy (avoid)

        # Stop loss multipliers (ATR-based)
        ('stop_mult_strong', 3.0),  # Wide stop in strong trend
        ('stop_mult_weak', 1.5),    # Tight stop in weak trend
        ('stop_mult_default', 2.0), # Default

        # Position sizing
        ('max_position_pct', 0.95), # Max % of capital per trade
        ('weak_position_mult', 0.5), # Multiplier for weak trends

        # Minimum slope threshold (avoid tiny slopes)
        ('min_slope', 0.001),       # Minimum absolute slope to consider

        # Logging
        ('log_trades', False),
        ('log_regime', False),
    )

    def __init__(self):
        # Multi-timeframe slopes
        self.mtf_slope = MultiTimeframeSlope(
            self.data,
            period_short=self.params.lr_short,
            period_medium=self.params.lr_medium,
            period_long=self.params.lr_long
        )

        # R² for regime detection
        self.r_squared = LinearRegressionR2(
            self.data,
            period=self.params.lr_medium
        )

        # ATR for stops
        self.atr = bt.indicators.ATR(self.data, period=14)

        # Track state
        self.order = None
        self.stop_price = None
        self.entry_regime = None
        self.trade_count = 0

    def get_regime(self):
        """
        Detect market regime based on R².

        Returns: 'strong_trend', 'weak_trend', or 'choppy'
        """
        r2 = self.r_squared[0]

        if r2 >= self.params.r2_strong_trend:
            return 'strong_trend'
        elif r2 >= self.params.r2_weak_trend:
            return 'weak_trend'
        else:
            return 'choppy'

    def is_trend_aligned(self):
        """
        Check if all timeframes agree on direction.

        Returns: True if short, medium, and long slopes all positive
        """
        return (
            self.mtf_slope.slope_short[0] > self.params.min_slope and
            self.mtf_slope.slope_medium[0] > self.params.min_slope and
            self.mtf_slope.slope_long[0] > self.params.min_slope
        )

    def is_accelerating(self):
        """
        Check if short-term slope exceeds medium-term (acceleration).

        Returns: True if accelerating upward
        """
        return self.mtf_slope.acceleration[0] > 0

    def calculate_position_size(self, multiplier=1.0):
        """
        Calculate position size based on regime confidence.

        Args:
            multiplier: 0.5 for weak trends, 1.0 for strong trends

        Returns: Number of shares to buy
        """
        cash = self.broker.get_cash()
        position_value = cash * self.params.max_position_pct * multiplier
        price = self.data.close[0]

        if price > 0:
            size = int(position_value / price)
            return max(0, size)
        return 0

    def calculate_stop_loss(self, regime):
        """
        Calculate stop loss price based on regime.

        Args:
            regime: 'strong_trend', 'weak_trend', or 'choppy'

        Returns: Stop loss price
        """
        if regime == 'strong_trend':
            mult = self.params.stop_mult_strong
        elif regime == 'weak_trend':
            mult = self.params.stop_mult_weak
        else:
            mult = self.params.stop_mult_default

        stop = self.data.close[0] - (self.atr[0] * mult)
        return stop

    def next(self):
        # Don't trade if order pending
        if self.order:
            return

        # Get current regime
        regime = self.get_regime()
        aligned = self.is_trend_aligned()
        accelerating = self.is_accelerating()

        if self.params.log_regime and len(self) % 20 == 0:
            print(f'{self.data.datetime.date(0)}: Regime={regime}, R²={self.r_squared[0]:.2f}, '
                  f'Aligned={aligned}, Accel={accelerating}')

        # === ENTRY LOGIC ===
        if not self.position:
            entry_signal = False
            position_mult = 1.0

            if regime == 'strong_trend' and aligned and accelerating:
                # Perfect setup: strong trend + alignment + acceleration
                entry_signal = True
                position_mult = 1.0
                if self.params.log_trades:
                    print(f'{self.data.datetime.date(0)}: STRONG TREND ENTRY - Full position')

            elif regime == 'weak_trend' and aligned:
                # Acceptable setup: weak trend but aligned
                entry_signal = True
                position_mult = self.params.weak_position_mult
                if self.params.log_trades:
                    print(f'{self.data.datetime.date(0)}: WEAK TREND ENTRY - Half position')

            elif regime == 'choppy':
                # Stay out - choppy market
                if self.params.log_trades and len(self) % 50 == 0:
                    print(f'{self.data.datetime.date(0)}: CHOPPY - Staying in cash')

            if entry_signal:
                size = self.calculate_position_size(position_mult)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_regime = regime
                    self.stop_price = self.calculate_stop_loss(regime)
                    self.trade_count += 1

        # === EXIT LOGIC ===
        else:
            exit_signal = False
            exit_reason = None

            # 1. Stop loss hit
            if self.data.close[0] <= self.stop_price:
                exit_signal = True
                exit_reason = 'STOP_LOSS'

            # 2. Regime changed to choppy
            elif regime == 'choppy':
                exit_signal = True
                exit_reason = 'REGIME_CHOPPY'

            # 3. Trend no longer aligned
            elif not aligned:
                exit_signal = True
                exit_reason = 'MISALIGNED'

            # 4. Momentum fading (not accelerating and regime weakening)
            elif not accelerating and regime == 'weak_trend':
                exit_signal = True
                exit_reason = 'MOMENTUM_FADE'

            # 5. Medium-term slope turning negative (early reversal detection)
            elif self.mtf_slope.slope_medium[0] < 0:
                exit_signal = True
                exit_reason = 'REVERSAL'

            if exit_signal:
                self.order = self.sell(size=self.position.size)
                if self.params.log_trades:
                    pnl_pct = ((self.data.close[0] / self.position.price) - 1) * 100
                    print(f'{self.data.datetime.date(0)}: EXIT - {exit_reason}, '
                          f'PnL: {pnl_pct:+.1f}%')

                self.stop_price = None
                self.entry_regime = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        if self.params.log_trades:
            print(f'Trade #{self.trade_count} closed: PnL ${trade.pnl:.2f}')


class ConservativeLinRegStrategy(AdaptiveLinRegStrategy):
    """
    More conservative version - only trades strong trends.

    Good for:
    - Risk-averse traders
    - Testing if being selective improves returns
    - Periods of high uncertainty
    """
    params = (
        # Stricter regime thresholds
        ('r2_strong_trend', 0.8),   # Higher bar for "strong"
        ('r2_weak_trend', 0.6),     # Higher bar for "weak"

        # Require acceleration for entry
        ('require_accel', True),

        # Tighter stops
        ('stop_mult_strong', 2.5),
        ('stop_mult_weak', 1.2),
    )

    def next(self):
        if self.order:
            return

        regime = self.get_regime()
        aligned = self.is_trend_aligned()
        accelerating = self.is_accelerating()

        # ONLY trade strong trends with acceleration
        if not self.position:
            if regime == 'strong_trend' and aligned and accelerating:
                size = self.calculate_position_size(1.0)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_regime = regime
                    self.stop_price = self.calculate_stop_loss(regime)
                    self.trade_count += 1
        else:
            # Same exit logic as parent
            exit_signal = False

            if (self.data.close[0] <= self.stop_price or
                regime == 'choppy' or
                not aligned or
                self.mtf_slope.slope_medium[0] < 0):
                exit_signal = True

            if exit_signal:
                self.order = self.sell(size=self.position.size)
                self.stop_price = None
                self.entry_regime = None


class AggressiveLinRegStrategy(AdaptiveLinRegStrategy):
    """
    More aggressive version - trades weak trends too.

    Good for:
    - Maximum capture of all moves
    - Bull markets
    - Testing upper bounds of strategy
    """
    params = (
        # More lenient thresholds
        ('r2_strong_trend', 0.6),   # Lower bar
        ('r2_weak_trend', 0.3),     # Lower bar

        # Larger positions
        ('weak_position_mult', 0.75),  # 75% instead of 50%

        # Wider stops
        ('stop_mult_strong', 4.0),
        ('stop_mult_weak', 2.0),
    )

    def next(self):
        if self.order:
            return

        regime = self.get_regime()
        aligned = self.is_trend_aligned()

        # Trade both strong AND weak trends if aligned
        if not self.position:
            if regime == 'strong_trend' and aligned:
                size = self.calculate_position_size(1.0)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_regime = regime
                    self.stop_price = self.calculate_stop_loss(regime)
                    self.trade_count += 1

            elif regime == 'weak_trend' and aligned:
                size = self.calculate_position_size(self.params.weak_position_mult)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_regime = regime
                    self.stop_price = self.calculate_stop_loss(regime)
                    self.trade_count += 1
        else:
            # Slightly more lenient exits
            exit_signal = False

            if (self.data.close[0] <= self.stop_price or
                regime == 'choppy' or
                not aligned):
                exit_signal = True

            if exit_signal:
                self.order = self.sell(size=self.position.size)
                self.stop_price = None
                self.entry_regime = None
