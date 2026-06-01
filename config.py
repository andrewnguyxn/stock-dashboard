"""Central configuration for the dashboard.

Holdings are defined here for the demo. In a production version these would
live in a database or be uploaded via CSV, but a static dict keeps the project
runnable out of the box with zero setup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Holding:
    """A single portfolio position."""

    ticker: str
    shares: float
    cost_basis: float  # average price paid per share


# The demo portfolio. Edit this list or wire it to a CSV / DB later.
HOLDINGS: list[Holding] = [
    Holding("NVDA", 20, 309.50),
    Holding("MSFT", 30, 292.00),
    Holding("AAPL", 50, 152.80),
    Holding("SPY", 25, 468.20),
    Holding("TSLA", 15, 261.40),
    Holding("AMZN", 12, 173.90),
]

BENCHMARK = "SPY"  # used for the "vs market" comparison

# Cache time-to-live in seconds. Tuned so a portfolio of this size stays well
# under Finnhub's 60 req/min free-tier limit even with several users.
QUOTE_TTL = 60      # live prices refresh at most once a minute
CANDLE_TTL = 3600   # historical candles change slowly; cache for an hour


def finnhub_key() -> str | None:
    """Return the Finnhub API key from env or Streamlit secrets, if present.

    Returns None when no key is configured, which puts the app in demo mode.
    """
    key = os.environ.get("FINNHUB_API_KEY")
    if key:
        return key
    # Streamlit secrets are only importable when running inside Streamlit.
    try:
        import streamlit as st

        return st.secrets.get("FINNHUB_API_KEY")  # type: ignore[no-any-return]
    except Exception:
        return None


def is_live() -> bool:
    """True when a real data source is configured, False for demo mode."""
    return finnhub_key() is not None
