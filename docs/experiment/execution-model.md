# Kallisto V1 Execution Model

Kallisto V1 is a simulation-only intraday model using public 5-minute market-data bars.

## Entry

The LLM may propose a LONG or synthetic SHORT hypothesis for a ticker in the current premarket-volume candidate set.

The deterministic engine then decides whether risk capacity exists and calculates a whole-share size using the active adaptive configuration. The current V1 defaults include:

- 0.5% per-trade risk budget
- 1.5% maximum combined open risk
- 30% single-position notional cap
- 75% gross-exposure cap
- 15% minimum cash reserve
- maximum 3 simultaneous positions

Hypothetical entry slippage:

- Microcap: **0.15%**
- Titan: **0.03%**

## Monitoring

Open positions are checked against subsequent 5-minute bars.

For LONG positions:

- stop triggers when the bar low reaches the stop
- target triggers when the bar high reaches the target

For synthetic SHORT positions:

- stop triggers when the bar high reaches the stop
- target triggers when the bar low reaches the target

If both target and stop are reached in the same bar, the simulator assumes the stop occurred first.

After a completed bar closes at least +1R in favor of the position, Kallisto can arm breakeven protection for later bars. This avoids same-bar lookahead.

## Exit

Positions can close through:

- TARGET
- STOP
- STOP_FIRST_SAME_BAR
- TIME_STOP
- FORCED_EOD_FLAT

The default maximum holding time is 75 minutes and may be adjusted only within bounded adaptive limits. All remaining positions are closed around 15:55 ET. Overnight carry is not allowed.

## Important simulation limits

This model does not reproduce real order-book priority, bid/ask spreads, partial fills, trading halts, short locates, borrow fees, commissions, regulatory fees, or market impact. Moomoo is the intended future brokerage integration target, but Kallisto V1 does not use the Moomoo API and does not submit live orders.
