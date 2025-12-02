"""
Simple Supertrend test using downloaded NVDA data
"""

import sys
import os
import pandas as pd
import backtrader as bt

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from agents.agent_2_strategy_core.supertrend import Supertrend

# Download NVDA data
print("Downloading NVDA data...")
try:
    import yfinance as yf
    nvda = yf.Ticker("NVDA")
    df = nvda.history(period="max", interval="1d")

    # Convert to required format
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
    df['date'] = pd.to_datetime(df['date'])
    print(f"Downloaded {len(df)} bars from {df['date'].min()} to {df['date'].max()}")

except Exception as e:
    print(f"Error downloading data: {e}")
    print("Using sample data instead...")

    # Create sample data if download fails
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'open': range(100, 200),
        'high': range(101, 201),
        'low': range(99, 199),
        'close': range(100, 200),
        'volume': [1000000] * 100
    })

# Create Backtrader data feed
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

# Test Config 1: ATR 14, Multiplier 3.0
print("\n" + "="*80)
print("CONFIG 1: ATR Period 14, Multiplier 3.0")
print("="*80)

cerebro = bt.Cerebro(runonce=False)  # Disable runonce to see debug output

# Add data
data = PandasData(dataname=df)
cerebro.adddata(data)

# Create a simple observer strategy to print Supertrend values
class SupertrendPrinter(bt.Strategy):
    def __init__(self):
        print("=== Strategy.__init__ called ===")
        self.supertrend = Supertrend(self.data, period=14, multiplier=3.0)
        print("=== Supertrend indicator created ===")

    def prenext(self):
        print(f"prenext() bar {len(self)}: Waiting for minimum period...")

    def next(self):
        # Check if Supertrend values are actually calculated or just default
        st_val = self.supertrend.supertrend[0]
        dir_val = self.supertrend.direction[0]
        upper = self.supertrend.final_upper[0]
        lower = self.supertrend.final_lower[0]

        if len(self) == 15 or len(self) == 20 or len(self) == 50:
            print(f"\nDETAILED CHECK bar {len(self)}:")
            print(f"  close=${self.data.close[0]:.2f}")
            print(f"  supertrend={st_val}")
            print(f"  direction={dir_val}")
            print(f"  final_upper={upper}")
            print(f"  final_lower={lower}")
            print()

cerebro.addstrategy(SupertrendPrinter)
cerebro.run()

print("\n" + "="*80)
print("If you see direction change messages above, the Supertrend is working!")
print("="*80)
