#!/usr/bin/env python3
"""
Dual Momentum Bar Type Experiment

Tests Dual Momentum strategy across different bar types and aggregations:
- Regular: 1, 2, 3, 4, 5 day
- Heiken Ashi: 1, 2, 3, 4, 5 day
- Linear Regression: 1, 2, 3, 4, 5 day

Purpose: Find if different bar constructions improve the strategy.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'mean_reversion'),
    'user': os.getenv('DB_USER', 'trader'),
    'password': os.getenv('DB_PASSWORD', 'trader123')
}

# Experiment configuration
TEST_SYMBOLS = [
    'AAOI', 'AAON', 'AAPL', 'ADMA', 'AGYS', 'ALGN', 'ALNT', 'ALTS', 'AMAT', 'AMBA',
    'AMD', 'AMKR', 'AMSC', 'AMTX', 'AMZN', 'ANGI', 'AOSL', 'APEI', 'ARCB', 'ARDX',
    'ARLP', 'ARQ', 'ARWR', 'ASML', 'ASND', 'ASTH', 'ATEC', 'ATRC', 'ATRO', 'ATXS',
    'AUPH', 'AVDL', 'AVGO', 'AVXL', 'AXGN', 'AXON', 'BBSI', 'BJRI', 'BKR', 'BLBD',
    'BOOM', 'BPOP', 'BRKR', 'CAMT', 'CAR', 'CASH', 'CDNA', 'CDZI', 'CECO', 'CENX'
]

# Bar type configurations to test
BAR_CONFIGS = [
    # Regular bars
    ('regular', 1), ('regular', 2), ('regular', 3), ('regular', 4), ('regular', 5),
    # Heiken Ashi bars
    ('heiken_ashi', 1), ('heiken_ashi', 2), ('heiken_ashi', 3), ('heiken_ashi', 4), ('heiken_ashi', 5),
    # Linear Regression bars
    ('linreg', 1), ('linreg', 2), ('linreg', 3), ('linreg', 4), ('linreg', 5),
]

# Strategy parameters
LOOKBACK_MONTHS = 12
TOP_PERCENTILE = 0.20
EXIT_PERCENTILE = 0.30
POSITION_SIZE = 10000
INITIAL_CAPITAL = 500000  # Smaller capital for 50 symbols


class DualMomentumBarExperiment:
    """Run Dual Momentum with different bar types."""

    def __init__(self, lookback_days=252, top_pct=0.20, exit_pct=0.30, position_size=10000):
        self.lookback_days = lookback_days
        self.top_pct = top_pct
        self.exit_pct = exit_pct
        self.position_size = position_size
        self.trades = []

    def calculate_momentum(self, prices: pd.Series) -> float:
        """Calculate momentum as percentage return over lookback period."""
        # Adjust lookback for aggregation (fewer bars available)
        actual_lookback = min(self.lookback_days, len(prices) - 1)

        if actual_lookback < 50:  # Need at least ~2.5 months
            return np.nan

        current_price = prices.iloc[-1]
        past_price = prices.iloc[-actual_lookback]

        if past_price == 0:
            return np.nan

        return ((current_price / past_price) - 1) * 100

    def run_backtest(self, all_data: dict, start_date: str = '2017-04-01',
                     end_date: str = '2025-11-01', aggregation_days: int = 1) -> dict:
        """
        Run dual momentum backtest.

        Args:
            all_data: Dict of {symbol: DataFrame} with OHLC data
            start_date: Backtest start
            end_date: Backtest end
            aggregation_days: Bar aggregation (affects lookback adjustment)
        """
        self.trades = []
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        # Adjust lookback for aggregation
        adjusted_lookback = max(50, self.lookback_days // aggregation_days)

        # Create monthly rebalance dates
        rebalance_dates = pd.date_range(start=start_dt, end=end_dt, freq='MS')

        portfolio_value = INITIAL_CAPITAL
        cash = INITIAL_CAPITAL
        positions = {}
        portfolio_history = []

        for rebalance_date in rebalance_dates:
            # Calculate momentum for all symbols
            momentum_scores = {}

            for symbol, df in all_data.items():
                df_subset = df[df.index <= rebalance_date]

                if len(df_subset) < adjusted_lookback:
                    continue

                momentum = self.calculate_momentum(df_subset['close'])

                if not np.isnan(momentum):
                    momentum_scores[symbol] = momentum

            if not momentum_scores:
                continue

            # Rank symbols
            ranked_symbols = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
            n_symbols = len(ranked_symbols)

            entry_cutoff = int(n_symbols * self.top_pct)
            exit_cutoff = int(n_symbols * self.exit_pct)

            top_for_entry = set([s for s, m in ranked_symbols[:entry_cutoff] if m > 0])
            symbols_to_hold = set([s for s, m in ranked_symbols[:exit_cutoff] if m > 0])

            # Get current prices
            current_prices = {}
            for symbol, df in all_data.items():
                if rebalance_date in df.index:
                    current_prices[symbol] = df.loc[rebalance_date, 'close']
                else:
                    prior_dates = df.index[df.index <= rebalance_date]
                    if len(prior_dates) > 0:
                        current_prices[symbol] = df.loc[prior_dates[-1], 'close']

            # Exit positions
            for symbol in list(positions.keys()):
                if symbol not in symbols_to_hold:
                    pos = positions[symbol]
                    if symbol in current_prices:
                        exit_price = current_prices[symbol]
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
                if symbol not in positions and symbol in current_prices:
                    price = current_prices[symbol]
                    if cash >= self.position_size and price > 0:
                        shares = int(self.position_size / price)
                        if shares > 0:
                            cost = shares * price
                            cash -= cost
                            positions[symbol] = {
                                'shares': shares,
                                'entry_price': price,
                                'entry_date': rebalance_date
                            }

            # Calculate portfolio value
            position_value = sum(
                pos['shares'] * current_prices.get(sym, pos['entry_price'])
                for sym, pos in positions.items()
            )
            portfolio_value = cash + position_value

            portfolio_history.append({
                'date': rebalance_date,
                'portfolio_value': portfolio_value,
                'cash': cash,
                'positions': len(positions)
            })

        # Close remaining positions
        for symbol, pos in positions.items():
            df = all_data.get(symbol)
            if df is not None:
                final_dates = df.index[df.index <= end_dt]
                if len(final_dates) > 0:
                    exit_price = df.loc[final_dates[-1], 'close']
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    pnl_pct = ((exit_price / pos['entry_price']) - 1) * 100

                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': final_dates[-1],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'shares': pos['shares'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })

        return self._calculate_metrics(pd.DataFrame(self.trades), pd.DataFrame(portfolio_history))

    def _calculate_metrics(self, trades_df: pd.DataFrame, portfolio_df: pd.DataFrame) -> dict:
        """Calculate performance metrics."""

        if len(trades_df) == 0 or len(portfolio_df) == 0:
            return {
                'total_trades': 0, 'win_rate': 0, 'total_return': 0,
                'annualized_return': 0, 'max_drawdown': 0, 'profit_factor': 0,
                'sharpe_ratio': 0, 'final_value': INITIAL_CAPITAL
            }

        # Trade metrics
        total_trades = len(trades_df)
        winning = len(trades_df[trades_df['pnl'] > 0])
        win_rate = winning / total_trades * 100 if total_trades > 0 else 0

        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Portfolio metrics
        final_value = portfolio_df['portfolio_value'].iloc[-1]
        total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100

        # Drawdown
        portfolio_df['peak'] = portfolio_df['portfolio_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['portfolio_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_drawdown = portfolio_df['drawdown'].min()

        # Annualized return
        days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
        years = days / 365.25
        annualized_return = ((final_value / INITIAL_CAPITAL) ** (1/years) - 1) * 100 if years > 0 else 0

        # Sharpe ratio
        monthly_returns = portfolio_df['portfolio_value'].pct_change().dropna()
        if len(monthly_returns) > 1:
            sharpe = (monthly_returns.mean() - 0.05/12) / monthly_returns.std() * np.sqrt(12) if monthly_returns.std() > 0 else 0
        else:
            sharpe = 0

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor if profit_factor != float('inf') else 999.99,
            'sharpe_ratio': sharpe,
            'final_value': final_value,
            'avg_pnl_pct': trades_df['pnl_pct'].mean() if len(trades_df) > 0 else 0
        }


def load_candle_data(candle_type: str, aggregation_days: int, symbols: list) -> dict:
    """Load candle data from database."""

    conn = psycopg2.connect(**DB_CONFIG)
    all_data = {}

    for symbol in symbols:
        query = """
            SELECT date, open, high, low, close, volume
            FROM candles
            WHERE symbol = %s
              AND candle_type = %s
              AND aggregation_days = %s
            ORDER BY date
        """

        with conn.cursor() as cur:
            cur.execute(query, (symbol, candle_type, aggregation_days))
            rows = cur.fetchall()

            if rows:
                df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])

                # Convert types
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)

                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.sort_index(inplace=True)

                all_data[symbol] = df

    conn.close()
    return all_data


def run_experiment():
    """Run the full bar type experiment."""

    print("=" * 80)
    print("DUAL MOMENTUM - BAR TYPE EXPERIMENT")
    print("=" * 80)
    print(f"\nSymbols: {len(TEST_SYMBOLS)}")
    print(f"Bar configurations: {len(BAR_CONFIGS)}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print("-" * 80)

    results = []

    for i, (candle_type, agg_days) in enumerate(BAR_CONFIGS):
        config_name = f"{candle_type}_{agg_days}d"
        print(f"\n[{i+1}/{len(BAR_CONFIGS)}] Testing {config_name}...")

        # Load data
        all_data = load_candle_data(candle_type, agg_days, TEST_SYMBOLS)
        print(f"  Loaded {len(all_data)} symbols")

        if len(all_data) < 10:
            print(f"  SKIP: Insufficient data")
            continue

        # Run backtest
        strategy = DualMomentumBarExperiment(
            lookback_days=252,
            top_pct=TOP_PERCENTILE,
            exit_pct=EXIT_PERCENTILE,
            position_size=POSITION_SIZE
        )

        metrics = strategy.run_backtest(
            all_data,
            start_date='2017-04-01',
            end_date='2025-11-01',
            aggregation_days=agg_days
        )

        metrics['candle_type'] = candle_type
        metrics['aggregation_days'] = agg_days
        metrics['config_name'] = config_name

        results.append(metrics)

        print(f"  Return: {metrics['total_return']:.1f}% | "
              f"Ann: {metrics['annualized_return']:.1f}% | "
              f"MaxDD: {metrics['max_drawdown']:.1f}% | "
              f"Sharpe: {metrics['sharpe_ratio']:.2f} | "
              f"Trades: {metrics['total_trades']}")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Sort by Sharpe ratio (risk-adjusted performance)
    results_df = results_df.sort_values('sharpe_ratio', ascending=False)

    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY - Sorted by Sharpe Ratio")
    print("=" * 80)

    print(f"\n{'Config':<18} {'Return':>10} {'Annual':>10} {'MaxDD':>10} {'Sharpe':>8} {'WinRate':>8} {'PF':>8} {'Trades':>8}")
    print("-" * 90)

    for _, row in results_df.iterrows():
        print(f"{row['config_name']:<18} "
              f"{row['total_return']:>9.1f}% "
              f"{row['annualized_return']:>9.1f}% "
              f"{row['max_drawdown']:>9.1f}% "
              f"{row['sharpe_ratio']:>8.2f} "
              f"{row['win_rate']:>7.1f}% "
              f"{row['profit_factor']:>8.2f} "
              f"{row['total_trades']:>8}")

    # Identify winner
    print("\n" + "=" * 80)
    print("TOP 3 CONFIGURATIONS (by Sharpe Ratio)")
    print("=" * 80)

    top3 = results_df.head(3)
    for rank, (_, row) in enumerate(top3.iterrows(), 1):
        print(f"\n#{rank}: {row['config_name']}")
        print(f"    Total Return:      {row['total_return']:.2f}%")
        print(f"    Annualized Return: {row['annualized_return']:.2f}%")
        print(f"    Max Drawdown:      {row['max_drawdown']:.2f}%")
        print(f"    Sharpe Ratio:      {row['sharpe_ratio']:.3f}")
        print(f"    Win Rate:          {row['win_rate']:.2f}%")
        print(f"    Profit Factor:     {row['profit_factor']:.2f}")

    # Compare bar types
    print("\n" + "=" * 80)
    print("ANALYSIS BY BAR TYPE")
    print("=" * 80)

    for candle_type in ['regular', 'heiken_ashi', 'linreg']:
        type_data = results_df[results_df['candle_type'] == candle_type]
        if len(type_data) > 0:
            best = type_data.iloc[0]
            print(f"\n{candle_type.upper()}:")
            print(f"  Best aggregation: {int(best['aggregation_days'])} day(s)")
            print(f"  Avg Sharpe: {type_data['sharpe_ratio'].mean():.3f}")
            print(f"  Avg Return: {type_data['total_return'].mean():.1f}%")

    # Save results
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results_path = os.path.join(output_dir, f'dual_momentum_bar_experiment_{timestamp}.csv')
    results_df.to_csv(results_path, index=False)
    print(f"\nResults saved to: {results_path}")

    return results_df


if __name__ == '__main__':
    results = run_experiment()
