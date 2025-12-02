#!/usr/bin/env python3
"""
Short-Side Hedge Strategy

Concept: Reduce exposure or go defensive when market stress indicators trigger.
Uses a simple moving average crossover on the broader market (SPY proxy via avg of all symbols)
combined with volatility regime detection.

Hedge Signals:
1. Market below 200-day SMA = reduce exposure
2. Short-term MA < Long-term MA = defensive mode
3. High volatility regime = smaller positions

This strategy is meant to OVERLAY on Dual Momentum to reduce drawdowns.
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

# Hedge parameters
FAST_MA = 50
SLOW_MA = 200
VOLATILITY_LOOKBACK = 20
HIGH_VOL_THRESHOLD = 1.5  # 1.5x normal volatility = defensive

INITIAL_CAPITAL = 1000000
POSITION_SIZE = 10000


class MarketRegimeDetector:
    """Detects market regime using aggregate market data."""

    def __init__(self, fast_ma=50, slow_ma=200, vol_lookback=20):
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.vol_lookback = vol_lookback

    def calculate_market_index(self, all_data: dict, date: pd.Timestamp) -> dict:
        """Calculate aggregate market metrics from all symbols."""
        prices = []
        returns = []

        for symbol, df in all_data.items():
            df_subset = df[df.index <= date]
            if len(df_subset) >= self.slow_ma:
                prices.append(df_subset['close'].iloc[-1])
                if len(df_subset) >= 2:
                    ret = (df_subset['close'].iloc[-1] / df_subset['close'].iloc[-2]) - 1
                    returns.append(ret)

        if not prices:
            return {'regime': 'unknown', 'exposure': 1.0}

        # Calculate aggregate metrics
        avg_return = np.mean(returns) if returns else 0
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0

        return {
            'avg_return': avg_return,
            'volatility': volatility,
            'n_symbols': len(prices)
        }

    def get_regime(self, all_data: dict, date: pd.Timestamp) -> dict:
        """Determine market regime and recommended exposure."""

        # Calculate market breadth and trend
        above_fast_ma = 0
        above_slow_ma = 0
        total = 0
        recent_returns = []

        for symbol, df in all_data.items():
            df_subset = df[df.index <= date]
            if len(df_subset) < self.slow_ma:
                continue

            total += 1
            current_price = df_subset['close'].iloc[-1]
            fast_ma = df_subset['close'].iloc[-self.fast_ma:].mean()
            slow_ma = df_subset['close'].iloc[-self.slow_ma:].mean()

            if current_price > fast_ma:
                above_fast_ma += 1
            if current_price > slow_ma:
                above_slow_ma += 1

            # Recent volatility
            if len(df_subset) >= self.vol_lookback:
                rets = df_subset['close'].pct_change().iloc[-self.vol_lookback:]
                recent_returns.extend(rets.dropna().tolist())

        if total == 0:
            return {'regime': 'unknown', 'exposure': 1.0, 'reason': 'No data'}

        # Breadth indicators
        pct_above_fast = above_fast_ma / total
        pct_above_slow = above_slow_ma / total

        # Volatility
        current_vol = np.std(recent_returns) * np.sqrt(252) if recent_returns else 0

        # Determine regime
        if pct_above_slow < 0.3:
            # Bear market - less than 30% above 200 SMA
            regime = 'bear'
            exposure = 0.25
            reason = f'Bear: Only {pct_above_slow*100:.0f}% above 200 SMA'
        elif pct_above_slow < 0.5:
            # Correction
            regime = 'correction'
            exposure = 0.50
            reason = f'Correction: {pct_above_slow*100:.0f}% above 200 SMA'
        elif pct_above_fast < 0.4:
            # Short-term weakness
            regime = 'weak'
            exposure = 0.75
            reason = f'Weak: Only {pct_above_fast*100:.0f}% above 50 SMA'
        else:
            # Bull market
            regime = 'bull'
            exposure = 1.0
            reason = f'Bull: {pct_above_slow*100:.0f}% above 200 SMA'

        # Adjust for high volatility
        if current_vol > 0.25:  # >25% annualized vol
            exposure *= 0.75
            reason += f' | High Vol ({current_vol*100:.0f}%)'

        return {
            'regime': regime,
            'exposure': exposure,
            'reason': reason,
            'pct_above_fast': pct_above_fast,
            'pct_above_slow': pct_above_slow,
            'volatility': current_vol
        }


class HedgedDualMomentum:
    """Dual Momentum with market regime overlay."""

    def __init__(self, lookback_months=18, entry_pct=0.25, exit_pct=0.40):
        self.lookback_days = lookback_months * 21
        self.entry_pct = entry_pct
        self.exit_pct = exit_pct
        self.regime_detector = MarketRegimeDetector()
        self.trades = []
        self.regime_history = []

    def calculate_momentum(self, prices):
        actual_lookback = min(self.lookback_days, len(prices) - 1)
        if actual_lookback < 30:
            return np.nan
        return ((prices.iloc[-1] / prices.iloc[-actual_lookback]) - 1) * 100

    def run_backtest(self, all_data: dict) -> dict:
        self.trades = []
        self.regime_history = []

        start_dt = pd.to_datetime('2017-04-01')
        end_dt = pd.to_datetime('2025-11-01')
        rebalance_dates = pd.date_range(start=start_dt, end=end_dt, freq='MS')

        cash = INITIAL_CAPITAL
        positions = {}
        portfolio_history = []

        for rebalance_date in rebalance_dates:
            # Get market regime
            regime_info = self.regime_detector.get_regime(all_data, rebalance_date)
            exposure = regime_info['exposure']

            self.regime_history.append({
                'date': rebalance_date,
                'regime': regime_info['regime'],
                'exposure': exposure,
                'reason': regime_info['reason']
            })

            # Adjusted position size based on regime
            adjusted_position_size = POSITION_SIZE * exposure

            # Calculate momentum
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

            # In bear market, be more selective
            if regime_info['regime'] == 'bear':
                entry_cutoff = max(1, entry_cutoff // 2)

            top_for_entry = set([s for s, m in ranked[:entry_cutoff] if m > 0])
            to_hold = set([s for s, m in ranked[:exit_cutoff] if m > 0])

            # Get prices
            prices = {}
            for symbol, df in all_data.items():
                prior = df.index[df.index <= rebalance_date]
                if len(prior) > 0:
                    prices[symbol] = df.loc[prior[-1], 'close']

            # Exit positions
            for symbol in list(positions.keys()):
                should_exit = symbol not in to_hold
                # Force exit more positions in bear market
                if regime_info['regime'] == 'bear' and symbol not in top_for_entry:
                    should_exit = True

                if should_exit and symbol in prices:
                    pos = positions[symbol]
                    exit_price = prices[symbol]
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100
                    cash += pos['shares'] * exit_price

                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': rebalance_date,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_year': rebalance_date.year,
                        'regime_at_exit': regime_info['regime']
                    })
                    del positions[symbol]

            # Enter new positions (with adjusted size)
            if regime_info['regime'] != 'bear':  # Don't enter new positions in bear
                for symbol in top_for_entry:
                    if symbol not in positions and symbol in prices:
                        price = prices[symbol]
                        if cash >= adjusted_position_size and price > 0:
                            shares = int(adjusted_position_size / price)
                            if shares > 0:
                                cash -= shares * price
                                positions[symbol] = {
                                    'shares': shares,
                                    'entry_price': price,
                                    'entry_date': rebalance_date
                                }

            # Portfolio value
            pos_value = sum(pos['shares'] * prices.get(sym, pos['entry_price'])
                           for sym, pos in positions.items())
            total_value = cash + pos_value

            portfolio_history.append({
                'date': rebalance_date,
                'value': total_value,
                'cash': cash,
                'positions': len(positions),
                'regime': regime_info['regime'],
                'exposure': exposure
            })

        # Close remaining
        for symbol, pos in list(positions.items()):
            df = all_data.get(symbol)
            if df is not None and len(df) > 0:
                exit_price = df['close'].iloc[-1]
                pnl = (exit_price - pos['entry_price']) * pos['shares']
                self.trades.append({
                    'symbol': symbol,
                    'entry_date': pos['entry_date'],
                    'exit_date': df.index[-1],
                    'pnl': pnl,
                    'pnl_pct': ((exit_price / pos['entry_price']) - 1) * 100,
                    'exit_year': df.index[-1].year,
                    'regime_at_exit': 'end'
                })

        return self._calc_metrics(pd.DataFrame(self.trades), pd.DataFrame(portfolio_history))

    def _calc_metrics(self, trades_df, portfolio_df):
        if len(trades_df) == 0 or len(portfolio_df) == 0:
            return {'error': 'No trades'}

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
        winning = len(trades_df[trades_df['pnl'] > 0])
        win_rate = (winning / n_trades * 100) if n_trades > 0 else 0

        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 999

        # Annual returns
        portfolio_df['year'] = portfolio_df['date'].dt.year
        annual = []
        for year in sorted(portfolio_df['year'].unique()):
            yd = portfolio_df[portfolio_df['year'] == year]
            if len(yd) >= 2:
                yr = ((yd['value'].iloc[-1] / yd['value'].iloc[0]) - 1) * 100
                yr_dd = yd['dd'].min()
                annual.append({'year': year, 'return': yr, 'max_dd': yr_dd})

        return {
            'total_return': total_return,
            'ann_return': ann_return,
            'max_dd': max_dd,
            'sharpe': sharpe,
            'total_trades': n_trades,
            'win_rate': win_rate,
            'profit_factor': min(pf, 999),
            'final_value': final,
            'annual': annual,
            'trades_df': trades_df,
            'portfolio_df': portfolio_df,
            'regime_df': pd.DataFrame(self.regime_history)
        }


def load_data():
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM candles WHERE candle_type = 'linreg' ORDER BY symbol")
        symbols = [r[0] for r in cur.fetchall()]

    print(f"Loading LinReg_5d data for {len(symbols)} symbols...")
    all_data = {}

    for i, symbol in enumerate(symbols):
        query = """
            SELECT date, close FROM candles
            WHERE symbol = %s AND candle_type = 'linreg' AND aggregation_days = 5
            ORDER BY date
        """
        with conn.cursor() as cur:
            cur.execute(query, (symbol,))
            rows = cur.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=['date', 'close'])
                df['close'] = df['close'].astype(float)
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
    print("HEDGED DUAL MOMENTUM STRATEGY")
    print("=" * 80)
    print("Dual Momentum + Market Regime Overlay")
    print("-" * 80)

    all_data = load_data()

    # Run hedged strategy
    print("\nRunning HEDGED Dual Momentum...")
    hedged = HedgedDualMomentum(lookback_months=18, entry_pct=0.25, exit_pct=0.40)
    hedged_results = hedged.run_backtest(all_data)

    # Print results
    print("\n" + "=" * 80)
    print("HEDGED DUAL MOMENTUM RESULTS")
    print("=" * 80)

    print(f"\nTotal Return:      {hedged_results['total_return']:.2f}%")
    print(f"Annualized Return: {hedged_results['ann_return']:.2f}%")
    print(f"Max Drawdown:      {hedged_results['max_dd']:.2f}%")
    print(f"Sharpe Ratio:      {hedged_results['sharpe']:.3f}")
    print(f"Total Trades:      {hedged_results['total_trades']}")
    print(f"Win Rate:          {hedged_results['win_rate']:.2f}%")
    print(f"Profit Factor:     {hedged_results['profit_factor']:.2f}")
    print(f"Final Value:       ${hedged_results['final_value']:,.2f}")

    print(f"\n{'Year':<6} {'Return':>10} {'MaxDD':>10}")
    print("-" * 30)
    for ar in hedged_results['annual']:
        print(f"{ar['year']:<6} {ar['return']:>9.2f}% {ar['max_dd']:>9.2f}%")

    # Regime analysis
    regime_df = hedged_results['regime_df']
    print("\n" + "=" * 80)
    print("REGIME ANALYSIS")
    print("=" * 80)

    regime_counts = regime_df['regime'].value_counts()
    print("\nRegime Distribution:")
    for regime, count in regime_counts.items():
        pct = count / len(regime_df) * 100
        print(f"  {regime:<12}: {count:>3} months ({pct:.1f}%)")

    # Show regime by year
    regime_df['year'] = regime_df['date'].dt.year
    print("\nRegime by Year:")
    for year in sorted(regime_df['year'].unique()):
        year_regimes = regime_df[regime_df['year'] == year]['regime'].value_counts()
        regime_str = ', '.join([f"{r}: {c}" for r, c in year_regimes.items()])
        print(f"  {year}: {regime_str}")

    # Comparison with unhedged
    print("\n" + "=" * 80)
    print("COMPARISON: HEDGED vs UNHEDGED")
    print("=" * 80)

    # Reference values from previous unhedged run
    unhedged = {
        'total_return': 310.96,
        'ann_return': 17.89,
        'max_dd': -41.60,
        'sharpe': 0.557
    }

    print(f"\n{'Metric':<20} {'Unhedged':>15} {'Hedged':>15} {'Improvement':>15}")
    print("-" * 65)
    print(f"{'Total Return':<20} {unhedged['total_return']:>14.2f}% {hedged_results['total_return']:>14.2f}% {hedged_results['total_return']-unhedged['total_return']:>+14.2f}%")
    print(f"{'Annualized':<20} {unhedged['ann_return']:>14.2f}% {hedged_results['ann_return']:>14.2f}% {hedged_results['ann_return']-unhedged['ann_return']:>+14.2f}%")
    print(f"{'Max Drawdown':<20} {unhedged['max_dd']:>14.2f}% {hedged_results['max_dd']:>14.2f}% {hedged_results['max_dd']-unhedged['max_dd']:>+14.2f}%")
    print(f"{'Sharpe Ratio':<20} {unhedged['sharpe']:>15.3f} {hedged_results['sharpe']:>15.3f} {hedged_results['sharpe']-unhedged['sharpe']:>+15.3f}")

    # Save results
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    hedged_results['portfolio_df'].to_csv(f'results/hedged_dual_momentum_portfolio_{timestamp}.csv', index=False)
    hedged_results['trades_df'].to_csv(f'results/hedged_dual_momentum_trades_{timestamp}.csv', index=False)
    regime_df.to_csv(f'results/hedged_dual_momentum_regimes_{timestamp}.csv', index=False)

    print(f"\nResults saved to results/hedged_dual_momentum_*_{timestamp}.csv")

    return hedged_results


if __name__ == '__main__':
    results = main()
