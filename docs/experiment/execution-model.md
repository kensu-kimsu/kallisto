# Final V1 Execution Model

The final V1 is a simulation-only intraday model using 5-minute public market-data bars.

## Entry

The LLM may propose a LONG or synthetic SHORT hypothesis for a ticker in the current premarket-volume candidate set.

The deterministic engine then decides whether risk capacity exists and calculates a whole-share size using:

- current portfolio equity
- stop distance
- 0.5% per-trade risk budget
- 1.5% maximum combined open risk
- 25% single-position notional cap
- 90% gross-exposure cap
- 10% cash-reserve rule

Hypothetical entry slippage:

- Microcap: 0.20%
- Titan: 0.05%

## Monitoring

Open positions are checked against subsequent 5-minute bars.

For LONG positions:

- stop triggers when the bar low reaches the stop
- target triggers when the bar high reaches the target

For synthetic SHORT positions:

- stop triggers when the bar high reaches the stop
- target triggers when the bar low reaches the target

If both target and stop are reached in the same bar, the simulator assumes the stop occurred first.

## Exit

Positions can close through:

- TARGET
- STOP
- STOP_FIRST_SAME_BAR
- FORCED_EOD_FLAT

All remaining positions are closed around 15:55 ET. Overnight carry is not allowed.

## Important simulation limits

This model does not reproduce real order-book priority, bid/ask spreads, partial fills, trading halts, short locates, borrow fees, commissions, regulatory fees, or market impact. Moomoo is the intended reference brokerage application, but no Moomoo API is used and no live order is submitted.
