#!/usr/bin/env python3
"""
Breakout Momentum - Bar Type & Parameter Optimization

Tests all combinations of:
- Bar types: regular, heiken_ashi, linreg
- Aggregations: 1, 2, 3, 4, 5 days
- Breakout periods: 10, 15, 20, 30 days
- Breakdown periods: 5, 10, 15 days
- Trailing stops: 10%, 15%, 20%, 25%
"""

import os
from datetime import datetime
import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
from itertools import product
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

# Test symbols (50 for faster iteration)
TEST_SYMBOLS = [
    'AAOI', 'AAON', 'AAPL', 'ADMA', 'AGYS', 'ALGN', 'ALNT', 'ALTS', 'AMAT', 'AMBA',
    'AMD', 'AMKR', 'AMSC', 'AMTX', 'AMZN', 'ANGI', 'AOSL', 'APEI', 'ARCB', 'ARDX',
    'ARLP', 'ARQ', 'ARWR', 'ASML', 'ASND', 'ASTH', 'ATEC', 'ATRC', 'ATRO', 'ATXS',
    'AUPH', 'AVDL', 'AVGO', 'AVXL', 'AXGN', 'AXON', 'BBSI', 'BJRI', 'BKR', 'BLBD',
    'BOOM', 'BPOP', 'BRKR', 'CAMT', 'CAR', 'CASH', 'CDNA', 'CDZI', 'CECO', 'CENX'
]

# Bar configurations
BAR_CONFIGS = [
    ('regular', 1), ('regular', 2), ('regular', 3), ('regular', 4), ('regular', 5),
    ('heiken_ashi', 1), ('heiken_ashi', 2), ('heiken_ashi', 3), ('heiken_ashi', 4), ('heiken_ashi', 5),
    ('linreg', 1), ('linreg', 2), ('linreg', 3), ('linreg', 4), ('linreg', 5),
]

# Parameter grid for optimization phase
BREAKOUT_PERIODS = [10, 15, 20, 30]
BREAKDOWN_PERIODS = [5, 10, 15]
TRAILING_STOPS = [0.10, 0.15, 0.20, 0.25]

# Fixed params
VOLUME_MULT = 1.5
TREND_MA = 50
MAX_HOLD = 60
INITIAL_CAPITAL = 500000
POSITION_SIZE = 10000
MAX_POSITIONS = 30


