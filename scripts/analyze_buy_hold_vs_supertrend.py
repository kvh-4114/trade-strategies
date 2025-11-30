"""
Compare Buy-and-Hold vs Supertrend Strategy
Analyze returns, drawdowns, and risk-adjusted performance
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
    """Simple buy-and-hold strategy"""

    def __init__(self):
        self.order = None

    def next(self):
        if not self.position:
            # Buy on first bar - account for commission to avoid rejection
            cash = self.broker.get_cash()
            close = self.data.close[0]
            # Commission is 0.1% so total cost is close * 1.001
            size = int(cash / (close * 1.001))
            if size > 0:
                self.order = self.buy(size=size)

def run_buy_hold(df):
    """Run buy-and-hold backtest"""
    cerebro = bt.Cerebro()

    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(BuyAndHold)

    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    strat = results[0]

    drawdown = strat.analyzers.drawdown.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    returns = strat.analyzers.returns.get_analysis()

    total_return = ((end_value - start_value) / start_value) * 100
    max_dd = drawdown.get('max', {}).get('drawdown', 0) if drawdown.get('max') else 0
    sharpe_ratio = sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0

    return {
        'return': total_return,
        'max_dd': max_dd,
        'sharpe': sharpe_ratio,
        'final_value': end_value
    }

def run_supertrend(df, params):
    """Run Supertrend backtest"""
    cerebro = bt.Cerebro()

    data = PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(
        SupertrendStrategy,
        atr_period=params['atr_period'],
        atr_multiplier=params['atr_multiplier'],
        stop_loss_type=params['stop_loss_type'],
        stop_loss_value=params['stop_loss_value'],
        profit_target=params['profit_target'],
        log_trades=False
    )

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)

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

    return {
        'return': total_return,
        'trades': num_trades,
        'max_dd': max_dd,
        'sharpe': sharpe_ratio,
        'final_value': end_value
    }

def analyze_symbol(symbol, csv_file, st_params):
    """Compare B&H vs Supertrend for a symbol"""

    # Load data
    df = pd.read_csv(csv_file, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])

    # Run both strategies
    print(f"\nAnalyzing {symbol}...")
    bh_results = run_buy_hold(df)
    st_results = run_supertrend(df, st_params)

    return {
        'symbol': symbol,
        'bh_return': bh_results['return'],
        'bh_max_dd': bh_results['max_dd'],
        'bh_sharpe': bh_results['sharpe'],
        'st_return': st_results['return'],
        'st_max_dd': st_results['max_dd'],
        'st_sharpe': st_results['sharpe'],
        'st_trades': st_results['trades'],
        'return_captured': (st_results['return'] / bh_results['return'] * 100) if bh_results['return'] > 0 else 0,
        'dd_reduction': ((bh_results['max_dd'] - st_results['max_dd']) / bh_results['max_dd'] * 100) if bh_results['max_dd'] > 0 else 0
    }

def main():
    print("="*100)
    print("BUY-AND-HOLD vs SUPERTREND ANALYSIS")
    print("="*100)

    # Define optimal configs for each stock
    configs = {
        'NVDA': {
            'csv': 'data/raw/NVDA_daily.csv',
            'params': {'atr_period': 30, 'atr_multiplier': 6.0, 'stop_loss_type': 'fixed_pct',
                      'stop_loss_value': -0.10, 'profit_target': None}
        },
        'AMD': {
            'csv': 'data/raw/AMD_daily.csv',
            'params': {'atr_period': 10, 'atr_multiplier': 6.0, 'stop_loss_type': 'fixed_pct',
                      'stop_loss_value': -0.10, 'profit_target': None}
        },
        'TSLA': {
            'csv': 'data/raw/TSLA_daily.csv',
            'params': {'atr_period': 10, 'atr_multiplier': 3.0, 'stop_loss_type': 'none',
                      'stop_loss_value': None, 'profit_target': 2.0}
        },
        'AAPL': {
            'csv': 'data/raw/AAPL_daily.csv',
            'params': {'atr_period': 20, 'atr_multiplier': 2.0, 'stop_loss_type': 'fixed_pct',
                      'stop_loss_value': -0.15, 'profit_target': 0.5}
        }
    }

    results = []
    for symbol, config in configs.items():
        result = analyze_symbol(symbol, config['csv'], config['params'])
        results.append(result)

    df = pd.DataFrame(results)

    print("\n" + "="*100)
    print("COMPARISON TABLE")
    print("="*100)
    print()

    print(f"{'Symbol':<8} {'B&H Return':>12} {'B&H MaxDD':>11} {'B&H Sharpe':>11} | "
          f"{'ST Return':>10} {'ST MaxDD':>9} {'ST Sharpe':>10} {'Trades':>8} | "
          f"{'Return %':>9} {'DD Reduced':>11}")
    print("-"*100)

    for _, row in df.iterrows():
        print(f"{row['symbol']:<8} {row['bh_return']:>11,.1f}% {row['bh_max_dd']:>10.1f}% {row['bh_sharpe']:>11.2f} | "
              f"{row['st_return']:>9.1f}% {row['st_max_dd']:>8.1f}% {row['st_sharpe']:>10.2f} {row['st_trades']:>8.0f} | "
              f"{row['return_captured']:>8.1f}% {row['dd_reduction']:>10.1f}%")

    print("-"*100)
    print(f"{'AVERAGE':<8} {df['bh_return'].mean():>11,.1f}% {df['bh_max_dd'].mean():>10.1f}% "
          f"{df['bh_sharpe'].mean():>11.2f} | "
          f"{df['st_return'].mean():>9.1f}% {df['st_max_dd'].mean():>8.1f}% "
          f"{df['st_sharpe'].mean():>10.2f} {df['st_trades'].mean():>8.1f} | "
          f"{df['return_captured'].mean():>8.1f}% {df['dd_reduction'].mean():>10.1f}%")

    print("\n" + "="*100)
    print("KEY INSIGHTS")
    print("="*100)
    print()

    # Return capture analysis
    avg_capture = df['return_captured'].mean()
    print(f"📊 RETURN CAPTURE")
    print(f"   Supertrend captures {avg_capture:.1f}% of buy-and-hold returns on average")
    print(f"   Range: {df['return_captured'].min():.1f}% to {df['return_captured'].max():.1f}%")
    print()

    # Drawdown analysis
    avg_dd_reduction = df['dd_reduction'].mean()
    print(f"🛡️  DRAWDOWN PROTECTION")
    print(f"   Average B&H max DD: {df['bh_max_dd'].mean():.1f}%")
    print(f"   Average ST max DD: {df['st_max_dd'].mean():.1f}%")
    print(f"   Average DD reduction: {avg_dd_reduction:.1f}%")
    print()

    # Sharpe analysis
    print(f"📈 RISK-ADJUSTED RETURNS (Sharpe Ratio)")
    print(f"   Average B&H Sharpe: {df['bh_sharpe'].mean():.2f}")
    print(f"   Average ST Sharpe: {df['st_sharpe'].mean():.2f}")

    sharpe_improvement = df['st_sharpe'].mean() - df['bh_sharpe'].mean()
    if sharpe_improvement > 0:
        print(f"   ✅ Supertrend improves Sharpe by {sharpe_improvement:.2f}")
    else:
        print(f"   ⚠️  Buy-and-hold has better Sharpe by {abs(sharpe_improvement):.2f}")
    print()

    # Trade-off analysis
    print(f"⚖️  TRADE-OFFS")
    print()
    print(f"   Buy-and-Hold:")
    print(f"   • Returns: {df['bh_return'].mean():,.1f}% (massive)")
    print(f"   • Max DD: {df['bh_max_dd'].mean():.1f}% (painful)")
    print(f"   • Sharpe: {df['bh_sharpe'].mean():.2f}")
    print(f"   • Requires: Perfect timing, diamond hands, emotional discipline")
    print()
    print(f"   Supertrend:")
    print(f"   • Returns: {df['st_return'].mean():.1f}% (modest)")
    print(f"   • Max DD: {df['st_max_dd'].mean():.1f}% (manageable)")
    print(f"   • Sharpe: {df['st_sharpe'].mean():.2f}")
    print(f"   • Provides: Risk management, systematic rules, peace of mind")

    print("\n" + "="*100)
    print("RECOMMENDATIONS")
    print("="*100)
    print()

    print("1. FOR MAXIMUM ABSOLUTE RETURNS:")
    print("   → Use Buy-and-Hold if you can tolerate 50%+ drawdowns")
    print()

    print("2. FOR MANAGED RISK:")
    print("   → Use Supertrend for ~10% max DD vs ~50%+ for B&H")
    print("   → Sacrifice ~99% of returns to reduce DD by ~80%")
    print()

    print("3. HYBRID APPROACH (RECOMMENDED):")
    print("   → Core position: 70% buy-and-hold (long-term conviction)")
    print("   → Tactical: 30% Supertrend (trend-following overlay)")
    print("   → Benefits: Capture most upside, reduce overall portfolio DD")
    print()

    print("4. IMPROVE SUPERTREND CAPTURE:")
    print("   → Test wider bands to stay in trends longer")
    print("   → Remove profit targets completely")
    print("   → Consider pyramiding (add to winners)")
    print("   → Use portfolio leverage with strict risk controls")

    print("\n" + "="*100)

if __name__ == '__main__':
    main()
