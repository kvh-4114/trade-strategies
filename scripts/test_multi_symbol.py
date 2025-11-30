"""
Test NVDA winner configuration on AAPL, AMD, TSLA
Validates if optimal params are consistent across symbols
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
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

def run_backtest(symbol, csv_file, atr_period, atr_mult, stop_loss):
    """Run backtest on a symbol with given parameters"""

    # Load data
    df = pd.read_csv(csv_file, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])

    # Setup cerebro
    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(
        SupertrendStrategy,
        atr_period=atr_period,
        atr_multiplier=atr_mult,
        stop_loss_type='fixed_pct' if stop_loss else 'none',
        stop_loss_value=stop_loss,
        profit_target=None,
        log_trades=False
    )

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    strat = results[0]
    trade_analysis = strat.analyzers.trades.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()

    num_trades = trade_analysis.get('total', {}).get('closed', 0)
    total_return = ((end_value - start_value) / start_value) * 100
    max_dd = drawdown.get('max', {}).get('drawdown', 0) if drawdown.get('max') else 0
    sharpe_ratio = sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0

    won = trade_analysis.get('won', {}).get('total', 0)
    win_rate = (won / num_trades * 100) if num_trades > 0 else 0

    # Calculate buy-and-hold
    bh_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100

    return {
        'symbol': symbol,
        'return': total_return,
        'trades': num_trades,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'sharpe': sharpe_ratio,
        'final_value': end_value,
        'buy_hold_return': bh_return
    }

def main():
    print("="*80)
    print("TESTING NVDA WINNER CONFIG ON OTHER STOCKS")
    print("Configuration: ATR 30, Mult 6.0, Stop Loss 10%")
    print("="*80)
    print()

    symbols = [
        ('AAPL', 'data/raw/AAPL_daily.csv'),
        ('AMD', 'data/raw/AMD_daily.csv'),
        ('TSLA', 'data/raw/TSLA_daily.csv'),
        ('NVDA', 'data/raw/NVDA_daily.csv')  # Include for comparison
    ]

    results = []
    for symbol, csv_file in symbols:
        print(f"Testing {symbol}...")
        result = run_backtest(symbol, csv_file, atr_period=30, atr_mult=6.0, stop_loss=-0.10)
        results.append(result)

    print("\n" + "="*80)
    print("RESULTS - NVDA WINNER CONFIG APPLIED TO ALL STOCKS")
    print("="*80)
    print()

    print(f"{'Symbol':<8} {'Return':>10} {'Trades':>8} {'Win%':>8} {'MaxDD':>8} {'Sharpe':>8} {'B&H Return':>12}")
    print("-" * 80)

    for r in results:
        print(f"{r['symbol']:<8} {r['return']:>9.1f}% {r['trades']:>8} {r['win_rate']:>7.1f}% "
              f"{r['max_dd']:>7.1f}% {r['sharpe']:>8.2f} {r['buy_hold_return']:>11,.0f}%")

    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    print()

    avg_return = sum(r['return'] for r in results) / len(results)
    avg_trades = sum(r['trades'] for r in results) / len(results)
    avg_win_rate = sum(r['win_rate'] for r in results) / len(results)

    print(f"Average Return: {avg_return:.1f}%")
    print(f"Average Trades: {avg_trades:.1f}")
    print(f"Average Win Rate: {avg_win_rate:.1f}%")
    print()

    best = max(results, key=lambda x: x['return'])
    print(f"Best Performer: {best['symbol']} with {best['return']:.1f}% return")
    print()

    # Check consistency
    all_profitable = all(r['return'] > 0 for r in results)
    if all_profitable:
        print("✅ Strategy is profitable on ALL tested stocks!")
    else:
        losing = [r['symbol'] for r in results if r['return'] <= 0]
        print(f"⚠️  Strategy lost money on: {', '.join(losing)}")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