class BreakoutOptimizer:
    """Optimized breakout strategy for parameter search."""

    def __init__(self, breakout_period, breakdown_period, trailing_stop,
                 volume_mult=1.5, trend_ma=50, max_hold=60):
        self.breakout_period = breakout_period
        self.breakdown_period = breakdown_period
        self.trailing_stop = trailing_stop
        self.volume_mult = volume_mult
        self.trend_ma = trend_ma
        self.max_hold = max_hold

    def run_backtest(self, all_data: dict) -> dict:
        start_date = pd.to_datetime('2017-04-01')
        end_date = pd.to_datetime('2025-11-01')

        all_dates = set()
        for df in all_data.values():
            all_dates.update(df.index.tolist())
        all_dates = sorted([d for d in all_dates if start_date <= d <= end_date])

        cash = INITIAL_CAPITAL
        positions = {}
        trades = []
        portfolio_values = []

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
                if idx >= self.breakdown_period:
                    m_low = df['low'].iloc[idx - self.breakdown_period:idx].min()
                    if current < m_low:
                        should_exit = True
                        reason = 'breakdown'

                # Trailing stop
                if not should_exit:
                    stop_price = pos['highest'] * (1 - self.trailing_stop)
                    if current < stop_price:
                        should_exit = True
                        reason = 'trailing'

                # Max hold
                if not should_exit and (idx - pos['entry_idx']) >= self.max_hold:
                    should_exit = True
                    reason = 'max_hold'

                if should_exit:
                    pnl = (current - pos['entry_price']) * pos['shares']
                    cash += pos['shares'] * current
                    trades.append({'pnl': pnl, 'reason': reason})
                    del positions[symbol]

            # Check entries
            if len(positions) < MAX_POSITIONS:
                for symbol, df in all_data.items():
                    if symbol in positions or date not in df.index:
                        continue

                    idx = df.index.get_loc(date)
                    if idx < max(self.breakout_period, self.trend_ma, 20):
                        continue

                    current = df['close'].iloc[idx]
                    vol = df['volume'].iloc[idx]

                    # Entry conditions
                    n_high = df['high'].iloc[idx - self.breakout_period:idx].max()
                    avg_vol = df['volume'].iloc[idx - 20:idx].mean()
                    ma = df['close'].iloc[idx - self.trend_ma:idx].mean()

                    if current > n_high and vol > avg_vol * self.volume_mult and current > ma:
                        if cash >= POSITION_SIZE and current > 0:
                            shares = int(POSITION_SIZE / current)
                            if shares > 0:
                                cash -= shares * current
                                positions[symbol] = {
                                    'entry_idx': idx,
                                    'entry_price': current,
                                    'shares': shares,
                                    'highest': current
                                }
                                if len(positions) >= MAX_POSITIONS:
                                    break

            # Portfolio value
            pos_val = sum(
                pos['shares'] * all_data[sym].loc[date, 'close']
                if sym in all_data and date in all_data[sym].index
                else pos['shares'] * pos['entry_price']
                for sym, pos in positions.items()
            )
            portfolio_values.append({'date': date, 'value': cash + pos_val})

        # Close remaining
        for symbol, pos in positions.items():
            if symbol in all_data and len(all_data[symbol]) > 0:
                exit_price = all_data[symbol]['close'].iloc[-1]
                trades.append({'pnl': (exit_price - pos['entry_price']) * pos['shares'], 'reason': 'end'})

        return self._calc_metrics(trades, portfolio_values)

    def _calc_metrics(self, trades, portfolio_values):
        if not trades or not portfolio_values:
            return {'total_return': 0, 'sharpe': 0, 'max_dd': 0, 'trades': 0, 'win_rate': 0, 'pf': 0}

        pv = pd.DataFrame(portfolio_values)
        final = pv['value'].iloc[-1]
        total_return = ((final / INITIAL_CAPITAL) - 1) * 100

        pv['peak'] = pv['value'].cummax()
        pv['dd'] = (pv['value'] - pv['peak']) / pv['peak'] * 100
        max_dd = pv['dd'].min()

        days = (pv['date'].iloc[-1] - pv['date'].iloc[0]).days
        years = days / 365.25
        ann_return = ((final / INITIAL_CAPITAL) ** (1/years) - 1) * 100 if years > 0 else 0

        pv['month'] = pv['date'].dt.to_period('M')
        monthly = pv.groupby('month')['value'].last().pct_change().dropna()
        sharpe = (monthly.mean() - 0.05/12) / monthly.std() * np.sqrt(12) if len(monthly) > 1 and monthly.std() > 0 else 0

        trades_df = pd.DataFrame(trades)
        n_trades = len(trades_df)
        winning = len(trades_df[trades_df['pnl'] > 0])
        win_rate = (winning / n_trades * 100) if n_trades > 0 else 0

        gp = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gl = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        pf = gp / gl if gl > 0 else 999

        return {
            'total_return': total_return,
            'ann_return': ann_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'trades': n_trades,
            'win_rate': win_rate,
            'pf': min(pf, 999),
            'final': final
        }


def load_candle_data(candle_type, aggregation, symbols):
    conn = psycopg2.connect(**DB_CONFIG)
    all_data = {}

    for symbol in symbols:
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

    conn.close()
    return all_data


