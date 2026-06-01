"""Technical indicators.

Kept deliberately small and pure: each function takes a price series and
returns a series. Easy to read, easy to test, no hidden state.
"""

from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, window: int = 20) -> pd.Series:
    """Simple moving average."""
    return close.rolling(window=window, min_periods=1).mean()


def ema(close: pd.Series, span: int = 50) -> pd.Series:
    """Exponential moving average."""
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    # When there are no losses at all, RS is infinite and RSI saturates at 100.
    # Guard the division so that case becomes 100 rather than undefined.
    rs = avg_gain / avg_loss
    out = 100 - (100 / (1 + rs))
    out = out.where(avg_loss != 0, 100.0)   # no losses -> fully overbought
    out = out.where(avg_gain != 0, out)     # keep computed value otherwise
    # First row has no delta; default it to the neutral midline.
    out.iloc[0] = 50.0
    return out.fillna(50.0)


def latest_rsi(close: pd.Series, period: int = 14) -> float:
    """Convenience: the most recent RSI value as a float."""
    series = rsi(close, period)
    return round(float(series.iloc[-1]), 1)
