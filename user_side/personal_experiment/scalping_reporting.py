"""Reporting for the simulation-only Kallisto adaptive scalping study."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from user_side.personal_experiment.baseline_replay import BASELINE_REPLAY_LOG, refresh_baseline_replay
from user_side.personal_experiment.scalping_fees import fee_adjusted_trade
from user_side.personal_experiment.scalping_state import DAILY_LOG, TRADE_LOG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs"
OUTPUT_ROOT = Path(os.environ.get("SCALPING_OUTPUT_ROOT", str(DEFAULT_OUTPUT_ROOT)))
RESULTS_ROOT = OUTPUT_ROOT / "results"
JOURNAL_ROOT = OUTPUT_ROOT / "journal" / "daily"
RUN_ROOT = Path(os.environ.get("SCALPING_RUN_ROOT", str(PROJECT_ROOT / "user_side" / "runs" / "scalping_v1")))
IMPROVEMENT_LOG = RUN_ROOT / "improvement_metrics.csv"
STARTING_EQUITY = 1000.0


def _all_fee_adjusted_trades() -> list[dict]:
    if not TRADE_LOG.exists():
        return []
    with TRADE_LOG.open("r", encoding="utf-8", newline="") as f:
        return [fee_adjusted_trade(row) for row in csv.DictReader(f)]


def fee_adjusted_summary(through_date: str | None = None) -> dict:
    trades = _all_fee_adjusted_trades()
    if through_date:
        trades = [t for t in trades if str(t.get("session_date", "")) <= through_date]
    gross = sum(float(t["gross_pnl_usd"]) for t in trades)
    fees = sum(float(t["fees_usd"]) for t in trades)
    net = sum(float(t["net_pnl_usd"]) for t in trades)
    return {"trades": len(trades), "gross_pnl_usd": gross, "fees_usd": fees, "net_pnl_usd": net, "net_equity": STARTING_EQUITY + net, "net_return_pct": net / STARTING_EQUITY * 100}


def fee_adjusted_equity_by_date() -> dict[str, float]:
    equity = STARTING_EQUITY
    by_date: dict[str, float] = {}
    for trade in _all_fee_adjusted_trades():
        equity += float(trade["net_pnl_usd"])
        by_date[str(trade["session_date"])] = equity
    return by_date


def create_daily_journal(row: dict, trades: list[dict]) -> Path:
    JOURNAL_ROOT.mkdir(parents=True, exist_ok=True)
    adjusted = [fee_adjusted_trade(t) for t in trades]
    day_gross = sum(float(t["gross_pnl_usd"]) for t in adjusted)
    day_fees = sum(float(t["fees_usd"]) for t in adjusted)
    day_net = sum(float(t["net_pnl_usd"]) for t in adjusted)
    cumulative = fee_adjusted_summary(str(row["date"]))
    lines = [
        f"# Kallisto V1 - {row['date']}", "", "> Simulation only. No live trades are placed.", "",
        "## Portfolio (Moomoo AU fee-adjusted)", "",
        f"- Simulator gross ending equity: ${float(row['ending_equity']):,.2f}",
        f"- Gross trading P/L today: ${day_gross:,.2f}",
        f"- Estimated Moomoo AU transaction fees today: ${day_fees:,.2f}",
        f"- Net P/L today after modeled fees: ${day_net:,.2f}",
        f"- Fee-adjusted ending equity: ${float(cumulative['net_equity']):,.2f}",
        f"- Fee-adjusted cumulative return: {float(cumulative['net_return_pct']):.2f}%",
        f"- Trades: {row['trades']}",
        "", "## Benchmarks", "", f"- S&P 500 normalized value: ${float(row['sp500_normalized']):,.2f}",
        f"- Nasdaq-100 normalized value: ${float(row['nasdaq100_normalized']):,.2f}", "", "## Closed trades (net after modeled fees)", "",
    ]
    if not adjusted:
        lines.append("- None")
    else:
        for trade in adjusted:
            lines.append(f"- {trade['ticker']} {trade['side']} | {trade['shares']} shares | gross ${float(trade['gross_pnl_usd']):,.2f} | fees ${float(trade['fees_usd']):,.2f} | net ${float(trade['net_pnl_usd']):,.2f} | {trade['exit_reason']}")
    lines += ["", "## Fee-model note", "", "- Headline Kallisto P/L is reported net of modeled Moomoo Australia US-stock transaction fees.", "- Commission is $0; modeled costs include the $0.99 platform fee per order, settlement fee, SEC sell fee, FINRA TAF and CAT fee.", "- Security-specific ADR custody and stock-borrow fees are included only when explicitly supplied; they are not invented when unavailable.", "", "## Kallisto automation", "", "- Autonomous simulation with bounded adaptive self-evaluation.", "- No manual trade approval.", "- All positions close in the same NYSE session.", ""]
    path = JOURNAL_ROOT / f"{row['date']}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

def refresh_chart() -> None:
    refresh_charts()


def refresh_charts() -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    refresh_baseline_replay()

    if DAILY_LOG.exists():
        df = pd.read_csv(DAILY_LOG)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            fee_equity = fee_adjusted_equity_by_date()
            df["fee_adjusted_equity"] = [fee_equity.get(d.strftime("%Y-%m-%d"), STARTING_EQUITY) for d in df["date"]]
            plt.figure(figsize=(11, 6))
            plt.plot(df["date"], df["fee_adjusted_equity"], label="Kallisto net after Moomoo AU fees")
            plt.plot(df["date"], df["ending_equity"], linestyle=":", label="Kallisto gross before fees")
            if BASELINE_REPLAY_LOG.exists():
                baseline = pd.read_csv(BASELINE_REPLAY_LOG)
                if not baseline.empty:
                    baseline["date"] = pd.to_datetime(baseline["date"])
                    plt.plot(baseline["date"], baseline["ending_equity"], linestyle=":", label="Frozen V1.0 risk replay")
            plt.plot(df["date"], df["sp500_normalized"], linestyle="--", label="S&P 500")
            plt.plot(df["date"], df["nasdaq100_normalized"], linestyle="--", label="Nasdaq-100")
            plt.axhline(1000, linewidth=1)
            plt.title("Kallisto Fee-Adjusted Equity vs Market")
            plt.xlabel("Date"); plt.ylabel("Normalized value (USD)")
            plt.grid(alpha=0.25); plt.legend(); plt.tight_layout()
            plt.savefig(RESULTS_ROOT / "scalping_equity_comparison.png", dpi=160)
            plt.close()

    if IMPROVEMENT_LOG.exists():
        imp = pd.read_csv(IMPROVEMENT_LOG)
        if not imp.empty:
            imp["date"] = pd.to_datetime(imp["date"])
            plt.figure(figsize=(11, 6))
            plt.plot(imp["date"], imp["rolling_5_return_pct"], label="Kallisto gross 5-session return (research)")
            plt.plot(imp["date"], imp["rolling_5_sp500_pct"], linestyle="--", label="S&P 500 5-session return")
            plt.plot(imp["date"], imp["rolling_5_nasdaq100_pct"], linestyle="--", label="Nasdaq-100 5-session return")
            plt.axhline(0, linewidth=1)
            plt.title("Kallisto Gross Adaptive-Learning Research Metrics")
            plt.xlabel("Date"); plt.ylabel("Return (%)")
            plt.grid(alpha=0.25); plt.legend(); plt.tight_layout()
            plt.savefig(RESULTS_ROOT / "self_improvement_returns.png", dpi=160)
            plt.close()

            plt.figure(figsize=(11, 6))
            plt.plot(imp["date"], imp["rolling_5_alpha_pct"], label="Kallisto gross alpha vs stronger benchmark (research)")
            plt.axhline(0, linewidth=1)
            plt.title("Kallisto Gross Adaptive-Learning Research Alpha")
            plt.xlabel("Date"); plt.ylabel("Alpha (percentage points)")
            plt.grid(alpha=0.25); plt.legend(); plt.tight_layout()
            plt.savefig(RESULTS_ROOT / "self_improvement_alpha.png", dpi=160)
            plt.close()
