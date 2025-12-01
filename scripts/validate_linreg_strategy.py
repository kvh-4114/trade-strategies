"""
LinReg Baseline Strategy Validation Test
=========================================

Validates the Linear Regression trading strategy against documented v3.0 results.
Uses data from the PostgreSQL database.

Expected Performance (from PRODUCTION_BASELINE_V3.0.md):
- Total Return: ~1,067% (conservative strategy with slope filter)
- Annualized Return: ~29.5%
- Max Drawdown: -7.09%
- Win Rate: 46.29%
- Profit Factor: 2.03
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
import os
import sys

# Add project root to path
sys.path.insert(0, '/home/user/trade-strategies')

from dotenv import load_dotenv
load_dotenv()

from agents.agent_5_infrastructure.database_manager import DatabaseManager


class HeikinAshiCalculator:
    """Calculate Heikin Ashi candles from OHLC data"""

    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Heikin Ashi candles.

        HA_Close = (Open + High + Low + Close) / 4
        HA_Open = (Previous HA_Open + Previous HA_Close) / 2
        HA_High = max(High, HA_Open, HA_Close)
        HA_Low = min(Low, HA_Open, HA_Close)
        """
        ha_df = df.copy()

        # HA Close
        ha_df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

        # HA Open (initialize first with regular calculation)
        ha_df['ha_open'] = (df['open'] + df['close']) / 2

        # Calculate HA Open iteratively
        for i in range(1, len(ha_df)):
            ha_df.iloc[i, ha_df.columns.get_loc('ha_open')] = (
                ha_df.iloc[i-1]['ha_open'] + ha_df.iloc[i-1]['ha_close']
            ) / 2

        # HA High and Low
        ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
        ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)

        return ha_df


class LinearRegressionIndicator:
    """Calculate Linear Regression candles from price data"""

    def __init__(self, period: int = 13, lookahead: int = 0):
        self.period = period
        self.lookahead = lookahead

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Linear Regression values for OHLC.

        For each bar, fits linear regression over the lookback period
        and projects to target_x = period - 1 + lookahead
        """
        result = df.copy()

        lr_open = []
        lr_high = []
        lr_low = []
        lr_close = []

        for i in range(len(df)):
            if i < self.period - 1:
                lr_open.append(np.nan)
                lr_high.append(np.nan)
                lr_low.append(np.nan)
                lr_close.append(np.nan)
                continue

            # Get window of data
            window_start = i - self.period + 1
            window_end = i + 1

            opens = df['ha_open'].iloc[window_start:window_end].values
            highs = df['ha_high'].iloc[window_start:window_end].values
            lows = df['ha_low'].iloc[window_start:window_end].values
            closes = df['ha_close'].iloc[window_start:window_end].values

            x = np.arange(self.period)
            target_x = self.period - 1 + self.lookahead

            # Linear regression for each OHLC
            open_coef = np.polyfit(x, opens, 1)
            high_coef = np.polyfit(x, highs, 1)
            low_coef = np.polyfit(x, lows, 1)
            close_coef = np.polyfit(x, closes, 1)

            lr_open.append(open_coef[0] * target_x + open_coef[1])
            lr_high.append(high_coef[0] * target_x + high_coef[1])
            lr_low.append(low_coef[0] * target_x + low_coef[1])
            lr_close.append(close_coef[0] * target_x + close_coef[1])

        result['lr_open'] = lr_open
        result['lr_high'] = lr_high
        result['lr_low'] = lr_low
        result['lr_close'] = lr_close

        return result


def resample_to_4day_bars(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily data to 4-day bars.
    Uses origin='epoch' for consistent bar boundaries across all symbols.
    """
    df_copy = df.copy()

    if 'date' in df_copy.columns:
        df_copy['date'] = pd.to_datetime(df_copy['date'])
        df_copy = df_copy.set_index('date')

    resampled = df_copy.resample('4D', origin='epoch').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    resampled = resampled.reset_index()
    return resampled


