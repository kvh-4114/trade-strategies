"""
FAST Grid Search - Focused on Recent Performance (2023-2025)

Sample 50 diverse symbols for speed
Test targeted parameter ranges
Find what works NOW (not 2016-2025)
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

        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0)

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        strat = results[0]
        time_return = strat.analyzers.timereturn.get_analysis()

        # Extract yearly returns
        yearly_returns = {}
        for date, ret in time_return.items():
            year = date.year if hasattr(date, 'year') else date
            yearly_returns[year] = ret * 100

        total_return = ((end_value - start_value) / start_value) * 100

        return {
            'total_return': total_return,
            'yearly_returns': yearly_returns,
            'success': True,
        }
    except Exception as e:
        return {
            'total_return': 0,
            'yearly_returns': {},
            'success': False,
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

# Focused grid - fewer combinations
entry_periods = [5, 7, 10, 12]
entry_mults = [1.5, 2.0, 2.5]
exit_periods = [15, 20, 25]
exit_mults = [4.0, 5.0, 6.0]

# Load sample of symbols
data_dir = 'data/raw/11_22_25_daily'
csv_files = glob.glob(f'{data_dir}/*_trades_*.csv')
random.seed(42)  # Reproducible sample
sample_files = random.sample(csv_files, min(50, len(csv_files)))

print(f"Loading {len(sample_files)} symbols (sample from {len(csv_files)})...")
all_data = {}
for csv_file in sample_files:
    symbol = extract_symbol(csv_file)
    df = load_csv(csv_file)
    if df is not None:
        all_data[symbol] = df

print(f"Loaded {len(all_data)} valid symbols")
print(f"\n{'='*100}")
print(f"FAST GRID SEARCH - FOCUSED ON RECENT PERFORMANCE")
print(f"{'='*100}")
print(f"Entry Periods: {entry_periods}")
print(f"Entry Multipliers: {entry_mults}")
print(f"Exit Periods: {exit_periods}")
print(f"Exit Multipliers: {exit_mults}")
total_combinations = len(entry_periods) * len(entry_mults) * len(exit_periods) * len(exit_mults)
print(f"Total Combinations: {total_combinations}")
print(f"Testing on {len(all_data)} symbols")
print(f"{'='*100}\n")

# Run grid search
results = []
combination_num = 0

for entry_p in entry_periods:
    for entry_m in entry_mults:
        for exit_p in exit_periods:
            for exit_m in exit_mults:
                combination_num += 1
                print(f"Testing {combination_num}/{total_combinations}: Entry ({entry_p}/{entry_m}) Exit ({exit_p}/{exit_m})", end='')

                # Test on all sample symbols
                yearly_returns_all = defaultdict(list)
                total_returns = []

                for symbol, df in all_data.items():
                    result = run_strategy(df, entry_p, entry_m, exit_p, exit_m)
                    if result['success']:
                        total_returns.append(result['total_return'])
                        for year, ret in result['yearly_returns'].items():
                            yearly_returns_all[year].append(ret)

                if not total_returns:
                    print(" - FAILED")
                    continue

                # Calculate metrics
                median_total = np.median(total_returns)

                # Recent years (2023-2025)
                recent_returns = []
                for year in [2023, 2024, 2025]:
                    if year in yearly_returns_all and len(yearly_returns_all[year]) > 0:
                        recent_returns.append(np.median(yearly_returns_all[year]))
                avg_recent = np.mean(recent_returns) if recent_returns else 0

                # All years
                all_years_median = {}
                for year in sorted(yearly_returns_all.keys()):
                    if len(yearly_returns_all[year]) > 0:
                        all_years_median[year] = np.median(yearly_returns_all[year])

                print(f" → Total: {median_total:.1f}%, Recent: {avg_recent:.1f}%")

                results.append({
                    'entry_period': entry_p,
                    'entry_mult': entry_m,
                    'exit_period': exit_p,
                    'exit_mult': exit_m,
                    'median_total_return': median_total,
                    'recent_3yr_median': avg_recent,
                    'yearly_medians': all_years_median,
                    'num_symbols': len(total_returns),
                })

print(f"\n{'='*100}")
print(f"RESULTS - {len(results)} VALID COMBINATIONS")
print(f"{'='*100}\n")

df_results = pd.DataFrame(results)

# Top 10 by recent performance
print(f"🔥 TOP 10 BY RECENT PERFORMANCE (2023-2025):")
print(f"{'Entry':<12} {'Exit':<12} {'Recent 3yr':<15} {'Total Return':<15} {'2023':<10} {'2024':<10} {'2025':<10}")
print(f"{'-'*100}")
top10_recent = df_results.nlargest(10, 'recent_3yr_median')
for _, row in top10_recent.iterrows():
    entry_str = f"{int(row['entry_period'])}/{row['entry_mult']:.1f}"
    exit_str = f"{int(row['exit_period'])}/{row['exit_mult']:.1f}"
    y2023 = row['yearly_medians'].get(2023, 0)
    y2024 = row['yearly_medians'].get(2024, 0)
    y2025 = row['yearly_medians'].get(2025, 0)
    print(f"{entry_str:<12} {exit_str:<12} {row['recent_3yr_median']:>13.1f}% "
          f"{row['median_total_return']:>13.1f}% {y2023:>8.1f}% {y2024:>8.1f}% {y2025:>8.1f}%")

# Top 10 by total return
print(f"\n🏆 TOP 10 BY TOTAL RETURN (All Years):")
print(f"{'Entry':<12} {'Exit':<12} {'Total Return':<15} {'Recent 3yr':<15}")
print(f"{'-'*60}")
top10_total = df_results.nlargest(10, 'median_total_return')
for _, row in top10_total.iterrows():
    entry_str = f"{int(row['entry_period'])}/{row['entry_mult']:.1f}"
    exit_str = f"{int(row['exit_period'])}/{row['exit_mult']:.1f}"
    print(f"{entry_str:<12} {exit_str:<12} {row['median_total_return']:>13.1f}% "
          f"{row['recent_3yr_median']:>13.1f}%")

# Current params
current = df_results[
    (df_results['entry_period'] == 10) &
    (df_results['entry_mult'] == 2.0) &
    (df_results['exit_period'] == 20) &
    (df_results['exit_mult'] == 5.0)
]

if not current.empty:
    current_row = current.iloc[0]
    print(f"\n📍 CURRENT PARAMETERS (10/2.0, 20/5.0):")
    print(f"   Total Return: {current_row['median_total_return']:.1f}%")
    print(f"   Recent 3yr: {current_row['recent_3yr_median']:.1f}%")
    print(f"   2023: {current_row['yearly_medians'].get(2023, 0):.1f}%")
    print(f"   2024: {current_row['yearly_medians'].get(2024, 0):.1f}%")
    print(f"   2025: {current_row['yearly_medians'].get(2025, 0):.1f}%")

    # Rank
    recent_rank = (df_results['recent_3yr_median'] > current_row['recent_3yr_median']).sum() + 1
    total_rank = (df_results['median_total_return'] > current_row['median_total_return']).sum() + 1
    print(f"   Rank (Recent): #{recent_rank}/{len(df_results)}")
    print(f"   Rank (Total): #{total_rank}/{len(df_results)}")

# Best recent
best_recent = df_results.nlargest(1, 'recent_3yr_median').iloc[0]
print(f"\n🔥 BEST FOR RECENT PERFORMANCE:")
print(f"   Entry: {int(best_recent['entry_period'])}/{best_recent['entry_mult']:.1f}")
print(f"   Exit: {int(best_recent['exit_period'])}/{best_recent['exit_mult']:.1f}")
print(f"   Total Return: {best_recent['median_total_return']:.1f}%")
print(f"   Recent 3yr: {best_recent['recent_3yr_median']:.1f}%")
print(f"\n   Year by Year:")
for year in sorted(best_recent['yearly_medians'].keys()):
    print(f"   {year}: {best_recent['yearly_medians'][year]:>6.1f}%")

# Best total
best_total = df_results.nlargest(1, 'median_total_return').iloc[0]
if (best_total['entry_period'] != best_recent['entry_period'] or
    best_total['exit_period'] != best_recent['exit_period']):
    print(f"\n🏆 BEST FOR TOTAL RETURN (Different from Recent):")
    print(f"   Entry: {int(best_total['entry_period'])}/{best_total['entry_mult']:.1f}")
    print(f"   Exit: {int(best_total['exit_period'])}/{best_total['exit_mult']:.1f}")
    print(f"   Total Return: {best_total['median_total_return']:.1f}%")
    print(f"   Recent 3yr: {best_total['recent_3yr_median']:.1f}%")

# Save results
output_file = 'data/results/fast_grid_search_results.csv'
df_results.to_csv(output_file, index=False)
print(f"\n📁 Results saved to: {output_file}")

print(f"\n{'='*100}")
print(f"💡 CONCLUSION:")
print(f"{'='*100}")

if best_recent['recent_3yr_median'] > 15:
    print(f"✅ Found parameters with solid recent performance")
    print(f"   Best recent 3yr: {best_recent['recent_3yr_median']:.1f}%")
    if not current.empty:
        improvement = best_recent['recent_3yr_median'] - current_row['recent_3yr_median']
        print(f"   Current: {current_row['recent_3yr_median']:.1f}%")
        print(f"   Improvement: {improvement:+.1f}%")
elif best_recent['recent_3yr_median'] > 5:
    print(f"⚠️ Recent performance weak but positive")
    print(f"   Best recent 3yr: {best_recent['recent_3yr_median']:.1f}%")
else:
    print(f"❌ All parameters show poor recent performance")
    print(f"   Best recent 3yr: {best_recent['recent_3yr_median']:.1f}%")
    print(f"   Strategy appears broken for 2023-2025 market regime")
