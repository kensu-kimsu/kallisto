from pathlib import Path
import csv
from datetime import datetime, UTC


COST_DIR = Path(
    "user_side/personal_experiment/cost_tracking"
)

COST_DIR.mkdir(
    parents=True,
    exist_ok=True
)

COST_FILE = COST_DIR / "api_cost_log.csv"


MODEL_PRICING = {
    "gpt-5.6-luna": {
        "input_per_million": 0.20,
        "output_per_million": 1.20,
    },
    "gpt-5.6-terra": {
        "input_per_million": 2.00,
        "output_per_million": 12.00,
    },
}


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
):
    if model_name not in MODEL_PRICING:
        raise ValueError(
            f"No pricing configured for {model_name}"
        )

    pricing = MODEL_PRICING[model_name]

    input_cost = (
        input_tokens
        / 1_000_000
    ) * pricing["input_per_million"]

    output_cost = (
        output_tokens
        / 1_000_000
    ) * pricing["output_per_million"]

    total_cost = (
        input_cost
        + output_cost
    )

    return {
        "input_cost_usd": input_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": total_cost,
    }


def get_cumulative_cost():
    if not COST_FILE.exists():
        return 0.0

    total = 0.0

    with open(
        COST_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            try:
                total += float(
                    row["total_cost_usd"]
                )
            except (ValueError, KeyError):
                continue

    return total


def log_api_usage(
    *,
    run_date,
    experiment,
    run_type,
    model_name,
    input_tokens,
    output_tokens,
):
    costs = calculate_cost(
        model_name,
        input_tokens,
        output_tokens,
    )

    cumulative_before = (
        get_cumulative_cost()
    )

    cumulative_after = (
        cumulative_before
        + costs["total_cost_usd"]
    )

    file_exists = COST_FILE.exists()

    fieldnames = [
        "logged_at_utc",
        "run_date",
        "experiment",
        "run_type",
        "model",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "input_cost_usd",
        "output_cost_usd",
        "total_cost_usd",
        "cumulative_cost_usd",
    ]

    row = {
        "logged_at_utc": (
            datetime.now(UTC).isoformat()
        ),
        "run_date": str(run_date),
        "experiment": experiment,
        "run_type": run_type,
        "model": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": (
            input_tokens
            + output_tokens
        ),
        "input_cost_usd": (
            f"{costs['input_cost_usd']:.6f}"
        ),
        "output_cost_usd": (
            f"{costs['output_cost_usd']:.6f}"
        ),
        "total_cost_usd": (
            f"{costs['total_cost_usd']:.6f}"
        ),
        "cumulative_cost_usd": (
            f"{cumulative_after:.6f}"
        ),
    }

    with open(
        COST_FILE,
        "a",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)

    return {
        **costs,
        "cumulative_cost_usd": cumulative_after,
    }


if __name__ == "__main__":
    print(
        f"Cost log: {COST_FILE}"
    )

    print(
        f"Current cumulative API cost: "
        f"${get_cumulative_cost():.6f} USD"
    )
