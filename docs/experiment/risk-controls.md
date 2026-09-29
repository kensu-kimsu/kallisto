# Risk Controls

V1 was reset on 2026-09-29 so the experiment could restart with deterministic capital-management rules from Day 1.

## Hard portfolio limits

Common:
- minimum cash reserve: 20% of current equity
- maximum gross long exposure: 80% of current equity
- maximum aggregate planned stop risk: 6% of current equity
- same-session SELL proceeds do not fund new BUY orders
- existing stops may be tightened but not loosened

Microcap Growth:
- maximum single position: 20% of equity
- maximum planned stop risk per new BUY: 1.5% of equity
- maximum open positions: 4
- BUY stop distance: 5% to 20%

Nasdaq Titan Growth:
- maximum single position: 30% of equity
- maximum planned stop risk per new BUY: 2.0% of equity
- maximum open positions: 3
- BUY stop distance: 3% to 15%

These are deterministic code checks. The LLM cannot override them.

A stop loss defines planned downside but cannot guarantee the final exit price during a gap.

The pre-reset V1 state is preserved on `archive/v1-pre-risk-reset-2026-09-29`.
