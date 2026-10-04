# Final V1 - Autonomous LLM Scalping Experiment

A six-month **simulation-only** experiment testing whether an LLM-guided intraday scalping process can grow a $1,000 USD portfolio and outperform both the S&P 500 and Nasdaq-100.

> This repository does not place live orders, connect to Moomoo, or move real money. All entries, exits, long positions, and short positions are hypothetical research simulations.

## Original project and attribution

This project is built on and inspired by the work of **Nathan Smith / LuckyOne7777**:

- [LLM-Investor-Behavior-Benchmark](https://github.com/LuckyOne7777/LLM-Investor-Behavior-Benchmark)
- [LLM-Trading-Lab](https://github.com/LuckyOne7777/LLM-Trading-Lab)

The original MIT license and copyright notice are retained.

## Final V1 research question

> Can a fully autonomous LLM-guided intraday strategy, constrained by deterministic risk controls and restricted to liquid premarket leaders, produce positive simulated capital growth and outperform the S&P 500 and Nasdaq-100 over six months?

Outperformance and positive returns are **research objectives, not guaranteed outcomes**.

## Starting capital

The final V1 uses **one combined simulated portfolio**:

- Starting capital: **$1,000 USD**
- No external deposits
- No leverage
- No options
- Whole shares only
- No overnight positions

## Stock universe

Every NYSE trading day, the experiment starts from two eligible universes:

### Microcaps

- U.S.-listed equities on major U.S. exchanges
- Market capitalization below $300 million
- Existing broker-restriction filtering remains available

### Nasdaq Titans

- Approximately the top 20 distinct Nasdaq-listed companies by market capitalization
- Duplicate company share classes filtered where possible

The workflow then ranks names by **premarket trading volume** and keeps the top five available names from each universe for the intraday candidate list.

## Intraday decision process

GitHub Actions runs during U.S. regular-market hours. The Python code uses `America/New_York` time and exits before calling OpenAI when the NYSE is closed or the run is outside the trading window.

During an eligible cycle:

```text
Premarket volume leaders
        ->
5-minute intraday market data
        ->
technical + fundamental feature set
        ->
GPT-5.6 Luna decision
        ->
deterministic risk engine
        ->
hypothetical LONG / SHORT position
        ->
5-minute stop / target monitoring
        ->
forced flat before market close
        ->
GitHub state + daily reporting
```

No manual approval is required.

## Analysis inputs

The experiment uses a combination of widely used public market-analysis concepts. It does **not** claim access to proprietary Wall Street models, hidden order flow, Level 2 feeds, or private research.

Technical inputs include:

- premarket volume
- premarket price change
- VWAP
- EMA 9 and EMA 20
- RSI(14)
- MACD and MACD signal
- ATR-based volatility
- relative intraday volume
- opening-range high/low
- opening-range breakout/breakdown

Fundamental/context fields may include, when available:

- market capitalization
- float shares
- average volume
- beta
- P/E and price-to-book
- profit margin
- revenue growth
- earnings growth
- return on equity
- debt-to-equity
- short interest as a percentage of float

Fundamentals are context for an intraday decision; they are not treated as a substitute for price/volume confirmation.

## Long and short simulation

The LLM may propose either:

- `LONG`
- `SHORT`

Shorting is **synthetic and simulation-only**. The simulator reserves the short position's notional capital as collateral and does not add short-sale proceeds to buying power. This keeps simulated gross exposure effectively unleveraged.

Actual broker short availability, borrow fees, locate requirements, margin requirements, and regulatory restrictions are **not modeled**. Moomoo remains the intended real-world reference broker, but this repository has no Moomoo API connection.

## Profit target

Every accepted trade must target at least:

**1.5% from the simulated entry price**

The deterministic engine may set a larger target when the volatility-based stop requires a higher reward-to-risk ratio.

A 1.5% target is a target, not an expected or guaranteed realized return.

## Deterministic risk management

The LLM chooses the ticker, direction, target percentage, confidence, and rationale. It does **not** choose unrestricted position size.

Hard limits:

| Control | Final V1 rule |
|---|---:|
| Risk per new trade | 0.5% of current equity |
| Maximum combined open stop risk | 1.5% of equity |
| Maximum gross exposure | 90% of equity |
| Maximum single-position notional | 25% of equity |
| Minimum uncommitted cash reserve | 10% of equity |
| Daily loss circuit breaker | 2% from session-start equity |
| Portfolio drawdown pause | 10% from high-water mark |
| Minimum LLM confidence | 0.60 |

ATR-based stop ranges:

- Microcap: approximately 1.0% to 2.5%
- Titan: approximately 0.5% to 1.25%

Minimum reward-to-risk floor: **1.5:1**.

There is **no fixed daily trade-count limit**. Risk capacity, available capital, signal quality, the entry cutoff, and the daily-loss circuit breaker determine how many simulated trades can actually be opened.

## Same-day flat rule

- New entries stop at **15:15 New York time**.
- Any remaining open position is force-closed at approximately **15:55 New York time**.
- No final V1 position is intentionally carried overnight.

## Execution assumptions

Market data uses 5-minute bars. Because bar data does not reveal the exact sequence of prices inside a bar, if both a stop and target are touched in the same 5-minute bar, the simulator uses the conservative assumption that the **stop was hit first**.

Hypothetical entry slippage assumptions:

- Microcaps: 0.20%
- Titans: 0.05%

Real fills can differ materially because of spreads, halts, liquidity, latency, partial fills, borrow availability, and market impact.

## GitHub Actions automation

The workflow is stored at:

```text
.github/workflows/daily-trading-experiment.yml
```

It runs several times during the U.S. market session. Fixed UTC schedules cover both U.S. daylight-saving and standard time; the Python workflow itself decides whether the NYSE is currently in the valid experiment window.

The workflow:

1. checks out the repository
2. installs Python dependencies
3. compile-checks the final V1 modules
4. runs one simulation cycle
5. commits updated state, journals, and results back to `main` when anything changed

A concurrency lock prevents two experiment jobs from updating state at the same time.

GitHub scheduled jobs are not guaranteed to start at the exact scheduled second, so this is an **approximate intraday simulation**, not a low-latency trading system.

## Daily tracking and benchmarks

Daily state is stored under:

```text
user_side/runs/scalping_v1/
```

Key files:

```text
portfolio_state.json
decision_log.jsonl
trade_log.csv
daily_performance.csv
```

Daily performance is compared with:

- S&P 500 (`^GSPC`)
- Nasdaq-100 (`^NDX`)

Both benchmarks are normalized to a $1,000 starting value.

The comparison chart is generated as:

```text
docs/results/scalping_equity_comparison.png
```

Daily journals are written to:

```text
docs/journal/daily/
```

## Run locally

```powershell
cd D:\LLM-Trading-Project\LLM-Investor-Behavior-Benchmark
.\.venv\Scripts\Activate.ps1
python -m user_side.personal_experiment.scalping_v1
```

The same New York market-hours and NYSE-calendar guards apply locally.

## Final V1 start date

The clean final V1 baseline begins with the **2026-10-05 NYSE session** at $1,000 USD.

Earlier versions are preserved in archive branches and are not included in final V1 performance statistics.

## Important limitations

This is not a live trading system and is not evidence that the same results could be achieved with real money. Important differences include:

- delayed/incomplete public market data
- GitHub Actions scheduling latency
- 5-minute bars rather than tick data
- simplified slippage
- no commissions or regulatory fees unless later added
- no realistic short-locate or borrow-cost model
- no order-book data
- no market-impact model
- possible data-provider gaps
- LLM reasoning errors

The experiment should be judged by its recorded six-month results, including losses and failure modes, rather than by an assumed expectation of profitability.

## License

Underlying LLM-Investor-Behavior-Benchmark code remains under its original MIT License.

Original copyright:

**Copyright (c) 2025 Nathan Smith**

---

**Status:** Final V1 implementation  
**Mode:** Simulation only  
**Starting capital:** $1,000 USD  
**Style:** Intraday scalping  
**Directions:** Long + synthetic unleveraged short  
**Benchmark objective:** S&P 500 and Nasdaq-100  
**Duration:** 6 months
