"""
Visualize New Entries from Last Bar
Creates detailed charts with natural + HA candles and LR lines
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
RESULTS_DIR = Path('results')
NEW_ENTRIES_DIR = Path('results/new_entries_charts')
NEW_ENTRIES_DIR.mkdir(exist_ok=True, parents=True)
HIST_DATA_DIR = Path(r"C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_22_25_daily")

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

def calculate_linreg(values, period, lookahead=0):
    """Calculate linear regression line"""
    if len(values) < period:
        return None

    y = values[-period:]
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)

    # Project to target point
    target_x = len(y) - 1 + lookahead
    return coeffs[0] * target_x + coeffs[1]

def create_entry_chart(symbol, entry_date, entry_price):
    """Create detailed chart for a new entry"""

    # Load data
    csv_file = HIST_DATA_DIR / f"{symbol}_trades_[11_22_25_daily].csv"
    if not csv_file.exists():
        print(f"  Data file not found for {symbol}")
        return False

    df_daily = pd.read_csv(csv_file)
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    df_daily = df_daily.sort_values('date').reset_index(drop=True)

    # Resample to 4-day bars
    df_daily_indexed = df_daily.set_index('date')
    df_4d = df_daily_indexed.resample('4D', origin='epoch').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()

    # Calculate Heikin Ashi
    ha_df = calculate_heikin_ashi(df_4d)
    df_4d = pd.concat([df_4d, ha_df], axis=1)

    # Get data from at least 90 days before entry
    entry_date = pd.to_datetime(entry_date)
    start_date = entry_date - timedelta(days=120)  # Extra buffer
    df_chart = df_4d[df_4d['date'] >= start_date].copy()

    if len(df_chart) < 10:
        print(f"  Not enough data for {symbol}")
        return False

    # Calculate LR lines for each bar
    entry_lr = []
    exit_lr = []

    for i in range(len(df_chart)):
        # Entry LR: 13-period, 0 lookahead
        if i >= 12:
            ha_closes = df_chart['ha_close'].iloc[:i+1]
            lr_val = calculate_linreg(ha_closes.values, 13, 0)
            entry_lr.append(lr_val)
        else:
            entry_lr.append(None)

        # Exit LR: 21-period, -3 lookahead
        if i >= 20:
            ha_closes = df_chart['ha_close'].iloc[:i+1]
            lr_val = calculate_linreg(ha_closes.values, 21, -3)
            exit_lr.append(lr_val)
        else:
            exit_lr.append(None)

    df_chart['entry_lr'] = entry_lr
    df_chart['exit_lr'] = exit_lr

    # Find entry bar
    matching = df_chart[df_chart['date'] == entry_date]
    if len(matching) == 0:
        # Find closest date
        closest_idx = (df_chart['date'] - entry_date).abs().idxmin()
        entry_idx = df_chart.index.get_loc(closest_idx)
    else:
        entry_idx = df_chart.index.get_loc(matching.index[0])

    # Create figure with 2 panels
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)

    title = f"{symbol} - New Entry on {entry_date.strftime('%Y-%m-%d')} @ ${entry_price:.2f}"
    fig.suptitle(title, fontsize=14, fontweight='bold')

    # Panel 1: Natural Candles
    for i in range(len(df_chart)):
        date = df_chart['date'].iloc[i]
        o, h, l, c = df_chart['open'].iloc[i], df_chart['high'].iloc[i], \
                     df_chart['low'].iloc[i], df_chart['close'].iloc[i]

        color = '#2ECC40' if c >= o else '#FF4136'
        ax1.plot([date, date], [l, h], color=color, linewidth=1, alpha=0.8)
        width = timedelta(days=2)
        ax1.add_patch(plt.Rectangle((date - width/2, min(o, c)), width, abs(c - o),
                                     facecolor=color, edgecolor=color, alpha=0.6))

    # Plot LR lines for natural candles
    valid_entry_lr = df_chart[df_chart['entry_lr'].notna()]
    valid_exit_lr = df_chart[df_chart['exit_lr'].notna()]

    if not valid_entry_lr.empty:
        ax1.plot(valid_entry_lr['date'], valid_entry_lr['entry_lr'],
                 color='blue', linewidth=2, label='Entry LR (13p, 0la)', alpha=0.7)
    if not valid_exit_lr.empty:
        ax1.plot(valid_exit_lr['date'], valid_exit_lr['exit_lr'],
                 color='red', linewidth=2, label='Exit LR (21p, -3la)', alpha=0.7)

    # Mark entry point
    ax1.scatter([df_chart['date'].iloc[entry_idx]], [entry_price],
                color='lime', s=200, marker='^', zorder=5,
                edgecolors='black', linewidths=2, label='Entry')

    ax1.set_ylabel('Price ($)', fontsize=11, fontweight='bold')
    ax1.set_title('Natural 4-Day Candles', fontsize=11, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Panel 2: Heikin Ashi Candles
    for i in range(len(df_chart)):
        date = df_chart['date'].iloc[i]
        o, h, l, c = df_chart['ha_open'].iloc[i], df_chart['ha_high'].iloc[i], \
                     df_chart['ha_low'].iloc[i], df_chart['ha_close'].iloc[i]

        color = '#2ECC40' if c >= o else '#FF4136'
        ax2.plot([date, date], [l, h], color=color, linewidth=1, alpha=0.8)
        width = timedelta(days=2)
        ax2.add_patch(plt.Rectangle((date - width/2, min(o, c)), width, abs(c - o),
                                     facecolor=color, edgecolor=color, alpha=0.6))

    # Plot LR lines for HA candles
    if not valid_entry_lr.empty:
        ax2.plot(valid_entry_lr['date'], valid_entry_lr['entry_lr'],
                 color='blue', linewidth=2, label='Entry LR (13p, 0la)', alpha=0.7)
    if not valid_exit_lr.empty:
        ax2.plot(valid_exit_lr['date'], valid_exit_lr['exit_lr'],
                 color='red', linewidth=2, label='Exit LR (21p, -3la)', alpha=0.7)

    # Mark entry point
    ax2.scatter([df_chart['date'].iloc[entry_idx]], [entry_price],
                color='lime', s=200, marker='^', zorder=5,
                edgecolors='black', linewidths=2, label='Entry')

    ax2.set_ylabel('Price ($)', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax2.set_title('Heikin Ashi 4-Day Candles', fontsize=11, fontweight='bold')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save chart
    filename = NEW_ENTRIES_DIR / f"entry_{symbol}_{entry_date.strftime('%Y%m%d')}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()

    return True

def create_html_viewer(symbols_info):
    """Create HTML viewer for new entry charts"""

    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>New Entries - November 20, 2025</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .summary {
            background-color: #fff;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }
        .chart-container {
            background-color: #fff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .chart-container h3 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
        }
        .chart-container img {
            width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .info {
            margin: 10px 0;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 4px;
        }
        .info span {
            font-weight: bold;
            color: #2c3e50;
        }
    </style>
</head>
<body>
    <h1>New Entries - November 20, 2025</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Entry Date:</strong> Thursday, November 20, 2025</p>
        <p><strong>Total New Positions:</strong> """ + str(len(symbols_info)) + """</p>
        <p><strong>Bar Type:</strong> 4-Day Bars (Natural + Heikin Ashi)</p>
        <p><strong>Entry Signal:</strong> HA Close crosses above 13-period LinReg (0 lookahead)</p>
        <p><strong>Exit Signal:</strong> HA Close crosses below 21-period LinReg (-3 lookahead)</p>
        <p><strong>History Shown:</strong> 90+ days prior to entry</p>
    </div>

    <div class="chart-grid">
"""

    for symbol, entry_price in symbols_info:
        html_content += f"""
        <div class="chart-container">
            <h3>{symbol}</h3>
            <div class="info">
                <span>Entry Price:</span> ${entry_price:.2f}
            </div>
            <img src="entry_{symbol}_20251120.png" alt="{symbol} Chart">
        </div>
"""

    html_content += """
    </div>

    <div class="summary" style="margin-top: 30px;">
        <h3>Chart Legend</h3>
        <ul>
            <li><strong>Green Candles:</strong> Close >= Open (bullish)</li>
            <li><strong>Red Candles:</strong> Close < Open (bearish)</li>
            <li><strong>Blue Line:</strong> Entry LinReg (13-period, 0 lookahead) - Fast/Responsive</li>
            <li><strong>Red Line:</strong> Exit LinReg (21-period, -3 lookahead) - Slow/Smooth</li>
            <li><strong>Green Triangle (^):</strong> Entry point</li>
        </ul>
        <p><strong>Note:</strong> Entry signal triggers when HA close crosses above the blue Entry LR line.</p>
    </div>

    <footer style="text-align: center; margin-top: 40px; color: #7f8c8d;">
        <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </footer>
</body>
</html>
"""

    html_file = NEW_ENTRIES_DIR / "new_entries_viewer.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_file

