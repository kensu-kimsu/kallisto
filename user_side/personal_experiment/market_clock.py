from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal


MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")
NEW_YORK_TZ = ZoneInfo("America/New_York")

NYSE = mcal.get_calendar("NYSE")


def get_market_context(now=None):
    """
    Return Melbourne time, New York time, latest COMPLETED NYSE session,
    and the next NYSE trading session.

    This prevents the Australian calendar date from being mistaken for
    the U.S. market trading date.
    """

    if now is None:
        now = datetime.now(UTC)

    now_utc = now.astimezone(UTC)
    melbourne_now = now_utc.astimezone(MELBOURNE_TZ)
    new_york_now = now_utc.astimezone(NEW_YORK_TZ)

    start_date = new_york_now.date() - timedelta(days=10)
    end_date = new_york_now.date() + timedelta(days=10)

    schedule = NYSE.schedule(
        start_date=start_date,
        end_date=end_date,
    )

    now_timestamp = pd.Timestamp(now_utc)

    completed = schedule[
        schedule["market_close"] <= now_timestamp
    ]

    upcoming = schedule[
        schedule["market_open"] > now_timestamp
    ]

    latest_completed_session = None
    next_session = None

    if not completed.empty:
        latest_completed_session = completed.index[-1].date()

    if not upcoming.empty:
        next_session = upcoming.index[0].date()

    return {
        "melbourne_time": melbourne_now,
        "new_york_time": new_york_now,
        "latest_completed_nyse_session": latest_completed_session,
        "next_nyse_session": next_session,
    }


def resolve_run_date():
    """
    Use this as the LIBB run_date for the personal experiment.

    It always returns the latest fully completed NYSE session.
    """
    context = get_market_context()

    run_date = context["latest_completed_nyse_session"]

    if run_date is None:
        raise RuntimeError(
            "Could not determine the latest completed NYSE session."
        )

    return run_date


if __name__ == "__main__":
    context = get_market_context()

    print("Melbourne time:")
    print(context["melbourne_time"])

    print("\nNew York time:")
    print(context["new_york_time"])

    print("\nLatest completed NYSE session:")
    print(context["latest_completed_nyse_session"])

    print("\nNext NYSE session:")
    print(context["next_nyse_session"])
