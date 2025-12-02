#!/usr/bin/env python3
"""
Dual Momentum Detailed Annual Analysis

Generates comprehensive yearly metrics including:
- Returns, drawdown, win rate, profit factor per year
- Monthly breakdown
- Trade statistics by year
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

CONFIGS = {
    'conservative': {'lookback_months': 6, 'entry_pct': 0.20, 'exit_pct': 0.35, 'name': 'LB6m_E20_X35'},
    'aggressive': {'lookback_months': 18, 'entry_pct': 0.25, 'exit_pct': 0.40, 'name': 'LB18m_E25_X40'}
}

POSITION_SIZE = 10000
INITIAL_CAPITAL = 1000000
CANDLE_TYPE = 'linreg'
AGGREGATION = 5


class DualMomentumAnalysis:
    def __init__(self, lookback_months, entry_pct, exit_pct):
        self.lookback_days = lookback_months * 21
        self.entry_pct = entry_pct
        self.exit_pct = exit_pct
        self.trades = []
        self.monthly_snapshots = []

    def calculate_momentum(self, prices):
        actual_lookback = min(self.lookback_days, len(prices) - 1)
        if actual_lookback < 30:
            return np.nan
        return ((prices.iloc[-1] / prices.iloc[-actual_lookback]) - 1) * 100

    def run_backtest(self, all_data):
        self.trades = []
        self.monthly_snapshots = []

        start_dt = pd.to_datetime('2017-04-01')
        end_dt = pd.to_datetime('2025-11-01')
        rebalance_dates = pd.date_range(start=start_dt, end=end_dt, freq='MS')

        cash = INITIAL_CAPITAL
        positions = {}
        peak_value = INITIAL_CAPITAL

        for rebalance_date in rebalance_dates:
            momentum_scores = {}
            for symbol, df in all_data.items():
                df_subset = df[df.index <= rebalance_date]
                if len(df_subset) < self.lookback_days // 5:
                    continue
                m = self.calculate_momentum(df_subset['close'])
                if not np.isnan(m):
                    momentum_scores[symbol] = m

            if not momentum_scores:
                continue

            ranked = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
            n = len(ranked)
            entry_cutoff = int(n * self.entry_pct)
            exit_cutoff = int(n * self.exit_pct)

            top_for_entry = set([s for s, m in ranked[:entry_cutoff] if m > 0])
            to_hold = set([s for s, m in ranked[:exit_cutoff] if m > 0])

            prices = {}
            for symbol, df in all_data.items():
                prior = df.index[df.index <= rebalance_date]
                if len(prior) > 0:
                    prices[symbol] = df.loc[prior[-1], 'close']

            # Process exits
            for symbol in list(positions.keys()):
                if symbol not in to_hold and symbol in prices:
                    pos = positions[symbol]
                    exit_price = prices[symbol]
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100
                    cash += pos['shares'] * exit_price

                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': rebalance_date,
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'shares': pos['shares'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_year': rebalance_date.year
                    })
                    del positions[symbol]

            # Process entries
            for symbol in top_for_entry:
                if symbol not in positions and symbol in prices:
                    price = prices[symbol]
                    if cash >= POSITION_SIZE and price > 0:
                        shares = int(POSITION_SIZE / price)
                        if shares > 0:
                            cash -= shares * price
                            positions[symbol] = {
                                'shares': shares,
                                'entry_price': price,
                                'entry_date': rebalance_date
                            }

            # Calculate portfolio value
            pos_value = sum(pos['shares'] * prices.get(sym, pos['entry_price'])
                           for sym, pos in positions.items())
            total_value = cash + pos_value
            peak_value = max(peak_value, total_value)
            drawdown = ((total_value - peak_value) / peak_value) * 100

            self.monthly_snapshots.append({
                'date': rebalance_date,
                'year': rebalance_date.year,
                'month': rebalance_date.month,
                'value': total_value,
                'cash': cash,
                'invested': pos_value,
                'positions': len(positions),
                'peak': peak_value,
                'drawdown': drawdown
            })

        # Close remaining
        for symbol, pos in list(positions.items()):
            df = all_data.get(symbol)
            if df is not None and len(df) > 0:
                exit_price = df['close'].iloc[-1]
                pnl = (exit_price - pos['entry_price']) * pos['shares']
                pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100
                self.trades.append({
                    'symbol': symbol,
                    'entry_date': pos['entry_date'],
                    'exit_date': df.index[-1],
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'shares': pos['shares'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_year': df.index[-1].year
                })

        return pd.DataFrame(self.trades), pd.DataFrame(self.monthly_snapshots)


def calculate_annual_metrics(trades_df, portfolio_df):
    """Calculate detailed metrics for each year."""

    years = sorted(portfolio_df['year'].unique())
    annual_data = []

    for year in years:
        year_portfolio = portfolio_df[portfolio_df['year'] == year]
        year_trades = trades_df[trades_df['exit_year'] == year]

        if len(year_portfolio) < 2:
            continue

        # Portfolio metrics
        start_val = year_portfolio['value'].iloc[0]
        end_val = year_portfolio['value'].iloc[-1]
        year_return = ((end_val / start_val) - 1) * 100

        # Max drawdown for the year
        year_max_dd = year_portfolio['drawdown'].min()

        # Trade metrics
        n_trades = len(year_trades)
        if n_trades > 0:
            winning = len(year_trades[year_trades['pnl'] > 0])
            losing = len(year_trades[year_trades['pnl'] < 0])
            win_rate = (winning / n_trades) * 100

            gross_profit = year_trades[year_trades['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(year_trades[year_trades['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999

            avg_win = year_trades[year_trades['pnl'] > 0]['pnl_pct'].mean() if winning > 0 else 0
            avg_loss = year_trades[year_trades['pnl'] < 0]['pnl_pct'].mean() if losing > 0 else 0
            total_pnl = year_trades['pnl'].sum()
        else:
            winning = losing = 0
            win_rate = profit_factor = avg_win = avg_loss = total_pnl = 0

        # Average positions
        avg_positions = year_portfolio['positions'].mean()

        annual_data.append({
            'year': year,
            'return': year_return,
            'max_dd': year_max_dd,
            'trades': n_trades,
            'wins': winning,
            'losses': losing,
            'win_rate': win_rate,
            'profit_factor': min(profit_factor, 999),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'avg_positions': avg_positions,
            'start_value': start_val,
            'end_value': end_val
        })

    return pd.DataFrame(annual_data)


def load_data():
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM candles WHERE candle_type = %s", (CANDLE_TYPE,))
        symbols = [r[0] for r in cur.fetchall()]

    all_data = {}
    for symbol in symbols:
        query = """
            SELECT date, close FROM candles
            WHERE symbol = %s AND candle_type = %s AND aggregation_days = %s
            ORDER BY date
        """
        with conn.cursor() as cur:
            cur.execute(query, (symbol, CANDLE_TYPE, AGGREGATION))
            rows = cur.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=['date', 'close'])
                df['close'] = df['close'].astype(float)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                all_data[symbol] = df

    conn.close()
    return all_data


def main():
    print("=" * 100)
    print("DUAL MOMENTUM - DETAILED ANNUAL ANALYSIS")
    print("=" * 100)

    print("\nLoading data...")
    all_data = load_data()
    print(f"Loaded {len(all_data)} symbols")

    for config_type, params in CONFIGS.items():
        print(f"\n{'='*100}")
        print(f"{config_type.upper()} CONFIG: {params['name']}")
        print("=" * 100)

        strategy = DualMomentumAnalysis(
            lookback_months=params['lookback_months'],
            entry_pct=params['entry_pct'],
            exit_pct=params['exit_pct']
        )

        trades_df, portfolio_df = strategy.run_backtest(all_data)
        annual_df = calculate_annual_metrics(trades_df, portfolio_df)

        # Print detailed annual table
        print(f"\n{'Year':>6} {'Return':>10} {'MaxDD':>10} {'Trades':>8} {'Wins':>6} {'Losses':>8} {'WinRate':>10} {'PF':>8} {'AvgWin':>10} {'AvgLoss':>10} {'TotalPnL':>14}")
        print("-" * 112)

        for _, row in annual_df.iterrows():
            print(f"{int(row['year']):>6} "
                  f"{row['return']:>9.2f}% "
                  f"{row['max_dd']:>9.2f}% "
                  f"{int(row['trades']):>8} "
                  f"{int(row['wins']):>6} "
                  f"{int(row['losses']):>8} "
                  f"{row['win_rate']:>9.2f}% "
                  f"{row['profit_factor']:>8.2f} "
                  f"{row['avg_win']:>9.2f}% "
                  f"{row['avg_loss']:>9.2f}% "
                  f"${row['total_pnl']:>12,.0f}")

        # Totals
        print("-" * 112)
        total_return = ((annual_df['end_value'].iloc[-1] / INITIAL_CAPITAL) - 1) * 100
        total_trades = annual_df['trades'].sum()
        total_wins = annual_df['wins'].sum()
        total_losses = annual_df['losses'].sum()
        overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = annual_df['total_pnl'].sum()

        print(f"{'TOTAL':>6} "
              f"{total_return:>9.2f}% "
              f"{annual_df['max_dd'].min():>9.2f}% "
              f"{int(total_trades):>8} "
              f"{int(total_wins):>6} "
              f"{int(total_losses):>8} "
              f"{overall_wr:>9.2f}% "
              f"{'---':>8} "
              f"{annual_df['avg_win'].mean():>9.2f}% "
              f"{annual_df['avg_loss'].mean():>9.2f}% "
              f"${total_pnl:>12,.0f}")

        # Summary stats
        print(f"\nSUMMARY STATISTICS:")
        print(f"  Best Year:     {int(annual_df.loc[annual_df['return'].idxmax(), 'year'])} ({annual_df['return'].max():.2f}%)")
        print(f"  Worst Year:    {int(annual_df.loc[annual_df['return'].idxmin(), 'year'])} ({annual_df['return'].min():.2f}%)")
        print(f"  Avg Return:    {annual_df['return'].mean():.2f}%")
        print(f"  Return StdDev: {annual_df['return'].std():.2f}%")
        print(f"  Positive Years: {len(annual_df[annual_df['return'] > 0])}/{len(annual_df)}")
        print(f"  Avg Positions: {annual_df['avg_positions'].mean():.1f}")
        print(f"  Worst Drawdown: {annual_df['max_dd'].min():.2f}% ({int(annual_df.loc[annual_df['max_dd'].idxmin(), 'year'])})")


if __name__ == '__main__':
    main()
