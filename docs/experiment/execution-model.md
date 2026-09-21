# Execution Model

Approved recommendations become pending simulated orders.

Pending orders are evaluated on the applicable NYSE session.

The simulator determines whether each LIMIT order could have filled using market data for that day.

If filled, the system updates:

- cash
- holdings
- trade history
- position history
- portfolio equity
- performance metrics

A pending order is not treated as filled until the simulated execution rules are satisfied.
