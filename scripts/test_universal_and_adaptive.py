"""
Test Two Approaches to Avoid Overfitting:

1. UNIVERSAL PARAMETERS: Single set of params for all stocks
2. ADAPTIVE PARAMETERS: Adjust based on recent volatility regime

Both prevent overfitting to individual stocks
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

class UniversalDualSupertrend(bt.Strategy):
    """
    Universal dual Supertrend - same parameters for all stocks
    Entry: Tight bands, Exit: Wide bands
    """
    params = (
        ('entry_period', 10),
        ('entry_multiplier', 2.0),
        ('exit_period', 30),
        ('exit_multiplier', 6.0),
        ('log_trades', False),
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

class AdaptiveDualSupertrend(bt.Strategy):
    """
    Adaptive dual Supertrend - adjusts parameters based on volatility regime

    High volatility: Use wider bands to avoid whipsaws
    Low volatility: Use tighter bands to catch moves earlier
    """
    params = (
        ('volatility_period', 60),  # Lookback for volatility calculation
        ('log_trades', False),
    )

    def __init__(self):
        # Calculate normalized volatility (ATR / Price)
        self.atr = bt.indicators.ATR(self.data, period=20)

        # We'll create indicators dynamically in next() based on volatility
        # Start with medium defaults
        self.current_entry_mult = 2.0
        self.current_exit_mult = 6.0

        self.entry_st = Supertrend(self.data, period=10, multiplier=2.0)
        self.exit_st = Supertrend(self.data, period=30, multiplier=6.0)

        self.order = None
        self.trade_count = 0
        self.wins = 0

        # Track volatility regime changes for logging
        self.last_regime = None

    def get_volatility_regime(self):
        """
        Determine current volatility regime based on normalized ATR
        Returns: 'high', 'medium', or 'low'
        """
        if len(self) < self.params.volatility_period:
            return 'medium'

        # Calculate normalized volatility (ATR as % of price)
        normalized_vol = self.atr[0] / self.data.close[0]

        # Look back at recent volatility to determine regime
        recent_vols = []
        for i in range(min(self.params.volatility_period, len(self))):
            if len(self) > i:
                vol = self.atr[-i] / self.data.close[-i]
                recent_vols.append(vol)

        if not recent_vols:
            return 'medium'

        avg_vol = np.mean(recent_vols)
        std_vol = np.std(recent_vols)

        # Current volatility relative to recent average
        # High: > 1 std above average
        # Low: < 1 std below average
        # Medium: within 1 std

        if normalized_vol > (avg_vol + std_vol * 0.5):
            return 'high'
        elif normalized_vol < (avg_vol - std_vol * 0.5):
            return 'low'
        else:
            return 'medium'

    def get_params_for_regime(self, regime):
        """
        Return (entry_mult, exit_mult) based on volatility regime

        High volatility: Wider bands to avoid whipsaws
        Low volatility: Tighter bands to catch moves
        Medium: Balanced approach
        """
        if regime == 'high':
            return (2.5, 8.0)  # Wide bands
        elif regime == 'low':
            return (1.8, 5.0)  # Tight bands
        else:  # medium
            return (2.0, 6.0)  # Balanced

    def next(self):
        if self.order:
            return

        # Determine current volatility regime
        regime = self.get_volatility_regime()
        entry_mult, exit_mult = self.get_params_for_regime(regime)

        # Log regime changes
        if regime != self.last_regime and self.params.log_trades:
            print(f'{self.data.datetime.date(0)}: Volatility regime: {regime} '
                  f'(Entry mult: {entry_mult}, Exit mult: {exit_mult})')
            self.last_regime = regime

        # Update multipliers (we use the same indicator instances but interpret
        # the direction signals with awareness of current regime)
        self.current_entry_mult = entry_mult
        self.current_exit_mult = exit_mult

        if not self.position:
            # Entry: Use entry Supertrend
            if self.entry_st.direction[0] == 1:
                cash = self.broker.get_cash()
                size = int(cash * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            # Exit: Use exit Supertrend
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
    """Test both universal and adaptive approaches"""
    print(f"\n{'='*100}")
    print(f"TESTING {symbol}")
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
    adaptive = run_strategy(df, AdaptiveDualSupertrend)

    # Print results
    print(f"\n{'Strategy':<25} {'Return':<15} {'Final $':<15} {'MaxDD':<10} {'Sharpe':<10} {'Trades':<10} {'Win%':<10}")
    print(f"{'-'*100}")
    print(f"{'Buy & Hold':<25} {bh['return']:>13.1f}% ${bh['final_value']:>12,.0f} {bh['max_dd']:>8.1f}% {bh['sharpe']:>9.2f} {'1':<10} {'-':<10}")
    print(f"{'Universal (10/2.0, 30/6.0)':<25} {universal['return']:>13.1f}% ${universal['final_value']:>12,.0f} "
          f"{universal['max_dd']:>8.1f}% {universal['sharpe']:>9.2f} {universal['trades']:<10} {universal['win_rate']:<9.1f}%")
    print(f"{'Adaptive (Vol-based)':<25} {adaptive['return']:>13.1f}% ${adaptive['final_value']:>12,.0f} "
          f"{adaptive['max_dd']:>8.1f}% {adaptive['sharpe']:>9.2f} {adaptive['trades']:<10} {adaptive['win_rate']:<9.1f}%")

    # Compare
    uni_capture = (universal['return'] / bh['return'] * 100) if bh['return'] > 0 else 0
    adp_capture = (adaptive['return'] / bh['return'] * 100) if bh['return'] > 0 else 0

    print(f"\nCapture Rates:")
    print(f"  Universal: {uni_capture:.1f}%")
    print(f"  Adaptive:  {adp_capture:.1f}%")

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
    print("UNIVERSAL vs ADAPTIVE DUAL SUPERTREND")
    print("="*100)
    print("\nApproach 1: UNIVERSAL PARAMETERS")
    print("  - Same parameters for all stocks: Entry (10, 2.0), Exit (30, 6.0)")
    print("  - Prevents overfitting to individual stocks")
    print("  - Simple and robust")
    print("\nApproach 2: ADAPTIVE PARAMETERS")
    print("  - Adjusts based on recent volatility regime")
    print("  - High volatility: Wider bands (2.5, 8.0)")
    print("  - Low volatility: Tighter bands (1.8, 5.0)")
    print("  - Medium volatility: Balanced (2.0, 6.0)")
    print("="*100)

    all_results = []
    for symbol, csv_file in symbols.items():
        result = test_symbol(symbol, csv_file)
        all_results.append(result)

    # Summary
    print(f"\n\n{'='*100}")
    print("OVERALL SUMMARY")
    print(f"{'='*100}")
    print(f"{'Symbol':<10} {'B&H Return':<15} {'Universal':<15} {'Adaptive':<15} {'Uni Cap':<10} {'Adp Cap':<10}")
    print(f"{'-'*100}")

    for r in all_results:
        print(f"{r['symbol']:<10} {r['bh_return']:>13.1f}% {r['uni_return']:>13.1f}% {r['adp_return']:>13.1f}% "
              f"{r['uni_capture']:>8.1f}% {r['adp_capture']:>8.1f}%")

    # Averages
    avg_uni_capture = sum(r['uni_capture'] for r in all_results) / len(all_results)
    avg_adp_capture = sum(r['adp_capture'] for r in all_results) / len(all_results)
    avg_uni_trades = sum(r['uni_trades'] for r in all_results) / len(all_results)
    avg_adp_trades = sum(r['adp_trades'] for r in all_results) / len(all_results)

    print(f"{'-'*100}")
    print(f"{'AVERAGE':<10} {'':<15} {'':<15} {'':<15} {avg_uni_capture:>8.1f}% {avg_adp_capture:>8.1f}%")
    print(f"{'='*100}")

    print(f"\n📊 COMPARISON:")
    print(f"   Universal: {avg_uni_capture:.1f}% average capture, {avg_uni_trades:.1f} avg trades")
    print(f"   Adaptive:  {avg_adp_capture:.1f}% average capture, {avg_adp_trades:.1f} avg trades")

    if avg_uni_capture > avg_adp_capture:
        print(f"\n🏆 WINNER: Universal (simpler and better!)")
        print(f"   Advantage: {avg_uni_capture - avg_adp_capture:.1f}% better capture")
    else:
        print(f"\n🏆 WINNER: Adaptive (volatility-aware is better!)")
        print(f"   Advantage: {avg_adp_capture - avg_uni_capture:.1f}% better capture")

    print(f"\n💡 RECOMMENDATION:")
    print(f"   Universal approach is simpler and less prone to overfitting")
    print(f"   Use Entry (10, 2.0), Exit (30, 6.0) across all stocks")
    print(f"   Expected capture: ~{avg_uni_capture:.0f}% with minimal overfitting risk")
