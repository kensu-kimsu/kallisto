# Kallisto V1 Reporting

Kallisto's live runtime state is persisted in Azure Blob Storage. Local/reference copies remain under:

`user_side/runs/scalping_v1/`

## Core state files

### `portfolio_state.json`

Current simulated cash, open positions, high-water mark, session state, cached premarket leaders, and benchmark bases.

### `decision_log.jsonl`

One JSON record per LLM decision cycle containing model-token counts, strategy version, raw model output, validated proposals, opened simulated positions, and positions closed during that cycle.

### `trade_log.csv`

Closed simulated trades with entry/exit timestamps, ticker and universe, LONG/SHORT direction, shares, entry/exit prices, stop and target, P/L, return percentage, exit reason, model confidence, and rationale.

### `daily_performance.csv`

Daily portfolio and benchmark summary including starting equity, ending equity, daily return, cumulative return, trade count, wins/losses, win rate, normalized S&P 500 value, and normalized Nasdaq-100 value.

## Adaptive learning files

### `adaptive_config.json`

The currently active bounded Kallisto strategy parameters and version.

### `weekly_evaluations.jsonl`

Every scheduled self-evaluation, including measured evidence, evaluator proposal, eligibility result, accepted/rejected status, and API token/cost data.

### `improvement_metrics.csv`

Self-improvement metrics such as rolling 5-session return, benchmark return, alpha, win rate, profit factor, maximum drawdown, adaptive equity, frozen-V1 replay equity, and adaptive-vs-baseline result.

### `strategy_versions.csv`

Audit trail for V1.0, V1.1, V1.2 and later bounded strategy versions, including why each accepted change was made.

### `baseline_replay.csv`

Frozen V1.0 risk-control counterfactual using the realized trade sequence. It helps measure the effect of changing risk parameters but is not a fully independent second LLM.

## Daily journal

Each completed NYSE session creates a Kallisto journal under:

`docs/journal/daily/YYYY-MM-DD.md`

## Charts

Kallisto regenerates:

- `docs/results/scalping_equity_comparison.png` — Kallisto vs frozen V1.0 replay, S&P 500 and Nasdaq-100
- `docs/results/self_improvement_returns.png` — rolling adaptive and benchmark returns
- `docs/results/self_improvement_alpha.png` — rolling alpha versus the stronger benchmark

The root README embeds the Kallisto dashboard and is refreshed from Azure after market sessions.

## Evaluation

The six-month result is judged from recorded evidence rather than an assumption of profitability. Key outcomes include total return, benchmark-relative return, adaptive-vs-frozen-V1 result, drawdown, win rate, profit factor, trade frequency, stop/target behavior, strategy-version history, and failure modes.
