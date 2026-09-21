from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


RUN_ROOT = Path(
    "user_side/runs/personal_v1"
)

OUTPUT_DIR = Path(
    "user_side/personal_experiment/reporting/output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PROJECTION_FILE = (
    OUTPUT_DIR
    / "four_week_projection.png"
)

PROJECTION_CSV = (
    OUTPUT_DIR
    / "four_week_projection.csv"
)


def load_equity_history(
    experiment,
):
    path = (
        RUN_ROOT
        / experiment
        / "portfolio"
        / "portfolio_history.csv"
    )

    if not path.exists():
        return None

    df = pd.read_csv(
        path
    )

    if df.empty:
        return None

    if (
        "date" not in df.columns
        or "equity" not in df.columns
    ):
        return None

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df["equity"] = pd.to_numeric(
        df["equity"],
        errors="coerce",
    )

    df = (
        df.dropna(
            subset=[
                "date",
                "equity",
            ]
        )
        .sort_values("date")
    )

    return df


def calculate_weekly_projection(
    experiment,
    display_name,
):
    history = load_equity_history(
        experiment
    )

    if (
        history is None
        or len(history) < 2
    ):
        return None

    weekly = (
        history
        .set_index("date")[
            "equity"
        ]
        .resample("W-FRI")
        .last()
        .dropna()
    )

    # Need at least two weekly equity points
    # to calculate one weekly return.
    if len(weekly) < 2:
        return None

    weekly_returns = (
        weekly.pct_change()
        .dropna()
    )

    if weekly_returns.empty:
        return None

    # Use at most the latest four completed
    # weekly returns.
    recent_returns = (
        weekly_returns.tail(4)
    )

    average_weekly_return = (
        recent_returns.mean()
    )

    current_equity = float(
        weekly.iloc[-1]
    )

    last_week = (
        weekly.index[-1]
    )

    rows = []

    # Week 0 = actual latest equity.
    rows.append(
        {
            "portfolio": display_name,
            "week": 0,
            "date": last_week,
            "projected_equity": (
                current_equity
            ),
            "average_weekly_return": (
                average_weekly_return
            ),
            "weeks_used": len(
                recent_returns
            ),
        }
    )

    projected_equity = (
        current_equity
    )

    for week_number in range(
        1,
        5,
    ):
        projected_equity *= (
            1
            + average_weekly_return
        )

        projection_date = (
            last_week
            + pd.Timedelta(
                weeks=week_number
            )
        )

        rows.append(
            {
                "portfolio": display_name,
                "week": week_number,
                "date": projection_date,
                "projected_equity": (
                    projected_equity
                ),
                "average_weekly_return": (
                    average_weekly_return
                ),
                "weeks_used": len(
                    recent_returns
                ),
            }
        )

    return {
        "name": display_name,
        "history": history,
        "weekly": weekly,
        "recent_returns": (
            recent_returns
        ),
        "average_weekly_return": (
            average_weekly_return
        ),
        "projection": pd.DataFrame(
            rows
        ),
    }


def generate_projection():
    portfolios = []

    microcap = (
        calculate_weekly_projection(
            "microcap",
            "Microcap Growth",
        )
    )

    titans = (
        calculate_weekly_projection(
            "titans",
            "Nasdaq Titan Growth",
        )
    )

    if microcap is not None:
        portfolios.append(
            microcap
        )

    if titans is not None:
        portfolios.append(
            titans
        )

    print()
    print("=" * 60)
    print(
        "4-WEEK MECHANICAL PROJECTION"
    )
    print("=" * 60)

    if not portfolios:
        print(
            "Not enough completed weekly "
            "history for a projection yet."
        )

        print(
            "Projection will start "
            "automatically once sufficient "
            "weekly performance data exists."
        )

        return None

    all_projection_rows = []

    fig, ax = plt.subplots(
        figsize=(11, 6)
    )

    for data in portfolios:
        name = data["name"]

        weekly = data[
            "weekly"
        ]

        projection = data[
            "projection"
        ]

        avg_return = data[
            "average_weekly_return"
        ]

        weeks_used = len(
            data["recent_returns"]
        )

        print()
        print(
            f"{name}"
        )

        print(
            f"Recent weeks used: "
            f"{weeks_used}"
        )

        print(
            f"Average weekly return: "
            f"{avg_return * 100:.2f}%"
        )

        print(
            f"Current weekly equity: "
            f"${weekly.iloc[-1]:,.2f}"
        )

        final_equity = float(
            projection.iloc[-1][
                "projected_equity"
            ]
        )

        print(
            f"Mechanical Week-4 equity: "
            f"${final_equity:,.2f}"
        )

        # Actual weekly history.
        ax.plot(
            weekly.index,
            weekly.values,
            marker="o",
            label=(
                f"{name} actual"
            ),
        )

        # Mechanical projection.
        ax.plot(
            projection["date"],
            projection[
                "projected_equity"
            ],
            marker="o",
            linestyle="--",
            label=(
                f"{name} projection"
            ),
        )

        all_projection_rows.append(
            projection
        )

    ax.set_title(
        "Portfolio Progress + "
        "4-Week Mechanical Projection"
    )

    ax.set_xlabel(
        "Week"
    )

    ax.set_ylabel(
        "Portfolio equity (USD)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        PROJECTION_FILE,
        dpi=160,
    )

    plt.close(
        fig
    )

    combined = pd.concat(
        all_projection_rows,
        ignore_index=True,
    )

    combined.to_csv(
        PROJECTION_CSV,
        index=False,
    )

    print()
    print(
        f"Projection chart: "
        f"{PROJECTION_FILE}"
    )

    print(
        f"Projection data: "
        f"{PROJECTION_CSV}"
    )

    print()
    print(
        "IMPORTANT: This is a mechanical "
        "extrapolation of recent weekly "
        "performance, not a prediction of "
        "future market returns."
    )

    return PROJECTION_FILE


if __name__ == "__main__":
    generate_projection()
