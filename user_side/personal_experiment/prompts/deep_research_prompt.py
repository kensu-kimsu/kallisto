from libb.model import LIBBmodel

from user_side.prompt_orchestration.get_prompt_data import get_macro_news
from user_side.personal_experiment.market_data.universe_data import (
    get_microcap_prompt_data,
    get_titan_prompt_data,
)


def create_personal_deep_research_prompt(
    libb: LIBBmodel,
    experiment: str,
    next_session,
) -> str:

    experiment = experiment.lower().strip()

    if experiment == "microcap":
        experiment_name = "MICROCAP GROWTH"
        universe = get_microcap_prompt_data()

        strategy_rules = """
STRATEGY-SPECIFIC RULES

- This is the Microcap Growth portfolio.
- A NEW position may ONLY be initiated from the supplied eligible microcap list.
- Eligible candidates are major-U.S.-exchange-listed equities below $300 million market cap.
- The candidate feed is ranked by trading volume.
- Existing holdings may still be HELD, TRIMMED, SOLD, or have stop-losses updated
  even if they disappear from today's candidate list.
- Never invent a ticker outside the supplied candidate universe for a new position.
"""

    elif experiment == "titans":
        experiment_name = "NASDAQ TITAN GROWTH"
        universe = get_titan_prompt_data()

        strategy_rules = """
STRATEGY-SPECIFIC RULES

- This is the Nasdaq Titan Growth portfolio.
- A NEW position may ONLY be initiated from the supplied eligible Titan list.
- The universe contains the top 20 distinct Nasdaq-listed equities ranked
  by current market capitalization.
- Existing holdings may still be HELD, TRIMMED, SOLD, or have stop-losses updated
  even if they disappear from today's top-20 list.
- Never invent a ticker outside the supplied candidate universe for a new position.
"""

    else:
        raise ValueError(
            "experiment must be either 'microcap' or 'titans'"
        )

    today = libb.run_date
    portfolio = libb.portfolio
    cash = libb.cash

    if portfolio.empty:
        portfolio_text = (
            "No active positions.\n"
            f"Available cash: ${cash:,.2f}\n"
            "This is an empty starting portfolio."
        )
    else:
        portfolio_text = portfolio.to_string(index=False)

    execution_log = libb.recent_execution_logs()

    if isinstance(execution_log, str) or execution_log.empty:
        execution_text = "No recent trade logs."
    else:
        execution_text = execution_log.to_string(index=False)

    try:
        macro_news = get_macro_news()
        if not macro_news.strip():
            macro_news = "No material macro headlines supplied."
    except Exception:
        macro_news = "No material macro headlines supplied."

    prompt = f"""
SYSTEM MESSAGE

You are managing a simulated investment portfolio as part of a controlled
six-month LLM trading experiment.

EXPERIMENT
{experiment_name}

LATEST COMPLETED NYSE SESSION
{today}

NEXT INTENDED NYSE TRADING SESSION
{next_session}

OBJECTIVE

Pursue aggressive portfolio growth while controlling the probability
and magnitude of permanent capital loss.

Growth is the primary objective, but every trade must remain rational,
liquid, executable, and risk-controlled.

COMMON PORTFOLIO RULES

- Starting capital was $1,000 USD.
- Use ONLY the current portfolio state supplied below.
- Never reset capital.
- No new external capital.
- Long-only.
- No short selling.
- No margin.
- No leverage.
- No options.
- No derivatives.
- Full shares only.
- Every new long position must specify a stop-loss.
- LIMIT orders only.
- DAY time-in-force only.
- Regular U.S. market hours only.
- No extended-hours execution.
- Never spend more cash than is available.
- Holding cash is allowed.
- All tickers must be uppercase.
- Do not fabricate prices, news, fundamentals, catalysts, or portfolio information.

{strategy_rules}

CURRENT PORTFOLIO

Cash:
${cash:,.2f}

Positions:
{portfolio_text}

ELIGIBLE NEW-POSITION UNIVERSE

{universe}

RECENT EXECUTION LOG

{execution_text}

SUPPLIED U.S. MACRO NEWS

{macro_news}

RESEARCH TASK

Evaluate the portfolio and supplied candidate universe.

Use only information actually supplied in this prompt.

Consider:

- current price
- market capitalization
- liquidity
- current volume
- average volume where supplied
- portfolio concentration
- available cash
- cost basis of existing positions
- stop-loss placement
- execution history
- supplied macro/news context

For existing positions choose among:

KEEP
ADD
TRIM
EXIT
UPDATE STOP

For eligible candidates choose whether any deserve:

INITIATE

Do NOT claim you analyzed financial statements, earnings, valuation ratios,
analyst estimates, catalysts, or news that were not supplied.

If the information is insufficient to justify a trade, holding cash is valid.

EXECUTION RULES

Every order must use:

- next intended trading session: {next_session}
- LIMIT order
- DAY time-in-force
- full shares only

Action codes:

"b" = buy
"s" = sell
"u" = update stop-loss

Every order must contain:

- action
- ticker
- shares
- order_type
- limit_price
- time_in_force
- date
- stop_loss
- rationale
- confidence

A new BUY ticker MUST come from the supplied eligible universe.

OUTPUT EXACTLY THREE BLOCKS

<ANALYSIS_BLOCK>
Explain the portfolio assessment, candidate assessment, major risks,
and reasoning behind the decision.
</ANALYSIS_BLOCK>

<ORDERS_JSON>
{{
  "orders": [
    {{
      "action": "b",
      "ticker": "XYZ",
      "shares": 1,
      "order_type": "LIMIT",
      "limit_price": 10.25,
      "time_in_force": "DAY",
      "date": "{next_session}",
      "stop_loss": 8.90,
      "rationale": "short justification",
      "confidence": 0.80
    }}
  ]
}}
</ORDERS_JSON>

If no orders are appropriate:

<ORDERS_JSON>
{{
  "orders": []
}}
</ORDERS_JSON>

<CONFIDENCE_LVL>
0.65
</CONFIDENCE_LVL>

The ORDERS_JSON block must contain valid JSON and no comments.
"""

    return prompt
