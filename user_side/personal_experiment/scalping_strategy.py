"""LLM decision prompt and validation for the simulation-only Kallisto study."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime

from openai import OpenAI

from user_side.personal_experiment.scalping_api_costs import record_api_call

MODEL = "gpt-5.6-luna"
MIN_TARGET_PCT = 0.004
MIN_CONFIDENCE = 0.58


def build_prompt(state: dict, candidates: list[dict], now_et: datetime, config: dict | None = None, track_name: str = "Kallisto Adaptive") -> str:
    config = config or {}
    min_confidence = float(config.get("min_confidence", MIN_CONFIDENCE))
    titan_min = float(config.get("titan_min_target_pct", MIN_TARGET_PCT))
    microcap_min = float(config.get("microcap_min_target_pct", 0.009))
    learning_notes = str(config.get("learning_notes", "Original Kallisto V1 rules only."))
    fee_multiple = float(config.get("fee_gate_min_gross_to_fees", 1.50))
    min_net_profit_pct = float(config.get("fee_gate_min_net_profit_pct", 0.0025))
    version = str(config.get("version", "V1.0"))
    payload = [{
        "ticker": c["ticker"], "name": c.get("name"), "universe": c["universe"],
        "selection_source": c.get("selection_source", "premarket"),
        "selection_volume": c.get("selection_volume"),
        "premarket_volume": c.get("premarket_volume"), "premarket_change_pct": c.get("premarket_change_pct"),
        "technical": c.get("technical"), "fundamental": c.get("fundamental", {}),
    } for c in candidates]

    return f"""
You are the autonomous decision engine for the {track_name} in a SIMULATED professional intraday scalping experiment.

Strategy version: {version}
Current New York time: {now_et.isoformat()}
Starting capital: $1,000 USD
Current uncommitted cash: ${state['cash']:.2f}
Open simulated positions: {json.dumps(state['positions'], default=str)}

PRIMARY JOB
Behave like a disciplined professional-style intraday scalper: identify only liquid,
well-defined short-duration setups, enter when supplied evidence is aligned, and avoid
turning a scalp into an investment. Deterministic code controls sizing, stops, exposure,
daily loss limits and forced exits.

RESEARCH OBJECTIVE
Seek positive risk-adjusted capital growth and attempt to outperform both the S&P 500
and Nasdaq-100 over six months. Outperformance is an objective, not a guarantee.

SETUPS TO LOOK FOR
1. VWAP reclaim/rejection with trend confirmation.
2. Opening-range breakout/breakdown with meaningful relative volume.
3. EMA 9/20 trend continuation after a pullback toward VWAP/EMA.
4. Failed breakout/breakdown reversal when momentum and VWAP positioning confirm it.
5. Strong premarket leader continuation only when regular-session price/volume confirms it.

CURRENT EVIDENCE-BASED LEARNING NOTES
{learning_notes}

DATA-SOURCE DISCIPLINE
- `selection_source=premarket` means Yahoo supplied genuine 04:00-09:29 ET extended-hours activity.
- `selection_source=regular_session_fallback` means extended-hours volume was unavailable and the ticker was selected using observed same-day regular-session activity instead.
- Never describe fallback candidates as premarket leaders or invent missing premarket statistics.
- When fallback data is used, base the decision primarily on the supplied regular-session technical evidence.

DISCIPLINE
- Do not trade merely because a ticker appears in the candidate list.
- When a clear liquid setup exists, choose the best opportunity instead of excessive cash defaulting.
- Prefer one or two high-quality ideas over many mediocre ideas.
- Avoid chasing moves far from VWAP unless momentum and relative volume remain strong.
- Do not invent catalysts, headlines, Level 2/order-book information, hidden order flow or proprietary signals.
- Long and synthetic 1x short ideas are both allowed.
- If evidence conflicts or reward/risk is unacceptable, return no trade.

SIMULATION RULES
- Simulation only. No live brokerage orders.
- Whole shares, no leverage, no options, flat before 16:00 ET.
- No new entries after 15:30 ET.
- Titan target proposals must be at least {titan_min:.4f}; microcap targets at least {microcap_min:.4f}.
- Proposal confidence must be at least {min_confidence:.2f} to pass validation.
- Deterministic code can raise target distance to maintain reward/risk.
- There is no daily trade-count target. Do not force weak trades.
- Transaction costs matter. Prefer fewer, higher-conviction setups with enough price movement to justify a round trip.
- Deterministic code will reject an entry unless expected gross target profit is at least {fee_multiple:.2f}x modeled Moomoo AU round-trip fees and expected net target profit is at least {min_net_profit_pct * 100:.2f}% of current equity.
- Do not lower target quality merely to generate more trades.

CANDIDATES
{json.dumps(payload, indent=2, default=str)}

Return JSON only:
{{"trades":[{{"ticker":"XYZ","side":"LONG","target_pct":0.008,"confidence":0.72,"rationale":"brief rationale tied only to supplied evidence"}}]}}
"""


def call_model(prompt: str, now_et: datetime) -> tuple[dict, dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(model=MODEL, input=prompt, reasoning={"effort": "low"})
    usage = response.usage
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    details = getattr(usage, "input_tokens_details", None) if usage else None
    cached_input_tokens = int(getattr(details, "cached_tokens", 0) or 0) if details else 0
    cost_row = record_api_call(now_et, MODEL, input_tokens, cached_input_tokens, output_tokens)
    tokens = {"input_tokens": input_tokens, "cached_input_tokens": cached_input_tokens, "output_tokens": output_tokens, "estimated_cost_usd": float(cost_row["total_cost_usd"])}
    text = (response.output_text or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc
    return payload, tokens


def validate_proposals(payload: dict, allowed_tickers: set[str], config: dict | None = None, candidate_map: dict[str, dict] | None = None) -> list[dict]:
    config = config or {}
    min_confidence = float(config.get("min_confidence", MIN_CONFIDENCE))
    trades = payload.get("trades", [])
    if not isinstance(trades, list):
        return []
    valid, seen = [], set()
    for trade in trades:
        if not isinstance(trade, dict):
            continue
        try:
            ticker = str(trade["ticker"]).upper().strip()
            side = str(trade["side"]).upper().strip()
            target_pct = float(trade["target_pct"])
            confidence = float(trade["confidence"])
            rationale = str(trade["rationale"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if ticker not in allowed_tickers or ticker in seen or side not in {"LONG", "SHORT"}:
            continue
        universe = ((candidate_map or {}).get(ticker) or {}).get("universe", "titan")
        floor = float(config.get("microcap_min_target_pct" if universe == "microcap" else "titan_min_target_pct", 0.009 if universe == "microcap" else MIN_TARGET_PCT))
        if not math.isfinite(target_pct) or target_pct < floor:
            continue
        if not math.isfinite(confidence) or not min_confidence <= confidence <= 1:
            continue
        if not rationale:
            continue
        seen.add(ticker)
        valid.append({"ticker": ticker, "side": side, "target_pct": target_pct, "confidence": confidence, "rationale": rationale})
    return valid
