# Kallisto V1 API Usage and Cost Tracking

Kallisto records every paid OpenAI trading-decision call and weekly evaluator call in:

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

Decision and evaluation logs keep token/cost information beside the associated model activity for research traceability.

## Pricing snapshot

Kallisto V1 currently uses `gpt-5.6-luna`.

The tracker is configured with this pricing table:

| Token type | USD per 1M tokens |
|---|---:|
| Input | $0.20 |
| Cached input | $0.02 |
| Output | $1.20 |

The pricing values are stored in:

`user_side/personal_experiment/scalping_api_costs.py`

If Kallisto changes model or pricing changes, that table must be updated. OpenAI billing remains the source of truth; repository values are research estimates calculated from reported token usage.

## README running summary

The cost tracker maintains the marked API-cost summary used by the Kallisto README/dashboard when that README copy is available to the reporting process. Azure remains the source of runtime logs and GitHub's post-market documentation workflow refreshes repository-facing results.

Tracked summary values include:

- average cost per active trading day
- average cost per active ISO week
- average cost per active calendar month
- total estimated API cost
- corresponding calls and token counts

## Calls that cost $0 OpenAI API money

OpenAI is not called when the NYSE is closed, before the decision window, after the entry cutoff, when the decision interval is not due, or when no eligible candidate has usable data.

Technical calculations, position monitoring, stop/target checks, benchmark calculations, chart generation, Git operations, and yfinance retrieval do not create OpenAI token charges.

The bounded weekly self-evaluator does create an additional paid call when its 5-session review becomes due.
