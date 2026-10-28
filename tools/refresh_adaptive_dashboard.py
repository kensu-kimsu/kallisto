"""Refresh the Kallisto README metrics/charts from Azure Blob Storage.

Used by GitHub Actions after the NYSE session. It only reads simulation outputs
and updates repository documentation; it does not place or simulate trades.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azure.storage.blob import BlobServiceClient

from user_side.personal_experiment.scalping_fees import fee_adjusted_trade
README = ROOT / "README.md"
RUN_ROOT = ROOT / "user_side" / "runs" / "scalping_v1"
RESULTS_ROOT = ROOT / "docs" / "results"
CONTAINER = os.environ.get("SCALPING_STATE_CONTAINER", "scalping-v1-state")
START = "<!-- ADAPTIVE_DASHBOARD_START -->"
END = "<!-- ADAPTIVE_DASHBOARD_END -->"
API_START = "<!-- API_COST_SUMMARY_START -->"
API_END = "<!-- API_COST_SUMMARY_END -->"


def _download() -> None:
    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = BlobServiceClient.from_connection_string(conn).get_container_client(CONTAINER)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    state_names = [
        "portfolio_state.json", "decision_log.jsonl", "daily_performance.csv", "trade_log.csv",
        "api_costs.csv", "adaptive_config.json", "weekly_evaluations.jsonl",
        "improvement_metrics.csv", "strategy_versions.csv", "baseline_replay.csv",
    ]
    for name in state_names:
        blob = container.get_blob_client(f"state/{name}")
        try:
            RUN_ROOT.joinpath(name).write_bytes(blob.download_blob().readall())
        except Exception as exc:
            print(f"WARNING: could not download state/{name}: {type(exc).__name__}: {exc}")
    for name in ["scalping_equity_comparison.png", "self_improvement_returns.png", "self_improvement_alpha.png"]:
        blob = container.get_blob_client(f"reports/results/{name}")
        try:
            RESULTS_ROOT.joinpath(name).write_bytes(blob.download_blob().readall())
        except Exception as exc:
            print(f"WARNING: could not download reports/results/{name}: {type(exc).__name__}: {exc}")


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _dashboard() -> str:
    daily = _rows(RUN_ROOT / "daily_performance.csv")
    trades = _rows(RUN_ROOT / "trade_log.csv")
    adjusted_trades = [fee_adjusted_trade(t) for t in trades]
    gross_trade_pnl = sum(_f(t.get("gross_pnl_usd"), 0.0) for t in adjusted_trades)
    modeled_fees = sum(_f(t.get("fees_usd"), 0.0) for t in adjusted_trades)
    net_trade_pnl = sum(_f(t.get("net_pnl_usd"), 0.0) for t in adjusted_trades)
    net_equity = 1000.0 + net_trade_pnl
    net_return = net_trade_pnl / 1000.0 * 100.0
    improvement = _rows(RUN_ROOT / "improvement_metrics.csv")
    versions = _rows(RUN_ROOT / "strategy_versions.csv")
    baseline = _rows(RUN_ROOT / "baseline_replay.csv")
    latest = improvement[-1] if improvement else {}
    d = daily[-1] if daily else {}
    active_config = {}
    config_path = RUN_ROOT / "adaptive_config.json"
    if config_path.exists():
        try:
            active_config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            active_config = {}
    current_version = active_config.get("version") or latest.get("version") or (versions[-1].get("version") if versions else "V1.0")
    equity = _f(d.get("ending_equity"), 1000.0)
    cumulative = _f(d.get("cumulative_return_pct"), 0.0)
    baseline_equity = _f(baseline[-1].get("ending_equity"), 1000.0) if baseline else 1000.0
    baseline_return = (baseline_equity / 1000.0 - 1) * 100
    vs_baseline = ((equity / baseline_equity) - 1) * 100 if baseline_equity else 0.0
    sp = _f(d.get("sp500_normalized"), 1000.0)
    ndx = _f(d.get("nasdaq100_normalized"), 1000.0)
    sp_ret = (sp / 1000.0 - 1) * 100
    ndx_ret = (ndx / 1000.0 - 1) * 100
    alpha = _f(latest.get("rolling_5_alpha_pct"), 0.0)
    win_rate = _f(latest.get("rolling_5_win_rate_pct"), 0.0)
    pf = _f(latest.get("rolling_5_profit_factor"), 0.0)
    dd = _f(latest.get("max_drawdown_pct"), 0.0)
    sessions = int(_f(latest.get("sessions"), len(daily)))
    lines = [
        START,
        "## Kallisto adaptive learning dashboard",
        "",
        "> Simulation only. Headline P/L and equity below are net of modeled Moomoo Australia US-stock transaction fees. Adaptive-learning metrics remain separately identified when they are based on the gross simulator series.",
        "",
        "| Metric | Current value |",
        "|---|---:|",
        f"| Strategy version | **{current_version}** |",
        f"| Completed sessions | {sessions} |",
        f"| Completed trades | {len(trades)} |",
        f"| **Kallisto net equity after modeled Moomoo AU fees** | **${net_equity:,.2f}** |",
        f"| **Kallisto net cumulative return** | **{net_return:.2f}%** |",
        f"| Simulator gross equity before fees | ${equity:,.2f} |",
        f"| Simulator gross cumulative return | {cumulative:.2f}% |",
        f"| Gross trading P/L | ${gross_trade_pnl:,.2f} |",
        f"| Modeled Moomoo AU transaction fees | **${modeled_fees:,.2f}** |",
        f"| Frozen V1.0 risk-replay equity | ${baseline_equity:,.2f} |",
        f"| Frozen V1.0 risk-replay return | {baseline_return:.2f}% |",
        f"| Gross simulator vs frozen V1.0 risk replay | {vs_baseline:.2f}% |",
        f"| S&P 500 return from experiment base | {sp_ret:.2f}% |",
        f"| Nasdaq-100 return from experiment base | {ndx_ret:.2f}% |",
        "",
        "### Fee treatment",
        "",
        "- Moomoo AU commission: $0.",
        "- Platform fee: $0.99 per order.",
        "- Settlement fee: $0.003/share, capped at 1% of transaction amount.",
        "- SEC fee: sells only, $0.0000206 × transaction amount, minimum $0.01/trade.",
        "- FINRA TAF: $0/share under the current published Moomoo AU live fee schedule.",
        "- CAT fee: NMS stocks $0.000003/share.",
        "- Security-specific ADR custody and stock-borrow fees are included only when an applicable amount is supplied; Kallisto does not invent unknown fees.",
        "",
        "### Beating-the-market and frozen-V1 graph",
        "",
        "![Kallisto vs frozen V1 risk replay, S&P 500 and Nasdaq-100](docs/results/scalping_equity_comparison.png)",
        "",
        "### Gross adaptive-learning research graphs",
        "",
        "![Kallisto rolling 5-session adaptive performance](docs/results/self_improvement_returns.png)",
        "",
        "![Kallisto rolling alpha vs the stronger market benchmark](docs/results/self_improvement_alpha.png)",
        "",
        "### Learning policy",
        "",
        "- Evaluation cadence: every 5 completed NYSE sessions.",
        "- First evaluation: after the first 5 completed sessions.",
        "- Parameter changes: no more often than every 10 completed sessions.",
        "- Evidence gate: at least 20 completed trades plus evaluator confidence of 0.60 or higher.",
        "- Hard risk limits remain bounded in deterministic code; the evaluator cannot remove them.",
        "- Every accepted change creates a new version (V1.1, V1.2, ...) and is recorded in `strategy_versions.csv`.",
        "- The frozen V1.0 replay and adaptive-learning diagnostic series remain gross research controls so the historical experiment is not silently rewritten. They are not the headline P/L report.",
        "",
        END,
    ]
    return "\n".join(lines)


def _api_cost_summary() -> str:
    rows = _rows(RUN_ROOT / "api_costs.csv")
    calls = len(rows)
    input_tokens = sum(int(_f(r.get("input_tokens"), 0)) for r in rows)
    output_tokens = sum(int(_f(r.get("output_tokens"), 0)) for r in rows)
    total_cost = sum(_f(r.get("total_cost_usd"), 0.0) for r in rows)

    parsed = []
    for row in rows:
        raw = row.get("timestamp_et")
        if not raw:
            continue
        try:
            parsed.append(datetime.fromisoformat(raw))
        except ValueError:
            pass

    active_days = len({d.date() for d in parsed})
    active_weeks = len({(d.isocalendar().year, d.isocalendar().week) for d in parsed})
    active_months = len({(d.year, d.month) for d in parsed})

    def avg(value, count):
        return value / count if count else 0.0

    lines = [
        API_START,
        "| Cost period | API cost (USD) | API calls | Input tokens | Output tokens |",
        "|---|---:|---:|---:|---:|",
        f"| Average daily | ${avg(total_cost, active_days):.4f} | {avg(calls, active_days):.1f} | {avg(input_tokens, active_days):,.0f} | {avg(output_tokens, active_days):,.0f} |",
        f"| Average weekly | ${avg(total_cost, active_weeks):.4f} | {avg(calls, active_weeks):.1f} | {avg(input_tokens, active_weeks):,.0f} | {avg(output_tokens, active_weeks):,.0f} |",
        f"| Average monthly | ${avg(total_cost, active_months):.4f} | {avg(calls, active_months):.1f} | {avg(input_tokens, active_months):,.0f} | {avg(output_tokens, active_months):,.0f} |",
        f"| **Total actual** | **${total_cost:.4f}** | **{calls}** | **{input_tokens:,}** | **{output_tokens:,}** |",
        API_END,
    ]
    return "\n".join(lines)


def _replace_block(text: str, start: str, end: str, block: str) -> str:
    if start not in text or end not in text:
        return text
    a = text.index(start)
    b = text.index(end) + len(end)
    return text[:a] + block + text[b:]


def _update_readme() -> None:
    text = README.read_text(encoding="utf-8")
    dashboard = _dashboard()
    if START in text and END in text:
        text = _replace_block(text, START, END, dashboard)
    else:
        anchor = "## OpenAI API cost tracking"
        pos = text.find(anchor)
        text = text[:pos] + dashboard + "\n\n" + text[pos:] if pos >= 0 else text + "\n\n" + dashboard + "\n"

    text = _replace_block(text, API_START, API_END, _api_cost_summary())

    daily = _rows(RUN_ROOT / "daily_performance.csv")
    if daily:
        text = text.replace(
            "**Status:** Azure deployed; adaptive learning ready for first complete session",
            "**Status:** Azure deployed; Day 1 complete; autonomous experiment running",
        )

    README.write_text(text, encoding="utf-8")


def main() -> None:
    _download()
    _update_readme()


if __name__ == "__main__":
    main()
