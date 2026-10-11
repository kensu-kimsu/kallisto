"""Bounded self-evaluation for the simulation-only scalping experiment.

The adaptive track may tune a small allow-list of parameters. Hard portfolio
safety limits stay bounded by deterministic ranges and every change is versioned.
"""

from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from user_side.personal_experiment.scalping_api_costs import record_api_call
from user_side.personal_experiment.scalping_state import DAILY_LOG, TRADE_LOG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = PROJECT_ROOT / "user_side" / "runs" / "scalping_v1"
RUN_ROOT = Path(os.environ.get("SCALPING_RUN_ROOT", str(DEFAULT_RUN_ROOT)))
CONFIG_PATH = RUN_ROOT / "adaptive_config.json"
EVALUATION_LOG = RUN_ROOT / "weekly_evaluations.jsonl"
IMPROVEMENT_LOG = RUN_ROOT / "improvement_metrics.csv"
VERSION_LOG = RUN_ROOT / "strategy_versions.csv"
MODEL = "gpt-5.6-luna"

DEFAULT_CONFIG = {
    "version": "V1.0",
    "min_confidence": 0.58,
    "risk_per_trade_pct": 0.005,
    "max_open_risk_pct": 0.015,
    "max_gross_exposure_pct": 0.75,
    "max_position_pct": 0.30,
    "min_cash_reserve_pct": 0.15,
    "reward_to_risk_floor": 1.5,
    "max_open_positions": 3,
    "max_hold_minutes": 75,
    "microcap_min_target_pct": 0.009,
    "titan_min_target_pct": 0.0045,
    "learning_notes": "Use the original Final V1 setup priorities without adaptive preference changes.",
    "last_evaluation_session_count": 0,
    "last_change_session_count": 0,
}

# Deliberately narrow ranges. The evaluator cannot disable core risk controls.
BOUNDS = {
    "min_confidence": (0.55, 0.75),
    "risk_per_trade_pct": (0.003, 0.006),
    "max_open_risk_pct": (0.009, 0.018),
    "max_gross_exposure_pct": (0.50, 0.80),
    "max_position_pct": (0.20, 0.35),
    "min_cash_reserve_pct": (0.15, 0.30),
    "reward_to_risk_floor": (1.3, 2.0),
    "max_open_positions": (1, 3),
    "max_hold_minutes": (45, 90),
    "microcap_min_target_pct": (0.006, 0.015),
    "titan_min_target_pct": (0.0035, 0.008),
}

IMPROVEMENT_FIELDS = [
    "date", "version", "sessions", "trades", "rolling_5_return_pct",
    "rolling_5_sp500_pct", "rolling_5_nasdaq100_pct", "rolling_5_alpha_pct",
    "rolling_5_win_rate_pct", "rolling_5_profit_factor", "max_drawdown_pct",
    "adaptive_equity", "baseline_equity", "adaptive_vs_baseline_pct",
]
VERSION_FIELDS = [
    "effective_date", "version", "reason", "sessions", "trades", "config_json"
]


def ensure_learning_state() -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    if not EVALUATION_LOG.exists():
        EVALUATION_LOG.write_text("", encoding="utf-8")
    for path, fields in ((IMPROVEMENT_LOG, IMPROVEMENT_FIELDS), (VERSION_LOG, VERSION_FIELDS)):
        if not path.exists():
            with path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()
    if VERSION_LOG.stat().st_size <= len(",".join(VERSION_FIELDS)) + 2:
        _append_version(DEFAULT_CONFIG, "Initial frozen Final V1 adaptive configuration", 0, 0, "prelaunch")


def load_config() -> dict:
    ensure_learning_state()
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        pass
    return cfg


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def baseline_config() -> dict:
    """Permanent frozen V1 settings for the independent shadow baseline."""
    return dict(DEFAULT_CONFIG)


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _safe_float(value, default=0.0) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _profit_factor(trades: list[dict]) -> float:
    wins = sum(max(0.0, _safe_float(t.get("pnl_usd"))) for t in trades)
    losses = abs(sum(min(0.0, _safe_float(t.get("pnl_usd"))) for t in trades))
    if losses == 0:
        return 99.0 if wins > 0 else 0.0
    return wins / losses


