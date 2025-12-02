"""
Dual Supertrend Strategy: Asymmetric Entry/Exit
- Entry: Tight bands (catch trends early)
- Exit: Wide bands (stay in longer, exit only on confirmed reversal)

Goal: Capture more of the trend by entering early and exiting late
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

class DualSupertrendStrategy(bt.Strategy):
    """
    Dual Supertrend with asymmetric entry/exit

    Entry: Use tight Supertrend to catch trends early
    Exit: Use wide Supertrend to stay in trend, exit only on confirmed reversal
    """
    params = (
        # Entry parameters (tight bands for early detection)
        ('entry_period', 10),
        ('entry_multiplier', 2.0),

        # Exit parameters (wide bands to stay in trend)
        ('exit_period', 30),
        ('exit_multiplier', 6.0),

        # Position sizing
        ('position_sizing', 'portfolio_pct'),

        ('log_trades', False),
    )

    def __init__(self):
        # Entry Supertrend (tight bands)
        self.entry_st = Supertrend(
            self.data,
            period=self.params.entry_period,
            multiplier=self.params.entry_multiplier
        )

        # Exit Supertrend (wide bands)
        self.exit_st = Supertrend(
            self.data,
            period=self.params.exit_period,
            multiplier=self.params.exit_multiplier
        )

        self.order = None
        self.entry_price = None
        self.trade_count = 0
        self.winning_trades = 0

    def _calculate_position_size(self):
        """Calculate position size"""
        cash = self.broker.get_cash()
        price = self.data.close[0]

        if self.params.position_sizing == 'portfolio_pct':
            position_value = cash * 0.95
            if price > 0:
                return int(position_value / price)
        return 0

    def next(self):
        if self.order:
            return

        if not self.position:
            # ENTRY LOGIC: Use tight Supertrend for early entry
            if self.entry_st.direction[0] == 1:
                size = self._calculate_position_size()
                if size > 0:
                    self.order = self.buy(size=size)
                    if self.params.log_trades:
                        self.log(f'BUY SIGNAL: Entry ST bullish')
        else:
            # EXIT LOGIC: Use wide Supertrend for confirmed reversal
            # Only exit when wide ST flips bearish (confirmed trend change)
            if len(self) > 1 and self.exit_st.direction[0] == -1 and self.exit_st.direction[-1] == 1:
                self.order = self.sell(size=self.position.size)
                if self.params.log_trades:
                    self.log(f'SELL SIGNAL: Exit ST reversal')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                if self.params.log_trades:
                    self.log(f'BUY EXECUTED: ${order.executed.price:.2f}')
            elif order.issell():
                self.entry_price = None
                if self.params.log_trades:
                    self.log(f'SELL EXECUTED: ${order.executed.price:.2f}')
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.trade_count += 1
        if trade.pnl > 0:
            self.winning_trades += 1

    def log(self, txt):
        print(f'{self.data.datetime.date(0)}: {txt}')

class BuyAndHold(bt.Strategy):
    def __init__(self):
        self.order = None
    def next(self):
        if not self.position:
            cash = self.broker.get_cash()
            size = int(cash / self.data.close[0])
            if size > 0:
                self.order = self.buy(size=size)

def run_buy_hold(df):
    """Run buy-and-hold"""
    cerebro = bt.Cerebro()
    cerebro.adddata(PandasData(dataname=df))
    cerebro.addstrategy(BuyAndHold)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    strat = results[0]
    drawdown = strat.analyzers.drawdown.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()

    return {
        'return': ((end_value - start_value) / start_value) * 100,
        'final_value': end_value,
        'max_dd': drawdown.get('max', {}).get('drawdown', 0),
        'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
    }

def run_dual_supertrend(df, entry_period, entry_mult, exit_period, exit_mult):
    """Run dual Supertrend strategy"""
    cerebro = bt.Cerebro()
    cerebro.adddata(PandasData(dataname=df))

    cerebro.addstrategy(
        DualSupertrendStrategy,
        entry_period=entry_period,
        entry_multiplier=entry_mult,
        exit_period=exit_period,
        exit_multiplier=exit_mult,
        position_sizing='portfolio_pct',
        log_trades=False
    )

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
    }

def test_symbol(symbol, csv_file):
    """Test dual Supertrend configurations"""
    print(f"\n{'='*100}")
    print(f"TESTING {symbol} - DUAL SUPERTREND (Asymmetric Entry/Exit)")
    print(f"{'='*100}")

    # Load data
    df = pd.read_csv(csv_file, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    print(f"Data: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Price: ${df.iloc[0]['close']:.2f} → ${df.iloc[-1]['close']:.2f}")

    # Run buy-and-hold
    print(f"\nRunning Buy-and-Hold...")
    bh_results = run_buy_hold(df)

    # Test different entry/exit combinations
    configs = [
        # (entry_period, entry_mult, exit_period, exit_mult, description)
        (10, 2.0, 30, 6.0, "Tight Entry / Wide Exit"),
        (10, 2.5, 30, 8.0, "Tight Entry / Very Wide Exit"),
        (10, 3.0, 30, 6.0, "Medium Entry / Wide Exit"),
        (14, 2.0, 30, 6.0, "Tight Entry (14) / Wide Exit"),
        (10, 2.0, 20, 5.0, "Tight Entry / Medium Exit"),
    ]

    results = []
    for entry_p, entry_m, exit_p, exit_m, desc in configs:
        print(f"  Testing: {desc}...", end='', flush=True)
        result = run_dual_supertrend(df, entry_p, entry_m, exit_p, exit_m)
        result['config'] = desc
        result['entry_p'] = entry_p
        result['entry_m'] = entry_m
        result['exit_p'] = exit_p
        result['exit_m'] = exit_m
        results.append(result)
        print(f" Done ({result['trades']} trades)")

    # Find best
    best = max(results, key=lambda x: x['return'])

    # Print results
    print(f"\n{'='*100}")
    print(f"RESULTS - {symbol}")
    print(f"{'='*100}")
    print(f"{'Strategy':<35} {'Return':<15} {'Final $':<15} {'MaxDD':<10} {'Sharpe':<10} {'Trades':<10}")
    print(f"{'-'*100}")
    print(f"{'Buy & Hold':<35} {bh_results['return']:>13.1f}% ${bh_results['final_value']:>12,.0f} "
          f"{bh_results['max_dd']:>8.1f}% {bh_results['sharpe']:>9.2f} {'1':<10}")

    for r in results:
        marker = " ⭐" if r == best else ""
        label = f"{r['config']} ({r['entry_p']}/{r['entry_m']}, {r['exit_p']}/{r['exit_m']})"
        print(f"{label:<35} {r['return']:>13.1f}% ${r['final_value']:>12,.0f} "
              f"{r['max_dd']:>8.1f}% {r['sharpe']:>9.2f} {r['trades']:<10}{marker}")

    print(f"{'-'*100}")

    # Best config details
    capture_pct = (best['return'] / bh_results['return'] * 100) if bh_results['return'] > 0 else 0
    dd_reduction = ((bh_results['max_dd'] - best['max_dd']) / bh_results['max_dd'] * 100) if bh_results['max_dd'] > 0 else 0

    print(f"\n🏆 BEST: {best['config']}")
    print(f"   Entry: ATR {best['entry_p']}, Mult {best['entry_m']} (catch trends early)")
    print(f"   Exit: ATR {best['exit_p']}, Mult {best['exit_m']} (stay in trend)")
    print(f"   Return Capture: {capture_pct:.1f}%")
    print(f"   DD Reduction: {dd_reduction:.1f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}% ({best['wins']}/{best['trades']})")
    print(f"   Sharpe vs B&H: {best['sharpe']:.2f} vs {bh_results['sharpe']:.2f}")

    return {
        'symbol': symbol,
        'bh_return': bh_results['return'],
        'st_return': best['return'],
        'capture_pct': capture_pct,
        'bh_dd': bh_results['max_dd'],
        'st_dd': best['max_dd'],
        'dd_reduction': dd_reduction,
        'st_trades': best['trades'],
        'config': best['config'],
    }

# Test symbols
symbols = {
    'NVDA': 'data/raw/NVDA_daily.csv',
    'AMD': 'data/raw/AMD_daily.csv',
    'TSLA': 'data/raw/TSLA_daily.csv',
    'AAPL': 'data/raw/AAPL_daily.csv',
}

if __name__ == '__main__':
    print("="*100)
    print("DUAL SUPERTREND STRATEGY - ASYMMETRIC ENTRY/EXIT")
    print("="*100)
    print("Concept:")
    print("  - Entry: Tight bands (early trend detection)")
    print("  - Exit: Wide bands (stay in trend, exit only on confirmed reversal)")
    print("  - Goal: Capture more of the trend by entering early and exiting late")
    print("="*100)

    all_results = []
    for symbol, csv_file in symbols.items():
        result = test_symbol(symbol, csv_file)
        all_results.append(result)

    # Summary
    print(f"\n\n{'='*100}")
    print("OVERALL SUMMARY - DUAL SUPERTREND")
    print(f"{'='*100}")
    print(f"{'Symbol':<10} {'B&H $':<15} {'ST $':<15} {'Capture':<10} {'DD Red':<10} {'Trades':<10} {'Config':<35}")
    print(f"{'-'*100}")

    for r in all_results:
        print(f"{r['symbol']:<10} ${r['bh_return']/100*100000:>12,.0f} ${r['st_return']/100*100000:>12,.0f} "
              f"{r['capture_pct']:>8.1f}% {r['dd_reduction']:>8.1f}% {r['st_trades']:<10} {r['config']:<35}")

    avg_capture = sum(r['capture_pct'] for r in all_results) / len(all_results)
    avg_dd_reduction = sum(r['dd_reduction'] for r in all_results) / len(all_results)

    print(f"{'-'*100}")
    print(f"{'AVERAGE':<10} {'':<15} {'':<15} {avg_capture:>8.1f}% {avg_dd_reduction:>8.1f}%")
    print(f"{'='*100}")

    print(f"\n💡 INSIGHT:")
    print(f"   Dual Supertrend allows early entry (tight bands) + late exit (wide bands)")
    print(f"   Average capture: {avg_capture:.1f}%")
    print(f"   Compare to single ST: ~31-43% depending on config")
