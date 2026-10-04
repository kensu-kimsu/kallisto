"""Persistent state for the simulation-only scalping experiment."""

from __future__ import annotations

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = PROJECT_ROOT / "user_side" / "runs" / "scalping_v1"
STATE_PATH = RUN_ROOT / "portfolio_state.json"
TRADE_LOG = RUN_ROOT / "trade_log.csv"
DAILY_LOG = RUN_ROOT / "daily_performance.csv"
DECISION_LOG = RUN_ROOT / "decision_log.jsonl"

TRADE_FIELDS = [
    "session_date", "opened_at", "closed_at", "ticker", "universe", "side",
    "shares", "entry_price", "exit_price", "stop_price", "target_price",
    "target_pct", "pnl_usd", "return_pct", "exit_reason", "confidence", "rationale",
]
DAILY_FIELDS = [
    "date", "starting_equity", "ending_equity", "daily_return_pct",
    "cumulative_return_pct", "cash", "trades", "wins", "losses", "win_rate_pct",
    "sp500_normalized", "nasdaq100_normalized",
]


def ensure_state(starting_cash: float = 1000.0) -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        save_state({
            "starting_cash": starting_cash,
            "cash": starting_cash,
            "positions": {},
            "session_date": None,
            "session_start_equity": starting_cash,
            "high_water_mark": starting_cash,
            "last_cycle_et": None,
            "premarket_candidates": [],
            "benchmark_base": {},
            "paused": False,
        })

    for path, fields in ((TRADE_LOG, TRADE_FIELDS), (DAILY_LOG, DAILY_FIELDS)):
        if not path.exists():
            with path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()

    if not DECISION_LOG.exists():
        DECISION_LOG.write_text("", encoding="utf-8")


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_row(path: Path, fields: list[str], row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=fields).writerow(
            {key: row.get(key, "") for key in fields}
        )


def append_decision(payload: dict) -> None:
    with DECISION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
