"""
Comprehensive Grid Search - Entry and Exit Parameters

Optimize INDEPENDENTLY to find best combination.
Focus on recent performance (2023-2025) to address flat returns.

Test grid:
- Entry Period: 5, 7, 10, 12, 15
- Entry Multiplier: 1.5, 2.0, 2.5, 3.0
- Exit Period: 15, 20, 25, 30
- Exit Multiplier: 3.5, 4.0, 5.0, 6.0

Total: 5 × 4 × 4 × 4 = 320 combinations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import backtrader as bt
from agents.agent_2_strategy_core.supertrend import Supertrend
import glob
from collections import defaultdict
import itertools

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

class DualSupertrend(bt.Strategy):
    params = (
        ('entry_period', 10),
        ('entry_multiplier', 2.0),
        ('exit_period', 20),
        ('exit_multiplier', 5.0),
    )

    def __init__(self):
        self.entry_st = Supertrend(self.data, period=self.params.entry_period,
                                   multiplier=self.params.entry_multiplier)
        self.exit_st = Supertrend(self.data, period=self.params.exit_period,
                                  multiplier=self.params.exit_multiplier)
        self.order = None

    def next(self):
        if self.order:
            return
        if not self.position:
            if self.entry_st.direction[0] == 1:
                cash = self.broker.get_cash()
                size = int(cash * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            if len(self) > 1 and self.exit_st.direction[0] == -1 and self.exit_st.direction[-1] == 1:
                self.order = self.sell(size=self.position.size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None

def run_strategy(df, entry_period, entry_mult, exit_period, exit_mult):
    """Run strategy and return results"""
    try:
        cerebro = bt.Cerebro()
        cerebro.adddata(PandasData(dataname=df))
        cerebro.addstrategy(DualSupertrend,
                           entry_period=entry_period,
                           entry_multiplier=entry_mult,
                           exit_period=exit_period,
                           exit_multiplier=exit_mult)

        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn', timeframe=bt.TimeFrame.Years)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)

        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0)

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        strat = results[0]
        time_return = strat.analyzers.timereturn.get_analysis()
        sharpe = strat.analyzers.sharpe.get_analysis()

        # Extract yearly returns
        yearly_returns = {}
        for date, ret in time_return.items():
            year = date.year if hasattr(date, 'year') else date
            yearly_returns[year] = ret * 100

        total_return = ((end_value - start_value) / start_value) * 100
        sharpe_ratio = sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0

        return {
            'total_return': total_return,
            'sharpe': sharpe_ratio,
            'yearly_returns': yearly_returns,
            'success': True,
        }
    except Exception as e:
        return {
            'total_return': 0,
            'sharpe': 0,
            'yearly_returns': {},
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

# Grid search parameters
entry_periods = [5, 7, 10, 12, 15]
entry_mults = [1.5, 2.0, 2.5, 3.0]
exit_periods = [15, 20, 25, 30]
exit_mults = [3.5, 4.0, 5.0, 6.0]

# Load all data
data_dir = 'data/raw/11_22_25_daily'
csv_files = glob.glob(f'{data_dir}/*_trades_*.csv')

print(f"Loading {len(csv_files)} symbols...")
all_data = {}
for csv_file in csv_files:
    symbol = extract_symbol(csv_file)
    df = load_csv(csv_file)
    if df is not None:
        all_data[symbol] = df

print(f"Loaded {len(all_data)} valid symbols")
print(f"\n{'='*120}")
print(f"GRID SEARCH - ENTRY AND EXIT OPTIMIZATION")
print(f"{'='*120}")
print(f"Entry Periods: {entry_periods}")
print(f"Entry Multipliers: {entry_mults}")
print(f"Exit Periods: {exit_periods}")
print(f"Exit Multipliers: {exit_mults}")
total_combinations = len(entry_periods) * len(entry_mults) * len(exit_periods) * len(exit_mults)
print(f"Total Combinations: {total_combinations}")
print(f"{'='*120}\n")

# Run grid search
results = []
combination_num = 0

for entry_p in entry_periods:
    for entry_m in entry_mults:
        for exit_p in exit_periods:
            for exit_m in exit_mults:
                combination_num += 1

                if combination_num % 20 == 0 or combination_num == 1:
                    print(f"Testing {combination_num}/{total_combinations}: Entry ({entry_p}/{entry_m}) Exit ({exit_p}/{exit_m})")

                # Test on all symbols
                yearly_returns_all = defaultdict(list)
                total_returns = []
                sharpes = []

                for symbol, df in all_data.items():
                    result = run_strategy(df, entry_p, entry_m, exit_p, exit_m)
                    if result['success']:
                        total_returns.append(result['total_return'])
                        sharpes.append(result['sharpe'])
                        for year, ret in result['yearly_returns'].items():
                            yearly_returns_all[year].append(ret)

                if not total_returns:
                    continue

                # Calculate metrics
                median_total = np.median(total_returns)
                mean_sharpe = np.mean(sharpes)

                # Recent years performance (2023-2025)
                recent_median = []
                for year in [2023, 2024, 2025]:
                    if year in yearly_returns_all:
                        recent_median.append(np.median(yearly_returns_all[year]))
                avg_recent = np.mean(recent_median) if recent_median else 0

                # All years median
                all_years_median = {}
                for year in sorted(yearly_returns_all.keys()):
                    all_years_median[year] = np.median(yearly_returns_all[year])

                results.append({
                    'entry_period': entry_p,
                    'entry_mult': entry_m,
                    'exit_period': exit_p,
                    'exit_mult': exit_m,
                    'median_total_return': median_total,
                    'mean_sharpe': mean_sharpe,
                    'recent_3yr_median': avg_recent,
                    'yearly_medians': all_years_median,
                })

print(f"\n{'='*120}")
print(f"GRID SEARCH COMPLETE - {len(results)} VALID COMBINATIONS")
print(f"{'='*120}\n")

df_results = pd.DataFrame(results)

# Top 20 by total return
print(f"🏆 TOP 20 BY TOTAL RETURN (2016-2025):")
print(f"{'Entry':<12} {'Exit':<12} {'Median Total':<15} {'Sharpe':<10} {'Recent 3yr':<15}")
print(f"{'-'*80}")
top20_total = df_results.nlargest(20, 'median_total_return')
for _, row in top20_total.iterrows():
    entry_str = f"{int(row['entry_period'])}/{row['entry_mult']:.1f}"
    exit_str = f"{int(row['exit_period'])}/{row['exit_mult']:.1f}"
    print(f"{entry_str:<12} {exit_str:<12} {row['median_total_return']:>13.1f}% "
          f"{row['mean_sharpe']:>8.2f} {row['recent_3yr_median']:>13.1f}%")

# Top 20 by RECENT performance (2023-2025)
print(f"\n🔥 TOP 20 BY RECENT PERFORMANCE (2023-2025 Average):")
print(f"{'Entry':<12} {'Exit':<12} {'Recent 3yr':<15} {'Median Total':<15} {'Sharpe':<10}")
print(f"{'-'*80}")
top20_recent = df_results.nlargest(20, 'recent_3yr_median')
for _, row in top20_recent.iterrows():
    entry_str = f"{int(row['entry_period'])}/{row['entry_mult']:.1f}"
    exit_str = f"{int(row['exit_period'])}/{row['exit_mult']:.1f}"
    print(f"{entry_str:<12} {exit_str:<12} {row['recent_3yr_median']:>13.1f}% "
          f"{row['median_total_return']:>13.1f}% {row['mean_sharpe']:>8.2f}")

# Compare our current params
current = df_results[
    (df_results['entry_period'] == 10) &
    (df_results['entry_mult'] == 2.0) &
    (df_results['exit_period'] == 20) &
    (df_results['exit_mult'] == 5.0)
]

if not current.empty:
    current_row = current.iloc[0]
    print(f"\n📍 CURRENT PARAMETERS (10/2.0, 20/5.0):")
    print(f"   Median Total Return: {current_row['median_total_return']:.1f}%")
    print(f"   Mean Sharpe: {current_row['mean_sharpe']:.2f}")
    print(f"   Recent 3yr Average: {current_row['recent_3yr_median']:.1f}%")

    # Rank
    total_rank = (df_results['median_total_return'] > current_row['median_total_return']).sum() + 1
    recent_rank = (df_results['recent_3yr_median'] > current_row['recent_3yr_median']).sum() + 1
    print(f"   Rank (Total Return): {total_rank}/{len(df_results)}")
    print(f"   Rank (Recent 3yr): {recent_rank}/{len(df_results)}")

# Best overall
best_overall = df_results.nlargest(1, 'median_total_return').iloc[0]
print(f"\n🏆 BEST OVERALL (Total Return):")
print(f"   Entry: {int(best_overall['entry_period'])}/{best_overall['entry_mult']:.1f}")
print(f"   Exit: {int(best_overall['exit_period'])}/{best_overall['exit_mult']:.1f}")
print(f"   Median Total Return: {best_overall['median_total_return']:.1f}%")
print(f"   Recent 3yr: {best_overall['recent_3yr_median']:.1f}%")

# Best recent
best_recent = df_results.nlargest(1, 'recent_3yr_median').iloc[0]
print(f"\n🔥 BEST RECENT PERFORMANCE (2023-2025):")
print(f"   Entry: {int(best_recent['entry_period'])}/{best_recent['entry_mult']:.1f}")
print(f"   Exit: {int(best_recent['exit_period'])}/{best_recent['exit_mult']:.1f}")
print(f"   Median Total Return: {best_recent['median_total_return']:.1f}%")
print(f"   Recent 3yr: {best_recent['recent_3yr_median']:.1f}%")

# Year by year for best recent
print(f"\n📅 BEST RECENT CONFIG - YEAR BY YEAR:")
print(f"{'Year':<10} {'Median Return':<15}")
print(f"{'-'*30}")
for year in sorted(best_recent['yearly_medians'].keys()):
    print(f"{year:<10} {best_recent['yearly_medians'][year]:>13.1f}%")

# Save results
output_file = 'data/results/grid_search_results.csv'
df_results.to_csv(output_file, index=False)
print(f"\n📁 Full results saved to: {output_file}")

print(f"\n{'='*120}")
print(f"💡 CONCLUSION:")
print(f"{'='*120}")
if best_recent['recent_3yr_median'] > 10:
    print(f"✅ Found better parameters for recent performance!")
    print(f"   Current (10/2.0, 20/5.0): {current_row['recent_3yr_median']:.1f}% recent")
    print(f"   Best ({int(best_recent['entry_period'])}/{best_recent['entry_mult']:.1f}, "
          f"{int(best_recent['exit_period'])}/{best_recent['exit_mult']:.1f}): "
          f"{best_recent['recent_3yr_median']:.1f}% recent")
    improvement = best_recent['recent_3yr_median'] - current_row['recent_3yr_median']
    print(f"   Improvement: +{improvement:.1f}%")
elif best_recent['recent_3yr_median'] > 0:
    print(f"⚠️ Recent performance weak but positive")
    print(f"   Best recent: {best_recent['recent_3yr_median']:.1f}%")
else:
    print(f"❌ All parameters show poor recent performance")
    print(f"   Best recent: {best_recent['recent_3yr_median']:.1f}%")
    print(f"   Strategy may be broken in current market regime")
