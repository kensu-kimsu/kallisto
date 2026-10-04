# Final V1 Model Policy

## Decision model

Intraday decision cycles use **GPT-5.6 Luna**.

The model may propose:

- ticker
- LONG or SHORT direction
- target percentage
- confidence
- short rationale based only on supplied evidence

## What the model does not control

Deterministic code controls:

- final share count
- ATR-based stop distance
- exposure limits
- per-trade risk
- combined open risk
- cash reserve
- daily-loss circuit breaker
- end-of-day forced closure

The model cannot override these controls.

## Evidence policy

The prompt supplies public technical and fundamental/context fields. The model is explicitly told not to claim access to proprietary Wall Street models, hidden order flow, Level 2 feeds, undisclosed news, or financial data that is not provided.

## Human role

There is no manual trade approval in final V1. The human role is observer and software maintainer.

All trading activity remains hypothetical simulation data. No live brokerage action is performed.
