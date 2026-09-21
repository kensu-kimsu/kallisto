from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_OUTPUT = (
    PROJECT_ROOT
    / "user_side"
    / "personal_experiment"
    / "reporting"
    / "output"
)

DOCS_RESULTS = PROJECT_ROOT / "docs" / "results"


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def copy_public_charts() -> None:
    DOCS_RESULTS.mkdir(parents=True, exist_ok=True)

    charts = [
        "equity_comparison.png",
        "drawdown_comparison.png",
        "four_week_projection.png",
    ]

    for filename in charts:
        source = REPORT_OUTPUT / filename
        destination = DOCS_RESULTS / filename

        if source.exists():
            shutil.copy2(source, destination)


def stage_experiment_files() -> None:
    paths = [
        "docs/journal",
        "docs/results",
        "user_side/runs/personal_v1",
        "user_side/personal_experiment/cost_tracking/api_cost_log.csv",
        "user_side/personal_experiment/reporting/output/daily_comparison.csv",
        "user_side/personal_experiment/reporting/output/weekly_summary.csv",
        "user_side/personal_experiment/reporting/output/monthly_summary.csv",
        "user_side/personal_experiment/reporting/output/performance_summary.json",
    ]

    run_git("add", "--", *paths)


def staged_changes_exist() -> bool:
    result = run_git(
        "diff",
        "--cached",
        "--quiet",
        check=False,
    )

    return result.returncode == 1


def commit_and_push(run_date: str) -> bool:
    copy_public_charts()
    stage_experiment_files()

    if not staged_changes_exist():
        print("\nGitHub sync: no experiment changes to commit.")
        return True

    message = f"experiment: record NYSE session {run_date}"

    commit = run_git(
        "commit",
        "-m",
        message,
        check=False,
    )

    if commit.returncode != 0:
        print("\nGitHub sync: commit failed.")
        print(commit.stderr.strip())
        return False

    push = run_git(
        "push",
        "origin",
        "main",
        check=False,
    )

    if push.returncode != 0:
        print("\nGitHub sync: commit was saved locally, but push failed.")
        print(push.stderr.strip())
        print("No force push was attempted.")
        return False

    print(f"\nGitHub sync complete: {message}")
    return True


if __name__ == "__main__":
    commit_and_push(date.today().isoformat())