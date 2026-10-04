"""Daily reporting for the simulation-only scalping study."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from user_side.personal_experiment.scalping_state import DAILY_LOG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = PROJECT_ROOT / "docs" / "results"
JOURNAL_ROOT = PROJECT_ROOT / "docs" / "journal" / "daily"


def create_daily_journal(row: dict, trades: list[dict]) -> Path:
    JOURNAL_ROOT.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# LLM Scalping V1 - {row['date']}",
        "",
        "> Simulation only. No live trades are placed.",
        "",
        "## Portfolio",
        "",
        f"- Starting equity: ${float(row['starting_equity']):,.2f}",
        f"- Ending equity: ${float(row['ending_equity']):,.2f}",
        f"- Daily return: {float(row['daily_return_pct']):.2f}%",
        f"- Cumulative return: {float(row['cumulative_return_pct']):.2f}%",
        f"- Trades: {row['trades']}",
        f"- Wins: {row['wins']}",
        f"- Losses: {row['losses']}",
        f"- Win rate: {float(row['win_rate_pct']):.2f}%",
        "",
        "## Benchmarks",
        "",
        f"- S&P 500 normalized value: ${float(row['sp500_normalized']):,.2f}",
        f"- Nasdaq-100 normalized value: ${float(row['nasdaq100_normalized']):,.2f}",
        "",
        "## Closed trades",
        "",
    ]
    if not trades:
        lines.append("- None")
    else:
        for trade in trades:
            lines.append(
                f"- {trade['ticker']} {trade['side']} | "
                f"{trade['shares']} shares | "
                f"P/L ${float(trade['pnl_usd']):,.2f} | "
                f"{trade['exit_reason']}"
            )

    lines += [
        "",
        "## Automation",
        "",
        "- Fully autonomous simulated workflow.",
        "- No manual trade approval.",
        "- All positions must be closed during the same NYSE session.",
        "",
    ]
    path = JOURNAL_ROOT / f"{row['date']}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def refresh_chart() -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    if not DAILY_LOG.exists():
        return
    df = pd.read_csv(DAILY_LOG)
    if df.empty:
        return

    df["date"] = pd.to_datetime(df["date"])
    plt.figure(figsize=(11, 6))
    plt.plot(df["date"], df["ending_equity"], label="LLM Scalping V1")
    plt.plot(df["date"], df["sp500_normalized"], linestyle="--", label="S&P 500")
    plt.plot(df["date"], df["nasdaq100_normalized"], linestyle="--", label="Nasdaq-100")
    plt.axhline(1000, linewidth=1)
    plt.title("LLM Scalping V1 vs Benchmarks")
    plt.xlabel("Date")
    plt.ylabel("Normalized value (USD)")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_ROOT / "scalping_equity_comparison.png", dpi=160)
    plt.close()
