"""
Phase 3 Runner - Supertrend Trend-Following Strategy
Tests Supertrend indicator on all stocks with parameter optimization
"""

import os
import sys
import yaml
import logging
import itertools
from datetime import datetime
from tqdm import tqdm

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager
from agents.agent_3_optimization.candle_loader import CandleLoader
import backtrader as bt
import pandas as pd

# Import Supertrend strategy
from agents.agent_2_strategy_core.supertrend_strategy import SupertrendStrategy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_phase_config(config_path: str) -> dict:
    """Load phase configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def generate_parameter_combinations(param_grid: dict) -> list:
    """
    Generate all combinations of parameters from grid.

    Handles conditional parameters (stop_loss, profit_target).
    """
    # Extract parameters
    atr_periods = param_grid.get('atr_period', [10])
    atr_multipliers = param_grid.get('atr_multiplier', [3.0])
    stop_loss_types = param_grid.get('stop_loss_type', ['none'])
    stop_loss_values = param_grid.get('stop_loss_value', [None])
    profit_targets = param_grid.get('profit_target', [None])

    combinations = []

    # Generate all combinations
    for period, multiplier, profit_target in itertools.product(
        atr_periods, atr_multipliers, profit_targets
    ):
        # For each stop loss type
        for sl_type in stop_loss_types:
            if sl_type == 'none':
                # No stop loss
                combinations.append({
                    'atr_period': period,
                    'atr_multiplier': multiplier,
                    'stop_loss_type': 'none',
                    'stop_loss_value': None,
                    'profit_target': profit_target
                })
            else:
                # ATR-based stop loss - try each value
                for sl_value in stop_loss_values:
                    if sl_value is not None:
                        combinations.append({
                            'atr_period': period,
                            'atr_multiplier': multiplier,
                            'stop_loss_type': sl_type,
                            'stop_loss_value': sl_value,
                            'profit_target': profit_target
                        })

    return combinations


def run_supertrend_backtest(candle_df, symbol, strategy_params, initial_capital=100000, commission=0.001):
    """
    Run a single Supertrend backtest.

    Returns:
        Dictionary with results
    """
    try:
        # Create Cerebro instance
        cerebro = bt.Cerebro()

        # Set initial capital
        cerebro.broker.setcash(initial_capital)

        # Set commission
        cerebro.broker.setcommission(commission=commission)

        # Convert DataFrame to Backtrader data feed
        candle_df = candle_df.copy()
        if 'date' in candle_df.columns:
            candle_df = candle_df.set_index('date')

        # Ensure datetime index
        if not isinstance(candle_df.index, pd.DatetimeIndex):
            candle_df.index = pd.to_datetime(candle_df.index)

        # Create data feed
        data_feed = bt.feeds.PandasData(
            dataname=candle_df,
            datetime=None,  # Use index
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )

        cerebro.adddata(data_feed, name=symbol)

        # Add strategy with parameters
        cerebro.addstrategy(SupertrendStrategy, **strategy_params)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                          timeframe=bt.TimeFrame.Days,
                          compression=1,
                          fund=True,
                          annualize=True,
                          riskfreerate=0.02)

        # Run backtest
        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        # Extract strategy instance
        strat = results[0]

        # Get trade stats from strategy
        total_trades = strat.trade_count
        winning_trades = strat.winning_trades
        losing_trades = strat.losing_trades
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        # Get drawdown
        dd_analysis = strat.analyzers.drawdown.get_analysis()
        max_drawdown_pct = 0.0
        try:
            if hasattr(dd_analysis, 'max') and hasattr(dd_analysis.max, 'drawdown'):
                max_drawdown_pct = dd_analysis.max.drawdown / 100.0
        except (AttributeError, TypeError):
            pass

        # Get Sharpe ratio
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = 0.0
        try:
            if sharpe_analysis and 'sharperatio' in sharpe_analysis:
                sharpe_value = sharpe_analysis['sharperatio']
                if sharpe_value is not None and not pd.isna(sharpe_value):
                    sharpe_ratio = sharpe_value
        except (AttributeError, TypeError, KeyError):
            pass

        # Calculate fallback Sharpe if needed
        if sharpe_ratio == 0.0 or pd.isna(sharpe_ratio):
            total_return = (end_value - start_value) / start_value
            if max_drawdown_pct > 0:
                num_days = len(candle_df)
                years = num_days / 252.0
                if years > 0:
                    annualized_return = ((1 + total_return) ** (1/years)) - 1
                    sharpe_ratio = (annualized_return - 0.02) / max_drawdown_pct

        # Calculate total return
        total_return = (end_value - start_value) / start_value

        # Build results dictionary
        metrics = {
            'symbol': symbol,
            'candle_type': 'regular',
            'aggregation_days': 1,
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

        return metrics

    except Exception as e:
        logger.error(f"Error in backtest for {symbol}: {e}")
        return {'error': str(e), 'symbol': symbol}


def save_results_to_db(results, db):
    """Save backtest results to database."""
    try:
        # Create strategy config first
        params = results['strategy_params']

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

        # Build config name
        config_name = (
            f"phase3_supertrend_"
            f"atr{params.get('atr_period', 10)}_"
            f"mult{params.get('atr_multiplier', 3.0)}_"
            f"sl{params.get('stop_loss_type', 'none')}"
        )

        config_params = (
            config_name,
            3,  # Phase 3
            results['candle_type'],
            results['aggregation_days'],
            'Supertrend',  # Use as mean_type identifier
            params.get('atr_period', 10),  # Store as mean_lookback
            params.get('atr_period', 10),  # Store as stddev_lookback
            params.get('atr_multiplier', 3.0),  # Store as entry_threshold
            pd.io.json.dumps(params)
        )

        config_result = db.execute_query(config_query, config_params)
        config_id = config_result[0][0]

        # Insert backtest results
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

        db.execute_query(results_query, results_params)
        logger.debug(f"Saved results for {results['symbol']}")

    except Exception as e:
        logger.error(f"Error saving results: {e}")


def run_phase_3(config_path: str, limit_stocks: int = None, limit_params: int = None):
    """
    Execute Phase 3 Supertrend testing.

    Args:
        config_path: Path to phase_3_supertrend_config.yaml
        limit_stocks: Optional limit on stocks (for testing)
        limit_params: Optional limit on parameter combinations (for testing)
    """
    logger.info("="*80)
    logger.info("PHASE 3: Supertrend Trend-Following Strategy")
    logger.info("="*80)

    # Load configuration
    config = load_phase_config(config_path)
    logger.info(f"Loaded configuration: {config['name']}")

    # Initialize database
    db = DatabaseManager()
    logger.info("Connected to database")

    # Initialize candle loader
    candle_loader = CandleLoader(db)

    # Get all symbols (same as Phase 1)
    symbols = candle_loader.get_available_symbols(candle_type='regular', aggregation_days=1)

    if limit_stocks:
        symbols = symbols[:limit_stocks]

    logger.info(f"Testing {len(symbols)} symbols")

    # Generate parameter combinations
    logger.info("\nGenerating parameter combinations...")
    param_combinations = generate_parameter_combinations(config['parameter_grid'])

    if limit_params:
        param_combinations = param_combinations[:limit_params]

    logger.info(f"Generated {len(param_combinations)} parameter combinations")

    # Get fixed parameters
    fixed_params = config['fixed_parameters']

    # Calculate total backtests
    total_backtests = len(symbols) * len(param_combinations)
    logger.info(f"\nTotal backtests: {total_backtests:,}")
    logger.info(f"  - Stocks: {len(symbols)}")
    logger.info(f"  - Parameters: {len(param_combinations)}")

    # Track results
    completed = 0
    failed = 0
    start_time = datetime.now()

    # Load candles once (regular 1d for all stocks)
    logger.info("\nLoading regular 1d candles for all stocks...")
    candles_dict = candle_loader.load_multiple_symbols(
        symbols=symbols,
        candle_type='regular',
        aggregation_days=1,
        start_date=config['backtest_period']['start_date'],
        end_date=config['backtest_period']['end_date']
    )
    logger.info(f"Loaded candles for {len(candles_dict)} symbols")

    # Run backtests
    logger.info("\nStarting Supertrend backtests...\n")

    for symbol in tqdm(candles_dict.keys(), desc="Stocks", position=0):
        candle_df = candles_dict[symbol]

        for param_combo in tqdm(param_combinations, desc=f"{symbol} params", position=1, leave=False):
            try:
                # Merge fixed and variable parameters
                strategy_params = fixed_params.copy()
                strategy_params.update(param_combo)

                # Run backtest
                result = run_supertrend_backtest(
                    candle_df=candle_df,
                    symbol=symbol,
                    strategy_params=strategy_params,
                    initial_capital=config['execution']['initial_capital'],
                    commission=config['execution']['commission']
                )

                # Save results
                if 'error' not in result:
                    save_results_to_db(result, db)
                    completed += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Error backtesting {symbol}: {e}")
                failed += 1

        # Log progress every stock
        if completed > 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = completed / elapsed if elapsed > 0 else 0
            remaining = (total_backtests - completed) / rate if rate > 0 else 0

            logger.info(
                f"\nProgress: {completed}/{total_backtests} ({completed/total_backtests*100:.1f}%) "
                f"| Failed: {failed} | Rate: {rate:.1f}/sec | ETA: {remaining/60:.0f}min"
            )

    # Final summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "="*80)
    logger.info("PHASE 3 EXECUTION COMPLETE!")
    logger.info("="*80)
    logger.info(f"Total backtests: {completed + failed}")
    logger.info(f"  Completed: {completed}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Success rate: {completed/(completed+failed)*100:.1f}%")
    logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
    logger.info(f"Average rate: {completed/elapsed:.1f} backtests/sec")
    logger.info("="*80)

    db.close()
    logger.info("✅ Phase 3 execution complete!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run Phase 3 Supertrend strategy testing')
    parser.add_argument(
        '--config',
        type=str,
        default='configs/phase_3_supertrend_config.yaml',
        help='Path to phase 3 configuration file'
    )
    parser.add_argument(
        '--limit-stocks',
        type=int,
        default=None,
        help='Limit number of stocks (for testing)'
    )
    parser.add_argument(
        '--limit-params',
        type=int,
        default=None,
        help='Limit number of parameter combinations (for testing)'
    )

    args = parser.parse_args()

    run_phase_3(
        config_path=args.config,
        limit_stocks=args.limit_stocks,
        limit_params=args.limit_params
    )
