"""
Test Adaptive Linear Regression Strategy on Recent Data (2023-2025)

Focus on the problem years where Supertrend failed (0% median return).
Goal: Achieve >15% median return on 2023-2025.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import backtrader as bt
from agents.agent_2_strategy_core.adaptive_linreg_strategy import (
    AdaptiveLinRegStrategy,
    ConservativeLinRegStrategy,
    AggressiveLinRegStrategy
)
from agents.agent_2_strategy_core.supertrend_strategy import SupertrendStrategy
import glob
from collections import defaultdict
import random

class PandasData(bt.feeds.PandasData):
    params = (
        ('datetime', 'date'),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )

def run_strategy(df, strategy_class, **kwargs):
    """Run strategy and return results"""
    try:
        cerebro = bt.Cerebro()
        cerebro.adddata(PandasData(dataname=df))
        cerebro.addstrategy(strategy_class, **kwargs)

        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn', timeframe=bt.TimeFrame.Years)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)

        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0)

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        strat = results[0]
        time_return = strat.analyzers.timereturn.get_analysis()
        trade_analysis = strat.analyzers.trades.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        sharpe = strat.analyzers.sharpe.get_analysis()

        # Extract yearly returns
        yearly_returns = {}
        for date, ret in time_return.items():
            year = date.year if hasattr(date, 'year') else date
            yearly_returns[year] = ret * 100

        num_trades = trade_analysis.get('total', {}).get('closed', 0)
        won = trade_analysis.get('won', {}).get('total', 0)

        total_return = ((end_value - start_value) / start_value) * 100

        return {
            'total_return': total_return,
            'yearly_returns': yearly_returns,
            'max_dd': drawdown.get('max', {}).get('drawdown', 0),
            'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
            'trades': num_trades,
            'win_rate': (won / num_trades * 100) if num_trades > 0 else 0,
            'success': True,
        }
    except Exception as e:
        return {
            'total_return': 0,
            'yearly_returns': {},
            'max_dd': 0,
            'sharpe': 0,
            'trades': 0,
            'win_rate': 0,
            'success': False,
            'error': str(e),
        }

def load_csv(csv_file):
    """Load CSV"""
    try:
        df = pd.read_csv(csv_file)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')
        df = df.dropna(subset=['date'])
        df = df.sort_values('date')
        df = df.reset_index(drop=True)
        if len(df) < 252:
            return None
        return df
    except:
        return None

def extract_symbol(filename):
    basename = os.path.basename(filename)
    return basename.split('_')[0]

# Load sample of symbols
data_dir = 'data/raw/11_22_25_daily'
csv_files = glob.glob(f'{data_dir}/*_trades_*.csv')
random.seed(42)
sample_files = random.sample(csv_files, min(50, len(csv_files)))

print(f"Loading {len(sample_files)} symbols...")
all_data = {}
for csv_file in sample_files:
    symbol = extract_symbol(csv_file)
    df = load_csv(csv_file)
    if df is not None:
        all_data[symbol] = df

print(f"Loaded {len(all_data)} valid symbols\n")
print(f"{'='*100}")
print(f"ADAPTIVE LINEAR REGRESSION STRATEGY - RECENT PERFORMANCE TEST")
print(f"{'='*100}")
print(f"Testing 3 variants:")
print(f"  1. Standard:     Trades strong trends (full pos) + weak trends (half pos)")
print(f"  2. Conservative: Only strong trends with strict criteria")
print(f"  3. Aggressive:   More lenient, larger positions")
print(f"\nBaseline: Supertrend (10/2.0, 20/5.0) - showed 0% median 2024-2025")
print(f"Goal: >15% median on 2023-2025")
print(f"{'='*100}\n")

# Test all strategies
strategies = {
    'Adaptive LinReg (Standard)': (AdaptiveLinRegStrategy, {}),
    'Adaptive LinReg (Conservative)': (ConservativeLinRegStrategy, {}),
    'Adaptive LinReg (Aggressive)': (AggressiveLinRegStrategy, {}),
    'Supertrend Baseline': (SupertrendStrategy, {
        'atr_period': 10,
        'atr_multiplier': 2.0,
        'exit_atr_period': 20,
        'exit_atr_multiplier': 5.0,
        'position_sizing': 'portfolio_pct',
    }),
}

all_results = {}

for strategy_name, (strategy_class, kwargs) in strategies.items():
    print(f"\nTesting {strategy_name}...")

    yearly_returns_all = defaultdict(list)
    total_returns = []
    max_dds = []
    sharpes = []
    trade_counts = []
    win_rates = []

    for symbol, df in all_data.items():
        result = run_strategy(df, strategy_class, **kwargs)
        if result['success']:
            total_returns.append(result['total_return'])
            max_dds.append(result['max_dd'])
            sharpes.append(result['sharpe'])
            trade_counts.append(result['trades'])
            win_rates.append(result['win_rate'])

            for year, ret in result['yearly_returns'].items():
                yearly_returns_all[year].append(ret)

    # Calculate statistics
    median_total = np.median(total_returns) if total_returns else 0
    median_dd = np.median(max_dds) if max_dds else 0
    mean_sharpe = np.mean(sharpes) if sharpes else 0
    median_trades = np.median(trade_counts) if trade_counts else 0
    mean_win_rate = np.mean(win_rates) if win_rates else 0

    # Recent years (2023-2025)
    recent_medians = []
    for year in [2023, 2024, 2025]:
        if year in yearly_returns_all and len(yearly_returns_all[year]) > 0:
            recent_medians.append(np.median(yearly_returns_all[year]))

    avg_recent = np.mean(recent_medians) if recent_medians else 0

    # Store results
    all_results[strategy_name] = {
        'median_total': median_total,
        'median_dd': median_dd,
        'mean_sharpe': mean_sharpe,
        'median_trades': median_trades,
        'mean_win_rate': mean_win_rate,
        'avg_recent': avg_recent,
        'yearly_medians': {year: np.median(yearly_returns_all[year])
                          for year in sorted(yearly_returns_all.keys())
                          if len(yearly_returns_all[year]) > 0},
        'num_symbols': len(total_returns),
    }

    print(f"  Median Total Return: {median_total:.1f}%")
    print(f"  Recent 3yr Average:  {avg_recent:.1f}%")
    print(f"  Median Max DD:       {median_dd:.1f}%")
    print(f"  Mean Sharpe:         {mean_sharpe:.2f}")
    print(f"  Median Trades:       {median_trades:.0f}")
    print(f"  Mean Win Rate:       {mean_win_rate:.1f}%")

# Summary comparison
print(f"\n{'='*100}")
print(f"COMPARISON - RECENT PERFORMANCE (2023-2025)")
print(f"{'='*100}\n")

print(f"{'Strategy':<35} {'Avg Recent':<15} {'Total Return':<15} {'Max DD':<10} {'Sharpe':<10}")
print(f"{'-'*90}")
for name, res in all_results.items():
    marker = " ✓" if res['avg_recent'] > 15 else ""
    print(f"{name:<35} {res['avg_recent']:>13.1f}% {res['median_total']:>13.1f}% "
          f"{res['median_dd']:>8.1f}% {res['mean_sharpe']:>8.2f}{marker}")

# Find best
best_recent = max(all_results.items(), key=lambda x: x[1]['avg_recent'])
best_total = max(all_results.items(), key=lambda x: x[1]['median_total'])

print(f"\n🏆 BEST RECENT PERFORMANCE (2023-2025):")
print(f"   {best_recent[0]}: {best_recent[1]['avg_recent']:.1f}%")

print(f"\n🏆 BEST TOTAL RETURN:")
print(f"   {best_total[0]}: {best_total[1]['median_total']:.1f}%")

# Year by year for best
print(f"\n📅 BEST RECENT - YEAR BY YEAR:")
print(f"{'Year':<10} {best_recent[0]:<20} {'Supertrend Baseline':<20}")
print(f"{'-'*55}")
supertrend_yearly = all_results['Supertrend Baseline']['yearly_medians']
best_yearly = best_recent[1]['yearly_medians']

for year in sorted(best_yearly.keys()):
    best_val = best_yearly.get(year, 0)
    super_val = supertrend_yearly.get(year, 0)
    diff = best_val - super_val
    marker = " ✓" if diff > 0 else ""
    print(f"{year:<10} {best_val:>18.1f}% {super_val:>18.1f}% ({diff:+.1f}%){marker}")

# Assessment
print(f"\n{'='*100}")
print(f"💡 ASSESSMENT:")
print(f"{'='*100}")

if best_recent[1]['avg_recent'] > 20:
    print(f"✅ EXCELLENT: Adaptive LinReg achieves {best_recent[1]['avg_recent']:.1f}% on 2023-2025")
    print(f"   This is a MAJOR improvement over Supertrend (0% median)")
    print(f"   Strategy successfully adapts to recent market conditions")
elif best_recent[1]['avg_recent'] > 15:
    print(f"✓ GOOD: Adaptive LinReg achieves {best_recent[1]['avg_recent']:.1f}% on 2023-2025")
    print(f"   Meets the >15% goal, significant improvement over Supertrend")
elif best_recent[1]['avg_recent'] > 10:
    print(f"⚠ ACCEPTABLE: {best_recent[1]['avg_recent']:.1f}% is better than Supertrend but marginal")
    print(f"   May need further tuning or different approach")
else:
    print(f"❌ INSUFFICIENT: {best_recent[1]['avg_recent']:.1f}% is not much better than Supertrend")
    print(f"   Linear regression approach may not be the answer")

print(f"\nNext step: If successful, test on ALL 268 symbols for validation")
