# Kallisto Live-transfer Principles

Kallisto V1 is intentionally simulation-only, but its strategy and risk behavior should remain reusable in a future Moomoo Australia paper/live deployment.

The design boundary is simple: the Kallisto LLM proposes; deterministic risk controls approve or reject; a broker adapter executes and reconciles. The LLM must never bypass the risk layer or directly submit unrestricted orders.

Future live migration should preserve Kallisto strategy inputs, adaptive-learning policy, position-sizing rules, stop/target logic, trading windows, decision timestamps, version history, and reporting. The market-data and execution backends should be replaced with broker-grade equivalents, while production safeguards must be added around data freshness, broker state, order idempotency, partial fills, short eligibility, and end-of-day reconciliation.

Exact simulated P/L is not expected to transfer 1:1 because live trading introduces spreads, latency, order queues, partial fills, rejects, short availability, borrow costs, halts, fees, and market impact. Those differences should be measured explicitly during Moomoo real-time-data and paper-trading stages before any real-money pilot.
