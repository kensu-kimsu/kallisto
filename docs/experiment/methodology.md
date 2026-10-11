# Kallisto V1 Methodology

## Objective

Kallisto V1 is a six-month, simulation-only intraday scalping experiment with one $1,000 USD portfolio.

The research objective is to seek positive simulated capital growth, improve through bounded self-evaluation, and attempt to outperform both the S&P 500 and Nasdaq-100. Neither profitability, self-improvement nor outperformance is assumed in advance.

## Candidate generation

Each NYSE session starts from two stock universes:

- major-exchange U.S.-listed microcaps
- a Nasdaq Titan universe of large Nasdaq-listed companies

Kallisto examines premarket 5-minute data and ranks available securities by accumulated premarket volume. The active V1 configuration keeps approximately the top 8 candidates from each universe when usable data is available.

## Decision cycles

Azure Functions is the trading clock. The Function wakes around U.S. market hours, restores Kallisto state from Azure Blob Storage, and the Python workflow checks the NYSE calendar plus New York local time before trading work proceeds.

Position monitoring runs on approximately a 5-minute cadence. LLM trade decisions are due approximately every 15 minutes after the opening price-discovery period and before the new-entry cutoff.

For each valid decision cycle, candidates are refreshed with current technical features and available fundamental context. GPT-5.6 Luna may propose a LONG or synthetic SHORT hypothesis.

The model does not control unrestricted sizing. Deterministic code decides whether sufficient risk capacity exists and calculates the hypothetical whole-share position size, stop, target and portfolio exposure.

## Adaptive self-evaluation

Kallisto measures its own completed trades and benchmark-relative performance daily. Every 5 completed NYSE sessions, a separate evaluator reviews the evidence. Actual parameter changes are gated until there are at least 20 completed trades and at least 10 completed sessions since the previous accepted change, with evaluator confidence of at least 0.60.

Accepted changes are bounded, versioned, and recorded as V1.1, V1.2, and so on. Hard safety rules cannot be removed by the evaluator.

## Analysis features

Technical features include:

- premarket volume and change
- VWAP
- EMA 9 / EMA 20
- RSI(14)
- MACD / signal
- ATR
- relative intraday volume
- opening-range high/low and breakout/breakdown

Fundamental/context fields may include market cap, float, beta, valuation, margins, growth, ROE, leverage, and short interest when the data source provides them.

These are public, widely used analysis concepts. Kallisto does not claim proprietary Wall Street signals or private market data.

## Intraday-only rule

Monitoring begins around 09:25 ET. Entries are allowed after approximately 09:40 ET. New entries stop at 15:30 ET. All remaining positions are force-closed at approximately 15:55 ET. No position is intentionally held overnight.

## Long and short treatment

Long and synthetic short hypotheses are allowed. Synthetic shorts reserve their full entry notional as collateral, and short-sale proceeds are not added to buying power. This keeps the simulated portfolio effectively unleveraged.

The simulation does not model real-world short locates, borrow fees, margin requirements, or broker-specific shortability.

## Benchmark comparison

Daily portfolio value is compared with normalized $1,000 series for:

- S&P 500 (`^GSPC`)
- Nasdaq-100 (`^NDX`)

Kallisto also tracks rolling alpha, drawdown, win rate, profit factor, strategy version history, and a frozen V1.0 risk replay used as a limited counterfactual control.

## Automation

No manual trade approval is required. Azure runs the simulation cycles. GitHub Actions compile-check the code, run deterministic tests, deploy the Azure Function, and refresh documentation/results from Azure after market sessions.

## Attribution

Kallisto remains based on and inspired by Nathan Smith / LuckyOne7777's LLM-Investor-Behavior-Benchmark and LLM-Trading-Lab projects. The original MIT license and attribution are retained.
