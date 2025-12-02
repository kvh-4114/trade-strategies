#!/usr/bin/env python3
"""
Breakout Momentum Strategy

Concept: Enter when price breaks above N-day high with volume confirmation.
Exit on trailing stop or break below N-day low.

Entry Criteria:
1. Price closes above N-day high (breakout)
2. Volume > 1.5x average volume (confirmation)
3. Price trending up (above short-term MA)

Exit Criteria:
1. Price closes below M-day low (breakdown)
2. OR trailing stop triggered
3. OR max holding period reached

This captures explosive moves that Dual Momentum might miss due to monthly rebalancing.
"""

import os
from datetime import datetime
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

# Strategy Parameters
BREAKOUT_PERIOD = 20        # N-day high for entry
BREAKDOWN_PERIOD = 10       # M-day low for exit
VOLUME_MULT = 1.5           # Volume must be 1.5x average
TREND_MA = 50               # Must be above this MA
TRAILING_STOP_PCT = 0.15    # 15% trailing stop
MAX_HOLD_DAYS = 60          # Max holding period

INITIAL_CAPITAL = 1000000
POSITION_SIZE = 10000
MAX_POSITIONS = 50


class BreakoutMomentumStrategy:
    """Breakout Momentum with volume confirmation."""

    def __init__(self, breakout_period=20, breakdown_period=10, volume_mult=1.5,
                 trend_ma=50, trailing_stop=0.15, max_hold=60):
        self.breakout_period = breakout_period
        self.breakdown_period = breakdown_period
        self.volume_mult = volume_mult
        self.trend_ma = trend_ma
        self.trailing_stop = trailing_stop
        self.max_hold = max_hold
        self.trades = []

    def check_entry_signal(self, df: pd.DataFrame, idx: int) -> bool:
        """Check if breakout entry conditions are met."""
        if idx < max(self.breakout_period, self.trend_ma, 20):
            return False

        current_close = df['close'].iloc[idx]
        current_volume = df['volume'].iloc[idx]

        # N-day high (excluding current bar)
        n_day_high = df['high'].iloc[idx - self.breakout_period:idx].max()

        # Average volume
        avg_volume = df['volume'].iloc[idx - 20:idx].mean()

        # Trend MA
        ma_value = df['close'].iloc[idx - self.trend_ma:idx].mean()

        # Entry conditions
        breakout = current_close > n_day_high
        volume_confirm = current_volume > avg_volume * self.volume_mult
        uptrend = current_close > ma_value

        return breakout and volume_confirm and uptrend

    def check_exit_signal(self, df: pd.DataFrame, idx: int, entry_idx: int,
                          entry_price: float, highest_price: float) -> tuple:
        """Check if exit conditions are met. Returns (should_exit, reason)."""
        if idx < self.breakdown_period:
            return False, None

        current_close = df['close'].iloc[idx]

        # M-day low
        m_day_low = df['low'].iloc[idx - self.breakdown_period:idx].min()

        # Breakdown exit
        if current_close < m_day_low:
            return True, 'breakdown'

        # Trailing stop
        trailing_stop_price = highest_price * (1 - self.trailing_stop)
        if current_close < trailing_stop_price:
            return True, 'trailing_stop'

        # Max hold period
        hold_days = idx - entry_idx
        if hold_days >= self.max_hold:
            return True, 'max_hold'

        return False, None

    def run_backtest(self, all_data: dict) -> dict:
        """Run backtest across all symbols."""
        self.trades = []

        start_date = pd.to_datetime('2017-04-01')
        end_date = pd.to_datetime('2025-11-01')

        # Combine all data into a single timeline
        all_dates = set()
        for df in all_data.values():
            all_dates.update(df.index.tolist())
        all_dates = sorted([d for d in all_dates if start_date <= d <= end_date])

        cash = INITIAL_CAPITAL
        positions = {}  # {symbol: {entry_idx, entry_price, entry_date, shares, highest}}
        portfolio_history = []

        for date in all_dates:
            # Update highest prices for trailing stops
            for symbol in list(positions.keys()):
                if symbol in all_data:
                    df = all_data[symbol]
                    if date in df.index:
                        current_price = df.loc[date, 'close']
                        if current_price > positions[symbol]['highest']:
                            positions[symbol]['highest'] = current_price

            # Check exits first
            for symbol in list(positions.keys()):
                if symbol not in all_data:
                    continue
                df = all_data[symbol]
                if date not in df.index:
                    continue

                idx = df.index.get_loc(date)
                pos = positions[symbol]

                should_exit, reason = self.check_exit_signal(
                    df, idx, pos['entry_idx'], pos['entry_price'], pos['highest']
                )

                if should_exit:
                    exit_price = df['close'].iloc[idx]
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100

                    cash += pos['shares'] * exit_price

                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': date,
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'shares': pos['shares'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': reason,
                        'hold_days': idx - pos['entry_idx'],
                        'exit_year': date.year
                    })
                    del positions[symbol]

            # Check entries
            if len(positions) < MAX_POSITIONS:
                for symbol, df in all_data.items():
                    if symbol in positions:
                        continue
                    if date not in df.index:
                        continue

                    idx = df.index.get_loc(date)
                    if self.check_entry_signal(df, idx):
                        price = df['close'].iloc[idx]
                        if cash >= POSITION_SIZE and price > 0:
                            shares = int(POSITION_SIZE / price)
                            if shares > 0:
                                cash -= shares * price
                                positions[symbol] = {
                                    'entry_idx': idx,
                                    'entry_price': price,
                                    'entry_date': date,
                                    'shares': shares,
                                    'highest': price
                                }

                                if len(positions) >= MAX_POSITIONS:
                                    break

            # Track portfolio value
            pos_value = 0
            for symbol, pos in positions.items():
                if symbol in all_data:
                    df = all_data[symbol]
                    if date in df.index:
                        pos_value += pos['shares'] * df.loc[date, 'close']
                    else:
                        pos_value += pos['shares'] * pos['entry_price']

            portfolio_history.append({
                'date': date,
                'value': cash + pos_value,
                'cash': cash,
                'positions': len(positions)
            })

        # Close remaining positions
        for symbol, pos in positions.items():
            if symbol in all_data:
                df = all_data[symbol]
                if len(df) > 0:
                    exit_price = df['close'].iloc[-1]
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': df.index[-1],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'shares': pos['shares'],
                        'pnl': pnl,
                        'pnl_pct': ((exit_price / pos['entry_price']) - 1) * 100,
                        'exit_reason': 'end',
                        'hold_days': len(df) - pos['entry_idx'],
                        'exit_year': df.index[-1].year
                    })

        return self._calc_metrics(pd.DataFrame(self.trades), pd.DataFrame(portfolio_history))

    def _calc_metrics(self, trades_df, portfolio_df):
        if len(trades_df) == 0 or len(portfolio_df) == 0:
            return {'error': 'No trades', 'total_trades': 0}

        final = portfolio_df['value'].iloc[-1]
        total_return = ((final / INITIAL_CAPITAL) - 1) * 100

        portfolio_df['peak'] = portfolio_df['value'].cummax()
        portfolio_df['dd'] = (portfolio_df['value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_dd = portfolio_df['dd'].min()

        days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
        years = days / 365.25
        ann_return = ((final / INITIAL_CAPITAL) ** (1/years) - 1) * 100 if years > 0 else 0

        # Monthly returns for Sharpe
        portfolio_df['month'] = portfolio_df['date'].dt.to_period('M')
        monthly = portfolio_df.groupby('month')['value'].last().pct_change().dropna()
        sharpe = (monthly.mean() - 0.05/12) / monthly.std() * np.sqrt(12) if len(monthly) > 1 and monthly.std() > 0 else 0

        n_trades = len(trades_df)
        winning = len(trades_df[trades_df['pnl'] > 0])
        win_rate = (winning / n_trades * 100) if n_trades > 0 else 0

        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 999

        avg_hold = trades_df['hold_days'].mean() if 'hold_days' in trades_df.columns else 0

        # Exit reason breakdown
        exit_reasons = trades_df['exit_reason'].value_counts().to_dict() if 'exit_reason' in trades_df.columns else {}

        # Annual returns
        portfolio_df['year'] = portfolio_df['date'].dt.year
        annual = []
        for year in sorted(portfolio_df['year'].unique()):
            yd = portfolio_df[portfolio_df['year'] == year]
            if len(yd) >= 2:
                yr = ((yd['value'].iloc[-1] / yd['value'].iloc[0]) - 1) * 100
                yr_dd = yd['dd'].min()
                yr_trades = len(trades_df[trades_df['exit_year'] == year])
                annual.append({'year': year, 'return': yr, 'max_dd': yr_dd, 'trades': yr_trades})

        return {
            'total_return': total_return,
            'ann_return': ann_return,
            'max_dd': max_dd,
            'sharpe': sharpe,
            'total_trades': n_trades,
            'win_rate': win_rate,
            'profit_factor': min(pf, 999),
            'final_value': final,
            'avg_hold_days': avg_hold,
            'exit_reasons': exit_reasons,
            'annual': annual,
            'trades_df': trades_df,
            'portfolio_df': portfolio_df
        }


def load_data(candle_type='linreg', aggregation=5):
    """Load candle data from database."""
    conn = psycopg2.connect(**DB_CONFIG)

    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM candles WHERE candle_type = %s ORDER BY symbol", (candle_type,))
        symbols = [r[0] for r in cur.fetchall()]

    print(f"Loading {candle_type}_{aggregation}d data for {len(symbols)} symbols...")
    all_data = {}

    for i, symbol in enumerate(symbols):
        query = """
            SELECT date, open, high, low, close, volume FROM candles
            WHERE symbol = %s AND candle_type = %s AND aggregation_days = %s
            ORDER BY date
        """
        with conn.cursor() as cur:
            cur.execute(query, (symbol, candle_type, aggregation))
            rows = cur.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                all_data[symbol] = df

        if (i + 1) % 50 == 0:
            print(f"  Loaded {i+1}/{len(symbols)}...")

    conn.close()
    print(f"Loaded {len(all_data)} symbols")
    return all_data


def main():
    print("=" * 80)
    print("BREAKOUT MOMENTUM STRATEGY")
    print("=" * 80)
    print(f"Breakout Period:  {BREAKOUT_PERIOD} days")
    print(f"Breakdown Period: {BREAKDOWN_PERIOD} days")
    print(f"Volume Confirm:   {VOLUME_MULT}x average")
    print(f"Trend Filter:     {TREND_MA}-day MA")
    print(f"Trailing Stop:    {TRAILING_STOP_PCT*100:.0f}%")
    print(f"Max Hold:         {MAX_HOLD_DAYS} days")
    print("-" * 80)

    all_data = load_data('linreg', 5)

    strategy = BreakoutMomentumStrategy(
        breakout_period=BREAKOUT_PERIOD,
        breakdown_period=BREAKDOWN_PERIOD,
        volume_mult=VOLUME_MULT,
        trend_ma=TREND_MA,
        trailing_stop=TRAILING_STOP_PCT,
        max_hold=MAX_HOLD_DAYS
    )

    print("\nRunning backtest...")
    results = strategy.run_backtest(all_data)

    print("\n" + "=" * 80)
    print("BREAKOUT MOMENTUM RESULTS")
    print("=" * 80)

    print(f"\nTotal Return:      {results['total_return']:.2f}%")
    print(f"Annualized Return: {results['ann_return']:.2f}%")
    print(f"Max Drawdown:      {results['max_dd']:.2f}%")
    print(f"Sharpe Ratio:      {results['sharpe']:.3f}")
    print(f"Total Trades:      {results['total_trades']}")
    print(f"Win Rate:          {results['win_rate']:.2f}%")
    print(f"Profit Factor:     {results['profit_factor']:.2f}")
    print(f"Avg Hold Days:     {results['avg_hold_days']:.1f}")
    print(f"Final Value:       ${results['final_value']:,.2f}")

    print(f"\nExit Reasons:")
    for reason, count in results['exit_reasons'].items():
        pct = count / results['total_trades'] * 100
        print(f"  {reason:<15}: {count:>5} ({pct:.1f}%)")

    print(f"\n{'Year':<6} {'Return':>10} {'MaxDD':>10} {'Trades':>8}")
    print("-" * 38)
    for ar in results['annual']:
        print(f"{ar['year']:<6} {ar['return']:>9.2f}% {ar['max_dd']:>9.2f}% {ar['trades']:>8}")

    # Save results
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results['portfolio_df'].to_csv(f'results/breakout_momentum_portfolio_{timestamp}.csv', index=False)
    results['trades_df'].to_csv(f'results/breakout_momentum_trades_{timestamp}.csv', index=False)

    print(f"\nResults saved to results/breakout_momentum_*_{timestamp}.csv")

    return results


if __name__ == '__main__':
    results = main()
