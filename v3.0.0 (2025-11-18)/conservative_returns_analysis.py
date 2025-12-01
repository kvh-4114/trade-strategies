"""
Conservative Allocation - Returns Analysis
Generate annual and monthly return breakdowns
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def analyze_returns_by_period(df_portfolio):
    """
    Calculate returns by year and by month
    """
    df = df_portfolio.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['month_name'] = df['date'].dt.strftime('%B')

    # Calculate returns by year
    annual_returns = []
    years = sorted(df['year'].unique())

    for year in years:
        year_data = df[df['year'] == year]
        if len(year_data) == 0:
            continue

        start_value = year_data['portfolio_value'].iloc[0]
        end_value = year_data['portfolio_value'].iloc[-1]

        # Handle edge case: use previous year's end value as start
        if year > years[0]:
            prev_year_data = df[df['year'] == year - 1]
            if len(prev_year_data) > 0:
                start_value = prev_year_data['portfolio_value'].iloc[-1]

        year_return = ((end_value - start_value) / start_value) * 100

        annual_returns.append({
            'year': year,
            'return_pct': year_return,
            'start_value': start_value,
            'end_value': end_value
        })

    df_annual = pd.DataFrame(annual_returns)

    # Calculate returns by month (aggregated across all years)
    monthly_returns = []

    for month in range(1, 13):
        month_name = pd.Timestamp(2020, month, 1).strftime('%B')
        month_returns_list = []

        for year in years:
            # Get this month's data
            month_data = df[(df['year'] == year) & (df['month'] == month)]
            if len(month_data) == 0:
                continue

            # Get start value (end of previous month)
            if month == 1:
                # Use previous year December
                prev_data = df[(df['year'] == year - 1) & (df['month'] == 12)]
                if len(prev_data) > 0:
                    start_value = prev_data['portfolio_value'].iloc[-1]
                else:
                    start_value = month_data['portfolio_value'].iloc[0]
            else:
                prev_data = df[(df['year'] == year) & (df['month'] == month - 1)]
                if len(prev_data) > 0:
                    start_value = prev_data['portfolio_value'].iloc[-1]
                else:
                    start_value = month_data['portfolio_value'].iloc[0]

            end_value = month_data['portfolio_value'].iloc[-1]
            month_return = ((end_value - start_value) / start_value) * 100
            month_returns_list.append(month_return)

        if month_returns_list:
            monthly_returns.append({
                'month': month,
                'month_name': month_name,
                'avg_return_pct': np.mean(month_returns_list),
                'median_return_pct': np.median(month_returns_list),
                'std_return_pct': np.std(month_returns_list),
                'min_return_pct': np.min(month_returns_list),
                'max_return_pct': np.max(month_returns_list),
                'count': len(month_returns_list)
            })

    df_monthly = pd.DataFrame(monthly_returns)

    return df_annual, df_monthly

def create_returns_charts(df_annual, df_monthly, output_path):
    """
    Create comprehensive returns visualization
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    fig.suptitle('Conservative Allocation (4 Tiers) - Returns Analysis',
                 fontsize=16, fontweight='bold', y=0.995)

    # 1. Annual Returns Bar Chart
    ax1 = fig.add_subplot(gs[0, :])
    colors = ['#06A77D' if x > 0 else '#D62828' for x in df_annual['return_pct']]
    bars = ax1.bar(df_annual['year'], df_annual['return_pct'], color=colors, alpha=0.8, edgecolor='black')

    # Add value labels on bars
    for i, (year, ret) in enumerate(zip(df_annual['year'], df_annual['return_pct'])):
        ax1.text(year, ret + (1 if ret > 0 else -1), f'{ret:.1f}%',
                ha='center', va='bottom' if ret > 0 else 'top',
                fontsize=9, fontweight='bold')

    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax1.set_xlabel('Year', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Annual Return (%)', fontsize=11, fontweight='bold')
    ax1.set_title('Annual Returns by Year', fontsize=12, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3, linestyle=':', axis='y')

    # Add average line
    avg_return = df_annual['return_pct'].mean()
    ax1.axhline(y=avg_return, color='blue', linestyle='--', linewidth=2,
                label=f'Average: {avg_return:.1f}%', alpha=0.7)
    ax1.legend(loc='upper left', fontsize=10)

    # 2. Annual Returns Statistics
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.axis('off')

    stats_text = f"""
    ANNUAL RETURNS STATISTICS
    {'='*40}

    Average Annual Return:    {df_annual['return_pct'].mean():>8.2f}%
    Median Annual Return:     {df_annual['return_pct'].median():>8.2f}%
    Std Dev:                  {df_annual['return_pct'].std():>8.2f}%

    Best Year:                {df_annual.loc[df_annual['return_pct'].idxmax(), 'year']:.0f}  ({df_annual['return_pct'].max():.2f}%)
    Worst Year:               {df_annual.loc[df_annual['return_pct'].idxmin(), 'year']:.0f}  ({df_annual['return_pct'].min():.2f}%)

    Positive Years:           {(df_annual['return_pct'] > 0).sum()}/{len(df_annual)}
    Negative Years:           {(df_annual['return_pct'] < 0).sum()}/{len(df_annual)}

    Win Rate:                 {(df_annual['return_pct'] > 0).sum() / len(df_annual) * 100:.1f}%
    """

    ax2.text(0.1, 0.9, stats_text, fontsize=10, family='monospace',
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # 3. Monthly Average Returns Bar Chart
    ax3 = fig.add_subplot(gs[1, 1])
    colors_monthly = ['#06A77D' if x > 0 else '#D62828' for x in df_monthly['avg_return_pct']]
    bars = ax3.bar(range(12), df_monthly['avg_return_pct'], color=colors_monthly,
                   alpha=0.8, edgecolor='black')

    # Add value labels
    for i, ret in enumerate(df_monthly['avg_return_pct']):
        ax3.text(i, ret + (0.1 if ret > 0 else -0.1), f'{ret:.1f}%',
                ha='center', va='bottom' if ret > 0 else 'top',
                fontsize=8, fontweight='bold')

    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax3.set_xticks(range(12))
    ax3.set_xticklabels(df_monthly['month_name'], rotation=45, ha='right')
    ax3.set_ylabel('Average Return (%)', fontsize=11, fontweight='bold')
    ax3.set_title('Average Returns by Month (All Years)', fontsize=12, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3, linestyle=':', axis='y')

    # 4. Monthly Returns Heatmap Table
    ax4 = fig.add_subplot(gs[2, :])
    ax4.axis('off')

    # Create table data
    table_data = []
    table_data.append(['Month', 'Avg Return', 'Median', 'Std Dev', 'Min', 'Max', '# Years'])

    for _, row in df_monthly.iterrows():
        table_data.append([
            row['month_name'][:3],
            f"{row['avg_return_pct']:.2f}%",
            f"{row['median_return_pct']:.2f}%",
            f"{row['std_return_pct']:.2f}%",
            f"{row['min_return_pct']:.2f}%",
            f"{row['max_return_pct']:.2f}%",
            f"{row['count']:.0f}"
        ])

    # Color code based on average return
    cell_colors = [['lightgray'] * 7]  # Header row
    for row in df_monthly.itertuples():
        if row.avg_return_pct > 2:
            row_color = ['#90EE90'] * 7  # Light green
        elif row.avg_return_pct > 0:
            row_color = ['#E8F5E9'] * 7  # Very light green
        elif row.avg_return_pct > -2:
            row_color = ['#FFEBEE'] * 7  # Very light red
        else:
            row_color = ['#FFCDD2'] * 7  # Light red
        cell_colors.append(row_color)

    table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                     cellColours=cell_colors, bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Bold header row
    for i in range(7):
        table[(0, i)].set_text_props(weight='bold')

    ax4.set_title('Monthly Returns Statistics', fontsize=12, fontweight='bold', pad=20)

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] {output_path}")

def print_returns_summary(df_annual, df_monthly):
    """Print detailed returns summary"""

    print("\n" + "=" * 100)
    print("CONSERVATIVE ALLOCATION - RETURNS ANALYSIS")
    print("=" * 100)

    print("\n" + "-" * 100)
    print("ANNUAL RETURNS")
    print("-" * 100)
    print(f"{'Year':<10} {'Start Value':<20} {'End Value':<20} {'Return':<15}")
    print("-" * 100)

    for _, row in df_annual.iterrows():
        print(f"{row['year']:<10.0f} ${row['start_value']:<19,.0f} ${row['end_value']:<19,.0f} {row['return_pct']:>13.2f}%")

    print("-" * 100)
    print(f"{'AVERAGE':<10} {'':<20} {'':<20} {df_annual['return_pct'].mean():>13.2f}%")
    print(f"{'MEDIAN':<10} {'':<20} {'':<20} {df_annual['return_pct'].median():>13.2f}%")
    print(f"{'STD DEV':<10} {'':<20} {'':<20} {df_annual['return_pct'].std():>13.2f}%")
    print("-" * 100)

    print("\n" + "-" * 100)
    print("MONTHLY RETURNS (AVERAGED ACROSS ALL YEARS)")
    print("-" * 100)
    print(f"{'Month':<12} {'Avg Return':<15} {'Median':<15} {'Std Dev':<15} {'Min':<15} {'Max':<15}")
    print("-" * 100)

    for _, row in df_monthly.iterrows():
        print(f"{row['month_name']:<12} {row['avg_return_pct']:>13.2f}% "
              f"{row['median_return_pct']:>13.2f}% {row['std_return_pct']:>13.2f}% "
              f"{row['min_return_pct']:>13.2f}% {row['max_return_pct']:>13.2f}%")

    print("-" * 100)

    # Best and worst months
    best_month = df_monthly.loc[df_monthly['avg_return_pct'].idxmax()]
    worst_month = df_monthly.loc[df_monthly['avg_return_pct'].idxmin()]

    print(f"\nBest Month (Average):   {best_month['month_name']} ({best_month['avg_return_pct']:.2f}%)")
    print(f"Worst Month (Average):  {worst_month['month_name']} ({worst_month['avg_return_pct']:.2f}%)")
    print()

    # Positive vs negative months
    positive_months = (df_monthly['avg_return_pct'] > 0).sum()
    print(f"Months with Positive Avg Returns: {positive_months}/12")
    print(f"Months with Negative Avg Returns: {12 - positive_months}/12")

    print("\n" + "=" * 100)

def main():
    print("\n" + "=" * 100)
    print("CONSERVATIVE ALLOCATION - RETURNS ANALYSIS")
    print("=" * 100)
    print()

    # Load portfolio data
    results_dir = Path("results")
    csv_files = sorted(results_dir.glob("conservative_portfolio_data_*.csv"))

    if not csv_files:
        print("ERROR: No portfolio data files found!")
        return

    csv_file = csv_files[-1]
    print(f"Loading: {csv_file}")
    df_portfolio = pd.read_csv(csv_file)
    print(f"Portfolio data points: {len(df_portfolio)}")
    print()

    # Analyze returns
    print("Analyzing returns by year and month...")
    df_annual, df_monthly = analyze_returns_by_period(df_portfolio)

    # Print summary
    print_returns_summary(df_annual, df_monthly)

    # Create charts
    print("\nGenerating returns analysis charts...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"conservative_returns_analysis_{timestamp}.png"
    create_returns_charts(df_annual, df_monthly, output_path)

    # Save data to CSV
    annual_csv = results_dir / f"annual_returns_{timestamp}.csv"
    df_annual.to_csv(annual_csv, index=False)
    print(f"[SAVED] {annual_csv}")

    monthly_csv = results_dir / f"monthly_returns_{timestamp}.csv"
    df_monthly.to_csv(monthly_csv, index=False)
    print(f"[SAVED] {monthly_csv}")

    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)

if __name__ == "__main__":
    main()