def calculate_entry_slope(df: pd.DataFrame, idx: int, period: int = 5) -> float:
    """
    Calculate entry slope using 5-period LinReg on HA close.
    Returns slope as percentage per bar, normalized by average price.
    """
    if idx < period - 1:
        return 0.0

    window_start = idx - period + 1
    window_end = idx + 1

    closes = df['ha_close'].iloc[window_start:window_end].values
    x = np.arange(period)

    coef = np.polyfit(x, closes, 1)
    slope = coef[0]  # dollars per bar

    avg_price = np.mean(closes)
    slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0

    return slope_pct


def get_position_size(slope: float, base_amount: float = 10000) -> float:
    """
    Get position size based on entry slope.

    Conservative Allocation Strategy:
    - >= 5.0%: $20,000 (2.0x)
    - >= 3.0%: $15,000 (1.5x)
    - >= 2.0%: $12,000 (1.2x)
    - >= 1.0%: $10,000 (1.0x)
    - < 1.0%: Skip ($0)
    """
    if slope >= 5.0:
        return base_amount * 2.0
    elif slope >= 3.0:
        return base_amount * 1.5
    elif slope >= 2.0:
        return base_amount * 1.2
    elif slope >= 1.0:
        return base_amount * 1.0
    else:
        return 0.0  # Skip trade


