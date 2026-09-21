from .microcap_screener import get_microcap_universe
from .titan_screener import get_titan_universe


def get_microcap_prompt_data():
    df = get_microcap_universe()

    lines = [
        "ELIGIBLE MICROCAP CANDIDATES",
        "New positions may ONLY be initiated from this list.",
        "",
        "Ticker | Price | Market Cap | Volume | Avg Volume | Company",
        "-" * 100,
    ]

    for row in df.itertuples():
        lines.append(
            f"{row.ticker} | "
            f"${row.price:,.2f} | "
            f"${row.market_cap:,.0f} | "
            f"{row.volume:,.0f} | "
            f"{row.avg_volume:,.0f} | "
            f"{row.name}"
        )

    return "\n".join(lines)


def get_titan_prompt_data():
    df = get_titan_universe()

    lines = [
        "ELIGIBLE NASDAQ TITAN CANDIDATES",
        "New positions may ONLY be initiated from this list.",
        "",
        "Ticker | Price | Market Cap | Volume | Company",
        "-" * 100,
    ]

    for row in df.itertuples():
        lines.append(
            f"{row.ticker} | "
            f"${row.price:,.2f} | "
            f"${row.market_cap:,.0f} | "
            f"{row.volume:,.0f} | "
            f"{row.name}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    print("\n=== MICROCAP ===\n")
    print(get_microcap_prompt_data())

    print("\n\n=== NASDAQ TITANS ===\n")
    print(get_titan_prompt_data())
