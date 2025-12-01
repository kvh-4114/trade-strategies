#!/usr/bin/env python3
"""
Dual Momentum Parameter Optimization

Uses LinReg_5d bars (winner from bar experiment) and optimizes:
- Lookback period: 6, 9, 12, 18 months
- Entry threshold: top 10%, 15%, 20%, 25%
- Exit threshold: top 25%, 30%, 35%, 40%

Total: 4 × 4 × 4 = 64 combinations
"""

import os
from datetime import datetime
from decimal import Decimal
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

# Use same 50 test symbols
TEST_SYMBOLS = [
    'AAOI', 'AAON', 'AAPL', 'ADMA', 'AGYS', 'ALGN', 'ALNT', 'ALTS', 'AMAT', 'AMBA',
    'AMD', 'AMKR', 'AMSC', 'AMTX', 'AMZN', 'ANGI', 'AOSL', 'APEI', 'ARCB', 'ARDX',
    'ARLP', 'ARQ', 'ARWR', 'ASML', 'ASND', 'ASTH', 'ATEC', 'ATRC', 'ATRO', 'ATXS',
    'AUPH', 'AVDL', 'AVGO', 'AVXL', 'AXGN', 'AXON', 'BBSI', 'BJRI', 'BKR', 'BLBD',
    'BOOM', 'BPOP', 'BRKR', 'CAMT', 'CAR', 'CASH', 'CDNA', 'CDZI', 'CECO', 'CENX'
]

# Parameter grid
LOOKBACK_MONTHS = [6, 9, 12, 18]  # Trading days: ~126, 189, 252, 378
ENTRY_THRESHOLDS = [0.10, 0.15, 0.20, 0.25]  # Top N%
EXIT_THRESHOLDS = [0.25, 0.30, 0.35, 0.40]   # Exit when below top N%

# Fixed params
POSITION_SIZE = 10000
INITIAL_CAPITAL = 500000
CANDLE_TYPE = 'linreg'
AGGREGATION = 5


