"""Azure Functions entry point for Final V1.

Runs short simulation cycles around U.S. market hours on weekdays. A cheap
New York time guard runs before Blob Storage sync so the Flex Consumption app
stays as close to free as possible. The strategy's own NYSE calendar/time
guards remain the final authority on whether trading work is needed.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

# These must be set before importing the scalping modules so their path constants
# point to Azure Functions' writable temporary filesystem rather than the package.
os.environ.setdefault("SCALPING_RUN_ROOT", "/tmp/scalping_v1")
os.environ.setdefault("SCALPING_OUTPUT_ROOT", "/tmp/scalping_output")
os.environ.setdefault("SCALPING_README_PATH", "/tmp/scalping_output/README.md")

import azure.functions as func

from user_side.personal_experiment.azure_runtime import sync_down, sync_up
from user_side.personal_experiment.scalping_v1 import main as run_scalping_cycle

app = func.FunctionApp()
NY = ZoneInfo("America/New_York")
EARLY_GUARD_START = time(9, 20)
EARLY_GUARD_END = time(16, 15)


def _inside_broad_market_window() -> bool:
    """Return True only during the broad weekday New York market window."""
    now_et = datetime.now(NY)
    return now_et.weekday() < 5 and EARLY_GUARD_START <= now_et.time() <= EARLY_GUARD_END


@app.timer_trigger(
    # 13:00-21:55 UTC safely covers 09:20-16:15 New York time across DST.
    # The New York guard below prevents unnecessary Blob work outside the session.
    schedule="0 */5 13-21 * * 1-5",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def scalping_timer(timer: func.TimerRequest) -> None:
    """Execute one guarded five-minute Final V1 cycle."""
    if timer.past_due:
        logging.warning("Final V1 timer invocation is past due; evaluating guarded cycle now.")

    # Avoid Blob Storage reads/writes and API setup outside the relevant ET window.
    if not _inside_broad_market_window():
        logging.info("Outside broad New York market window; skipping Final V1 cycle.")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY application setting is missing.")

    sync_down()
    try:
        run_scalping_cycle()
    finally:
        # Persist even when a data/API exception occurs after state changed.
        sync_up()
