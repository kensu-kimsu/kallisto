# Final V1 Reporting

The final V1 stores its live experiment state under:

`user_side/runs/scalping_v1/`

## Files

### `portfolio_state.json`

Current simulated cash, open positions, high-water mark, session state, cached premarket leaders, and benchmark bases.

### `decision_log.jsonl`

One JSON record per LLM decision cycle containing model-token counts, raw model output, validated proposals, opened simulated positions, and positions closed during that cycle.

### `trade_log.csv`

Closed simulated trades with:

- entry/exit timestamps
- ticker and universe
- LONG/SHORT direction
- shares
- entry/exit prices
- stop and target
- P/L
- return percentage
- exit reason
- model confidence and rationale

### `daily_performance.csv`

Daily portfolio and benchmark summary including:

- starting equity
- ending equity
- daily return
- cumulative return
- trade count
- wins/losses
- win rate
- normalized S&P 500 value
- normalized Nasdaq-100 value

## Daily journal

Each completed NYSE session creates:

`docs/journal/daily/YYYY-MM-DD.md`

## Chart

The comparison chart is regenerated as:

`docs/results/scalping_equity_comparison.png`

It plots the final V1 portfolio against normalized $1,000 S&P 500 and Nasdaq-100 series.

## Evaluation

The six-month result should be judged from recorded data rather than an assumption of profitability. Key outcomes include total return, benchmark-relative return, drawdown, win rate, trade frequency, stop/target behavior, and failure modes.
