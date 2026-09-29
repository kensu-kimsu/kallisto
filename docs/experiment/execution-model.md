# Execution Model

The LLM proposes simulated orders.

Before they are saved, the workflow applies:
- structural order validation
- universe validation
- cash validation
- deterministic portfolio-risk validation

When GitHub Actions runs with `AUTO_APPROVE_SIMULATED_ORDERS=true`, a valid simulated recommendation is automatically approved.

Approved recommendations become pending simulated orders. On the applicable NYSE session, LIBB evaluates whether each LIMIT order could have filled using market data for that day.

If filled, the system updates cash, holdings, trade history, position history, portfolio equity, and performance metrics.

This repository performs simulation only and does not place live brokerage orders.
