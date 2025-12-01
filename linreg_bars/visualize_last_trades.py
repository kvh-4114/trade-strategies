"""
Visualize Last 25 Trades
Show 4-day bars (both natural and Heikin Ashi) with LinReg and entry/exit points
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Constants
BASE_POSITION_SIZE = 10000
ENTRY_LR_PERIOD = 13
ENTRY_LR_LOOKAHEAD = 0
EXIT_LR_PERIOD = 21
EXIT_LR_LOOKAHEAD = -3

def calculate_slope_allocation_conservative(slope, base_size=BASE_POSITION_SIZE):
    """Conservative allocation - skip weak trades < 1.0%"""
    if slope >= 5.0:
        return base_size * 2.0
    elif slope >= 3.0:
        return base_size * 1.5
    elif slope >= 2.0:
        return base_size * 1.2
    elif slope >= 1.0:
        return base_size * 1.0
    else:
        return 0.0

def resample_to_4day(df):
    """Resample daily data to 4-day bars

    Uses origin='epoch' to ensure all symbols have identical bar boundaries.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Resample to 4-day bars with epoch origin for consistency
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

def calculate_linreg(prices, period, lookahead=0):
    """Calculate linear regression line"""
    if len(prices) < period:
        return None

    y = prices[-period:]
    x = np.arange(len(y))

    # Fit linear regression
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    intercept = coeffs[1]

    # Calculate line values
    line = slope * x + intercept

    # Apply lookahead
    if lookahead != 0:
        line = np.roll(line, lookahead)
        if lookahead > 0:
            line[:lookahead] = np.nan
        else:
            line[lookahead:] = np.nan

    return line

