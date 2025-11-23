"""
Metrics Calculator for Strategy Performance Analysis
Calculates Sharpe, Sortino, Calmar, Drawdown, and other performance metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculate comprehensive performance metrics for trading strategies.

    Includes:
    - Risk-adjusted returns (Sharpe, Sortino, Calmar)
    - Drawdown analysis
    - Trade statistics
    - Risk metrics (VaR, CVaR)
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger(__name__)

    def calculate_all_metrics(
        self,
        equity_curve: pd.Series,
        trades: Optional[pd.DataFrame] = None,
        initial_capital: float = 100000
    ) -> Dict:
        """
        Calculate all performance metrics.

        Args:
            equity_curve: Series with equity values (index: dates)
            trades: DataFrame with trade details (optional)
            initial_capital: Starting capital

        Returns:
            Dictionary with all metrics
        """
        metrics = {}

        # Basic returns
        returns = equity_curve.pct_change().dropna()

        # Capital metrics
        metrics['initial_capital'] = initial_capital
        metrics['final_value'] = equity_curve.iloc[-1]
        metrics['total_return'] = (equity_curve.iloc[-1] - initial_capital) / initial_capital

        # Annualized return
        years = len(equity_curve) / 252  # Assuming daily data
        metrics['annualized_return'] = (1 + metrics['total_return']) ** (1/years) - 1

        # Risk-adjusted metrics
        metrics['sharpe_ratio'] = self.sharpe_ratio(returns)
        metrics['sortino_ratio'] = self.sortino_ratio(returns)

        # Drawdown metrics
        dd_metrics = self.drawdown_metrics(equity_curve)
        metrics.update(dd_metrics)

        # Calmar ratio
        if metrics['max_drawdown'] != 0:
            metrics['calmar_ratio'] = metrics['annualized_return'] / abs(metrics['max_drawdown'])
        else:
            metrics['calmar_ratio'] = 0.0

        # Recovery factor
        if metrics['max_drawdown'] != 0:
            metrics['recovery_factor'] = metrics['total_return'] / abs(metrics['max_drawdown'])
        else:
            metrics['recovery_factor'] = 0.0

        # Trade statistics (if trades provided)
        if trades is not None and len(trades) > 0:
            trade_stats = self.trade_statistics(trades)
            metrics.update(trade_stats)
        else:
            # Default trade stats
            metrics.update({
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'avg_trade': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'avg_holding_period': 0.0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            })

        # Risk metrics
        metrics['value_at_risk'] = self.value_at_risk(returns, confidence=0.95)
        metrics['conditional_var'] = self.conditional_var(returns, confidence=0.95)

        return metrics

    def sharpe_ratio(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe Ratio.

        Args:
            returns: Series of returns
            periods_per_year: Trading periods per year (252 for daily)

        Returns:
            Sharpe ratio
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / periods_per_year)

        if excess_returns.std() == 0:
            return 0.0

        sharpe = np.sqrt(periods_per_year) * (excess_returns.mean() / excess_returns.std())
        return float(sharpe)

    def sortino_ratio(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """
        Calculate Sortino Ratio (uses downside deviation instead of total std).

        Args:
            returns: Series of returns
            periods_per_year: Trading periods per year

        Returns:
            Sortino ratio
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / periods_per_year)

        # Downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        sortino = np.sqrt(periods_per_year) * (excess_returns.mean() / downside_returns.std())
        return float(sortino)

    def drawdown_metrics(self, equity_curve: pd.Series) -> Dict:
        """
        Calculate drawdown metrics.

        Args:
            equity_curve: Series with equity values

        Returns:
            Dictionary with drawdown metrics
        """
        # Calculate running maximum
        running_max = equity_curve.expanding().max()

        # Calculate drawdown
        drawdown = (equity_curve - running_max) / running_max

        metrics = {
            'max_drawdown': float(drawdown.min()),
            'avg_drawdown': float(drawdown[drawdown < 0].mean()) if len(drawdown[drawdown < 0]) > 0 else 0.0
        }

        # Drawdown duration
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0

        for in_dd in is_drawdown:
            if in_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0

        if current_period > 0:
            drawdown_periods.append(current_period)

        metrics['max_drawdown_duration'] = max(drawdown_periods) if drawdown_periods else 0

        return metrics

    def trade_statistics(self, trades: pd.DataFrame) -> Dict:
        """
        Calculate trade statistics.

        Args:
            trades: DataFrame with columns [entry_price, exit_price, pnl, etc.]

        Returns:
            Dictionary with trade statistics
        """
        if len(trades) == 0:
            return {}

        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] < 0]

        stats = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
        }

        # Win rate
        stats['win_rate'] = len(winning_trades) / len(trades) if len(trades) > 0 else 0.0

        # Average win/loss
        stats['avg_win'] = float(winning_trades['pnl'].mean()) if len(winning_trades) > 0 else 0.0
        stats['avg_loss'] = float(losing_trades['pnl'].mean()) if len(losing_trades) > 0 else 0.0
        stats['avg_trade'] = float(trades['pnl'].mean())

        # Largest win/loss
        stats['largest_win'] = float(trades['pnl'].max()) if len(trades) > 0 else 0.0
        stats['largest_loss'] = float(trades['pnl'].min()) if len(trades) > 0 else 0.0

        # Profit factor
        total_wins = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0

        if total_losses > 0:
            stats['profit_factor'] = total_wins / total_losses
        else:
            stats['profit_factor'] = 0.0 if total_wins == 0 else float('inf')

        # Holding period
        if 'holding_period' in trades.columns:
            stats['avg_holding_period'] = float(trades['holding_period'].mean())
        else:
            stats['avg_holding_period'] = 0.0

        # Consecutive wins/losses
        stats['max_consecutive_wins'] = self._max_consecutive(trades['pnl'] > 0)
        stats['max_consecutive_losses'] = self._max_consecutive(trades['pnl'] < 0)

        return stats

    def _max_consecutive(self, condition: pd.Series) -> int:
        """Calculate maximum consecutive True values"""
        max_consec = 0
        current_consec = 0

        for value in condition:
            if value:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0

        return max_consec

    def value_at_risk(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR).

        Args:
            returns: Series of returns
            confidence: Confidence level (e.g., 0.95 for 95%)

        Returns:
            VaR at specified confidence level
        """
        if len(returns) == 0:
            return 0.0

        var = np.percentile(returns, (1 - confidence) * 100)
        return float(var)

    def conditional_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        Args:
            returns: Series of returns
            confidence: Confidence level

        Returns:
            CVaR at specified confidence level
        """
        if len(returns) == 0:
            return 0.0

        var = self.value_at_risk(returns, confidence)
        cvar = returns[returns <= var].mean()
        return float(cvar)

    def rolling_sharpe(
        self,
        returns: pd.Series,
        window: int = 252
    ) -> pd.Series:
        """
        Calculate rolling Sharpe ratio.

        Args:
            returns: Series of returns
            window: Rolling window size

        Returns:
            Series of rolling Sharpe ratios
        """
        excess_returns = returns - (self.risk_free_rate / 252)

        rolling_mean = excess_returns.rolling(window).mean()
        rolling_std = excess_returns.rolling(window).std()

        rolling_sharpe = np.sqrt(252) * (rolling_mean / rolling_std)
        return rolling_sharpe

    def information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate Information Ratio.

        Args:
            returns: Strategy returns
            benchmark_returns: Benchmark returns

        Returns:
            Information ratio
        """
        if len(returns) != len(benchmark_returns):
            self.logger.warning("Returns and benchmark have different lengths")
            return 0.0

        excess_returns = returns - benchmark_returns

        if excess_returns.std() == 0:
            return 0.0

        ir = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
        return float(ir)


def calculate_metrics(
    equity_curve: pd.Series,
    trades: Optional[pd.DataFrame] = None,
    initial_capital: float = 100000
) -> Dict:
    """
    Convenience function to calculate all metrics.

    Args:
        equity_curve: Equity curve series
        trades: Trades DataFrame (optional)
        initial_capital: Starting capital

    Returns:
        Dictionary with all metrics
    """
    calculator = MetricsCalculator()
    return calculator.calculate_all_metrics(equity_curve, trades, initial_capital)
