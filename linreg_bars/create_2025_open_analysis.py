"""
Create 2025 Open P&L and Unique Symbols Chart
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Load allocation trades
results_dir = Path('results')
trades_file = sorted(results_dir.glob('allocation_trades_*.csv'))[-1]

print(f"Loading: {trades_file}")
df = pd.read_csv(trades_file)

# Convert dates
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['exit_date'] = pd.to_datetime(df['exit_date'])

# Filter for 2025
start_2025 = pd.Timestamp('2025-01-01')
end_date = pd.Timestamp('2025-11-21')

# Create date range (trading days only, so we'll use the actual dates from trades)
all_dates = sorted(set(df['entry_date'].tolist() + df['exit_date'].tolist()))
dates_2025 = [d for d in all_dates if start_2025 <= d <= end_date]

# Calculate open P&L and unique symbols for each date
open_pnl_history = []
unique_symbols_history = []

for date in dates_2025:
    # Find trades that are open on this date
    open_trades = df[
        (df['entry_date'] <= date) &
        ((df['exit_date'] > date) | (df['status'] == 'OPEN'))
    ]

    # Calculate total open P&L
    # For closed trades, use the P&L at that point
    # For still-open trades, use current unrealized P&L
    total_open_pnl = 0
    unique_symbols = set()

    for _, trade in open_trades.iterrows():
        if trade['status'] == 'CLOSED':
            # Calculate what the P&L would have been at this date
            # (this is an approximation - we're using the final P&L)
            # In reality we'd need daily price data to be exact
            total_open_pnl += trade['pnl']
        else:
            # Still open - use current unrealized P&L
            total_open_pnl += trade['pnl']

        unique_symbols.add(trade['symbol'])

    open_pnl_history.append(total_open_pnl)
    unique_symbols_history.append(len(unique_symbols))

# Create the chart
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
fig.suptitle('2025 Open P&L and Unique Symbols Analysis', fontsize=16, fontweight='bold')

# Chart 1: Open P&L
ax1.plot(dates_2025, [pnl/1000 for pnl in open_pnl_history],
         color='#2E7D32', linewidth=2, label='Open P&L')
ax1.fill_between(dates_2025, 0, [pnl/1000 for pnl in open_pnl_history],
                  alpha=0.3, color='#2E7D32')
ax1.set_ylabel('Open P&L ($K)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# Add value label at end
final_pnl = open_pnl_history[-1]
ax1.text(dates_2025[-1], final_pnl/1000, f'${final_pnl/1000:.1f}K',
         fontsize=11, fontweight='bold', ha='right', va='bottom',
         bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

# Chart 2: Unique Open Symbols
ax2.plot(dates_2025, unique_symbols_history,
         color='#1976D2', linewidth=2, label='Unique Open Symbols')
ax2.fill_between(dates_2025, 0, unique_symbols_history,
                  alpha=0.3, color='#1976D2')
ax2.set_ylabel('Number of Unique Symbols', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper left')

# Add statistics box
avg_symbols = sum(unique_symbols_history) / len(unique_symbols_history)
max_symbols = max(unique_symbols_history)
min_symbols = min(unique_symbols_history)
current_symbols = unique_symbols_history[-1]

stats_text = f'Avg: {avg_symbols:.0f} | Max: {max_symbols} | Min: {min_symbols} | Current: {current_symbols}'
ax2.text(0.5, 0.95, stats_text, transform=ax2.transAxes,
         fontsize=10, fontweight='bold', ha='center', va='top',
         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

# Add value label at end
ax2.text(dates_2025[-1], current_symbols, f'{current_symbols}',
         fontsize=11, fontweight='bold', ha='right', va='bottom',
         bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

plt.tight_layout()

# Save
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = results_dir / f'2025_open_analysis_{timestamp}.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n[SAVED] {output_file}")

# Print summary
print("\n" + "="*80)
print("2025 OPEN ANALYSIS SUMMARY")
print("="*80)
print(f"\nOpen P&L:")
print(f"  Current: ${final_pnl:,.0f}")
print(f"  Peak: ${max(open_pnl_history):,.0f}")
print(f"  Average: ${sum(open_pnl_history)/len(open_pnl_history):,.0f}")

print(f"\nUnique Open Symbols:")
print(f"  Current: {current_symbols}")
print(f"  Average: {avg_symbols:.0f}")
print(f"  Max: {max_symbols}")
print(f"  Min: {min_symbols}")

print("\n" + "="*80)