class DualMomentumOptimizer:
    """Optimized backtest runner for parameter search."""

    def __init__(self, lookback_days, entry_pct, exit_pct):
        self.lookback_days = lookback_days
        self.entry_pct = entry_pct
        self.exit_pct = exit_pct
        self.trades = []

    def calculate_momentum(self, prices: pd.Series) -> float:
        actual_lookback = min(self.lookback_days, len(prices) - 1)
        if actual_lookback < 30:
            return np.nan
        current = prices.iloc[-1]
        past = prices.iloc[-actual_lookback]
        if past == 0:
            return np.nan
        return ((current / past) - 1) * 100

    def run_backtest(self, all_data: dict) -> dict:
        self.trades = []
        start_dt = pd.to_datetime('2017-04-01')
        end_dt = pd.to_datetime('2025-11-01')

        rebalance_dates = pd.date_range(start=start_dt, end=end_dt, freq='MS')

        cash = INITIAL_CAPITAL
        positions = {}
        portfolio_history = []

        for rebalance_date in rebalance_dates:
            momentum_scores = {}

            for symbol, df in all_data.items():
                df_subset = df[df.index <= rebalance_date]
                if len(df_subset) < self.lookback_days // 5:  # Adjusted for 5-day bars
                    continue
                momentum = self.calculate_momentum(df_subset['close'])
                if not np.isnan(momentum):
                    momentum_scores[symbol] = momentum

            if not momentum_scores:
                continue

            ranked = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
            n = len(ranked)

            entry_cutoff = int(n * self.entry_pct)
            exit_cutoff = int(n * self.exit_pct)

            top_for_entry = set([s for s, m in ranked[:entry_cutoff] if m > 0])
            to_hold = set([s for s, m in ranked[:exit_cutoff] if m > 0])

            # Get prices
            prices = {}
            for symbol, df in all_data.items():
                prior = df.index[df.index <= rebalance_date]
                if len(prior) > 0:
                    prices[symbol] = df.loc[prior[-1], 'close']

            # Exit
            for symbol in list(positions.keys()):
                if symbol not in to_hold and symbol in prices:
                    pos = positions[symbol]
                    exit_price = prices[symbol]
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100
                    cash += pos['shares'] * exit_price
                    self.trades.append({
                        'pnl': pnl, 'pnl_pct': pnl_pct
                    })
                    del positions[symbol]

            # Enter
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

            # Track portfolio
            pos_value = sum(
                pos['shares'] * prices.get(sym, pos['entry_price'])
                for sym, pos in positions.items()
            )
            portfolio_history.append({
                'date': rebalance_date,
                'value': cash + pos_value
            })

        # Close remaining
        for symbol, pos in positions.items():
            df = all_data.get(symbol)
            if df is not None and len(df) > 0:
                exit_price = df['close'].iloc[-1]
                pnl = (exit_price - pos['entry_price']) * pos['shares']
                pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100
                self.trades.append({'pnl': pnl, 'pnl_pct': pnl_pct})

        return self._calc_metrics(pd.DataFrame(self.trades), pd.DataFrame(portfolio_history))

    def _calc_metrics(self, trades_df, portfolio_df):
        if len(trades_df) == 0 or len(portfolio_df) == 0:
            return {'total_return': 0, 'sharpe': 0, 'max_dd': 0, 'trades': 0, 'win_rate': 0, 'pf': 0}

        final = portfolio_df['value'].iloc[-1]
        total_return = ((final / INITIAL_CAPITAL) - 1) * 100

        portfolio_df['peak'] = portfolio_df['value'].cummax()
        portfolio_df['dd'] = (portfolio_df['value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_dd = portfolio_df['dd'].min()

        days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
        years = days / 365.25
        ann_return = ((final / INITIAL_CAPITAL) ** (1/years) - 1) * 100 if years > 0 else 0

        monthly_ret = portfolio_df['value'].pct_change().dropna()
        sharpe = (monthly_ret.mean() - 0.05/12) / monthly_ret.std() * np.sqrt(12) if len(monthly_ret) > 1 and monthly_ret.std() > 0 else 0

        n_trades = len(trades_df)
        win_rate = len(trades_df[trades_df['pnl'] > 0]) / n_trades * 100 if n_trades > 0 else 0

        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 999

        return {
            'total_return': total_return,
            'ann_return': ann_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'trades': n_trades,
            'win_rate': win_rate,
            'pf': min(pf, 999)
        }


def load_linreg_5d_data(symbols):
    """Load LinReg 5-day candles."""
    conn = psycopg2.connect(**DB_CONFIG)
    all_data = {}

    for symbol in symbols:
        query = """
            SELECT date, open, high, low, close, volume
            FROM candles
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
    return all_data


def run_optimization():
    """Run full parameter grid search."""

    print("=" * 80)
    print("DUAL MOMENTUM PARAMETER OPTIMIZATION")
    print("=" * 80)
    print(f"Bar Type: {CANDLE_TYPE}_{AGGREGATION}d (winner from bar experiment)")
    print(f"Symbols: {len(TEST_SYMBOLS)}")
    print(f"Lookback periods: {LOOKBACK_MONTHS} months")
    print(f"Entry thresholds: {[f'{x*100:.0f}%' for x in ENTRY_THRESHOLDS]}")
    print(f"Exit thresholds: {[f'{x*100:.0f}%' for x in EXIT_THRESHOLDS]}")
    print(f"Total combinations: {len(LOOKBACK_MONTHS) * len(ENTRY_THRESHOLDS) * len(EXIT_THRESHOLDS)}")
    print("-" * 80)

    # Load data once
    print("\nLoading LinReg_5d data...")
    all_data = load_linreg_5d_data(TEST_SYMBOLS)
    print(f"Loaded {len(all_data)} symbols")

    results = []
    total = len(LOOKBACK_MONTHS) * len(ENTRY_THRESHOLDS) * len(EXIT_THRESHOLDS)
    count = 0

    for lookback_m in LOOKBACK_MONTHS:
        lookback_days = lookback_m * 21  # ~21 trading days per month

        for entry_pct in ENTRY_THRESHOLDS:
            for exit_pct in EXIT_THRESHOLDS:
                count += 1
                config_name = f"LB{lookback_m}m_E{int(entry_pct*100)}_X{int(exit_pct*100)}"

                strategy = DualMomentumOptimizer(
                    lookback_days=lookback_days,
                    entry_pct=entry_pct,
                    exit_pct=exit_pct
                )

                metrics = strategy.run_backtest(all_data)
                metrics['lookback_months'] = lookback_m
                metrics['entry_pct'] = entry_pct * 100
                metrics['exit_pct'] = exit_pct * 100
                metrics['config'] = config_name

                results.append(metrics)

                if count % 10 == 0 or count == total:
                    print(f"[{count}/{total}] {config_name}: "
                          f"Return={metrics['total_return']:.1f}% "
                          f"Sharpe={metrics['sharpe']:.2f} "
                          f"MaxDD={metrics['max_dd']:.1f}%")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Sort by Sharpe (primary), then by return (secondary)
    results_df = results_df.sort_values(['sharpe', 'total_return'], ascending=[False, False])

    # Print top 10
    print("\n" + "=" * 80)
    print("TOP 10 PARAMETER COMBINATIONS (by Sharpe Ratio)")
    print("=" * 80)
    print(f"\n{'Config':<20} {'Return':>10} {'Annual':>10} {'MaxDD':>10} {'Sharpe':>8} {'WinRate':>8} {'Trades':>8}")
    print("-" * 84)

    for _, row in results_df.head(10).iterrows():
        print(f"{row['config']:<20} "
              f"{row['total_return']:>9.1f}% "
              f"{row['ann_return']:>9.1f}% "
              f"{row['max_dd']:>9.1f}% "
              f"{row['sharpe']:>8.3f} "
              f"{row['win_rate']:>7.1f}% "
              f"{row['trades']:>8}")

    # Best configuration details
    best = results_df.iloc[0]
    print("\n" + "=" * 80)
    print("OPTIMAL CONFIGURATION")
    print("=" * 80)
    print(f"\nParameters:")
    print(f"  Lookback Period:   {int(best['lookback_months'])} months")
    print(f"  Entry Threshold:   Top {int(best['entry_pct'])}%")
    print(f"  Exit Threshold:    Top {int(best['exit_pct'])}%")
    print(f"\nPerformance:")
    print(f"  Total Return:      {best['total_return']:.2f}%")
    print(f"  Annualized Return: {best['ann_return']:.2f}%")
    print(f"  Max Drawdown:      {best['max_dd']:.2f}%")
    print(f"  Sharpe Ratio:      {best['sharpe']:.3f}")
    print(f"  Win Rate:          {best['win_rate']:.2f}%")
    print(f"  Profit Factor:     {best['pf']:.2f}")
    print(f"  Total Trades:      {int(best['trades'])}")

    # Analysis by parameter
    print("\n" + "=" * 80)
    print("PARAMETER SENSITIVITY ANALYSIS")
    print("=" * 80)

    # By lookback
    print("\nBy Lookback Period:")
    for lb in LOOKBACK_MONTHS:
        subset = results_df[results_df['lookback_months'] == lb]
        print(f"  {lb}m: Avg Sharpe={subset['sharpe'].mean():.3f}, "
              f"Avg Return={subset['total_return'].mean():.1f}%, "
              f"Best Sharpe={subset['sharpe'].max():.3f}")

    # By entry threshold
    print("\nBy Entry Threshold:")
    for ep in ENTRY_THRESHOLDS:
        subset = results_df[results_df['entry_pct'] == ep * 100]
        print(f"  Top {int(ep*100)}%: Avg Sharpe={subset['sharpe'].mean():.3f}, "
              f"Avg Return={subset['total_return'].mean():.1f}%")

    # By exit threshold
    print("\nBy Exit Threshold:")
    for xp in EXIT_THRESHOLDS:
        subset = results_df[results_df['exit_pct'] == xp * 100]
        print(f"  Top {int(xp*100)}%: Avg Sharpe={subset['sharpe'].mean():.3f}, "
              f"Avg Return={subset['total_return'].mean():.1f}%")

    # Save results
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = f'results/dual_momentum_optimization_{timestamp}.csv'
    results_df.to_csv(path, index=False)
    print(f"\nResults saved to: {path}")

    # Comparison with baseline
    print("\n" + "=" * 80)
    print("COMPARISON: OPTIMIZED vs BASELINE")
    print("=" * 80)
    baseline = results_df[(results_df['lookback_months'] == 12) &
                          (results_df['entry_pct'] == 20) &
                          (results_df['exit_pct'] == 30)]

    if len(baseline) > 0:
        bl = baseline.iloc[0]
        best_lb = f"{int(best['lookback_months'])} months"
        best_entry = f"Top {int(best['entry_pct'])}%"
        best_exit = f"Top {int(best['exit_pct'])}%"
        bl_ret = f"{bl['total_return']:.1f}%"
        best_ret = f"{best['total_return']:.1f}%"
        imp_ret = f"+{best['total_return']-bl['total_return']:.1f}%"
        bl_sharpe = f"{bl['sharpe']:.3f}"
        best_sharpe = f"{best['sharpe']:.3f}"
        imp_sharpe = f"+{best['sharpe']-bl['sharpe']:.3f}"
        bl_dd = f"{bl['max_dd']:.1f}%"
        best_dd = f"{best['max_dd']:.1f}%"
        imp_dd = f"{best['max_dd']-bl['max_dd']:.1f}%"

        print(f"\n{'Metric':<20} {'Baseline':>15} {'Optimized':>15} {'Improvement':>15}")
        print("-" * 65)
        print(f"{'Lookback':<20} {'12 months':>15} {best_lb:>15}")
        print(f"{'Entry Threshold':<20} {'Top 20%':>15} {best_entry:>15}")
        print(f"{'Exit Threshold':<20} {'Top 30%':>15} {best_exit:>15}")
        print(f"{'Total Return':<20} {bl_ret:>15} {best_ret:>15} {imp_ret:>15}")
        print(f"{'Sharpe Ratio':<20} {bl_sharpe:>15} {best_sharpe:>15} {imp_sharpe:>15}")
        print(f"{'Max Drawdown':<20} {bl_dd:>15} {best_dd:>15} {imp_dd:>15}")

    return results_df, best


if __name__ == '__main__':
    results_df, best_config = run_optimization()
