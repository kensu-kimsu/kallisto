"""Mirror new Kallisto simulation events into a Moomoo REST paper account.

This runner is intentionally a *shadow execution* layer:
- the six-month simulation remains the research source of truth;
- Moomoo paper receives only decisions created after paper mode is armed;
- old decisions are never replayed into the broker;
- live-money endpoints do not exist in this module.

The runner is safe to call after every Azure simulation cycle.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from user_side.personal_experiment.broker.moomoo_rest_paper import MoomooRestPaperBroker
from user_side.personal_experiment.broker.safety import OrderIntent
from user_side.personal_experiment.scalping_state import DECISION_LOG, RUN_ROOT

NY = ZoneInfo("America/New_York")
SHADOW_STATE = RUN_ROOT / "moomoo_shadow_state.json"
PAPER_LOG = RUN_ROOT / "moomoo_paper_log.jsonl"


def paper_enabled() -> bool:
    return os.environ.get("KALLISTO_MOOMOO_PAPER_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _read_decisions() -> list[dict]:
    if not DECISION_LOG.exists():
        return []
    rows = []
    for raw in DECISION_LOG.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if row.get("status") == "LLM_DECISION" and row.get("llm_called") is True:
            rows.append(row)
    rows.sort(key=lambda row: str(row.get("timestamp_et") or ""))
    return rows


def _load_state() -> dict:
    if not SHADOW_STATE.exists():
        return {
            "armed": False,
            "last_seen_decision_timestamp": "",
            "paper_account_id": "",
            "last_broker_positions": {},
            "last_broker_equity": None,
        }
    return json.loads(SHADOW_STATE.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    SHADOW_STATE.parent.mkdir(parents=True, exist_ok=True)
    SHADOW_STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _log(payload: dict) -> None:
    PAPER_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PAPER_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _event_key(timestamp: str, action: str, ticker: str, side: str, shares: int) -> str:
    raw = f"{timestamp}|{action}|{ticker.upper()}|{side.upper()}|{int(shares)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _remark(key: str) -> str:
    return f"Kallisto:{key}"


def run_paper_shadow_cycle(now_et: datetime | None = None) -> dict:
    if not paper_enabled():
        return {"enabled": False, "status": "PAPER_DISABLED"}

    now_et = now_et or datetime.now(NY)
    decisions = _read_decisions()
    state = _load_state()

    # First enabled invocation is an arming boundary. Never replay the historical
    # experiment into a newly connected broker account.
    if not state.get("armed"):
        latest = str(decisions[-1].get("timestamp_et") or "") if decisions else ""
        state.update(
            {
                "armed": True,
                "armed_at_et": now_et.isoformat(),
                "last_seen_decision_timestamp": latest,
            }
        )
        _save_state(state)
        _log(
            {
                "timestamp_et": now_et.isoformat(),
                "status": "PAPER_ARMED_NO_HISTORICAL_REPLAY",
                "last_seen_decision_timestamp": latest,
            }
        )
        return {"enabled": True, "status": "PAPER_ARMED_NO_HISTORICAL_REPLAY"}

    broker = MoomooRestPaperBroker.from_env()
    before = broker.snapshot()
    state["paper_account_id"] = before.account_id
    state["last_broker_positions"] = before.positions
    state["last_broker_equity"] = before.total_assets

    last_seen = str(state.get("last_seen_decision_timestamp") or "")
    pending = [
        row for row in decisions
        if str(row.get("timestamp_et") or "") > last_seen
    ]

    submitted = 0
    blocked = 0
    duplicates = 0

    for row in pending:
        timestamp = str(row.get("timestamp_et") or "")
        quote_time = datetime.fromisoformat(timestamp)
        strategy_version = str(row.get("strategy_version") or "V1.0")

        # Closed positions are risk-reducing and are processed before new entries.
        for pos in row.get("closed_positions") or []:
            ticker = str(pos.get("ticker") or "").upper().strip()
            side = str(pos.get("side") or "").upper().strip()
            shares = int(float(pos.get("shares") or 0))
            if not ticker or shares < 1 or side not in {"LONG", "SHORT"}:
                continue
            key = _event_key(timestamp, "CLOSE", ticker, side, shares)
            try:
                result = broker.submit_market_close(
                    ticker=ticker,
                    original_side=side,
                    qty=shares,
                    remark=_remark(key),
                )
                submitted += int(result.get("submitted") is True)
                duplicates += int(result.get("duplicate") is True)
                _log(
                    {
                        "timestamp_et": now_et.isoformat(),
                        "source_decision_et": timestamp,
                        "status": "PAPER_CLOSE",
                        "event_key": key,
                        "ticker": ticker,
                        "side": side,
                        "shares": shares,
                        "broker_result": result,
                    }
                )
            except Exception as exc:
                blocked += 1
                _log(
                    {
                        "timestamp_et": now_et.isoformat(),
                        "source_decision_et": timestamp,
                        "status": "PAPER_CLOSE_ERROR",
                        "event_key": key,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )

        # Refresh broker equity before entry safety checks.
        snap = broker.snapshot()
        start_equity = float(state.get("paper_session_start_equity") or snap.total_assets)
        if state.get("paper_session_date") != str(now_et.date()):
            state["paper_session_date"] = str(now_et.date())
            state["paper_session_start_equity"] = snap.total_assets
            start_equity = snap.total_assets

        for pos in row.get("opened_positions") or []:
            ticker = str(pos.get("ticker") or "").upper().strip()
            side = str(pos.get("side") or "").upper().strip()
            shares = int(float(pos.get("shares") or 0))
            entry_price = float(pos.get("entry_price") or 0.0)
            if not ticker or shares < 1 or entry_price <= 0 or side not in {"LONG", "SHORT"}:
                continue
            key = _event_key(timestamp, "OPEN", ticker, side, shares)
            intent = OrderIntent(
                ticker=ticker,
                side=side,
                qty=shares,
                limit_price=entry_price,
                session_date=str(quote_time.date()),
                strategy_version=strategy_version,
                reason="PAPER_SHADOW_ENTRY",
            )
            try:
                result = broker.submit_market_entry(
                    intent=intent,
                    quote_time=quote_time,
                    now=now_et,
                    session_start_equity=start_equity,
                    current_equity=snap.total_assets,
                    remark=_remark(key),
                )
                submitted += int(result.get("submitted") is True)
                duplicates += int(result.get("duplicate") is True)
                blocked += int(
                    result.get("submitted") is not True and result.get("duplicate") is not True
                )
                _log(
                    {
                        "timestamp_et": now_et.isoformat(),
                        "source_decision_et": timestamp,
                        "status": "PAPER_ENTRY",
                        "event_key": key,
                        "ticker": ticker,
                        "side": side,
                        "shares": shares,
                        "broker_result": result,
                    }
                )
            except Exception as exc:
                blocked += 1
                _log(
                    {
                        "timestamp_et": now_et.isoformat(),
                        "source_decision_et": timestamp,
                        "status": "PAPER_ENTRY_ERROR",
                        "event_key": key,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )

        # We advance only after the complete source decision has been attempted.
        # Broker remarks make a retry idempotent if Azure crashes between submit
        # and state persistence.
        state["last_seen_decision_timestamp"] = timestamp
        _save_state(state)

    after = broker.snapshot()
    state["last_broker_positions"] = after.positions
    state["last_broker_equity"] = after.total_assets
    state["last_cycle_et"] = now_et.isoformat()
    _save_state(state)

    result = {
        "enabled": True,
        "status": "PAPER_CYCLE_OK",
        "account_id": after.account_id,
        "source_decisions_processed": len(pending),
        "orders_submitted": submitted,
        "duplicates_skipped": duplicates,
        "orders_blocked_or_failed": blocked,
        "paper_equity": after.total_assets,
        "paper_positions": after.positions,
        "open_orders": len(after.open_orders),
    }
    _log({"timestamp_et": now_et.isoformat(), **result})
    return result
