"""Deterministic risk and fill model for the simulation-only scalping study."""

from __future__ import annotations

from datetime import datetime

from user_side.personal_experiment.scalping_state import (
    TRADE_FIELDS,
    TRADE_LOG,
    append_row,
)

RISK_PER_TRADE_PCT = 0.005
MAX_OPEN_RISK_PCT = 0.015
MAX_GROSS_EXPOSURE_PCT = 0.90
MAX_POSITION_PCT = 0.25
MIN_CASH_RESERVE_PCT = 0.10
DAILY_LOSS_LIMIT_PCT = 0.02
PORTFOLIO_DRAWDOWN_PAUSE_PCT = 0.10
REWARD_TO_RISK_FLOOR = 1.5
MIN_TARGET_PCT = 0.015


def mark_to_market(state: dict, prices: dict[str, float]) -> float:
    equity = float(state["cash"])
    for ticker, pos in state.get("positions", {}).items():
        current = float(prices.get(ticker, pos["entry_price"]))
        shares = int(pos["shares"])
        if pos["side"] == "LONG":
            equity += shares * current
        else:
            pnl = shares * (float(pos["entry_price"]) - current)
            equity += float(pos["reserved_capital"]) + pnl
    return equity


def stop_pct(universe: str, atr_pct: float) -> float:
    # Microcaps receive a wider volatility allowance than large-cap Titans.
    if universe == "microcap":
        return min(max(float(atr_pct or 0), 0.010), 0.025)
    return min(max(float(atr_pct or 0), 0.005), 0.0125)


def open_simulated_trade(
    *,
    state: dict,
    proposal: dict,
    candidate: dict,
    now_et: datetime,
    current_equity: float,
) -> dict | None:
    ticker = proposal["ticker"]
    if ticker in state["positions"]:
        return None

    if current_equity <= float(state["session_start_equity"]) * (1 - DAILY_LOSS_LIMIT_PCT):
        state["paused"] = True
        return None
    if current_equity <= float(state["high_water_mark"]) * (1 - PORTFOLIO_DRAWDOWN_PAUSE_PCT):
        state["paused"] = True
        return None

    tech = candidate.get("technical") or {}
    raw_price = float(tech.get("price") or 0)
    if raw_price <= 0:
        return None

    universe = candidate["universe"]
    stop_distance = stop_pct(universe, float(tech.get("atr_pct") or 0))
    target_pct = max(
        float(proposal["target_pct"]),
        MIN_TARGET_PCT,
        stop_distance * REWARD_TO_RISK_FLOOR,
    )

    # Conservative hypothetical slippage assumptions.
    slippage = 0.0020 if universe == "microcap" else 0.0005
    if proposal["side"] == "LONG":
        entry = raw_price * (1 + slippage)
        stop = entry * (1 - stop_distance)
        target = entry * (1 + target_pct)
    else:
        entry = raw_price * (1 - slippage)
        stop = entry * (1 + stop_distance)
        target = entry * (1 - target_pct)

    per_share_risk = abs(entry - stop)
    if per_share_risk <= 0:
        return None

    gross = sum(
        int(pos["shares"]) * float(pos["entry_price"])
        for pos in state["positions"].values()
    )
    open_risk = sum(
        int(pos["shares"]) * abs(float(pos["entry_price"]) - float(pos["stop_price"]))
        for pos in state["positions"].values()
    )

    shares_by_trade_risk = int((current_equity * RISK_PER_TRADE_PCT) / per_share_risk)
    shares_by_open_risk = int(
        max(0.0, current_equity * MAX_OPEN_RISK_PCT - open_risk) / per_share_risk
    )
    gross_capacity = max(0.0, current_equity * MAX_GROSS_EXPOSURE_PCT - gross)
    cash_capacity = max(
        0.0,
        float(state["cash"]) - current_equity * MIN_CASH_RESERVE_PCT,
    )
    notional_capacity = min(
        current_equity * MAX_POSITION_PCT,
        gross_capacity,
        cash_capacity,
    )
    shares_by_notional = int(notional_capacity / entry)
    shares = min(shares_by_trade_risk, shares_by_open_risk, shares_by_notional)

    if shares < 1:
        return None

    # For synthetic shorts, notional is held as collateral instead of adding
    # short-sale proceeds to buying power. This keeps exposure effectively 1x.
    reserved_capital = shares * entry
    state["cash"] = float(state["cash"]) - reserved_capital
    state["positions"][ticker] = {
        "ticker": ticker,
        "universe": universe,
        "side": proposal["side"],
        "shares": shares,
        "entry_price": round(entry, 6),
        "stop_price": round(stop, 6),
        "target_price": round(target, 6),
        "target_pct": round(target_pct, 6),
        "opened_at": now_et.isoformat(),
        "reserved_capital": round(reserved_capital, 6),
        "confidence": proposal["confidence"],
        "rationale": proposal["rationale"],
    }
    return state["positions"][ticker]


def close_simulated_trade(
    *,
    state: dict,
    ticker: str,
    exit_price: float,
    reason: str,
    now_et: datetime,
) -> dict:
    pos = state["positions"].pop(ticker)
    shares = int(pos["shares"])
    entry = float(pos["entry_price"])
    exit_price = float(exit_price)

    if pos["side"] == "LONG":
        pnl = shares * (exit_price - entry)
        state["cash"] = float(state["cash"]) + shares * exit_price
    else:
        pnl = shares * (entry - exit_price)
        state["cash"] = float(state["cash"]) + float(pos["reserved_capital"]) + pnl

    row = {
        "session_date": str(now_et.date()),
        "opened_at": pos["opened_at"],
        "closed_at": now_et.isoformat(),
        "ticker": ticker,
        "universe": pos["universe"],
        "side": pos["side"],
        "shares": shares,
        "entry_price": round(entry, 6),
        "exit_price": round(exit_price, 6),
        "stop_price": pos["stop_price"],
        "target_price": pos["target_price"],
        "target_pct": pos["target_pct"],
        "pnl_usd": round(pnl, 4),
        "return_pct": round((pnl / float(pos["reserved_capital"])) * 100, 4),
        "exit_reason": reason,
        "confidence": pos["confidence"],
        "rationale": pos["rationale"],
    }
    append_row(TRADE_LOG, TRADE_FIELDS, row)
    return row


def evaluate_bar(pos: dict, bar) -> tuple[float, str] | None:
    high = float(bar["high"])
    low = float(bar["low"])
    stop = float(pos["stop_price"])
    target = float(pos["target_price"])

    if pos["side"] == "LONG":
        stop_hit = low <= stop
        target_hit = high >= target
    else:
        stop_hit = high >= stop
        target_hit = low <= target

    # With 5-minute OHLC data we cannot know the exact intrabar sequence.
    # If both levels are touched in one bar, assume the stop happened first.
    if stop_hit:
        return stop, "STOP_FIRST_SAME_BAR" if target_hit else "STOP"
    if target_hit:
        return target, "TARGET"
    return None
