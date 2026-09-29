from __future__ import annotations

import json
import math
from pathlib import Path

SETTINGS_PATH = Path(__file__).with_name("experiment_settings.json")


def _load_policy(experiment: str) -> dict:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        settings = json.load(f)

    common = settings["risk_management"]
    specific = common[experiment]

    return {
        "minimum_cash_reserve_pct": float(common["minimum_cash_reserve_pct"]),
        "max_gross_exposure_pct": float(common["max_gross_exposure_pct"]),
        "max_total_open_risk_pct": float(common["max_total_open_risk_pct"]),
        "stop_updates_may_not_loosen": bool(common["stop_updates_may_not_loosen"]),
        "max_position_pct": float(specific["max_position_pct"]),
        "max_risk_per_trade_pct": float(specific["max_risk_per_trade_pct"]),
        "max_open_positions": int(specific["max_open_positions"]),
        "min_stop_distance_pct": float(specific["min_stop_distance_pct"]),
        "max_stop_distance_pct": float(specific["max_stop_distance_pct"]),
    }


def describe_risk_policy(experiment: str) -> str:
    p = _load_policy(experiment)
    return (
        f"- Keep at least {p['minimum_cash_reserve_pct']:.0%} of current equity in cash after BUY orders.\n"
        f"- Gross long exposure may not exceed {p['max_gross_exposure_pct']:.0%} of equity.\n"
        f"- Maximum single position: {p['max_position_pct']:.0%} of equity.\n"
        f"- Maximum planned loss to stop per new BUY: {p['max_risk_per_trade_pct']:.1%} of equity.\n"
        f"- Maximum aggregate planned open-position risk: {p['max_total_open_risk_pct']:.0%} of equity.\n"
        f"- Maximum open positions: {p['max_open_positions']}.\n"
        f"- BUY stop distance: {p['min_stop_distance_pct']:.0%} to {p['max_stop_distance_pct']:.0%}.\n"
        "- Existing stops may be tightened but not loosened.\n"
        "- Same-session SELL proceeds are not assumed available for BUY orders."
    )


def _num(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _positions(libb) -> dict:
    portfolio = getattr(libb, "portfolio", None)
    if portfolio is None or getattr(portfolio, "empty", True):
        return {}

    rows = portfolio.to_dict("records")
    out = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).upper().strip()
        shares = _num(row.get("shares"))
        if not ticker or shares is None or shares <= 0:
            continue
        market_price = _num(row.get("market_price"))
        market_value = _num(row.get("market_value"))
        if market_value is None and market_price is not None:
            market_value = shares * market_price
        out[ticker] = {
            "shares": shares,
            "market_price": market_price,
            "market_value": market_value or 0.0,
            "stop_loss": _num(row.get("stop_loss")),
        }
    return out


def validate_portfolio_risk(orders: dict, experiment: str, libb) -> list[str]:
    p = _load_policy(experiment)
    positions = _positions(libb)
    current_cash = float(libb.cash)
    current_exposure = sum(x["market_value"] for x in positions.values())
    equity = current_cash + current_exposure

    if equity <= 0:
        return ["Risk engine could not determine positive portfolio equity."]

    errors = []
    total_buy_commitment = 0.0
    total_new_risk = 0.0
    projected_values = {k: v["market_value"] for k, v in positions.items()}
    buy_tickers = set()

    current_open_risk = 0.0
    for ticker, pos in positions.items():
        if pos["market_price"] is None or pos["stop_loss"] is None:
            errors.append(f"Existing position {ticker} lacks data needed to measure stop risk.")
            continue
        current_open_risk += pos["shares"] * max(pos["market_price"] - pos["stop_loss"], 0.0)

    for n, order in enumerate(orders.get("orders", []), start=1):
        action = str(order.get("action", "")).lower().strip()
        ticker = str(order.get("ticker", "")).upper().strip()
        shares = order.get("shares")
        limit_price = _num(order.get("limit_price"))
        stop_loss = _num(order.get("stop_loss"))

        if action == "b" and isinstance(shares, int) and not isinstance(shares, bool) and shares > 0 and limit_price and stop_loss and limit_price > stop_loss:
            notional = shares * limit_price
            planned_loss = shares * (limit_price - stop_loss)
            stop_distance = (limit_price - stop_loss) / limit_price

            total_buy_commitment += notional
            total_new_risk += planned_loss
            buy_tickers.add(ticker)
            projected_values[ticker] = projected_values.get(ticker, 0.0) + notional

            if projected_values[ticker] > equity * p["max_position_pct"] + 1e-9:
                errors.append(f"Order {n}: projected {ticker} position exceeds the {p['max_position_pct']:.0%} position cap.")

            if planned_loss > equity * p["max_risk_per_trade_pct"] + 1e-9:
                errors.append(f"Order {n}: planned stop loss exceeds the {p['max_risk_per_trade_pct']:.1%} per-trade risk cap.")

            if stop_distance < p["min_stop_distance_pct"] - 1e-12 or stop_distance > p["max_stop_distance_pct"] + 1e-12:
                errors.append(f"Order {n}: BUY stop distance {stop_distance:.1%} is outside the allowed range.")

            if ticker in positions and positions[ticker]["stop_loss"] is not None and stop_loss < positions[ticker]["stop_loss"] - 1e-9:
                errors.append(f"Order {n}: ADD would loosen {ticker}'s existing stop.")

        if action == "u" and ticker in positions and stop_loss is not None:
            existing_stop = positions[ticker]["stop_loss"]
            market_price = positions[ticker]["market_price"]
            if p["stop_updates_may_not_loosen"] and existing_stop is not None and stop_loss < existing_stop - 1e-9:
                errors.append(f"Order {n}: stop update would loosen {ticker}'s existing stop.")
            if market_price is not None and stop_loss >= market_price:
                errors.append(f"Order {n}: updated stop for {ticker} must stay below current market price.")

    projected_cash = current_cash - total_buy_commitment
    if projected_cash < equity * p["minimum_cash_reserve_pct"] - 1e-9:
        errors.append(f"Projected cash would fall below the {p['minimum_cash_reserve_pct']:.0%} reserve.")

    projected_exposure = current_exposure + total_buy_commitment
    if projected_exposure > equity * p["max_gross_exposure_pct"] + 1e-9:
        errors.append(f"Projected gross exposure would exceed {p['max_gross_exposure_pct']:.0%} of equity.")

    if current_open_risk + total_new_risk > equity * p["max_total_open_risk_pct"] + 1e-9:
        errors.append(f"Projected planned open-position risk would exceed {p['max_total_open_risk_pct']:.0%} of equity.")

    if len(set(positions) | buy_tickers) > p["max_open_positions"]:
        errors.append(f"Projected open positions would exceed the {p['max_open_positions']}-position limit.")

    return errors
