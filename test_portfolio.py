"""Unit tests for the pure computation layer.

Run with:  pytest -q
These cover the parts that must be correct — portfolio math and indicators —
using hand-checked numbers rather than live data.
"""

from __future__ import annotations

import pandas as pd

from src import config
from src.data import Quote
from src.portfolio import build_position, build_summary, Summary, Position
from src.indicators import sma, ema, rsi, latest_rsi


def test_position_pnl_math():
    h = config.Holding("TEST", shares=10, cost_basis=100.0)
    q = Quote("TEST", price=110.0, prev_close=105.0)
    p = build_position(h, q)

    assert p.value == 1100.0
    assert p.cost == 1000.0
    assert round(p.day_change_pct, 4) == round((110 - 105) / 105 * 100, 4)
    assert p.total_return_pct == 10.0


def test_summary_rollup_and_weights():
    positions = [
        Position("A", 10, 100, price=110, prev_close=100),  # value 1100
        Position("B", 5, 200, price=200, prev_close=200),   # value 1000
    ]
    s = Summary(
        total_value=sum(p.value for p in positions),
        total_cost=sum(p.cost for p in positions),
        day_change_value=sum(p.value - p.shares * p.prev_close for p in positions),
        positions=positions,
    )
    assert s.total_value == 2100
    weights = s.weights()
    assert round(weights["A"], 2) == round(1100 / 2100 * 100, 2)
    assert s.best().ticker == "A"   # A moved +10%, B moved 0%
    assert s.worst().ticker == "B"


def test_build_summary_runs_on_demo_data():
    s = build_summary()
    assert len(s.positions) == len(config.HOLDINGS)
    assert s.total_value > 0


def test_sma_and_ema_lengths_match_input():
    close = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert len(sma(close, 2)) == len(close)
    assert len(ema(close, 2)) == len(close)


def test_rsi_bounds():
    # A steadily rising series should have a high RSI; bounds always 0-100.
    rising = pd.Series(range(1, 40), dtype=float)
    val = latest_rsi(rising)
    assert 0 <= val <= 100
    assert val > 50  # uptrend => above midline

    series = rsi(pd.Series([5, 5, 5, 5, 5], dtype=float))
    assert (series.between(0, 100)).all()
