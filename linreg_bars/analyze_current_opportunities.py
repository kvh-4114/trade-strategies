"""
Analyze Current Open Positions for Trading Opportunities
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load current open positions
df = pd.read_csv('results/trades_with_slopes_2.2a_20251118_203658.csv')
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['exit_date'] = pd.to_datetime(df['exit_date'])

# Filter to conservative allocation and OPEN positions only
df_open = df[(df['entry_slope_5p_0la'] >= 1.0) & (df['status'] == 'OPEN')].copy()

# Calculate additional metrics
current_date = df_open['exit_date'].max()
df_open['days_in_trade'] = (df_open['exit_date'] - df_open['entry_date']).dt.days
df_open['pnl_pct'] = df_open['pnl_pct']
df_open['days_since_entry'] = (current_date - df_open['entry_date']).dt.days

# Position sizing multiplier based on entry slope
def get_multiplier(slope):
    if slope >= 5.0: return 2.0
    elif slope >= 3.0: return 1.5
    elif slope >= 2.0: return 1.2
    elif slope >= 1.0: return 1.0
    else: return 0.0

df_open['position_multiplier'] = df_open['entry_slope_5p_0la'].apply(get_multiplier)

print("="*100)
print("CURRENT OPEN POSITIONS ANALYSIS")
print(f"As of: {current_date.strftime('%Y-%m-%d')}")
print("="*100)
print(f"\nTotal Open Positions: {len(df_open):,}")
print(f"Total Unrealized P&L: ${df_open['pnl'].sum():,.0f}")
print(f"Average P&L per Position: ${df_open['pnl'].mean():,.0f}")
print()

# FACTOR 1: Most Recent Entries (Freshest Signals)
print("="*100)
print("FACTOR 1: MOST RECENT ENTRIES (Last 30 Days)")
print("="*100)
recent_entries = df_open[df_open['days_since_entry'] <= 30].nlargest(20, 'entry_date')
if len(recent_entries) > 0:
    print(f"\nFound {len(df_open[df_open['days_since_entry'] <= 30])} positions entered in last 30 days\n")
    print("Top 20 Most Recent:")
    print(recent_entries[['symbol', 'entry_date', 'entry_slope_5p_0la', 'pnl', 'pnl_pct', 'days_in_trade', 'position_multiplier']].to_string(index=False))
else:
    print("\nNo entries in last 30 days")
print()

# FACTOR 2: Highest Entry Slopes (Strongest Momentum at Entry)
print("="*100)
print("FACTOR 2: HIGHEST ENTRY SLOPES (Strongest Momentum)")
print("="*100)
top_slopes = df_open.nlargest(20, 'entry_slope_5p_0la')
print(f"\nTop 20 by Entry Slope:\n")
print(top_slopes[['symbol', 'entry_date', 'entry_slope_5p_0la', 'pnl', 'pnl_pct', 'days_in_trade', 'position_multiplier']].to_string(index=False))
print()

# FACTOR 3: Highest Current Open P&L
print("="*100)
print("FACTOR 3: HIGHEST CURRENT OPEN P&L (What's Working Now)")
print("="*100)
top_pnl = df_open.nlargest(20, 'pnl')
print(f"\nTop 20 by Current P&L:\n")
print(top_pnl[['symbol', 'entry_date', 'entry_slope_5p_0la', 'pnl', 'pnl_pct', 'days_in_trade', 'position_multiplier']].to_string(index=False))
print()

# FACTOR 4: Best P&L % (Efficiency)
print("="*100)
print("FACTOR 4: HIGHEST P&L PERCENTAGE (Most Efficient)")
print("="*100)
top_pnl_pct = df_open.nlargest(20, 'pnl_pct')
print(f"\nTop 20 by P&L %:\n")
print(top_pnl_pct[['symbol', 'entry_date', 'entry_slope_5p_0la', 'pnl', 'pnl_pct', 'days_in_trade', 'position_multiplier']].to_string(index=False))
print()

# FACTOR 5: Recent + High Slope + Positive P&L (Combined Score)
print("="*100)
print("FACTOR 5: COMPOSITE SCORE (Recent + High Slope + Winning)")
print("="*100)
df_open['recency_score'] = 1 / (1 + df_open['days_since_entry'] / 30)  # Decays over 30 days
df_open['slope_score'] = df_open['entry_slope_5p_0la'] / df_open['entry_slope_5p_0la'].max()
df_open['pnl_score'] = (df_open['pnl'] - df_open['pnl'].min()) / (df_open['pnl'].max() - df_open['pnl'].min())
df_open['composite_score'] = (
    df_open['recency_score'] * 0.3 + 
    df_open['slope_score'] * 0.4 + 
    df_open['pnl_score'] * 0.3
)
top_composite = df_open.nlargest(20, 'composite_score')
print("\nTop 20 by Composite Score (30% Recency, 40% Slope, 30% P&L):\n")
print(top_composite[['symbol', 'entry_date', 'entry_slope_5p_0la', 'pnl', 'pnl_pct', 'days_in_trade', 'composite_score']].to_string(index=False))
print()

# FACTOR 6: High Conviction (2.0x positions with positive P&L)
print("="*100)
print("FACTOR 6: HIGH CONVICTION WINNERS (2.0x Multiplier + Positive P&L)")
print("="*100)
high_conviction = df_open[(df_open['position_multiplier'] == 2.0) & (df_open['pnl'] > 0)].sort_values('pnl', ascending=False)
print(f"\nFound {len(high_conviction)} high conviction winners\n")
if len(high_conviction) > 0:
    print(high_conviction.head(20)[['symbol', 'entry_date', 'entry_slope_5p_0la', 'pnl', 'pnl_pct', 'days_in_trade']].to_string(index=False))
else:
    print("No high conviction winners found")
print()

# Summary Statistics by Position Multiplier
print("="*100)
print("POSITION BREAKDOWN BY CONVICTION LEVEL")
print("="*100)
for mult in [2.0, 1.5, 1.2, 1.0]:
    subset = df_open[df_open['position_multiplier'] == mult]
    if len(subset) > 0:
        print(f"\n{mult}x Positions (Slope >= {5.0 if mult==2.0 else 3.0 if mult==1.5 else 2.0 if mult==1.2 else 1.0}%):")
        print(f"  Count: {len(subset)}")
        print(f"  Avg P&L: ${subset['pnl'].mean():,.0f}")
        print(f"  Total P&L: ${subset['pnl'].sum():,.0f}")
        print(f"  Avg Days in Trade: {subset['days_in_trade'].mean():.0f}")
        print(f"  Win Rate: {len(subset[subset['pnl'] > 0]) / len(subset) * 100:.1f}%")

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
