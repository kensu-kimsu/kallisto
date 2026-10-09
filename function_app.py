"""Azure Functions entry point for Final V1.

Runs one short simulation cycle every five minutes on weekdays. The strategy's
own NYSE calendar/time guards decide whether trading work is needed.
"""

from __future__ import annotations

import logging
import os

# These must be set before importing the scalping modules so their path constants
# point to Azure Functions' writable temporary filesystem rather than the package.
os.environ.setdefault("SCALPING_RUN_ROOT", "/tmp/scalping_v1")
os.environ.setdefault("SCALPING_OUTPUT_ROOT", "/tmp/scalping_output")
os.environ.setdefault("SCALPING_README_PATH", "/tmp/scalping_output/README.md")

import azure.functions as func

from user_side.personal_experiment.azure_runtime import sync_down, sync_up
from user_side.personal_experiment.scalping_v1 import main as run_scalping_cycle

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */5 * * * 1-5",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def scalping_timer(timer: func.TimerRequest) -> None:
    """Execute one idempotent five-minute Final V1 cycle."""
    if timer.past_due:
        logging.warning("Final V1 timer invocation is past due; running guarded cycle now.")

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY application setting is missing.")

    sync_down()
    try:
        run_scalping_cycle()
    finally:
        # Persist even when a data/API exception occurs after state changed.
        sync_up()
