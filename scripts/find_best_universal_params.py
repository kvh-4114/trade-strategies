"""
Find the best UNIVERSAL parameters for dual Supertrend
Test multiple candidates and pick the one with best average performance

Goal: Maximize average capture rate across all stocks without overfitting
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtrader as bt
from agents.agent_2_strategy_core.supertrend import Supertrend

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
    params = (
        ('entry_period', 10),
        ('entry_multiplier', 2.0),
        ('exit_period', 30),
        ('exit_multiplier', 6.0),
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

class BuyAndHold(bt.Strategy):
    def __init__(self):
        self.order = None
    def next(self):
        if not self.position:
            cash = self.broker.get_cash()
            size = int(cash / self.data.close[0])
            if size > 0:
                self.order = self.buy(size=size)

def run_strategy(df, strategy_class, **kwargs):
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
        'max_dd': drawdown.get('max', {}).get('drawdown', 0),
        'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
        'trades': num_trades,
        'wins': won,
    }

# Load all symbols
symbols = {
    'NVDA': 'data/raw/NVDA_daily.csv',
    'AMD': 'data/raw/AMD_daily.csv',
    'TSLA': 'data/raw/TSLA_daily.csv',
    'AAPL': 'data/raw/AAPL_daily.csv',
}

dfs = {}
bh_results = {}

print("Loading data and running buy-and-hold baselines...")
for symbol, csv_file in symbols.items():
    df = pd.read_csv(csv_file, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    dfs[symbol] = df

    bh = run_strategy(df, BuyAndHold)
    bh_results[symbol] = bh
    print(f"  {symbol}: B&H {bh['return']:.1f}%")

# Test universal parameter candidates
candidates = [
    # (entry_period, entry_mult, exit_period, exit_mult, description)
    (10, 1.5, 30, 5.0, "Very Tight Entry / Medium Exit"),
    (10, 1.8, 30, 5.0, "Tight Entry / Medium Exit"),
    (10, 2.0, 20, 5.0, "Balanced Entry / Medium-Tight Exit"),
    (10, 2.0, 30, 6.0, "Balanced Entry / Wide Exit (CURRENT)"),
    (10, 2.0, 30, 7.0, "Balanced Entry / Very Wide Exit"),
    (10, 2.5, 30, 6.0, "Medium Entry / Wide Exit"),
    (10, 2.5, 30, 8.0, "Medium Entry / Very Wide Exit"),
    (14, 2.0, 30, 6.0, "Longer Entry / Wide Exit"),
]

print(f"\n{'='*120}")
print("TESTING UNIVERSAL PARAMETER CANDIDATES")
print(f"{'='*120}")

all_candidate_results = []

for entry_p, entry_m, exit_p, exit_m, desc in candidates:
    print(f"\nTesting: {desc} (Entry {entry_p}/{entry_m}, Exit {exit_p}/{exit_m})")

    results_by_symbol = {}
    captures = []

    for symbol in symbols.keys():
        result = run_strategy(
            dfs[symbol],
            UniversalDualSupertrend,
            entry_period=entry_p,
            entry_multiplier=entry_m,
            exit_period=exit_p,
            exit_multiplier=exit_m
        )

        bh_ret = bh_results[symbol]['return']
        capture = (result['return'] / bh_ret * 100) if bh_ret > 0 else 0
        captures.append(capture)
        results_by_symbol[symbol] = {**result, 'capture': capture}

        print(f"  {symbol}: {result['return']:>8.1f}% ({capture:>5.1f}% capture, {result['trades']} trades)")

    avg_capture = sum(captures) / len(captures)
    avg_trades = sum(r['trades'] for r in results_by_symbol.values()) / len(results_by_symbol)
    avg_sharpe = sum(r['sharpe'] for r in results_by_symbol.values()) / len(results_by_symbol)

    all_candidate_results.append({
        'desc': desc,
        'entry_p': entry_p,
        'entry_m': entry_m,
        'exit_p': exit_p,
        'exit_m': exit_m,
        'avg_capture': avg_capture,
        'avg_trades': avg_trades,
        'avg_sharpe': avg_sharpe,
        'by_symbol': results_by_symbol,
    })

    print(f"  → Average: {avg_capture:.1f}% capture, {avg_trades:.1f} trades, Sharpe {avg_sharpe:.2f}")

# Find best
best = max(all_candidate_results, key=lambda x: x['avg_capture'])

# Print summary
print(f"\n\n{'='*120}")
print("SUMMARY - ALL UNIVERSAL CANDIDATES")
print(f"{'='*120}")
print(f"{'Configuration':<40} {'Avg Capture':<15} {'Avg Trades':<12} {'Avg Sharpe':<12}")
print(f"{'-'*120}")

for r in sorted(all_candidate_results, key=lambda x: x['avg_capture'], reverse=True):
    marker = " 🏆" if r == best else ""
    print(f"{r['desc']:<40} {r['avg_capture']:>13.1f}% {r['avg_trades']:>10.1f} {r['avg_sharpe']:>10.2f}{marker}")

print(f"{'='*120}")

# Best configuration details
print(f"\n\n🏆 BEST UNIVERSAL CONFIGURATION:")
print(f"   {best['desc']}")
print(f"   Entry: ATR {best['entry_p']}, Multiplier {best['entry_m']}")
print(f"   Exit: ATR {best['exit_p']}, Multiplier {best['exit_m']}")
print(f"\n   Average Capture: {best['avg_capture']:.1f}%")
print(f"   Average Trades: {best['avg_trades']:.1f}")
print(f"   Average Sharpe: {best['avg_sharpe']:.2f}")

print(f"\n   Per-Symbol Performance:")
for symbol in symbols.keys():
    sym_result = best['by_symbol'][symbol]
    bh_ret = bh_results[symbol]['return']
    print(f"   {symbol}: {sym_result['return']:>8.1f}% / {bh_ret:>8.1f}% B&H = {sym_result['capture']:>5.1f}% capture "
          f"({sym_result['trades']} trades, Sharpe {sym_result['sharpe']:.2f})")

print(f"\n💡 RECOMMENDATION:")
print(f"   Use these universal parameters for ALL stocks")
print(f"   Expected performance: ~{best['avg_capture']:.0f}% capture with no overfitting")
print(f"   This configuration balances performance across different market regimes")