def plot_trade(trade, daily_data, output_path):
    """
    Create detailed chart for a single trade
    """
    symbol = trade['symbol']
    entry_date = pd.to_datetime(trade['entry_date'])
    exit_date = pd.to_datetime(trade['exit_date'])

    # Filter daily data around the trade
    start_date = entry_date - pd.Timedelta(days=200)  # Get context before trade
    end_date = exit_date + pd.Timedelta(days=40)  # Get context after trade

    df_daily = daily_data[
        (daily_data['date'] >= start_date) &
        (daily_data['date'] <= end_date)
    ].copy()

    if len(df_daily) < 50:
        print(f"  Insufficient data for {symbol}")
        return False

    # Resample to 4-day bars
    df_4day = resample_to_4day(df_daily)

    # Calculate Heikin Ashi
    df_ha = calculate_heikin_ashi(df_4day)

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

    title = (f"{symbol} - Trade from {entry_date.date()} to {exit_date.date()}\n"
             f"P&L: ${trade['pnl']:,.0f} | Slope: {trade['entry_slope_5p_0la']:.2f}% | "
             f"Position Size: {trade['position_size'] / BASE_POSITION_SIZE:.1f}x")
    fig.suptitle(title, fontsize=14, fontweight='bold')

    # Plot 1: Natural 4-Day Bars
    ax1.set_title('Natural 4-Day OHLC Bars', fontsize=12, fontweight='bold')

    for idx, row in df_4day.iterrows():
        date = row['date']
        x = idx

        # Candle body
        body_color = 'green' if row['close'] >= row['open'] else 'red'
        body_height = abs(row['close'] - row['open'])
        body_bottom = min(row['open'], row['close'])

        rect = Rectangle((x - 0.4, body_bottom), 0.8, body_height,
                         facecolor=body_color, edgecolor='black', alpha=0.8)
        ax1.add_patch(rect)

        # Wicks
        ax1.plot([x, x], [row['low'], row['high']], color='black', linewidth=1)

    # Add entry LinReg line (13-period, 0 lookahead)
    for i in range(ENTRY_LR_PERIOD, len(df_4day)):
        closes = df_4day['close'].iloc[i-ENTRY_LR_PERIOD:i].values
        lr_line = calculate_linreg(closes, ENTRY_LR_PERIOD, ENTRY_LR_LOOKAHEAD)
        if lr_line is not None:
            x_vals = np.arange(i-ENTRY_LR_PERIOD, i)
            ax1.plot(x_vals, lr_line, color='blue', linewidth=2, alpha=0.6, label='Entry LR (13p)' if i == ENTRY_LR_PERIOD else '')

    # Add exit LinReg line (21-period, -3 lookahead)
    for i in range(EXIT_LR_PERIOD, len(df_4day)):
        closes = df_4day['close'].iloc[i-EXIT_LR_PERIOD:i].values
        lr_line = calculate_linreg(closes, EXIT_LR_PERIOD, EXIT_LR_LOOKAHEAD)
        if lr_line is not None:
            x_vals = np.arange(i-EXIT_LR_PERIOD, i)
            # Apply lookahead shift
            x_vals = x_vals + EXIT_LR_LOOKAHEAD
            valid_mask = ~np.isnan(lr_line)
            ax1.plot(x_vals[valid_mask], lr_line[valid_mask], color='orange', linewidth=2, alpha=0.6,
                    label='Exit LR (21p, -3la)' if i == EXIT_LR_PERIOD else '')

    # Mark entry and exit points
    entry_idx = df_4day[df_4day['date'] <= entry_date].index[-1] if len(df_4day[df_4day['date'] <= entry_date]) > 0 else 0
    exit_idx = df_4day[df_4day['date'] <= exit_date].index[-1] if len(df_4day[df_4day['date'] <= exit_date]) > 0 else len(df_4day)-1

    entry_price = df_4day.loc[entry_idx, 'close']
    exit_price = df_4day.loc[exit_idx, 'close']

    ax1.scatter([entry_idx], [entry_price], color='green', s=200, marker='^',
               edgecolor='black', linewidth=2, zorder=5, label='Entry')
    ax1.scatter([exit_idx], [exit_price], color='red', s=200, marker='v',
               edgecolor='black', linewidth=2, zorder=5, label='Exit')

    ax1.set_ylabel('Price ($)', fontsize=10, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle=':')
    ax1.legend(loc='upper left', fontsize=9)

    # Plot 2: Heikin Ashi 4-Day Bars
    ax2.set_title('Heikin Ashi 4-Day Bars', fontsize=12, fontweight='bold')

    for idx, row in df_ha.iterrows():
        date = row['date']
        x = idx

        # HA Candle body
        body_color = 'green' if row['ha_close'] >= row['ha_open'] else 'red'
        body_height = abs(row['ha_close'] - row['ha_open'])
        body_bottom = min(row['ha_open'], row['ha_close'])

        rect = Rectangle((x - 0.4, body_bottom), 0.8, body_height,
                         facecolor=body_color, edgecolor='black', alpha=0.8)
        ax2.add_patch(rect)

        # HA Wicks
        ax2.plot([x, x], [row['ha_low'], row['ha_high']], color='black', linewidth=1)

    # Add entry LinReg line on HA closes
    for i in range(ENTRY_LR_PERIOD, len(df_ha)):
        ha_closes = df_ha['ha_close'].iloc[i-ENTRY_LR_PERIOD:i].values
        lr_line = calculate_linreg(ha_closes, ENTRY_LR_PERIOD, ENTRY_LR_LOOKAHEAD)
        if lr_line is not None:
            x_vals = np.arange(i-ENTRY_LR_PERIOD, i)
            ax2.plot(x_vals, lr_line, color='blue', linewidth=2, alpha=0.6, label='Entry LR (13p)' if i == ENTRY_LR_PERIOD else '')

    # Add exit LinReg line on HA closes
    for i in range(EXIT_LR_PERIOD, len(df_ha)):
        ha_closes = df_ha['ha_close'].iloc[i-EXIT_LR_PERIOD:i].values
        lr_line = calculate_linreg(ha_closes, EXIT_LR_PERIOD, EXIT_LR_LOOKAHEAD)
        if lr_line is not None:
            x_vals = np.arange(i-EXIT_LR_PERIOD, i)
            x_vals = x_vals + EXIT_LR_LOOKAHEAD
            valid_mask = ~np.isnan(lr_line)
            ax2.plot(x_vals[valid_mask], lr_line[valid_mask], color='orange', linewidth=2, alpha=0.6,
                    label='Exit LR (21p, -3la)' if i == EXIT_LR_PERIOD else '')

    # Mark entry and exit on HA chart
    ha_entry_price = df_ha.loc[entry_idx, 'ha_close']
    ha_exit_price = df_ha.loc[exit_idx, 'ha_close']

    ax2.scatter([entry_idx], [ha_entry_price], color='green', s=200, marker='^',
               edgecolor='black', linewidth=2, zorder=5, label='Entry')
    ax2.scatter([exit_idx], [ha_exit_price], color='red', s=200, marker='v',
               edgecolor='black', linewidth=2, zorder=5, label='Exit')

    ax2.set_xlabel('Bar Index', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Price ($)', fontsize=10, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle=':')
    ax2.legend(loc='upper left', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight')
    plt.close()

    return True

def main():
    print("\n" + "=" * 100)
    print("VISUALIZE LAST 25 TRADES")
    print("=" * 100)
    print()

    # Load conservative allocation trades
    results_dir = Path("results")
    csv_files = sorted(results_dir.glob("trades_with_slopes_2.2a_*.csv"))

    if not csv_files:
        print("ERROR: No trades file found!")
        return

    csv_file = csv_files[-1]
    print(f"Loading: {csv_file}")
    df_trades = pd.read_csv(csv_file)

    # Apply conservative allocation filter
    df_trades['position_size'] = df_trades['entry_slope_5p_0la'].apply(
        calculate_slope_allocation_conservative
    )
    df_conservative = df_trades[df_trades['position_size'] > 0].copy()

    # Get last 25 trades
    df_conservative['exit_date'] = pd.to_datetime(df_conservative['exit_date'])
    df_last_25 = df_conservative.nlargest(25, 'exit_date')

    print(f"Found {len(df_last_25)} recent trades")
    print()

    # Create output directory
    charts_dir = results_dir / "trade_charts"
    charts_dir.mkdir(exist_ok=True)

    # Load historical data directory
    hist_data_dir = Path(r"C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_22_25_daily")

    if not hist_data_dir.exists():
        print(f"ERROR: Historical data directory not found: {hist_data_dir}")
        return

    print(f"Loading data from: {hist_data_dir}")
    print()

    # Process each trade
    successful = 0
    for i, (idx, trade) in enumerate(df_last_25.iterrows(), 1):
        symbol = trade['symbol']
        print(f"[{i}/25] Processing {symbol}...")

        # Find data file (uses special naming pattern)
        csv_file = hist_data_dir / f"{symbol}_trades_[11_22_25_daily].csv"

        if not csv_file.exists():
            print(f"  Data file not found: {csv_file}")
            continue

        # Load daily data
        try:
            df_daily = pd.read_csv(csv_file)
            df_daily['date'] = pd.to_datetime(df_daily['date'])

            # Create chart
            exit_date_str = pd.to_datetime(trade['exit_date']).strftime('%Y-%m-%d')
            output_path = charts_dir / f"trade_{i:02d}_{symbol}_{exit_date_str}.png"

            if plot_trade(trade, df_daily, output_path):
                print(f"  [SAVED] {output_path.name}")
                successful += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    print()
    print("=" * 100)
    print(f"COMPLETE: Generated {successful}/25 trade charts")
    print(f"Charts saved to: {charts_dir}")
    print("=" * 100)

if __name__ == "__main__":
    main()
