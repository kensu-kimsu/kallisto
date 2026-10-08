"""LLM decision prompt and validation for the simulation-only scalping study."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime

from openai import OpenAI

MODEL = "gpt-5.6-luna"
MIN_TARGET_PCT = 0.004
MIN_CONFIDENCE = 0.58


def build_prompt(state: dict, candidates: list[dict], now_et: datetime) -> str:
    payload = [
        {
            "ticker": c["ticker"],
            "name": c.get("name"),
            "universe": c["universe"],
            "premarket_volume": c.get("premarket_volume"),
            "premarket_change_pct": c.get("premarket_change_pct"),
            "technical": c.get("technical"),
            "fundamental": c.get("fundamental", {}),
        }
        for c in candidates
    ]

    return f"""
You are the autonomous decision engine for a SIMULATED professional intraday scalping experiment.

Current New York time: {now_et.isoformat()}
Starting capital: $1,000 USD
Current uncommitted cash: ${state['cash']:.2f}
Open simulated positions: {json.dumps(state['positions'], default=str)}

PRIMARY JOB
Behave like a disciplined professional intraday scalper: identify only liquid,
well-defined short-duration setups, enter when the supplied evidence is aligned,
and avoid turning a scalp into an investment. The deterministic engine controls
position size, stop distance, total exposure, daily loss limits and forced exits.

RESEARCH OBJECTIVE
Seek positive risk-adjusted capital growth and attempt to outperform both the
S&P 500 and Nasdaq-100 over six months. Outperformance is an objective, not a guarantee.

SETUPS TO LOOK FOR
Prefer one of these evidence-backed patterns when the supplied data supports it:
1. VWAP reclaim/rejection with trend confirmation.
2. Opening-range breakout/breakdown with meaningful relative volume.
3. EMA 9/20 trend continuation after a pullback toward VWAP/EMA.
4. Failed breakout/breakdown reversal when momentum and VWAP positioning confirm it.
5. Strong premarket leader continuation only when regular-session price/volume confirms it.

PROFESSIONAL DISCIPLINE
- Do not trade merely because a ticker appears in the candidate list.
- But when a clear, liquid setup exists, choose the best opportunity instead of
  defaulting to cash through excessive caution.
- Prefer one or two high-quality ideas over many mediocre ideas.
- Avoid chasing an extended move far from VWAP unless momentum and relative volume remain strong.
- Do not invent catalysts, headlines, Level 2/order-book information, hidden order flow,
  proprietary signals or fundamentals that were not supplied.
- Long and synthetic 1x short ideas are both allowed.
- If evidence is conflicting or no setup has acceptable reward/risk, return no trade.

ANALYSIS INPUTS
Use only the supplied data. Technical evidence includes price, VWAP, EMA 9/20,
RSI(14), MACD, ATR, opening-range behavior, relative volume, premarket volume and gap.
Fundamental context is secondary and may include market cap, float, beta, valuation,
profitability, growth, leverage and short interest.

SIMULATION RULES
- Simulation only. No live brokerage orders are placed.
- LONG and synthetic 1x SHORT positions are allowed.
- No leverage and no options.
- Whole shares only.
- Every position must be flat before 16:00 ET.
- No new entries after 15:30 ET.
- The proposed target must be plausible for an intraday scalp; use 0.004 or higher.
- The deterministic risk engine may raise the target to preserve minimum reward/risk.
- Synthetic short-sale proceeds do not become new buying power.
- There is no fixed daily trade-count target. Do not force weak trades.

CANDIDATES
{json.dumps(payload, indent=2, default=str)}

Return JSON only in this exact shape:
{{
  "trades": [
    {{
      "ticker": "XYZ",
      "side": "LONG",
      "target_pct": 0.008,
      "confidence": 0.72,
      "rationale": "brief rationale tied only to supplied evidence"
    }}
  ]
}}

Allowed side values: LONG or SHORT.
target_pct must be 0.004 or higher.
confidence must be between 0 and 1.
"""


def call_model(prompt: str) -> tuple[dict, dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        reasoning={"effort": "low"},
    )
    text = (response.output_text or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc

    usage = response.usage
    tokens = {
        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
    }
    return payload, tokens


def validate_proposals(payload: dict, allowed_tickers: set[str]) -> list[dict]:
    trades = payload.get("trades", [])
    if not isinstance(trades, list):
        return []

    valid = []
    seen = set()
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

        if ticker not in allowed_tickers or ticker in seen:
            continue
        if side not in {"LONG", "SHORT"}:
            continue
        if not math.isfinite(target_pct) or target_pct < MIN_TARGET_PCT:
            continue
        if not math.isfinite(confidence) or not MIN_CONFIDENCE <= confidence <= 1:
            continue
        if not rationale:
            continue

        seen.add(ticker)
        valid.append({
            "ticker": ticker,
            "side": side,
            "target_pct": target_pct,
            "confidence": confidence,
            "rationale": rationale,
        })
    return valid
