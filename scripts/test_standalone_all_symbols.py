"""
Test Universal Dual Supertrend - STANDALONE Performance Analysis

NO buy-hold comparison (that's look-ahead bias!)
Focus on: Yearly returns, yearly drawdowns, overall strategy performance

Include ALL symbols - even those with negative overall returns.
This is the REAL test.
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

class UniversalDualSupertrend(bt.Strategy):
    """Universal dual Supertrend with optimal parameters"""
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
        self.yearly_values = {}  # Track portfolio value by year

    def next(self):
        # Track yearly portfolio values
        year = self.data.datetime.date(0).year
        value = self.broker.getvalue()
        if year not in self.yearly_values:
            self.yearly_values[year] = []
        self.yearly_values[year].append(value)

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

def run_strategy(df):
    """Run strategy and return detailed results"""
    try:
        cerebro = bt.Cerebro()
        cerebro.adddata(PandasData(dataname=df))
        cerebro.addstrategy(UniversalDualSupertrend)

        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn', timeframe=bt.TimeFrame.Years)

        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0)

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        strat = results[0]
        trade_analysis = strat.analyzers.trades.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        sharpe = strat.analyzers.sharpe.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        time_return = strat.analyzers.timereturn.get_analysis()

        num_trades = trade_analysis.get('total', {}).get('closed', 0)
        won = trade_analysis.get('won', {}).get('total', 0)

        # Extract yearly returns
        yearly_returns = {}
        for date, ret in time_return.items():
            year = date.year if hasattr(date, 'year') else date
            yearly_returns[year] = ret * 100

        # Calculate yearly drawdowns from yearly_values
        yearly_drawdowns = {}
        for year, values in strat.yearly_values.items():
            if len(values) > 0:
                peak = values[0]
                max_dd = 0
                for val in values:
                    if val > peak:
                        peak = val
                    dd = (peak - val) / peak * 100
                    if dd > max_dd:
                        max_dd = dd
                yearly_drawdowns[year] = max_dd

        return {
            'total_return': ((end_value - start_value) / start_value) * 100,
            'final_value': end_value,
            'max_dd': drawdown.get('max', {}).get('drawdown', 0),
            'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
            'trades': num_trades,
            'wins': won,
            'win_rate': (won / num_trades * 100) if num_trades > 0 else 0,
            'yearly_returns': yearly_returns,
            'yearly_drawdowns': yearly_drawdowns,
            'success': True,
        }
    except Exception as e:
        return {
            'total_return': 0,
            'final_value': 100000,
            'max_dd': 0,
            'sharpe': 0,
            'trades': 0,
            'wins': 0,
            'win_rate': 0,
            'yearly_returns': {},
            'yearly_drawdowns': {},
            'success': False,
            'error': str(e),
        }

def load_csv(csv_file):
    """Load CSV with proper date parsing"""
    try:
        df = pd.read_csv(csv_file)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')
        df = df.dropna(subset=['date'])
        df = df.sort_values('date')
        df = df.reset_index(drop=True)

        # Minimum 252 bars for meaningful backtest
        if len(df) < 252:
            return None

        return df
    except Exception as e:
        return None

def extract_symbol(filename):
    """Extract symbol from filename"""
    basename = os.path.basename(filename)
    return basename.split('_')[0]

# Find all symbol files
data_dir = 'data/raw/11_22_25_daily'
csv_files = glob.glob(f'{data_dir}/*_trades_*.csv')

print(f"Found {len(csv_files)} symbol files")
print(f"{'='*120}")
print(f"STANDALONE STRATEGY PERFORMANCE - ALL SYMBOLS")
print(f"{'='*120}")
print(f"Entry: ATR 10, Multiplier 2.0")
print(f"Exit:  ATR 20, Multiplier 5.0")
print(f"NO filtering - testing on ALL stocks (no look-ahead bias)")
print(f"{'='*120}\n")

results = []
failed_symbols = []
all_yearly_returns = defaultdict(list)
all_yearly_drawdowns = defaultdict(list)

for i, csv_file in enumerate(csv_files, 1):
    symbol = extract_symbol(csv_file)

    if i % 20 == 0 or i == 1:
        print(f"Processing {i}/{len(csv_files)}: {symbol}...")

    df = load_csv(csv_file)
    if df is None:
        failed_symbols.append({'symbol': symbol, 'reason': 'Invalid data or < 252 bars'})
        continue

    # Run strategy
    result = run_strategy(df)
    if not result['success']:
        failed_symbols.append({'symbol': symbol, 'reason': f'Strategy error: {result.get("error", "unknown")}'})
        continue

    # Collect yearly data
    for year, ret in result['yearly_returns'].items():
        all_yearly_returns[year].append(ret)
    for year, dd in result['yearly_drawdowns'].items():
        all_yearly_drawdowns[year].append(dd)

    results.append({
        'symbol': symbol,
        'total_return': result['total_return'],
        'final_value': result['final_value'],
        'max_dd': result['max_dd'],
        'sharpe': result['sharpe'],
        'trades': result['trades'],
        'win_rate': result['win_rate'],
        'yearly_returns': result['yearly_returns'],
        'yearly_drawdowns': result['yearly_drawdowns'],
    })

print(f"\n{'='*120}")
print(f"RESULTS - {len(results)} SYMBOLS TESTED")
print(f"{'='*120}\n")

if not results:
    print("No valid results!")
    sys.exit(1)

df_results = pd.DataFrame(results)

# Overall statistics
avg_return = df_results['total_return'].mean()
median_return = df_results['total_return'].median()
std_return = df_results['total_return'].std()
min_return = df_results['total_return'].min()
max_return = df_results['total_return'].max()

avg_dd = df_results['max_dd'].mean()
median_dd = df_results['max_dd'].median()
max_dd = df_results['max_dd'].max()

avg_sharpe = df_results['sharpe'].mean()
median_sharpe = df_results['sharpe'].median()

avg_trades = df_results['trades'].mean()
avg_win_rate = df_results['win_rate'].mean()

positive_returns = len(df_results[df_results['total_return'] > 0])
positive_pct = (positive_returns / len(df_results)) * 100

print(f"📊 OVERALL PERFORMANCE:")
print(f"   Total Return (Mean):     {avg_return:>8.1f}%")
print(f"   Total Return (Median):   {median_return:>8.1f}%")
print(f"   Total Return (Std Dev):  {std_return:>8.1f}%")
print(f"   Total Return (Min):      {min_return:>8.1f}% ({df_results.loc[df_results['total_return'].idxmin(), 'symbol']})")
print(f"   Total Return (Max):      {max_return:>8.1f}% ({df_results.loc[df_results['total_return'].idxmax(), 'symbol']})")
print(f"\n📉 DRAWDOWN STATISTICS:")
print(f"   Max Drawdown (Mean):     {avg_dd:>8.1f}%")
print(f"   Max Drawdown (Median):   {median_dd:>8.1f}%")
print(f"   Max Drawdown (Worst):    {max_dd:>8.1f}% ({df_results.loc[df_results['max_dd'].idxmax(), 'symbol']})")
print(f"\n📈 RISK-ADJUSTED RETURNS:")
print(f"   Sharpe Ratio (Mean):     {avg_sharpe:>8.2f}")
print(f"   Sharpe Ratio (Median):   {median_sharpe:>8.2f}")
print(f"\n📊 TRADING STATISTICS:")
print(f"   Avg Trades:              {avg_trades:>8.1f}")
print(f"   Avg Win Rate:            {avg_win_rate:>8.1f}%")
print(f"   Positive Returns:        {positive_returns}/{len(df_results)} ({positive_pct:.1f}%)")

# Percentile analysis
print(f"\n📉 RETURN PERCENTILES:")
for p in [10, 25, 50, 75, 90]:
    val = df_results['total_return'].quantile(p/100)
    print(f"   {p}th percentile: {val:>8.1f}%")

# Distribution analysis
print(f"\n📊 RETURN DISTRIBUTION:")
bins = [-float('inf'), 0, 100, 200, 500, 1000, float('inf')]
labels = ['<0% (Loss)', '0-100%', '100-200%', '200-500%', '500-1000%', '>1000%']
df_results['return_bin'] = pd.cut(df_results['total_return'], bins=bins, labels=labels)
distribution = df_results['return_bin'].value_counts().sort_index()
for bin_label, count in distribution.items():
    pct = (count / len(df_results)) * 100
    bar = '█' * int(pct / 2)
    print(f"   {bin_label:<15} {count:>4} ({pct:>5.1f}%) {bar}")

# Yearly analysis
print(f"\n{'='*120}")
print(f"YEARLY PERFORMANCE ANALYSIS")
print(f"{'='*120}\n")

years = sorted(all_yearly_returns.keys())
print(f"{'Year':<10} {'Avg Return':<15} {'Median Return':<15} {'Avg Drawdown':<15} {'Median DD':<15} {'Stocks':<10}")
print(f"{'-'*100}")
for year in years:
    returns = all_yearly_returns[year]
    drawdowns = all_yearly_drawdowns.get(year, [])

    avg_ret = np.mean(returns) if returns else 0
    med_ret = np.median(returns) if returns else 0
    avg_dd = np.mean(drawdowns) if drawdowns else 0
    med_dd = np.median(drawdowns) if drawdowns else 0

    print(f"{year:<10} {avg_ret:>13.1f}% {med_ret:>13.1f}% {avg_dd:>13.1f}% {med_dd:>13.1f}% {len(returns):<10}")

# Top 20 performers
print(f"\n🏆 TOP 20 PERFORMERS (Total Return):")
print(f"{'Symbol':<10} {'Total Return':<15} {'Max DD':<10} {'Sharpe':<10} {'Trades':<10} {'Win%':<10}")
print(f"{'-'*80}")
top20 = df_results.nlargest(20, 'total_return')
for _, row in top20.iterrows():
    print(f"{row['symbol']:<10} {row['total_return']:>13.1f}% {row['max_dd']:>8.1f}% "
          f"{row['sharpe']:>8.2f} {row['trades']:<10.0f} {row['win_rate']:<9.1f}%")

# Bottom 20 performers
print(f"\n❌ BOTTOM 20 PERFORMERS (Total Return):")
print(f"{'Symbol':<10} {'Total Return':<15} {'Max DD':<10} {'Sharpe':<10} {'Trades':<10} {'Win%':<10}")
print(f"{'-'*80}")
bottom20 = df_results.nsmallest(20, 'total_return')
for _, row in bottom20.iterrows():
    print(f"{row['symbol']:<10} {row['total_return']:>13.1f}% {row['max_dd']:>8.1f}% "
          f"{row['sharpe']:>8.2f} {row['trades']:<10.0f} {row['win_rate']:<9.1f}%")

# Failed symbols
if failed_symbols:
    print(f"\n⚠️  FAILED SYMBOLS ({len(failed_symbols)}):")
    for item in failed_symbols[:20]:
        print(f"   {item['symbol']}: {item['reason']}")
    if len(failed_symbols) > 20:
        print(f"   ... and {len(failed_symbols) - 20} more")

print(f"\n{'='*120}")
print(f"💡 STANDALONE STRATEGY ASSESSMENT:")
print(f"{'='*120}")

if median_return > 200:
    print(f"✅ EXCELLENT: {median_return:.1f}% median return across {len(results)} symbols")
elif median_return > 100:
    print(f"✓ GOOD: {median_return:.1f}% median return")
elif median_return > 50:
    print(f"⚠ ACCEPTABLE: {median_return:.1f}% median return")
elif median_return > 0:
    print(f"⚠ MARGINAL: {median_return:.1f}% median return")
else:
    print(f"❌ POOR: {median_return:.1f}% median return (negative!)")

print(f"\n   Positive return rate: {positive_pct:.1f}%")
print(f"   Median max drawdown: {median_dd:.1f}%")
print(f"   Average Sharpe ratio: {avg_sharpe:.2f}")
print(f"\n   This is the REAL performance - no look-ahead bias")
print(f"   Includes ALL symbols (winners AND losers)")

# Save results
output_file = 'data/results/standalone_all_symbols_results.csv'
df_results.to_csv(output_file, index=False)
print(f"\n📁 Detailed results saved to: {output_file}")

# Save yearly summary
yearly_summary = []
for year in years:
    returns = all_yearly_returns[year]
    drawdowns = all_yearly_drawdowns.get(year, [])
    yearly_summary.append({
        'year': year,
        'avg_return': np.mean(returns) if returns else 0,
        'median_return': np.median(returns) if returns else 0,
        'avg_drawdown': np.mean(drawdowns) if drawdowns else 0,
        'median_drawdown': np.median(drawdowns) if drawdowns else 0,
        'num_stocks': len(returns),
    })
df_yearly = pd.DataFrame(yearly_summary)
yearly_file = 'data/results/yearly_performance_summary.csv'
df_yearly.to_csv(yearly_file, index=False)
print(f"📁 Yearly summary saved to: {yearly_file}")
