"""
Compare optimization results across all symbols
Identify patterns in optimal parameters
"""

import pandas as pd
import os

def load_top_result(symbol):
    """Load the top optimization result for a symbol"""
    csv_file = f'data/results/{symbol}_optimization_results.csv'

    if not os.path.exists(csv_file):
        print(f"Warning: {csv_file} not found")
        return None

    df = pd.read_csv(csv_file)
    df = df.sort_values('return', ascending=False)

    top = df.iloc[0]

    return {
        'symbol': symbol,
        'return': top['return'],
        'atr_period': top['atr_period'],
        'atr_multiplier': top['atr_multiplier'],
        'stop_loss_type': top['stop_loss_type'],
        'stop_loss_value': top['stop_loss_value'],
        'profit_target': top['profit_target'],
        'trades': top['trades'],
        'win_rate': top['win_rate'],
        'max_dd': top['max_dd'],
        'sharpe': top['sharpe']
    }

def main():
    print("="*80)
    print("MULTI-SYMBOL OPTIMIZATION COMPARISON")
    print("="*80)
    print()

    symbols = ['NVDA', 'AMD', 'TSLA', 'AAPL']
    results = []

    for symbol in symbols:
        result = load_top_result(symbol)
        if result:
            results.append(result)

    if not results:
        print("No optimization results found!")
        return

    # Create comparison dataframe
    df = pd.DataFrame(results)

    print("TOP CONFIGURATION FOR EACH SYMBOL")
    print("="*80)
    print()

    print(f"{'Symbol':<8} {'Return':>8} {'Period':>7} {'Mult':>6} {'SL Type':>10} {'SL Val':>8} "
          f"{'PT':>6} {'Trades':>7} {'Win%':>6} {'MaxDD':>7} {'Sharpe':>7}")
    print("-"*100)

    for _, row in df.iterrows():
        sl_val = f"{row['stop_loss_value']:.2f}" if pd.notna(row['stop_loss_value']) else "None"
        pt = f"{row['profit_target']:.1f}" if pd.notna(row['profit_target']) else "None"

        print(f"{row['symbol']:<8} {row['return']:>7.1f}% {row['atr_period']:>7.0f} {row['atr_multiplier']:>6.1f} "
              f"{row['stop_loss_type']:>10} {sl_val:>8} {pt:>6} {row['trades']:>7.0f} "
              f"{row['win_rate']:>5.1f}% {row['max_dd']:>6.1f}% {row['sharpe']:>7.2f}")

    print("\n" + "="*80)
    print("PARAMETER PATTERNS")
    print("="*80)
    print()

    # Analyze patterns
    print(f"ATR Period Range: {df['atr_period'].min():.0f} - {df['atr_period'].max():.0f}")
    print(f"Most Common Period: {df['atr_period'].mode().values[0]:.0f}")
    print()

    print(f"ATR Multiplier Range: {df['atr_multiplier'].min():.1f} - {df['atr_multiplier'].max():.1f}")
    print(f"Most Common Multiplier: {df['atr_multiplier'].mode().values[0]:.1f}")
    print()

    print(f"Average Trades: {df['trades'].mean():.1f}")
    print(f"Average Win Rate: {df['win_rate'].mean():.1f}%")
    print(f"Average Max DD: {df['max_dd'].mean():.1f}%")
    print(f"Average Sharpe: {df['sharpe'].mean():.2f}")
    print()

    # Check for patterns
    stop_loss_pattern = df['stop_loss_type'].value_counts()
    print("Stop Loss Preference:")
    for sl_type, count in stop_loss_pattern.items():
        print(f"  {sl_type}: {count}/{len(df)} symbols")
    print()

    # Profit target analysis
    has_pt = df['profit_target'].notna().sum()
    no_pt = df['profit_target'].isna().sum()
    print(f"Profit Target Usage:")
    print(f"  With PT: {has_pt}/{len(df)} symbols")
    print(f"  No PT: {no_pt}/{len(df)} symbols")

    if has_pt > 0:
        avg_pt = df[df['profit_target'].notna()]['profit_target'].mean()
        print(f"  Average PT (when used): {avg_pt:.1f}")

    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print()

    # Universal config - average of winners
    avg_period = df['atr_period'].median()
    avg_mult = df['atr_multiplier'].median()

    print("CONSERVATIVE (One-Size-Fits-All) Configuration:")
    print(f"  ATR Period: {avg_period:.0f}")
    print(f"  ATR Multiplier: {avg_mult:.1f}")
    print(f"  Stop Loss: 10% fixed")
    print(f"  Profit Target: None (let winners run)")
    print()

    print("STOCK-SPECIFIC Recommendations:")
    print("  Use individual optimized parameters for each stock")
    print("  Expected performance shown in table above")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
