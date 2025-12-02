#!/usr/bin/env python3
"""
Breakout Momentum - Detailed Annual Analysis

Uses optimal config: heiken_ashi_1d, BO10_BD5_TS25
"""

import os
import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'mean_reversion'),
    'user': os.getenv('DB_USER', 'trader'),
    'password': os.getenv('DB_PASSWORD', 'trader123')
}

# Optimal parameters
CANDLE_TYPE = 'heiken_ashi'
AGGREGATION = 1
BREAKOUT_PERIOD = 10
BREAKDOWN_PERIOD = 5
TRAILING_STOP = 0.25
VOLUME_MULT = 1.5
TREND_MA = 50
MAX_HOLD = 60

INITIAL_CAPITAL = 1000000
POSITION_SIZE = 10000
MAX_POSITIONS = 50


class BreakoutAnnualAnalysis:
    def __init__(self):
        self.trades = []
        self.daily_values = []

    def run_backtest(self, all_data):
        self.trades = []
        self.daily_values = []

        start_date = pd.to_datetime('2017-04-01')
        end_date = pd.to_datetime('2025-11-01')

        all_dates = set()
        for df in all_data.values():
            all_dates.update(df.index.tolist())
        all_dates = sorted([d for d in all_dates if start_date <= d <= end_date])

        cash = INITIAL_CAPITAL
        positions = {}
        peak = INITIAL_CAPITAL

        for date in all_dates:
            # Update highest prices
            for symbol in positions:
                if symbol in all_data and date in all_data[symbol].index:
                    price = all_data[symbol].loc[date, 'close']
                    if price > positions[symbol]['highest']:
                        positions[symbol]['highest'] = price

            # Check exits
            for symbol in list(positions.keys()):
                if symbol not in all_data:
                    continue
                df = all_data[symbol]
                if date not in df.index:
                    continue

                idx = df.index.get_loc(date)
                pos = positions[symbol]
                current = df['close'].iloc[idx]

                should_exit = False
                reason = None

                # Breakdown
                if idx >= BREAKDOWN_PERIOD:
                    m_low = df['low'].iloc[idx - BREAKDOWN_PERIOD:idx].min()
                    if current < m_low:
                        should_exit = True
                        reason = 'breakdown'

                # Trailing stop
                if not should_exit:
                    stop_price = pos['highest'] * (1 - TRAILING_STOP)
                    if current < stop_price:
                        should_exit = True
                        reason = 'trailing'

                # Max hold
                if not should_exit and (idx - pos['entry_idx']) >= MAX_HOLD:
                    should_exit = True
                    reason = 'max_hold'

                if should_exit:
                    pnl = (current - pos['entry_price']) * pos['shares']
                    pnl_pct = ((current / pos['entry_price']) - 1) * 100
                    cash += pos['shares'] * current

                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': date,
                        'entry_price': pos['entry_price'],
                        'exit_price': current,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': reason,
                        'hold_days': idx - pos['entry_idx'],
                        'exit_year': date.year
                    })
                    del positions[symbol]

            # Check entries
            if len(positions) < MAX_POSITIONS:
                for symbol, df in all_data.items():
                    if symbol in positions or date not in df.index:
                        continue

                    idx = df.index.get_loc(date)
                    if idx < max(BREAKOUT_PERIOD, TREND_MA, 20):
                        continue

                    current = df['close'].iloc[idx]
                    vol = df['volume'].iloc[idx]

                    n_high = df['high'].iloc[idx - BREAKOUT_PERIOD:idx].max()
                    avg_vol = df['volume'].iloc[idx - 20:idx].mean()
                    ma = df['close'].iloc[idx - TREND_MA:idx].mean()

                    if current > n_high and vol > avg_vol * VOLUME_MULT and current > ma:
                        if cash >= POSITION_SIZE and current > 0:
                            shares = int(POSITION_SIZE / current)
                            if shares > 0:
                                cash -= shares * current
                                positions[symbol] = {
                                    'entry_idx': idx,
                                    'entry_price': current,
                                    'entry_date': date,
                                    'shares': shares,
                                    'highest': current
                                }
                                if len(positions) >= MAX_POSITIONS:
                                    break

            # Track daily value
            pos_val = sum(
                pos['shares'] * all_data[sym].loc[date, 'close']
                if sym in all_data and date in all_data[sym].index
                else pos['shares'] * pos['entry_price']
                for sym, pos in positions.items()
            )
            total = cash + pos_val
            peak = max(peak, total)
            dd = ((total - peak) / peak) * 100

            self.daily_values.append({
                'date': date,
                'value': total,
                'cash': cash,
                'positions': len(positions),
                'peak': peak,
                'drawdown': dd
            })

        # Close remaining
        for symbol, pos in list(positions.items()):
            if symbol in all_data and len(all_data[symbol]) > 0:
                exit_price = all_data[symbol]['close'].iloc[-1]
                pnl = (exit_price - pos['entry_price']) * pos['shares']
                self.trades.append({
                    'symbol': symbol,
                    'entry_date': pos['entry_date'],
                    'exit_date': all_data[symbol].index[-1],
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': ((exit_price / pos['entry_price']) - 1) * 100,
                    'reason': 'end',
                    'hold_days': len(all_data[symbol]) - pos['entry_idx'],
                    'exit_year': all_data[symbol].index[-1].year
                })

        return pd.DataFrame(self.trades), pd.DataFrame(self.daily_values)


