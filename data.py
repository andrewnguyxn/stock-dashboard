"""Data access layer.

Design goal: the app must run for anyone who clones it, with or without an API
key, and must never crash because an upstream provider is down. We achieve that
with a fallback chain:

    live mode  : Finnhub for real-time quotes, yfinance for historical candles
    demo mode  : deterministic synthetic data (no network, always works)

Mode is chosen automatically based on whether FINNHUB_API_KEY is configured.
Every network call is wrapped so a failure degrades gracefully to demo data
rather than throwing.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass

import pandas as pd

import config


@dataclass
class Quote:
    """A point-in-time quote for one ticker."""

    ticker: str
    price: float
    prev_close: float

    @property
    def change(self) -> float:
        return self.price - self.prev_close

    @property
    def pct_change(self) -> float:
        if self.prev_close == 0:
            return 0.0
        return (self.change / self.prev_close) * 100


# --------------------------------------------------------------------------- #
# Demo data (deterministic so the UI looks consistent and sensible)
# --------------------------------------------------------------------------- #

def _seed(ticker: str) -> int:
    """Stable integer seed derived from a ticker symbol."""
    return int(hashlib.md5(ticker.encode()).hexdigest(), 16) % (2**32)


def _demo_quote(ticker: str) -> Quote:
    import random

    rng = random.Random(_seed(ticker))
    base = rng.uniform(80, 900)
    pct = rng.uniform(-2.5, 2.5)
    prev = base / (1 + pct / 100)
    return Quote(ticker=ticker, price=round(base, 2), prev_close=round(prev, 2))


def _demo_candles(ticker: str, days: int) -> pd.DataFrame:
    import random

    rng = random.Random(_seed(ticker))
    price = _demo_quote(ticker).price * 0.7  # start lower so the trend rises
    rows = []
    today = dt.date.today()
    for i in range(days, 0, -1):
        drift = rng.uniform(-0.02, 0.025)  # slight upward bias
        price = max(1.0, price * (1 + drift))
        high = price * (1 + abs(rng.uniform(0, 0.015)))
        low = price * (1 - abs(rng.uniform(0, 0.015)))
        open_ = low + (high - low) * rng.random()
        rows.append(
            {
                "date": today - dt.timedelta(days=i),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(price, 2),
                "volume": int(rng.uniform(5e6, 8e7)),
            }
        )
    return pd.DataFrame(rows).set_index("date")


# --------------------------------------------------------------------------- #
# Live providers (best-effort; fall back to demo on any failure)
# --------------------------------------------------------------------------- #

def _finnhub_quote(ticker: str, key: str) -> Quote | None:
    try:
        import requests

        resp = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": ticker, "token": key},
            timeout=8,
        )
        resp.raise_for_status()
        d = resp.json()
        # Finnhub returns c=current, pc=previous close. Zero means no data.
        if not d or d.get("c") in (None, 0):
            return None
        return Quote(ticker=ticker, price=float(d["c"]), prev_close=float(d["pc"]))
    except Exception:
        return None


def _yfinance_candles(ticker: str, days: int) -> pd.DataFrame | None:
    try:
        import yfinance as yf

        period = f"{max(days, 7)}d"
        df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if df.empty:
            return None
        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )[["open", "high", "low", "close", "volume"]]
        df.index = pd.to_datetime(df.index).date
        df.index.name = "date"
        return df
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Public API (cached when running under Streamlit)
# --------------------------------------------------------------------------- #

def _maybe_cache(ttl: int):
    """Use st.cache_data when inside Streamlit, otherwise a no-op decorator.

    This lets the same functions be imported by the headless pipeline script
    without dragging in Streamlit's caching machinery.
    """
    # Headless callers (pipeline, tests) set this so we never import Streamlit's
    # script-runner machinery, which would otherwise log context warnings.
    import os

    if os.environ.get("HEADLESS") == "1":
        return lambda fn: fn

    try:
        import streamlit as st

        # Only use Streamlit's cache when a real script run context exists;
        # otherwise return a plain pass-through decorator.
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return lambda fn: fn
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda fn: fn


@_maybe_cache(ttl=config.QUOTE_TTL)
def get_quote(ticker: str) -> Quote:
    """Return a quote, using live data if available else demo data."""
    key = config.finnhub_key()
    if key:
        live = _finnhub_quote(ticker, key)
        if live is not None:
            return live
    return _demo_quote(ticker)


@_maybe_cache(ttl=config.CANDLE_TTL)
def get_candles(ticker: str, days: int = 90) -> pd.DataFrame:
    """Return historical OHLCV. Live history via yfinance, else demo data."""
    if config.is_live():
        live = _yfinance_candles(ticker, days)
        if live is not None and len(live) >= 2:
            return live
    return _demo_candles(ticker, days)
