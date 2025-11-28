"""
Test Supertrend Strategy on Single Symbol with Debug Output
Shows Supertrend indicator values and verifies database writes
"""

import os
import sys
import pandas as pd

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_5_infrastructure.database_manager import DatabaseManager
from agents.agent_3_optimization.candle_loader import CandleLoader
import backtrader as bt
from agents.agent_2_strategy_core.supertrend_strategy import SupertrendStrategy
from agents.agent_2_strategy_core.supertrend import Supertrend


class DebugSupertrend(Supertrend):
    """Debug version of Supertrend that prints values."""

    params = (
        ('period', 10),
        ('multiplier', 3.0),
        ('debug', True),
    )

    def __init__(self):
        super().__init__()
        self.bar_count = 0

    def next(self):
        """Calculate Supertrend with debug output using FIXED algorithm."""
        self.bar_count += 1

        # Store values before calling parent
        close = self.data.close[0]
        basic_upper = self.basic_band[0] + (self.params.multiplier * self.atr[0])
        basic_lower = self.basic_band[0] - (self.params.multiplier * self.atr[0])

        if len(self) > 1:
            prev_direction = self.direction[-1]
        else:
            prev_direction = None

        # Call parent to do the actual calculation
        super().next()

        # Debug output for first 30 bars and transitions
        if self.params.debug and (self.bar_count <= 30 or (prev_direction is not None and prev_direction != self.direction[0])):
            date = self.data.datetime.date(0)
            print(f"Bar {self.bar_count:4d} | {date} | Close: ${close:6.2f} | "
                  f"FinalLower: ${self.final_lower[0]:6.2f} | FinalUpper: ${self.final_upper[0]:6.2f} | "
                  f"Prev Dir: {prev_direction if prev_direction is not None else 'N/A':>3} | "
                  f"New Dir: {self.direction[0]:2.0f} | ST: ${self.supertrend[0]:6.2f}")


class DebugSupertrendStrategy(SupertrendStrategy):
    """Strategy with debug Supertrend."""

    def __init__(self):
        """Initialize with debug indicator."""
        # Use debug Supertrend
        self.supertrend = DebugSupertrend(
            self.data,
            period=self.params.atr_period,
            multiplier=self.params.atr_multiplier,
            debug=True
        )

        # ATR for stop loss
        if self.params.stop_loss_type == 'atr':
            self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

        # Track trade state
        self.entry_price = None
        self.order = None

        # Track performance
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0


def test_supertrend_single_symbol(symbol='NVDA', test_db_write=True):
    """
    Test Supertrend on single symbol with debug output.

    Args:
        symbol: Stock symbol to test
        test_db_write: Whether to test database write
    """

    print("\n" + "="*100)
    print(f"TESTING SUPERTREND ON {symbol}")
    print("="*100)

    # Initialize database and loader
    db = DatabaseManager()
    candle_loader = CandleLoader(db)

    # Load candles for symbol
    print(f"\n1. Loading candles for {symbol}...")
    candle_df = candle_loader.load_candles(
        symbol=symbol,
        candle_type='regular',
        aggregation_days=1
    )

    if candle_df is None or len(candle_df) == 0:
        print(f"❌ No candles found for {symbol}")
        db.close()
        return

    print(f"✅ Loaded {len(candle_df)} candles ({candle_df.index[0]} to {candle_df.index[-1]})")

    # Setup Cerebro
    print(f"\n2. Setting up Supertrend backtest...")
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.001)

    # Create data feed
    data_feed = bt.feeds.PandasData(
        dataname=candle_df,
        datetime=None,
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )

    cerebro.adddata(data_feed, name=symbol)

    # Add strategy with simple params
    strategy_params = {
        'atr_period': 10,
        'atr_multiplier': 3.0,
        'position_sizing': 'fixed',
        'position_size': 10000,
        'stop_loss_type': 'none',
        'stop_loss_value': None,
        'profit_target': None,
        'log_trades': True
    }

    cerebro.addstrategy(DebugSupertrendStrategy, **strategy_params)

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
    print(f"\n3. Running Supertrend backtest...")
    print("-"*100)
    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()
    print("-"*100)

    # Extract results
    strat = results[0]

    print(f"\n4. Backtest Results:")
    print(f"   Start Value: ${start_value:,.2f}")
    print(f"   End Value:   ${end_value:,.2f}")
    print(f"   PnL:         ${end_value - start_value:,.2f}")
    print(f"   Return:      {(end_value - start_value) / start_value * 100:.2f}%")
    print(f"   Total Trades: {strat.trade_count}")
    print(f"   Winning:      {strat.winning_trades}")
    print(f"   Losing:       {strat.losing_trades}")

    if strat.trade_count > 0:
        win_rate = strat.winning_trades / strat.trade_count * 100
        print(f"   Win Rate:     {win_rate:.1f}%")

    # Test database write if requested
    if test_db_write and strat.trade_count > 0:
        print(f"\n5. Testing database write...")

        # Get Sharpe ratio
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = 0.0
        if sharpe_analysis and 'sharperatio' in sharpe_analysis:
            sharpe_value = sharpe_analysis['sharperatio']
            if sharpe_value is not None and not pd.isna(sharpe_value):
                sharpe_ratio = sharpe_value

        # Get drawdown
        dd_analysis = strat.analyzers.drawdown.get_analysis()
        max_drawdown_pct = 0.0
        if hasattr(dd_analysis, 'max') and hasattr(dd_analysis.max, 'drawdown'):
            max_drawdown_pct = dd_analysis.max.drawdown / 100.0

        # Create config
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

        config_name = f"test_supertrend_{symbol}_atr{strategy_params['atr_period']}_mult{strategy_params['atr_multiplier']}"

        config_params = (
            config_name,
            999,  # Test phase
            'regular',
            1,
            'Supertrend',
            strategy_params['atr_period'],
            strategy_params['atr_period'],
            strategy_params['atr_multiplier'],
            pd.io.json.dumps(strategy_params)
        )

        config_result = db.execute_query(config_query, config_params)
        config_id = config_result[0][0]

        print(f"   ✅ Created config_id: {config_id}")

        # Insert result
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
            symbol,
            (end_value - start_value) / start_value,
            sharpe_ratio,
            max_drawdown_pct,
            strat.trade_count,
            win_rate if strat.trade_count > 0 else 0.0
        )

        result_row = db.execute_query(results_query, results_params)
        result_id = result_row[0][0]

        print(f"   ✅ Created result_id: {result_id}")

        # Verify we can read it back
        verify_query = "SELECT * FROM backtest_results WHERE id = %s"
        verify_result = db.execute_query(verify_query, (result_id,))

        if verify_result:
            print(f"   ✅ Verified: Result successfully written to database!")
        else:
            print(f"   ❌ Error: Could not read back result!")

    elif strat.trade_count == 0:
        print(f"\n❌ NO TRADES GENERATED - Supertrend indicator bug still present!")
        print(f"   Check debug output above to see why direction never equals 1")

    db.close()

    print("\n" + "="*100)
    print("TEST COMPLETE")
    print("="*100 + "\n")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test Supertrend on single symbol')
    parser.add_argument(
        '--symbol',
        type=str,
        default='NVDA',
        help='Stock symbol to test (default: NVDA)'
    )
    parser.add_argument(
        '--no-db-write',
        action='store_true',
        help='Skip database write test'
    )

    args = parser.parse_args()

    test_supertrend_single_symbol(
        symbol=args.symbol,
        test_db_write=not args.no_db_write
    )
