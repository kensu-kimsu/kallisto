import yfinance as yf
from yfinance import EquityQuery
import pandas as pd
from user_side.personal_experiment.broker.moomoo_policy import filter_new_position_candidates


NASDAQ_EXCHANGES = [
    "NMS",
    "NGM",
    "NCM",
]


def get_titan_universe(top_n: int = 20):

    query = EquityQuery(
        "and",
        [
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("is-in", ["exchange", *NASDAQ_EXCHANGES]),
        ]
    )

    # Pull more than 20 because we may remove duplicate share classes
    # or entries with incomplete metadata.
    result = yf.screen(
        query,
        size=80,
        sortField="intradaymarketcap",
        sortAsc=False,
    )

    quotes = result.get("quotes", [])

    rows = []
    seen_companies = set()

    for q in quotes:

        symbol = q.get("symbol")

        if not symbol:
            continue

        try:
            info = yf.Ticker(symbol).info
        except Exception:
            continue

        quote_type = info.get("quoteType")
        exchange = info.get("exchange")
        company_name = info.get("longName") or info.get("shortName")
        market_cap = info.get("marketCap")
        price = info.get("regularMarketPrice")
        volume = info.get("regularMarketVolume")

        # Equity only
        if quote_type != "EQUITY":
            continue

        # Nasdaq only
        if exchange not in NASDAQ_EXCHANGES:
            continue

        if not company_name or not market_cap or not price:
            continue

        # Prevent multiple share classes from occupying multiple slots.
        # Example: GOOG + GOOGL
        if company_name in seen_companies:
            continue

        seen_companies.add(company_name)

        rows.append({
            "ticker": symbol,
            "name": company_name,
            "exchange": exchange,
            "market_cap": market_cap,
            "price": price,
            "volume": volume or 0,
        })

        if len(rows) >= top_n:
            break

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError(
            "No Nasdaq Titan stocks were returned after filtering."
        )

    df = df.sort_values(
        "market_cap",
        ascending=False
    ).reset_index(drop=True)

    df = filter_new_position_candidates(df)
    return df


if __name__ == "__main__":

    titans = get_titan_universe()

    print("\nTOP 20 NASDAQ TITAN STOCKS BY MARKET CAP\n")

    for i, row in enumerate(titans.itertuples(), start=1):

        print(
            f"{i:>2}. "
            f"{row.ticker:<7} "
            f"${row.price:<10,.2f} "
            f"{row.exchange:<4} "
            f"Market Cap: ${row.market_cap:>18,.0f} "
            f"| {row.name}"
        )
