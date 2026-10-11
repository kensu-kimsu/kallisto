# Kallisto V1 Model Policy

## Trading decision model

Intraday decision cycles use **GPT-5.6 Luna**.

The model may propose:

- ticker
- LONG or SHORT direction
- target percentage
- confidence
- short rationale based only on supplied evidence

## Adaptive evaluator

Kallisto also uses a bounded evaluator that reviews measured trading results every 5 completed NYSE sessions. It may propose small changes to an allow-list of strategy parameters and may write short learning notes that are fed into future decision prompts.

The evaluator does **not** retrain model weights. It cannot make arbitrary code changes and cannot disable the hard portfolio safety rules.

A parameter change requires sufficient evidence, including at least 20 completed trades, at least 10 completed sessions since the previous accepted change, and evaluator confidence of at least 0.60.

## What the models do not control

Deterministic code remains responsible for:

- final share count
- ATR-based stop distance
- hard parameter bounds
- exposure limits
- daily-loss circuit breaker
- portfolio drawdown pause
- no-leverage rule
- same-day-flat requirement
- end-of-day forced closure

Neither the trading model nor the evaluator can override these protections.

## Evidence policy

The prompt supplies public technical and fundamental/context fields. The models are explicitly told not to claim access to proprietary Wall Street models, hidden order flow, Level 2 feeds, undisclosed news, or financial data that is not provided.

## Human role

There is no manual trade approval in Kallisto V1. The human role is observer and software maintainer.

All trading activity remains hypothetical simulation data. No live brokerage action is performed.
