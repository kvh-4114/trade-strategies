"""
Conservative Allocation - Symbol Performance Analysis
Analyze best and worst performing symbols
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Constants
BASE_POSITION_SIZE = 10000

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

def analyze_symbols(df_trades):
    """
    Analyze performance by symbol
    """
    # Group by symbol and calculate metrics
    symbol_stats = []

    for symbol, trades in df_trades.groupby('symbol'):
        # Calculate weighted P&L
        position_mult = trades['position_size'] / BASE_POSITION_SIZE
        weighted_pnl = (trades['pnl'] * position_mult).sum()

        # Calculate statistics
        num_trades = len(trades)
        avg_pnl = trades['pnl'].mean()
        win_rate = (trades['pnl'] > 0).sum() / num_trades * 100
        avg_slope = trades['entry_slope_5p_0la'].mean()

        # Winning and losing trades
        winners = trades[trades['pnl'] > 0]
        losers = trades[trades['pnl'] <= 0]

        avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0

        # Calculate profit factor
        total_wins = winners['pnl'].sum() if len(winners) > 0 else 0
        total_losses = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else np.inf

        symbol_stats.append({
            'symbol': symbol,
            'total_pnl': weighted_pnl,
            'num_trades': num_trades,
            'avg_pnl': avg_pnl,
            'win_rate': win_rate,
            'avg_slope': avg_slope,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'num_winners': len(winners),
            'num_losers': len(losers)
        })

    df_symbols = pd.DataFrame(symbol_stats)
    df_symbols = df_symbols.sort_values('total_pnl', ascending=False).reset_index(drop=True)

    return df_symbols

def create_symbol_analysis_charts(df_best, df_worst, output_path):
    """
    Create comprehensive symbol analysis visualization
    """
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)

    fig.suptitle('Conservative Allocation - Top 25 Best & Worst Symbols',
                 fontsize=16, fontweight='bold', y=0.995)

    # 1. Best 25 Symbols - Total P&L
    ax1 = fig.add_subplot(gs[0, 0])
    y_pos = range(len(df_best))
    bars = ax1.barh(y_pos, df_best['total_pnl'] / 1000, color='#06A77D', alpha=0.8, edgecolor='black')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(df_best['symbol'], fontsize=8)
    ax1.set_xlabel('Total P&L ($K)', fontsize=10, fontweight='bold')
    ax1.set_title('Top 25 Symbols by Total P&L', fontsize=11, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3, linestyle=':', axis='x')
    ax1.invert_yaxis()

    # Add value labels
    for i, (pnl, trades) in enumerate(zip(df_best['total_pnl'], df_best['num_trades'])):
        ax1.text(pnl / 1000, i, f' ${pnl/1000:.0f}K ({trades})',
                va='center', fontsize=7, fontweight='bold')

    # 2. Worst 25 Symbols - Total P&L
    ax2 = fig.add_subplot(gs[0, 1])
    y_pos = range(len(df_worst))
    bars = ax2.barh(y_pos, df_worst['total_pnl'] / 1000, color='#D62828', alpha=0.8, edgecolor='black')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(df_worst['symbol'], fontsize=8)
    ax2.set_xlabel('Total P&L ($K)', fontsize=10, fontweight='bold')
    ax2.set_title('Bottom 25 Symbols by Total P&L', fontsize=11, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3, linestyle=':', axis='x')
    ax2.invert_yaxis()

    # Add value labels
    for i, (pnl, trades) in enumerate(zip(df_worst['total_pnl'], df_worst['num_trades'])):
        ax2.text(pnl / 1000, i, f' ${pnl/1000:.0f}K ({trades})',
                va='center', fontsize=7, fontweight='bold')

    # 3. Best 25 - Win Rate vs Avg P&L Scatter
    ax3 = fig.add_subplot(gs[1, 0])
    scatter = ax3.scatter(df_best['win_rate'], df_best['avg_pnl'],
                         s=df_best['num_trades']*2, alpha=0.6, c=df_best['total_pnl'],
                         cmap='Greens', edgecolors='black', linewidth=0.5)

    # Annotate top symbols
    for i in range(min(5, len(df_best))):
        ax3.annotate(df_best.iloc[i]['symbol'],
                    (df_best.iloc[i]['win_rate'], df_best.iloc[i]['avg_pnl']),
                    fontsize=7, ha='left', va='bottom')

    ax3.set_xlabel('Win Rate (%)', fontsize=10, fontweight='bold')
    ax3.set_ylabel('Avg P&L per Trade ($)', fontsize=10, fontweight='bold')
    ax3.set_title('Top 25: Win Rate vs Avg P&L (size = # trades)', fontsize=11, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3, linestyle=':')
    plt.colorbar(scatter, ax=ax3, label='Total P&L ($)')

    # 4. Worst 25 - Win Rate vs Avg P&L Scatter
    ax4 = fig.add_subplot(gs[1, 1])
    scatter = ax4.scatter(df_worst['win_rate'], df_worst['avg_pnl'],
                         s=df_worst['num_trades']*2, alpha=0.6, c=df_worst['total_pnl'],
                         cmap='Reds_r', edgecolors='black', linewidth=0.5)

    # Annotate worst symbols
    for i in range(min(5, len(df_worst))):
        ax4.annotate(df_worst.iloc[i]['symbol'],
                    (df_worst.iloc[i]['win_rate'], df_worst.iloc[i]['avg_pnl']),
                    fontsize=7, ha='left', va='bottom')

    ax4.set_xlabel('Win Rate (%)', fontsize=10, fontweight='bold')
    ax4.set_ylabel('Avg P&L per Trade ($)', fontsize=10, fontweight='bold')
    ax4.set_title('Bottom 25: Win Rate vs Avg P&L (size = # trades)', fontsize=11, fontweight='bold', pad=10)
    ax4.grid(True, alpha=0.3, linestyle=':')
    plt.colorbar(scatter, ax=ax4, label='Total P&L ($)')

    # 5. Statistics Comparison - Best 25
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.axis('off')

    best_stats = f"""
    TOP 25 SYMBOLS - STATISTICS
    {'='*45}

    Total Combined P&L:      ${df_best['total_pnl'].sum():>12,.0f}
    Total Trades:            {df_best['num_trades'].sum():>12,}

    Average Win Rate:        {df_best['win_rate'].mean():>12.1f}%
    Average P&L/Trade:       ${df_best['avg_pnl'].mean():>12,.0f}
    Average Slope:           {df_best['avg_slope'].mean():>12.2f}%

    Avg Profit Factor:       {df_best['profit_factor'].replace([np.inf], 10).mean():>12.2f}

    Best Symbol:             {df_best.iloc[0]['symbol']:>12}
    Best Total P&L:          ${df_best.iloc[0]['total_pnl']:>12,.0f}
    """

    ax5.text(0.1, 0.9, best_stats, fontsize=9, family='monospace',
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

    # 6. Statistics Comparison - Worst 25
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.axis('off')

    worst_stats = f"""
    BOTTOM 25 SYMBOLS - STATISTICS
    {'='*45}

    Total Combined P&L:      ${df_worst['total_pnl'].sum():>12,.0f}
    Total Trades:            {df_worst['num_trades'].sum():>12,}

    Average Win Rate:        {df_worst['win_rate'].mean():>12.1f}%
    Average P&L/Trade:       ${df_worst['avg_pnl'].mean():>12,.0f}
    Average Slope:           {df_worst['avg_slope'].mean():>12.2f}%

    Avg Profit Factor:       {df_worst['profit_factor'].replace([np.inf], 10).mean():>12.2f}

    Worst Symbol:            {df_worst.iloc[-1]['symbol']:>12}
    Worst Total P&L:         ${df_worst.iloc[-1]['total_pnl']:>12,.0f}
    """

    ax6.text(0.1, 0.9, worst_stats, fontsize=9, family='monospace',
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.3))

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] {output_path}")

def print_symbol_analysis(df_best, df_worst, df_all):
    """Print detailed symbol analysis"""

    print("\n" + "=" * 120)
    print("TOP 25 SYMBOLS BY TOTAL P&L")
    print("=" * 120)
    print(f"{'Rank':<6} {'Symbol':<10} {'Total P&L':<15} {'# Trades':<10} {'Avg P&L':<12} "
          f"{'Win Rate':<10} {'Avg Slope':<12} {'Profit Factor':<15}")
    print("-" * 120)

    for i, row in df_best.iterrows():
        pf = row['profit_factor'] if row['profit_factor'] != np.inf else 999.99
        print(f"{i+1:<6} {row['symbol']:<10} ${row['total_pnl']:<14,.0f} {row['num_trades']:<10} "
              f"${row['avg_pnl']:<11,.0f} {row['win_rate']:<9.1f}% {row['avg_slope']:<11.2f}% {pf:<15.2f}")

    print("-" * 120)
    print(f"{'TOTAL':<6} {'':<10} ${df_best['total_pnl'].sum():<14,.0f} "
          f"{df_best['num_trades'].sum():<10} ${df_best['avg_pnl'].mean():<11,.0f} "
          f"{df_best['win_rate'].mean():<9.1f}% {df_best['avg_slope'].mean():<11.2f}%")
    print("=" * 120)

    print("\n" + "=" * 120)
    print("BOTTOM 25 SYMBOLS BY TOTAL P&L")
    print("=" * 120)
    print(f"{'Rank':<6} {'Symbol':<10} {'Total P&L':<15} {'# Trades':<10} {'Avg P&L':<12} "
          f"{'Win Rate':<10} {'Avg Slope':<12} {'Profit Factor':<15}")
    print("-" * 120)

    for i, row in df_worst.iterrows():
        pf = row['profit_factor'] if row['profit_factor'] != np.inf else 999.99
        rank = len(df_all) - i
        print(f"{rank:<6} {row['symbol']:<10} ${row['total_pnl']:<14,.0f} {row['num_trades']:<10} "
              f"${row['avg_pnl']:<11,.0f} {row['win_rate']:<9.1f}% {row['avg_slope']:<11.2f}% {pf:<15.2f}")

    print("-" * 120)
    print(f"{'TOTAL':<6} {'':<10} ${df_worst['total_pnl'].sum():<14,.0f} "
          f"{df_worst['num_trades'].sum():<10} ${df_worst['avg_pnl'].mean():<11,.0f} "
          f"{df_worst['win_rate'].mean():<9.1f}% {df_worst['avg_slope'].mean():<11.2f}%")
    print("=" * 120)

    # Overall statistics
    print("\n" + "=" * 120)
    print("OVERALL STATISTICS")
    print("=" * 120)
    print(f"Total Symbols:                     {len(df_all):>10,}")
    print(f"Total Trades:                      {df_all['num_trades'].sum():>10,}")
    print(f"Total P&L:                         ${df_all['total_pnl'].sum():>10,.0f}")
    print()
    print(f"Top 25 Contribution:               ${df_best['total_pnl'].sum():>10,.0f}  "
          f"({df_best['total_pnl'].sum() / df_all['total_pnl'].sum() * 100:.1f}%)")
    print(f"Bottom 25 Contribution:            ${df_worst['total_pnl'].sum():>10,.0f}  "
          f"({df_worst['total_pnl'].sum() / df_all['total_pnl'].sum() * 100:.1f}%)")
    print()
    print(f"Positive Symbols:                  {(df_all['total_pnl'] > 0).sum():>10,}  "
          f"({(df_all['total_pnl'] > 0).sum() / len(df_all) * 100:.1f}%)")
    print(f"Negative Symbols:                  {(df_all['total_pnl'] < 0).sum():>10,}  "
          f"({(df_all['total_pnl'] < 0).sum() / len(df_all) * 100:.1f}%)")
    print("=" * 120)

def main():
    print("\n" + "=" * 120)
    print("CONSERVATIVE ALLOCATION - SYMBOL PERFORMANCE ANALYSIS")
    print("=" * 120)
    print()

    # Load trades with slopes
    results_dir = Path("results")
    csv_files = sorted(results_dir.glob("trades_with_slopes_2.2a_*.csv"))

    if not csv_files:
        print("ERROR: No trades_with_slopes_2.2a files found!")
        return

    csv_file = csv_files[-1]
    print(f"Loading: {csv_file}")
    df_trades = pd.read_csv(csv_file)
    print(f"Total trades loaded: {len(df_trades):,}")
    print()

    # Apply conservative allocation
    print("Applying conservative allocation (skip < 1.0% slope)...")
    df_trades['position_size'] = df_trades['entry_slope_5p_0la'].apply(
        calculate_slope_allocation_conservative
    )

    # Filter to only trades that pass the filter
    df_conservative = df_trades[df_trades['position_size'] > 0].copy()
    print(f"Trades after filter: {len(df_conservative):,}")
    print(f"Unique symbols: {df_conservative['symbol'].nunique():,}")
    print()

    # Analyze symbols
    print("Analyzing symbol performance...")
    df_symbols = analyze_symbols(df_conservative)

    # Get top 25 and bottom 25
    df_best_25 = df_symbols.head(25).copy()
    df_worst_25 = df_symbols.tail(25).copy().iloc[::-1].reset_index(drop=True)  # Reverse for plotting

    # Print analysis
    print_symbol_analysis(df_best_25, df_worst_25, df_symbols)

    # Create charts
    print("\nGenerating symbol analysis charts...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"conservative_symbol_analysis_{timestamp}.png"
    create_symbol_analysis_charts(df_best_25, df_worst_25, output_path)

    # Save data to CSV
    all_symbols_csv = results_dir / f"all_symbols_performance_{timestamp}.csv"
    df_symbols.to_csv(all_symbols_csv, index=False)
    print(f"[SAVED] {all_symbols_csv}")

    best_csv = results_dir / f"top25_symbols_{timestamp}.csv"
    df_best_25.to_csv(best_csv, index=False)
    print(f"[SAVED] {best_csv}")

    worst_csv = results_dir / f"bottom25_symbols_{timestamp}.csv"
    df_worst_25.to_csv(worst_csv, index=False)
    print(f"[SAVED] {worst_csv}")

    print("\n" + "=" * 120)
    print("ANALYSIS COMPLETE")
    print("=" * 120)

if __name__ == "__main__":
    main()
