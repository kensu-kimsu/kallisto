# Kallisto V1 Risk Controls

Risk management is deterministic and cannot be overridden by the trading LLM or the adaptive evaluator.

## Current hard/default portfolio controls

| Control | Current V1 setting |
|---|---:|
| Risk per new trade | 0.5% of current equity |
| Maximum combined open stop risk | 1.5% of current equity |
| Maximum gross exposure | 75% of current equity |
| Maximum single-position notional | 30% of current equity |
| Minimum uncommitted cash reserve | 15% of current equity |
| Daily loss circuit breaker | 2% from session-start equity |
| Portfolio drawdown pause | 10% from high-water mark |
| Maximum open positions | 3 |
| Maximum holding time | 75 minutes |
| Minimum LLM confidence | 0.58 |
| Minimum reward/risk floor | 1.5:1 |

Some tunable values may change as Kallisto learns, but only inside narrow hard-coded bounds. Safety-critical rules such as the daily-loss breaker, drawdown pause, no-leverage rule, and end-of-day flat requirement are not removable by the evaluator.

## Stop model

Stops are based on current ATR percentage and clamped to a universe-specific intraday range:

- Microcap: **0.6% to 1.8%**
- Nasdaq Titan: **0.3% to 0.9%**

The target must also satisfy the active minimum reward/risk rule. Default minimum targets are 0.90% for microcaps and 0.45% for Titans.

## Breakeven protection

After a completed 5-minute bar closes at least +1R in favor of the position, Kallisto may move the stop to approximately the entry price for subsequent bars. This avoids same-bar lookahead.

## No leverage

Long positions consume their simulated purchase notional.

Synthetic short positions reserve the full entry notional as collateral. Short-sale proceeds are not added to buying power. This is a simulation convention designed to keep effective gross exposure unleveraged.

## Intraday circuit breakers

- No new entries after 15:30 ET.
- A 2% session loss pauses new entries for the remainder of the session.
- A 10% portfolio drawdown from the recorded high-water mark pauses new entries.
- Positions are time-stopped after the active maximum holding period if neither target nor stop has fired.
- All remaining positions are force-closed around 15:55 ET.

## Same-bar ambiguity

The simulator uses 5-minute OHLC data. If both a stop and target are touched within one bar, the exact sequence is unknown, so Kallisto conservatively assumes the stop was hit first.

## Adaptive bounds

Kallisto's evaluator may propose small changes to selected parameters such as confidence threshold, risk per trade, open-risk cap, gross exposure, single-position cap, cash reserve, reward/risk floor, maximum positions, holding time, and minimum targets. All proposed values are clamped to predefined bounds before they can become active.

## Limitations

Stops do not guarantee real-world execution prices. Microcap gaps, trading halts, spreads, liquidity, short borrow availability, and latency can produce outcomes very different from this simulation.
