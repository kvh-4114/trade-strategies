"""
Test that _nextforce = True makes next() get called
"""

import backtrader as bt


class TestIndicator(bt.Indicator):
    """Test indicator with _nextforce"""

    lines = ('test_line',)
    params = (('period', 5),)

    # THIS IS THE KEY
    _nextforce = True

    def __init__(self):
        print("=== TestIndicator.__init__ called ===")
        self.addminperiod(self.params.period)
        self.call_count = 0

    def nextstart(self):
        print(f"=== nextstart() called at bar {len(self)} ===")
        self.lines.test_line[0] = 100.0
        self.call_count += 1

    def next(self):
        print(f"=== next() called at bar {len(self)} ===")
        self.lines.test_line[0] = 200.0 + len(self)
        self.call_count += 1


class TestStrategy(bt.Strategy):
    def __init__(self):
        print("=== Strategy.__init__ called ===")
        self.test_ind = TestIndicator(self.data)

    def prenext(self):
        print(f"Strategy.prenext() bar {len(self)}")

    def next(self):
        val = self.test_ind.test_line[0]
        print(f"Strategy.next() bar {len(self)}: test_line = {val}")


if __name__ == '__main__':
    import pandas as pd

    # Create simple test data
    dates = pd.date_range('2020-01-01', periods=20, freq='D')
    df = pd.DataFrame({
        'open': range(100, 120),
        'high': range(101, 121),
        'low': range(99, 119),
        'close': range(100, 120),
        'volume': [1000000] * 20
    }, index=dates)

    cerebro = bt.Cerebro()

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(TestStrategy)

    print("\n" + "="*80)
    print("Testing _nextforce = True")
    print("="*80 + "\n")

    cerebro.run()

    print("\n" + "="*80)
    print("If you see 'next() called' messages above, _nextforce works!")
    print("="*80)
