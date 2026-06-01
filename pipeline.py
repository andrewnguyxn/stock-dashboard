"""Automated data pipeline.

This is what the scheduled GitHub Action runs each morning. It has no Streamlit
dependency — it's a plain script that fetches data, computes everything, writes
a JSON snapshot and a Markdown digest, and reports run metrics.

Run locally with:  python pipeline.py
"""

from __future__ import annotations

import os

# Tell the data layer we're running headless so it skips Streamlit's caching
# machinery entirely (avoids spurious context warnings on a scheduled run).
os.environ["HEADLESS"] = "1"

import json
import time
from pathlib import Path

from src import config
from src.portfolio import build_summary
from src.digest import generate, benchmark_day_pct

DATA = Path("data")
SNAPSHOT = DATA / "snapshot.json"
DIGEST_MD = DATA / "digest.md"


def run() -> dict:
    start = time.time()
    DATA.mkdir(exist_ok=True)

    summary = build_summary()
    bench = benchmark_day_pct()
    digest = generate(summary, bench)

    # One quote per holding + one for the benchmark.
    api_calls = len(config.HOLDINGS) + 1
    duration = round(time.time() - start, 2)

    snapshot = {
        "generated_at": digest.generated_at,
        "mode": "live" if config.is_live() else "demo",
        "totals": {
            "value": round(summary.total_value, 2),
            "day_change_value": round(summary.day_change_value, 2),
            "day_change_pct": round(summary.day_change_pct, 2),
            "total_return_pct": round(summary.total_return_pct, 2),
        },
        "positions": [
            {
                "ticker": p.ticker,
                "price": round(p.price, 2),
                "day_change_pct": round(p.day_change_pct, 2),
                "value": round(p.value, 2),
                "total_return_pct": round(p.total_return_pct, 2),
                "weight": round(summary.weights()[p.ticker], 2),
            }
            for p in summary.positions
        ],
        "digest": {
            "text": digest.text,
            "tags": digest.tags,
            "generated_at": digest.generated_at,
        },
        "metrics": {
            "tickers": len(config.HOLDINGS),
            "api_calls": api_calls,
            "duration_s": duration,
        },
    }

    SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
    DIGEST_MD.write_text(
        f"# Daily digest — {digest.generated_at}\n\n{digest.text}\n\n"
        + "\n".join(f"- {t}" for t in digest.tags)
        + "\n"
    )

    print(f"[pipeline] mode={snapshot['mode']} "
          f"value=${summary.total_value:,.0f} "
          f"day={summary.day_change_pct:+.2f}% "
          f"calls={api_calls} duration={duration}s")
    print(f"[pipeline] digest: {digest.text}")
    return snapshot


if __name__ == "__main__":
    run()
