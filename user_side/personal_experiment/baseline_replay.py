"""Retrospective frozen-V1 risk-control baseline for the simulation study.

This replay uses the adaptive track's realized trade sequence but resizes each
trade with the original V1.0 risk settings. It is a counterfactual control for
risk-parameter changes, not an independent second LLM. It therefore does not
measure trade-selection changes caused by adaptive prompt notes.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from user_side.personal_experiment.scalping_fees import round_trip_fees
from user_side.personal_experiment.scalping_state import TRADE_LOG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = PROJECT_ROOT / "user_side" / "runs" / "scalping_v1"
RUN_ROOT = Path(os.environ.get("SCALPING_RUN_ROOT", str(DEFAULT_RUN_ROOT)))
BASELINE_REPLAY_LOG = RUN_ROOT / "baseline_replay.csv"
FIELDS = ["date", "ending_equity", "cumulative_return_pct", "trades"]

STARTING_EQUITY = 1000.0
RISK_PER_TRADE_PCT = 0.005
MAX_POSITION_PCT = 0.30
MIN_CASH_RESERVE_PCT = 0.15


def _rows() -> list[dict]:
    if not TRADE_LOG.exists():
        return []
    with TRADE_LOG.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return sorted(rows, key=lambda r: r.get("closed_at") or r.get("opened_at") or "")


def _shares_for_trade(equity: float, trade: dict) -> int:
    entry = float(trade["entry_price"])
    stop = float(trade["stop_price"])
    per_share_risk = abs(entry - stop)
    # The live simulation may have moved the stored stop to breakeven before the
    # trade closed. If so, reconstruct the minimum original V1 stop distance so
    # the frozen replay does not incorrectly size the trade at zero shares.
    if entry > 0 and per_share_risk < entry * 0.0001:
        fallback_stop_pct = 0.006 if trade.get("universe") == "microcap" else 0.003
        per_share_risk = entry * fallback_stop_pct
    if entry <= 0 or per_share_risk <= 0:
        return 0
    by_risk = int((equity * RISK_PER_TRADE_PCT) / per_share_risk)
    by_position = int((equity * MAX_POSITION_PCT) / entry)
    by_cash = int((equity * (1 - MIN_CASH_RESERVE_PCT)) / entry)
    return max(0, min(by_risk, by_position, by_cash))


def refresh_baseline_replay() -> Path:
    """Rebuild the frozen V1 risk baseline from completed adaptive trades."""
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    equity = STARTING_EQUITY
    by_date: dict[str, dict] = defaultdict(lambda: {"trades": 0, "ending_equity": STARTING_EQUITY})
    for trade in _rows():
        try:
            shares = _shares_for_trade(equity, trade)
            entry = float(trade["entry_price"])
            exit_price = float(trade["exit_price"])
        except (KeyError, TypeError, ValueError):
            continue
        gross_pnl = shares * (entry - exit_price) if trade.get("side") == "SHORT" else shares * (exit_price - entry)
        fees = round_trip_fees(
            side=trade.get("side", "LONG"),
            shares=shares,
            entry_price=entry,
            exit_price=exit_price,
        )
        pnl = gross_pnl - float(fees["total_fee"])
        equity += pnl
        day = trade.get("session_date") or datetime.fromisoformat(trade["closed_at"]).date().isoformat()
        by_date[day]["trades"] += 1
        by_date[day]["ending_equity"] = equity

    with BASELINE_REPLAY_LOG.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for day in sorted(by_date):
            end = float(by_date[day]["ending_equity"])
            writer.writerow({
                "date": day,
                "ending_equity": round(end, 4),
                "cumulative_return_pct": round((end / STARTING_EQUITY - 1) * 100, 4),
                "trades": by_date[day]["trades"],
            })
    return BASELINE_REPLAY_LOG
