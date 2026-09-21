import yfinance as yf
from yfinance import EquityQuery
import pandas as pd
from user_side.personal_experiment.broker.moomoo_policy import filter_new_position_candidates


MICROCAP_MAX = 300_000_000

ALLOWED_EXCHANGES = [
    "NMS",
    "NGM",
    "NCM",
    "NYQ",
    "ASE",
]


def get_microcap_universe(candidate_count: int = 50):

    query = EquityQuery(
        "and",
        [
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("is-in", ["exchange", *ALLOWED_EXCHANGES]),
            EquityQuery("lt", ["intradaymarketcap", MICROCAP_MAX]),
            EquityQuery("gt", ["intradaymarketcap", 0]),
        ]
    )

    result = yf.screen(
        query,
        size=250,
        sortField="dayvolume",
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
        company_name = info.get("longName") or info.get("shortName")
        market_cap = info.get("marketCap")
        price = info.get("regularMarketPrice")
        volume = info.get("regularMarketVolume")
        avg_volume = info.get("averageVolume")
        exchange = info.get("exchange")

        if quote_type != "EQUITY":
            continue

        if exchange not in ALLOWED_EXCHANGES:
            continue

        if not company_name or not market_cap or not price:
            continue

        if market_cap >= MICROCAP_MAX:
            continue

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
            "avg_volume": avg_volume or 0,
        })

        if len(rows) >= candidate_count:
            break

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError("No microcap stocks were returned after filtering.")

    df = filter_new_position_candidates(df)
    return df.reset_index(drop=True)


if __name__ == "__main__":

    microcaps = get_microcap_universe()

    print("\nTOP 50 LIQUID EXCHANGE-LISTED MICROCAP CANDIDATES (< $300M)\n")

    for i, row in enumerate(microcaps.itertuples(), start=1):

        print(
            f"{i:>2}. "
            f"{row.ticker:<7} "
            f"${row.price:<9,.2f} "
            f"{row.exchange:<4} "
            f"Market Cap: ${row.market_cap:>14,.0f} "
            f"Volume: {row.volume:>12,.0f} "
            f"| {row.name}"
        )
