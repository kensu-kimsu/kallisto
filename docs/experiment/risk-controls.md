# Risk Controls

The experiment includes hard programmatic safeguards.

## Order Validation

Checks include:

- allowed action type
- approved universe membership
- positive whole-share quantity
- positive limit price
- confidence between 0 and 1
- valid stop loss for buys
- sufficient simulated cash
- sell quantity not exceeding owned shares
- updates only for existing holdings

## Session Protection

Before an OpenAI call, the workflow checks:

- valid NYSE session
- duplicate session
- portfolio synchronization
- missed sessions

This prevents unnecessary API spending and protects experiment chronology.
