"""
Trend Strength Adaptive Dual Supertrend

Adapts exit parameters based on BACKWARDS-LOOKING trend strength (ADX).
NO look-ahead bias - only uses data available up to current bar.

Logic:
- Strong trend (ADX > 30): Use wide exit bands to stay in trend longer
- Moderate trend (ADX 20-30): Use medium bands (our optimal default)
- Weak trend (ADX < 20): Use tight bands to exit choppy markets faster

Entry parameters stay fixed (10, 2.0) - always responsive
Exit parameters adapt based on market regime
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

class TrendStrengthAdaptive(bt.Strategy):
    """
    Adaptive Dual Supertrend using trend strength (ADX) for exit parameter selection.

    Entry: Fixed tight bands (10, 2.0)
    Exit: Adaptive based on ADX:
        - Strong trend (ADX > 30): Wide bands (30, 7.0)
        - Moderate trend (ADX 20-30): Medium bands (20, 5.0) [optimal]
        - Weak trend (ADX < 20): Tight bands (15, 4.0)
    """
    params = (
        ('adx_period', 14),
        ('log_trades', False),
        ('log_regime_changes', True),
    )

    def __init__(self):
        # Trend strength indicator (ADX)
        self.adx = bt.indicators.ADX(self.data, period=self.params.adx_period)

        # Entry Supertrend (FIXED - always responsive)
        self.entry_st = Supertrend(self.data, period=10, multiplier=2.0)

        # Exit Supertrend (ADAPTIVE - starts with optimal default)
        self.exit_st = Supertrend(self.data, period=20, multiplier=5.0)

        self.order = None
        self.trade_count = 0
        self.wins = 0

        # Track current regime
        self.current_regime = None
        self.regime_changes = []

    def get_trend_regime(self):
        """
        Determine trend strength regime using ADX.

        Returns:
            str: 'strong', 'moderate', or 'weak'
        """
        if len(self) < self.params.adx_period:
            return 'moderate'  # Default until ADX is ready

        adx_value = self.adx[0]

        if adx_value > 30:
            return 'strong'
        elif adx_value > 20:
            return 'moderate'
        else:
            return 'weak'

    def get_exit_params_for_regime(self, regime):
        """
        Return (period, multiplier) for exit Supertrend based on regime.

        Strong trend: Stay in longer with wide bands
        Moderate trend: Optimal balanced bands
        Weak trend: Exit faster with tight bands
        """
        params_map = {
            'strong': (30, 7.0),   # Wide - stay in strong trends
            'moderate': (20, 5.0), # Optimal - balanced approach
            'weak': (15, 4.0),     # Tight - exit choppy markets fast
        }
        return params_map.get(regime, (20, 5.0))

    def next(self):
        if self.order:
            return

        # Determine current trend regime
        regime = self.get_trend_regime()

        # Log regime changes
        if regime != self.current_regime:
            if self.params.log_regime_changes and len(self) >= self.params.adx_period:
                period, mult = self.get_exit_params_for_regime(regime)
                print(f'{self.data.datetime.date(0)}: Regime change: {self.current_regime} → {regime} '
                      f'(ADX: {self.adx[0]:.1f}, Exit params: {period}/{mult})')
                self.regime_changes.append({
                    'date': self.data.datetime.date(0),
                    'from': self.current_regime,
                    'to': regime,
                    'adx': self.adx[0],
                })
            self.current_regime = regime

        # Get appropriate exit parameters for current regime
        # NOTE: We can't dynamically recreate indicators in backtrader
        # Instead, we interpret the same exit_st signals with awareness of regime
        # For proper implementation, we'd use regime to select between pre-created indicators

        if not self.position:
            # ENTRY: Use fixed tight Supertrend
            if self.entry_st.direction[0] == 1:
                cash = self.broker.get_cash()
                size = int(cash * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    if self.params.log_trades:
                        print(f'{self.data.datetime.date(0)}: BUY (Regime: {regime}, ADX: {self.adx[0]:.1f})')
        else:
            # EXIT: Use exit Supertrend reversal
            if len(self) > 1 and self.exit_st.direction[0] == -1 and self.exit_st.direction[-1] == 1:
                self.order = self.sell(size=self.position.size)
                if self.params.log_trades:
                    print(f'{self.data.datetime.date(0)}: SELL (Regime: {regime}, ADX: {self.adx[0]:.1f})')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            if trade.pnl > 0:
                self.wins += 1

class TrendStrengthAdaptiveMultiST(bt.Strategy):
    """
    IMPROVED VERSION: Pre-create multiple exit Supertrends and select based on regime.

    This properly adapts by using different exit indicators for different regimes.
    """
    params = (
        ('adx_period', 14),
        ('log_trades', False),
        ('log_regime_changes', False),
    )

    def __init__(self):
        # Trend strength indicator
        self.adx = bt.indicators.ADX(self.data, period=self.params.adx_period)

        # Entry Supertrend (FIXED)
        self.entry_st = Supertrend(self.data, period=10, multiplier=2.0)

        # Multiple Exit Supertrends (one for each regime)
        self.exit_st_strong = Supertrend(self.data, period=30, multiplier=7.0)
        self.exit_st_moderate = Supertrend(self.data, period=20, multiplier=5.0)
        self.exit_st_weak = Supertrend(self.data, period=15, multiplier=4.0)

        self.order = None
        self.trade_count = 0
        self.wins = 0
        self.current_regime = None

    def get_trend_regime(self):
        """Determine trend strength using ADX"""
        if len(self) < self.params.adx_period:
            return 'moderate'

        adx_value = self.adx[0]

        if adx_value > 30:
            return 'strong'
        elif adx_value > 20:
            return 'moderate'
        else:
            return 'weak'

    def get_exit_st_for_regime(self, regime):
        """Select the appropriate exit Supertrend for current regime"""
        regime_map = {
            'strong': self.exit_st_strong,
            'moderate': self.exit_st_moderate,
            'weak': self.exit_st_weak,
        }
        return regime_map.get(regime, self.exit_st_moderate)

    def next(self):
        if self.order:
            return

        regime = self.get_trend_regime()

        if regime != self.current_regime and self.params.log_regime_changes:
            if len(self) >= self.params.adx_period:
                print(f'{self.data.datetime.date(0)}: Regime: {regime} (ADX: {self.adx[0]:.1f})')
            self.current_regime = regime

        # Select exit indicator based on regime
        exit_st = self.get_exit_st_for_regime(regime)

        if not self.position:
            if self.entry_st.direction[0] == 1:
                cash = self.broker.get_cash()
                size = int(cash * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            # Use regime-appropriate exit indicator
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
    """Test trend-strength adaptive vs universal"""
    print(f"\n{'='*100}")
    print(f"TESTING {symbol} - TREND STRENGTH ADAPTIVE")
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
    adaptive = run_strategy(df, TrendStrengthAdaptiveMultiST)

    # Print results
    print(f"\n{'Strategy':<30} {'Return':<15} {'Final $':<15} {'MaxDD':<10} {'Sharpe':<10} {'Trades':<10} {'Win%':<10}")
    print(f"{'-'*100}")
    print(f"{'Buy & Hold':<30} {bh['return']:>13.1f}% ${bh['final_value']:>12,.0f} {bh['max_dd']:>8.1f}% {bh['sharpe']:>9.2f} {'1':<10} {'-':<10}")
    print(f"{'Universal (20/5.0 exit)':<30} {universal['return']:>13.1f}% ${universal['final_value']:>12,.0f} "
          f"{universal['max_dd']:>8.1f}% {universal['sharpe']:>9.2f} {universal['trades']:<10} {universal['win_rate']:<9.1f}%")
    print(f"{'Adaptive (ADX-based exit)':<30} {adaptive['return']:>13.1f}% ${adaptive['final_value']:>12,.0f} "
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
    print("TREND STRENGTH ADAPTIVE DUAL SUPERTREND")
    print("="*100)
    print("\nAdaptive Approach: Adjust exit parameters based on ADX (trend strength)")
    print("  - Strong trend (ADX > 30): Wide exit (30, 7.0) - stay in")
    print("  - Moderate trend (ADX 20-30): Medium exit (20, 5.0) - balanced [optimal]")
    print("  - Weak trend (ADX < 20): Tight exit (15, 4.0) - exit fast")
    print("\nComparison:")
    print("  - Universal: Fixed (20, 5.0) exit for all conditions")
    print("  - Adaptive: Dynamically select exit based on backwards-looking ADX")
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
        print(f"\n🏆 WINNER: Adaptive (trend-aware is better!)")
        print(f"   ADX-based adaptation adds {avg_adp_capture - avg_uni_capture:.1f}% extra capture")
    elif avg_adp_capture < avg_uni_capture - 1:
        print(f"\n🏆 WINNER: Universal (simpler is better!)")
        print(f"   Fixed parameters outperform by {avg_uni_capture - avg_adp_capture:.1f}%")
    else:
        print(f"\n⚖️  TIE: Both approaches perform similarly")
        print(f"   Difference of {abs(avg_adp_capture - avg_uni_capture):.1f}% is negligible")

    print(f"\n💡 INSIGHT:")
    print(f"   Backwards-looking ADX adaptation uses ONLY data up to current bar")
    print(f"   No look-ahead bias - this is a fair test of adaptive parameters")
    print(f"   If adaptive wins, it means market regimes are detectable in real-time")
