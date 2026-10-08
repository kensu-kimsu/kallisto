# Live-transfer principles

Final V1 is intentionally simulation-only, but its strategy and risk behavior should remain reusable in a future Moomoo Australia paper/live deployment.

The design boundary is simple: the LLM proposes; deterministic risk controls approve or reject; a broker adapter executes and reconciles. The LLM must never bypass the risk layer or directly submit unrestricted orders.

Future live migration should preserve strategy inputs, LLM policy, position-sizing rules, stop/target logic, trading windows, decision timestamps, and reporting. Only the market-data and execution backends should change.

Exact simulated P/L is not expected to transfer 1:1 because live trading introduces spreads, latency, order queues, partial fills, rejects, short availability, borrow costs, halts, fees, and market impact. Those differences should be measured explicitly during Moomoo real-time-data and paper-trading stages before any real-money pilot.
