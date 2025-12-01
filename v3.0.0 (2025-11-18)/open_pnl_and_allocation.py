"""
OPEN P&L ANALYSIS & SLOPE-BASED CAPITAL ALLOCATION
===================================================

1. Charts open/unrealized P&L for every bar (mark-to-market)
2. Tests slope-based capital allocation strategies

AUTHOR: Slope Threshold Experiments
DATE: November 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
from typing import Dict, List, Tuple

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

RESULTS_DIR = 'results'
INITIAL_CASH = 1000000.0
BASE_POSITION_SIZE = 10000.0


def load_trades_with_slopes(exp_id='2.2a'):
    """Load trades with slope data"""
    import glob
    pattern = os.path.join(RESULTS_DIR, f'trades_with_slopes_{exp_id}_*.csv')
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"No trades file found for {exp_id}")

    latest = max(files, key=os.path.getmtime)
    print(f"Loading: {latest}")

    df = pd.read_csv(latest, parse_dates=['entry_date', 'exit_date'])
    return df


def simulate_open_pnl_timeline(df_trades, position_size=BASE_POSITION_SIZE, slope_threshold=-999.0, slope_column='entry_slope_5p_0la'):
    """
    Simulate open P&L at every bar, tracking unrealized gains/losses.

    Returns DataFrame with daily open P&L, realized P&L, total P&L
    """
    # Filter by slope if applicable
    if slope_threshold > -999:
        df_trades = df_trades[df_trades[slope_column] >= slope_threshold].copy()

    print(f"  Analyzing {len(df_trades):,} trades...")

    # Get date range
    min_date = df_trades['entry_date'].min()
    max_date = df_trades['exit_date'].max()

    # Create daily timeline (4-day bars, but we'll track daily for granularity)
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

    open_pnl_list = []
    realized_pnl_list = []
    cash_list = []
    num_open_positions = []

    cash = INITIAL_CASH
    cumulative_realized_pnl = 0

    for date in all_dates:
        # Get positions open on this date
        open_positions = df_trades[
            (df_trades['entry_date'] <= date) &
            (df_trades['exit_date'] > date)
        ].copy()

        # Calculate open P&L for these positions
        # We need to estimate their current value
        # Simplification: Linear interpolation of P&L between entry and exit
        open_pnl = 0
        for _, trade in open_positions.iterrows():
            days_held = (date - trade['entry_date']).days
            total_days = (trade['exit_date'] - trade['entry_date']).days

            if total_days > 0:
                # Linear interpolation of P&L
                pnl_ratio = days_held / total_days
                estimated_pnl = trade['pnl'] * pnl_ratio
                open_pnl += estimated_pnl

        # Get realized P&L from trades that closed today
        closed_today = df_trades[df_trades['exit_date'] == date]
        realized_today = closed_today['pnl'].sum()

        # Update cash
        cash += realized_today

        # Track cumulative realized
        cumulative_realized_pnl += realized_today

        open_pnl_list.append(open_pnl)
        realized_pnl_list.append(cumulative_realized_pnl)
        cash_list.append(cash)
        num_open_positions.append(len(open_positions))

    df_timeline = pd.DataFrame({
        'date': all_dates,
        'open_pnl': open_pnl_list,
        'realized_pnl': realized_pnl_list,
        'total_pnl': np.array(open_pnl_list) + np.array(realized_pnl_list),
        'cash': cash_list,
        'num_open_positions': num_open_positions,
        'portfolio_value': np.array(cash_list) + np.array(open_pnl_list)
    })

    return df_timeline


def calculate_slope_allocation(slope, base_size=BASE_POSITION_SIZE, conservative=False):
    """
    Calculate position size based on slope.

    Allocation tiers (standard):
    - Slope >= 5.0%: 2.0x (very strong)
    - Slope >= 3.0%: 1.5x (strong)
    - Slope >= 2.0%: 1.2x (good)
    - Slope >= 1.0%: 1.0x (baseline)
    - Slope >= 0.5%: 0.7x (weak but positive)
    - Slope >= 0.0%: 0.4x (very weak)
    - Slope < 0.0%: 0.0x (skip)

    Allocation tiers (conservative - no weak/very weak):
    - Slope >= 5.0%: 2.0x (very strong)
    - Slope >= 3.0%: 1.5x (strong)
    - Slope >= 2.0%: 1.2x (good)
    - Slope >= 1.0%: 1.0x (baseline)
    - Slope < 1.0%: 0.0x (skip)
    """
    if conservative:
        # Conservative mode: Skip anything below 1.0%
        if slope >= 5.0:
            return base_size * 2.0
        elif slope >= 3.0:
            return base_size * 1.5
        elif slope >= 2.0:
            return base_size * 1.2
        elif slope >= 1.0:
            return base_size * 1.0
        else:
            return 0.0  # Skip weak trades
    else:
        # Standard mode: Include weak trades with reduced sizing
        if slope >= 5.0:
            return base_size * 2.0
        elif slope >= 3.0:
            return base_size * 1.5
        elif slope >= 2.0:
            return base_size * 1.2
        elif slope >= 1.0:
            return base_size * 1.0
        elif slope >= 0.5:
            return base_size * 0.7
        elif slope >= 0.0:
            return base_size * 0.4
        else:
            return 0.0  # Skip negative slope


def simulate_allocation_strategy(df_trades, slope_column='entry_slope_5p_0la', conservative=False):
    """
    Simulate portfolio with slope-based capital allocation.

    Args:
        conservative: If True, skip trades with slope < 1.0%
    """
    mode_str = "CONSERVATIVE (skip < 1.0%)" if conservative else "STANDARD (include weak)"
    print(f"  Simulating slope-based allocation ({mode_str})...")

    # Calculate position size for each trade based on slope
    df_trades = df_trades.copy()
    df_trades['position_size'] = df_trades[slope_column].apply(
        lambda x: calculate_slope_allocation(x, conservative=conservative)
    )
    df_trades['allocation_multiplier'] = df_trades['position_size'] / BASE_POSITION_SIZE

    # Filter out trades with zero allocation (negative slope)
    df_active = df_trades[df_trades['position_size'] > 0].copy()

    # Calculate scaled P&L based on position size
    df_active['scaled_pnl'] = df_active['pnl'] * df_active['allocation_multiplier']

    # Get date range
    min_date = df_active['entry_date'].min()
    max_date = df_active['exit_date'].max()
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')

    # Simulate timeline
    portfolio_values = []
    cash = INITIAL_CASH
    cumulative_pnl = 0

    for date in all_dates:
        # Realized P&L from closed trades
        closed_today = df_active[df_active['exit_date'] == date]
        realized_today = closed_today['scaled_pnl'].sum()

        cash += realized_today
        cumulative_pnl += realized_today

        # Open positions
        open_positions = df_active[
            (df_active['entry_date'] <= date) &
            (df_active['exit_date'] > date)
        ]

        # Estimate open P&L (linear interpolation)
        open_pnl = 0
        for _, trade in open_positions.iterrows():
            days_held = (date - trade['entry_date']).days
            total_days = (trade['exit_date'] - trade['entry_date']).days

            if total_days > 0:
                pnl_ratio = days_held / total_days
                estimated_pnl = trade['scaled_pnl'] * pnl_ratio
                open_pnl += estimated_pnl

        portfolio_value = cash + open_pnl
        portfolio_values.append(portfolio_value)

    df_timeline = pd.DataFrame({
        'date': all_dates,
        'portfolio_value': portfolio_values
    })

    # Calculate metrics
    total_pnl = df_active['scaled_pnl'].sum()
    num_trades = len(df_active)
    avg_pnl = total_pnl / num_trades if num_trades > 0 else 0

    # Allocation distribution
    allocation_dist = df_active['allocation_multiplier'].value_counts().sort_index()

    metrics = {
        'total_pnl': total_pnl,
        'num_trades': num_trades,
        'avg_pnl': avg_pnl,
        'final_value': portfolio_values[-1] if portfolio_values else INITIAL_CASH,
        'allocation_distribution': allocation_dist,
        'timeline': df_timeline,
        'trades': df_active
    }

    return metrics


def create_open_pnl_charts(baseline_timeline, filtered_timeline, allocation_timeline, save_path=None):
    """
    Create comprehensive charts showing open P&L and allocation strategies.
    """
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(4, 2, hspace=0.35, wspace=0.3)

    # 1. Total P&L (Open + Realized) - Main comparison
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(baseline_timeline['date'], baseline_timeline['total_pnl'] / 1e6,
             label='Baseline (No Filter)', linewidth=2, alpha=0.8, color='steelblue')
    ax1.plot(filtered_timeline['date'], filtered_timeline['total_pnl'] / 1e6,
             label='Slope Filter (5p/2.0%)', linewidth=2, alpha=0.8, color='orange')
    ax1.plot(allocation_timeline['date'],
             (allocation_timeline['portfolio_value'] - INITIAL_CASH) / 1e6,
             label='Slope Allocation (Variable Sizing)', linewidth=2, alpha=0.8, color='green')

    ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Total P&L ($M)', fontsize=12, fontweight='bold')
    ax1.set_title('Total P&L Over Time: Open + Realized (Mark-to-Market)',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)

    # 2. Open P&L Only - Shows unrealized gains/losses
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(baseline_timeline['date'], baseline_timeline['open_pnl'] / 1e6,
             label='Baseline', linewidth=1.5, alpha=0.7, color='steelblue')
    ax2.plot(filtered_timeline['date'], filtered_timeline['open_pnl'] / 1e6,
             label='Slope Filter', linewidth=1.5, alpha=0.7, color='orange')

    ax2.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Open P&L ($M)', fontsize=11, fontweight='bold')
    ax2.set_title('Unrealized P&L (Open Positions Only)', fontsize=13, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)

    # 3. Realized P&L Only - Cumulative closed trades
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(baseline_timeline['date'], baseline_timeline['realized_pnl'] / 1e6,
             label='Baseline', linewidth=1.5, alpha=0.7, color='steelblue')
    ax3.plot(filtered_timeline['date'], filtered_timeline['realized_pnl'] / 1e6,
             label='Slope Filter', linewidth=1.5, alpha=0.7, color='orange')

    ax3.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Realized P&L ($M)', fontsize=11, fontweight='bold')
    ax3.set_title('Realized P&L (Closed Trades Only)', fontsize=13, fontweight='bold')
    ax3.legend(loc='best', fontsize=10)
    ax3.grid(True, alpha=0.3)

    # 4. Portfolio Value Comparison
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.plot(baseline_timeline['date'], baseline_timeline['portfolio_value'] / 1e6,
             label='Baseline', linewidth=2, alpha=0.8, color='steelblue')
    ax4.plot(filtered_timeline['date'], filtered_timeline['portfolio_value'] / 1e6,
             label='Slope Filter', linewidth=2, alpha=0.8, color='orange')
    ax4.plot(allocation_timeline['date'], allocation_timeline['portfolio_value'] / 1e6,
             label='Slope Allocation', linewidth=2, alpha=0.8, color='green')

    ax4.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Portfolio Value ($M)', fontsize=11, fontweight='bold')
    ax4.set_title('Portfolio Value (Cash + Open P&L)', fontsize=13, fontweight='bold')
    ax4.legend(loc='best', fontsize=10)
    ax4.grid(True, alpha=0.3)

    # 5. Number of Open Positions
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.plot(baseline_timeline['date'], baseline_timeline['num_open_positions'],
             label='Baseline', linewidth=1.5, alpha=0.7, color='steelblue')
    ax5.plot(filtered_timeline['date'], filtered_timeline['num_open_positions'],
             label='Slope Filter', linewidth=1.5, alpha=0.7, color='orange')

    ax5.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax5.set_ylabel('Number of Open Positions', fontsize=11, fontweight='bold')
    ax5.set_title('Open Positions Over Time', fontsize=13, fontweight='bold')
    ax5.legend(loc='best', fontsize=10)
    ax5.grid(True, alpha=0.3)

    # 6. Open vs Realized P&L Ratio (Baseline)
    ax6 = fig.add_subplot(gs[3, 0])
    baseline_total = baseline_timeline['open_pnl'] + baseline_timeline['realized_pnl']
    baseline_total[baseline_total == 0] = 1  # Avoid division by zero
    baseline_open_pct = (baseline_timeline['open_pnl'] / baseline_total) * 100

    ax6.plot(baseline_timeline['date'], baseline_open_pct,
             linewidth=1.5, alpha=0.7, color='steelblue')
    ax6.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax6.set_ylabel('% of Total P&L', fontsize=11, fontweight='bold')
    ax6.set_title('Baseline: Open P&L as % of Total P&L', fontsize=13, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    ax6.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax6.axhline(y=50, color='red', linestyle=':', alpha=0.3)

    # 7. Open vs Realized P&L Ratio (Filtered)
    ax7 = fig.add_subplot(gs[3, 1])
    filtered_total = filtered_timeline['open_pnl'] + filtered_timeline['realized_pnl']
    filtered_total[filtered_total == 0] = 1
    filtered_open_pct = (filtered_timeline['open_pnl'] / filtered_total) * 100

    ax7.plot(filtered_timeline['date'], filtered_open_pct,
             linewidth=1.5, alpha=0.7, color='orange')
    ax7.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax7.set_ylabel('% of Total P&L', fontsize=11, fontweight='bold')
    ax7.set_title('Slope Filter: Open P&L as % of Total P&L', fontsize=13, fontweight='bold')
    ax7.grid(True, alpha=0.3)
    ax7.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax7.axhline(y=50, color='red', linestyle=':', alpha=0.3)

    plt.suptitle('Open P&L Analysis & Slope-Based Capital Allocation',
                 fontsize=16, fontweight='bold', y=0.995)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n[SAVED] Open P&L chart: {save_path}")
    else:
        plt.show()

    return fig


def create_allocation_analysis_chart(allocation_metrics, baseline_metrics, filtered_metrics, save_path=None):
    """
    Create detailed allocation strategy analysis.
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Slope-Based Capital Allocation Strategy Analysis', fontsize=16, fontweight='bold')

    # 1. Allocation Distribution
    ax1 = axes[0, 0]
    alloc_dist = allocation_metrics['allocation_distribution']
    ax1.bar(alloc_dist.index, alloc_dist.values, color='green', alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Allocation Multiplier', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Number of Trades', fontsize=11, fontweight='bold')
    ax1.set_title('Distribution of Position Sizes', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')

    # Add labels
    for i, (mult, count) in enumerate(alloc_dist.items()):
        ax1.text(mult, count, f'{int(count):,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 2. Strategy Comparison
    ax2 = axes[0, 1]
    strategies = ['Baseline\n(No Filter)', 'Slope Filter\n(Binary)', 'Slope Allocation\n(Variable)']
    total_pnls = [
        baseline_metrics['total_pnl'],
        filtered_metrics['total_pnl'],
        allocation_metrics['total_pnl']
    ]
    num_trades = [
        baseline_metrics['num_trades'],
        filtered_metrics['num_trades'],
        allocation_metrics['num_trades']
    ]

    x = np.arange(len(strategies))
    width = 0.35

    ax2_twin = ax2.twinx()

    bars1 = ax2.bar(x - width/2, np.array(total_pnls) / 1e6, width,
                    label='Total P&L ($M)', color='steelblue', alpha=0.7)
    bars2 = ax2_twin.bar(x + width/2, num_trades, width,
                        label='# Trades', color='orange', alpha=0.7)

    ax2.set_xlabel('Strategy', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Total P&L ($M)', fontsize=11, fontweight='bold', color='steelblue')
    ax2_twin.set_ylabel('Number of Trades', fontsize=11, fontweight='bold', color='orange')
    ax2.set_title('Strategy Performance Comparison', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(strategies)
    ax2.tick_params(axis='y', labelcolor='steelblue')
    ax2_twin.tick_params(axis='y', labelcolor='orange')
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'${height:.2f}M',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    for bar in bars2:
        height = bar.get_height()
        ax2_twin.text(bar.get_x() + bar.get_width()/2., height,
                     f'{int(height):,}',
                     ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 3. Avg P&L per Trade
    ax3 = axes[1, 0]
    avg_pnls = [
        baseline_metrics['avg_pnl'],
        filtered_metrics['avg_pnl'],
        allocation_metrics['avg_pnl']
    ]

    bars = ax3.bar(strategies, avg_pnls, color=['steelblue', 'orange', 'green'], alpha=0.7)
    ax3.set_xlabel('Strategy', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Avg P&L per Trade ($)', fontsize=11, fontweight='bold')
    ax3.set_title('Average P&L per Trade', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'${height:.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 4. Efficiency Metrics
    ax4 = axes[1, 1]

    # Calculate efficiency (total P&L / num trades)
    efficiencies = [
        (baseline_metrics['total_pnl'] / baseline_metrics['num_trades']) if baseline_metrics['num_trades'] > 0 else 0,
        (filtered_metrics['total_pnl'] / filtered_metrics['num_trades']) if filtered_metrics['num_trades'] > 0 else 0,
        (allocation_metrics['total_pnl'] / allocation_metrics['num_trades']) if allocation_metrics['num_trades'] > 0 else 0
    ]

    pnl_per_100_trades = [e * 100 for e in efficiencies]

    bars = ax4.bar(strategies, pnl_per_100_trades, color=['steelblue', 'orange', 'green'], alpha=0.7)
    ax4.set_xlabel('Strategy', fontsize=11, fontweight='bold')
    ax4.set_ylabel('P&L per 100 Trades ($)', fontsize=11, fontweight='bold')
    ax4.set_title('Trading Efficiency', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')

    for bar in bars:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'${height/1000:.1f}k',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[SAVED] Allocation analysis: {save_path}")
    else:
        plt.show()

    return fig


def print_allocation_report(allocation_metrics, baseline_metrics, filtered_metrics):
    """Print detailed allocation strategy report"""

    print(f"\n{'='*100}")
    print("SLOPE-BASED CAPITAL ALLOCATION STRATEGY ANALYSIS")
    print(f"{'='*100}")

    print(f"\n{'ALLOCATION DISTRIBUTION':-^100}")
    print("\nPosition Size Multipliers:")
    print(f"{'Multiplier':<15} {'# Trades':<15} {'% of Trades':<15} {'Slope Range'}")
    print("-" * 100)

    alloc_dist = allocation_metrics['allocation_distribution'].sort_index(ascending=False)
    total_trades = alloc_dist.sum()

    slope_ranges = {
        2.0: ">= 5.0%",
        1.5: "3.0% - 5.0%",
        1.2: "2.0% - 3.0%",
        1.0: "1.0% - 2.0%",
        0.7: "0.5% - 1.0%",
        0.4: "0.0% - 0.5%"
    }

    for mult, count in alloc_dist.items():
        pct = (count / total_trades * 100) if total_trades > 0 else 0
        slope_range = slope_ranges.get(mult, "Unknown")
        print(f"{mult:<15.1f}x {count:<15,} {pct:<14.1f}% {slope_range}")

    print(f"\n{'STRATEGY COMPARISON':-^100}")
    print(f"\n{'Metric':<35} {'Baseline':<20} {'Slope Filter':<20} {'Slope Allocation':<20}")
    print("-" * 100)

    print(f"{'Total P&L':<35} ${baseline_metrics['total_pnl']:>17,.0f}  ${filtered_metrics['total_pnl']:>17,.0f}  ${allocation_metrics['total_pnl']:>17,.0f}")
    print(f"{'Number of Trades':<35} {baseline_metrics['num_trades']:>19,}  {filtered_metrics['num_trades']:>19,}  {allocation_metrics['num_trades']:>19,}")
    print(f"{'Avg P&L per Trade':<35} ${baseline_metrics['avg_pnl']:>18,.0f}  ${filtered_metrics['avg_pnl']:>18,.0f}  ${allocation_metrics['avg_pnl']:>18,.0f}")

    # Calculate improvements
    baseline_total = baseline_metrics['total_pnl']
    alloc_total_vs_baseline = ((allocation_metrics['total_pnl'] - baseline_total) / baseline_total * 100) if baseline_total != 0 else 0
    filter_total_vs_baseline = ((filtered_metrics['total_pnl'] - baseline_total) / baseline_total * 100) if baseline_total != 0 else 0

    alloc_trades_vs_baseline = ((allocation_metrics['num_trades'] - baseline_metrics['num_trades']) / baseline_metrics['num_trades'] * 100) if baseline_metrics['num_trades'] != 0 else 0
    filter_trades_vs_baseline = ((filtered_metrics['num_trades'] - baseline_metrics['num_trades']) / baseline_metrics['num_trades'] * 100) if baseline_metrics['num_trades'] != 0 else 0

    print(f"\n{'% Change vs Baseline':<35} {'Baseline':<20} {'Slope Filter':<20} {'Slope Allocation':<20}")
    print("-" * 100)
    print(f"{'Total P&L':<35} {'0.0%':>19}  {filter_total_vs_baseline:>18.1f}%  {alloc_total_vs_baseline:>18.1f}%")
    print(f"{'Number of Trades':<35} {'0.0%':>19}  {filter_trades_vs_baseline:>18.1f}%  {alloc_trades_vs_baseline:>18.1f}%")

    print(f"\n{'='*100}")
    print("KEY INSIGHTS")
    print(f"{'='*100}")

    if allocation_metrics['total_pnl'] > filtered_metrics['total_pnl']:
        improvement = ((allocation_metrics['total_pnl'] - filtered_metrics['total_pnl']) / filtered_metrics['total_pnl'] * 100)
        print(f"\n[+] Slope allocation beats binary filter by {improvement:.1f}% in total P&L")

    if allocation_metrics['num_trades'] > filtered_metrics['num_trades']:
        more_trades = allocation_metrics['num_trades'] - filtered_metrics['num_trades']
        print(f"[+] Allocation captures {more_trades:,} additional trades vs binary filter")

    if allocation_metrics['total_pnl'] > baseline_total:
        print(f"[+] Allocation beats baseline by ${allocation_metrics['total_pnl'] - baseline_total:,.0f}")

    print(f"\n[*] Allocation uses {len(alloc_dist)} different position sizes vs binary (2 sizes: 0x or 1x)")
    print(f"[*] Variable sizing allows capturing weak opportunities with reduced capital")

    print(f"\n{'='*100}\n")


def main():
    """Main execution"""

    print("\n" + "="*100)
    print("OPEN P&L ANALYSIS & SLOPE-BASED CAPITAL ALLOCATION")
    print("="*100)

    # Load trades
    print("\nLoading baseline trades...")
    df_baseline = load_trades_with_slopes('2.2a')  # 5-period slope (baseline)

    print("\nLoading 5-period slope trades...")
    df_filtered = load_trades_with_slopes('2.2a')  # 5-period slope

    # 1. Simulate baseline open P&L timeline
    print("\n" + "="*100)
    print("SIMULATING BASELINE OPEN P&L")
    print("="*100)
    baseline_timeline = simulate_open_pnl_timeline(df_baseline, slope_threshold=-999.0)
    baseline_metrics = {
        'total_pnl': baseline_timeline['total_pnl'].iloc[-1],
        'num_trades': len(df_baseline),
        'avg_pnl': df_baseline['pnl'].mean()
    }

    # 2. Simulate filtered open P&L timeline (5p/2.0%)
    print("\n" + "="*100)
    print("SIMULATING SLOPE FILTER OPEN P&L (5-PERIOD / 2.0%)")
    print("="*100)
    filtered_timeline = simulate_open_pnl_timeline(df_filtered, slope_threshold=2.0, slope_column='entry_slope_5p_0la')
    filtered_trades = df_filtered[df_filtered['entry_slope_5p_0la'] >= 2.0]
    filtered_metrics = {
        'total_pnl': filtered_trades['pnl'].sum(),
        'num_trades': len(filtered_trades),
        'avg_pnl': filtered_trades['pnl'].mean()
    }

    # 3. Simulate allocation strategies
    print("\n" + "="*100)
    print("SIMULATING SLOPE-BASED CAPITAL ALLOCATION")
    print("="*100)

    # Standard allocation (includes weak trades)
    allocation_std_metrics = simulate_allocation_strategy(df_filtered, slope_column='entry_slope_5p_0la', conservative=False)

    # Conservative allocation (skips weak trades < 1.0%)
    allocation_con_metrics = simulate_allocation_strategy(df_filtered, slope_column='entry_slope_5p_0la', conservative=True)

    # Print reports
    print("\n" + "="*100)
    print("STANDARD ALLOCATION (Includes Weak Trades)")
    print("="*100)
    print_allocation_report(allocation_std_metrics, baseline_metrics, filtered_metrics)

    print("\n" + "="*100)
    print("CONSERVATIVE ALLOCATION (Skips Trades < 1.0% Slope)")
    print("="*100)
    print_allocation_report(allocation_con_metrics, baseline_metrics, filtered_metrics)

    # Create charts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Chart 1: Open P&L comparison (using conservative allocation)
    chart1_path = os.path.join(RESULTS_DIR, f'open_pnl_analysis_{timestamp}.png')
    create_open_pnl_charts(baseline_timeline, filtered_timeline, allocation_con_metrics['timeline'], save_path=chart1_path)

    # Chart 2: Allocation strategy analysis (using conservative allocation)
    chart2_path = os.path.join(RESULTS_DIR, f'allocation_strategy_{timestamp}.png')
    create_allocation_analysis_chart(allocation_con_metrics, baseline_metrics, filtered_metrics, save_path=chart2_path)

    # Save allocation trade details (using conservative allocation)
    alloc_trades_path = os.path.join(RESULTS_DIR, f'allocation_trades_{timestamp}.csv')
    allocation_con_metrics['trades'].to_csv(alloc_trades_path, index=False)
    print(f"[SAVED] Allocation trades: {alloc_trades_path}")

    print("\n" + "="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)


if __name__ == '__main__':
    main()
