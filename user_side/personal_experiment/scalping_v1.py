"""Final V1 autonomous intraday scalping simulation.

Simulation only: this module never connects to Moomoo or any other broker,
never submits live orders, and never moves money. It uses public market data,
LLM-generated hypotheses, deterministic risk limits, and hypothetical fills.
"""

from __future__ import annotations

import csv
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

from user_side.personal_experiment.scalping_engine import (
    DAILY_LOSS_LIMIT_PCT,
    close_simulated_trade,
    evaluate_bar,
    mark_to_market,
    open_simulated_trade,
)
from user_side.personal_experiment.scalping_market_data import (
    latest_price,
    scan_premarket,
    session_bars,
    technical_snapshot,
)
from user_side.personal_experiment.scalping_reporting import (
    create_daily_journal,
    refresh_chart,
)
from user_side.personal_experiment.scalping_state import (
    DAILY_FIELDS,
    DAILY_LOG,
    TRADE_LOG,
    append_decision,
    append_row,
    ensure_state,
    load_state,
    save_state,
)
from user_side.personal_experiment.scalping_strategy import (
    MODEL,
    build_prompt,
    call_model,
    validate_proposals,
)

NY = ZoneInfo("America/New_York")
STARTING_CASH = 1000.0
FIRST_SESSION = "2026-10-05"
PREMARKET_LEADERS_PER_UNIVERSE = 5
NEW_ENTRY_CUTOFF = time(15, 15)
FORCE_FLAT_TIME = time(15, 55)


def is_nyse_session(day) -> bool:
    schedule = mcal.get_calendar("NYSE").schedule(start_date=day, end_date=day)
    return not schedule.empty


def start_session(state: dict, now_et: datetime) -> None:
    if state.get("session_date") == str(now_et.date()):
        return
    if state.get("positions"):
        raise RuntimeError("Previous session still has open positions; refusing overnight carry.")
    state["session_date"] = str(now_et.date())
    state["session_start_equity"] = float(state["cash"])
    state["last_cycle_et"] = None
    state["premarket_candidates"] = []
    state["paused"] = False


def current_prices(state: dict, day) -> dict[str, float]:
    prices = {}
    for ticker, pos in state.get("positions", {}).items():
        price = latest_price(ticker, day)
        prices[ticker] = price if price is not None else float(pos["entry_price"])
    return prices


def monitor_positions(state: dict, now_et: datetime) -> list[dict]:
    closed = []
    for ticker in list(state.get("positions", {})):
        pos = state["positions"].get(ticker)
        bars = session_bars(ticker, now_et.date())
        if bars.empty:
            continue
        opened = datetime.fromisoformat(pos["opened_at"])
        bars = bars.loc[(bars.index > opened) & (bars.index <= now_et)]
        for ts, bar in bars.iterrows():
            result = evaluate_bar(pos, bar)
            if result is None:
                continue
            exit_price, reason = result
            closed.append(
                close_simulated_trade(
                    state=state,
                    ticker=ticker,
                    exit_price=exit_price,
                    reason=reason,
                    now_et=ts.to_pydatetime(),
                )
            )
            break
    return closed


def force_flat(state: dict, now_et: datetime) -> list[dict]:
    closed = []
    for ticker in list(state.get("positions", {})):
        price = latest_price(ticker, now_et.date())
        if price is None:
            continue
        closed.append(
            close_simulated_trade(
                state=state,
                ticker=ticker,
                exit_price=price,
                reason="FORCED_EOD_FLAT",
                now_et=now_et,
            )
        )
    return closed


def build_candidates(state: dict, now_et: datetime) -> list[dict]:
    if not state.get("premarket_candidates"):
        state["premarket_candidates"] = scan_premarket(
            now_et.date(),
            leaders_per_universe=PREMARKET_LEADERS_PER_UNIVERSE,
        )

    candidates = []
    for item in state["premarket_candidates"]:
        tech = technical_snapshot(item["ticker"], now_et.date())
        if tech is None:
            continue
        row = dict(item)
        row["technical"] = tech
        candidates.append(row)
    return candidates


def read_today_trades(day) -> list[dict]:
    with TRADE_LOG.open("r", encoding="utf-8", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("session_date") == str(day)]


