"""LLM decision prompt and validation for the simulation-only scalping study."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime

from openai import OpenAI

MODEL = "gpt-5.6-luna"
MIN_TARGET_PCT = 0.015
MIN_CONFIDENCE = 0.60


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
You are the autonomous decision engine for a SIMULATED intraday scalping research experiment.

Current New York time: {now_et.isoformat()}
Starting capital: $1,000 USD
Current uncommitted cash: ${state['cash']:.2f}
Open simulated positions: {json.dumps(state['positions'], default=str)}

RESEARCH OBJECTIVE
Seek positive risk-adjusted capital growth and attempt to outperform both the
S&P 500 and Nasdaq-100 over six months. Outperformance is an objective, not a guarantee.

CANDIDATE SELECTION
The candidate list contains the highest premarket-volume names found inside:
1. eligible major-exchange U.S.-listed microcaps below $300M market cap
2. the Nasdaq Titan universe

ANALYSIS INPUTS
Use only the supplied data. Technical evidence includes VWAP, EMA 9/20,
RSI(14), MACD, ATR, opening-range breakout/breakdown, relative volume,
premarket volume and premarket gap. Fundamental context may include market cap,
float, beta, valuation, profitability, growth, leverage and short interest.

These are widely used public market-analysis concepts. Do not claim access to
proprietary Wall Street models, hidden order flow, Level 2 data, undisclosed
fundamentals, or news that was not supplied.

SIMULATION RULES
- Simulation only. No live brokerage orders are placed.
- LONG and synthetic 1x SHORT positions are allowed.
- No leverage.
- No options.
- Whole shares only.
- Every position must be flat before 16:00 ET.
- No new entries after 15:15 ET.
- Every proposed trade must target at least 1.5% from the simulated entry.
- A deterministic risk engine chooses the final share count and stop distance.
- Synthetic short-sale proceeds do not become new buying power.
- There is no fixed daily trade-count limit, but do not force weak trades.
- Prefer alignment between price/volume trend, VWAP, momentum, volatility,
  opening-range behavior and the available fundamental context.
- If the evidence is weak or conflicting, return no trade.

CANDIDATES
{json.dumps(payload, indent=2, default=str)}

Return JSON only in this exact shape:
{{
  "trades": [
    {{
      "ticker": "XYZ",
      "side": "LONG",
      "target_pct": 0.015,
      "confidence": 0.72,
      "rationale": "brief supplied-evidence rationale"
    }}
  ]
}}

Allowed side values: LONG or SHORT.
target_pct must be 0.015 or higher.
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
