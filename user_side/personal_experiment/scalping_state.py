"""Persistent state for the simulation-only scalping experiment."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = PROJECT_ROOT / "user_side" / "runs" / "scalping_v1"
RUN_ROOT = Path(os.environ.get("SCALPING_RUN_ROOT", str(DEFAULT_RUN_ROOT)))
STATE_PATH = RUN_ROOT / "portfolio_state.json"
TRADE_LOG = RUN_ROOT / "trade_log.csv"
DAILY_LOG = RUN_ROOT / "daily_performance.csv"
DECISION_LOG = RUN_ROOT / "decision_log.jsonl"
BASELINE_STATE_PATH = RUN_ROOT / "baseline_portfolio_state.json"
BASELINE_TRADE_LOG = RUN_ROOT / "baseline_trade_log.csv"
BASELINE_DAILY_LOG = RUN_ROOT / "baseline_daily_performance.csv"
BASELINE_DECISION_LOG = RUN_ROOT / "baseline_decision_log.jsonl"

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


def _initial_state(starting_cash: float) -> dict:
    return {
        "starting_cash": starting_cash,
        "cash": starting_cash,
        "positions": {},
        "session_date": None,
        "session_start_equity": starting_cash,
        "high_water_mark": starting_cash,
        "last_cycle_et": None,
        "last_decision_et": None,
        "premarket_candidates": [],
        "benchmark_base": {},
        "paused": False,
    }


def _ensure_track(state_path: Path, trade_log: Path, daily_log: Path, decision_log: Path, starting_cash: float) -> None:
    if not state_path.exists():
        state_path.write_text(json.dumps(_initial_state(starting_cash), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path, fields in ((trade_log, TRADE_FIELDS), (daily_log, DAILY_FIELDS)):
        if not path.exists():
            with path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()
    if not decision_log.exists():
        decision_log.write_text("", encoding="utf-8")


def ensure_state(starting_cash: float = 1000.0) -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    _ensure_track(STATE_PATH, TRADE_LOG, DAILY_LOG, DECISION_LOG, starting_cash)
    _ensure_track(BASELINE_STATE_PATH, BASELINE_TRADE_LOG, BASELINE_DAILY_LOG, BASELINE_DECISION_LOG, starting_cash)


def _load(path: Path) -> dict:
    state = json.loads(path.read_text(encoding="utf-8"))
    state.setdefault("last_decision_et", None)
    state.setdefault("last_cycle_et", None)
    state.setdefault("premarket_candidates", [])
    state.setdefault("paused", False)
    return state


def load_state() -> dict:
    return _load(STATE_PATH)


def load_baseline_state() -> dict:
    return _load(BASELINE_STATE_PATH)


def _save(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_state(state: dict) -> None:
    _save(STATE_PATH, state)


def save_baseline_state(state: dict) -> None:
    _save(BASELINE_STATE_PATH, state)


def append_row(path: Path, fields: list[str], row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=fields).writerow({key: row.get(key, "") for key in fields})


def append_decision(payload: dict, path: Path = DECISION_LOG) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
