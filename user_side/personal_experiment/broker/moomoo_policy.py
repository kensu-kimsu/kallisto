import json
from pathlib import Path

import pandas as pd


RESTRICTION_FILE = Path(
    "user_side/personal_experiment/broker/moomoo_restrictions.json"
)


def load_restrictions():
    if not RESTRICTION_FILE.exists():
        return set()

    with open(RESTRICTION_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    blocked = data.get("blocked_for_new_positions", [])

    return {
        str(symbol).upper().strip()
        for symbol in blocked
    }


def is_new_position_allowed(ticker: str) -> bool:
    blocked = load_restrictions()

    return ticker.upper().strip() not in blocked


def filter_new_position_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove stocks manually recorded as unavailable/restricted
    for opening new positions through Moomoo Australia.
    """

    if df.empty:
        return df

    blocked = load_restrictions()

    return (
        df[
            ~df["ticker"]
            .astype(str)
            .str.upper()
            .isin(blocked)
        ]
        .copy()
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    blocked = load_restrictions()

    print("Moomoo blocked-for-new-position symbols:")

    if blocked:
        for symbol in sorted(blocked):
            print(symbol)
    else:
        print("None currently recorded.")
