# Kallisto V1 Portfolio Rules

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
- Microcap universe filtered by the project rules and available public data

### Nasdaq Titans

- Large Nasdaq-listed companies used as the high-liquidity comparison universe
- Duplicate share classes filtered where possible

The final intraday candidate list is based primarily on the highest available premarket trading volume within each universe. Kallisto V1 currently keeps approximately the top 8 usable candidates from each side.

## Direction

- LONG allowed
- Synthetic SHORT allowed

Synthetic shorting is research-only. Full notional is reserved as collateral and short proceeds are not reused, so the simulated portfolio does not intentionally use leverage.

## Targets and reward/risk

Kallisto uses volatility-aware minimum intraday targets rather than a fixed swing-trade target:

- Microcap default minimum target: **0.90%**
- Nasdaq Titan default minimum target: **0.45%**
- Minimum reward/risk floor: **1.5:1** by default

The adaptive evaluator may adjust these within narrow hard-coded ranges. The deterministic engine may also raise a proposed target when necessary to preserve the active reward/risk floor.

## Trade frequency

There is no hard daily trade-count target. Actual trade count is constrained by signal quality, available capital, risk capacity, maximum simultaneous positions, the daily-loss circuit breaker, and the 15:30 ET entry cutoff.

## Market hours

- Monitoring begins around 09:25 ET.
- New entries are allowed after approximately 09:40 ET.
- Position monitoring is approximately every 5 minutes.
- LLM decisions are approximately every 15 minutes when due.
- New entries stop at 15:30 ET.
- Remaining positions are closed around 15:55 ET.

## Adaptive rule changes

Kallisto may tune only an allow-list of bounded parameters after sufficient evidence. It cannot remove the no-leverage, no-options, same-day-flat, daily-loss, or drawdown-protection rules.
