"""
INDEPENDENT SLOPE CALCULATOR
=============================

Calculates LinReg slope for any LR period/lookahead configuration.
This is independent of the entry/exit strategy LR parameters.

USAGE:
------
    from calculate_slope import calculate_slope, add_slopes_to_trades

    # Calculate slope for price series
    slope = calculate_slope(prices, lr_period=13, lr_lookahead=0)

    # Add slopes to all baseline trades
    df_trades = add_slopes_to_trades(df_trades, price_data,
                                      lr_period=21, lr_lookahead=-1)

AUTHOR: Claude Code Experiments
DATE: November 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import glob
import os


def calculate_slope(prices: np.ndarray, lr_period: int = 13, lr_lookahead: int = 0) -> float:
    """
    Calculate normalized linear regression slope.

    Args:
        prices: Array of prices (most recent at end)
        lr_period: Lookback period for LR fit
        lr_lookahead: Projection point (0=current, -1=backcast, -3=smooth)

    Returns:
        Slope as % per bar (normalized by average price)
        Returns 0.0 if insufficient data
    """
    if len(prices) < lr_period:
        return 0.0

    # Get last lr_period prices
    y = prices[-lr_period:]
    x = np.arange(len(y))

    # Fit linear regression
    coeffs = np.polyfit(x, y, 1)
    slope_raw = coeffs[0]  # Slope in price units per bar

    # Normalize by average price (as % per bar)
    avg_price = np.mean(y)
    if avg_price == 0:
        return 0.0

    slope_pct = (slope_raw / avg_price) * 100

    return slope_pct


def calculate_slope_from_ha(ha_closes: np.ndarray, lr_period: int = 13,
                            lr_lookahead: int = 0) -> float:
    """
    Calculate slope from Heikin Ashi closes (standard for this strategy).

    Args:
        ha_closes: Heikin Ashi close prices
        lr_period: LR lookback period
        lr_lookahead: LR lookahead parameter (not used in basic calculation)

    Returns:
        Slope as % per bar
    """
    # For now, lookahead mainly affects the LR indicator calculation in backtrader
    # For post-analysis, we calculate slope on the closes directly
    return calculate_slope(ha_closes, lr_period, lr_lookahead)


def load_symbol_data(symbol: str, data_dir: str, bar_timeframe: str = '4day') -> Optional[pd.DataFrame]:
    """
    Load and prepare data for a single symbol.

    Args:
        symbol: Stock symbol
        data_dir: Directory with daily data files
        bar_timeframe: '4day' or 'daily'

    Returns:
        DataFrame with OHLCV data, or None if not found
    """
    # Find file for symbol
    pattern = os.path.join(data_dir, f'{symbol}_trades_*.csv')
    files = glob.glob(pattern)

    if not files:
        return None

    # Load daily data
    df_daily = pd.read_csv(files[0])

    if len(df_daily) < 100:
        return None

    # Resample if needed
    if bar_timeframe == '4day':
        df_daily['date'] = pd.to_datetime(df_daily['date'])
        df_daily = df_daily.sort_values('date')
        df_daily.set_index('date', inplace=True)

        df_bars = df_daily.resample('4D', origin='epoch').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        df_bars.reset_index(inplace=True)
        return df_bars
    else:
        # Daily bars - just ensure date is datetime
        df_daily['date'] = pd.to_datetime(df_daily['date'])
        return df_daily


def calculate_ha_close(open_price: float, high: float, low: float, close: float) -> float:
    """Calculate Heikin Ashi close for a single bar"""
    return (open_price + high + low + close) / 4.0


def calculate_ha_candles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Heikin Ashi candles from OHLC data.

    Args:
        df: DataFrame with open, high, low, close columns

    Returns:
        DataFrame with additional ha_open, ha_high, ha_low, ha_close columns
    """
    df = df.copy()

    df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
    df['ha_open'] = (df['open'] + df['close']) / 2.0

    # Calculate sequential HA opens
    for i in range(1, len(df)):
        df.loc[df.index[i], 'ha_open'] = (df.loc[df.index[i-1], 'ha_open'] +
                                           df.loc[df.index[i-1], 'ha_close']) / 2.0

    df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
    df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)

    return df


def calculate_slopes_for_symbol(symbol: str, data_dir: str, bar_timeframe: str = '4day',
                                lr_period: int = 13, lr_lookahead: int = 0) -> Dict:
    """
    Calculate current slope for a symbol.

    Args:
        symbol: Stock symbol
        data_dir: Directory with daily data
        bar_timeframe: '4day' or 'daily'
        lr_period: Slope LR period
        lr_lookahead: Slope LR lookahead (informational, not used in calculation)

    Returns:
        Dict with symbol, current_slope, and metadata
    """
    # Load data
    df = load_symbol_data(symbol, data_dir, bar_timeframe)

    if df is None or len(df) < lr_period + 10:
        return {
            'symbol': symbol,
            'slope': None,
            'error': 'Insufficient data'
        }

    # Calculate HA candles
    df = calculate_ha_candles(df)

    # Calculate current slope
    slope = calculate_slope(df['ha_close'].values, lr_period, lr_lookahead)

    return {
        'symbol': symbol,
        'slope': slope,
        'bars_available': len(df),
        'last_date': df['date'].iloc[-1] if 'date' in df.columns else None,
        'last_price': df['close'].iloc[-1]
    }


