"""Deterministic risk and fill model for the simulation-only scalping study."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from user_side.personal_experiment.scalping_fees import round_trip_fees
from user_side.personal_experiment.scalping_state import TRADE_FIELDS, TRADE_LOG, append_row

RISK_PER_TRADE_PCT = 0.005
MAX_OPEN_RISK_PCT = 0.015
MAX_GROSS_EXPOSURE_PCT = 0.75
MAX_POSITION_PCT = 0.30
MIN_CASH_RESERVE_PCT = 0.15
DAILY_LOSS_LIMIT_PCT = 0.02
PORTFOLIO_DRAWDOWN_PAUSE_PCT = 0.10
REWARD_TO_RISK_FLOOR = 1.5
MAX_OPEN_POSITIONS = 3
MAX_HOLD_MINUTES = 75
MIN_TARGET_BY_UNIVERSE = {"microcap": 0.009, "titan": 0.0045}
FEE_GATE_MIN_GROSS_TO_FEES = 1.50
FEE_GATE_MIN_NET_PROFIT_PCT = 0.0025


def _cfg(config: dict | None, key: str, default):
    return (config or {}).get(key, default)


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
    if universe == "microcap":
        return min(max(float(atr_pct or 0), 0.006), 0.018)
    return min(max(float(atr_pct or 0), 0.003), 0.009)


def open_simulated_trade(*, state: dict, proposal: dict, candidate: dict, now_et: datetime, current_equity: float, config: dict | None = None) -> dict | None:
    ticker = proposal["ticker"]
    if ticker in state["positions"]:
        return None
    if len(state.get("positions", {})) >= int(_cfg(config, "max_open_positions", MAX_OPEN_POSITIONS)):
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
    min_target = float(_cfg(config, "microcap_min_target_pct" if universe == "microcap" else "titan_min_target_pct", MIN_TARGET_BY_UNIVERSE.get(universe, 0.005)))
    rr_floor = float(_cfg(config, "reward_to_risk_floor", REWARD_TO_RISK_FLOOR))
    target_pct = max(float(proposal["target_pct"]), min_target, stop_distance * rr_floor)

    slippage = 0.0015 if universe == "microcap" else 0.0003
    if proposal["side"] == "LONG":
        entry, stop, target = raw_price * (1 + slippage), None, None
        stop = entry * (1 - stop_distance)
        target = entry * (1 + target_pct)
    else:
        entry = raw_price * (1 - slippage)
        stop = entry * (1 + stop_distance)
        target = entry * (1 - target_pct)

    per_share_risk = abs(entry - stop)
    if per_share_risk <= 0:
        return None

    gross = sum(int(pos["shares"]) * float(pos["entry_price"]) for pos in state["positions"].values())
    open_risk = sum(int(pos["shares"]) * abs(float(pos["entry_price"]) - float(pos["stop_price"])) for pos in state["positions"].values())
    risk_per_trade = float(_cfg(config, "risk_per_trade_pct", RISK_PER_TRADE_PCT))
    max_open_risk = float(_cfg(config, "max_open_risk_pct", MAX_OPEN_RISK_PCT))
    max_gross = float(_cfg(config, "max_gross_exposure_pct", MAX_GROSS_EXPOSURE_PCT))
    max_position = float(_cfg(config, "max_position_pct", MAX_POSITION_PCT))
    min_cash_reserve = float(_cfg(config, "min_cash_reserve_pct", MIN_CASH_RESERVE_PCT))

    shares_by_trade_risk = int((current_equity * risk_per_trade) / per_share_risk)
    shares_by_open_risk = int(max(0.0, current_equity * max_open_risk - open_risk) / per_share_risk)
    gross_capacity = max(0.0, current_equity * max_gross - gross)
    cash_capacity = max(0.0, float(state["cash"]) - current_equity * min_cash_reserve)
    notional_capacity = min(current_equity * max_position, gross_capacity, cash_capacity)
    shares_by_notional = int(notional_capacity / entry)
    shares = min(shares_by_trade_risk, shares_by_open_risk, shares_by_notional)
    if shares < 1:
        return None

    # Fee-aware viability gate. Kallisto should not take a scalp where the target
    # is mostly consumed by the intended broker's round-trip transaction costs.
    fee_estimate = round_trip_fees(
        side=proposal["side"],
        shares=shares,
        entry_price=entry,
        exit_price=target,
    )
    estimated_fees = float(fee_estimate["total_fee"])
    expected_gross_profit = shares * abs(target - entry)
    expected_net_profit = expected_gross_profit - estimated_fees
    fee_multiple = float(_cfg(config, "fee_gate_min_gross_to_fees", FEE_GATE_MIN_GROSS_TO_FEES))
    min_net_profit_pct = float(_cfg(config, "fee_gate_min_net_profit_pct", FEE_GATE_MIN_NET_PROFIT_PCT))
    if expected_gross_profit < estimated_fees * fee_multiple:
        return None
    if expected_net_profit < current_equity * min_net_profit_pct:
        return None

    reserved_capital = shares * entry
    state["cash"] = float(state["cash"]) - reserved_capital
    state["positions"][ticker] = {
        "ticker": ticker, "universe": universe, "side": proposal["side"], "shares": shares,
        "entry_price": round(entry, 6), "initial_stop_price": round(stop, 6), "stop_price": round(stop, 6),
        "target_price": round(target, 6), "target_pct": round(target_pct, 6), "opened_at": now_et.isoformat(),
        "reserved_capital": round(reserved_capital, 6), "confidence": proposal["confidence"],
        "rationale": proposal["rationale"], "breakeven_armed": False,
        "strategy_version": (config or {}).get("version", "V1.0"),
        "estimated_round_trip_fees": round(estimated_fees, 6),
        "expected_gross_profit_at_target": round(expected_gross_profit, 6),
        "expected_net_profit_at_target": round(expected_net_profit, 6),
    }
    return state["positions"][ticker]


def close_simulated_trade(*, state: dict, ticker: str, exit_price: float, reason: str, now_et: datetime, trade_log: Path = TRADE_LOG) -> dict:
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
        "session_date": str(now_et.date()), "opened_at": pos["opened_at"], "closed_at": now_et.isoformat(),
        "ticker": ticker, "universe": pos["universe"], "side": pos["side"], "shares": shares,
        "entry_price": round(entry, 6), "exit_price": round(exit_price, 6), "stop_price": pos["stop_price"],
        "target_price": pos["target_price"], "target_pct": pos["target_pct"], "pnl_usd": round(pnl, 4),
        "return_pct": round((pnl / float(pos["reserved_capital"])) * 100, 4), "exit_reason": reason,
        "confidence": pos["confidence"], "rationale": pos["rationale"],
    }
    append_row(trade_log, TRADE_FIELDS, row)
    return row


def evaluate_bar(pos: dict, bar, bar_time: datetime | None = None, config: dict | None = None) -> tuple[float, str] | None:
    high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
    stop, target = float(pos["stop_price"]), float(pos["target_price"])
    if pos["side"] == "LONG":
        stop_hit, target_hit = low <= stop, high >= target
    else:
        stop_hit, target_hit = high >= stop, low <= target
    if stop_hit:
        return stop, "STOP_FIRST_SAME_BAR" if target_hit else "STOP"
    if target_hit:
        return target, "TARGET"
    opened = datetime.fromisoformat(pos["opened_at"])
    max_hold = int(_cfg(config, "max_hold_minutes", MAX_HOLD_MINUTES))
    if bar_time is not None and bar_time - opened >= timedelta(minutes=max_hold):
        return close, "TIME_STOP"
    initial_stop = float(pos.get("initial_stop_price", pos["stop_price"]))
    one_r = abs(float(pos["entry_price"]) - initial_stop)
    if one_r > 0 and not pos.get("breakeven_armed"):
        if pos["side"] == "LONG" and close >= float(pos["entry_price"]) + one_r:
            pos["stop_price"] = round(float(pos["entry_price"]), 6)
            pos["breakeven_armed"] = True
        elif pos["side"] == "SHORT" and close <= float(pos["entry_price"]) - one_r:
            pos["stop_price"] = round(float(pos["entry_price"]), 6)
            pos["breakeven_armed"] = True
    return None
