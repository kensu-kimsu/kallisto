import json
from pathlib import Path


RUN_ROOT = Path(
    "user_side/runs/personal_v1"
)

GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def load_pending_orders(experiment):
    path = (
        RUN_ROOT
        / experiment
        / "portfolio"
        / "pending_trades.json"
    )

    if not path.exists():
        return []

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    return data.get(
        "orders",
        [],
    )


def display_portfolio(
    title,
    experiment,
):
    orders = load_pending_orders(
        experiment
    )

    print()

    print(
        f"{YELLOW}{BOLD}"
        + "=" * 68
        + f"{RESET}"
    )

    print(
        f"{YELLOW}{BOLD}"
        f"{title}"
        f"{RESET}"
    )

    print(
        f"{YELLOW}{BOLD}"
        + "=" * 68
        + f"{RESET}"
    )

    if not orders:
        print(
            f"{YELLOW}"
            "No pending simulated orders."
            f"{RESET}"
        )
        return

    total_commitment = 0.0

    for number, order in enumerate(
        orders,
        start=1,
    ):
        ticker = str(
            order.get(
                "ticker",
                "UNKNOWN",
            )
        ).upper()

        company = order.get(
            "company_name",
            ticker,
        )

        action = str(
            order.get(
                "action",
                "",
            )
        ).upper()

        shares = int(
            order.get(
                "shares",
                0,
            )
        )

        limit_price = float(
            order.get(
                "limit_price",
                0,
            )
        )

        stop_loss = order.get(
            "stop_loss"
        )

        confidence = order.get(
            "confidence"
        )

        date = order.get(
            "date",
            "Unknown",
        )

        rationale = order.get(
            "rationale",
            "",
        )

        commitment = (
            shares
            * limit_price
        )

        if action == "B":
            total_commitment += (
                commitment
            )

        print()
        print(
            f"{YELLOW}{BOLD}"
            f"ORDER {number}"
            f"{RESET}"
        )

        print(
            f"  Company:       "
            f"{YELLOW}"
            f"{company}"
            f"{RESET}"
        )

        print(
            f"  Ticker:        "
            f"{GREEN}{BOLD}"
            f"{ticker}"
            f"{RESET}"
        )

        print(
            f"  Action:        "
            f"{GREEN}{BOLD}"
            f"{action}"
            f"{RESET}"
        )

        print(
            f"  Shares:        "
            f"{GREEN}"
            f"{shares:,}"
            f"{RESET}"
        )

        print(
            f"  Limit price:   "
            f"{GREEN}"
            f"${limit_price:,.2f}"
            f"{RESET}"
        )

        if stop_loss is None:
            stop_text = "None"
        else:
            stop_text = (
                f"${float(stop_loss):,.2f}"
            )

        print(
            f"  Stop loss:     "
            f"{YELLOW}"
            f"{stop_text}"
            f"{RESET}"
        )

        print(
            f"  Max cost:      "
            f"{GREEN}"
            f"${commitment:,.2f}"
            f"{RESET}"
        )

        print(
            f"  Confidence:    "
            f"{confidence}"
        )

        print(
            f"  Trading date:  "
            f"{date}"
        )

        print(
            f"  Rationale:     "
            f"{rationale}"
        )

    print()

    print(
        f"{YELLOW}{BOLD}"
        "TOTAL MAXIMUM BUY COMMITMENT: "
        f"{GREEN}"
        f"${total_commitment:,.2f}"
        f"{RESET}"
    )


def main():
    print()

    print(
        f"{YELLOW}{BOLD}"
        "SAVED LLM TRADING RECOMMENDATIONS"
        f"{RESET}"
    )

    print(
        "Local read-only viewer — "
        "no market-data lookup and "
        "no OpenAI API call."
    )

    display_portfolio(
        "MICROCAP GROWTH",
        "microcap",
    )

    display_portfolio(
        "NASDAQ TITAN GROWTH",
        "titans",
    )

    print()

    print(
        f"{GREEN}"
        "Viewer complete."
        f"{RESET}"
    )

    print(
        "No trades were executed and "
        "no API cost was incurred."
    )


if __name__ == "__main__":
    main()
