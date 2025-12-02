"""
Optimized Conservative Allocation Portfolio Analysis
Uses efficient event-based approach for mark-to-market calculations
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime, timedelta

# Constants
BASE_POSITION_SIZE = 10000
STARTING_CASH = 1000000

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

def simulate_portfolio_fast(df_trades):
    """
    Fast mark-to-market simulation using event-based approach.
    Samples weekly instead of daily for speed.
    """
    print("Simulating mark-to-market portfolio (fast method)...")

    # Convert dates
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
    df_trades['exit_date'] = pd.to_datetime(df_trades['exit_date'])

    # Get date range
    start_date = df_trades['entry_date'].min()
    end_date = df_trades['exit_date'].max()
    print(f"  Date range: {start_date.date()} to {end_date.date()}")

    # Create weekly sampling dates
    date_range = pd.date_range(start=start_date, end=end_date, freq='W-FRI')
    print(f"  Sampling {len(date_range)} weeks (weekly intervals)")

    portfolio_data = []
    cash = STARTING_CASH
    realized_pnl = 0.0

    for current_date in date_range:
        # Get trades that closed by this date
        closed_by_now = df_trades[df_trades['exit_date'] <= current_date]
        position_mult = closed_by_now['position_size'] / BASE_POSITION_SIZE
        realized_pnl_now = (closed_by_now['pnl'] * position_mult).sum()

        # Get currently open positions
        open_mask = (df_trades['entry_date'] <= current_date) & (df_trades['exit_date'] > current_date)
        open_positions = df_trades[open_mask].copy()

        # Calculate open P&L vectorized
        if len(open_positions) > 0:
            total_days = (open_positions['exit_date'] - open_positions['entry_date']).dt.days
            days_held = (current_date - open_positions['entry_date']).dt.days
            pnl_ratio = days_held / total_days.replace(0, 1)  # Avoid division by zero
            position_mult_open = open_positions['position_size'] / BASE_POSITION_SIZE
            open_pnl = (open_positions['pnl'] * pnl_ratio * position_mult_open).sum()
        else:
            open_pnl = 0.0

        # Portfolio metrics
        total_pnl = realized_pnl_now + open_pnl
        portfolio_value = cash + total_pnl
        concurrent_positions = len(open_positions)

        portfolio_data.append({
            'date': current_date,
            'cash': cash,
            'realized_pnl': realized_pnl_now,
            'open_pnl': open_pnl,
            'total_pnl': total_pnl,
            'portfolio_value': portfolio_value,
            'concurrent_positions': concurrent_positions
        })

    df_portfolio = pd.DataFrame(portfolio_data)

    # Calculate drawdown
    df_portfolio['peak_value'] = df_portfolio['portfolio_value'].cummax()
    df_portfolio['drawdown'] = df_portfolio['portfolio_value'] - df_portfolio['peak_value']
    df_portfolio['drawdown_pct'] = (df_portfolio['drawdown'] / df_portfolio['peak_value']) * 100

    print(f"  Final portfolio value: ${df_portfolio['portfolio_value'].iloc[-1]:,.0f}")
    print(f"  Total P&L: ${df_portfolio['total_pnl'].iloc[-1]:,.0f}")
    print(f"  Max concurrent positions: {df_portfolio['concurrent_positions'].max()}")
    print(f"  Max drawdown: {df_portfolio['drawdown_pct'].min():.2f}%")

    return df_portfolio

def create_portfolio_charts(df_portfolio, strategy_name, output_suffix=""):
    """Create comprehensive portfolio analysis charts"""

    # Create figure with 4 subplots
    fig, axes = plt.subplots(4, 1, figsize=(16, 14))
    fig.suptitle(f'{strategy_name} - Portfolio Analysis{output_suffix}',
                 fontsize=16, fontweight='bold', y=0.995)

    # 1. Portfolio Value (Mark-to-Market)
    ax1 = axes[0]
    ax1.plot(df_portfolio['date'], df_portfolio['portfolio_value'] / 1e6,
             linewidth=2, color='#2E86AB', label='Total Portfolio Value')
    ax1.axhline(y=STARTING_CASH / 1e6, color='gray', linestyle='--',
                linewidth=1, alpha=0.5, label='Starting Capital')
    ax1.fill_between(df_portfolio['date'],
                     STARTING_CASH / 1e6,
                     df_portfolio['portfolio_value'] / 1e6,
                     alpha=0.3, color='#2E86AB')
    ax1.set_ylabel('Portfolio Value ($M)', fontsize=11, fontweight='bold')
    ax1.set_title('Mark-to-Market Portfolio Value', fontsize=12, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3, linestyle=':')
    ax1.legend(loc='upper left', fontsize=10)

    # Add final value annotation
    final_value = df_portfolio['portfolio_value'].iloc[-1]
    final_date = df_portfolio['date'].iloc[-1]
    ax1.annotate(f'${final_value/1e6:.2f}M',
                xy=(final_date, final_value/1e6),
                xytext=(10, 10), textcoords='offset points',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

    # 2. P&L Breakdown (Realized vs Open)
    ax2 = axes[1]
    ax2.plot(df_portfolio['date'], df_portfolio['realized_pnl'] / 1e6,
             linewidth=2, color='#06A77D', label='Realized P&L')
    ax2.plot(df_portfolio['date'], df_portfolio['open_pnl'] / 1e6,
             linewidth=1.5, color='#F77F00', alpha=0.7, label='Open P&L (Unrealized)')
    ax2.plot(df_portfolio['date'], df_portfolio['total_pnl'] / 1e6,
             linewidth=2, color='#2E86AB', linestyle='--', label='Total P&L')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.3)
    ax2.set_ylabel('P&L ($M)', fontsize=11, fontweight='bold')
    ax2.set_title('Realized vs Unrealized P&L', fontsize=12, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3, linestyle=':')
    ax2.legend(loc='upper left', fontsize=10)

    # 3. Drawdown
    ax3 = axes[2]
    ax3.fill_between(df_portfolio['date'], 0, df_portfolio['drawdown_pct'],
                     color='#D62828', alpha=0.5)
    ax3.plot(df_portfolio['date'], df_portfolio['drawdown_pct'],
             linewidth=2, color='#D62828')
    ax3.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
    ax3.set_title('Drawdown from Peak', fontsize=12, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3, linestyle=':')
    ax3.set_ylim([df_portfolio['drawdown_pct'].min() * 1.1, 1])

    # Add max drawdown annotation
    max_dd_idx = df_portfolio['drawdown_pct'].idxmin()
    max_dd_value = df_portfolio['drawdown_pct'].loc[max_dd_idx]
    max_dd_date = df_portfolio['date'].loc[max_dd_idx]
    ax3.annotate(f'Max DD: {max_dd_value:.2f}%',
                xy=(max_dd_date, max_dd_value),
                xytext=(10, -20), textcoords='offset points',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

    # 4. Concurrent Active Positions
    ax4 = axes[3]
    ax4.fill_between(df_portfolio['date'], 0, df_portfolio['concurrent_positions'],
                     color='#9D4EDD', alpha=0.4)
    ax4.plot(df_portfolio['date'], df_portfolio['concurrent_positions'],
             linewidth=1.5, color='#9D4EDD')
    ax4.set_ylabel('Number of Positions', fontsize=11, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax4.set_title('Concurrent Active Positions', fontsize=12, fontweight='bold', pad=10)
    ax4.grid(True, alpha=0.3, linestyle=':')

    # Add max positions annotation
    max_positions = df_portfolio['concurrent_positions'].max()
    avg_positions = df_portfolio['concurrent_positions'].mean()
    ax4.axhline(y=max_positions, color='red', linestyle='--',
                linewidth=1, alpha=0.5, label=f'Max: {max_positions}')
    ax4.axhline(y=avg_positions, color='blue', linestyle='--',
                linewidth=1, alpha=0.5, label=f'Avg: {avg_positions:.1f}')
    ax4.legend(loc='upper left', fontsize=10)

    # Format x-axis dates for all subplots
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 4, 7, 10)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return fig

def print_portfolio_summary(df_portfolio, strategy_name):
    """Print comprehensive portfolio statistics"""

    print("\n" + "=" * 100)
    print(f"{strategy_name} - PORTFOLIO SUMMARY")
    print("=" * 100)
    print()

    # Performance metrics
    starting_value = STARTING_CASH
    final_value = df_portfolio['portfolio_value'].iloc[-1]
    total_return = final_value - starting_value
    total_return_pct = (total_return / starting_value) * 100

    print("PERFORMANCE METRICS")
    print("-" * 100)
    print(f"Starting Capital:        ${starting_value:>15,.0f}")
    print(f"Final Portfolio Value:   ${final_value:>15,.0f}")
    print(f"Total Return:            ${total_return:>15,.0f}  ({total_return_pct:>6.2f}%)")
    print()

    # P&L breakdown
    final_realized = df_portfolio['realized_pnl'].iloc[-1]
    final_open = df_portfolio['open_pnl'].iloc[-1]

    print("P&L BREAKDOWN")
    print("-" * 100)
    print(f"Realized P&L:            ${final_realized:>15,.0f}")
    print(f"Open P&L (Unrealized):   ${final_open:>15,.0f}")
    print(f"Total P&L:               ${final_realized + final_open:>15,.0f}")
    print()

    # Drawdown analysis
    max_dd = df_portfolio['drawdown_pct'].min()
    max_dd_date = df_portfolio.loc[df_portfolio['drawdown_pct'].idxmin(), 'date']

    print("DRAWDOWN ANALYSIS")
    print("-" * 100)
    print(f"Maximum Drawdown:        {max_dd:>15.2f}%")
    print(f"Max DD Date:             {max_dd_date.date()}")
    print()

    # Position statistics
    avg_positions = df_portfolio['concurrent_positions'].mean()
    max_positions = df_portfolio['concurrent_positions'].max()
    max_pos_date = df_portfolio.loc[df_portfolio['concurrent_positions'].idxmax(), 'date']

    print("POSITION STATISTICS")
    print("-" * 100)
    print(f"Average Concurrent Positions:  {avg_positions:>10.1f}")
    print(f"Maximum Concurrent Positions:  {max_positions:>10.0f}  (on {max_pos_date.date()})")
    print()

    # Date range
    start_date = df_portfolio['date'].iloc[0]
    end_date = df_portfolio['date'].iloc[-1]
    days = (end_date - start_date).days
    years = days / 365.25

    print("TIME PERIOD")
    print("-" * 100)
    print(f"Start Date:              {start_date.date()}")
    print(f"End Date:                {end_date.date()}")
    print(f"Duration:                {days} days ({years:.2f} years)")
    print()

    # Annualized metrics
    annualized_return = (((final_value / starting_value) ** (1 / years)) - 1) * 100

    print("ANNUALIZED METRICS")
    print("-" * 100)
    print(f"Annualized Return:       {annualized_return:>15.2f}%")
    print()

    print("=" * 100)

def main():
    print("\n" + "=" * 100)
    print("CONSERVATIVE ALLOCATION - PORTFOLIO ANALYSIS (OPTIMIZED)")
    print("=" * 100)
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
    print(f"Trades eliminated: {len(df_trades) - len(df_conservative):,}")
    print()

    # Simulate portfolio
    df_portfolio = simulate_portfolio_fast(df_conservative)

    # Print summary
    print_portfolio_summary(df_portfolio, "Conservative Allocation (4 Tiers)")

    # Create full period charts
    print("\nGenerating full period charts...")
    fig_full = create_portfolio_charts(
        df_portfolio,
        "Conservative Allocation (4 Tiers)",
        ""
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_full = results_dir / f"conservative_portfolio_full_{timestamp}.png"
    fig_full.savefig(output_file_full, dpi=150, bbox_inches='tight')
    print(f"[SAVED] {output_file_full}")
    plt.close(fig_full)

    # Create 2025-only charts
    print("\nGenerating 2025-specific charts...")
    df_2025 = df_portfolio[df_portfolio['date'].dt.year == 2025].copy()

    if len(df_2025) > 0:
        # Reset drawdown calculation for 2025 only
        df_2025['peak_value'] = df_2025['portfolio_value'].cummax()
        df_2025['drawdown'] = df_2025['portfolio_value'] - df_2025['peak_value']
        df_2025['drawdown_pct'] = (df_2025['drawdown'] / df_2025['peak_value']) * 100

        fig_2025 = create_portfolio_charts(
            df_2025,
            "Conservative Allocation (4 Tiers)",
            " - 2025 Only"
        )

        output_file_2025 = results_dir / f"conservative_portfolio_2025_{timestamp}.png"
        fig_2025.savefig(output_file_2025, dpi=150, bbox_inches='tight')
        print(f"[SAVED] {output_file_2025}")
        plt.close(fig_2025)

        # Print 2025 summary
        print("\n" + "=" * 100)
        print("2025 PERFORMANCE SUMMARY")
        print("=" * 100)
        print(f"Start Value (2025):      ${df_2025['portfolio_value'].iloc[0]:>15,.0f}")
        print(f"End Value (2025):        ${df_2025['portfolio_value'].iloc[-1]:>15,.0f}")

        value_2025_start = df_2025['portfolio_value'].iloc[0]
        value_2025_end = df_2025['portfolio_value'].iloc[-1]
        return_2025 = value_2025_end - value_2025_start
        return_2025_pct = (return_2025 / value_2025_start) * 100

        print(f"2025 Return:             ${return_2025:>15,.0f}  ({return_2025_pct:>6.2f}%)")
        print(f"Max Drawdown (2025):     {df_2025['drawdown_pct'].min():>15.2f}%")
        print(f"Avg Positions (2025):    {df_2025['concurrent_positions'].mean():>15.1f}")
        print(f"Max Positions (2025):    {df_2025['concurrent_positions'].max():>15.0f}")
        print("=" * 100)
    else:
        print("No 2025 data found!")

    # Save portfolio data
    output_csv = results_dir / f"conservative_portfolio_data_{timestamp}.csv"
    df_portfolio.to_csv(output_csv, index=False)
    print(f"\n[SAVED] Portfolio data: {output_csv}")

    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)

if __name__ == "__main__":
    main()
