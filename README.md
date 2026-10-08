# Final V1 - Autonomous LLM Scalping Experiment

A six-month **simulation-only** research experiment testing whether an autonomous LLM-guided intraday scalping process can grow a $1,000 USD portfolio and outperform both the S&P 500 and Nasdaq-100.

> This repository does not place live orders or move real money. Moomoo is the intended future reference broker, but Final V1 is a simulation.

## Original project and attribution

This project is built on and inspired by **Nathan Smith / LuckyOne7777**:

- [LLM-Investor-Behavior-Benchmark](https://github.com/LuckyOne7777/LLM-Investor-Behavior-Benchmark)
- [LLM-Trading-Lab](https://github.com/LuckyOne7777/LLM-Trading-Lab)

The original MIT license and copyright notice are retained.

## Research objective

> Can a fully autonomous LLM-guided intraday strategy, constrained by deterministic risk controls and focused on premarket volume leaders, achieve positive simulated capital growth and outperform the S&P 500 and Nasdaq-100 over six months?

Positive returns and benchmark outperformance are objectives, not guarantees.

## Final V1 baseline

- Starting capital: **$1,000 USD**
- Clean Final V1 start: **2026-10-08 NYSE session**
- No external deposits
- No leverage
- No options
- Whole shares only
- LONG and synthetic 1x SHORT trades allowed
- No overnight positions
- No manual trade approval

The Oct 7 run was an infrastructure/prelaunch test and is excluded from the clean Final V1 performance series.

## Trading universe

Each NYSE trading day begins with two source universes.

### Microcaps

- major U.S. exchanges
- market capitalization below $300 million
- approximately top **8** eligible names by premarket volume

### Nasdaq Titans

- approximately the top 20 distinct Nasdaq-listed companies by market capitalization
- approximately top **8** available names by premarket volume

The two lists are combined into the intraday candidate set.

## Intraday architecture

```text
Premarket volume scan
        ->
5-minute market data
        ->
technical + fundamental context
        ->
GPT-5.6 Luna decision every ~15 minutes
        ->
deterministic risk engine
        ->
hypothetical LONG / SHORT entry
        ->
5-minute position monitoring
        ->
stop / target / time-stop / EOD exit
        ->
GitHub checkpoint + reporting
```

GitHub Actions no longer needs to wake the strategy for every decision. Two persistent session runners are launched each market day and the Python process itself cycles every five minutes.

## Professional scalping inputs

Final V1 uses public, reproducible market-analysis concepts rather than claiming access to proprietary institutional models.

Technical inputs include:

- premarket volume and premarket change
- VWAP
- EMA 9 / EMA 20
- RSI(14)
- MACD and signal line
- ATR-based volatility
- relative intraday volume
- opening-range high/low
- opening-range breakout/breakdown

The LLM is prompted to look for evidence-backed intraday patterns such as:

- VWAP reclaim/rejection
- opening-range breakout/breakdown
- EMA 9/20 continuation after pullback
- failed breakout/breakdown reversal
- confirmed premarket-leader continuation

Fundamental context may include market cap, float, average volume, beta, valuation, profitability, growth, leverage, return on equity, and short interest when available.

The LLM may only use supplied data and must not invent catalysts, Level 2 data, hidden order flow, proprietary signals, or undisclosed news.

## Intraday timing

- monitoring begins around **09:25 ET**
- first new entries are allowed after **09:40 ET**
- LLM decision cadence: approximately **15 minutes**
- position monitoring cadence: approximately **5 minutes**
- no new entries after **15:30 ET**
- all remaining positions are forced flat around **15:55 ET**

No position is intentionally carried overnight.

## Risk management

The LLM proposes ticker, direction, target, confidence, and rationale. Deterministic code controls position size, stop distance, exposure, and portfolio-level safety.

Core protections include:

- per-trade risk budgeting
- combined open-risk limit
- maximum gross exposure
- maximum single-position notional
- minimum cash reserve
- daily loss circuit breaker
- portfolio drawdown pause
- maximum simultaneous positions
- volatility-based stops
- minimum reward-to-risk requirement
- breakeven-style protection after favorable movement
- time-stop exit for stale scalps
- forced end-of-day flat rule

Synthetic shorts reserve full notional capital; short-sale proceeds do not create extra buying power.

## Execution assumptions

Final V1 uses 5-minute public market bars. It is therefore an approximate intraday simulation, not a low-latency execution system.

The simulator includes conservative slippage assumptions and treats ambiguous same-bar stop/target touches conservatively.

Real execution can differ because of spreads, latency, liquidity, partial fills, halts, borrow availability, market impact, and broker rules.

## GitHub Actions automation

Workflow:

```text
.github/workflows/daily-trading-experiment.yml
```

Two persistent scheduled jobs cover the NYSE session:

```text
morning segment
09:25 ET -> 12:25 ET

Afternoon segment
12:25 ET -> approximately 16:05 ET
```

Each persistent process cycles every five minutes and checkpoints state back to GitHub. A concurrency lock prevents two runners from updating the trading state at the same time.

GitHub schedule launch time is still best-effort; the long-running process is designed so a delayed cron launch does not determine every individual trading decision.

## Experiment data

Final V1 state is stored under:

```text
user_side/runs/scalping_v1/
```

Important files:

```text
portfolio_state.json
decision_log.jsonl
trade_log.csv
daily_performance.csv
api_costs.csv
```

## Performance benchmarks

Performance is compared against:

- S&P 500 (`^GSPC`)
- Nasdaq-100 (`^NDX`)

All three series are normalized to the same $1,000 baseline.

Generated chart:

```text
docs/results/scalping_equity_comparison.png
```

## OpenAI API cost tracking

Every paid LLM decision records input, cached-input and output token usage plus an estimated USD cost in:

```text
user_side/runs/scalping_v1/api_costs.csv
```

The table below is automatically refreshed after every recorded OpenAI decision call.

Averages are calculated over **active periods containing at least one API call**. A partially completed trading day/week/month will therefore make the running average provisional.

<!-- API_COST_SUMMARY_START -->
| Cost period | API cost (USD) | API calls | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| Average daily | $0.0000 | 0.0 | 0 | 0 |
| Average weekly | $0.0000 | 0.0 | 0 | 0 |
| Average monthly | $0.0000 | 0.0 | 0 | 0 |
| **Total actual** | **$0.0000** | **0** | **0** | **0** |
<!-- API_COST_SUMMARY_END -->

Current cost calculations use the GPT-5.6 Luna pricing snapshot configured in `scalping_api_costs.py`. Repository cost figures are calculated estimates from API-reported token usage; OpenAI billing remains the source of truth.

## Daily reporting

At the end of each NYSE session the experiment records:

- starting equity
- ending equity
- daily return
- cumulative return
- number of closed trades
- wins / losses
- win rate
- normalized S&P 500 value
- normalized Nasdaq-100 value

Daily journals are written to:

```text
docs/journal/daily/
```

## Path toward a future personal AI trading agent

Final V1 tests the strategy, automation, and risk architecture first. A future live system should retain the separation:

```text
MarketDataProvider
        ->
StrategyEngine / LLM
        ->
Deterministic RiskManager
        ->
Broker adapter
        ->
ExecutionMonitor
        ->
Broker/account reconciliation
```

The LLM should never be able to bypass the deterministic risk layer and send unrestricted broker orders.

Before live deployment, the system would still need:

1. real-time broker quotes
2. real bid/ask and execution-quality checks
3. order acknowledgements, partial fills, rejects, cancels and replacements
4. real short availability and borrow costs
5. verified Moomoo API permissions and order types
6. real buying power and settlement handling
7. trading-halt/volatility-interruption handling
8. reconnect and retry protection
9. broker/account reconciliation
10. independent kill switches and daily-loss controls
11. secure credential management
12. monitoring and alerts

A safer transfer path is:

```text
Final V1 public-data simulation
        ->
real-time broker market data + simulation
        ->
Moomoo API paper trading
        ->
shadow mode
        ->
small-capital live pilot with hard kill switch
        ->
larger deployment only if live evidence supports it
```

## Important limitations

- public/delayed market-data limitations
- 5-minute bars rather than tick/order-book data
- GitHub-hosted infrastructure is not exchange-grade
- simplified slippage/fill assumptions
- no realistic partial-fill model
- no realistic short borrow/locate fee model
- no live broker reconciliation
- data-provider failures are possible
- LLM outputs can be wrong
- stops reduce planned risk but cannot guarantee real execution price

The experiment should be judged by the complete six-month record, including losses, no-trade periods, rejected decisions, data failures, API costs, and operational failures.

## License

Underlying LLM-Investor-Behavior-Benchmark code remains under its original MIT License.

Original copyright:

**Copyright (c) 2025 Nathan Smith**

---

**Status:** Final V1 active  
**Mode:** Simulation only  
**Starting capital:** $1,000 USD  
**Style:** Autonomous intraday scalping  
**Directions:** Long + synthetic unleveraged short  
**Benchmark objective:** Beat S&P 500 and Nasdaq-100 over six months  
**Duration:** 6 months
