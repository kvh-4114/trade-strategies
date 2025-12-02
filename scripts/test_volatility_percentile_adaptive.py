"""
Volatility Percentile Adaptive Dual Supertrend

Adapts exit parameters based on BACKWARDS-LOOKING volatility percentile.
NO look-ahead bias - only uses data available up to current bar.

Logic:
- High volatility (top 20%): Use tighter bands to avoid whipsaws
- Low volatility (bottom 20%): Use wider bands to stay in smooth trends
- Medium volatility: Use optimal default

Key insight: In high-vol periods, tighter bands prevent getting shaken out
In low-vol periods, wider bands avoid exiting too early
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
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

class VolatilityPercentileAdaptive(bt.Strategy):
    """
    Adaptive Dual Supertrend using volatility percentile for exit parameter selection.

    Entry: Fixed tight bands (10, 2.0)
    Exit: Adaptive based on volatility percentile:
        - High vol (top 20%): Balanced bands (20, 5.0) - avoid whipsaws
        - Medium vol (middle 60%): Balanced bands (20, 5.0) - optimal
        - Low vol (bottom 20%): Wider bands (25, 6.0) - stay in smooth trends
    """
    params = (
        ('vol_lookback', 126),  # ~6 months of daily data
        ('log_regime_changes', False),
    )

    def __init__(self):
        # Volatility indicator
        self.atr = bt.indicators.ATR(self.data, period=20)

        # Entry Supertrend (FIXED)
        self.entry_st = Supertrend(self.data, period=10, multiplier=2.0)

        # Multiple Exit Supertrends
        self.exit_st_high_vol = Supertrend(self.data, period=20, multiplier=5.0)    # Balanced
        self.exit_st_medium_vol = Supertrend(self.data, period=20, multiplier=5.0)  # Balanced
        self.exit_st_low_vol = Supertrend(self.data, period=25, multiplier=6.0)     # Wider

        self.order = None
        self.trade_count = 0
        self.wins = 0
        self.current_regime = None

        # Track volatility history for percentile calculation
        self.vol_history = []

    def get_volatility_percentile(self):
        """
        Calculate where current volatility ranks in recent history.

        Returns:
            float: Percentile (0.0 to 1.0)
        """
        if len(self) < 20:  # Need ATR to be ready
            return 0.5

        # Normalized volatility (ATR as % of price)
        current_vol = self.atr[0] / self.data.close[0]

        # Collect recent volatility history (backwards-looking only!)
        lookback = min(self.params.vol_lookback, len(self))
        recent_vols = []
        for i in range(lookback):
            if len(self) > i and self.atr[-i] > 0 and self.data.close[-i] > 0:
                vol = self.atr[-i] / self.data.close[-i]
                recent_vols.append(vol)

        if not recent_vols:
            return 0.5

        # Calculate percentile (what fraction of history is below current?)
        percentile = sum(1 for v in recent_vols if v < current_vol) / len(recent_vols)
        return percentile

    def get_volatility_regime(self):
        """
        Classify current volatility regime.

        Returns:
            str: 'high', 'medium', or 'low'
        """
        percentile = self.get_volatility_percentile()

        if percentile > 0.80:  # Top 20%
            return 'high'
        elif percentile < 0.20:  # Bottom 20%
            return 'low'
        else:
            return 'medium'

    def get_exit_st_for_regime(self, regime):
        """Select exit Supertrend based on volatility regime"""
        regime_map = {
            'high': self.exit_st_high_vol,      # Balanced for choppy markets
            'medium': self.exit_st_medium_vol,  # Optimal default
            'low': self.exit_st_low_vol,        # Wider for smooth trends
        }
        return regime_map.get(regime, self.exit_st_medium_vol)

    def next(self):
        if self.order:
            return

        regime = self.get_volatility_regime()

        if regime != self.current_regime and self.params.log_regime_changes:
            if len(self) >= 20:
                pct = self.get_volatility_percentile()
                vol = self.atr[0] / self.data.close[0] * 100
                print(f'{self.data.datetime.date(0)}: Vol regime: {regime} '
                      f'(Percentile: {pct:.0%}, Vol: {vol:.2f}%)')
            self.current_regime = regime

        # Select exit indicator based on volatility regime
        exit_st = self.get_exit_st_for_regime(regime)

        if not self.position:
            if self.entry_st.direction[0] == 1:
                cash = self.broker.get_cash()
                size = int(cash * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            if len(self) > 1 and exit_st.direction[0] == -1 and exit_st.direction[-1] == 1:
                self.order = self.sell(size=self.position.size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            if trade.pnl > 0:
                self.wins += 1

class UniversalDualSupertrend(bt.Strategy):
    """Universal (non-adaptive) for comparison"""
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
            size = int(cash / self.data.close[0])
            if size > 0:
                self.order = self.buy(size=size)

def run_strategy(df, strategy_class, **kwargs):
    """Run a strategy and return results"""
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
    }

def test_symbol(symbol, csv_file):
    """Test volatility-percentile adaptive vs universal"""
    print(f"\n{'='*100}")
    print(f"TESTING {symbol} - VOLATILITY PERCENTILE ADAPTIVE")
    print(f"{'='*100}")

    # Load data
    df = pd.read_csv(csv_file, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    print(f"Data: {df['date'].min().date()} to {df['date'].max().date()}")

    # Run all strategies
    print(f"Running strategies...")
    bh = run_strategy(df, BuyAndHold)
    universal = run_strategy(df, UniversalDualSupertrend)
    adaptive = run_strategy(df, VolatilityPercentileAdaptive)

    # Print results
    print(f"\n{'Strategy':<30} {'Return':<15} {'Final $':<15} {'MaxDD':<10} {'Sharpe':<10} {'Trades':<10} {'Win%':<10}")
    print(f"{'-'*100}")
    print(f"{'Buy & Hold':<30} {bh['return']:>13.1f}% ${bh['final_value']:>12,.0f} {bh['max_dd']:>8.1f}% {bh['sharpe']:>9.2f} {'1':<10} {'-':<10}")
    print(f"{'Universal (20/5.0 exit)':<30} {universal['return']:>13.1f}% ${universal['final_value']:>12,.0f} "
          f"{universal['max_dd']:>8.1f}% {universal['sharpe']:>9.2f} {universal['trades']:<10} {universal['win_rate']:<9.1f}%")
    print(f"{'Adaptive (Vol%-based exit)':<30} {adaptive['return']:>13.1f}% ${adaptive['final_value']:>12,.0f} "
          f"{adaptive['max_dd']:>8.1f}% {adaptive['sharpe']:>9.2f} {adaptive['trades']:<10} {adaptive['win_rate']:<9.1f}%")

    # Compare
    uni_capture = (universal['return'] / bh['return'] * 100) if bh['return'] > 0 else 0
    adp_capture = (adaptive['return'] / bh['return'] * 100) if bh['return'] > 0 else 0

    print(f"\nCapture Rates:")
    print(f"  Universal: {uni_capture:.1f}%")
    print(f"  Adaptive:  {adp_capture:.1f}%")
    print(f"  Difference: {adp_capture - uni_capture:+.1f}%")

    return {
        'symbol': symbol,
        'bh_return': bh['return'],
        'uni_return': universal['return'],
        'adp_return': adaptive['return'],
        'uni_capture': uni_capture,
        'adp_capture': adp_capture,
        'uni_trades': universal['trades'],
        'adp_trades': adaptive['trades'],
        'uni_sharpe': universal['sharpe'],
        'adp_sharpe': adaptive['sharpe'],
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
    print("VOLATILITY PERCENTILE ADAPTIVE DUAL SUPERTREND")
    print("="*100)
    print("\nAdaptive Approach: Adjust exit parameters based on volatility percentile")
    print("  - High volatility (top 20%): Balanced exit (20, 5.0) - avoid whipsaws")
    print("  - Medium volatility (middle 60%): Balanced exit (20, 5.0) - optimal")
    print("  - Low volatility (bottom 20%): Wider exit (25, 6.0) - stay in smooth trends")
    print("\nKey insight: Volatility percentile normalizes across symbols")
    print("  - TSLA's 'normal' volatility might be AAPL's 'high' volatility")
    print("  - Percentile adapts to each stock's own characteristics")
    print("="*100)

    all_results = []
    for symbol, csv_file in symbols.items():
        result = test_symbol(symbol, csv_file)
        all_results.append(result)

    # Summary
    print(f"\n\n{'='*100}")
    print("OVERALL SUMMARY")
    print(f"{'='*100}")
    print(f"{'Symbol':<10} {'B&H Return':<15} {'Universal':<15} {'Adaptive':<15} {'Uni Cap':<10} {'Adp Cap':<10} {'Diff':<10}")
    print(f"{'-'*100}")

    for r in all_results:
        diff = r['adp_capture'] - r['uni_capture']
        marker = " ✓" if diff > 0 else ""
        print(f"{r['symbol']:<10} {r['bh_return']:>13.1f}% {r['uni_return']:>13.1f}% {r['adp_return']:>13.1f}% "
              f"{r['uni_capture']:>8.1f}% {r['adp_capture']:>8.1f}% {diff:>8.1f}%{marker}")

    # Averages
    avg_uni_capture = sum(r['uni_capture'] for r in all_results) / len(all_results)
    avg_adp_capture = sum(r['adp_capture'] for r in all_results) / len(all_results)
    avg_uni_trades = sum(r['uni_trades'] for r in all_results) / len(all_results)
    avg_adp_trades = sum(r['adp_trades'] for r in all_results) / len(all_results)

    print(f"{'-'*100}")
    print(f"{'AVERAGE':<10} {'':<15} {'':<15} {'':<15} {avg_uni_capture:>8.1f}% {avg_adp_capture:>8.1f}% "
          f"{avg_adp_capture - avg_uni_capture:>8.1f}%")
    print(f"{'='*100}")

    print(f"\n📊 COMPARISON:")
    print(f"   Universal: {avg_uni_capture:.1f}% average capture, {avg_uni_trades:.1f} avg trades")
    print(f"   Adaptive:  {avg_adp_capture:.1f}% average capture, {avg_adp_trades:.1f} avg trades")
    print(f"   Improvement: {avg_adp_capture - avg_uni_capture:+.1f}%")

    if avg_adp_capture > avg_uni_capture + 1:
        print(f"\n🏆 WINNER: Adaptive (volatility-aware is better!)")
        print(f"   Volatility percentile adaptation adds {avg_adp_capture - avg_uni_capture:.1f}% extra capture")
    elif avg_adp_capture < avg_uni_capture - 1:
        print(f"\n🏆 WINNER: Universal (simpler is better!)")
        print(f"   Fixed parameters outperform by {avg_uni_capture - avg_adp_capture:.1f}%")
    else:
        print(f"\n⚖️  TIE: Both approaches perform similarly")
        print(f"   Difference of {abs(avg_adp_capture - avg_uni_capture):.1f}% is negligible")

    print(f"\n💡 CONCLUSION:")
    print(f"   Backwards-looking volatility percentile uses ONLY historical data")
    print(f"   No look-ahead bias - this is a fair real-world test")
