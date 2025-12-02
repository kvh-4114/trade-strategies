"""
Generate CSV of Current Open Positions with Trading Recommendations
Base position: $1,000 (not $10,000)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuration
RESULTS_DIR = Path('results')
HIST_DATA_DIR = Path(r"C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_22_25_daily")
BASE_POSITION = 1000.0  # $1,000 base instead of $10,000

def resample_to_4day(df):
    """Resample to 4-day bars with epoch origin"""
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()

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
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2

    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2

    ha_high = df[['high']].values.flatten()
    ha_low = df[['low']].values.flatten()

    for i in range(len(df)):
        ha_high[i] = max(df['high'].iloc[i], ha_open[i], ha_close.iloc[i])
        ha_low[i] = min(df['low'].iloc[i], ha_open[i], ha_close.iloc[i])

    return pd.DataFrame({
        'ha_open': ha_open,
        'ha_high': ha_high,
        'ha_low': ha_low,
        'ha_close': ha_close
    })

def calculate_current_slope(ha_closes, period=5):
    """Calculate current slope as % per bar"""
    if len(ha_closes) < period:
        return None
    y = ha_closes[-period:]
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    avg_price = np.mean(y)
    return (slope / avg_price) * 100 if avg_price > 0 else 0

def get_current_data(symbol):
    """Get current price and slopes for a symbol"""
    csv_file = HIST_DATA_DIR / f"{symbol}_trades_[11_22_25_daily].csv"

    if not csv_file.exists():
        return None, None, None

    try:
        # Load and resample
        df_daily = pd.read_csv(csv_file)
        df_daily['date'] = pd.to_datetime(df_daily['date'])
        df_4day = resample_to_4day(df_daily)

        # Calculate HA
        df_ha = calculate_heikin_ashi(df_4day)
        df_4day = pd.concat([df_4day, df_ha], axis=1)

        # Get current price (last close)
        current_price = df_4day['close'].iloc[-1]

        # Calculate current entry slope (5-period on HA close)
        current_entry_slope = calculate_current_slope(df_4day['ha_close'].values, 5)

        # Calculate current exit slope (21-period on HA close)
        current_exit_slope = calculate_current_slope(df_4day['ha_close'].values, 21)

        return current_price, current_entry_slope, current_exit_slope

    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return None, None, None

def get_position_size(slope):
    """Get recommended position size based on current slope"""
    if slope is None or slope < 1.0:
        return 0, 0.0, "SKIP"
    elif slope >= 5.0:
        return 2000, 2.0, "High Conviction"
    elif slope >= 3.0:
        return 1500, 1.5, "Above Average"
    elif slope >= 2.0:
        return 1200, 1.2, "Average"
    else:  # >= 1.0
        return 1000, 1.0, "Base"

print("="*100)
print("GENERATING CURRENT POSITIONS CSV")
print("="*100)
print()

# Load trades
df = pd.read_csv(RESULTS_DIR / 'trades_with_slopes_2.2a_20251118_203658.csv')
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['exit_date'] = pd.to_datetime(df['exit_date'])

# Filter to open positions with >= 1.0% entry slope
df_open = df[(df['status'] == 'OPEN') & (df['entry_slope_5p_0la'] >= 1.0)].copy()

print(f"Processing {len(df_open)} open positions...")
print()

# Group by symbol to handle initial + pyramid entries
symbol_positions = {}

for idx, row in df_open.iterrows():
    symbol = row['symbol']

    if symbol not in symbol_positions:
        symbol_positions[symbol] = {
            'entries': [],
            'total_shares': 0,
            'avg_entry_price': 0,
            'entry_slope': row['entry_slope_5p_0la']
        }

    symbol_positions[symbol]['entries'].append({
        'type': row['entry_type'],
        'date': row['entry_date'],
        'price': row['entry_price'],
        'shares': row['size']
    })

    symbol_positions[symbol]['total_shares'] += row['size']

# Build output data
output_rows = []
processed = 0

for symbol, position_data in symbol_positions.items():
    processed += 1

    if processed % 20 == 0:
        print(f"Processed {processed}/{len(symbol_positions)} symbols...")

    # Get current data
    current_price, current_entry_slope, current_exit_slope = get_current_data(symbol)

    if current_price is None:
        continue

    # Get position sizing recommendation
    rec_size, multiplier, rec_level = get_position_size(current_entry_slope)
    rec_shares = int(rec_size / current_price) if rec_size > 0 else 0

    # Sort entries by date
    entries = sorted(position_data['entries'], key=lambda x: x['date'])

    # Build entry info strings
    if len(entries) == 1:
        entry_dates = entries[0]['date'].strftime('%Y-%m-%d')
        entry_prices = f"${entries[0]['price']:.2f}"
        entry_types = entries[0]['type']
    else:
        entry_dates = ' | '.join([e['date'].strftime('%Y-%m-%d') for e in entries])
        entry_prices = ' | '.join([f"${e['price']:.2f}" for e in entries])
        entry_types = ' | '.join([e['type'] for e in entries])

    # Calculate average entry price
    total_cost = sum([e['price'] * e['shares'] for e in entries])
    total_shares = sum([e['shares'] for e in entries])
    avg_entry_price = total_cost / total_shares if total_shares > 0 else 0

    # Calculate unrealized P&L
    unrealized_pnl = (current_price - avg_entry_price) * total_shares
    unrealized_pnl_pct = ((current_price - avg_entry_price) / avg_entry_price * 100) if avg_entry_price > 0 else 0

    # Check if exit signal likely (current price vs exit trend)
    exit_signal_risk = "YES" if current_exit_slope and current_exit_slope < -1.0 else "NO"

    output_rows.append({
        'Symbol': symbol,
        'Entry_Type': entry_types,
        'Entry_Date': entry_dates,
        'Entry_Price': entry_prices,
        'Avg_Entry_Price': f"${avg_entry_price:.2f}",
        'Current_Price': f"${current_price:.2f}",
        'Entry_Slope_Original': f"{position_data['entry_slope']:.2f}%",
        'Entry_Slope_Current': f"{current_entry_slope:.2f}%" if current_entry_slope else "N/A",
        'Exit_Slope_Current': f"{current_exit_slope:.2f}%" if current_exit_slope else "N/A",
        'Unrealized_PnL': f"${unrealized_pnl:.2f}",
        'Unrealized_PnL_Pct': f"{unrealized_pnl_pct:.1f}%",
        'Exit_Signal_Risk': exit_signal_risk,
        'Recommended_Level': rec_level,
        'Recommended_Multiplier': f"{multiplier:.1f}x",
        'Recommended_Position_Size': f"${rec_size}",
        'Recommended_Shares': rec_shares,
        'Current_Holdings_Shares': total_shares,
        'Holdings_vs_Recommendation': f"{(total_shares / rec_shares * 100):.0f}%" if rec_shares > 0 else "N/A"
    })

# Create DataFrame and save
df_output = pd.DataFrame(output_rows)

# Sort by recommended position size (descending), then by current entry slope (descending)
df_output['sort_size'] = df_output['Recommended_Position_Size'].str.replace('$', '').astype(float)
df_output['sort_slope'] = df_output['Entry_Slope_Current'].str.replace('%', '').replace('N/A', '0').astype(float)
df_output = df_output.sort_values(['sort_size', 'sort_slope'], ascending=[False, False])
df_output = df_output.drop(['sort_size', 'sort_slope'], axis=1)

# Save CSV
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = RESULTS_DIR / f'current_positions_trading_plan_{timestamp}.csv'
df_output.to_csv(output_file, index=False)

print()
print("="*100)
print("SUMMARY")
print("="*100)
print(f"Total Positions: {len(df_output)}")
print()
print("By Recommendation Level:")
for level in ['High Conviction', 'Above Average', 'Average', 'Base', 'SKIP']:
    count = len(df_output[df_output['Recommended_Level'] == level])
    if count > 0:
        print(f"  {level}: {count} positions")

print()
print("Exit Signal Risk:")
print(f"  High Risk (negative exit slope): {len(df_output[df_output['Exit_Signal_Risk'] == 'YES'])} positions")
print(f"  Low Risk: {len(df_output[df_output['Exit_Signal_Risk'] == 'NO'])} positions")

print()
print("="*100)
print(f"[SAVED] {output_file}")
print("="*100)
print()

# Display top 10 recommendations
print("TOP 10 TRADING RECOMMENDATIONS:")
print()
print(df_output.head(10)[['Symbol', 'Current_Price', 'Entry_Slope_Current', 'Recommended_Level',
                           'Recommended_Shares', 'Exit_Signal_Risk']].to_string(index=False))
print()
