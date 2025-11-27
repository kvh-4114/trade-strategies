"""
Phase 2 Runner - Parameter Optimization
Optimizes mean reversion parameters for regular 1-day candles on profitable stocks
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
from agents.agent_3_optimization.backtest_executor import BacktestExecutor

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


def get_profitable_stocks(db: DatabaseManager, candle_type: str = 'regular', agg_days: int = 1) -> list:
    """
    Query database for stocks that were profitable in Phase 1.

    Args:
        db: Database manager instance
        candle_type: Candle type to filter ('regular')
        agg_days: Aggregation days to filter (1)

    Returns:
        List of profitable stock symbols
    """
    query = """
        SELECT DISTINCT br.symbol
        FROM backtest_results br
        JOIN strategy_configs sc ON br.config_id = sc.id
        WHERE sc.phase = 1
          AND sc.candle_type = %s
          AND sc.aggregation_days = %s
          AND br.total_return > 0
        ORDER BY br.symbol
    """

    results = db.execute_query(query, (candle_type, agg_days))
    symbols = [row[0] for row in results]

    logger.info(f"Found {len(symbols)} profitable stocks from Phase 1")
    return symbols


def generate_parameter_combinations(param_grid: dict) -> list:
    """
    Generate all combinations of parameters from grid.

    Args:
        param_grid: Dictionary of parameter lists

    Returns:
        List of parameter dictionaries
    """
    # Handle stop loss combinations specially
    # Only combine stop_loss_type and stop_loss_value when type != 'none'

    # Extract stop loss params
    stop_loss_types = param_grid.get('stop_loss_type', ['none'])
    stop_loss_values = param_grid.get('stop_loss_value', [None])

    # Other params (excluding stop loss)
    other_params = {k: v for k, v in param_grid.items()
                    if k not in ['stop_loss_type', 'stop_loss_value', 'exit_threshold']}

    # Generate combinations for other params
    param_names = list(other_params.keys())
    param_values = list(other_params.values())

    combinations = []
    for values in itertools.product(*param_values):
        param_dict = dict(zip(param_names, values))

        # Handle exit_threshold - only use with profit_target exit type
        exit_type = param_dict.get('exit_type')
        if exit_type == 'profit_target':
            # Add exit_threshold
            for threshold in param_grid.get('exit_threshold', [0.05]):
                param_with_threshold = param_dict.copy()
                param_with_threshold['exit_threshold'] = threshold

                # Add stop loss combinations
                for combo in _generate_stop_loss_combos(stop_loss_types, stop_loss_values):
                    final_params = param_with_threshold.copy()
                    final_params.update(combo)
                    combinations.append(final_params)
        else:
            # No exit_threshold needed
            param_dict['exit_threshold'] = None

            # Add stop loss combinations
            for combo in _generate_stop_loss_combos(stop_loss_types, stop_loss_values):
                final_params = param_dict.copy()
                final_params.update(combo)
                combinations.append(final_params)

    return combinations


def _generate_stop_loss_combos(types: list, values: list) -> list:
    """Generate valid stop loss combinations."""
    combos = []

    for sl_type in types:
        if sl_type == 'none':
            combos.append({'stop_loss_type': 'none', 'stop_loss_value': None})
        else:  # fixed_pct
            for sl_value in values:
                if sl_value is not None and sl_value < 0:  # Only negative values
                    combos.append({'stop_loss_type': sl_type, 'stop_loss_value': sl_value})

    return combos


def run_phase_2(config_path: str, limit_stocks: int = None, limit_params: int = None):
    """
    Execute Phase 2 parameter optimization.

    Args:
        config_path: Path to phase_2_config.yaml
        limit_stocks: Optional limit on number of stocks (for testing)
        limit_params: Optional limit on parameter combinations (for testing)
    """
    logger.info("="*80)
    logger.info("PHASE 2: Parameter Optimization for Regular 1d Candles")
    logger.info("="*80)

    # Load configuration
    config = load_phase_config(config_path)
    logger.info(f"Loaded configuration: {config['name']}")

    # Initialize database
    db = DatabaseManager()
    logger.info("Connected to database")

    # Initialize components
    candle_loader = CandleLoader(db)
    executor = BacktestExecutor(
        initial_capital=config['execution']['initial_capital'],
        commission=config['execution']['commission']
    )

    # Get profitable stocks from Phase 1
    logger.info("\nQuerying profitable stocks from Phase 1...")
    symbols = get_profitable_stocks(db, candle_type='regular', agg_days=1)

    if limit_stocks:
        symbols = symbols[:limit_stocks]
        logger.info(f"Limited to {len(symbols)} stocks for testing")

    if not symbols:
        logger.error("No profitable stocks found from Phase 1!")
        return

    # Generate parameter combinations
    logger.info("\nGenerating parameter combinations...")
    param_combinations = generate_parameter_combinations(config['parameter_grid'])

    if limit_params:
        param_combinations = param_combinations[:limit_params]
        logger.info(f"Limited to {len(param_combinations)} parameter combinations for testing")

    logger.info(f"Generated {len(param_combinations)} parameter combinations")

    # Get fixed parameters
    fixed_params = config['fixed_parameters']

    # Calculate total backtests
    total_backtests = len(symbols) * len(param_combinations)
    logger.info(f"\nTotal backtests to run: {total_backtests:,}")
    logger.info(f"  - Stocks: {len(symbols)}")
    logger.info(f"  - Parameter combinations: {len(param_combinations)}")

    # Track results
    completed = 0
    failed = 0
    start_time = datetime.now()

    # Load candles once (regular 1d for all profitable stocks)
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
    logger.info("\nStarting parameter grid search...\n")

    for symbol in tqdm(candles_dict.keys(), desc="Stocks", position=0):
        candle_df = candles_dict[symbol]

        for param_combo in tqdm(param_combinations, desc=f"{symbol} params", position=1, leave=False):
            try:
                # Merge fixed and variable parameters
                strategy_params = fixed_params.copy()
                strategy_params.update(param_combo)

                # Run backtest
                result = executor.run_backtest(
                    candle_df=candle_df,
                    symbol=symbol,
                    strategy_params=strategy_params,
                    candle_type='regular',
                    aggregation_days=1
                )

                # Save results to database
                if 'error' not in result:
                    executor.save_results(result, db)
                    completed += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Error backtesting {symbol} with params {param_combo}: {e}")
                failed += 1

        # Log progress every stock
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
    logger.info("PHASE 2 EXECUTION COMPLETE!")
    logger.info("="*80)
    logger.info(f"Total backtests: {completed + failed}")
    logger.info(f"  Completed: {completed}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Success rate: {completed/(completed+failed)*100:.1f}%")
    logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
    logger.info(f"Average rate: {completed/elapsed:.1f} backtests/sec")
    logger.info("="*80)

    db.close()
    logger.info("✅ Phase 2 execution complete!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run Phase 2 parameter optimization')
    parser.add_argument(
        '--config',
        type=str,
        default='configs/phase_2_config.yaml',
        help='Path to phase 2 configuration file'
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

    run_phase_2(
        config_path=args.config,
        limit_stocks=args.limit_stocks,
        limit_params=args.limit_params
    )
