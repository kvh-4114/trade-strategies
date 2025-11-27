"""
Backtest Executor - Agent 3 Component
Runs individual backtests with Backtrader
"""

import backtrader as bt
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Optional, List
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.agent_2_strategy_core.base_strategy import MeanReversionStrategy
from agents.agent_4_analysis.metrics_calculator import MetricsCalculator
from agents.agent_3_optimization.data_feed import create_data_feed

logger = logging.getLogger(__name__)


class BacktestExecutor:
    """
    Executes single backtests with specified parameters.

    Handles Backtrader setup, execution, and results extraction.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.0
    ):
        """
        Initialize backtest executor.

        Args:
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage percentage
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.logger = logging.getLogger(__name__)

    def run_backtest(
        self,
        candle_df: pd.DataFrame,
        symbol: str,
        strategy_params: Dict,
        candle_type: str,
        aggregation_days: int
    ) -> Dict:
        """
        Run a single backtest.

        Args:
            candle_df: DataFrame with candle data
            symbol: Stock symbol
            strategy_params: Dictionary of strategy parameters
            candle_type: Type of candle used
            aggregation_days: Aggregation period

        Returns:
            Dictionary with backtest results and metrics
        """
        try:
            # Create Cerebro instance
            cerebro = bt.Cerebro()

            # Set initial capital
            cerebro.broker.setcash(self.initial_capital)

            # Set commission
            cerebro.broker.setcommission(commission=self.commission)

            # Add data feed
            data_feed = create_data_feed(candle_df, name=symbol)
            cerebro.adddata(data_feed)

            # Add strategy with parameters
            cerebro.addstrategy(MeanReversionStrategy, **strategy_params)

            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

            # Run backtest
            self.logger.info(f"Running backtest for {symbol} ({candle_type}, {aggregation_days}d)")

            start_value = cerebro.broker.getvalue()
            results = cerebro.run()
            end_value = cerebro.broker.getvalue()

            # Extract strategy instance
            strat = results[0]

            # Get trade stats directly from strategy (it tracks wins/losses in notify_trade)
            total_trades = strat.trade_count
            winning_trades = strat.winning_trades
            losing_trades = strat.losing_trades

            # Calculate win rate
            win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

            # Get drawdown info
            dd_analysis = strat.analyzers.drawdown.get_analysis()
            max_drawdown_pct = 0.0
            try:
                if hasattr(dd_analysis, 'max') and hasattr(dd_analysis.max, 'drawdown'):
                    max_drawdown_pct = dd_analysis.max.drawdown / 100.0  # Convert to decimal
            except (AttributeError, TypeError):
                pass

            # Get returns analyzer
            returns_analysis = strat.analyzers.returns.get_analysis()
            total_return = (end_value - start_value) / start_value

            # Get Sharpe from analyzer
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            sharpe_ratio = 0.0
            try:
                if sharpe_analysis and 'sharperatio' in sharpe_analysis:
                    sharpe_value = sharpe_analysis['sharperatio']
                    # Handle None or NaN values
                    if sharpe_value is not None and not pd.isna(sharpe_value):
                        sharpe_ratio = sharpe_value
            except (AttributeError, TypeError, KeyError):
                pass

            # Build metrics dictionary directly from analyzer results
            metrics = {
                'symbol': symbol,
                'candle_type': candle_type,
                'aggregation_days': aggregation_days,
                'start_value': start_value,
                'end_value': end_value,
                'pnl': end_value - start_value,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown_pct,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'strategy_params': strategy_params
            }

            self.logger.info(
                f"Completed backtest for {symbol}: "
                f"PnL=${metrics['pnl']:.2f}, "
                f"Sharpe={metrics.get('sharpe_ratio', 0):.2f}, "
                f"Trades={metrics['total_trades']}"
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Error running backtest for {symbol}: {e}")
            return {
                'symbol': symbol,
                'candle_type': candle_type,
                'aggregation_days': aggregation_days,
                'error': str(e),
                'success': False
            }

    def run_multiple_backtests(
        self,
        candles_dict: Dict[str, pd.DataFrame],
        strategy_params: Dict,
        candle_type: str,
        aggregation_days: int
    ) -> List[Dict]:
        """
        Run backtests for multiple symbols.

        Args:
            candles_dict: Dictionary mapping symbol -> DataFrame
            strategy_params: Strategy parameters
            candle_type: Type of candle
            aggregation_days: Aggregation period

        Returns:
            List of results dictionaries
        """
        results = []

        for symbol, candle_df in candles_dict.items():
            result = self.run_backtest(
                candle_df=candle_df,
                symbol=symbol,
                strategy_params=strategy_params,
                candle_type=candle_type,
                aggregation_days=aggregation_days
            )
            results.append(result)

        self.logger.info(f"Completed {len(results)} backtests")

        return results

    def save_results(self, results: Dict, db_manager) -> bool:
        """
        Save backtest results to database.

        Args:
            results: Results dictionary from backtest
            db_manager: DatabaseManager instance

        Returns:
            True if successful
        """
        try:
            import json

            # Step 1: Create or get strategy_config
            strategy_params = results.get('strategy_params', {})
            config_name = f"{results['symbol']}_{results['candle_type']}_{results['aggregation_days']}d"

            # Insert strategy config (only using columns that exist in table)
            config_query = """
                INSERT INTO strategy_configs (
                    config_name, phase,
                    candle_type, aggregation_days,
                    mean_type, mean_lookback, stddev_lookback, entry_threshold,
                    parameters
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (config_name) DO UPDATE SET config_name = EXCLUDED.config_name
                RETURNING id
            """

            config_params = (
                config_name,
                1,  # Phase 1
                results['candle_type'],
                results['aggregation_days'],
                strategy_params.get('mean_type', 'SMA'),
                strategy_params.get('mean_lookback', 20),
                strategy_params.get('stddev_lookback', 20),
                strategy_params.get('entry_threshold', 2.0),
                json.dumps(strategy_params)  # Store all params including exit_type in JSONB
            )

            config_result = db_manager.execute_query(config_query, config_params)

            # Verify config was created and we got an ID back
            if not config_result or len(config_result) == 0:
                raise Exception("Failed to create strategy_config - no ID returned")

            config_id = config_result[0][0]
            self.logger.debug(f"Created strategy_config ID: {config_id}")

            # Step 2: Insert backtest results (only columns that exist in table)
            results_query = """
                INSERT INTO backtest_results (
                    config_id, symbol,
                    total_return, sharpe_ratio, max_drawdown,
                    total_trades, win_rate
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """

            results_params = (
                config_id,
                results['symbol'],
                results['total_return'],
                results['sharpe_ratio'],
                results['max_drawdown'],
                results['total_trades'],
                results['win_rate']
            )

            result_insert = db_manager.execute_query(results_query, results_params)

            # Verify insert succeeded
            if not result_insert or len(result_insert) == 0:
                raise Exception("Failed to insert backtest_results - no ID returned")

            result_id = result_insert[0][0]
            self.logger.info(f"✅ Saved {results['symbol']} (config={config_id}, result={result_id})")

            return True

        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return False
