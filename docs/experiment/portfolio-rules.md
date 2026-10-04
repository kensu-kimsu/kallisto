# Final V1 Portfolio Rules

## Portfolio

- One combined simulated portfolio
- Starting capital: $1,000 USD
- No external deposits during the six-month experiment
- Whole shares only
- No options
- No leverage
- No overnight positions

## Eligible stock sources

### Microcaps

- U.S.-listed equities
- Major U.S. exchanges
- Market capitalization below $300 million
- Existing restriction filtering remains available

### Nasdaq Titans

- Approximately top 20 distinct Nasdaq-listed companies by market capitalization
- Duplicate share classes filtered where possible

The final intraday candidate list is based on the highest available premarket trading volume within each universe.

## Direction

- LONG allowed
- Synthetic SHORT allowed

Synthetic shorting is research-only. Full notional is reserved as collateral and short proceeds are not reused, so the simulated portfolio does not intentionally exceed 1x gross capital.

## Profit target

Every LLM proposal must target at least 1.5% from simulated entry. The deterministic risk engine may increase that target to preserve the minimum reward-to-risk rule.

## Trade frequency

There is no hard daily trade-count limit. Actual trade count is constrained by signal quality, available capital, risk capacity, the daily-loss circuit breaker, and the 15:15 ET entry cutoff.

## Market hours

- Decisions are made only during regular NYSE market hours.
- New entries stop at 15:15 ET.
- Remaining positions are closed around 15:55 ET.
