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

            # Get equity curve from broker
            equity_curve = pd.Series(
                [self.initial_capital] + [end_value],
                index=[candle_df.index[0], candle_df.index[-1]]
            )

            # Calculate metrics
            metrics_calc = MetricsCalculator(risk_free_rate=0.02)

            # Get trade analyzer results
            trade_analysis = strat.analyzers.trades.get_analysis()

            # Build trades DataFrame if we have trades
            trades_df = None
            if hasattr(trade_analysis, 'total') and trade_analysis.total.total > 0:
                # Extract trade data
                trades_data = []
                if hasattr(strat, 'trade_list'):
                    for trade in strat.trade_list:
                        trades_data.append({
                            'entry_date': trade.get('entry_date'),
                            'exit_date': trade.get('exit_date'),
                            'entry_price': trade.get('entry_price'),
                            'exit_price': trade.get('exit_price'),
                            'pnl': trade.get('pnl'),
                            'holding_period': trade.get('holding_period', 0)
                        })

                    if trades_data:
                        trades_df = pd.DataFrame(trades_data)

            # Calculate comprehensive metrics
            metrics = metrics_calc.calculate_all_metrics(
                equity_curve=equity_curve,
                trades=trades_df,
                initial_capital=self.initial_capital
            )

            # Add backtest-specific info
            metrics['symbol'] = symbol
            metrics['candle_type'] = candle_type
            metrics['aggregation_days'] = aggregation_days
            metrics['start_value'] = start_value
            metrics['end_value'] = end_value
            metrics['pnl'] = end_value - start_value
            metrics['strategy_params'] = strategy_params

            # Add analyzer results
            metrics['total_trades'] = trade_analysis.total.total if hasattr(trade_analysis, 'total') else 0

            # Drawdown
            dd_analysis = strat.analyzers.drawdown.get_analysis()
            if hasattr(dd_analysis, 'max'):
                metrics['max_drawdown'] = dd_analysis.max.drawdown / 100.0  # Convert to decimal

            # Sharpe from analyzer
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            if sharpe_analysis and 'sharperatio' in sharpe_analysis:
                metrics['sharpe_ratio_bt'] = sharpe_analysis['sharperatio']

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

            # Insert strategy config
            config_query = """
                INSERT INTO strategy_configs (
                    config_name, phase,
                    candle_type, aggregation_days,
                    mean_type, mean_lookback, stddev_lookback, entry_threshold,
                    exit_type, parameters
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
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
                strategy_params.get('exit_type', 'mean'),
                json.dumps(strategy_params)
            )

            config_result = db_manager.execute_query(config_query, config_params)

            # Verify config was created and we got an ID back
            if not config_result or len(config_result) == 0:
                raise Exception("Failed to create strategy_config - no ID returned")

            config_id = config_result[0][0]
            self.logger.debug(f"Created strategy_config ID: {config_id}")

            # Step 2: Insert backtest results with RETURNING to verify
            results_query = """
                INSERT INTO backtest_results (
                    config_id, symbol,
                    initial_capital, final_value, total_return, annualized_return,
                    sharpe_ratio, sortino_ratio, calmar_ratio,
                    max_drawdown, avg_drawdown, max_drawdown_duration,
                    total_trades, winning_trades, losing_trades, win_rate,
                    avg_win, avg_loss,
                    profit_factor
                )
                VALUES (
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s
                )
                RETURNING id
            """

            results_params = (
                config_id,
                results['symbol'],
                results['initial_capital'],
                results['final_value'],
                results['total_return'],
                results['annualized_return'],
                results['sharpe_ratio'],
                results['sortino_ratio'],
                results['calmar_ratio'],
                results['max_drawdown'],
                results.get('avg_drawdown', 0),
                results.get('max_drawdown_duration', 0),
                results['total_trades'],
                results['winning_trades'],
                results['losing_trades'],
                results['win_rate'],
                results.get('avg_win', 0),
                results.get('avg_loss', 0),
                results.get('profit_factor', 0)
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