def run_strategy_on_symbol(df_daily: pd.DataFrame, symbol: str,
                           use_slope_filter: bool = True) -> list:
    """
    Run LinReg baseline strategy on a single symbol.

    Entry: 13-period LinReg (0 lookahead) - buy when LR green AND price > LR_high
    Exit: 21-period LinReg (-3 lookahead) - sell when LR red OR price < LR_low
    """
    trades = []

    # Resample to 4-day bars
    df_4day = resample_to_4day_bars(df_daily)

    if len(df_4day) < 50:
        return trades

    # Calculate Heikin Ashi
    df_ha = HeikinAshiCalculator.calculate(df_4day)

    # Calculate Entry LR (13-period, 0 lookahead)
    entry_lr = LinearRegressionIndicator(period=13, lookahead=0)
    df_entry = entry_lr.calculate(df_ha)

    # Calculate Exit LR (21-period, -3 lookahead)
    exit_lr = LinearRegressionIndicator(period=21, lookahead=-3)
    df_exit = exit_lr.calculate(df_entry)

    # Rename exit LR columns
    df_exit = df_exit.rename(columns={
        'lr_open': 'entry_lr_open',
        'lr_high': 'entry_lr_high',
        'lr_low': 'entry_lr_low',
        'lr_close': 'entry_lr_close'
    })

    # Recalculate exit LR
    exit_lr_calc = LinearRegressionIndicator(period=21, lookahead=-3)
    df_final = exit_lr_calc.calculate(df_exit)
    df_final = df_final.rename(columns={
        'lr_open': 'exit_lr_open',
        'lr_high': 'exit_lr_high',
        'lr_low': 'exit_lr_low',
        'lr_close': 'exit_lr_close'
    })

    # Trading logic
    position = None
    min_period = max(21, 13) + 3  # Need enough data for both LRs

    for i in range(min_period, len(df_final)):
        row = df_final.iloc[i]

        if pd.isna(row['entry_lr_close']) or pd.isna(row['exit_lr_close']):
            continue

        # Entry LR signals
        entry_lr_green = row['entry_lr_close'] > row['entry_lr_open']
        price_above_entry_lr_high = row['close'] > row['entry_lr_high']

        # Exit LR signals
        exit_lr_red = row['exit_lr_close'] < row['exit_lr_open']
        price_below_exit_lr_low = row['close'] < row['exit_lr_low']

        if position is None:
            # Check for entry
            if entry_lr_green and price_above_entry_lr_high:
                # Calculate entry slope
                slope = calculate_entry_slope(df_final, i, period=5)

                if use_slope_filter:
                    position_size = get_position_size(slope)
                    if position_size == 0:
                        continue  # Skip trade
                else:
                    position_size = 10000  # Fixed size without filter

                position = {
                    'symbol': symbol,
                    'entry_date': row['date'],
                    'entry_price': row['close'],
                    'entry_idx': i,
                    'slope': slope,
                    'position_size': position_size,
                    'shares': position_size / row['close']
                }
        else:
            # Check for exit
            if exit_lr_red or price_below_exit_lr_low:
                exit_price = row['close']
                pnl = (exit_price - position['entry_price']) * position['shares']
                pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                hold_days = (row['date'] - position['entry_date']).days

                trade = {
                    'symbol': symbol,
                    'entry_date': position['entry_date'],
                    'exit_date': row['date'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'shares': position['shares'],
                    'position_size': position['position_size'],
                    'slope': position['slope'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'hold_days': hold_days,
                    'status': 'CLOSED'
                }
                trades.append(trade)
                position = None

    # Record any open position at end
    if position is not None:
        last_row = df_final.iloc[-1]
        exit_price = last_row['close']
        pnl = (exit_price - position['entry_price']) * position['shares']
        pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
        hold_days = (last_row['date'] - position['entry_date']).days

        trade = {
            'symbol': symbol,
            'entry_date': position['entry_date'],
            'exit_date': last_row['date'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'shares': position['shares'],
            'position_size': position['position_size'],
            'slope': position['slope'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_days': hold_days,
            'status': 'OPEN'
        }
        trades.append(trade)

    return trades


def calculate_portfolio_metrics(trades_df: pd.DataFrame,
                                starting_capital: float = 1_000_000) -> dict:
    """Calculate portfolio performance metrics from trades."""

    if len(trades_df) == 0:
        return {}

    # Separate closed and open trades
    closed_trades = trades_df[trades_df['status'] == 'CLOSED'].copy()
    open_trades = trades_df[trades_df['status'] == 'OPEN'].copy()

    if len(closed_trades) == 0:
        return {}

    # Sort by exit date
    closed_trades = closed_trades.sort_values('exit_date')

    # Calculate cumulative metrics
    closed_trades['cumulative_pnl'] = closed_trades['pnl'].cumsum()
    closed_trades['portfolio_value'] = starting_capital + closed_trades['cumulative_pnl']
    closed_trades['peak'] = closed_trades['portfolio_value'].cummax()
    closed_trades['drawdown'] = closed_trades['portfolio_value'] - closed_trades['peak']
    closed_trades['drawdown_pct'] = (closed_trades['drawdown'] / closed_trades['peak']) * 100

    total_pnl = closed_trades['pnl'].sum()
    total_return = (total_pnl / starting_capital) * 100
    final_value = starting_capital + total_pnl
    max_drawdown = closed_trades['drawdown_pct'].min()

    # Trade statistics
    winners = closed_trades[closed_trades['pnl'] > 0]
    losers = closed_trades[closed_trades['pnl'] <= 0]
    win_rate = len(winners) / len(closed_trades) * 100 if len(closed_trades) > 0 else 0

    total_wins = winners['pnl'].sum() if len(winners) > 0 else 0
    total_losses = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else 0

    avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
    avg_hold = closed_trades['hold_days'].mean()

    # Calculate annualized return
    if len(closed_trades) > 0:
        date_range = (closed_trades['exit_date'].max() - closed_trades['exit_date'].min()).days
        years = date_range / 365.25 if date_range > 0 else 1
        annualized_return = ((1 + total_return/100) ** (1/years) - 1) * 100
    else:
        annualized_return = 0

    return {
        'total_trades': len(trades_df),
        'closed_trades': len(closed_trades),
        'open_trades': len(open_trades),
        'total_pnl': total_pnl,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'final_value': final_value,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_hold_days': avg_hold,
        'winning_trades': len(winners),
        'losing_trades': len(losers),
        'unrealized_pnl': open_trades['pnl'].sum() if len(open_trades) > 0 else 0
    }


def main():
    """Run validation test of LinReg strategy against database data."""

    print("=" * 100)
    print("LinReg Baseline Strategy Validation Test")
    print("=" * 100)

    # Connect to database
    print("\nConnecting to database...")
    db = DatabaseManager()

    # Get available symbols
    symbols = db.get_available_symbols()
    print(f"Found {len(symbols)} symbols in database")

    # Full run with all symbols
    test_symbols = symbols  # All symbols
    print(f"Testing with ALL {len(test_symbols)} symbols...")

    # Run strategy on each symbol
    all_trades = []
    symbols_processed = 0
    symbols_with_trades = 0

    print("\nProcessing symbols...")

    for i, symbol in enumerate(test_symbols):
        try:
            # Load daily data from database
            df = db.load_stock_data(symbol)

            if len(df) < 100:
                continue

            # Convert Decimal columns to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            # Reset index if date is index
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()

            # Ensure date column exists and is datetime
            if 'date' not in df.columns and df.index.name == 'date':
                df = df.reset_index()

            df['date'] = pd.to_datetime(df.index if 'date' not in df.columns else df['date'])

            # Run strategy with slope filter (Conservative)
            trades = run_strategy_on_symbol(df, symbol, use_slope_filter=True)

            if trades:
                all_trades.extend(trades)
                symbols_with_trades += 1

            symbols_processed += 1

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(test_symbols)} symbols...")

        except Exception as e:
            print(f"  Error processing {symbol}: {e}")
            continue

    print(f"\nProcessed {symbols_processed} symbols")
    print(f"Symbols with trades: {symbols_with_trades}")
    print(f"Total trades: {len(all_trades)}")

    if len(all_trades) == 0:
        print("\n[ERROR] No trades generated!")
        db.close()
        return

    # Convert to DataFrame
    trades_df = pd.DataFrame(all_trades)

    # Calculate portfolio metrics
    metrics = calculate_portfolio_metrics(trades_df)

    print("\n" + "=" * 100)
    print("VALIDATION RESULTS")
    print("=" * 100)

    print("\nPortfolio Performance:")
    print(f"  Total P&L: ${metrics['total_pnl']:,.0f}")
    print(f"  Total Return: {metrics['total_return']:.2f}%")
    print(f"  Annualized Return: {metrics['annualized_return']:.2f}%")
    print(f"  Final Value: ${metrics['final_value']:,.0f}")

    print("\nRisk Metrics:")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")

    print("\nTrade Statistics:")
    print(f"  Total Trades: {metrics['total_trades']:,}")
    print(f"  Closed Trades: {metrics['closed_trades']:,}")
    print(f"  Open Positions: {metrics['open_trades']:,}")
    print(f"  Win Rate: {metrics['win_rate']:.2f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Avg Win: ${metrics['avg_win']:,.0f}")
    print(f"  Avg Loss: ${metrics['avg_loss']:,.0f}")
    print(f"  Avg Hold Time: {metrics['avg_hold_days']:.0f} days")

    print("\n" + "=" * 100)
    print("COMPARISON TO DOCUMENTED v3.0 RESULTS")
    print("=" * 100)

    expected_metrics = {
        'total_return': 1067.52,  # Conservative strategy
        'annualized_return': 29.50,
        'max_drawdown': -7.09,
        'win_rate': 46.29,
        'profit_factor': 2.03
    }

    print("\n{:<25} {:>15} {:>15} {:>15}".format(
        "Metric", "Expected", "Actual", "Difference"
    ))
    print("-" * 70)

    # Scale expected values based on number of symbols tested
    scale_factor = len(test_symbols) / 270  # Full dataset has 270 symbols

    for metric_name, expected in expected_metrics.items():
        actual = metrics.get(metric_name.replace('_', '_'), 0)

        # Don't scale percentage metrics
        if metric_name in ['win_rate', 'profit_factor', 'max_drawdown', 'annualized_return']:
            scaled_expected = expected
        else:
            scaled_expected = expected * scale_factor

        diff = actual - scaled_expected
        print(f"{metric_name:<25} {scaled_expected:>15.2f} {actual:>15.2f} {diff:>+15.2f}")

    print("\n" + "=" * 100)
    print("NOTE: Running on subset of symbols. Full validation requires all 268 symbols.")
    print("=" * 100)

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'/home/user/trade-strategies/data/results/validation_trades_{timestamp}.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    trades_df.to_csv(output_file, index=False)
    print(f"\n[SAVED] {output_file}")

    db.close()

    return trades_df, metrics


if __name__ == '__main__':
    trades_df, metrics = main()
