"""Forward-only fee-adjusted risk accounting for simulation-only V1.2."""

from __future__ import annotations

import csv
from pathlib import Path

from user_side.personal_experiment.scalping_fees import fee_adjusted_trade, round_trip_fees
from user_side.personal_experiment.scalping_state import TRADE_LOG


def fee_adjusted_snapshot(state: dict, gross_equity: float, prices: dict[str, float] | None = None, *, day: str | None = None, trade_log: Path = TRADE_LOG) -> dict:
    session_day = str(day or state.get("session_date") or "")
    prior_fees = today_fees = today_realized_net = 0.0
    completed_today = 0
    traded_tickers: set[str] = set()
    if trade_log.exists():
        with trade_log.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                date = str(row.get("session_date") or "")
                if not date or date > session_day:
                    continue
                adjusted = fee_adjusted_trade(row)
                fees = float(adjusted["fees_usd"])
                if date < session_day:
                    prior_fees += fees
                else:
                    today_fees += fees
                    today_realized_net += float(adjusted["net_pnl_usd"])
                    completed_today += 1
                    traded_tickers.add(str(row.get("ticker") or ""))
    open_fee_reserve = 0.0
    for ticker, position in state.get("positions", {}).items():
        price = float((prices or {}).get(ticker, position["entry_price"]))
        open_fee_reserve += float(round_trip_fees(
            side=position["side"], shares=int(position["shares"]),
            entry_price=float(position["entry_price"]), exit_price=price,
        )["total_fee"])
        traded_tickers.add(ticker)
    start_net = float(state["session_start_equity"]) - prior_fees
    net_equity = float(gross_equity) - prior_fees - today_fees - open_fee_reserve
    return {
        "net_equity": net_equity,
        "session_start_net_equity": start_net,
        "session_net_return_pct": 100 * (net_equity / start_net - 1) if start_net > 0 else -100.0,
        "today_realized_net_usd": today_realized_net,
        "today_realized_net_pct": 100 * today_realized_net / start_net if start_net > 0 else -100.0,
        "today_completed_trades": completed_today,
        "today_traded_tickers": sorted(traded_tickers),
        "modeled_fees_today_usd": today_fees,
        "open_fee_reserve_usd": open_fee_reserve,
    }


def v12_entry_allowed(state: dict, snapshot: dict, config: dict) -> bool:
    """Preserve historical net losses; anchor V1.2 prospective net drawdown separately."""
    if config.get("version") != "V1.2":
        return True
    day = str(state.get("session_date") or "")
    net_equity = float(snapshot["net_equity"])
    if "v12_net_high_water_mark" not in state:
        state["v12_net_high_water_mark"] = net_equity
        state["v12_net_start_equity"] = net_equity
        state["v12_net_start_session"] = day
    peak = max(float(state["v12_net_high_water_mark"]), net_equity)
    state["v12_net_high_water_mark"] = peak
    state["v12_entries_today"] = max(int(state.get("v12_entries_today", 0)), int(snapshot["today_completed_trades"]) + len(state.get("positions", {})))
    state["v12_tickers_traded_today"] = sorted(set(state.get("v12_tickers_traded_today", [])) | set(snapshot["today_traded_tickers"]))
    if float(snapshot["today_realized_net_pct"]) >= 100 * float(config.get("daily_net_target_pct", 0.01)):
        state["v12_target_hit_session"] = day
    if state.get("v12_target_hit_session") == day:
        return False
    if net_equity <= 0:
        state["paused"] = True
        return False
    if float(snapshot["session_net_return_pct"]) <= -100 * float(config.get("daily_net_loss_limit_pct", 0.015)):
        state["paused"] = True
        return False
    if net_equity <= peak * (1 - float(config.get("v12_net_drawdown_pause_pct", 0.10))):
        state["paused"] = True
        return False
    if int(state["v12_entries_today"]) >= int(config.get("max_trades_per_day", 2)):
        return False
    return not bool(state.get("paused"))