def run_bar_type_experiment():
    """Phase 1: Test all bar types with default parameters."""
    print("=" * 80)
    print("PHASE 1: BAR TYPE EXPERIMENT")
    print("=" * 80)
    print(f"Testing {len(BAR_CONFIGS)} bar configurations with default params")
    print(f"Default: Breakout=20, Breakdown=10, TrailingStop=15%")
    print("-" * 80)

    results = []

    for i, (candle_type, agg) in enumerate(BAR_CONFIGS):
        config_name = f"{candle_type}_{agg}d"
        print(f"[{i+1}/{len(BAR_CONFIGS)}] {config_name}...", end=" ")

        all_data = load_candle_data(candle_type, agg, TEST_SYMBOLS)

        if len(all_data) < 20:
            print("SKIP (insufficient data)")
            continue

        strategy = BreakoutOptimizer(
            breakout_period=20,
            breakdown_period=10,
            trailing_stop=0.15
        )

        metrics = strategy.run_backtest(all_data)
        metrics['candle_type'] = candle_type
        metrics['aggregation'] = agg
        metrics['config'] = config_name

        results.append(metrics)
        print(f"Return={metrics['total_return']:.1f}% Sharpe={metrics['sharpe']:.2f} MaxDD={metrics['max_dd']:.1f}%")

    results_df = pd.DataFrame(results).sort_values('sharpe', ascending=False)

    print("\n" + "=" * 80)
    print("BAR TYPE RESULTS - Sorted by Sharpe")
    print("=" * 80)
    print(f"\n{'Config':<18} {'Return':>10} {'Sharpe':>10} {'MaxDD':>10} {'WinRate':>10} {'Trades':>8}")
    print("-" * 70)

    for _, row in results_df.iterrows():
        print(f"{row['config']:<18} {row['total_return']:>9.1f}% {row['sharpe']:>10.3f} "
              f"{row['max_dd']:>9.1f}% {row['win_rate']:>9.1f}% {row['trades']:>8}")

    # Best by type
    print("\n" + "=" * 80)
    print("BEST BY BAR TYPE")
    print("=" * 80)

    for ct in ['regular', 'heiken_ashi', 'linreg']:
        subset = results_df[results_df['candle_type'] == ct]
        if len(subset) > 0:
            best = subset.iloc[0]
            print(f"{ct.upper()}: {best['config']} (Sharpe={best['sharpe']:.3f}, Return={best['total_return']:.1f}%)")

    return results_df


