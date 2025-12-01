"""
Create Trading Opportunity Charts
Top 10 from each category with detailed analysis
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
CHARTS_DIR = Path('results/opportunity_charts')
CHARTS_DIR.mkdir(exist_ok=True, parents=True)
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

def calculate_linreg(prices, period):
    """Calculate linear regression value"""
    if len(prices) < period:
        return None
    y = prices[-period:]
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    return coeffs[0] * (len(y) - 1) + coeffs[1]

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

def create_opportunity_chart(symbol, entry_date, exit_date, entry_price, current_pnl, entry_slope, position_mult, category, rank):
    """Create detailed trading opportunity chart"""

    # Load data
    csv_file = HIST_DATA_DIR / f"{symbol}_trades_[11_22_25_daily].csv"
    if not csv_file.exists():
        print(f"  Data file not found for {symbol}")
        return False

    df_daily = pd.read_csv(csv_file)
    df_daily['date'] = pd.to_datetime(df_daily['date'])

    # Resample to 4-day bars
    df_4day = resample_to_4day(df_daily)

    # Calculate HA candles
    df_ha = calculate_heikin_ashi(df_4day)
    df_4day = pd.concat([df_4day, df_ha], axis=1)

    # Determine date range (90 days or from entry, whichever is longer)
    entry_date = pd.to_datetime(entry_date)
    exit_date = pd.to_datetime(exit_date)
    days_since_entry = (exit_date - entry_date).days

    lookback_days = max(90, days_since_entry + 10)
    start_date = exit_date - timedelta(days=lookback_days)

    # Filter data
    df_chart = df_4day[df_4day['date'] >= start_date].copy()

    if len(df_chart) < 10:
        print(f"  Insufficient data for {symbol}")
        return False

    # Calculate LinReg for entry (13-period) and exit (21-period)
    entry_lr = []
    exit_lr = []

    for i in range(len(df_chart)):
        # Entry LR (13-period on HA close)
        if i >= 12:
            lr_val = calculate_linreg(df_chart['ha_close'].iloc[:i+1].values, 13)
            entry_lr.append(lr_val)
        else:
            entry_lr.append(None)

        # Exit LR (21-period on HA close)
        if i >= 20:
            lr_val = calculate_linreg(df_chart['ha_close'].iloc[:i+1].values, 21)
            exit_lr.append(lr_val)
        else:
            exit_lr.append(None)

    df_chart['entry_lr'] = entry_lr
    df_chart['exit_lr'] = exit_lr

    # Calculate current slope
    current_slope = calculate_current_slope(df_chart['ha_close'].values, 5)
    current_slope_str = f"{current_slope:.2f}%" if current_slope else "N/A"

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # Title with all key info
    pnl_str = f"${current_pnl:,.0f}" if current_pnl >= 0 else f"-${abs(current_pnl):,.0f}"
    pnl_pct = (current_pnl / (entry_price * 100)) * 100  # Assuming base position

    fig.suptitle(
        f"{category} #{rank}: {symbol}\n"
        f"Entry: {entry_date.strftime('%Y-%m-%d')} | "
        f"Current P&L: {pnl_str} ({pnl_pct:+.1f}%) | "
        f"Entry Slope: {entry_slope:.2f}% | Current Slope: {current_slope_str} | "
        f"Position: {position_mult:.1f}x",
        fontsize=12, fontweight='bold'
    )

    # Plot 1: Natural 4-Day Candles
    for idx, row in df_chart.iterrows():
        color = 'green' if row['close'] >= row['open'] else 'red'
        ax1.plot([row['date'], row['date']], [row['low'], row['high']], color='black', linewidth=0.5)
        ax1.plot([row['date'], row['date']], [row['open'], row['close']], color=color, linewidth=3)

    ax1.set_ylabel('Price ($)', fontsize=10)
    ax1.set_title('Natural 4-Day Candles', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Heikin Ashi Candles + LinReg
    for idx, row in df_chart.iterrows():
        color = 'green' if row['ha_close'] >= row['ha_open'] else 'red'
        ax2.plot([row['date'], row['date']], [row['ha_low'], row['ha_high']], color='black', linewidth=0.5)
        ax2.plot([row['date'], row['date']], [row['ha_open'], row['ha_close']], color=color, linewidth=3)

    # Plot LinReg lines
    ax2.plot(df_chart['date'], df_chart['entry_lr'], 'b-', linewidth=1.5, label='Entry LR (13-period)', alpha=0.7)
    ax2.plot(df_chart['date'], df_chart['exit_lr'], 'orange', linewidth=1.5, label='Exit LR (21-period)', alpha=0.7)

    # Mark entry point
    entry_idx = df_chart[df_chart['date'] <= entry_date].index[-1] if len(df_chart[df_chart['date'] <= entry_date]) > 0 else 0
    ax2.scatter(df_chart.loc[entry_idx, 'date'], entry_price, color='lime', s=150, marker='^',
                zorder=5, edgecolors='black', linewidths=2, label=f'Entry: ${entry_price:.2f}')

    ax2.set_xlabel('Date', fontsize=10)
    ax2.set_ylabel('Price ($)', fontsize=10)
    ax2.set_title('Heikin Ashi 4-Day Candles with Linear Regression', fontsize=10)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save
    filename = f"{category.lower().replace(' ', '_').replace('-', '_')}_{rank:02d}_{symbol}.png"
    filepath = CHARTS_DIR / filename
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()

    return True

# Main execution
print("="*100)
print("CREATING TRADING OPPORTUNITY CHARTS")
print("="*100)

df = pd.read_csv(RESULTS_DIR / 'trades_with_slopes_2.2a_20251118_203658.csv')
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['exit_date'] = pd.to_datetime(df['exit_date'])

# Filter to open positions with >= 1.0% slope
df_open = df[(df['status'] == 'OPEN') & (df['entry_slope_5p_0la'] >= 1.0)].copy()

# Add calculated fields
df_open['days_since_entry'] = (df_open['exit_date'].max() - df_open['entry_date']).dt.days

def get_multiplier(slope):
    if slope >= 5.0: return 2.0
    elif slope >= 3.0: return 1.5
    elif slope >= 2.0: return 1.2
    else: return 1.0

df_open['position_mult'] = df_open['entry_slope_5p_0la'].apply(get_multiplier)

# Category 1: Best High-Conviction Recent Entries
print("\nCategory 1: High-Conviction Recent Entries (2.0x, last 30 days)")
cat1 = df_open[(df_open['position_mult'] == 2.0) & (df_open['days_since_entry'] <= 30)].nlargest(10, 'entry_slope_5p_0la')
print(f"Selected {len(cat1)} positions\n")

# Category 2: Best Long-Term Winners Still Trending
print("Category 2: Long-Term Winners (100+ days, positive P&L)")
cat2 = df_open[(df_open['days_since_entry'] >= 100) & (df_open['pnl'] > 0)].nlargest(10, 'pnl')
print(f"Selected {len(cat2)} positions\n")

# Category 3: Highest Conviction Winners
print("Category 3: Highest Conviction Winners (2.0x, positive P&L)")
cat3 = df_open[(df_open['position_mult'] == 2.0) & (df_open['pnl'] > 0)].nlargest(10, 'pnl')
print(f"Selected {len(cat3)} positions\n")

# Generate charts
all_charts = []
categories = [
    ("High-Conviction Recent", cat1),
    ("Long-Term Winners", cat2),
    ("High-Conviction Winners", cat3)
]

for cat_name, cat_df in categories:
    print(f"\n{'='*100}")
    print(f"Generating charts for: {cat_name}")
    print(f"{'='*100}\n")

    for rank, (idx, row) in enumerate(cat_df.iterrows(), 1):
        symbol = row['symbol']
        print(f"[{rank}/10] {symbol}...", end=" ")

        success = create_opportunity_chart(
            symbol=symbol,
            entry_date=row['entry_date'],
            exit_date=row['exit_date'],
            entry_price=row['entry_price'],
            current_pnl=row['pnl'],
            entry_slope=row['entry_slope_5p_0la'],
            position_mult=row['position_mult'],
            category=cat_name,
            rank=rank
        )

        if success:
            print("Done")
            all_charts.append({
                'category': cat_name,
                'rank': rank,
                'symbol': symbol,
                'entry_date': row['entry_date'].strftime('%Y-%m-%d'),
                'pnl': row['pnl'],
                'pnl_pct': (row['pnl'] / (row['entry_price'] * 100)) * 100,
                'entry_slope': row['entry_slope_5p_0la'],
                'days_in_trade': row['days_since_entry'],
                'position_mult': row['position_mult'],
                'filename': f"{cat_name.lower().replace(' ', '_').replace('-', '_')}_{rank:02d}_{symbol}.png"
            })
        else:
            print("Failed")

# Create HTML viewer
print(f"\n{'='*100}")
print("Creating HTML Viewer")
print(f"{'='*100}\n")

html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Trading Opportunities - Top 30 Positions</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        h1 {{ color: white; text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; }}
        .category-section {{ margin-bottom: 50px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .category-title {{ font-size: 24px; font-weight: bold; color: #34495e; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #3498db; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 30px; margin-top: 20px; }}
        .chart-card {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .chart-info {{ margin-bottom: 15px; padding: 10px; background: #ecf0f1; border-radius: 5px; }}
        .chart-info h3 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .stat-row {{ display: flex; justify-content: space-between; margin: 5px 0; font-size: 14px; }}
        .positive {{ color: #27ae60; font-weight: bold; }}
        .negative {{ color: #e74c3c; font-weight: bold; }}
        img {{ width: 100%; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Trading Opportunities - Top 30 Positions</h1>
    <div style="text-align: center; background: #3498db; color: white; padding: 15px; border-radius: 8px; margin-bottom: 30px;">
        <h2>Portfolio Snapshot</h2>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

for cat_name, _ in categories:
    cat_charts = [c for c in all_charts if c['category'] == cat_name]
    html_content += f'<div class="category-section"><div class="category-title">{cat_name}</div><div class="grid">'

    for chart in cat_charts:
        pnl_class = 'positive' if chart['pnl'] >= 0 else 'negative'
        pnl_str = f"${chart['pnl']:,.0f}"
        html_content += f"""
        <div class="chart-card">
            <div class="chart-info">
                <h3>#{chart['rank']} - {chart['symbol']}</h3>
                <div class="stat-row"><span>Entry:</span><span>{chart['entry_date']}</span></div>
                <div class="stat-row"><span>P&L:</span><span class="{pnl_class}">{pnl_str} ({chart['pnl_pct']:+.1f}%)</span></div>
                <div class="stat-row"><span>Entry Slope:</span><span>{chart['entry_slope']:.2f}%</span></div>
                <div class="stat-row"><span>Days:</span><span>{chart['days_in_trade']}</span></div>
            </div>
            <img src="{chart['filename']}" alt="{chart['symbol']}">
        </div>
        """
    html_content += '</div></div>'

html_content += '</body></html>'

html_file = CHARTS_DIR / 'trading_opportunities.html'
with open(html_file, 'w') as f:
    f.write(html_content)

print(f"Complete: Generated {len(all_charts)} charts")
print(f"Open: {html_file.absolute()}")
