"""Azure Functions entry point for Kallisto.

Runs short simulation cycles around U.S. market hours on weekdays. A cheap
New York time guard runs before Blob Storage sync so the Flex Consumption app
stays as close to free as possible.

When KALLISTO_MOOMOO_PAPER_ENABLED=true, the same timer also mirrors only *new*
Kallisto broker events to Moomoo's REST simulated-trading account. Historical
decisions are never replayed, and Moomoo live-money endpoints are not used.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

# These must be set before importing the Kallisto modules so their path constants
# point to Azure Functions' writable temporary filesystem rather than the package.
os.environ.setdefault("SCALPING_RUN_ROOT", "/tmp/scalping_v1")
os.environ.setdefault("SCALPING_V13_RUN_ROOT", "/tmp/scalping_v13")
os.environ.setdefault("SCALPING_OUTPUT_ROOT", "/tmp/scalping_output")
os.environ.setdefault("SCALPING_README_PATH", "/tmp/scalping_output/README.md")

import azure.functions as func

from user_side.personal_experiment.azure_runtime import sync_down, sync_up, sync_v13_down, sync_v13_up
from user_side.personal_experiment.broker.moomoo_shadow import (
    paper_enabled,
    run_paper_shadow_cycle,
)
from user_side.personal_experiment.scalping_v1 import main as run_scalping_cycle
from user_side.personal_experiment.scalping_v13 import main as run_v13_cycle

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
    """Execute one guarded five-minute Kallisto cycle."""
    if timer.past_due:
        logging.warning("Kallisto timer invocation is past due; evaluating guarded cycle now.")

    if not _inside_broad_market_window():
        logging.info("Outside broad New York market window; skipping Kallisto cycle.")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY application setting is missing.")

    sync_down()
    try:
        # The six-month simulation remains the primary experiment and is always run.
        run_scalping_cycle()
        # V1.3 is simulation-only, independently persisted and never broker-mirrored.
        try:
            sync_v13_down()
            try:
                run_v13_cycle()
            finally:
                sync_v13_up()
        except Exception:
            logging.exception("V1.3 cycle failed; V1.2 remains unaffected.")

        # Paper execution is optional and isolated. A Moomoo outage must never
        # corrupt or stop the simulation experiment.
        if paper_enabled():
            try:
                paper_result = run_paper_shadow_cycle()
                logging.info("Kallisto Moomoo paper cycle: %s", paper_result)
            except Exception:
                logging.exception(
                    "Moomoo paper shadow cycle failed; simulation state remains authoritative."
                )
    finally:
        # Persist even when a data/API exception occurs after state changed.
        sync_up()
