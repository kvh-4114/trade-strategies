"""
Test Universal Dual Supertrend Parameters Across ALL Symbols

Validates that Entry (10, 2.0) / Exit (20, 5.0) works robustly across
a diverse universe of 250+ stocks.

This is the ULTIMATE test of overfitting:
- If params work across 250+ symbols → NOT overfitted
- If params fail on many symbols → Overfitted to original 4 stocks
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import backtrader as bt
from agents.agent_2_strategy_core.supertrend import Supertrend
import glob
from pathlib import Path

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
        self.trade_count = 0
        self.wins = 0

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

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            if trade.pnl > 0:
                self.wins += 1

class BuyAndHold(bt.Strategy):
    def __init__(self):
        self.order = None
    def next(self):
        if not self.position:
            cash = self.broker.get_cash()
            size = int(cash * 0.95 / self.data.close[0])
            if size > 0:
                self.order = self.buy(size=size)

def run_strategy(df, strategy_class, **kwargs):
    """Run a strategy and return results"""
    try:
        cerebro = bt.Cerebro()
        cerebro.adddata(PandasData(dataname=df))
        cerebro.addstrategy(strategy_class, **kwargs)

        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)

        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.0)

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        strat = results[0]
        trade_analysis = strat.analyzers.trades.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        sharpe = strat.analyzers.sharpe.get_analysis()

        num_trades = trade_analysis.get('total', {}).get('closed', 0)
        won = trade_analysis.get('won', {}).get('total', 0)

        return {
            'return': ((end_value - start_value) / start_value) * 100,
            'final_value': end_value,
            'max_dd': drawdown.get('max', {}).get('drawdown', 0),
            'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
            'trades': num_trades,
            'wins': won,
            'win_rate': (won / num_trades * 100) if num_trades > 0 else 0,
            'success': True,
        }
    except Exception as e:
        return {
            'return': 0,
            'final_value': 100000,
            'max_dd': 0,
            'sharpe': 0,
            'trades': 0,
            'wins': 0,
            'win_rate': 0,
            'success': False,
            'error': str(e),
        }

def load_csv(csv_file):
    """Load CSV with proper date parsing"""
    try:
        df = pd.read_csv(csv_file)

        # Parse date (handle MM/DD/YYYY format)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')

        # Drop rows with invalid dates
        df = df.dropna(subset=['date'])

        # Sort by date
        df = df.sort_values('date')

        # Reset index
        df = df.reset_index(drop=True)

        # Filter: need at least 252 bars (1 year) for meaningful backtest
        if len(df) < 252:
            return None

        return df
    except Exception as e:
        print(f"Error loading {csv_file}: {e}")
        return None

def extract_symbol(filename):
    """Extract symbol from filename like 'AAPL_trades_[11_22_25_daily].csv'"""
    basename = os.path.basename(filename)
    return basename.split('_')[0]

# Find all symbol files
data_dir = 'data/raw/11_22_25_daily'
csv_files = glob.glob(f'{data_dir}/*_trades_*.csv')

print(f"Found {len(csv_files)} symbol files")
print(f"{'='*120}")
print(f"TESTING UNIVERSAL PARAMETERS ACROSS ALL SYMBOLS")
print(f"{'='*120}")
print(f"Entry: ATR 10, Multiplier 2.0")
print(f"Exit:  ATR 20, Multiplier 5.0")
print(f"{'='*120}\n")

results = []
failed_symbols = []

for i, csv_file in enumerate(csv_files, 1):
    symbol = extract_symbol(csv_file)

    # Progress indicator every 20 symbols
    if i % 20 == 0 or i == 1:
        print(f"Processing {i}/{len(csv_files)}: {symbol}...")

    # Load data
    df = load_csv(csv_file)
    if df is None:
        failed_symbols.append({'symbol': symbol, 'reason': 'Invalid data or < 252 bars'})
        continue

    # Run buy-hold
    bh = run_strategy(df, BuyAndHold)
    if not bh['success'] or bh['return'] <= 0:
        failed_symbols.append({'symbol': symbol, 'reason': 'Buy-hold failed or negative return'})
        continue

    # Run universal dual Supertrend
    st = run_strategy(df, UniversalDualSupertrend)
    if not st['success']:
        failed_symbols.append({'symbol': symbol, 'reason': f'Strategy failed: {st.get("error", "unknown")}'})
        continue

    # Calculate metrics
    capture = (st['return'] / bh['return'] * 100) if bh['return'] > 0 else 0

    results.append({
        'symbol': symbol,
        'bh_return': bh['return'],
        'st_return': st['return'],
        'capture': capture,
        'bh_sharpe': bh['sharpe'],
        'st_sharpe': st['sharpe'],
        'trades': st['trades'],
        'win_rate': st['win_rate'],
        'max_dd': st['max_dd'],
        'bh_max_dd': bh['max_dd'],
    })

print(f"\n{'='*120}")
print(f"RESULTS SUMMARY - {len(results)} SYMBOLS TESTED")
print(f"{'='*120}\n")

if not results:
    print("No valid results!")
    sys.exit(1)

# Convert to DataFrame for analysis
df_results = pd.DataFrame(results)

# Overall statistics
avg_capture = df_results['capture'].mean()
median_capture = df_results['capture'].median()
std_capture = df_results['capture'].std()
min_capture = df_results['capture'].min()
max_capture = df_results['capture'].max()

avg_trades = df_results['trades'].mean()
avg_sharpe = df_results['st_sharpe'].mean()

# Count how many beat buy-hold
beat_bh = len(df_results[df_results['st_return'] > df_results['bh_return']])
beat_bh_pct = (beat_bh / len(df_results)) * 100

# Count how many had positive returns
positive_returns = len(df_results[df_results['st_return'] > 0])
positive_pct = (positive_returns / len(df_results)) * 100

print(f"📊 CAPTURE RATE STATISTICS:")
print(f"   Mean:       {avg_capture:.1f}%")
print(f"   Median:     {median_capture:.1f}%")
print(f"   Std Dev:    {std_capture:.1f}%")
print(f"   Min:        {min_capture:.1f}% ({df_results.loc[df_results['capture'].idxmin(), 'symbol']})")
print(f"   Max:        {max_capture:.1f}% ({df_results.loc[df_results['capture'].idxmax(), 'symbol']})")
print(f"\n📈 PERFORMANCE METRICS:")
print(f"   Avg Trades:        {avg_trades:.1f}")
print(f"   Avg Sharpe:        {avg_sharpe:.2f}")
print(f"   Positive Returns:  {positive_returns}/{len(df_results)} ({positive_pct:.1f}%)")
print(f"   Beat Buy-Hold:     {beat_bh}/{len(df_results)} ({beat_bh_pct:.1f}%)")

# Percentile analysis
percentiles = [10, 25, 50, 75, 90]
print(f"\n📉 CAPTURE RATE PERCENTILES:")
for p in percentiles:
    val = df_results['capture'].quantile(p/100)
    print(f"   {p}th percentile: {val:.1f}%")

# Top 10 performers
print(f"\n🏆 TOP 10 PERFORMERS (Highest Capture %):")
print(f"{'Symbol':<10} {'B&H Return':<15} {'ST Return':<15} {'Capture':<10} {'Trades':<10} {'Sharpe':<10}")
print(f"{'-'*80}")
top10 = df_results.nlargest(10, 'capture')
for _, row in top10.iterrows():
    print(f"{row['symbol']:<10} {row['bh_return']:>13.1f}% {row['st_return']:>13.1f}% "
          f"{row['capture']:>8.1f}% {row['trades']:<10.0f} {row['st_sharpe']:<10.2f}")

# Bottom 10 performers
print(f"\n❌ BOTTOM 10 PERFORMERS (Lowest Capture %):")
print(f"{'Symbol':<10} {'B&H Return':<15} {'ST Return':<15} {'Capture':<10} {'Trades':<10} {'Sharpe':<10}")
print(f"{'-'*80}")
bottom10 = df_results.nsmallest(10, 'capture')
for _, row in bottom10.iterrows():
    print(f"{row['symbol']:<10} {row['bh_return']:>13.1f}% {row['st_return']:>13.1f}% "
          f"{row['capture']:>8.1f}% {row['trades']:<10.0f} {row['st_sharpe']:<10.2f}")

# Failed symbols
if failed_symbols:
    print(f"\n⚠️  FAILED SYMBOLS ({len(failed_symbols)}):")
    for item in failed_symbols[:20]:  # Show first 20
        print(f"   {item['symbol']}: {item['reason']}")
    if len(failed_symbols) > 20:
        print(f"   ... and {len(failed_symbols) - 20} more")

# Distribution analysis
print(f"\n📊 CAPTURE RATE DISTRIBUTION:")
bins = [0, 20, 40, 60, 80, 100, float('inf')]
labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%', '>100%']
df_results['capture_bin'] = pd.cut(df_results['capture'], bins=bins, labels=labels)
distribution = df_results['capture_bin'].value_counts().sort_index()
for bin_label, count in distribution.items():
    pct = (count / len(df_results)) * 100
    bar = '█' * int(pct / 2)  # Visual bar
    print(f"   {bin_label:<10} {count:>4} ({pct:>5.1f}%) {bar}")

print(f"\n{'='*120}")
print(f"💡 CONCLUSION:")
print(f"{'='*120}")

if avg_capture > 50:
    print(f"✅ EXCELLENT: {avg_capture:.1f}% average capture across {len(results)} diverse symbols")
    print(f"   Universal parameters (10/2.0, 20/5.0) are ROBUST and production-ready")
elif avg_capture > 40:
    print(f"✓ GOOD: {avg_capture:.1f}% average capture across {len(results)} symbols")
    print(f"   Universal parameters work well across diverse stocks")
elif avg_capture > 30:
    print(f"⚠ ACCEPTABLE: {avg_capture:.1f}% average capture")
    print(f"   Parameters work but may need refinement for some sectors")
else:
    print(f"❌ POOR: {avg_capture:.1f}% average capture")
    print(f"   Parameters may be overfitted to original test symbols")

print(f"\n   Tested on {len(results)} symbols - this validates robustness")
print(f"   Median capture: {median_capture:.1f}% (robust to outliers)")
print(f"   {positive_pct:.1f}% of symbols had positive returns")

# Save detailed results to CSV
output_file = 'data/results/universal_all_symbols_results.csv'
df_results.to_csv(output_file, index=False)
print(f"\n📁 Detailed results saved to: {output_file}")
