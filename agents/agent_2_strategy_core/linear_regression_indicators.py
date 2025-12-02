"""
Linear Regression Indicators for Adaptive Trading

Provides slope, R-squared, and intercept for trend analysis and regime detection.
"""
import backtrader as bt
import numpy as np


class LinearRegressionSlope(bt.Indicator):
    """
    Calculate the slope of linear regression line.

    Positive slope = uptrend
    Negative slope = downtrend
    Magnitude = trend strength
    """
    lines = ('slope',)
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        # Get last N prices
        prices = np.array([self.data.close[-i] for i in range(self.params.period - 1, -1, -1)])

        # X values (time: 0, 1, 2, ..., period-1)
        x = np.arange(self.params.period)

        # Linear regression: y = mx + b
        # Slope (m) = covariance(x,y) / variance(x)
        slope = np.polyfit(x, prices, 1)[0]

        self.lines.slope[0] = slope


class LinearRegressionR2(bt.Indicator):
    """
    Calculate R-squared (coefficient of determination) of linear regression.

    R² near 1.0 = strong linear trend (trending market)
    R² near 0.0 = poor fit (choppy/ranging market)

    Use for regime detection.
    """
    lines = ('r_squared',)
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        # Get last N prices
        prices = np.array([self.data.close[-i] for i in range(self.params.period - 1, -1, -1)])

        # X values
        x = np.arange(self.params.period)

        # Fit linear regression
        coeffs = np.polyfit(x, prices, 1)
        slope, intercept = coeffs[0], coeffs[1]

        # Predicted values
        y_pred = slope * x + intercept

        # R² = 1 - (SS_res / SS_tot)
        # SS_res = sum of squared residuals
        # SS_tot = total sum of squares
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)

        if ss_tot == 0:
            r_squared = 0.0
        else:
            r_squared = 1 - (ss_res / ss_tot)

        # Clamp to [0, 1]
        r_squared = max(0.0, min(1.0, r_squared))

        self.lines.r_squared[0] = r_squared


class LinearRegressionIntercept(bt.Indicator):
    """
    Calculate the intercept of linear regression line.

    Less commonly used, but useful for:
    - Projected price at current time
    - Distance from regression line (support/resistance)
    """
    lines = ('intercept',)
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        # Get last N prices
        prices = np.array([self.data.close[-i] for i in range(self.params.period - 1, -1, -1)])

        # X values
        x = np.arange(self.params.period)

        # Linear regression: y = mx + b
        intercept = np.polyfit(x, prices, 1)[1]

        self.lines.intercept[0] = intercept


class LinearRegressionForecast(bt.Indicator):
    """
    Project the linear regression line forward to predict next value.

    forecast = slope * period + intercept

    Useful for:
    - Setting profit targets
    - Identifying divergence (price vs forecast)
    """
    lines = ('forecast',)
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        # Get last N prices
        prices = np.array([self.data.close[-i] for i in range(self.params.period - 1, -1, -1)])

        # X values
        x = np.arange(self.params.period)

        # Fit
        coeffs = np.polyfit(x, prices, 1)
        slope, intercept = coeffs[0], coeffs[1]

        # Forecast next value (x = period)
        forecast = slope * self.params.period + intercept

        self.lines.forecast[0] = forecast


class MultiTimeframeSlope(bt.Indicator):
    """
    Calculate slopes at multiple timeframes simultaneously.

    Provides short, medium, and long-term slope in one indicator.
    Useful for detecting alignment and acceleration.
    """
    lines = ('slope_short', 'slope_medium', 'slope_long', 'acceleration')
    params = (
        ('period_short', 10),
        ('period_medium', 20),
        ('period_long', 50),
    )

    def __init__(self):
        self.slope_short_ind = LinearRegressionSlope(self.data, period=self.params.period_short)
        self.slope_medium_ind = LinearRegressionSlope(self.data, period=self.params.period_medium)
        self.slope_long_ind = LinearRegressionSlope(self.data, period=self.params.period_long)

        self.addminperiod(self.params.period_long)

    def next(self):
        self.lines.slope_short[0] = self.slope_short_ind[0]
        self.lines.slope_medium[0] = self.slope_medium_ind[0]
        self.lines.slope_long[0] = self.slope_long_ind[0]

        # Acceleration = short-term slope exceeding medium-term slope
        self.lines.acceleration[0] = self.slope_short_ind[0] - self.slope_medium_ind[0]
