# Final V1 API Usage and Cost Tracking

Final V1 records every paid OpenAI decision call in:

`user_side/runs/scalping_v1/api_costs.csv`

Each record includes:

- New York timestamp
- NYSE session date
- model name
- input tokens
- cached input tokens
- output tokens
- uncached-input cost
- cached-input cost
- output cost
- total estimated cost for that API call

The decision log also keeps the token/cost information beside the model decision for research traceability.

## Pricing snapshot

Final V1 currently uses `gpt-5.6-luna`.

The tracker is configured with the OpenAI standard text-token pricing published for GPT-5.6 Luna on 2026-10-08:

| Token type | USD per 1M tokens |
|---|---:|
| Input | $0.20 |
| Cached input | $0.02 |
| Output | $1.20 |

The pricing values are deliberately stored in one module:

`user_side/personal_experiment/scalping_api_costs.py`

If the experiment changes model or OpenAI pricing changes, that table must be updated. OpenAI billing remains the source of truth; repository values are research estimates calculated from reported token usage.

## README running summary

After every paid LLM decision call, the tracker refreshes a marked table in the repository README containing:

- average cost per active trading day
- average cost per active ISO week
- average cost per active calendar month
- total actual estimated API cost
- corresponding average/total calls and token counts

Averages are based on periods that contain at least one recorded API call. During a partially completed trading day/week/month, those running averages are naturally provisional.

## Calls that cost $0 OpenAI API money

OpenAI is not called when the NYSE is closed, before the decision window, after the entry cutoff, when the decision interval is not due, when no eligible candidate has usable data, or when a deterministic risk pause prevents a new decision.

Technical calculations, position monitoring, stop/target checks, benchmark calculations, chart generation, Git operations, and yfinance retrieval do not create OpenAI token charges.
