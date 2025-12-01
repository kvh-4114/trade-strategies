#!/usr/bin/env python3
"""
Dual Momentum Full Validation - All 268 Symbols

Runs optimized Dual Momentum configurations on full symbol set:
- Conservative: LB6m_E20_X35 (lower drawdown, more trades)
- Aggressive: LB18m_E25_X40 (higher returns, higher risk)

Uses LinReg_5d bars (winner from bar experiment)
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

# Optimized configurations to test
CONFIGS = {
    'conservative': {
        'name': 'LB6m_E20_X35',
        'lookback_months': 6,
        'entry_pct': 0.20,
        'exit_pct': 0.35
    },
    'aggressive': {
        'name': 'LB18m_E25_X40',
        'lookback_months': 18,
        'entry_pct': 0.25,
        'exit_pct': 0.40
    }
}

# Fixed params
POSITION_SIZE = 10000
INITIAL_CAPITAL = 1000000
CANDLE_TYPE = 'linreg'
AGGREGATION = 5


class DualMomentumFull:
    """Full-scale Dual Momentum backtest."""

    def __init__(self, lookback_months, entry_pct, exit_pct, position_size=10000):
        self.lookback_days = lookback_months * 21
        self.entry_pct = entry_pct
        self.exit_pct = exit_pct
        self.position_size = position_size
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

    def run_backtest(self, all_data: dict, start_date='2017-04-01', end_date='2025-11-01') -> dict:
        self.trades = []
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        rebalance_dates = pd.date_range(start=start_dt, end=end_dt, freq='MS')

        cash = INITIAL_CAPITAL
        positions = {}
        portfolio_history = []

        for rebalance_date in rebalance_dates:
            # Calculate momentum scores
            momentum_scores = {}
            for symbol, df in all_data.items():
                df_subset = df[df.index <= rebalance_date]
                if len(df_subset) < self.lookback_days // 5:
                    continue
                momentum = self.calculate_momentum(df_subset['close'])
                if not np.isnan(momentum):
                    momentum_scores[symbol] = momentum

            if not momentum_scores:
                continue

            # Rank and filter
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

            # Exit positions
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
                        'pnl_pct': pnl_pct
                    })
                    del positions[symbol]

            # Enter new positions
            for symbol in top_for_entry:
                if symbol not in positions and symbol in prices:
                    price = prices[symbol]
                    if cash >= self.position_size and price > 0:
                        shares = int(self.position_size / price)
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
                'value': cash + pos_value,
                'cash': cash,
                'positions': len(positions),
                'invested': pos_value
            })

        # Close remaining positions
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
                    'pnl_pct': pnl_pct
                })

        return self._calc_metrics(pd.DataFrame(self.trades), pd.DataFrame(portfolio_history))

    def _calc_metrics(self, trades_df, portfolio_df):
        if len(trades_df) == 0 or len(portfolio_df) == 0:
            return {'error': 'No trades'}

        # Trade metrics
        total_trades = len(trades_df)
        winning = len(trades_df[trades_df['pnl'] > 0])
        losing = len(trades_df[trades_df['pnl'] < 0])
        win_rate = winning / total_trades * 100

        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999

        avg_win = trades_df[trades_df['pnl'] > 0]['pnl_pct'].mean() if winning > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl_pct'].mean() if losing > 0 else 0

        # Portfolio metrics
        final = portfolio_df['value'].iloc[-1]
        total_return = ((final / INITIAL_CAPITAL) - 1) * 100

        portfolio_df['peak'] = portfolio_df['value'].cummax()
        portfolio_df['dd'] = (portfolio_df['value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_dd = portfolio_df['dd'].min()

        # Annualized
        days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
        years = days / 365.25
        ann_return = ((final / INITIAL_CAPITAL) ** (1/years) - 1) * 100 if years > 0 else 0

        # Sharpe
        monthly_ret = portfolio_df['value'].pct_change().dropna()
        sharpe = (monthly_ret.mean() - 0.05/12) / monthly_ret.std() * np.sqrt(12) if len(monthly_ret) > 1 and monthly_ret.std() > 0 else 0

        # Annual returns
        portfolio_df['year'] = portfolio_df['date'].dt.year
        annual_returns = []
        for year in sorted(portfolio_df['year'].unique()):
            year_data = portfolio_df[portfolio_df['year'] == year]
            if len(year_data) >= 2:
                yr_return = ((year_data['value'].iloc[-1] / year_data['value'].iloc[0]) - 1) * 100
                annual_returns.append({'year': year, 'return': yr_return})

        return {
            'total_trades': total_trades,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': win_rate,
            'profit_factor': min(profit_factor, 999),
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'total_return': total_return,
            'ann_return': ann_return,
            'max_dd': max_dd,
            'sharpe': sharpe,
            'final_value': final,
            'annual_returns': annual_returns,
            'trades_df': trades_df,
            'portfolio_df': portfolio_df
        }


def load_all_linreg_data():
    """Load LinReg_5d candles for all symbols."""
    conn = psycopg2.connect(**DB_CONFIG)

    # Get all symbols
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM candles WHERE candle_type = %s ORDER BY symbol", (CANDLE_TYPE,))
        symbols = [r[0] for r in cur.fetchall()]

    print(f"Loading {CANDLE_TYPE}_{AGGREGATION}d data for {len(symbols)} symbols...")

    all_data = {}
    for i, symbol in enumerate(symbols):
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

        if (i + 1) % 50 == 0:
            print(f"  Loaded {i+1}/{len(symbols)}...")

    conn.close()
    print(f"Loaded {len(all_data)} symbols total")
    return all_data


def run_full_validation():
    """Run both optimized configs on all symbols."""

    print("=" * 80)
    print("DUAL MOMENTUM - FULL VALIDATION (268 Symbols)")
    print("=" * 80)
    print(f"Bar Type: {CANDLE_TYPE}_{AGGREGATION}d")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"Position Size: ${POSITION_SIZE:,}")
    print("-" * 80)

    # Load data
    all_data = load_all_linreg_data()

    results = {}

    for config_type, params in CONFIGS.items():
        print(f"\n{'='*80}")
        print(f"Running {config_type.upper()} config: {params['name']}")
        print(f"  Lookback: {params['lookback_months']} months")
        print(f"  Entry: Top {params['entry_pct']*100:.0f}%")
        print(f"  Exit: Top {params['exit_pct']*100:.0f}%")
        print("-" * 80)

        strategy = DualMomentumFull(
            lookback_months=params['lookback_months'],
            entry_pct=params['entry_pct'],
            exit_pct=params['exit_pct'],
            position_size=POSITION_SIZE
        )

        metrics = strategy.run_backtest(all_data)
        metrics['config_type'] = config_type
        metrics['config_name'] = params['name']
        results[config_type] = metrics

        # Print results
        print(f"\nRESULTS: {params['name']}")
        print("-" * 40)
        print(f"Total Return:      {metrics['total_return']:.2f}%")
        print(f"Annualized Return: {metrics['ann_return']:.2f}%")
        print(f"Max Drawdown:      {metrics['max_dd']:.2f}%")
        print(f"Sharpe Ratio:      {metrics['sharpe']:.3f}")
        print(f"Total Trades:      {metrics['total_trades']}")
        print(f"Win Rate:          {metrics['win_rate']:.2f}%")
        print(f"Profit Factor:     {metrics['profit_factor']:.2f}")
        print(f"Avg Win:           {metrics['avg_win_pct']:.2f}%")
        print(f"Avg Loss:          {metrics['avg_loss_pct']:.2f}%")
        print(f"Final Value:       ${metrics['final_value']:,.2f}")

        print(f"\nAnnual Returns:")
        for ar in metrics['annual_returns']:
            print(f"  {ar['year']}: {ar['return']:>8.2f}%")

    # Side-by-side comparison
    print("\n" + "=" * 80)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 80)

    cons = results['conservative']
    aggr = results['aggressive']

    print(f"\n{'Metric':<25} {'Conservative':>18} {'Aggressive':>18}")
    print("-" * 65)
    print(f"{'Config':<25} {cons['config_name']:>18} {aggr['config_name']:>18}")
    print(f"{'Total Return':<25} {cons['total_return']:>17.2f}% {aggr['total_return']:>17.2f}%")
    print(f"{'Annualized Return':<25} {cons['ann_return']:>17.2f}% {aggr['ann_return']:>17.2f}%")
    print(f"{'Max Drawdown':<25} {cons['max_dd']:>17.2f}% {aggr['max_dd']:>17.2f}%")
    print(f"{'Sharpe Ratio':<25} {cons['sharpe']:>18.3f} {aggr['sharpe']:>18.3f}")
    print(f"{'Win Rate':<25} {cons['win_rate']:>17.2f}% {aggr['win_rate']:>17.2f}%")
    print(f"{'Profit Factor':<25} {cons['profit_factor']:>18.2f} {aggr['profit_factor']:>18.2f}")
    print(f"{'Total Trades':<25} {cons['total_trades']:>18} {aggr['total_trades']:>18}")
    print(f"{'Final Value':<25} ${cons['final_value']:>16,.0f} ${aggr['final_value']:>16,.0f}")

    # Determine winner
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    if cons['sharpe'] > aggr['sharpe']:
        winner = 'conservative'
        winner_data = cons
    else:
        winner = 'aggressive'
        winner_data = aggr

    print(f"\nBest Risk-Adjusted Performance: {winner.upper()} ({winner_data['config_name']})")
    print(f"  - Sharpe Ratio: {winner_data['sharpe']:.3f}")
    print(f"  - Annualized Return: {winner_data['ann_return']:.2f}%")
    print(f"  - Max Drawdown: {winner_data['max_dd']:.2f}%")

    # Save results
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for config_type, metrics in results.items():
        # Save trades
        trades_path = f"results/dual_momentum_full_{config_type}_trades_{timestamp}.csv"
        metrics['trades_df'].to_csv(trades_path, index=False)

        # Save portfolio
        portfolio_path = f"results/dual_momentum_full_{config_type}_portfolio_{timestamp}.csv"
        metrics['portfolio_df'].to_csv(portfolio_path, index=False)

    # Save summary
    summary = []
    for config_type, metrics in results.items():
        summary.append({
            'config': metrics['config_name'],
            'type': config_type,
            'total_return': metrics['total_return'],
            'ann_return': metrics['ann_return'],
            'max_dd': metrics['max_dd'],
            'sharpe': metrics['sharpe'],
            'win_rate': metrics['win_rate'],
            'profit_factor': metrics['profit_factor'],
            'total_trades': metrics['total_trades'],
            'final_value': metrics['final_value']
        })

    summary_df = pd.DataFrame(summary)
    summary_path = f"results/dual_momentum_full_summary_{timestamp}.csv"
    summary_df.to_csv(summary_path, index=False)

    print(f"\nResults saved to results/dual_momentum_full_*_{timestamp}.csv")

    return results


if __name__ == '__main__':
    results = run_full_validation()