# Main execution
if __name__ == "__main__":
    print("="*80)
    print("VISUALIZE NEW ENTRIES - NOVEMBER 20, 2025")
    print("="*80)

    # Load baseline trades to get new entries
    baseline_file = sorted(RESULTS_DIR.glob('baseline_trades_*.csv'))[-1]
    print(f"\nLoading: {baseline_file}")

    df_trades = pd.read_csv(baseline_file)
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])

    # Get entries from Nov 20, 2025
    new_entries = df_trades[df_trades['entry_date'] == '2025-11-20'].copy()
    new_entries = new_entries.sort_values('symbol')

    print(f"Found {len(new_entries)} new entries on 2025-11-20")
    print()

    # Create charts
    successful = 0
    symbols_info = []

    for i, (idx, entry) in enumerate(new_entries.iterrows(), 1):
        symbol = entry['symbol']
        entry_date = entry['entry_date']
        entry_price = entry['entry_price']

        print(f"[{i}/{len(new_entries)}] Creating chart for {symbol}...")

        if create_entry_chart(symbol, entry_date, entry_price):
            print(f"  [SAVED]")
            successful += 1
            symbols_info.append((symbol, entry_price))
        else:
            print(f"  [FAILED]")

    print()
    print("="*80)
    print(f"COMPLETE: Generated {successful}/{len(new_entries)} charts")
    print(f"Charts saved to: {NEW_ENTRIES_DIR}")
    print("="*80)

    # Create HTML viewer
    if successful > 0:
        html_file = create_html_viewer(symbols_info)
        print(f"\n[SAVED] HTML Viewer: {html_file}")
        print(f"\nOpen this file in your web browser:")
        print(f"file:///{html_file.absolute()}")

    print()
