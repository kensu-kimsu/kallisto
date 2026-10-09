# Final V1 - Autonomous LLM Scalping Experiment

A six-month **simulation-only** research experiment testing whether an autonomous LLM-guided intraday scalping process can grow a $1,000 USD portfolio and outperform both the S&P 500 and Nasdaq-100.

> This repository does not place live orders or move real money. Moomoo Australia is the intended future broker integration target, but Final V1 remains a simulation.

## Original project and attribution

This project is built on and inspired by **Nathan Smith / LuckyOne7777**:

- LLM-Investor-Behavior-Benchmark
- LLM-Trading-Lab

The original MIT license and copyright notice are retained.

## Research objective

> Can a fully autonomous LLM-guided intraday strategy, constrained by deterministic risk controls and focused on premarket volume leaders, achieve positive simulated capital growth and outperform the S&P 500 and Nasdaq-100 over six months?

Positive returns and benchmark outperformance are objectives, not guarantees.

## Final V1 baseline

- Starting capital: **$1,000 USD**
- Clean Day 1: **the first complete Azure-hosted NYSE session after deployment**
- Oct 7-8 infrastructure attempts are excluded from the clean performance series
- No external deposits
- No leverage
- No options
- Whole shares only
- LONG and synthetic 1x SHORT trades allowed
- No overnight positions
- No manual trade approval

## Azure Functions runtime

Final V1 now uses **Azure Functions as the trading clock**. The unreliable GitHub Actions market schedule has been retired and is manual-only.

```text
Azure timer trigger every 5 minutes on weekdays
        ->
restore state from Azure Blob Storage
        ->
NYSE calendar/time guard
        ->
5-minute market data + position monitoring
        ->
GPT-5.6 Luna decision when ~15-minute cadence is due
        ->
deterministic risk engine
        ->
hypothetical LONG / SHORT execution
        ->
persist state + reports to Azure Blob Storage
        ->
function exits
```

The timer runs on a five-minute weekday cadence while the Python strategy itself decides whether the current New York time is inside the experiment window. This avoids hard-coding daylight-saving changes into UTC schedules.

Runtime entry point:

```text
function_app.py
```

Azure state adapter:

```text
user_side/personal_experiment/azure_runtime.py
```

Azure deployment guide:

```text
docs/experiment/azure-functions-deployment.md
```

## Trading universe

Each trading day combines approximately the top **8 eligible microcaps by premarket volume** and top **8 available Nasdaq Titan candidates by premarket volume**.

Technical inputs include premarket volume/change, VWAP, EMA 9/20, RSI(14), MACD, ATR, relative volume and opening-range levels. Fundamental context may include market cap, float, beta, valuation, profitability, growth, leverage, ROE and short interest when available.

The LLM may only use supplied information and must not invent catalysts, Level 2 data, hidden order flow, proprietary signals or undisclosed news.

## Intraday timing

- monitoring begins around **09:25 ET**
- first entries allowed after **09:40 ET**
- LLM decision cadence: approximately **15 minutes**
- position monitoring cadence: approximately **5 minutes**
- no new entries after **15:30 ET**
- all remaining positions forced flat around **15:55 ET**

## Risk management

The LLM proposes ticker, direction, target, confidence and rationale. Deterministic code controls position size, stop distance, exposure and portfolio safety.

Core protections include per-trade risk budgeting, combined open-risk limit, gross exposure limit, single-position cap, cash reserve, daily-loss breaker, drawdown pause, maximum simultaneous positions, volatility stops, minimum reward/risk, breakeven protection, time-stop exits and forced end-of-day flat.

## Experiment state

During Azure execution the persistent source of truth is the Azure Blob container:

```text
scalping-v1-state/
  state/portfolio_state.json
  state/decision_log.jsonl
  state/trade_log.csv
  state/daily_performance.csv
  state/api_costs.csv
  reports/...
```

Repository copies under `user_side/runs/scalping_v1/` remain the initial/reference dataset and can be refreshed from Azure for reporting.

## OpenAI API cost tracking

Every paid LLM decision records token usage and an estimated USD cost in `api_costs.csv`.

<!-- API_COST_SUMMARY_START -->
| Cost period | API cost (USD) | API calls | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| Average daily | $0.0000 | 0.0 | 0 | 0 |
| Average weekly | $0.0000 | 0.0 | 0 | 0 |
| Average monthly | $0.0000 | 0.0 | 0 | 0 |
| **Total actual** | **$0.0000** | **0** | **0** | **0** |
<!-- API_COST_SUMMARY_END -->

OpenAI billing remains the source of truth for actual API charges.

## GitHub Actions

GitHub is now used for source control, smoke testing and deployment—not as the live market clock.

```text
.github/workflows/scalping-smoke-test.yml
.github/workflows/deploy-azure-function.yml
.github/workflows/daily-trading-experiment.yml   # legacy/manual only
```

The Azure deployment workflow is intentionally manual until Azure resources, repository variables and secrets have been configured.

## Live-transfer design for Moomoo Australia

Broker-neutral interfaces are defined in:

```text
user_side/personal_experiment/scalping_interfaces.py
```

Current Final V1:

```text
MarketDataProvider -> yfinance/public 5-minute data
ExecutionGateway  -> deterministic simulation engine
```

Future Moomoo deployment:

```text
MoomooMarketDataProvider
        ->
same strategy + deterministic risk manager
        ->
MoomooExecutionGateway
        ->
order/fill monitoring + broker reconciliation
```

The LLM must never bypass the deterministic risk manager or directly send unrestricted broker orders.

Detailed transfer checklist:

```text
docs/experiment/moomoo-live-transfer.md
```

Exact simulated P/L is **not** assumed to transfer 1:1 to real money because live trading adds spreads, latency, queue position, partial fills, rejects, halts, short availability, borrow costs, fees and market impact.

## Validation rule for Day 1

A day counts only if the Azure runtime actually executes market cycles. A legitimate zero-trade day is possible, but `decision_log.jsonl` must prove that the LLM evaluated eligible setups. A day with no decision records because the runtime failed does **not** count.

## Important limitations

- public/delayed market-data limitations
- 5-minute bars rather than tick/order-book data
- simplified slippage/fill assumptions
- no realistic partial-fill model yet
- no realistic short borrow/locate fee model yet
- no live broker reconciliation yet
- data-provider failures are possible
- LLM outputs can be wrong

## License

Underlying LLM-Investor-Behavior-Benchmark code remains under its original MIT License.

Original copyright:

**Copyright (c) 2025 Nathan Smith**

---

**Status:** Azure migration ready for user resource setup  
**Mode:** Simulation only  
**Starting capital:** $1,000 USD  
**Style:** Autonomous intraday scalping  
**Directions:** Long + synthetic unleveraged short  
**Benchmark objective:** Beat S&P 500 and Nasdaq-100 over six months  
**Duration:** 6 months