def _max_drawdown(equities: list[float]) -> float:
    peak = None
    worst = 0.0
    for value in equities:
        if peak is None or value > peak:
            peak = value
        if peak and peak > 0:
            worst = min(worst, (value / peak - 1.0) * 100.0)
    return abs(worst)


def compute_metrics(baseline_daily_path: Path | None = None) -> dict:
    daily = _read_csv(DAILY_LOG)
    trades = _read_csv(TRADE_LOG)
    last5 = daily[-5:]
    dates = {r.get("date") for r in last5}
    last5_trades = [t for t in trades if t.get("session_date") in dates]

    if last5:
        first_start = _safe_float(last5[0].get("starting_equity"), 1000.0)
        last_end = _safe_float(last5[-1].get("ending_equity"), first_start)
        roll_return = ((last_end / first_start) - 1) * 100 if first_start else 0.0
        sp0 = _safe_float(last5[0].get("sp500_normalized"), 1000.0)
        sp1 = _safe_float(last5[-1].get("sp500_normalized"), sp0)
        nd0 = _safe_float(last5[0].get("nasdaq100_normalized"), 1000.0)
        nd1 = _safe_float(last5[-1].get("nasdaq100_normalized"), nd0)
        sp_ret = ((sp1 / sp0) - 1) * 100 if sp0 else 0.0
        nd_ret = ((nd1 / nd0) - 1) * 100 if nd0 else 0.0
        alpha = roll_return - max(sp_ret, nd_ret)
    else:
        roll_return = sp_ret = nd_ret = alpha = 0.0

    wins = sum(_safe_float(t.get("pnl_usd")) > 0 for t in last5_trades)
    win_rate = wins / len(last5_trades) * 100 if last5_trades else 0.0
    equities = [_safe_float(r.get("ending_equity"), 1000.0) for r in daily]
    adaptive_equity = equities[-1] if equities else 1000.0

    baseline_equity = 1000.0
    if baseline_daily_path:
        baseline_daily = _read_csv(baseline_daily_path)
        if baseline_daily:
            baseline_equity = _safe_float(baseline_daily[-1].get("ending_equity"), 1000.0)
    adaptive_vs_baseline = ((adaptive_equity / baseline_equity) - 1) * 100 if baseline_equity else 0.0

    return {
        "sessions": len(daily),
        "trades": len(trades),
        "rolling_5_return_pct": roll_return,
        "rolling_5_sp500_pct": sp_ret,
        "rolling_5_nasdaq100_pct": nd_ret,
        "rolling_5_alpha_pct": alpha,
        "rolling_5_win_rate_pct": win_rate,
        "rolling_5_profit_factor": _profit_factor(last5_trades),
        "max_drawdown_pct": _max_drawdown(equities),
        "adaptive_equity": adaptive_equity,
        "baseline_equity": baseline_equity,
        "adaptive_vs_baseline_pct": adaptive_vs_baseline,
    }


def record_improvement_snapshot(day: str, baseline_daily_path: Path | None = None) -> dict:
    ensure_learning_state()
    cfg = load_config()
    metrics = compute_metrics(baseline_daily_path)
    existing = _read_csv(IMPROVEMENT_LOG)
    if any(row.get("date") == day for row in existing):
        return metrics
    row = {"date": day, "version": cfg["version"], **metrics}
    with IMPROVEMENT_LOG.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=IMPROVEMENT_FIELDS).writerow(
            {k: round(v, 6) if isinstance(v, float) else v for k, v in row.items() if k in IMPROVEMENT_FIELDS}
        )
    return metrics


def _next_version(version: str) -> str:
    try:
        major, minor = version.lstrip("V").split(".", 1)
        return f"V{int(major)}.{int(minor) + 1}"
    except Exception:
        return "V1.1"


def _append_version(config: dict, reason: str, sessions: int, trades: int, day: str) -> None:
    with VERSION_LOG.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=VERSION_FIELDS).writerow({
            "effective_date": day,
            "version": config.get("version", "V1.0"),
            "reason": reason,
            "sessions": sessions,
            "trades": trades,
            "config_json": json.dumps(config, sort_keys=True),
        })


