# Final V1 - Autonomous LLM Scalping Experiment

A six-month **simulation-only** research experiment testing whether an LLM-guided intraday scalping process can grow a $1,000 USD portfolio and outperform both the S&P 500 and Nasdaq-100.

> This repository does not place live orders, connect to Moomoo, or move real money. All entries, exits, long positions, and short positions are hypothetical research simulations.

## Original project and attribution

This project is built on and inspired by the work of **Nathan Smith / LuckyOne7777**:

- [LLM-Investor-Behavior-Benchmark](https://github.com/LuckyOne7777/LLM-Investor-Behavior-Benchmark)
- [LLM-Trading-Lab](https://github.com/LuckyOne7777/LLM-Trading-Lab)

The original MIT license and copyright notice are retained.

## Research question

> Can a fully autonomous LLM-guided intraday strategy, constrained by deterministic risk controls and restricted to liquid premarket leaders, produce positive simulated capital growth and outperform the S&P 500 and Nasdaq-100 over six months?

Positive returns and benchmark outperformance are **research objectives, not guaranteed outcomes**.

## Starting capital

Final V1 uses one combined simulated portfolio:

- Starting capital: **$1,000 USD**
- No external deposits
- No leverage
- No options
- Whole shares only
- No overnight positions
- Long and synthetic short trades allowed

## Stock universe

Each trading day begins with two source universes.

### Microcaps

- U.S.-listed equities on major U.S. exchanges
- Market capitalization below **$300 million**
- Broker-restriction filtering remains available

### Nasdaq Titans

- Approximately the top 20 distinct Nasdaq-listed companies by market capitalization
- Duplicate share classes filtered where possible

The workflow ranks eligible names by **premarket trading volume** and keeps approximately the top five available names from each universe for the intraday candidate list.

## Intraday decision process

GitHub Actions runs during U.S. market hours. Python uses `America/New_York` time and exits before calling OpenAI when the NYSE is closed or outside the experiment window.

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

Final V1 uses widely known public trading indicators rather than claiming access to proprietary institutional models.

Technical inputs include:

- premarket volume
- premarket price change
- VWAP
- EMA 9 and EMA 20
- RSI(14)
- MACD and signal line
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

Fundamentals provide context for the intraday decision but do not replace price and volume confirmation.

## Long and short simulation

The LLM may propose either `LONG` or `SHORT`.

Shorting is synthetic and simulation-only. The simulator reserves the position's full notional value as collateral and does not add short-sale proceeds to buying power, keeping simulated gross exposure effectively unleveraged.

Real short availability, locate requirements, borrow fees, margin rules, and regulatory restrictions are not yet modeled.

Moomoo remains the intended real-world reference broker, but Final V1 has no live Moomoo API connection.

## Profit target

Every accepted trade must target at least **1.5% from simulated entry**.

The deterministic engine may require a larger target when the stop distance would otherwise violate the minimum reward-to-risk requirement.

A target is not a guaranteed realized return.

## Deterministic risk management

The LLM chooses the ticker, direction, target percentage, confidence, and rationale. It does **not** have unrestricted control of position size or portfolio risk.

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
| Minimum reward-to-risk | 1.5:1 |

ATR-based stop ranges:

- Microcap: approximately 1.0% to 2.5%
- Titan: approximately 0.5% to 1.25%

There is **no fixed daily trade-count limit**. Risk capacity, available capital, signal quality, the entry cutoff, and the daily-loss circuit breaker determine how many simulated trades can be opened.

## Same-day flat rule

- New entries stop at **15:15 New York time**.
- Remaining positions are force-closed at approximately **15:55 New York time**.
- No Final V1 position is intentionally carried overnight.

## Execution assumptions

Market data uses 5-minute bars. If both stop and target appear to be touched inside the same bar, the simulator conservatively assumes the **stop was hit first**.

Hypothetical entry slippage assumptions:

- Microcaps: 0.20%
- Titans: 0.05%

Real execution can differ because of spreads, latency, partial fills, liquidity, halts, borrow availability, and market impact.

## GitHub Actions automation

Workflow:

```text
.github/workflows/daily-trading-experiment.yml
```

It runs repeatedly during the U.S. session, compile-checks Final V1 modules, executes one simulation cycle, and commits updated state/results back to `main` when anything changes.

A concurrency lock prevents overlapping runs from updating state simultaneously.

GitHub scheduled jobs are not guaranteed to launch at an exact second, so Final V1 is an **approximate intraday simulation**, not a low-latency execution system.

## Daily tracking and benchmarks

State is stored under:

```text
user_side/runs/scalping_v1/
```

Important files:

```text
portfolio_state.json
decision_log.jsonl
trade_log.csv
daily_performance.csv
```

Performance is compared against:

- S&P 500 (`^GSPC`)
- Nasdaq-100 (`^NDX`)

All series are normalized to the same $1,000 starting value.

Generated comparison chart:

```text
docs/results/scalping_equity_comparison.png
```

### Current recorded performance

The first completed daily performance row currently recorded is **2026-10-07**.

| Series | Normalized value | Return from $1,000 baseline |
|---|---:|---:|
| LLM Scalper | $1,000.00 | 0.00% |
| S&P 500 | $996.57 | -0.34% |
| Nasdaq-100 | $996.04 | -0.40% |

No simulated trades were completed in that recorded session, so the LLM portfolio remained at $1,000.

## Path from Final V1 to a future personal AI trading agent

Final V1 is intended to test the **decision and risk architecture** first. A live system would require a separate production-grade execution layer.

The transferable architecture is:

```text
Market data
    ->
Candidate selection
    ->
Technical/fundamental feature engine
    ->
LLM decision layer
    ->
Deterministic risk manager
    ->
Execution policy
    ->
Broker adapter
    ->
Broker reconciliation + monitoring
```

The LLM should never directly bypass the risk engine and send unrestricted broker orders.

### Capabilities still required before live trading

1. **Real-time broker quotes** - replace delayed/public quotes with broker-grade streaming market data.
2. **Bid/ask spread and realistic slippage** - use live bid/ask and execution-quality checks instead of fixed assumptions.
3. **Order lifecycle handling** - support acknowledgements, partial fills, rejects, cancellations, and replacements.
4. **Real short availability and borrow costs** - verify borrow/locate availability and fees before any short order.
5. **Moomoo API permissions and supported order types** - confirm account permissions and exact API capabilities.
6. **Buying power and settlement rules** - read the broker account as the source of truth.
7. **Trading halts and volatility interruptions** - prevent entry or react safely when trading is halted or interrupted.
8. **Reconnect and retry logic** - recover safely from network/API failures without accidentally duplicating orders.
9. **Broker/account reconciliation** - compare local state against broker positions, cash, and open orders every cycle.
10. **Independent kill switches** - stop trading on daily loss, excessive drawdown, stale data, reconciliation mismatch, or repeated broker errors.
11. **Secure credential handling** - keep tokens and credentials outside source control, using secrets management.
12. **Monitoring and alerts** - notify the operator when data, broker connectivity, execution, or state becomes abnormal.

### Proposed transfer path

```text
Final V1
GitHub Actions + public-data simulation
        ->
Real-time Moomoo market data + local simulation
        ->
Moomoo API paper trading
        ->
Shadow mode: live data and live account observation, no order submission
        ->
Small-capital live pilot with hard limits and kill switch
        ->
Larger deployment only if live evidence supports it
```

A future implementation should separate interfaces such as:

```text
MarketDataProvider
StrategyEngine
RiskManager
Broker
Portfolio
ExecutionMonitor
```

That makes it possible to reuse the same strategy and risk logic across simulation, paper trading, and live trading while swapping only the market-data and broker adapters.

## Important limitations

Final V1 is not evidence that the same results could be achieved with real money. Important differences include:

- delayed/incomplete public market data
- GitHub Actions scheduling latency
- 5-minute bars instead of tick data
- simplified slippage
- no realistic order book
- no partial-fill model
- no commissions/regulatory fees unless later added
- no realistic short-locate/borrow-cost model
- no broker reconciliation
- possible data-provider gaps
- LLM reasoning errors

The experiment should be judged by its complete six-month record, including losses, no-trade days, rejected decisions, and failure modes.

## Final V1 start date

The clean Final V1 baseline is **$1,000 USD**. The first completed performance row currently present in the repository is **2026-10-07**.

Earlier designs are preserved in archive branches and are not included in Final V1 performance statistics.

## License

Underlying LLM-Investor-Behavior-Benchmark code remains under its original MIT License.

Original copyright:

**Copyright (c) 2025 Nathan Smith**

---

**Status:** Final V1 active  
**Mode:** Simulation only  
**Starting capital:** $1,000 USD  
**Style:** Intraday scalping  
**Directions:** Long + synthetic unleveraged short  
**Benchmark objective:** S&P 500 and Nasdaq-100  
**Duration:** 6 months
