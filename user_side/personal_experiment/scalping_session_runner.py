"""Persistent GitHub Actions session runner for the simulated scalping study.

A scheduled workflow starts this process well before the relevant market segment.
The process then stays alive, runs a monitoring cycle every five minutes, and
persists state to GitHub after every cycle. This avoids relying on GitHub cron
to wake the strategy at every intraday decision point.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time as sleep_time
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CYCLE_SECONDS = 300

SEGMENTS = {
    "morning": (time(9, 25), time(12, 25)),
    "afternoon": (time(12, 25), time(16, 5)),
}


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        check=check,
    )


def persist_state(now_et: datetime) -> None:
    paths = [
        "user_side/runs/scalping_v1",
        "docs/journal/daily",
        "docs/results",
        "README.md",
    ]
    existing = [path for path in paths if (PROJECT_ROOT / path).exists()]
    if existing:
        run(["git", "add", "--", *existing])

    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=PROJECT_ROOT,
        check=False,
    ).returncode != 0
    if not changed:
        print("Checkpoint: no state changes to commit.", flush=True)
        return

    stamp = now_et.strftime("%Y-%m-%d %H:%M ET")
    run(["git", "commit", "-m", f"experiment: scalping checkpoint {stamp}"])

    # A single concurrency group prevents normal overlap, but pull/rebase still
    # protects against an unrelated repository update while this long job runs.
    for attempt in range(1, 4):
        try:
            run(["git", "pull", "--rebase", "origin", "main"])
            run(["git", "push", "origin", "main"])
            print(f"Checkpoint pushed at {stamp}.", flush=True)
            return
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            print(f"Checkpoint push attempt {attempt} failed; retrying...", flush=True)
            sleep_time.sleep(10 * attempt)


def wait_until(start_et: time) -> None:
    while True:
        now = datetime.now(NY)
        target = datetime.combine(now.date(), start_et, tzinfo=NY)
        if now >= target:
            return
        seconds = min(60, max(1, int((target - now).total_seconds())))
        print(
            f"Waiting for segment start {start_et.strftime('%H:%M')} ET; "
            f"now {now.strftime('%H:%M:%S')} ET.",
            flush=True,
        )
        sleep_time.sleep(seconds)


def next_five_minute_boundary(now: datetime) -> datetime:
    minute = (now.minute // 5 + 1) * 5
    if minute >= 60:
        nxt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        nxt = now.replace(minute=minute, second=0, microsecond=0)
    return nxt


def run_segment(segment: str) -> None:
    start_et, end_et = SEGMENTS[segment]
    now = datetime.now(NY)
    end_dt = datetime.combine(now.date(), end_et, tzinfo=NY)

    if now >= end_dt:
        print(f"{segment} segment already ended; nothing to run.", flush=True)
        return

    wait_until(start_et)
    print(
        f"Starting {segment} persistent scalping segment at "
        f"{datetime.now(NY).isoformat()}.",
        flush=True,
    )

    while True:
        now = datetime.now(NY)
        if now >= end_dt:
            break

        print(f"\n--- Scalping cycle {now.isoformat()} ---", flush=True)
        completed = run(
            [sys.executable, "-m", "user_side.personal_experiment.scalping_v1"],
            check=False,
        )
        persist_state(datetime.now(NY))

        if completed.returncode != 0:
            print(
                f"Cycle returned code {completed.returncode}; state was checkpointed. "
                "Continuing to the next cycle.",
                flush=True,
            )

        now = datetime.now(NY)
        wake = next_five_minute_boundary(now)
        if wake >= end_dt:
            break
        sleep_seconds = max(1, int((wake - now).total_seconds()))
        print(f"Next monitoring cycle at {wake.strftime('%H:%M:%S')} ET.", flush=True)
        sleep_time.sleep(sleep_seconds)

    # One final cycle/checkpoint makes the afternoon segment reliably execute
    # the 15:55 forced-flat logic even if a prior cycle drifted slightly.
    if segment == "afternoon":
        now = datetime.now(NY)
        if now.time() <= time(16, 10):
            print("\n--- Final EOD safety cycle ---", flush=True)
            run(
                [sys.executable, "-m", "user_side.personal_experiment.scalping_v1"],
                check=False,
            )
            persist_state(datetime.now(NY))

    print(f"Completed {segment} scalping segment.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segment", choices=sorted(SEGMENTS), required=True)
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")
    run_segment(args.segment)


if __name__ == "__main__":
    main()
