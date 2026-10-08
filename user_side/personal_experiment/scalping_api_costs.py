"""OpenAI API cost accounting for Final V1.

Pricing is a snapshot for the model used by the experiment. Actual OpenAI
billing remains the source of truth. Update PRICING_USD_PER_MILLION if the
model or published rates change.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = PROJECT_ROOT / "user_side" / "runs" / "scalping_v1"
COST_LOG = RUN_ROOT / "api_costs.csv"
README_PATH = PROJECT_ROOT / "README.md"

COST_FIELDS = [
    "timestamp_et",
    "session_date",
    "model",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "input_cost_usd",
    "cached_input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
]

# OpenAI published GPT-5.6 Luna standard text pricing snapshot, 2026-10-08.
# USD per 1M tokens.
PRICING_USD_PER_MILLION = {
    "gpt-5.6-luna": {
        "input": 0.20,
        "cached_input": 0.02,
        "output": 1.20,
    },
}

README_START = "<!-- API_COST_SUMMARY_START -->"
README_END = "<!-- API_COST_SUMMARY_END -->"


def ensure_cost_log() -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    if COST_LOG.exists():
        return
    with COST_LOG.open("w", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=COST_FIELDS).writeheader()


def _pricing(model: str) -> dict[str, float]:
    if model not in PRICING_USD_PER_MILLION:
        raise RuntimeError(
            f"No API pricing configured for {model}. "
            "Update PRICING_USD_PER_MILLION before continuing."
        )
    return PRICING_USD_PER_MILLION[model]


def calculate_cost(
    model: str,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
) -> dict[str, float]:
    rates = _pricing(model)
    cached = max(0, min(int(cached_input_tokens), int(input_tokens)))
    uncached = max(0, int(input_tokens) - cached)
    output = max(0, int(output_tokens))

    input_cost = uncached / 1_000_000 * rates["input"]
    cached_cost = cached / 1_000_000 * rates["cached_input"]
    output_cost = output / 1_000_000 * rates["output"]
    total = input_cost + cached_cost + output_cost

    return {
        "input_cost_usd": input_cost,
        "cached_input_cost_usd": cached_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": total,
    }


def record_api_call(
    *,
    timestamp_et: datetime,
    model: str,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
) -> dict:
    ensure_cost_log()
    costs = calculate_cost(
        model,
        input_tokens,
        cached_input_tokens,
        output_tokens,
    )
    row = {
        "timestamp_et": timestamp_et.isoformat(),
        "session_date": str(timestamp_et.date()),
        "model": model,
        "input_tokens": int(input_tokens),
        "cached_input_tokens": int(cached_input_tokens),
        "output_tokens": int(output_tokens),
        "input_cost_usd": f"{costs['input_cost_usd']:.8f}",
        "cached_input_cost_usd": f"{costs['cached_input_cost_usd']:.8f}",
        "output_cost_usd": f"{costs['output_cost_usd']:.8f}",
        "total_cost_usd": f"{costs['total_cost_usd']:.8f}",
    }
    with COST_LOG.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=COST_FIELDS).writerow(row)

    update_readme_cost_summary()
    return row


def _rows() -> list[dict]:
    ensure_cost_log()
    with COST_LOG.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def get_cost_summary() -> dict:
    rows = _rows()
    if not rows:
        return {
            "calls": 0,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "total_cost_usd": 0.0,
            "active_days": 0,
            "active_weeks": 0,
            "active_months": 0,
        }

    parsed_dates = [datetime.fromisoformat(r["timestamp_et"]) for r in rows]
    return {
        "calls": len(rows),
        "input_tokens": sum(int(r["input_tokens"]) for r in rows),
        "cached_input_tokens": sum(int(r["cached_input_tokens"]) for r in rows),
        "output_tokens": sum(int(r["output_tokens"]) for r in rows),
        "total_cost_usd": sum(float(r["total_cost_usd"]) for r in rows),
        "active_days": len({d.date() for d in parsed_dates}),
        "active_weeks": len({(d.isocalendar().year, d.isocalendar().week) for d in parsed_dates}),
        "active_months": len({(d.year, d.month) for d in parsed_dates}),
    }


def cost_for_date(session_date: str) -> float:
    return sum(
        float(row["total_cost_usd"])
        for row in _rows()
        if row["session_date"] == session_date
    )


def _avg(value: float, periods: int) -> float:
    return value / periods if periods else 0.0


def _avg_int(value: int, periods: int) -> float:
    return value / periods if periods else 0.0


def render_readme_table() -> str:
    s = get_cost_summary()
    total = s["total_cost_usd"]
    calls = s["calls"]
    inputs = s["input_tokens"]
    outputs = s["output_tokens"]

    periods = [
        ("Average daily", s["active_days"]),
        ("Average weekly", s["active_weeks"]),
        ("Average monthly", s["active_months"]),
    ]

    lines = [
        README_START,
        "| Cost period | API cost (USD) | API calls | Input tokens | Output tokens |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, count in periods:
        lines.append(
            f"| {label} | ${_avg(total, count):.4f} | "
            f"{_avg_int(calls, count):.1f} | "
            f"{_avg_int(inputs, count):,.0f} | "
            f"{_avg_int(outputs, count):,.0f} |"
        )
    lines.append(
        f"| **Total actual** | **${total:.4f}** | **{calls}** | "
        f"**{inputs:,}** | **{outputs:,}** |"
    )
    lines.append(README_END)
    return "\n".join(lines)


def update_readme_cost_summary() -> None:
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        return

    start = text.index(README_START)
    end = text.index(README_END) + len(README_END)
    updated = text[:start] + render_readme_table() + text[end:]
    if updated != text:
        README_PATH.write_text(updated, encoding="utf-8")
