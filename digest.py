"""Daily digest generator.

Produces the plain-English morning summary shown at the top of the dashboard
and written to disk by the automated pipeline.

v1 is template-based: zero cost, no external calls, fully deterministic. The
README notes an optional upgrade to an LLM-written summary (Claude API) as a
future enhancement; the function signature stays the same so swapping the
implementation is a one-line change.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from portfolio import Summary
import config


@dataclass
class Digest:
    """A generated digest: a prose paragraph plus structured tags."""

    text: str
    tags: list[str]
    generated_at: str


def _fmt_pct(p: float) -> str:
    return f"{p:+.2f}%"


def generate(summary: Summary, benchmark_pct: float | None = None) -> Digest:
    """Build a digest from a portfolio summary.

    benchmark_pct is the day move of the benchmark (e.g. SPY) for comparison.
    """
    best = summary.best()
    worst = summary.worst()
    day = summary.day_change_pct

    direction = "gained" if day >= 0 else "slipped"
    parts: list[str] = [
        f"Your portfolio {direction} {_fmt_pct(day)} today, "
        f"now worth ${summary.total_value:,.0f}."
    ]

    if benchmark_pct is not None:
        verb = "outpacing" if day > benchmark_pct else "trailing"
        parts.append(
            f"That's {verb} the benchmark ({_fmt_pct(benchmark_pct)})."
        )

    parts.append(
        f"{best.ticker} led ({_fmt_pct(best.day_change_pct)}), "
        f"while {worst.ticker} lagged ({_fmt_pct(worst.day_change_pct)})."
    )

    tags = [
        f"{best.ticker} {_fmt_pct(best.day_change_pct)}",
        f"{worst.ticker} {_fmt_pct(worst.day_change_pct)}",
        f"{len(summary.positions)} holdings tracked",
    ]

    return Digest(
        text=" ".join(parts),
        tags=tags,
        generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def benchmark_day_pct() -> float | None:
    """Day move of the configured benchmark, for the digest comparison."""
    try:
        from .data import get_quote

        q = get_quote(config.BENCHMARK)
        return q.pct_change
    except Exception:
        return None
