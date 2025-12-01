"""
Calculate entry slopes for all trades in baseline_trades CSV
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Constants
ENTRY_LR_PERIOD = 13
ENTRY_LR_LOOKAHEAD = 0
SLOPE_CALC_PERIOD = 5
SLOPE_CALC_LOOKAHEAD = 0

def resample_to_4day(df):
    """Resample daily data to 4-day bars with epoch origin"""
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    resampled = df.resample('4D', origin='epoch').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    return resampled.reset_index()

def calculate_heikin_ashi(df):
    """Calculate Heikin Ashi candles"""
    ha_df = df.copy()

    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2

    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2

    ha_high = df[['high', 'open', 'close']].max(axis=1)
    ha_low = df[['low', 'open', 'close']].min(axis=1)

    ha_df['ha_open'] = ha_open
    ha_df['ha_high'] = ha_high
    ha_df['ha_low'] = ha_low
    ha_df['ha_close'] = ha_close

    return ha_df

def calculate_linreg_slope(prices, period, lookahead=0):
    """Calculate linear regression slope as % per bar"""
    if len(prices) < period:
        return None

    y = prices[-period:]
    x = np.arange(len(y))

    # Fit linear regression
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]

    # Convert to percentage per bar
    avg_price = np.mean(y)
    slope_pct = (slope / avg_price) * 100

    return slope_pct

def calculate_slope_at_entry(symbol, entry_date, hist_data_dir):
    """Calculate slope at entry point for a trade"""

    # Load daily data
    csv_file = hist_data_dir / f"{symbol}_trades_[11_22_25_daily].csv"

    if not csv_file.exists():
        return None

    try:
        df_daily = pd.read_csv(csv_file)
        df_daily['date'] = pd.to_datetime(df_daily['date'])

        # Resample to 4-day bars
        df_4day = resample_to_4day(df_daily)

        # Calculate Heikin Ashi
        df_ha = calculate_heikin_ashi(df_4day)

        # Find entry bar
        entry_date = pd.to_datetime(entry_date)
        entry_bars = df_ha[df_ha['date'] <= entry_date]

        if len(entry_bars) < SLOPE_CALC_PERIOD + 5:
            return None

        # Calculate slope at entry
        entry_idx = len(entry_bars) - 1
        ha_closes = df_ha['ha_close'].iloc[:entry_idx+1].values

        if len(ha_closes) < SLOPE_CALC_PERIOD:
            return None

        slope = calculate_linreg_slope(ha_closes, SLOPE_CALC_PERIOD, SLOPE_CALC_LOOKAHEAD)

        return slope

    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return None

def main():
    print("\n" + "=" * 100)
    print("CALCULATE ENTRY SLOPES FOR ALL TRADES")
    print("=" * 100)
    print()

    # Find latest baseline trades file
    trades_file = Path("results/baseline_trades_20251119_071733.csv")

    if not trades_file.exists():
        print(f"ERROR: Trades file not found: {trades_file}")
        return

    print(f"Loading trades from: {trades_file}")
    df_trades = pd.read_csv(trades_file)
    print(f"Total trades: {len(df_trades):,}")
    print()

    # Historical data directory
    hist_data_dir = Path(r"C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_22_25_daily")

    if not hist_data_dir.exists():
        print(f"ERROR: Historical data directory not found: {hist_data_dir}")
        return

    print("Calculating entry slopes for all trades...")
    print()

    # Calculate slope for each trade
    # Optimization: Group by symbol to load data only once per symbol
    print("Optimizing: Processing by symbol to reduce I/O...")
    
    # Create a dictionary to store slopes: index -> slope
    slope_map = {}
    failed = 0
    
    # Get unique symbols
    symbols = df_trades['symbol'].unique()
    print(f"Processing {len(symbols)} symbols...")
    
    for i, symbol in enumerate(symbols):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(symbols)} symbols processed...")
            
        # Get all trades for this symbol
        symbol_indices = df_trades[df_trades['symbol'] == symbol].index
        
        # Load data once
        csv_file = hist_data_dir / f"{symbol}_trades_[11_22_25_daily].csv"
        if not csv_file.exists():
            print(f"  WARNING: Data file not found for {symbol}")
            failed += len(symbol_indices)
            continue
            
        try:
            df_daily = pd.read_csv(csv_file)
            df_daily['date'] = pd.to_datetime(df_daily['date'])
            
            # Resample to 4-day bars
            df_4day = resample_to_4day(df_daily)
            
            # Calculate Heikin Ashi
            df_ha = calculate_heikin_ashi(df_4day)
            
            # Process each trade for this symbol
            for idx in symbol_indices:
                entry_date = pd.to_datetime(df_trades.loc[idx, 'entry_date'])
                
                # Find entry bar
                entry_bars = df_ha[df_ha['date'] <= entry_date]
                
                if len(entry_bars) < SLOPE_CALC_PERIOD + 5:
                    failed += 1
                    continue
                    
                # Calculate slope at entry
                entry_idx = len(entry_bars) - 1
                ha_closes = df_ha['ha_close'].iloc[:entry_idx+1].values
                
                if len(ha_closes) < SLOPE_CALC_PERIOD:
                    failed += 1
                    continue
                    
                slope = calculate_linreg_slope(ha_closes, SLOPE_CALC_PERIOD, SLOPE_CALC_LOOKAHEAD)
                
                if slope is not None:
                    slope_map[idx] = slope
                else:
                    failed += 1
                    
        except Exception as e:
            print(f"  Error processing {symbol}: {e}")
            failed += len(symbol_indices)

    # Map slopes back to dataframe
    print("Mapping slopes to dataframe...")
    df_trades['entry_slope_5p_0la'] = df_trades.index.map(slope_map)

    print()
    print("=" * 100)
    print(f"COMPLETE")
    print("=" * 100)
    print(f"Trades with slopes calculated: {len(df_trades) - failed:,}")
    print(f"Failed calculations: {failed:,}")
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path("results") / f"trades_with_slopes_2.2a_{timestamp}.csv"
    df_trades.to_csv(output_file, index=False)

    print(f"[SAVED] {output_file}")
    print()

    # Show slope distribution
    df_with_slopes = df_trades[df_trades['entry_slope_5p_0la'].notna()]

    print("Slope Distribution:")
    print(f"  Mean: {df_with_slopes['entry_slope_5p_0la'].mean():.2f}%")
    print(f"  Median: {df_with_slopes['entry_slope_5p_0la'].median():.2f}%")
    print(f"  Std Dev: {df_with_slopes['entry_slope_5p_0la'].std():.2f}%")
    print()
    print(f"  Min: {df_with_slopes['entry_slope_5p_0la'].min():.2f}%")
    print(f"  Max: {df_with_slopes['entry_slope_5p_0la'].max():.2f}%")
    print()

    # Slope ranges
    print("Slope Ranges:")
    print(f"  < 0.0%: {len(df_with_slopes[df_with_slopes['entry_slope_5p_0la'] < 0.0]):,} trades")
    print(f"  0.0-1.0%: {len(df_with_slopes[(df_with_slopes['entry_slope_5p_0la'] >= 0.0) & (df_with_slopes['entry_slope_5p_0la'] < 1.0)]):,} trades")
    print(f"  1.0-2.0%: {len(df_with_slopes[(df_with_slopes['entry_slope_5p_0la'] >= 1.0) & (df_with_slopes['entry_slope_5p_0la'] < 2.0)]):,} trades")
    print(f"  2.0-3.0%: {len(df_with_slopes[(df_with_slopes['entry_slope_5p_0la'] >= 2.0) & (df_with_slopes['entry_slope_5p_0la'] < 3.0)]):,} trades")
    print(f"  3.0-5.0%: {len(df_with_slopes[(df_with_slopes['entry_slope_5p_0la'] >= 3.0) & (df_with_slopes['entry_slope_5p_0la'] < 5.0)]):,} trades")
    print(f"  >= 5.0%: {len(df_with_slopes[df_with_slopes['entry_slope_5p_0la'] >= 5.0]):,} trades")
    print()

if __name__ == "__main__":
    main()
