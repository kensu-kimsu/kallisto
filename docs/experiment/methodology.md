\# Experiment Methodology



\## Source and Attribution



This personal experiment is adapted from the original work of \*\*Nathan Smith / LuckyOne7777\*\*:



\- \[LLM-Investor-Behavior-Benchmark](https://github.com/LuckyOne7777/LLM-Investor-Behavior-Benchmark)

\- \[LLM-Trading-Lab](https://github.com/LuckyOne7777/LLM-Trading-Lab)



The original projects provide the LIBB framework, portfolio-processing architecture, persistent state, simulated order handling, and core experimental structure.



This repository applies that foundation to a separate six-month simulated experiment operated from Australia.



\## Objective



The experiment compares two independently managed AI portfolios:



\- Microcap Growth

\- Nasdaq Titan Growth



Each begins with $1,000 USD.



The portfolios are compared against:



\- S\&P 500

\- Nasdaq-100



\## Operating Location



The experiment is operated from Melbourne, Australia.



Because the U.S. market trades overnight relative to Australian daytime hours, the workflow uses the latest fully completed NYSE session rather than requiring live overnight monitoring.



\## Decision Process



The AI is responsible for investment decisions.



The human operator:



\- runs the workflow

\- reviews validated recommendations

\- approves valid simulated orders

\- does not selectively rewrite valid AI investment decisions



\## Execution



Approved recommendations become pending simulated orders.



On the next applicable NYSE session, the LIBB execution engine determines whether the order could have filled using market data for that session.



\## Constraints



The experiment is:



\- simulation only

\- long only

\- whole shares only

\- LIMIT orders only

\- DAY time-in-force

\- regular-hours execution

\- no leverage

\- no margin

\- no options

\- no short selling



\## Portfolio Universes



\### Microcap Growth



The Microcap universe includes U.S.-listed equities with market capitalization below $300 million and major-exchange listings.



The workflow supplies approximately the top 50 qualifying securities by trading volume.



The trading application available to the operator in Australia does not necessarily support every U.S.-listed microcap, so a separate restriction mechanism is available for securities that are known to be unavailable.



\### Nasdaq Titan Growth



The Nasdaq Titan universe includes approximately the top 20 distinct Nasdaq-listed equities by market capitalization.



Duplicate company share classes are filtered where possible.



\## Models



Monday-Thursday completed NYSE sessions:



\- GPT-5.6 Luna



Friday completed NYSE session:



\- GPT-5.6 Terra



\## Safeguards



Before an API call is made, the workflow checks:



\- whether a new completed NYSE session exists

\- whether that session has already been processed

\- whether both portfolios are synchronized

\- whether a trading session appears to have been skipped



This avoids unnecessary API spending and protects the chronological integrity of the experiment.



\## Reporting



The system tracks:



\- portfolio equity

\- cash

\- holdings

\- trade history

\- daily returns

\- weekly returns

\- monthly returns

\- drawdowns

\- S\&P 500 comparison

\- Nasdaq-100 comparison

\- OpenAI API usage and cost

\- four-week mechanical projections



\## Limitations



This is a simulated study.



Real-world fills, spreads, liquidity, broker restrictions, partial fills, and execution timing may differ materially from the simulation.



Four-week projections are mechanical extrapolations of recent weekly performance and are not forecasts.

