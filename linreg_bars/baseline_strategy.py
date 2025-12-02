"""
OPTIMIZED 4-DAY BAR STRATEGY - PRODUCTION BASELINE v2.0
========================================================

Linear Regression Chandelier Strategy on 4-Day Bars
Using Heikin Ashi candles with OPTIMIZED dual LR configuration

OPTIMIZATION HISTORY:
---------------------
Original Baseline (v1.0):
  - Entry LR: 13-period, -1 lookahead
  - Exit LR: 13-period, -1 lookahead
  - Return: 511%
  - Profit Factor: 1.81

Optimized Baseline (v2.0):
  - Entry LR: 13-period, 0 lookahead (OPTIMIZED)
  - Exit LR: 21-period, -3 lookahead (OPTIMIZED)
  - Return: 659%
  - Profit Factor: 2.00
  - Improvement: +148 percentage points (+29.0%)

OPTIMIZATION EXPERIMENTS CONDUCTED:
-----------------------------------
1. Volume Filters: FAILED (-70% return) - Do not use
2. Exit Strategies (ATR, targets, etc.): FAILED (-5% return) - Keep LR-based
3. Exit Period (Dual LR): SUCCESS (+8.4% return) - Use 21-period for exits
4. Exit Lookahead: MAJOR SUCCESS (+17.6% return) - Use -3 lookahead
5. Entry Lookahead: SUCCESS (+1.2% return) - Use 0 lookahead

KEY INSIGHT:
-----------
Asymmetric LR configuration works best:
- FAST ENTRY (13-period, 0 lookahead) = Catch trends early
- SLOW EXIT (21-period, -3 lookahead) = Let winners run

STRATEGY PARAMETERS:
--------------------
Entry Rules:
  - Bar Length: 4 days (resampled from daily data)
  - Entry LR: 13-period, 0 lookahead (current bar projection)
  - Signal: LR close > LR open (green candle) AND price closes above LR high
  - Initial Position: $7,000
  - Pyramid: $5,000 (one-time add on same signal)

Exit Rules:
  - Exit LR: 21-period, -3 lookahead (very smooth/backcast)
  - Signal: LR close < LR open (red candle) OR price closes below LR low

Position Management:
  - Starting Capital: $1,000,000
  - Commission: 0.1% per trade
  - Pyramiding: Allowed once per position

EXPECTED PERFORMANCE (Backtested):
----------------------------------
- Total Return: 659.32%
- Profit Factor: 2.00
- Win Rate: 46.1%
- Max Drawdown: -11.45%
- Average Hold Time: 45 days
- Total Trades: 20,856

DATA REQUIREMENTS:
------------------
- Daily OHLCV data from historical_data/11_14_2025_daily
- Minimum 100 days of daily data per symbol
- Date range: Full history through Nov 7, 2025

USAGE:
------
    python baseline_strategy.py

AUTHOR: Claude Code Experiments
DATE: November 2025
VERSION: 2.0 (Optimized) - COPIED FOR SLOPE THRESHOLD EXPERIMENTS
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime
import os
import glob

# ============================================================================
# INDICATORS
# ============================================================================

class HeikinAshi(bt.Indicator):
    """Heikin Ashi Candlesticks"""
    lines = ('ha_open', 'ha_high', 'ha_low', 'ha_close')

    def __init__(self):
        self.lines.ha_close = (self.data.open + self.data.high +
                               self.data.low + self.data.close) / 4.0
        self.lines.ha_open = (self.data.open + self.data.close) / 2.0

    def next(self):
        if len(self) > 1:
            self.lines.ha_open[0] = (self.lines.ha_open[-1] +
                                     self.lines.ha_close[-1]) / 2.0

        self.lines.ha_high[0] = max(self.data.high[0],
                                    self.lines.ha_open[0],
                                    self.lines.ha_close[0])
        self.lines.ha_low[0] = min(self.data.low[0],
                                   self.lines.ha_open[0],
                                   self.lines.ha_close[0])


class LinearRegressionCandles(bt.Indicator):
    """
    Linear Regression applied to Heikin Ashi candles

    Creates smoothed OHLC values using linear regression projection.
    Lookahead parameter controls the projection point:
      +1 = forward/predictive
       0 = current bar
      -1 = symmetric/backcast
      -3 = very smooth/backcast
    """
    lines = ('lr_open', 'lr_high', 'lr_low', 'lr_close')
    params = (('period', 13), ('lookahead', -1))

    def __init__(self):
        self.ha = HeikinAshi(self.data)
        self.addminperiod(self.params.period + abs(self.params.lookahead))

    def next(self):
        lookback = self.params.period
        lookahead = self.params.lookahead

        # Collect HA candle data
        ha_opens = [self.ha.ha_open[-i] for i in range(lookback-1, -1, -1)]
        ha_highs = [self.ha.ha_high[-i] for i in range(lookback-1, -1, -1)]
        ha_lows = [self.ha.ha_low[-i] for i in range(lookback-1, -1, -1)]
        ha_closes = [self.ha.ha_close[-i] for i in range(lookback-1, -1, -1)]

        # Linear regression
        x = np.arange(lookback)

        open_lr = np.polyfit(x, ha_opens, 1)
        high_lr = np.polyfit(x, ha_highs, 1)
        low_lr = np.polyfit(x, ha_lows, 1)
        close_lr = np.polyfit(x, ha_closes, 1)

        # Project to target bar
        target_x = lookback - 1 + lookahead

        self.lines.lr_open[0] = open_lr[0] * target_x + open_lr[1]
        self.lines.lr_high[0] = high_lr[0] * target_x + high_lr[1]
        self.lines.lr_low[0] = low_lr[0] * target_x + low_lr[1]
        self.lines.lr_close[0] = close_lr[0] * target_x + close_lr[1]


# ============================================================================
# STRATEGY
# ============================================================================

class OptimizedDualLRStrategy(bt.Strategy):
    """
    Optimized 4-Day Linear Regression Strategy with Dual LR Configuration

    Key Innovation: Uses different LR configurations for entry vs exit
    - Entry LR: Fast (13-period, 0 lookahead) to catch trends early
    - Exit LR: Slow (21-period, -3 lookahead) to let winners run

    This asymmetric approach improved returns by 29% vs baseline.
    """

    params = (
        ('entry_lr_period', 13),
        ('entry_lr_lookahead', 0),      # OPTIMIZED: 0 for responsive entries
        ('exit_lr_period', 21),          # OPTIMIZED: 21 for patient exits
        ('exit_lr_lookahead', -3),       # OPTIMIZED: -3 for smooth exits
        ('initial_capital', 7000),
        ('pyramid_capital', 5000),
        ('printlog', False),
    )

    def __init__(self):
        # Entry LR: Fast and responsive
        self.entry_lr = LinearRegressionCandles(
            self.data,
            period=self.params.entry_lr_period,
            lookahead=self.params.entry_lr_lookahead
        )

        # Exit LR: Slow and smooth
        self.exit_lr = LinearRegressionCandles(
            self.data,
            period=self.params.exit_lr_period,
            lookahead=self.params.exit_lr_lookahead
        )

        self.order = None
        self.trades_list = []
        self.entry_price = None
        self.entry_date = None
        self.pyramid_executed = False

        # Track individual entries for pyramid analysis
        self.active_entries = []  # List of entry records

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                # Record this buy as an active entry
                entry_type = 'pyramid' if len(self.active_entries) > 0 else 'first_entry'
                self.active_entries.append({
                    'entry_price': order.executed.price,
                    'size': order.executed.size,
                    'entry_date': self.data.datetime.date(0),
                    'entry_type': entry_type,
                    'value': order.executed.price * order.executed.size
                })
            self.order = None

    def next(self):
        if self.order:
            return

        # Check if we have valid LR values
        if len(self.entry_lr.lr_close) < 1 or len(self.exit_lr.lr_close) < 1:
            return

        # Entry logic uses ENTRY LR (fast)
        entry_lr_green = self.entry_lr.lr_close[0] > self.entry_lr.lr_open[0]
        current_price = self.data.close[0]

        # Exit logic uses EXIT LR (slow)
        exit_lr_red = self.exit_lr.lr_close[0] < self.exit_lr.lr_open[0]

        if not self.position:
            # Initial entry - use fast entry LR
            self.pyramid_executed = False
            if entry_lr_green and current_price > self.entry_lr.lr_high[0]:
                size = int(self.params.initial_capital / current_price)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.entry_price = current_price
                    self.entry_date = self.data.datetime.date(0)

        elif self.position and not self.pyramid_executed:
            # Pyramid entry - use fast entry LR
            if entry_lr_green and current_price > self.entry_lr.lr_high[0]:
                size = int(self.params.pyramid_capital / current_price)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.pyramid_executed = True

        elif self.position:
            # Exit logic - use slow exit LR (lets winners run)
            if exit_lr_red or current_price < self.exit_lr.lr_low[0]:
                self.order = self.sell(size=self.position.size)

    def notify_trade(self, trade):
        if trade.isclosed:
            # When a position closes, record each individual entry as a separate trade
            exit_date = self.data.datetime.date(0)
            exit_price = self.data.close[0]

            # Calculate P&L for each entry proportionally
            for entry in self.active_entries:
                entry_value = entry['value']
                entry_pnl = (exit_price - entry['entry_price']) * entry['size']
                entry_pnl_pct = (entry_pnl / entry_value) * 100 if entry_value > 0 else 0
                hold_days = (exit_date - entry['entry_date']).days

                trade_record = {
                    'symbol': trade.data._name,
                    'entry_date': entry['entry_date'],
                    'exit_date': exit_date,
                    'entry_price': entry['entry_price'],
                    'exit_price': exit_price,
                    'size': entry['size'],
                    'pnl': entry_pnl,
                    'pnl_pct': entry_pnl_pct,
                    'value': entry_value,
                    'entry_type': entry['entry_type'],
                    'status': 'CLOSED',
                    'hold_days': hold_days
                }
                self.trades_list.append(trade_record)

            # Clear active entries
            self.active_entries = []

    def stop(self):
        # Record any open positions at the end
        if self.position and len(self.active_entries) > 0:
            exit_date = self.data.datetime.date(0)
            exit_price = self.data.close[0]

            for entry in self.active_entries:
                entry_value = entry['value']
                unrealized_pnl = (exit_price - entry['entry_price']) * entry['size']
                unrealized_pnl_pct = (unrealized_pnl / entry_value) * 100 if entry_value > 0 else 0
                hold_days = (exit_date - entry['entry_date']).days

                self.trades_list.append({
                    'symbol': self.data._name,
                    'entry_date': entry['entry_date'],
                    'exit_date': exit_date,
                    'entry_price': entry['entry_price'],
                    'exit_price': exit_price,
                    'size': entry['size'],
                    'pnl': unrealized_pnl,
                    'pnl_pct': unrealized_pnl_pct,
                    'value': entry_value,
                    'entry_type': entry['entry_type'],
                    'status': 'OPEN',
                    'hold_days': hold_days
                })


# ============================================================================
# DATA RESAMPLING
# ============================================================================

def resample_daily_to_4days(df_daily):
    """Resample daily data to 4-day bars

    Uses origin='epoch' to ensure all symbols have identical bar boundaries.
    Each successive bar ends on a different day of the week (4-day cycle).
    Critical for portfolio synchronization - all symbols must trade on the same bars.
    """
    df = df_daily.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df.set_index('date', inplace=True)

    resampled = df.resample('4D', origin='epoch').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    resampled.reset_index(inplace=True)
    return resampled


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_optimized_strategy():
    """Run optimized 4-day strategy on all symbols"""

    print("="*100)
    print("OPTIMIZED 4-DAY BAR STRATEGY - PRODUCTION BASELINE v2.0")
    print("="*100)

    # Configuration
    DAILY_DATA_PATH = r'C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_22_25_daily'
    STARTING_CASH = 1_000_000
    INITIAL_CAPITAL = 7_000
    PYRAMID_CAPITAL = 5_000

    print(f"\nStarting Capital: ${STARTING_CASH:,}")
    print(f"Initial Entry: ${INITIAL_CAPITAL:,}")
    print(f"Pyramid: ${PYRAMID_CAPITAL:,}")
    print(f"\nOPTIMIZED CONFIGURATION:")
    print(f"  Entry LR: 13-period, 0 lookahead (fast/responsive)")
    print(f"  Exit LR: 21-period, -3 lookahead (slow/smooth)")
    print(f"  Expected Return: 659%+ (vs 511% baseline)")
    print(f"  Data Directory: {DAILY_DATA_PATH}")

    # Find all daily data files
    pattern = os.path.join(DAILY_DATA_PATH, '*_trades_*.csv')
    files = glob.glob(pattern)

    print(f"\nFound {len(files)} data files")

    if len(files) == 0:
        print(f"\n[ERROR] No files found matching: {pattern}")
        return []

    # Process each symbol
    all_trades = []
    symbols_processed = 0
    symbols_with_data = 0

    print(f"\n{'='*100}")
    print("Processing Symbols...")
    print(f"{'='*100}")

    for file_path in sorted(files):
        symbol = os.path.basename(file_path).split('_')[0]

        try:
            # Load daily data
            df_daily = pd.read_csv(file_path)

            if len(df_daily) < 100:
                continue

            # Resample to 4-day bars
            df_4day = resample_daily_to_4days(df_daily)

            if len(df_4day) < 50:
                continue

            # Create cerebro for this symbol
            cerebro = bt.Cerebro()
            cerebro.broker.setcash(STARTING_CASH)
            cerebro.broker.setcommission(commission=0.001)

            # Add data
            data = bt.feeds.PandasData(
                dataname=df_4day,
                datetime='date',
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            data._name = symbol
            cerebro.adddata(data)

            # Add OPTIMIZED strategy
            cerebro.addstrategy(OptimizedDualLRStrategy,
                                entry_lr_period=13,
                                entry_lr_lookahead=0,      # OPTIMIZED
                                exit_lr_period=21,         # OPTIMIZED
                                exit_lr_lookahead=-3,      # OPTIMIZED
                                initial_capital=INITIAL_CAPITAL,
                                pyramid_capital=PYRAMID_CAPITAL,
                                printlog=False)

            # Run
            results = cerebro.run()
            strat = results[0]

            symbols_processed += 1

            if strat.trades_list:
                all_trades.extend(strat.trades_list)
                symbols_with_data += 1

        except Exception as e:
            continue

    print(f"\n{'='*100}")
    print("PROCESSING COMPLETE")
    print(f"{'='*100}")
    print(f"Symbols processed: {symbols_processed}")
    print(f"Symbols with trades: {symbols_with_data}")
    print(f"Total trades: {len(all_trades)}")

    if len(all_trades) == 0:
        print("\n[ERROR] No trades generated")
        return []

    # Convert to DataFrame
    df_trades = pd.DataFrame(all_trades)

    # Separate open and closed trades
    df_open = df_trades[df_trades.get('status') == 'OPEN'].copy() if 'status' in df_trades.columns else pd.DataFrame()
    df_closed = df_trades[df_trades.get('status') == 'CLOSED'].copy() if 'status' in df_trades.columns else df_trades.copy()

    print(f"\nClosed trades: {len(df_closed)}")
    print(f"Open positions: {len(df_open)}")

    # Sort CLOSED trades by exit date for performance calculation
    df_closed_sorted = df_closed.sort_values('exit_date').reset_index(drop=True) if len(df_closed) > 0 else df_closed

    # Calculate cumulative performance (CLOSED TRADES ONLY)
    if len(df_closed_sorted) > 0:
        df_closed_sorted['cumulative_pnl'] = df_closed_sorted['pnl'].cumsum()
        df_closed_sorted['portfolio_value'] = STARTING_CASH + df_closed_sorted['cumulative_pnl']
        df_closed_sorted['peak'] = df_closed_sorted['portfolio_value'].cummax()
        df_closed_sorted['drawdown'] = df_closed_sorted['portfolio_value'] - df_closed_sorted['peak']
        df_closed_sorted['drawdown_pct'] = (df_closed_sorted['drawdown'] / df_closed_sorted['peak']) * 100

    # Calculate performance metrics (CLOSED TRADES ONLY)
    total_pnl = df_closed_sorted['pnl'].sum() if len(df_closed_sorted) > 0 else 0
    total_return = (total_pnl / STARTING_CASH) * 100
    final_value = STARTING_CASH + total_pnl
    max_drawdown = df_closed_sorted['drawdown_pct'].min() if len(df_closed_sorted) > 0 else 0
    risk_adjusted = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

    winners = df_closed_sorted[df_closed_sorted['pnl'] > 0] if len(df_closed_sorted) > 0 else pd.DataFrame()
    losers = df_closed_sorted[df_closed_sorted['pnl'] <= 0] if len(df_closed_sorted) > 0 else pd.DataFrame()
    win_rate = len(winners) / len(df_closed_sorted) * 100 if len(df_closed_sorted) > 0 else 0
    avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
    profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 and losers['pnl'].sum() != 0 else 0

    avg_hold = df_closed['hold_days'].mean() if len(df_closed) > 0 and 'hold_days' in df_closed.columns else 0

    print(f"\n{'='*100}")
    print("PERFORMANCE SUMMARY - OPTIMIZED BASELINE v2.0")
    print(f"{'='*100}")
    print(f"\nReturns:")
    print(f"  Total P&L: ${total_pnl:,.0f}")
    print(f"  Total Return: {total_return:.2f}%")
    print(f"  Final Value: ${final_value:,.0f}")
    print(f"\nRisk:")
    print(f"  Max Drawdown: {max_drawdown:.2f}%")
    print(f"  Risk-Adjusted Return: {risk_adjusted:.2f}")
    print(f"\nTrade Statistics:")
    print(f"  Total Trades: {len(df_trades):,}")
    print(f"  Closed Trades: {len(df_closed):,}")
    print(f"  Open Positions: {len(df_open):,}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  Avg Win: ${avg_win:,.0f}")
    print(f"  Avg Loss: ${avg_loss:,.0f}")
    print(f"  Avg Hold Time: {avg_hold:.0f} days")

    print(f"\n{'='*100}")
    print("IMPROVEMENT VS ORIGINAL BASELINE v1.0")
    print(f"{'='*100}")
    print(f"  Original Return: 511%")
    print(f"  Optimized Return: {total_return:.2f}%")
    print(f"  Improvement: +{total_return - 511:.2f} percentage points (+{((total_return - 511) / 511 * 100):.1f}%)")

    if len(df_open) > 0:
        print(f"\n{'='*100}")
        print(f"OPEN POSITIONS (as of {df_open['exit_date'].max()})")
        print(f"{'='*100}")
        print(f"\nTotal open positions: {len(df_open)}")
        print(f"Total unrealized P&L: ${df_open['pnl'].sum():,.0f}")
        print(f"\nTop 10 Open Positions by P&L:")
        print(df_open.nlargest(10, 'pnl')[['symbol', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'size', 'pnl', 'pnl_pct']].to_string(index=False))

        print(f"\nBottom 10 Open Positions by P&L:")
        print(df_open.nsmallest(10, 'pnl')[['symbol', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'size', 'pnl', 'pnl_pct']].to_string(index=False))

    # Save results (all trades with status field)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'results/baseline_trades_{timestamp}.csv'
    df_trades.to_csv(output_file, index=False)

    print(f"\n{'='*100}")
    print(f"[SAVED] {output_file}")
    print(f"{'='*100}")

    return all_trades


if __name__ == '__main__':
    trades = run_optimized_strategy()