def _bounded_config(current: dict, proposal: dict) -> dict:
    new = dict(current)
    changes = proposal.get("changes", {}) if isinstance(proposal, dict) else {}
    for key, bounds in BOUNDS.items():
        if key not in changes:
            continue
        lo, hi = bounds
        try:
            value = float(changes[key])
        except (TypeError, ValueError):
            continue
        value = min(max(value, lo), hi)
        if key in {"max_open_positions", "max_hold_minutes"}:
            value = int(round(value))
        new[key] = value
    notes = str(proposal.get("learning_notes", "")).strip()[:1200]
    if notes:
        new["learning_notes"] = notes
    return new


def _call_evaluator(metrics: dict, current: dict, recent_trades: list[dict], now_et: datetime) -> tuple[dict, dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    prompt = f"""
You are the weekly research evaluator for a SIMULATION-ONLY intraday scalping experiment.
Your job is not to maximize activity. Diagnose the measured evidence and propose only
small, defensible parameter changes. Do not weaken safety limits outside supplied bounds.
Do not invent market data. If evidence is weak, recommend no change.

Current config:\n{json.dumps(current, indent=2)}
Measured metrics:\n{json.dumps(metrics, indent=2)}
Recent closed trades (max 40):\n{json.dumps(recent_trades[-40:], indent=2)}
Allowed parameter bounds:\n{json.dumps(BOUNDS, indent=2)}

Return JSON only:
{{
  "summary": "what worked/failed and why, based only on measured evidence",
  "changes": {{"parameter_name": numeric_value}},
  "learning_notes": "short setup/time-of-day/direction guidance for future prompts",
  "confidence": 0.0
}}
"""
    client = OpenAI(api_key=api_key)
    response = client.responses.create(model=MODEL, input=prompt, reasoning={"effort": "low"})
    usage = response.usage
    inp = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    details = getattr(usage, "input_tokens_details", None) if usage else None
    cached = int(getattr(details, "cached_tokens", 0) or 0) if details else 0
    cost = record_api_call(now_et, MODEL, inp, cached, out)
    tokens = {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out, "estimated_cost_usd": float(cost["total_cost_usd"])}
    try:
        return json.loads((response.output_text or "").strip()), tokens
    except json.JSONDecodeError:
        return {"summary": "Evaluator returned invalid JSON; no changes applied.", "changes": {}, "learning_notes": "", "confidence": 0.0}, tokens


def maybe_weekly_evaluate(now_et: datetime, baseline_daily_path: Path | None = None) -> dict | None:
    """Evaluate every 5 completed sessions; allow config changes only every 10 sessions.

    The first weekly review is observation-only unless enough evidence exists. A change
    requires at least 20 completed trades and 10 sessions since the last change.
    """
    ensure_learning_state()
    current = load_config()
    metrics = compute_metrics(baseline_daily_path)
    sessions = int(metrics["sessions"])
    trades_count = int(metrics["trades"])
    if sessions < 5 or sessions - int(current.get("last_evaluation_session_count", 0)) < 5:
        return None

    trades = _read_csv(TRADE_LOG)
    proposal, tokens = _call_evaluator(metrics, current, trades, now_et)
    can_change = trades_count >= 20 and sessions - int(current.get("last_change_session_count", 0)) >= 10
    confidence = _safe_float(proposal.get("confidence"), 0.0)
    changed = False
    old_version = current["version"]
    if can_change and confidence >= 0.60:
        candidate = _bounded_config(current, proposal)
        materially_changed = any(candidate.get(k) != current.get(k) for k in BOUNDS) or candidate.get("learning_notes") != current.get("learning_notes")
        if materially_changed:
            candidate["version"] = _next_version(old_version)
            candidate["last_change_session_count"] = sessions
            current = candidate
            changed = True

    current["last_evaluation_session_count"] = sessions
    save_config(current)
    record = {
        "timestamp_et": now_et.isoformat(),
        "sessions": sessions,
        "trades": trades_count,
        "metrics": metrics,
        "proposal": proposal,
        "change_eligible": can_change,
        "changed": changed,
        "old_version": old_version,
        "new_version": current["version"],
        "tokens": tokens,
    }
    with EVALUATION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    if changed:
        _append_version(current, str(proposal.get("summary", "Adaptive evidence-based update"))[:600], sessions, trades_count, str(now_et.date()))
    return record
