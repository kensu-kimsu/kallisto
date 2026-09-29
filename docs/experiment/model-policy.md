# Model Policy

Completed Monday-Thursday NYSE sessions use **GPT-5.6 Luna**.

Completed Friday NYSE sessions use **GPT-5.6 Terra** for the deeper weekly review.

The LLM proposes investment decisions, but portfolio risk limits are enforced by deterministic code outside the model.

Valid simulated orders are automatically approved only after validation when `AUTO_APPROVE_SIMULATED_ORDERS=true`.

The human role is observer and software maintainer rather than discretionary trade approver.
