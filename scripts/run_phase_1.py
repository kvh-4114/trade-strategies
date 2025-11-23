"""
Phase 1 Runner - Baseline Candle Type Comparison
Tests all 13 candle type combinations with fixed strategy parameters
"""

import os
import sys
import yaml
import logging
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


def get_candle_combinations(config: dict) -> list:
    """
    Get list of candle type combinations to test.

    Returns:
        List of tuples (candle_type, aggregation_days)
    """
    combinations = []

    # Regular candles
    for agg_days in [1, 2, 3, 4, 5]:
        combinations.append(('regular', agg_days))

    # Heiken Ashi candles
    for agg_days in [1, 2, 3, 4, 5]:
        combinations.append(('heiken_ashi', agg_days))

    # Linear Regression candles (only 1, 2, 3 day as per blueprint)
    for agg_days in [1, 2, 3]:
        combinations.append(('linreg', agg_days))

    return combinations


def run_phase_1(config_path: str, limit_symbols: int = None):
    """
    Execute Phase 1 baseline testing.

    Args:
        config_path: Path to phase_1_config.yaml
        limit_symbols: Optional limit on number of symbols to test
    """
    logger.info("="*60)
    logger.info("PHASE 1: Baseline Candle Type Comparison")
    logger.info("="*60)

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

    # Get list of candle combinations
    combinations = get_candle_combinations(config)
    logger.info(f"Testing {len(combinations)} candle combinations")

    # Get available symbols
    symbols = candle_loader.get_available_symbols(candle_type='regular', aggregation_days=1)

    if limit_symbols:
        symbols = symbols[:limit_symbols]

    logger.info(f"Testing {len(symbols)} symbols")

    # Get fixed strategy parameters from config
    strategy_params = config['fixed_parameters']
    logger.info(f"Strategy parameters: {strategy_params}")

    # Track results
    total_backtests = len(symbols) * len(combinations)
    completed = 0
    failed = 0

    logger.info(f"\nStarting {total_backtests} backtests...\n")

    # Iterate through each combination
    for candle_type, agg_days in combinations:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {candle_type} {agg_days}d")
        logger.info(f"{'='*60}\n")

        # Load candles for all symbols
        candles_dict = candle_loader.load_multiple_symbols(
            symbols=symbols,
            candle_type=candle_type,
            aggregation_days=agg_days,
            start_date=config['execution']['start_date'],
            end_date=config['execution']['end_date']
        )

        logger.info(f"Loaded candles for {len(candles_dict)} symbols")

        # Run backtests for each symbol
        for symbol in tqdm(candles_dict.keys(), desc=f"{candle_type} {agg_days}d"):
            try:
                candle_df = candles_dict[symbol]

                # Run backtest
                result = executor.run_backtest(
                    candle_df=candle_df,
                    symbol=symbol,
                    strategy_params=strategy_params,
                    candle_type=candle_type,
                    aggregation_days=agg_days
                )

                # Save results to database
                if 'error' not in result:
                    executor.save_results(result, db)
                    completed += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Error testing {symbol}: {e}")
                failed += 1

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("PHASE 1 COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total backtests: {total_backtests}")
    logger.info(f"Completed: {completed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {100*completed/total_backtests:.1f}%")
    logger.info(f"{'='*60}\n")

    # Generate summary report
    generate_summary_report(db)

    db.close()
    logger.info("✅ Phase 1 execution complete!")


def generate_summary_report(db: DatabaseManager):
    """Generate summary report of Phase 1 results."""
    logger.info("\nGenerating Phase 1 Summary Report...")

    # Get top performers by Sharpe ratio
    query = """
        SELECT
            candle_type,
            aggregation_days,
            COUNT(*) as num_stocks,
            AVG(sharpe_ratio) as avg_sharpe,
            AVG(total_return) as avg_return,
            AVG(max_drawdown) as avg_drawdown,
            AVG(total_trades) as avg_trades
        FROM backtest_results
        GROUP BY candle_type, aggregation_days
        ORDER BY avg_sharpe DESC
    """

    results = db.execute_query(query)

    print("\n" + "="*80)
    print("PHASE 1 RESULTS SUMMARY - BY CANDLE TYPE")
    print("="*80)
    print(f"{'Candle Type':<20} {'Agg':<5} {'Stocks':<8} {'Avg Sharpe':<12} {'Avg Return':<12} {'Avg DD':<10} {'Avg Trades'}")
    print("-"*80)

    for row in results:
        candle_type, agg_days, num_stocks, avg_sharpe, avg_return, avg_dd, avg_trades = row
        print(
            f"{candle_type:<20} {agg_days:<5} {num_stocks:<8} "
            f"{avg_sharpe:>11.3f} {avg_return:>11.2%} "
            f"{avg_dd:>9.2%} {avg_trades:>11.1f}"
        )

    print("="*80 + "\n")

    # Get top performing individual stocks
    query = """
        SELECT
            symbol,
            candle_type,
            aggregation_days,
            sharpe_ratio,
            total_return,
            max_drawdown,
            total_trades
        FROM backtest_results
        ORDER BY sharpe_ratio DESC
        LIMIT 20
    """

    results = db.execute_query(query)

    print("\n" + "="*80)
    print("TOP 20 INDIVIDUAL STOCK PERFORMANCES")
    print("="*80)
    print(f"{'Symbol':<8} {'Candle Type':<20} {'Agg':<5} {'Sharpe':<10} {'Return':<10} {'DD':<10} {'Trades'}")
    print("-"*80)

    for row in results:
        symbol, candle_type, agg_days, sharpe, ret, dd, trades = row
        print(
            f"{symbol:<8} {candle_type:<20} {agg_days:<5} "
            f"{sharpe:>9.3f} {ret:>9.2%} {dd:>9.2%} {trades:>7}"
        )

    print("="*80 + "\n")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run Phase 1 baseline testing')
    parser.add_argument(
        '--config',
        type=str,
        default='configs/phase_1_config.yaml',
        help='Path to phase 1 configuration file'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of symbols for testing'
    )

    args = parser.parse_args()

    run_phase_1(config_path=args.config, limit_symbols=args.limit)