def finish_day(state: dict, now_et: datetime) -> None:
    if state.get("positions"):
        raise RuntimeError("Cannot write daily summary while simulated positions remain open.")

    ending = float(state["cash"])
    start = float(state["session_start_equity"])
    daily_return = ((ending / start) - 1) * 100 if start else 0.0
    cumulative_return = ((ending / STARTING_CASH) - 1) * 100
    trades = read_today_trades(now_et.date())
    wins = sum(float(t["pnl_usd"]) > 0 for t in trades)
    losses = sum(float(t["pnl_usd"]) < 0 for t in trades)
    win_rate = (wins / len(trades) * 100) if trades else 0.0

    sp = latest_price("^GSPC", now_et.date())
    ndx = latest_price("^NDX", now_et.date())
    base = state.setdefault("benchmark_base", {})
    if sp is not None:
        base.setdefault("sp500", sp)
    if ndx is not None:
        base.setdefault("nasdaq100", ndx)

    sp_norm = 1000.0 * sp / base["sp500"] if sp and base.get("sp500") else 1000.0
    ndx_norm = 1000.0 * ndx / base["nasdaq100"] if ndx and base.get("nasdaq100") else 1000.0

    existing_dates = set()
    with DAILY_LOG.open("r", encoding="utf-8", newline="") as f:
        existing_dates = {row["date"] for row in csv.DictReader(f)}

    row = {
        "date": str(now_et.date()),
        "starting_equity": round(start, 4),
        "ending_equity": round(ending, 4),
        "daily_return_pct": round(daily_return, 4),
        "cumulative_return_pct": round(cumulative_return, 4),
        "cash": round(ending, 4),
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "sp500_normalized": round(sp_norm, 4),
        "nasdaq100_normalized": round(ndx_norm, 4),
    }

    if row["date"] not in existing_dates:
        append_row(DAILY_LOG, DAILY_FIELDS, row)
        create_daily_journal(row, trades)
        refresh_chart()

    state["high_water_mark"] = max(
        float(state.get("high_water_mark", ending)),
        ending,
    )


def main() -> None:
    ensure_state(STARTING_CASH)
    state = load_state()
    now_et = datetime.now(NY)

    print("=" * 68)
    print("FINAL V1 - AUTONOMOUS LLM SCALPING EXPERIMENT")
    print("SIMULATION ONLY - NO LIVE BROKERAGE ORDERS")
    print("=" * 68)
    print(f"New York time: {now_et.isoformat()}")

    if str(now_et.date()) < FIRST_SESSION:
        print(f"Experiment begins on NYSE session {FIRST_SESSION}.")
        return
    if not is_nyse_session(now_et.date()):
        print("NYSE is closed today.")
        return
    if now_et.time() < time(9, 30) or now_et.time() > time(16, 10):
        print("Outside the intraday experiment window.")
        return

    start_session(state, now_et)
    closed = monitor_positions(state, now_et)

    if now_et.time() >= FORCE_FLAT_TIME:
        closed.extend(force_flat(state, now_et))
        finish_day(state, now_et)
        state["last_cycle_et"] = now_et.isoformat()
        save_state(state)
        print(f"EOD flat complete. Positions closed this cycle: {len(closed)}")
        return

    prices = current_prices(state, now_et.date())
    equity = mark_to_market(state, prices)
    if equity <= float(state["session_start_equity"]) * (1 - DAILY_LOSS_LIMIT_PCT):
        state["paused"] = True

    if now_et.time() >= NEW_ENTRY_CUTOFF or state.get("paused"):
        state["last_cycle_et"] = now_et.isoformat()
        save_state(state)
        print("No new entries: entry cutoff or risk pause active.")
        return

    candidates = build_candidates(state, now_et)
    if not candidates:
        state["last_cycle_et"] = now_et.isoformat()
        save_state(state)
        print("No eligible premarket-volume candidates with usable intraday data.")
        return

    prompt = build_prompt(state, candidates, now_et)
    response, tokens = call_model(prompt)
    proposals = validate_proposals(
        response,
        {candidate["ticker"] for candidate in candidates},
    )
    candidate_map = {candidate["ticker"]: candidate for candidate in candidates}

    opened = []
    for proposal in proposals:
        prices = current_prices(state, now_et.date())
        equity = mark_to_market(state, prices)
        position = open_simulated_trade(
            state=state,
            proposal=proposal,
            candidate=candidate_map[proposal["ticker"]],
            now_et=now_et,
            current_equity=equity,
        )
        if position is not None:
            opened.append(position)

    append_decision({
        "timestamp_et": now_et.isoformat(),
        "model": MODEL,
        "tokens": tokens,
        "model_output": response,
        "accepted_proposals": proposals,
        "opened_positions": opened,
        "closed_positions": closed,
    })

    state["last_cycle_et"] = now_et.isoformat()
    save_state(state)
    print(
        f"Candidates: {len(candidates)} | proposals: {len(proposals)} | "
        f"opened: {len(opened)} | closed: {len(closed)}"
    )


if __name__ == "__main__":
    main()
