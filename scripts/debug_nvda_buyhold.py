"""
Debug NVDA buy-and-hold calculation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtrader as bt

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

class BuyAndHoldDebug(bt.Strategy):
    """Buy-and-hold with detailed logging"""

    def __init__(self):
        self.order = None
        self.bought = False

    def log(self, txt):
        print(f'{self.data.datetime.date(0)}: {txt}')

    def next(self):
        if not self.bought:
            cash = self.broker.get_cash()
            close = self.data.close[0]

            # ORIGINAL CALCULATION (without accounting for commission)
            size = int(cash / close)

            self.log(f'BUY ORDER - Cash: ${cash:,.2f}, Close: ${close:.2f}, Size: {size:,} shares')

            if size > 0:
                self.order = self.buy(size=size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.bought = True
                self.log(f'BUY EXECUTED - Price: ${order.executed.price:.2f}, '
                        f'Size: {order.executed.size:,}, '
                        f'Cost: ${order.executed.value:,.2f}, '
                        f'Comm: ${order.executed.comm:.2f}')
                self.log(f'Portfolio Value: ${self.broker.getvalue():,.2f}')
        elif order.status in [order.Rejected, order.Margin]:
            self.log(f'ORDER REJECTED - Status: {order.getstatusname()}, Size: {order.created.size:,}')

    def stop(self):
        final_value = self.broker.getvalue()
        cash = self.broker.get_cash()
        position_value = final_value - cash

        if self.position:
            shares = self.position.size
            final_price = self.data.close[0]
            self.log(f'FINAL - Shares: {shares:,}, Price: ${final_price:.2f}, '
                    f'Position Value: ${position_value:,.2f}')

        self.log(f'FINAL - Cash: ${cash:,.2f}, Total: ${final_value:,.2f}')

# Load NVDA data
df = pd.read_csv('data/raw/NVDA_daily.csv',
                 names=['date', 'open', 'high', 'low', 'close', 'volume'],
                 parse_dates=['date'])
df = df.sort_values('date')

print(f"Data range: {df['date'].min()} to {df['date'].max()}")
print(f"First close: ${df.iloc[0]['close']:.2f}")
print(f"Last close: ${df.iloc[-1]['close']:.2f}")
print(f"Raw return: {((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']) * 100:.2f}%")
print(f"Multiplier: {df.iloc[-1]['close'] / df.iloc[0]['close']:.2f}x")
print()

# Run backtest
cerebro = bt.Cerebro()
data = PandasData(dataname=df)
cerebro.adddata(data)
cerebro.addstrategy(BuyAndHoldDebug)

cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)

start_value = cerebro.broker.getvalue()
print(f"Starting Value: ${start_value:,.2f}")
print()

results = cerebro.run()

end_value = cerebro.broker.getvalue()
total_return = ((end_value - start_value) / start_value) * 100

print()
print(f"="*80)
print(f"Starting Value: ${start_value:,.2f}")
print(f"Ending Value: ${end_value:,.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"="*80)
