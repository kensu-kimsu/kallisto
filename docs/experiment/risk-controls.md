# Final V1 Risk Controls

Risk management is deterministic and cannot be overridden by the LLM.

## Hard portfolio limits

| Control | Rule |
|---|---:|
| Risk per new trade | 0.5% of current equity |
| Maximum combined open stop risk | 1.5% of current equity |
| Maximum gross exposure | 90% of current equity |
| Maximum single-position notional | 25% of current equity |
| Minimum uncommitted cash reserve | 10% of current equity |
| Daily loss circuit breaker | 2% from session-start equity |
| Portfolio drawdown pause | 10% from high-water mark |
| Minimum LLM confidence | 0.60 |

## Stop model

Stops are based on current ATR percentage and then clamped to a universe-specific range:

- Microcap: 1.0% to 2.5%
- Nasdaq Titan: 0.5% to 1.25%

Each accepted trade must target at least 1.5%. The engine also enforces a minimum 1.5:1 reward-to-risk relationship, so the actual target may be greater than 1.5%.

## No leverage

Long positions consume their simulated purchase notional.

Synthetic short positions reserve the full entry notional as collateral. Short-sale proceeds are not added to buying power. This is a simulation convention designed to keep effective gross exposure unleveraged.

## Intraday circuit breakers

- No new entries after 15:15 ET.
- A 2% session loss pauses new entries for the remainder of the session.
- A 10% portfolio drawdown from the recorded high-water mark pauses new entries.
- All remaining positions are force-closed around 15:55 ET.

## Same-bar ambiguity

The simulator uses 5-minute OHLC data. If both a stop and target are touched within one bar, the exact sequence is unknown, so the conservative assumption is that the stop was hit first.

## Limitations

Stops do not guarantee real-world execution prices. Microcap gaps, trading halts, spreads, liquidity, short borrow availability, and latency can produce outcomes very different from this simulation.
