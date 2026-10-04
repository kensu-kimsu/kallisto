# Final V1 Methodology - LLM Scalping

## Objective

Final V1 is a six-month, simulation-only intraday scalping experiment with one $1,000 USD portfolio.

The research objective is to seek positive simulated capital growth and attempt to outperform both the S&P 500 and Nasdaq-100. Neither profitability nor outperformance is assumed in advance.

## Candidate generation

Each NYSE session starts from two stock universes:

- major-exchange U.S.-listed microcaps below $300 million market cap
- approximately the top 20 distinct Nasdaq-listed Titan companies by market capitalization

The system examines premarket 5-minute data and ranks securities by accumulated premarket volume. Up to five available leaders from each universe are retained for the intraday candidate set.

## Decision cycles

GitHub Actions runs repeatedly during U.S. market hours. The Python workflow checks the NYSE calendar and New York local time before any LLM call.

For each valid decision cycle, candidates are refreshed with current 5-minute technical features and the cached daily fundamental context. GPT-5.6 Luna may propose a LONG or synthetic SHORT hypothesis.

The model does not control unrestricted sizing. Deterministic code decides whether sufficient risk capacity exists and calculates the hypothetical whole-share position size and stop.

## Analysis features

Technical features include:

- premarket volume and gap
- VWAP
- EMA 9 / EMA 20
- RSI(14)
- MACD / signal
- ATR
- relative intraday volume
- opening-range high/low and breakout/breakdown

Fundamental/context fields may include market cap, float, beta, valuation, margins, growth, ROE, leverage, and short interest when the data source provides them.

These are public, widely used analysis concepts. The experiment does not claim proprietary Wall Street signals or private market data.

## Intraday-only rule

New entries stop at 15:15 ET. All remaining positions are force-closed at approximately 15:55 ET. No position is intentionally held overnight.

## Long and short treatment

Long and synthetic short hypotheses are allowed. Synthetic shorts reserve their full entry notional as collateral, and short-sale proceeds are not added to buying power. This keeps the simulated portfolio effectively unleveraged.

The simulation does not model real-world short locates, borrow fees, margin requirements, or broker-specific shortability.

## Benchmark comparison

Daily portfolio value is compared with normalized $1,000 series for:

- S&P 500 (`^GSPC`)
- Nasdaq-100 (`^NDX`)

## Automation

No manual approval is required. GitHub Actions compile-checks the final V1 modules, runs the simulation cycle, and commits changed experiment state and reports back to the repository.

## Attribution

This repository remains based on and inspired by Nathan Smith / LuckyOne7777's LLM-Investor-Behavior-Benchmark and LLM-Trading-Lab projects. The original MIT license and attribution are retained.
