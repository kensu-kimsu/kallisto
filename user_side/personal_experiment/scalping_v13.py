"""Kallisto V1.3 isolated $5,000 paper-trading experiment.

Run with: python -m user_side.personal_experiment.scalping_v13
Never writes to the V1/V1.2 state or results. No live orders.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from user_side.personal_experiment.scalping_v1 import (
    NY, ENTRY_START, NEW_ENTRY_CUTOFF, FORCE_FLAT_TIME,
    is_nyse_session, scan_premarket_with_diagnostics, technical_snapshot,
)
from user_side.personal_experiment.scalping_strategy import build_prompt, call_model, validate_proposals
from user_side.personal_experiment.scalping_engine import open_simulated_trade, evaluate_bar, mark_to_market
from user_side.personal_experiment.scalping_market_data import session_bars, latest_price
from user_side.personal_experiment.scalping_fees import round_trip_fees

ROOT = Path(__file__).resolve().parents[2] / "user_side" / "runs" / "scalping_v13"
STATE_FILE = ROOT / "state.json"
DECISIONS = ROOT / "decisions.jsonl"
TRADES = ROOT / "trades.jsonl"
INITIAL_CAPITAL = 5000.0
CONFIG = {
    "version": "V1.3", "min_confidence": 0.72,
    "risk_per_trade_pct": 0.005, "max_open_risk_pct": 0.01,
    "max_gross_exposure_pct": 0.50, "max_position_pct": 0.45,
    "min_cash_reserve_pct": 0.30, "reward_to_risk_floor": 2.0,
    "max_open_positions": 1, "max_hold_minutes": 60,
    "titan_min_target_pct": 0.02, "fee_gate_min_gross_to_fees": 3.0,
    "fee_gate_min_net_profit_pct": 0.005, "fee_gate_min_net_to_risk": 1.25,
    "max_trades_per_day": 2, "allow_microcap_entries": False,
}
# This module is an isolated research configuration, not a live broker client.
def initial_state():
    return {"cash": INITIAL_CAPITAL, "positions": {}, "session_date": None,
            "session_start_equity": INITIAL_CAPITAL, "high_water_mark": INITIAL_CAPITAL,
            "paused": False, "v12_entries_today": 0,
            "v12_tickers_traded_today": [], "v12_target_hit_session": None}

def load():
    ROOT.mkdir(parents=True, exist_ok=True)
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else initial_state()

def save(state):
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.replace(STATE_FILE)

def log(path, row):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")

def main():
    now = datetime.now(NY)
    if not is_nyse_session(now.date()) or not ENTRY_START <= now.time() < FORCE_FLAT_TIME:
        return
    state = load()
    day = str(now.date())
    if state["session_date"] != day:
        if state["positions"]:
            raise RuntimeError("Unclosed position from previous session")
        state.update(session_date=day, session_start_equity=state["cash"],
                     paused=False, v12_entries_today=0,
                     v12_tickers_traded_today=[], v12_target_hit_session=None,
                     last_decision_et=None)
    # Positions are monitored and closed using the same bar-based simulation rules.
    for ticker in list(state["positions"]):
        pos = state["positions"][ticker]
        bars = session_bars(ticker, now.date())
        opened = datetime.fromisoformat(pos["opened_at"])
        for ts, bar in bars.loc[(bars.index > opened) & (bars.index <= now)].iterrows():
            outcome = evaluate_bar(pos, bar, ts.to_pydatetime(), CONFIG)
            if outcome:
                exit_price, reason = outcome
                shares = int(pos["shares"])
                gross_pnl = shares * (exit_price - pos["entry_price"]) * (1 if pos["side"] == "LONG" else -1)
                fees = round_trip_fees(side=pos["side"], shares=shares,
                    entry_price=pos["entry_price"], exit_price=exit_price)["total_fee"]
                state["cash"] += pos["reserved_capital"] + gross_pnl - fees
                log(TRADES, {"date": day, "ticker": ticker, "gross_pnl": gross_pnl,
                             "fees": fees, "net_pnl": gross_pnl - fees, "reason": reason})
                del state["positions"][ticker]
                break
    if now.time() >= NEW_ENTRY_CUTOFF or state["positions"] or state["paused"]:
        save(state)
        return
    if state.get("last_decision_et") and (now - datetime.fromisoformat(state["last_decision_et"])).total_seconds() < 900:
        save(state)
        return
    equity = mark_to_market(state, {})
    if equity <= state["session_start_equity"] * 0.985 or equity <= state["high_water_mark"] * 0.90:
        state["paused"] = True
        save(state)
        return
    budget = min(equity * CONFIG["max_position_pct"], equity * CONFIG["max_gross_exposure_pct"],
                 state["cash"] - equity * CONFIG["min_cash_reserve_pct"])
    leaders, diagnostics = scan_premarket_with_diagnostics(
        now.date(), leaders_per_universe=12, titan_only=True,
        max_share_price=max(0, budget / 1.001))
    candidates = []
    for row in leaders:
        tech = technical_snapshot(row["ticker"], now.date())
        if tech and 5 <= tech["price"] <= budget / 1.001:
            candidates.append({**row, "technical": tech})
    state["last_decision_et"] = now.isoformat()
    if not candidates:
        log(DECISIONS, {"date": day, "status": "NO_CANDIDATES", "diagnostics": diagnostics})
        save(state)
        return
    response, tokens = call_model(build_prompt(state, candidates, now, CONFIG, "Kallisto V1.3 $5k Paper"), now)
    mapping = {c["ticker"]: c for c in candidates}
    proposals = validate_proposals(response, set(mapping), CONFIG, mapping)
    opened = []
    for proposal in proposals:
        if state["positions"] or state["v12_entries_today"] >= CONFIG["max_trades_per_day"]:
            break
        position = open_simulated_trade(state=state, proposal=proposal, candidate=mapping[proposal["ticker"]],
            now_et=now, current_equity=equity, config=CONFIG, risk_equity=equity)
        if position:
            opened.append(proposal["ticker"])
    log(DECISIONS, {"date": day, "time": now.isoformat(), "candidates": len(candidates),
                    "proposals": proposals, "opened": opened, "model_output": response,
                    "tokens": tokens, "diagnostics": diagnostics})
    save(state)

if __name__ == "__main__":
    main()
