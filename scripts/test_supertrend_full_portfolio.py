"""
Test Supertrend with FULL PORTFOLIO position sizing (fair comparison)
Compare against buy-and-hold with both using 100% of capital
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

class BuyAndHold(bt.Strategy):
    """Simple buy-and-hold strategy"""
    def __init__(self):
        self.order = None

    def next(self):
        if not self.position:
            cash = self.broker.get_cash()
            close = self.data.close[0]
            size = int(cash / close)
            if size > 0:
                self.order = self.buy(size=size)

def run_buy_hold(df):
    """Run buy-and-hold backtest"""
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
        'max_dd': drawdown.get('max', {}).get('drawdown', 0) if drawdown.get('max') else 0,
        'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
    }

def run_supertrend(df, params):
    """Run Supertrend with full portfolio sizing"""
    cerebro = bt.Cerebro()
    cerebro.adddata(PandasData(dataname=df))

    cerebro.addstrategy(
        SupertrendStrategy,
        atr_period=params['atr_period'],
        atr_multiplier=params['atr_multiplier'],
        position_sizing='portfolio_pct',  # ✅ USE FULL PORTFOLIO!
        stop_loss_type=params.get('stop_loss_type', 'none'),
        stop_loss_value=params.get('stop_loss_value', None),
        profit_target=params.get('profit_target', None),
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
        'max_dd': drawdown.get('max', {}).get('drawdown', 0) if drawdown.get('max') else 0,
        'sharpe': sharpe.get('sharperatio', 0) if sharpe.get('sharperatio') else 0,
        'trades': num_trades,
        'wins': won,
        'win_rate': (won / num_trades * 100) if num_trades > 0 else 0,
    }

def test_symbol(symbol, csv_file, st_params):
    """Test a single symbol"""
    print(f"\n{'='*80}")
    print(f"Testing {symbol}")
    print(f"{'='*80}")

    # Load data
    df = pd.read_csv(csv_file, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    print(f"Data: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Price: ${df.iloc[0]['close']:.2f} → ${df.iloc[-1]['close']:.2f}")
    print(f"\nSupertrend params: ATR {st_params['atr_period']}, Mult {st_params['atr_multiplier']}, " +
          f"SL {st_params.get('stop_loss_type', 'none')}, PT {st_params.get('profit_target', 'none')}")

    # Run both strategies
    print(f"\nRunning backtests...")
    bh_results = run_buy_hold(df)
    st_results = run_supertrend(df, st_params)

    # Calculate metrics
    capture_pct = (st_results['return'] / bh_results['return'] * 100) if bh_results['return'] > 0 else 0
    dd_reduction = ((bh_results['max_dd'] - st_results['max_dd']) / bh_results['max_dd'] * 100) if bh_results['max_dd'] > 0 else 0

    # Print results
    print(f"\n{'Strategy':<20} {'Return':<15} {'Final $':<15} {'MaxDD':<10} {'Sharpe':<10} {'Trades':<10}")
    print(f"{'-'*80}")
    print(f"{'Buy & Hold':<20} {bh_results['return']:>13.1f}% ${bh_results['final_value']:>12,.0f} {bh_results['max_dd']:>8.1f}% {bh_results['sharpe']:>9.2f} {'1':<10}")
    print(f"{'Supertrend':<20} {st_results['return']:>13.1f}% ${st_results['final_value']:>12,.0f} {st_results['max_dd']:>8.1f}% {st_results['sharpe']:>9.2f} {st_results['trades']:<10}")
    print(f"{'-'*80}")
    print(f"{'Return Capture:':<20} {capture_pct:>13.1f}%")
    print(f"{'DD Reduction:':<20} {dd_reduction:>13.1f}%")
    print(f"{'Win Rate:':<20} {st_results['win_rate']:>13.1f}% ({st_results['wins']}/{st_results['trades']})")

    return {
        'symbol': symbol,
        'bh_return': bh_results['return'],
        'st_return': st_results['return'],
        'capture_pct': capture_pct,
        'bh_dd': bh_results['max_dd'],
        'st_dd': st_results['max_dd'],
        'dd_reduction': dd_reduction,
        'bh_sharpe': bh_results['sharpe'],
        'st_sharpe': st_results['sharpe'],
        'trades': st_results['trades'],
    }

# Test configurations (using optimized params from previous analysis)
configs = {
    'NVDA': {
        'csv': 'data/raw/NVDA_daily.csv',
        'params': {
            'atr_period': 30,
            'atr_multiplier': 6.0,
            'stop_loss_type': 'fixed_pct',
            'stop_loss_value': -0.10,
            'profit_target': None
        }
    },
    'AMD': {
        'csv': 'data/raw/AMD_daily.csv',
        'params': {
            'atr_period': 10,
            'atr_multiplier': 6.0,
            'stop_loss_type': 'fixed_pct',
            'stop_loss_value': -0.10,
            'profit_target': None
        }
    },
    'TSLA': {
        'csv': 'data/raw/TSLA_daily.csv',
        'params': {
            'atr_period': 10,
            'atr_multiplier': 3.0,
            'stop_loss_type': 'none',
            'stop_loss_value': None,
            'profit_target': 2.0
        }
    },
    'AAPL': {
        'csv': 'data/raw/AAPL_daily.csv',
        'params': {
            'atr_period': 20,
            'atr_multiplier': 2.0,
            'stop_loss_type': 'fixed_pct',
            'stop_loss_value': -0.15,
            'profit_target': 0.5
        }
    },
}

if __name__ == '__main__':
    print("="*80)
    print("SUPERTREND WITH FULL PORTFOLIO vs BUY-AND-HOLD")
    print("Position Sizing: 95% of portfolio (FAIR COMPARISON)")
    print("Commission: 0%")
    print("="*80)

    results = []
    for symbol, config in configs.items():
        result = test_symbol(symbol, config['csv'], config['params'])
        results.append(result)

    # Summary table
    print(f"\n\n{'='*80}")
    print("SUMMARY - FULL PORTFOLIO POSITION SIZING")
    print(f"{'='*80}")
    print(f"{'Symbol':<10} {'B&H Ret':<12} {'ST Ret':<12} {'Capture':<10} {'DD Red':<10} {'Trades':<10}")
    print(f"{'-'*80}")

    for r in results:
        print(f"{r['symbol']:<10} {r['bh_return']:>10.1f}% {r['st_return']:>10.1f}% {r['capture_pct']:>8.1f}% {r['dd_reduction']:>8.1f}% {r['trades']:<10}")

    # Averages
    avg_capture = sum(r['capture_pct'] for r in results) / len(results)
    avg_dd_reduction = sum(r['dd_reduction'] for r in results) / len(results)

    print(f"{'-'*80}")
    print(f"{'AVERAGE':<10} {'':<12} {'':<12} {avg_capture:>8.1f}% {avg_dd_reduction:>8.1f}%")
    print(f"{'='*80}")

    print(f"\n🎯 KEY INSIGHT:")
    print(f"   With FULL portfolio allocation, Supertrend captures {avg_capture:.1f}% of returns")
    print(f"   vs only 1.2% with fixed $10K positions")
    print(f"   That's a {avg_capture / 1.2:.1f}x improvement!")
