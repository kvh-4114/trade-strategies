"""
Debug Supertrend strategy on NVDA to verify trades execute properly
Check for commission-related order rejections
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

class SupertrendDebug(bt.Strategy):
    """Debug version with detailed logging"""

    params = (
        ('atr_period', 30),
        ('atr_multiplier', 6.0),
        ('position_size', 10000),
        ('stop_loss_type', 'fixed_pct'),
        ('stop_loss_value', -0.10),
        ('profit_target', None),
    )

    def __init__(self):
        self.supertrend = Supertrend(
            self.data,
            period=self.params.atr_period,
            multiplier=self.params.atr_multiplier
        )
        self.entry_price = None
        self.order = None
        self.trade_num = 0

    def log(self, txt):
        print(f'{self.data.datetime.date(0)}: {txt}')

    def next(self):
        if self.order:
            return

        cash = self.broker.get_cash()
        portfolio_value = self.broker.getvalue()
        close = self.data.close[0]
        direction = self.supertrend.direction[0]

        if not self.position:
            # BUY LOGIC
            if direction == 1:
                # Calculate size WITHOUT commission adjustment
                size_no_comm = int(self.params.position_size / close)
                cost_no_comm = size_no_comm * close
                comm_no_comm = cost_no_comm * 0.001
                total_no_comm = cost_no_comm + comm_no_comm

                # Calculate size WITH commission adjustment
                size_with_comm = int(self.params.position_size / (close * 1.001))
                cost_with_comm = size_with_comm * close
                comm_with_comm = cost_with_comm * 0.001
                total_with_comm = cost_with_comm + comm_with_comm

                self.log(f'BUY SIGNAL - Cash: ${cash:,.2f}, Close: ${close:.2f}')
                self.log(f'  NO COMM ADJ: size={size_no_comm:,}, cost=${cost_no_comm:,.2f}, comm=${comm_no_comm:.2f}, total=${total_no_comm:,.2f}')
                self.log(f'  WITH COMM ADJ: size={size_with_comm:,}, cost=${cost_with_comm:,.2f}, comm=${comm_with_comm:.2f}, total=${total_with_comm:,.2f}')

                # Use the CURRENT calculation (no commission adjustment)
                self.order = self.buy(size=size_no_comm)

        else:
            # SELL LOGIC
            profit_pct = (close - self.entry_price) / self.entry_price if self.entry_price else 0

            exit_reason = None

            # Check stop loss
            if self.params.stop_loss_type == 'fixed_pct' and self.params.stop_loss_value:
                if profit_pct <= self.params.stop_loss_value:
                    exit_reason = f'Stop loss ({profit_pct:.1%})'

            # Check profit target
            if self.params.profit_target and profit_pct >= self.params.profit_target:
                exit_reason = f'Profit target ({profit_pct:.1%})'

            # Check trend reversal
            if len(self) > 1 and direction == -1 and self.supertrend.direction[-1] == 1:
                exit_reason = 'Trend reversal'

            if exit_reason:
                position_value = self.position.size * close
                self.log(f'SELL SIGNAL: {exit_reason} - Position: {self.position.size:,} shares, Value: ${position_value:,.2f}, Profit: {profit_pct:.1%}')
                self.order = self.sell(size=self.position.size)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.trade_num += 1
                self.entry_price = order.executed.price
                self.log(f'BUY EXECUTED #{self.trade_num}: Price=${order.executed.price:.2f}, Size={order.executed.size:,}, Cost=${order.executed.value:,.2f}, Comm=${order.executed.comm:.2f}')
                self.log(f'  Cash after: ${self.broker.get_cash():,.2f}, Portfolio: ${self.broker.getvalue():,.2f}')
            elif order.issell():
                profit = order.executed.value - (self.entry_price * order.executed.size)
                self.log(f'SELL EXECUTED #{self.trade_num}: Price=${order.executed.price:.2f}, Size={order.executed.size:,}, Value=${order.executed.value:,.2f}, Comm=${order.executed.comm:.2f}')
                self.log(f'  Profit: ${profit:,.2f}, Cash after: ${self.broker.get_cash():,.2f}, Portfolio: ${self.broker.getvalue():,.2f}')
                self.entry_price = None

        elif order.status in [order.Rejected, order.Margin]:
            self.log(f'❌ ORDER REJECTED - Status: {order.getstatusname()}, Size: {order.created.size:,}')

        self.order = None

# Load data
df = pd.read_csv('data/raw/NVDA_daily.csv',
                 names=['date', 'open', 'high', 'low', 'close', 'volume'],
                 parse_dates=['date'])
df = df.sort_values('date')

print(f"="*80)
print(f"NVDA Supertrend Strategy Debug")
print(f"="*80)
print(f"Data range: {df['date'].min()} to {df['date'].max()}")
print(f"First close: ${df.iloc[0]['close']:.2f}")
print(f"Last close: ${df.iloc[-1]['close']:.2f}")
print(f"Buy-hold return: {((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']) * 100:.2f}%")
print(f"\nStrategy: ATR 30, Mult 6.0, 10% SL, No PT")
print(f"="*80)
print()

cerebro = bt.Cerebro()
cerebro.adddata(PandasData(dataname=df))
cerebro.addstrategy(SupertrendDebug)

cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)

start_value = cerebro.broker.getvalue()
results = cerebro.run()
end_value = cerebro.broker.getvalue()

print()
print(f"="*80)
print(f"FINAL RESULTS")
print(f"="*80)
print(f"Starting Value: ${start_value:,.2f}")
print(f"Ending Value: ${end_value:,.2f}")
print(f"Total Return: {((end_value - start_value) / start_value) * 100:.2f}%")
print(f"="*80)