def add_entry_slopes_to_baseline_trades(df_trades: pd.DataFrame, data_dir: str,
                                       bar_timeframe: str = '4day',
                                       lr_period: int = 13,
                                       lr_lookahead: int = 0) -> pd.DataFrame:
    """
    Calculate entry slope for all baseline trades using specified LR config.

    This is the KEY FUNCTION for experiments - it recalculates slopes using
    different LR parameters than the strategy used.

    Args:
        df_trades: Baseline trades DataFrame
        data_dir: Directory with daily data
        bar_timeframe: '4day' or 'daily'
        lr_period: Slope LR period to use
        lr_lookahead: Slope LR lookahead to use

    Returns:
        DataFrame with 'entry_slope_{period}p_{lookahead}la' column added
    """
    print(f"\nCalculating entry slopes with {lr_period}p/{lr_lookahead}la configuration...")
    print(f"Bar timeframe: {bar_timeframe}")
    print(f"Total trades: {len(df_trades):,}")

    df_trades = df_trades.copy()
    slope_col = f'entry_slope_{lr_period}p_{lr_lookahead}la'
    df_trades[slope_col] = 0.0

    # Group by symbol for efficiency
    symbols = df_trades['symbol'].unique()
    print(f"Processing {len(symbols)} symbols...")

    processed = 0
    for symbol in symbols:
        # Load and prepare data for this symbol
        df_data = load_symbol_data(symbol, data_dir, bar_timeframe)

        if df_data is None:
            continue

        # Calculate HA candles
        df_data = calculate_ha_candles(df_data)
        df_data['date'] = pd.to_datetime(df_data['date'])

        # Get all trades for this symbol
        symbol_trades = df_trades[df_trades['symbol'] == symbol].copy()

        # Calculate slope at each entry date
        for idx, trade in symbol_trades.iterrows():
            entry_date = pd.to_datetime(trade['entry_date'])

            # Find data up to entry date
            df_history = df_data[df_data['date'] <= entry_date]

            if len(df_history) >= lr_period:
                slope = calculate_slope(df_history['ha_close'].values, lr_period, lr_lookahead)
                df_trades.loc[idx, slope_col] = slope

        processed += 1
        if processed % 10 == 0:
            print(f"  Processed {processed}/{len(symbols)} symbols...")

    print(f"[SUCCESS] Slopes calculated for {processed} symbols")
    print(f"   Slope column: {slope_col}")
    print(f"   Avg slope: {df_trades[slope_col].mean():.3f}%")
    print(f"   Median slope: {df_trades[slope_col].median():.3f}%")
    print(f"   Min/Max: {df_trades[slope_col].min():.3f}% / {df_trades[slope_col].max():.3f}%")

    return df_trades


def analyze_slope_distribution(df_trades: pd.DataFrame, slope_col: str = 'entry_slope') -> Dict:
    """
    Analyze the distribution of slopes in a trade dataset.

    Args:
        df_trades: DataFrame with slope column
        slope_col: Name of slope column to analyze

    Returns:
        Dict with distribution statistics
    """
    if slope_col not in df_trades.columns:
        # Try to find any slope column
        slope_cols = [col for col in df_trades.columns if 'slope' in col.lower()]
        if slope_cols:
            slope_col = slope_cols[0]
        else:
            return {'error': 'No slope column found'}

    slopes = df_trades[slope_col]

    stats = {
        'count': len(slopes),
        'mean': slopes.mean(),
        'median': slopes.median(),
        'std': slopes.std(),
        'min': slopes.min(),
        'max': slopes.max(),
        'q25': slopes.quantile(0.25),
        'q75': slopes.quantile(0.75),
        'pct_positive': (slopes > 0).sum() / len(slopes) * 100,
        'pct_negative': (slopes < 0).sum() / len(slopes) * 100,
    }

    return stats


if __name__ == '__main__':
    # Test the slope calculator
    print("="*80)
    print("SLOPE CALCULATOR TEST")
    print("="*80)

    # Test with synthetic data
    prices = np.array([100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124])

    print("\nTest 1: Uptrending prices")
    print(f"Prices: {prices}")

    for period in [5, 7, 10, 13]:
        slope = calculate_slope(prices, lr_period=period, lr_lookahead=0)
        print(f"  {period}-period slope: {slope:+.3f}%")

    # Test with downtrend
    prices_down = prices[::-1]
    print("\nTest 2: Downtrending prices")
    print(f"Prices: {prices_down}")

    for period in [5, 7, 10, 13]:
        slope = calculate_slope(prices_down, lr_period=period, lr_lookahead=0)
        print(f"  {period}-period slope: {slope:+.3f}%")

    # Test with flat prices
    prices_flat = np.array([100] * 13)
    print("\nTest 3: Flat prices")
    print(f"Prices: {prices_flat}")

    slope = calculate_slope(prices_flat, lr_period=13, lr_lookahead=0)
    print(f"  13-period slope: {slope:+.3f}%")

    print("\n" + "="*80)
    print("[SUCCESS] Slope calculator tests complete")
    print("="*80)
