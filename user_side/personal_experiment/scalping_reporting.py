"""Reporting for the simulation-only adaptive scalping study."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from user_side.personal_experiment.baseline_replay import BASELINE_REPLAY_LOG, refresh_baseline_replay
from user_side.personal_experiment.scalping_state import DAILY_LOG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs"
OUTPUT_ROOT = Path(os.environ.get("SCALPING_OUTPUT_ROOT", str(DEFAULT_OUTPUT_ROOT)))
RESULTS_ROOT = OUTPUT_ROOT / "results"
JOURNAL_ROOT = OUTPUT_ROOT / "journal" / "daily"
RUN_ROOT = Path(os.environ.get("SCALPING_RUN_ROOT", str(PROJECT_ROOT / "user_side" / "runs" / "scalping_v1")))
IMPROVEMENT_LOG = RUN_ROOT / "improvement_metrics.csv"


def create_daily_journal(row: dict, trades: list[dict]) -> Path:
    JOURNAL_ROOT.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# LLM Scalping V1 - {row['date']}", "", "> Simulation only. No live trades are placed.", "",
        "## Portfolio", "", f"- Starting equity: ${float(row['starting_equity']):,.2f}",
        f"- Ending equity: ${float(row['ending_equity']):,.2f}", f"- Daily return: {float(row['daily_return_pct']):.2f}%",
        f"- Cumulative return: {float(row['cumulative_return_pct']):.2f}%", f"- Trades: {row['trades']}",
        f"- Wins: {row['wins']}", f"- Losses: {row['losses']}", f"- Win rate: {float(row['win_rate_pct']):.2f}%",
        "", "## Benchmarks", "", f"- S&P 500 normalized value: ${float(row['sp500_normalized']):,.2f}",
        f"- Nasdaq-100 normalized value: ${float(row['nasdaq100_normalized']):,.2f}", "", "## Closed trades", "",
    ]
    if not trades:
        lines.append("- None")
    else:
        for trade in trades:
            lines.append(f"- {trade['ticker']} {trade['side']} | {trade['shares']} shares | P/L ${float(trade['pnl_usd']):,.2f} | {trade['exit_reason']}")
    lines += ["", "## Automation", "", "- Autonomous simulation with bounded adaptive self-evaluation.", "- No manual trade approval.", "- All positions close in the same NYSE session.", ""]
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
            plt.figure(figsize=(11, 6))
            plt.plot(df["date"], df["ending_equity"], label="Adaptive LLM")
            if BASELINE_REPLAY_LOG.exists():
                baseline = pd.read_csv(BASELINE_REPLAY_LOG)
                if not baseline.empty:
                    baseline["date"] = pd.to_datetime(baseline["date"])
                    plt.plot(baseline["date"], baseline["ending_equity"], linestyle=":", label="Frozen V1.0 risk replay")
            plt.plot(df["date"], df["sp500_normalized"], linestyle="--", label="S&P 500")
            plt.plot(df["date"], df["nasdaq100_normalized"], linestyle="--", label="Nasdaq-100")
            plt.axhline(1000, linewidth=1)
            plt.title("Adaptive LLM vs Frozen V1 Risk Replay and Market")
            plt.xlabel("Date"); plt.ylabel("Normalized value (USD)")
            plt.grid(alpha=0.25); plt.legend(); plt.tight_layout()
            plt.savefig(RESULTS_ROOT / "scalping_equity_comparison.png", dpi=160)
            plt.close()

    if IMPROVEMENT_LOG.exists():
        imp = pd.read_csv(IMPROVEMENT_LOG)
        if not imp.empty:
            imp["date"] = pd.to_datetime(imp["date"])
            plt.figure(figsize=(11, 6))
            plt.plot(imp["date"], imp["rolling_5_return_pct"], label="Adaptive 5-session return")
            plt.plot(imp["date"], imp["rolling_5_sp500_pct"], linestyle="--", label="S&P 500 5-session return")
            plt.plot(imp["date"], imp["rolling_5_nasdaq100_pct"], linestyle="--", label="Nasdaq-100 5-session return")
            plt.axhline(0, linewidth=1)
            plt.title("Measured Self-Improvement: Rolling 5-Session Performance")
            plt.xlabel("Date"); plt.ylabel("Return (%)")
            plt.grid(alpha=0.25); plt.legend(); plt.tight_layout()
            plt.savefig(RESULTS_ROOT / "self_improvement_returns.png", dpi=160)
            plt.close()

            plt.figure(figsize=(11, 6))
            plt.plot(imp["date"], imp["rolling_5_alpha_pct"], label="Alpha vs stronger benchmark")
            plt.axhline(0, linewidth=1)
            plt.title("Measured Self-Improvement: Rolling Alpha")
            plt.xlabel("Date"); plt.ylabel("Alpha (percentage points)")
            plt.grid(alpha=0.25); plt.legend(); plt.tight_layout()
            plt.savefig(RESULTS_ROOT / "self_improvement_alpha.png", dpi=160)
            plt.close()
