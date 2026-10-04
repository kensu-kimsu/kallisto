# How to Read This Repository

Start with the root `README.md`. It describes the **final V1 autonomous LLM scalping experiment** that is currently active.

## Final V1 experiment documents

Read these next:

1. [experiment/methodology.md](experiment/methodology.md) - research design and intraday workflow
2. [experiment/portfolio-rules.md](experiment/portfolio-rules.md) - eligible universes and trading rules
3. [experiment/risk-controls.md](experiment/risk-controls.md) - deterministic capital protection
4. [experiment/execution-model.md](experiment/execution-model.md) - hypothetical fills, stops, targets, and forced close
5. [experiment/model-policy.md](experiment/model-policy.md) - what the LLM may and may not decide
6. [experiment/reporting.md](experiment/reporting.md) - state, trades, journals, charts, and benchmarks
7. [experiment/api-costs.md](experiment/api-costs.md) - model token-usage tracking

Daily experiment records are written under `docs/journal/daily/`, and the benchmark comparison chart is written under `docs/results/` after sufficient experiment data exists.

## Final V1 code

The active experiment entry point is:

`user_side/personal_experiment/scalping_v1.py`

Supporting modules:

- `scalping_market_data.py`
- `scalping_strategy.py`
- `scalping_engine.py`
- `scalping_state.py`
- `scalping_reporting.py`

Persistent final V1 state is stored in:

`user_side/runs/scalping_v1/`

## Original framework documentation

The remaining documentation in this folder describes the underlying LIBB framework and original project architecture. It is retained for attribution, reference, and future development, but some original workflow documents do not describe the active final V1 scalping experiment.

The repository remains based on Nathan Smith / LuckyOne7777's LLM-Investor-Behavior-Benchmark and LLM-Trading-Lab work, with the original MIT attribution retained.
