# LLM Trading Experiment

A six-month simulated trading experiment comparing two AI-managed equity strategies:

- **Microcap Growth**
- **Nasdaq Titan Growth**

The experiment is operated from **Australia** and is designed around the time-zone difference between Australia and the U.S. stock market.

The objective is to observe how an LLM-driven portfolio-management process behaves over time when given a fixed capital base, a defined investment universe, strict execution rules, automated accounting, benchmark comparisons, and minimal human intervention.

> **Simulation only. No live-money trading is performed by this repository.**

---

## Original Project and Attribution

This experiment is built on and inspired by the original work of **Nathan Smith / LuckyOne7777**.

Primary source projects:

- [LLM-Investor-Behavior-Benchmark](https://github.com/LuckyOne7777/LLM-Investor-Behavior-Benchmark)
- [LLM-Trading-Lab](https://github.com/LuckyOne7777/LLM-Trading-Lab)

The original repositories provided the foundation for:

- the LIBB framework
- persistent portfolio state
- simulated order processing
- research workflow
- performance metrics
- overall experiment structure

This repository extends that foundation with a personal experiment layer including:

- two custom stock universes
- Australian time-zone handling
- automated NYSE session detection
- duplicate-session protection
- U.S. holiday/weekend protection
- GPT-5.6 model routing
- manual approval checkpoints
- hard order validation
- OpenAI API cost tracking
- custom performance reporting
- S&P 500 and Nasdaq-100 benchmarks
- drawdown tracking
- four-week mechanical performance projections
- GitHub-based documentation

The original LIBB framework remains credited to its original author.

---

# Research Question

The main research question is:

> How do two LLM-managed equity portfolios with very different investment universes behave over a six-month simulated period when the AI is allowed to make investment decisions under fixed rules and consistent execution constraints?

The two strategies are intentionally different.

One portfolio focuses on highly speculative U.S.-listed microcap equities.

The second focuses on the largest Nasdaq-listed companies by market capitalization.

Both portfolios begin with the same simulated capital.

---

# Experiment Design

## Duration

Planned duration:

**6 months**

Initial experiment period:

**September 2026 to approximately March 2027**

---

## Starting Capital

Each strategy begins independently with:

| Portfolio | Starting Capital |
|---|---:|
| Microcap Growth | $1,000 USD |
| Nasdaq Titan Growth | $1,000 USD |

The portfolios are completely separate.

Performance is also compared against:

- S&P 500
- Nasdaq-100

Both benchmarks are normalized to the same $1,000 starting value for easier comparison.

---

# Portfolio 1: Microcap Growth

The Microcap Growth portfolio represents the more speculative side of the experiment.

## Universe Rules

Eligible securities must:

- be U.S.-listed equities
- trade on a major U.S. exchange
- have a market capitalization below **$300 million**
- pass the experiment's candidate-screening rules
- be included in the current generated candidate universe

Supported exchange codes currently include:

- Nasdaq Global Select Market
- Nasdaq Global Market
- Nasdaq Capital Market
- New York Stock Exchange
- NYSE American

The candidate universe is ranked primarily by trading volume.

The workflow supplies approximately the top **50 qualifying names** to the model.

---

## Trading App Availability Limitation

This experiment is designed with future real-world executability in mind.

The trading application available to me in Australia does **not necessarily provide access to every U.S.-listed microcap security**.

Some microcap securities may be unavailable for opening new positions, restricted, or otherwise unsupported.

Because of this, the experiment contains a restriction mechanism that can exclude securities known to be unavailable through the trading application.

This restriction list is maintained separately from the AI decision process.

The current six-month study remains fully simulated.

---

# Portfolio 2: Nasdaq Titan Growth

The Nasdaq Titan Growth portfolio represents the large-cap side of the experiment.

## Universe Rules

The universe consists of approximately the:

**Top 20 distinct Nasdaq-listed equities by market capitalization**

Eligible exchanges include:

- Nasdaq Global Select Market
- Nasdaq Global Market
- Nasdaq Capital Market

Duplicate company share classes are filtered where possible so the candidate universe represents distinct companies rather than multiple listings of the same company.

The universe may include foreign-domiciled companies if they are Nasdaq-listed and otherwise meet the experiment rules.

---

# AI Model Schedule

The experiment uses two OpenAI models.

## Monday-Thursday NYSE Sessions

Regular completed NYSE sessions use:

**GPT-5.6 Luna**

These runs are intended for normal daily portfolio-management decisions.

## Friday NYSE Session

The completed Friday session uses:

**GPT-5.6 Terra**

Friday is treated as the deeper weekly research and portfolio-review cycle.

The weekly model may perform broader portfolio assessment and rebalancing.

---

# Australian Time-Zone Design

This experiment is operated from **Melbourne, Australia**.

The U.S. stock market operates overnight relative to Australian daytime hours.

I do not stay awake to monitor the U.S. market session.

Instead, the workflow is based on the:

> **Latest fully completed NYSE trading session**

The system tracks both:

- `Australia/Melbourne`
- `America/New_York`

The normal operating pattern is:

```text
U.S. market trades overnight
        ->
NYSE session closes
        ->
Australian daytime
        ->
Workflow detects latest completed session
        ->
Previous simulated orders are processed
        ->
Portfolio is updated
        ->
AI generates next-session orders
        ->
Human approval
        ->
Orders wait for the next U.S. session
```

This removes the need to monitor U.S. markets overnight.

---

# NYSE Session Protection

The workflow includes safeguards designed to prevent duplicate API calls and preserve chronological experiment integrity.

Before any OpenAI request is made, the system checks:

- whether the latest date is a valid NYSE session
- whether that session has already been processed
- whether both portfolios are synchronized
- whether the next expected NYSE session exists
- whether a trading session was accidentally skipped

If the latest completed session has already been processed, the program exits before calling OpenAI.

Example:

```text
NO NEW NYSE SESSION.

Workflow stopped BEFORE OpenAI.
API cost for this attempt: $0.00
```

This also protects against:

- weekends
- U.S. stock-market holidays
- accidental duplicate runs

---

# Trading Rules

## Allowed

- long-only positions
- full shares
- LIMIT orders
- DAY time-in-force
- regular trading hours
- simulated stop losses
- holding cash

## Not Allowed

- short selling
- margin
- leverage
- options
- fractional shares
- extended-hours execution

---

# Order Validation

The AI is responsible for generating the investment decision.

Every proposed order must pass programmatic validation before entering the simulation.

The validator checks:

- ticker belongs to the permitted universe
- action type is allowed
- shares are whole numbers
- shares are greater than zero
- order type is LIMIT
- time-in-force is DAY
- order date matches the intended NYSE session
- limit price is positive
- confidence is between 0 and 1
- buy orders have a valid stop loss
- buy stop loss is below the buy limit
- available simulated cash is sufficient
- sell quantity does not exceed owned shares
- update instructions only target existing positions

If an order fails validation, the recommendation is rejected.

The program does **not** silently rewrite or modify the AI's investment decision.

---

# Human Intervention Policy

The AI is intended to function as the portfolio manager.

My role is primarily:

- experiment operator
- reviewer
- observer

After validation, the program displays the recommendation and asks:

```text
Approve these AI orders for the SIMULATED portfolio? [Y/N]:
```

During the planned six-month study, I intend not to selectively override valid AI investment decisions.

A valid recommendation is approved into the simulation.

If a recommendation violates the experiment's hard rules, it is rejected by the program rather than manually rewritten.

This helps preserve the integrity of the experiment.

---

# Simulated Execution

An approved order becomes a:

**pending simulated order**

A pending order is not automatically treated as a filled position.

On the following applicable NYSE session, the LIBB execution engine checks whether the order could have executed using market data for that trading day.

The simulator then determines whether the limit order filled.

If an order fills, the system automatically updates:

- cash
- shares owned
- portfolio positions
- trade history
- position history
- portfolio equity
- gains and losses
- performance metrics

If the order does not satisfy its simulated execution conditions, it is not treated as a successful trade.

---

# Portfolio Accounting

All portfolio calculations are automated.

The system tracks:

- starting capital
- current cash
- position quantities
- position values
- total portfolio equity
- trade execution
- daily return
- cumulative return
- drawdown
- historical portfolio value

No manual portfolio arithmetic is required.

---

# Benchmarks

The experiment compares both AI portfolios against:

## S&P 500

Ticker used for data:

`^GSPC`

## Nasdaq-100

Ticker used for data:

`^NDX`

Benchmark series are normalized to the same $1,000 starting capital.

This allows direct comparison between:

- Microcap Growth
- Nasdaq Titan Growth
- S&P 500
- Nasdaq-100

---

# Performance Reporting

Reports are automatically regenerated after successful workflow runs.

Current reporting includes:

- daily portfolio history
- weekly performance
- monthly performance
- cumulative equity
- drawdown
- performance summary
- benchmark comparison

The primary chart is:

```text
user_side/personal_experiment/reporting/output/equity_comparison.png
```

It shows the simulated value of the original $1,000 allocation over time.

The chart includes:

- Microcap Growth
- Nasdaq Titan Growth
- S&P 500
- Nasdaq-100
- final return annotations
- maximum drawdown annotations
- starting-capital reference

---

# Four-Week Mechanical Projection

The experiment also generates a four-week projection once enough weekly data exists.

The projection uses recent weekly performance and mechanically compounds the recent average weekly return forward.

This is **not a market forecast**.

It is a simple trend extrapolation answering:

> If the recent average weekly performance continued unchanged, what would the portfolio path look like over the next four weeks?

Actual historical performance and projected values are kept visually separate.

---

# API Cost Tracking

OpenAI API usage is tracked separately from portfolio performance.

Every model call records:

- run date
- portfolio
- model
- input tokens
- output tokens
- total tokens
- estimated input cost
- estimated output cost
- estimated total call cost
- cumulative experiment cost

The log is stored at:

```text
user_side/personal_experiment/cost_tracking/api_cost_log.csv
```

This allows the experiment to evaluate not only investment performance, but also the computational cost required to operate the AI strategy.

---

# Cost-Preservation Safeguards

OpenAI is not called when:

- the latest NYSE session has already been processed
- the market was closed for a holiday
- it is a weekend with no new completed session
- portfolios are out of synchronization
- a required trading session appears to have been skipped

Saved recommendations can also be reviewed locally without an API call.

---

# Viewing Current Recommendations

Current approved pending simulated orders can be viewed with:

```powershell
python -m user_side.personal_experiment.show_recommendations
```

This viewer:

- reads local files only
- shows company names
- shows ticker
- shows action
- shows number of shares
- shows limit price
- shows stop loss
- shows confidence
- shows rationale
- calculates maximum order commitment

It makes:

**No OpenAI API request.**

---

# Daily Operating Procedure

From PowerShell:

```powershell
cd D:\LLM-Trading-Project\LLM-Investor-Behavior-Benchmark
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the experiment:

```powershell
python -m user_side.personal_experiment.simulation_workflow
```

If there is no new NYSE session, the workflow exits before making an API call.

If there is a new session:

1. previous orders are processed
2. portfolios are updated
3. candidate universes are generated
4. OpenAI research is performed
5. API cost is logged
6. orders are validated
7. recommendations are displayed
8. manual approval is requested
9. approved orders become pending simulated orders
10. reports are refreshed

---

# Viewing the Comparison Chart

The current comparison chart can be opened at any time with:

```powershell
Start-Process .\user_side\personal_experiment\reporting\output\equity_comparison.png
```

To regenerate reports first:

```powershell
python -m user_side.personal_experiment.reporting.refresh_reports
```

Then open the chart:

```powershell
Start-Process .\user_side\personal_experiment\reporting\output\equity_comparison.png
```

Refreshing reports does not make an OpenAI API call.

---

# Repository Structure

```text
user_side/
|
|-- personal_experiment/
|   |
|   |-- broker/
|   |   `-- simulated brokerage restrictions
|   |
|   |-- cost_tracking/
|   |   `-- API usage and cost tracking
|   |
|   |-- market_data/
|   |   |-- microcap screener
|   |   |-- Nasdaq Titan screener
|   |   `-- prompt universe formatting
|   |
|   |-- prompts/
|   |   `-- personal AI research prompts
|   |
|   |-- reporting/
|   |   |-- performance tracker
|   |   |-- periodic reports
|   |   |-- four-week projection
|   |   `-- output/
|   |
|   |-- market_clock.py
|   |-- simulation_workflow.py
|   `-- show_recommendations.py
|
`-- runs/
    `-- personal_v1/
        |-- microcap/
        `-- titans/
```

---

# GitHub as the Main Documentation Source

GitHub is intended to act as the primary documentation source for this study.

Planned documentation structure:

```text
docs/
|-- experiment/
|   |-- methodology.md
|   |-- portfolio-rules.md
|   |-- model-policy.md
|   |-- execution-model.md
|   |-- risk-controls.md
|   |-- reporting.md
|   `-- api-costs.md
|
|-- journal/
|   |-- weekly-log.md
|   `-- monthly-summary.md
|
`-- results/
    |-- equity_comparison.png
    |-- drawdown_comparison.png
    `-- four_week_projection.png
```

The repository will be updated throughout the six-month experiment.

---

# Weekly Documentation

A weekly summary should include:

- week number
- starting portfolio equity
- ending portfolio equity
- weekly return
- cumulative return
- benchmark returns
- trades executed
- orders that did not fill
- maximum drawdown
- weekly API cost
- cumulative API cost
- notable AI decisions
- validation failures
- confirmation of whether any human override occurred

---

# Reproducibility

The project uses persistent run directories so that each portfolio maintains independent state.

Important experiment state includes:

- cash
- portfolio positions
- pending trades
- trade history
- position history
- portfolio history
- research output
- prompts
- performance metrics

The intent is to preserve enough information to reconstruct how each portfolio evolved throughout the study.

---

# Limitations

## Simulation vs Live Trading

All trading is simulated.

Real-world execution may differ because of:

- bid/ask spreads
- latency
- order priority
- partial fills
- exchange conditions
- broker restrictions
- trading halts
- liquidity constraints

## Microcap Availability

Not every microcap security available in market-data feeds is necessarily tradable through the trading application available to me in Australia.

## Market Data

Market information comes from third-party data sources and may contain delays, gaps, or inconsistencies.

## AI Output

LLM-generated research may contain incorrect assumptions or reasoning.

Programmatic validation reduces some structural errors but cannot guarantee that an investment decision is economically sound.

## Projections

Four-week projections are mechanical extrapolations of historical experiment performance and should not be interpreted as expected returns.

## Small Starting Capital

Each portfolio begins with only $1,000, meaning whole-share restrictions may materially affect allocation decisions.

---

# Security

API credentials are never intentionally stored inside this repository.

The OpenAI API key is supplied through the local operating-system environment:

```text
OPENAI_API_KEY
```

Secret files, virtual environments, environment-variable files, and credential files are excluded through `.gitignore`.

---

# Disclaimer

This repository documents a personal research and software experiment.

It is not financial advice, investment advice, or a recommendation to buy or sell any security.

All portfolio activity described here is simulated.

Past simulated performance does not imply future performance.

---

# License and Original Work

The underlying **LLM-Investor-Behavior-Benchmark** project is distributed under the MIT License.

Original copyright:

**Copyright (c) 2025 Nathan Smith**

The original MIT license and copyright notice are retained in this repository.

For the original implementation and documentation, visit:

- [LLM-Investor-Behavior-Benchmark](https://github.com/LuckyOne7777/LLM-Investor-Behavior-Benchmark)
- [LLM-Trading-Lab](https://github.com/LuckyOne7777/LLM-Trading-Lab)

---

# Status

**Experiment setup:** Active  
**Mode:** Simulation only  
**Location:** Australia  
**Starting capital:** $1,000 per portfolio  
**Strategies:** Microcap Growth vs Nasdaq Titan Growth  
**Benchmarks:** S&P 500 and Nasdaq-100  
**Planned duration:** 6 months
