# Kallisto Moomoo Paper Trading V0

This is a **paper-trading-only** bridge. The live Kallisto experiment remains simulation-only and the broker adapter hard-blocks live execution.

## What V0 adds

- broker account/position/order snapshot
- reconciliation between Kallisto expected positions and Moomoo paper positions
- deterministic duplicate-order protection
- stale-quote blocking
- daily-loss lockout before new entries
- paper-only environment enforcement
- manual symbol restriction support
- short-entry blocking unless short availability is explicitly verified
- order-state refresh including requested quantity, dealt quantity, remaining quantity and average fill price
- partial-fill detection
- cancellation of individual/open paper orders
- end-of-day flat verification
- reduce orders for end-of-day flattening

## Important design rule

The LLM never talks directly to Moomoo.

```text
Kallisto LLM proposal
        ->
deterministic risk engine
        ->
broker safety gate
        ->
MoomooPaperBroker
        ->
Moomoo OpenD / paper account
        ->
actual broker order + position state
        ->
reconciliation
```

Any failed safety check blocks a new order.

## Current safety status

Real trading is intentionally disabled in code. `MoomooPaperBroker` always uses `TrdEnv.SIMULATE`. The current Azure-hosted Kallisto experiment is unchanged and continues to use its simulation execution gateway.

## Local paper-trading host setup

Moomoo OpenD must be running on the machine that executes the paper adapter. The Python SDK is intentionally not added to the main Azure `requirements.txt`; this avoids changing the current production experiment before paper testing begins.

On the dedicated paper host, install the Moomoo OpenAPI Python SDK according to the current official Moomoo OpenAPI documentation, then run OpenD locally (default host `127.0.0.1`, port `11111`).

Do not enter or commit account passwords, unlock passwords, tokens, or credentials into this repository.

## Paper-trading lifecycle

For each proposed trade:

1. Query broker account, positions and orders.
2. Reconcile broker state with Kallisto's expected state.
3. Reject the proposal if state does not reconcile.
4. Reject if the quote is stale.
5. Reject if the daily loss breaker is reached.
6. Reject duplicate order intents.
7. Reject restricted symbols.
8. For shorts, require explicit broker short-availability confirmation.
9. Submit only to `TrdEnv.SIMULATE`.
10. Poll the order state.
11. Use broker-reported `dealt_qty` and `dealt_avg_price`; do not assume the requested quantity filled.
12. Reconcile positions again after fills/cancellations.

## End of day

1. Stop new entries before the configured cutoff.
2. Cancel any remaining entry orders individually.
3. Query actual paper positions.
4. Submit reduce orders for any remaining positions.
5. Keep checking broker state until positions are zero.
6. Record `EOD_FLAT_CONFIRMED` only when Moomoo reports no remaining positions.

If Kallisto cannot confirm flat status, the next session must start locked until the discrepancy is resolved.

## Why this is separate from the existing simulation

We want to compare three datasets without contaminating them:

- `simulation_data`
- `paper_broker_data`
- future `live_data`

The current six-month simulation history remains intact. Paper trading is the bridge used to measure the gap between hypothetical fills and broker-reported paper execution.

## Promotion gates before any live branch

A future live branch should not be enabled until paper trading demonstrates, over a meaningful sample, all of the following:

- no duplicate orders
- no unexplained reconciliation failures
- no stale-data entries
- correct handling of partial fills
- correct order cancellation behavior
- no unintended overnight positions
- daily-loss lockout works
- short orders are blocked unless eligibility is verified
- paper execution results are reasonably consistent with the simulated strategy

A separate code review and explicit live-enable change should be required before any real-money capability is added.
