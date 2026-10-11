# Kallisto -> Moomoo Australia Transfer Checklist

Kallisto V1 remains simulation-only. This document defines what should stay conceptually consistent and what must change before using Kallisto with Moomoo Australia paper or live trading.

## Preserve across environments

The following should remain consistent across simulation, paper and live environments so results can be compared fairly:

- Kallisto premarket candidate-selection rules
- technical feature calculations and timestamps
- LLM prompt policy and model version
- adaptive-learning policy and strategy-version history
- long/short proposal schema
- deterministic position-sizing and portfolio-risk rules
- entry cutoff and forced-flat policy
- decision identifiers and timestamps
- benchmark methodology
- daily reporting and API-cost accounting

## Replace with Moomoo-backed components

The public-data and synthetic execution layers must be swapped for broker-backed implementations:

1. MarketDataProvider
   - real-time quotes
   - bid/ask and order book where available
   - streaming K-lines / trades
   - market status and stale-data detection

2. ExecutionGateway
   - account and position query
   - buying power / maximum trade quantity
   - order placement
   - modify/cancel
   - acknowledgement and order-state stream
   - partial fills and rejects
   - fill-price reconciliation
   - short eligibility / borrow constraints
   - end-of-day flat verification

## Source of truth

For paper/live trading, the broker is authoritative for cash, buying power, positions, open orders, fills and order status.

The Kallisto live agent must reconcile against the broker after every order event. Any unexplained mismatch must trigger a fail-closed trading pause.

## Required live safety controls

Before real money is enabled:

- stale quote kill switch
- disconnected market-data kill switch
- disconnected trade-event kill switch
- broker/local state mismatch kill switch
- maximum daily loss kill switch outside the LLM
- maximum portfolio drawdown kill switch outside the LLM
- maximum order size and maximum gross exposure checks
- duplicate-order protection using idempotent client decision/order IDs
- retry policy that never blindly resubmits an uncertain order
- forced-flat check before the NYSE close
- alerting for rejects, repeated API errors, reconciliation failures and unexpected open positions
- secure OAuth/token storage with no secrets committed to GitHub

## Transfer-validation sequence

Use Kallisto progressively in more realistic environments:

1. Kallisto V1 public-data simulation.
2. Moomoo real-time market data while keeping hypothetical execution.
3. Moomoo API paper trading using broker order lifecycle and broker positions.
4. Shadow mode against live quotes: generate orders but do not submit them.
5. Small-capital live pilot with hard limits and manual emergency kill switch.
6. Scale only after paper/live statistics show that any simulated edge survives spreads, slippage, fill quality and broker constraints.

## Result interpretation

Kallisto strategy behavior may be transferable; exact simulated P/L is not assumed to transfer. The live-validation target is to measure the gap between intended and actual fills, simulated and actual slippage, simulated and broker-confirmed shortability, simulated and accepted trade count, and simulated versus paper/live P/L.

Those gaps should be reported explicitly rather than hidden, because they determine whether Kallisto is genuinely deployable with real money.