def run_parameter_optimization(best_bar_config):
    """Phase 2: Optimize parameters on best bar type."""
    candle_type, agg = best_bar_config
    agg = int(agg)  # Convert numpy.int64 to int

    print("\n" + "=" * 80)
    print(f"PHASE 2: PARAMETER OPTIMIZATION on {candle_type}_{agg}d")
    print("=" * 80)

    param_grid = list(product(BREAKOUT_PERIODS, BREAKDOWN_PERIODS, TRAILING_STOPS))
    print(f"Testing {len(param_grid)} parameter combinations")
    print(f"Breakout: {BREAKOUT_PERIODS}")
    print(f"Breakdown: {BREAKDOWN_PERIODS}")
    print(f"Trailing Stop: {[f'{x*100:.0f}%' for x in TRAILING_STOPS]}")
    print("-" * 80)

    all_data = load_candle_data(candle_type, agg, TEST_SYMBOLS)
    print(f"Loaded {len(all_data)} symbols")

    results = []

    for i, (bp, bd, ts) in enumerate(param_grid):
        config_name = f"BO{bp}_BD{bd}_TS{int(ts*100)}"

        strategy = BreakoutOptimizer(
            breakout_period=bp,
            breakdown_period=bd,
            trailing_stop=ts
        )

        metrics = strategy.run_backtest(all_data)
        metrics['breakout'] = bp
        metrics['breakdown'] = bd
        metrics['trailing_stop'] = ts * 100
        metrics['config'] = config_name

        results.append(metrics)

        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{len(param_grid)}] {config_name}: "
                  f"Return={metrics['total_return']:.1f}% Sharpe={metrics['sharpe']:.2f}")

    results_df = pd.DataFrame(results).sort_values('sharpe', ascending=False)

    print("\n" + "=" * 80)
    print("TOP 10 PARAMETER COMBINATIONS")
    print("=" * 80)
    print(f"\n{'Config':<18} {'Return':>10} {'Sharpe':>10} {'MaxDD':>10} {'WinRate':>10} {'PF':>8}")
    print("-" * 70)

    for _, row in results_df.head(10).iterrows():
        print(f"{row['config']:<18} {row['total_return']:>9.1f}% {row['sharpe']:>10.3f} "
              f"{row['max_dd']:>9.1f}% {row['win_rate']:>9.1f}% {row['pf']:>8.2f}")

    # Best config
    best = results_df.iloc[0]
    print("\n" + "=" * 80)
    print("OPTIMAL CONFIGURATION")
    print("=" * 80)
    print(f"\nParameters:")
    print(f"  Bar Type:       {candle_type}_{agg}d")
    print(f"  Breakout:       {int(best['breakout'])} days")
    print(f"  Breakdown:      {int(best['breakdown'])} days")
    print(f"  Trailing Stop:  {int(best['trailing_stop'])}%")
    print(f"\nPerformance:")
    print(f"  Total Return:   {best['total_return']:.2f}%")
    print(f"  Annualized:     {best['ann_return']:.2f}%")
    print(f"  Max Drawdown:   {best['max_dd']:.2f}%")
    print(f"  Sharpe Ratio:   {best['sharpe']:.3f}")
    print(f"  Win Rate:       {best['win_rate']:.2f}%")
    print(f"  Profit Factor:  {best['pf']:.2f}")

    # Parameter sensitivity
    print("\n" + "=" * 80)
    print("PARAMETER SENSITIVITY")
    print("=" * 80)

    print("\nBy Breakout Period:")
    for bp in BREAKOUT_PERIODS:
        subset = results_df[results_df['breakout'] == bp]
        print(f"  {bp}d: Avg Sharpe={subset['sharpe'].mean():.3f}, Avg Return={subset['total_return'].mean():.1f}%")

    print("\nBy Breakdown Period:")
    for bd in BREAKDOWN_PERIODS:
        subset = results_df[results_df['breakdown'] == bd]
        print(f"  {bd}d: Avg Sharpe={subset['sharpe'].mean():.3f}, Avg Return={subset['total_return'].mean():.1f}%")

    print("\nBy Trailing Stop:")
    for ts in TRAILING_STOPS:
        subset = results_df[results_df['trailing_stop'] == ts * 100]
        print(f"  {ts*100:.0f}%: Avg Sharpe={subset['sharpe'].mean():.3f}, Avg Return={subset['total_return'].mean():.1f}%")

    return results_df, best


def main():
    print("=" * 80)
    print("BREAKOUT MOMENTUM - FULL OPTIMIZATION")
    print("=" * 80)
    print(f"Symbols: {len(TEST_SYMBOLS)}")
    print(f"Bar types: {len(BAR_CONFIGS)}")
    print("-" * 80)

    # Phase 1: Bar type experiment
    bar_results = run_bar_type_experiment()

    # Get best bar config
    best_bar = bar_results.iloc[0]
    best_bar_config = (best_bar['candle_type'], best_bar['aggregation'])

    # Phase 2: Parameter optimization
    param_results, best_params = run_parameter_optimization(best_bar_config)

    # Save all results
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    bar_results.to_csv(f'results/breakout_bar_experiment_{timestamp}.csv', index=False)
    param_results.to_csv(f'results/breakout_param_optimization_{timestamp}.csv', index=False)

    print(f"\nResults saved to results/breakout_*_{timestamp}.csv")

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"\nBest Bar Type: {best_bar['config']}")
    print(f"Best Parameters: BO{int(best_params['breakout'])}_BD{int(best_params['breakdown'])}_TS{int(best_params['trailing_stop'])}")
    print(f"\nFinal Performance:")
    print(f"  Sharpe: {best_params['sharpe']:.3f}")
    print(f"  Return: {best_params['total_return']:.2f}%")
    print(f"  Max DD: {best_params['max_dd']:.2f}%")

    return bar_results, param_results


if __name__ == '__main__':
    bar_results, param_results = main()
