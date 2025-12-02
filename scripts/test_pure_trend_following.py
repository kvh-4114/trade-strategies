"""
Pure Trend-Following Test: NO stop losses, NO profit targets
Only exit on Supertrend reversal signal

Analyze:
- Total returns vs buy-and-hold
- Yearly returns breakdown
- Drawdown analysis
- Multiple band widths to find optimal
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import backtrader as bt
from agents.agent_2_strategy_core.supertrend_strategy import SupertrendStrategy

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
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='returns', timeframe=bt.TimeFrame.Years)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    strat = results[0]
    drawdown = strat.analyzers.drawdown.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    yearly_returns = strat.analyzers.returns.get_analysis()

    return {
        'return': ((end_value - start_value) / start_value) * 100,
        'final_value': end_value,
        'max_dd': drawdown.get('max', {}).get('drawdown', 0),
        'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
        'yearly_returns': yearly_returns,
    }

def run_supertrend(df, atr_period, atr_mult):
    """Run pure trend-following Supertrend"""
    cerebro = bt.Cerebro()
    cerebro.adddata(PandasData(dataname=df))

    cerebro.addstrategy(
        SupertrendStrategy,
        atr_period=atr_period,
        atr_multiplier=atr_mult,
        position_sizing='portfolio_pct',
        stop_loss_type='none',      # ✅ NO STOP LOSS
        stop_loss_value=None,
        profit_target=None,          # ✅ NO PROFIT TARGET
        log_trades=False
    )

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='returns', timeframe=bt.TimeFrame.Years)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    strat = results[0]
    trade_analysis = strat.analyzers.trades.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    yearly_returns = strat.analyzers.returns.get_analysis()

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
        'yearly_returns': yearly_returns,
    }

def print_yearly_comparison(symbol, bh_yearly, st_yearly):
    """Print yearly returns side-by-side"""
    print(f"\n{'='*80}")
    print(f"{symbol} - YEARLY RETURNS COMPARISON")
    print(f"{'='*80}")
    print(f"{'Year':<10} {'Buy & Hold':<15} {'Supertrend':<15} {'Difference':<15}")
    print(f"{'-'*80}")

    all_years = sorted(set(list(bh_yearly.keys()) + list(st_yearly.keys())))

    for year in all_years:
        year_str = str(year)[:4] if year else 'N/A'
        bh_ret = bh_yearly.get(year, 0) * 100
        st_ret = st_yearly.get(year, 0) * 100
        diff = st_ret - bh_ret

        print(f"{year_str:<10} {bh_ret:>13.1f}% {st_ret:>13.1f}% {diff:>13.1f}%")

def test_symbol(symbol, csv_file):
    """Test a symbol with multiple band widths"""
    print(f"\n{'='*100}")
    print(f"TESTING {symbol} - PURE TREND FOLLOWING (No SL, No PT)")
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

    # Test multiple ATR multipliers
    multipliers = [4.0, 6.0, 8.0, 10.0, 12.0]
    atr_period = 30  # Longer period for smoother trends

    print(f"\nTesting ATR multipliers: {multipliers}")
    print(f"ATR Period: {atr_period}")

    st_results = []
    for mult in multipliers:
        print(f"  Testing Mult {mult}...", end='', flush=True)
        result = run_supertrend(df, atr_period, mult)
        result['multiplier'] = mult
        st_results.append(result)
        print(f" Done ({result['trades']} trades)")

    # Find best configuration
    best = max(st_results, key=lambda x: x['return'])

    # Print results table
    print(f"\n{'='*100}")
    print(f"RESULTS SUMMARY - {symbol}")
    print(f"{'='*100}")
    print(f"{'Strategy':<25} {'Return':<15} {'Final $':<15} {'MaxDD':<10} {'Sharpe':<10} {'Trades':<10}")
    print(f"{'-'*100}")
    print(f"{'Buy & Hold':<25} {bh_results['return']:>13.1f}% ${bh_results['final_value']:>12,.0f} "
          f"{bh_results['max_dd']:>8.1f}% {bh_results['sharpe']:>9.2f} {'1':<10}")

    for r in st_results:
        label = f"Supertrend (Mult {r['multiplier']})"
        marker = " ⭐" if r == best else ""
        print(f"{label:<25} {r['return']:>13.1f}% ${r['final_value']:>12,.0f} "
              f"{r['max_dd']:>8.1f}% {r['sharpe']:>9.2f} {r['trades']:<10}{marker}")

    print(f"{'-'*100}")

    # Best configuration details
    capture_pct = (best['return'] / bh_results['return'] * 100) if bh_results['return'] > 0 else 0
    dd_reduction = ((bh_results['max_dd'] - best['max_dd']) / bh_results['max_dd'] * 100) if bh_results['max_dd'] > 0 else 0

    print(f"\n🏆 BEST CONFIGURATION: ATR {atr_period}, Multiplier {best['multiplier']}")
    print(f"   Return Capture: {capture_pct:.1f}%")
    print(f"   DD Reduction: {dd_reduction:.1f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}% ({best['wins']}/{best['trades']})")
    print(f"   Sharpe vs B&H: {best['sharpe']:.2f} vs {bh_results['sharpe']:.2f}")

    # Print yearly comparison for best config
    print_yearly_comparison(symbol, bh_results['yearly_returns'], best['yearly_returns'])

    return {
        'symbol': symbol,
        'bh_return': bh_results['return'],
        'bh_final': bh_results['final_value'],
        'bh_dd': bh_results['max_dd'],
        'bh_sharpe': bh_results['sharpe'],
        'st_return': best['return'],
        'st_final': best['final_value'],
        'st_dd': best['max_dd'],
        'st_sharpe': best['sharpe'],
        'st_trades': best['trades'],
        'st_wins': best['wins'],
        'st_multiplier': best['multiplier'],
        'capture_pct': capture_pct,
        'dd_reduction': dd_reduction,
    }

# Symbol configurations
symbols = {
    'NVDA': 'data/raw/NVDA_daily.csv',
    'AMD': 'data/raw/AMD_daily.csv',
    'TSLA': 'data/raw/TSLA_daily.csv',
    'AAPL': 'data/raw/AAPL_daily.csv',
}

if __name__ == '__main__':
    print("="*100)
    print("PURE TREND-FOLLOWING ANALYSIS")
    print("="*100)
    print("Configuration:")
    print("  - Position Sizing: 95% of portfolio")
    print("  - Stop Loss: NONE (only exit on trend reversal)")
    print("  - Profit Target: NONE (let winners run)")
    print("  - ATR Period: 30 (longer for smoother trends)")
    print("  - ATR Multipliers Tested: 4.0, 6.0, 8.0, 10.0, 12.0")
    print("  - Commission: 0%")
    print("="*100)

    all_results = []
    for symbol, csv_file in symbols.items():
        result = test_symbol(symbol, csv_file)
        all_results.append(result)

    # Overall summary
    print(f"\n\n{'='*100}")
    print("OVERALL SUMMARY - PURE TREND FOLLOWING")
    print(f"{'='*100}")
    print(f"{'Symbol':<10} {'B&H $':<15} {'ST $':<15} {'Capture':<10} {'B&H DD':<10} {'ST DD':<10} "
          f"{'DD Red':<10} {'Mult':<8} {'Trades':<10}")
    print(f"{'-'*100}")

    for r in all_results:
        print(f"{r['symbol']:<10} ${r['bh_final']:>12,.0f} ${r['st_final']:>12,.0f} "
              f"{r['capture_pct']:>8.1f}% {r['bh_dd']:>8.1f}% {r['st_dd']:>8.1f}% "
              f"{r['dd_reduction']:>8.1f}% {r['st_multiplier']:<8.1f} {r['st_trades']:<10}")

    # Averages
    avg_capture = sum(r['capture_pct'] for r in all_results) / len(all_results)
    avg_dd_reduction = sum(r['dd_reduction'] for r in all_results) / len(all_results)
    avg_trades = sum(r['st_trades'] for r in all_results) / len(all_results)

    print(f"{'-'*100}")
    print(f"{'AVERAGE':<10} {'':<15} {'':<15} {avg_capture:>8.1f}% {'':<10} {'':<10} "
          f"{avg_dd_reduction:>8.1f}% {'':<8} {avg_trades:<10.1f}")
    print(f"{'='*100}")

    print(f"\n💡 KEY INSIGHTS:")
    print(f"   Average Return Capture: {avg_capture:.1f}%")
    print(f"   Average DD Reduction: {avg_dd_reduction:.1f}%")
    print(f"   Average Trades: {avg_trades:.1f}")
    print(f"\n   Pure trend-following (no SL/PT) optimizes for maximum trend capture")
    print(f"   Accepts higher drawdowns in exchange for staying in winning trends")
