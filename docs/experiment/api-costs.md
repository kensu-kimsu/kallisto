# Final V1 API Usage Tracking

Every intraday LLM decision cycle records token usage in:

`user_side/runs/scalping_v1/decision_log.jsonl`

Each record includes:

- New York timestamp
- model name
- input tokens
- output tokens
- raw model JSON
- validated proposals
- simulated positions opened
- positions closed during that cycle

Final V1 does not hard-code a USD cost estimate because API prices may change during the six-month experiment. Token counts preserve enough information to calculate cost later using the applicable pricing for each period.

OpenAI is not called when the NYSE is closed, the workflow is outside the regular-market decision window, the entry cutoff has passed, or the risk pause blocks new entries.