def load_data():
    conn = psycopg2.connect(**DB_CONFIG)

    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM candles WHERE candle_type = %s ORDER BY symbol", (CANDLE_TYPE,))
        symbols = [r[0] for r in cur.fetchall()]

    print(f"Loading {CANDLE_TYPE}_{AGGREGATION}d data for {len(symbols)} symbols...")
    all_data = {}

    for symbol in symbols:
        query = """
            SELECT date, open, high, low, close, volume FROM candles
            WHERE symbol = %s AND candle_type = %s AND aggregation_days = %s
            ORDER BY date
        """
        with conn.cursor() as cur:
            cur.execute(query, (symbol, CANDLE_TYPE, AGGREGATION))
            rows = cur.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                all_data[symbol] = df

    conn.close()
    print(f"Loaded {len(all_data)} symbols")
    return all_data


def main():
    print("=" * 100)
    print("BREAKOUT MOMENTUM - DETAILED ANNUAL ANALYSIS")
    print("=" * 100)
    print(f"Config: {CANDLE_TYPE}_{AGGREGATION}d, BO{BREAKOUT_PERIOD}_BD{BREAKDOWN_PERIOD}_TS{int(TRAILING_STOP*100)}")
    print("-" * 100)

    all_data = load_data()

    strategy = BreakoutAnnualAnalysis()
    trades_df, portfolio_df = strategy.run_backtest(all_data)

    # Annual analysis
    portfolio_df['year'] = portfolio_df['date'].dt.year
    trades_df['exit_year'] = pd.to_datetime(trades_df['exit_date']).dt.year

    years = sorted(portfolio_df['year'].unique())

    print(f"\n{'Year':>6} {'Return':>10} {'MaxDD':>10} {'Trades':>8} {'Wins':>6} {'Losses':>8} {'WinRate':>10} {'PF':>8} {'AvgWin':>10} {'AvgLoss':>10} {'AvgHold':>8}")
    print("-" * 108)

    annual_data = []
    for year in years:
        yp = portfolio_df[portfolio_df['year'] == year]
        yt = trades_df[trades_df['exit_year'] == year]

        if len(yp) < 2:
            continue

        start_val = yp['value'].iloc[0]
        end_val = yp['value'].iloc[-1]
        year_return = ((end_val / start_val) - 1) * 100
        year_dd = yp['drawdown'].min()

        n_trades = len(yt)
        if n_trades > 0:
            wins = len(yt[yt['pnl'] > 0])
            losses = len(yt[yt['pnl'] < 0])
            win_rate = (wins / n_trades) * 100

            gp = yt[yt['pnl'] > 0]['pnl'].sum()
            gl = abs(yt[yt['pnl'] < 0]['pnl'].sum())
            pf = gp / gl if gl > 0 else 999

            avg_win = yt[yt['pnl'] > 0]['pnl_pct'].mean() if wins > 0 else 0
            avg_loss = yt[yt['pnl'] < 0]['pnl_pct'].mean() if losses > 0 else 0
            avg_hold = yt['hold_days'].mean()
        else:
            wins = losses = 0
            win_rate = pf = avg_win = avg_loss = avg_hold = 0

        annual_data.append({
            'year': year, 'return': year_return, 'max_dd': year_dd,
            'trades': n_trades, 'wins': wins, 'losses': losses,
            'win_rate': win_rate, 'pf': min(pf, 999),
            'avg_win': avg_win, 'avg_loss': avg_loss, 'avg_hold': avg_hold
        })

        print(f"{year:>6} {year_return:>9.2f}% {year_dd:>9.2f}% {n_trades:>8} {wins:>6} {losses:>8} "
              f"{win_rate:>9.2f}% {min(pf,999):>8.2f} {avg_win:>9.2f}% {avg_loss:>9.2f}% {avg_hold:>8.1f}")

    # Totals
    print("-" * 108)
    total_return = ((portfolio_df['value'].iloc[-1] / INITIAL_CAPITAL) - 1) * 100
    total_trades = len(trades_df)
    total_wins = len(trades_df[trades_df['pnl'] > 0])
    total_losses = len(trades_df[trades_df['pnl'] < 0])
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    overall_avg_hold = trades_df['hold_days'].mean()

    print(f"{'TOTAL':>6} {total_return:>9.2f}% {portfolio_df['drawdown'].min():>9.2f}% {total_trades:>8} "
          f"{total_wins:>6} {total_losses:>8} {overall_wr:>9.2f}% {'---':>8} "
          f"{trades_df[trades_df['pnl']>0]['pnl_pct'].mean():>9.2f}% {trades_df[trades_df['pnl']<0]['pnl_pct'].mean():>9.2f}% {overall_avg_hold:>8.1f}")

    # Exit reason breakdown by year
    print("\n" + "=" * 100)
    print("EXIT REASONS BY YEAR")
    print("=" * 100)
    print(f"\n{'Year':>6} {'Trailing':>12} {'MaxHold':>12} {'Breakdown':>12} {'End':>12}")
    print("-" * 60)

    for year in years:
        yt = trades_df[trades_df['exit_year'] == year]
        if len(yt) == 0:
            continue
        reasons = yt['reason'].value_counts()
        trailing = reasons.get('trailing', 0)
        max_hold = reasons.get('max_hold', 0)
        breakdown = reasons.get('breakdown', 0)
        end = reasons.get('end', 0)
        print(f"{year:>6} {trailing:>12} {max_hold:>12} {breakdown:>12} {end:>12}")

    # Summary stats
    annual_df = pd.DataFrame(annual_data)
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)
    print(f"\n  Best Year:      {int(annual_df.loc[annual_df['return'].idxmax(), 'year'])} ({annual_df['return'].max():.2f}%)")
    print(f"  Worst Year:     {int(annual_df.loc[annual_df['return'].idxmin(), 'year'])} ({annual_df['return'].min():.2f}%)")
    print(f"  Avg Return:     {annual_df['return'].mean():.2f}%")
    print(f"  Return StdDev:  {annual_df['return'].std():.2f}%")
    print(f"  Positive Years: {len(annual_df[annual_df['return'] > 0])}/{len(annual_df)}")
    print(f"  Avg Win Rate:   {annual_df['win_rate'].mean():.2f}%")
    print(f"  Worst Drawdown: {annual_df['max_dd'].min():.2f}%")
    print(f"  Avg Hold Days:  {overall_avg_hold:.1f}")


if __name__ == '__main__':
    main()
