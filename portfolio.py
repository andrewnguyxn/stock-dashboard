"""Portfolio computations.

Turns raw quotes + holdings into the numbers the UI and digest need:
per-position value and P&L, allocation weights, and a portfolio-level summary.
Pure functions over plain data so they're trivial to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config
from .data import Quote, get_quote


@dataclass
class Position:
    """A holding enriched with live pricing and computed P&L."""

    ticker: str
    shares: float
    cost_basis: float
    price: float
    prev_close: float

    @property
    def value(self) -> float:
        return self.shares * self.price

    @property
    def cost(self) -> float:
        return self.shares * self.cost_basis

    @property
    def day_change_pct(self) -> float:
        if self.prev_close == 0:
            return 0.0
        return ((self.price - self.prev_close) / self.prev_close) * 100

    @property
    def total_return_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return ((self.price - self.cost_basis) / self.cost_basis) * 100


@dataclass
class Summary:
    """Portfolio-level roll-up."""

    total_value: float
    total_cost: float
    day_change_value: float
    positions: list[Position]

    @property
    def day_change_pct(self) -> float:
        prev_value = self.total_value - self.day_change_value
        if prev_value == 0:
            return 0.0
        return (self.day_change_value / prev_value) * 100

    @property
    def total_return_value(self) -> float:
        return self.total_value - self.total_cost

    @property
    def total_return_pct(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return (self.total_return_value / self.total_cost) * 100

    def weights(self) -> dict[str, float]:
        """Each position's share of total value, as a percentage."""
        if self.total_value == 0:
            return {p.ticker: 0.0 for p in self.positions}
        return {p.ticker: p.value / self.total_value * 100 for p in self.positions}

    def best(self) -> Position:
        return max(self.positions, key=lambda p: p.day_change_pct)

    def worst(self) -> Position:
        return min(self.positions, key=lambda p: p.day_change_pct)


def build_position(holding: config.Holding, quote: Quote) -> Position:
    return Position(
        ticker=holding.ticker,
        shares=holding.shares,
        cost_basis=holding.cost_basis,
        price=quote.price,
        prev_close=quote.prev_close,
    )


def build_summary(holdings: list[config.Holding] | None = None) -> Summary:
    """Fetch quotes for all holdings and compute the full summary."""
    holdings = holdings or config.HOLDINGS
    positions: list[Position] = []
    for h in holdings:
        positions.append(build_position(h, get_quote(h.ticker)))

    total_value = sum(p.value for p in positions)
    total_cost = sum(p.cost for p in positions)
    day_change = sum(p.value - (p.shares * p.prev_close) for p in positions)

    return Summary(
        total_value=total_value,
        total_cost=total_cost,
        day_change_value=day_change,
        positions=positions,
    )
