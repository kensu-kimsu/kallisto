from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RUN_ROOT = (
    PROJECT_ROOT
    / "user_side"
    / "runs"
    / "personal_v1"
)

JOURNAL_ROOT = (
    PROJECT_ROOT
    / "docs"
    / "journal"
    / "daily"
)

COST_LOG = (
    PROJECT_ROOT
    / "user_side"
    / "personal_experiment"
    / "cost_tracking"
    / "api_cost_log.csv"
)


def _read_last_csv_row(path: Path) -> dict:
    if not path.exists():
        return {}

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    return rows[-1] if rows else {}


def _load_json(path: Path):
    if not path.exists():
        return None

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def _portfolio_snapshot(experiment: str) -> dict:
    base = RUN_ROOT / experiment / "portfolio"

    cash_data = _load_json(
        base / "cash.json"
    ) or {}

    pending = _load_json(
        base / "pending_trades.json"
    ) or {}

    history = _read_last_csv_row(
        base / "portfolio_history.csv"
    )

    trade_log = _read_last_csv_row(
        base / "trade_log.csv"
    )

    return {
        "cash": cash_data,
        "pending": pending,
        "history": history,
        "trade_log": trade_log,
    }


def _cost_rows_for_date(run_date: str) -> list[dict]:
    if not COST_LOG.exists():
        return []

    with open(
        COST_LOG,
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    return [
        row
        for row in rows
        if row.get("run_date") == run_date
    ]


def _format_pending_orders(pending) -> list[str]:
    if not isinstance(pending, dict):
        return ["- None"]

    orders = pending.get("orders", [])

    if not orders:
        return ["- None"]

    lines = []

    for order in orders:
        company = order.get(
            "company_name",
            order.get("ticker", "Unknown"),
        )

        ticker = order.get(
            "ticker",
            "Unknown",
        )

        action = str(
            order.get("action", "")
        ).upper()

        shares = order.get(
            "shares",
            "?"
        )

        limit_price = order.get(
            "limit_price",
            "?"
        )

        stop_loss = order.get(
            "stop_loss"
        )

        lines.append(
            f"- {company} ({ticker}): "
            f"{action} {shares} shares "
            f"@ limit {limit_price}"
            + (
                f", stop {stop_loss}"
                if stop_loss is not None
                else ""
            )
        )

    return lines


def _find_value(
    row: dict,
    *possible_names: str,
    default: str = "N/A",
):
    lowered = {
        str(k).lower(): v
        for k, v in row.items()
    }

    for name in possible_names:
        if name.lower() in lowered:
            value = lowered[name.lower()]

            if value not in {
                None,
                "",
            }:
                return value

    return default


def create_daily_journal(
    run_date,
    next_session=None,
) -> Path:
    run_date = str(run_date)

    JOURNAL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    microcap = _portfolio_snapshot(
        "microcap"
    )

    titans = _portfolio_snapshot(
        "titans"
    )

    cost_rows = _cost_rows_for_date(
        run_date
    )

    daily_cost = sum(
        float(
            row.get(
                "total_cost_usd",
                0,
            )
            or 0
        )
        for row in cost_rows
    )

    cumulative_cost = 0.0

    if cost_rows:
        cumulative_cost = float(
            cost_rows[-1].get(
                "cumulative_cost_usd",
                0,
            )
            or 0
        )

    micro_hist = microcap["history"]
    titan_hist = titans["history"]

    lines = [
        f"# NYSE Session - {run_date}",
        "",
        "> Simulation only. No live-money trading.",
        "",
        "## Session",
        "",
        f"- Completed NYSE session: {run_date}",
        f"- Next intended NYSE session: {next_session or 'N/A'}",
        "",
        "## Microcap Growth",
        "",
        f"- Portfolio value: "
        f"{_find_value(micro_hist, 'total_value', 'portfolio_value', 'value')}",
        f"- Cash: "
        f"{_find_value(microcap['cash'], 'cash', default=str(microcap['cash']))}",
        "",
        "### Pending AI Orders",
        "",
        *_format_pending_orders(
            microcap["pending"]
        ),
        "",
        "## Nasdaq Titan Growth",
        "",
        f"- Portfolio value: "
        f"{_find_value(titan_hist, 'total_value', 'portfolio_value', 'value')}",
        f"- Cash: "
        f"{_find_value(titans['cash'], 'cash', default=str(titans['cash']))}",
        "",
        "### Pending AI Orders",
        "",
        *_format_pending_orders(
            titans["pending"]
        ),
        "",
        "## API Usage",
        "",
        f"- API cost for this session: ${daily_cost:.4f} USD",
        f"- Cumulative API cost: ${cumulative_cost:.4f} USD",
        "",
        "## Human Intervention",
        "",
        "- Valid AI recommendations were approved without rewriting the investment decision.",
        "",
        "## Notes",
        "",
        "- This page was generated automatically by the experiment workflow.",
        "",
    ]

    output_path = (
        JOURNAL_ROOT
        / f"{run_date}.md"
    )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        f"Daily journal created: "
        f"{output_path.relative_to(PROJECT_ROOT)}"
    )

    return output_path


if __name__ == "__main__":
    raise SystemExit(
        "This module is intended to be called "
        "from simulation_workflow.py."
    )