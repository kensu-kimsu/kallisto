import os
import json
import csv
import math
from pathlib import Path
from datetime import datetime, timedelta
from user_side.personal_experiment.github_sync import commit_and_push


from openai import OpenAI
import pandas_market_calendars as mcal

from libb import LIBBmodel
from libb.other.parse import parse_json

from user_side.personal_experiment.market_clock import get_market_context
from user_side.personal_experiment.prompts.deep_research_prompt import (
    create_personal_deep_research_prompt,
)
from user_side.personal_experiment.reporting.refresh_reports import (
    main as refresh_reports,
)
from user_side.personal_experiment.reporting.four_week_projection import (
    generate_projection,
)
from user_side.personal_experiment.cost_tracking.api_cost_tracker import (
    log_api_usage,
)
from user_side.personal_experiment.market_data.microcap_screener import (
    get_microcap_universe,
)
from user_side.personal_experiment.market_data.titan_screener import (
    get_titan_universe,
)
from user_side.personal_experiment.daily_journal import (
    create_daily_journal,
)

RUN_ROOT = Path("user_side/runs/personal_v1")

DAILY_MODEL = "gpt-5.6-luna"
WEEKLY_MODEL = "gpt-5.6-terra"

# Terminal readability colors.
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def load_existing_config(model_path: Path):
    config_path = model_path / "config.json"

    with open(
        config_path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def choose_model(run_date):
    if run_date.weekday() == 4:
        return WEEKLY_MODEL, "weekly"

    return DAILY_MODEL, "daily"


def call_openai(prompt: str, model_name: str):
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set."
        )

    client = OpenAI(
        api_key=api_key
    )

    reasoning_effort = (
        "medium"
        if model_name == WEEKLY_MODEL
        else "low"
    )

    response = client.responses.create(
        model=model_name,
        input=prompt,
        reasoning={
            "effort": reasoning_effort
        },
    )

    output = response.output_text

    if not output:
        raise RuntimeError(
            "OpenAI returned an empty response."
        )

    usage = response.usage

    input_tokens = (
        usage.input_tokens
        if usage is not None
        else 0
    )

    output_tokens = (
        usage.output_tokens
        if usage is not None
        else 0
    )

    return (
        output,
        input_tokens,
        output_tokens,
    )


def get_eligible_universe(experiment):
    """
    Return both:

    1. Set of eligible tickers used for hard validation.
    2. Dictionary mapping ticker -> company name used
       only for the human-readable order display.

    This uses the same screener call, so no extra
    market-data request is needed just for names.
    """

    if experiment == "microcap":
        df = get_microcap_universe(
            candidate_count=50
        )

    elif experiment == "titans":
        df = get_titan_universe(
            top_n=20
        )

    else:
        raise RuntimeError(
            f"Unknown experiment: {experiment}"
        )

    if df is None or len(df) == 0:
        raise RuntimeError(
            f"No eligible stocks returned "
            f"for {experiment}."
        )

    columns = {
        str(c).lower(): c
        for c in df.columns
    }

    ticker_column = None

    for possible in [
        "ticker",
        "symbol",
    ]:
        if possible in columns:
            ticker_column = columns[possible]
            break

    if ticker_column is None:
        raise RuntimeError(
            "Could not find ticker/symbol "
            "column in screener results."
        )

    name_column = None

    for possible in [
        "company",
        "name",
        "companyname",
        "shortname",
        "longname",
    ]:
        if possible in columns:
            name_column = columns[possible]
            break

    eligible_tickers = set()
    company_names = {}

    for _, row in df.iterrows():
        ticker = str(
            row[ticker_column]
        ).upper().strip()

        if not ticker:
            continue

        eligible_tickers.add(
            ticker
        )

        company_name = ticker

        if name_column is not None:
            raw_name = row[
                name_column
            ]

            if raw_name is not None:
                candidate_name = str(
                    raw_name
                ).strip()

                if (
                    candidate_name
                    and candidate_name.lower()
                    not in {
                        "nan",
                        "none",
                    }
                ):
                    company_name = (
                        candidate_name
                    )

        company_names[
            ticker
        ] = company_name

    return (
        eligible_tickers,
        company_names,
    )


def get_eligible_tickers(experiment):
    """
    Backward-compatible helper used by our
    existing tests.
    """

    tickers, _ = (
        get_eligible_universe(
            experiment
        )
    )

    return tickers


def get_owned_shares(libb, ticker):
    """
    Read current holdings directly from LIBB's
    in-memory portfolio.

    Written defensively so it can handle a
    DataFrame or dictionary representation.
    """

    ticker = ticker.upper().strip()

    portfolio = libb.portfolio

    if portfolio is None:
        return 0

    # Pandas DataFrame style
    if hasattr(portfolio, "columns"):
        if getattr(
            portfolio,
            "empty",
            False,
        ):
            return 0

        columns = {
            str(c).lower(): c
            for c in portfolio.columns
        }

        ticker_column = None

        for possible in [
            "ticker",
            "symbol",
        ]:
            if possible in columns:
                ticker_column = columns[possible]
                break

        shares_column = None

        for possible in [
            "shares",
            "quantity",
            "qty",
            "units",
        ]:
            if possible in columns:
                shares_column = columns[possible]
                break

        if shares_column is None:
            return 0

        if ticker_column is not None:
            matches = portfolio[
                portfolio[ticker_column]
                .astype(str)
                .str.upper()
                == ticker
            ]

            if len(matches) == 0:
                return 0

            return int(
                matches.iloc[0][
                    shares_column
                ]
            )

        # Some portfolio DataFrames use ticker
        # as their index.
        index_strings = [
            str(x).upper()
            for x in portfolio.index
        ]

        if ticker in index_strings:
            actual_index = list(
                portfolio.index
            )[
                index_strings.index(ticker)
            ]

            return int(
                portfolio.loc[
                    actual_index,
                    shares_column,
                ]
            )

        return 0

    # Dictionary style
    if isinstance(portfolio, dict):
        position = (
            portfolio.get(ticker)
            or portfolio.get(
                ticker.lower()
            )
        )

        if position is None:
            return 0

        if isinstance(
            position,
            (int, float),
        ):
            return int(position)

        if isinstance(
            position,
            dict,
        ):
            for key in [
                "shares",
                "quantity",
                "qty",
                "units",
            ]:
                if key in position:
                    return int(
                        position[key]
                    )

    return 0


def validate_orders(
    orders,
    next_session,
    experiment,
    libb,
    eligible_tickers,
):
    """
    Validate AI orders without modifying them.

    If an AI order violates experiment rules,
    the entire recommendation is rejected.
    """

    errors = []

    if not isinstance(orders, dict):
        raise RuntimeError(
            "ORDERS_JSON was not parsed "
            "into a dictionary."
        )

    if "orders" not in orders:
        raise RuntimeError(
            "ORDERS_JSON does not contain "
            "an 'orders' field."
        )

    if not isinstance(
        orders["orders"],
        list,
    ):
        raise RuntimeError(
            "'orders' must be a list."
        )

    current_cash = float(
        libb.cash
    )

    total_buy_commitment = 0.0

    allowed_actions = {
        "b",
        "s",
        "u",
    }

    for number, order in enumerate(
        orders["orders"],
        start=1,
    ):
        prefix = f"Order {number}"

        if not isinstance(order, dict):
            errors.append(
                f"{prefix}: order is not "
                f"a dictionary."
            )
            continue

        required = [
            "action",
            "ticker",
            "shares",
            "order_type",
            "limit_price",
            "time_in_force",
            "date",
            "stop_loss",
            "rationale",
            "confidence",
        ]

        missing = [
            field
            for field in required
            if field not in order
        ]

        if missing:
            errors.append(
                f"{prefix}: missing fields "
                f"{missing}"
            )
            continue

        action = str(
            order["action"]
        ).lower().strip()

        ticker = str(
            order["ticker"]
        ).upper().strip()

        if action not in allowed_actions:
            errors.append(
                f"{prefix}: invalid action "
                f"'{action}'."
            )

        if not ticker:
            errors.append(
                f"{prefix}: ticker is empty."
            )

        # Whole positive shares only.
        shares = order["shares"]

        if (
            isinstance(shares, bool)
            or not isinstance(shares, int)
        ):
            errors.append(
                f"{prefix}: shares must be "
                f"a whole integer."
            )
        elif shares <= 0:
            errors.append(
                f"{prefix}: shares must be "
                f"greater than zero."
            )

        # LIMIT orders only.
        if (
            str(order["order_type"])
            .upper()
            .strip()
            != "LIMIT"
        ):
            errors.append(
                f"{prefix}: only LIMIT "
                f"orders are allowed."
            )

        # DAY orders only.
        if (
            str(order["time_in_force"])
            .upper()
            .strip()
            != "DAY"
        ):
            errors.append(
                f"{prefix}: only DAY "
                f"orders are allowed."
            )

        # Correct trading date.
        if str(
            order["date"]
        ) != str(next_session):
            errors.append(
                f"{prefix}: order date "
                f"{order['date']} does not "
                f"match next NYSE session "
                f"{next_session}."
            )

        # Limit price validation.
        try:
            limit_price = float(
                order["limit_price"]
            )

            if (
                not math.isfinite(
                    limit_price
                )
                or limit_price <= 0
            ):
                raise ValueError

        except (
            TypeError,
            ValueError,
        ):
            errors.append(
                f"{prefix}: limit_price must "
                f"be a positive number."
            )
            limit_price = None

        # Confidence 0 to 1.
        try:
            confidence = float(
                order["confidence"]
            )

            if (
                not math.isfinite(
                    confidence
                )
                or not (
                    0 <= confidence <= 1
                )
            ):
                raise ValueError

        except (
            TypeError,
            ValueError,
        ):
            errors.append(
                f"{prefix}: confidence must "
                f"be between 0 and 1."
            )

        owned_shares = (
            get_owned_shares(
                libb,
                ticker,
            )
        )

        # BUY safety checks.
        if action == "b":
            if ticker not in eligible_tickers:
                errors.append(
                    f"{prefix}: BUY ticker "
                    f"{ticker} is outside the "
                    f"approved {experiment} "
                    f"universe."
                )

            stop_loss = order[
                "stop_loss"
            ]

            try:
                stop_loss = float(
                    stop_loss
                )

                if (
                    not math.isfinite(
                        stop_loss
                    )
                    or stop_loss <= 0
                ):
                    raise ValueError

                if (
                    limit_price is not None
                    and stop_loss
                    >= limit_price
                ):
                    errors.append(
                        f"{prefix}: BUY "
                        f"stop_loss must be "
                        f"below limit_price."
                    )

            except (
                TypeError,
                ValueError,
            ):
                errors.append(
                    f"{prefix}: BUY requires "
                    f"a positive numeric "
                    f"stop_loss."
                )

            if (
                isinstance(shares, int)
                and not isinstance(
                    shares,
                    bool,
                )
                and shares > 0
                and limit_price is not None
            ):
                total_buy_commitment += (
                    shares
                    * limit_price
                )

        # SELL safety checks.
        elif action == "s":
            if owned_shares <= 0:
                errors.append(
                    f"{prefix}: cannot SELL "
                    f"{ticker}; no position "
                    f"is currently owned."
                )

            elif (
                isinstance(shares, int)
                and shares > owned_shares
            ):
                errors.append(
                    f"{prefix}: attempts to "
                    f"sell {shares} shares of "
                    f"{ticker}, but only "
                    f"{owned_shares} are owned."
                )

        # UPDATE safety checks.
        elif action == "u":
            if owned_shares <= 0:
                errors.append(
                    f"{prefix}: cannot UPDATE "
                    f"{ticker}; no existing "
                    f"position is owned."
                )

            elif (
                isinstance(shares, int)
                and shares > owned_shares
            ):
                errors.append(
                    f"{prefix}: UPDATE "
                    f"references {shares} "
                    f"shares of {ticker}, "
                    f"but only {owned_shares} "
                    f"are owned."
                )

            if (
                order["stop_loss"]
                is not None
            ):
                try:
                    update_stop = float(
                        order["stop_loss"]
                    )

                    if (
                        not math.isfinite(
                            update_stop
                        )
                        or update_stop <= 0
                    ):
                        raise ValueError

                except (
                    TypeError,
                    ValueError,
                ):
                    errors.append(
                        f"{prefix}: UPDATE "
                        f"stop_loss must be "
                        f"positive when supplied."
                    )

    # Conservative cash rule:
    # purchases must be affordable using
    # cash already available now.
    #
    # We deliberately do NOT assume that a
    # simultaneous SELL will fill and fund
    # another BUY.
    if total_buy_commitment > (
        current_cash + 0.000001
    ):
        errors.append(
            "Total proposed BUY commitment "
            f"is ${total_buy_commitment:,.2f}, "
            f"but available simulated cash "
            f"is only ${current_cash:,.2f}."
        )

    if errors:
        message = (
            "\nAI ORDER VALIDATION FAILED\n"
            + "-" * 50
            + "\n"
            + "\n".join(
                f"- {error}"
                for error in errors
            )
            + "\n"
            + "-" * 50
            + "\nNo pending simulated "
            + "orders were saved."
        )

        raise RuntimeError(
            message
        )

    return True


def add_company_names_to_orders(
    orders,
    company_names,
):
    """
    Add a human-readable company name to each
    order before it is permanently saved.

    This does not change the trading decision.
    """

    for order in orders.get(
        "orders",
        [],
    ):
        ticker = str(
            order.get(
                "ticker",
                "",
            )
        ).upper().strip()

        order["company_name"] = (
            company_names.get(
                ticker,
                ticker,
            )
        )

    return orders


def display_orders_for_approval(
    experiment,
    orders,
    current_cash,
    company_names,
):
    """
    Human-readable order summary.

    Colors are visual only and have no effect on
    validation or simulation behavior.
    """

    print()

    print(
        f"{YELLOW}{BOLD}"
        + "=" * 60
        + f"{RESET}"
    )

    print(
        f"{YELLOW}{BOLD}"
        f"{experiment.upper()} "
        f"- VALIDATED AI RECOMMENDATION"
        f"{RESET}"
    )

    print(
        f"{YELLOW}{BOLD}"
        + "=" * 60
        + f"{RESET}"
    )

    print(
        f"Current simulated cash: "
        f"{GREEN}"
        f"${float(current_cash):,.2f}"
        f"{RESET}"
    )

    print()

    if len(orders["orders"]) == 0:
        print(
            f"{YELLOW}"
            "AI proposed no orders."
            f"{RESET}"
        )

    for number, order in enumerate(
        orders["orders"],
        start=1,
    ):
        ticker = str(
            order["ticker"]
        ).upper().strip()

        company_name = (
            company_names.get(
                ticker,
                ticker,
            )
        )

        action = str(
            order["action"]
        ).upper()

        print(
            f"{YELLOW}{BOLD}"
            f"ORDER {number}"
            f"{RESET}"
        )

        print(
            f"  Company:     "
            f"{YELLOW}"
            f"{company_name}"
            f"{RESET}"
        )

        print(
            f"  Ticker:      "
            f"{GREEN}{BOLD}"
            f"{ticker}"
            f"{RESET}"
        )

        print(
            f"  Action:      "
            f"{GREEN}{BOLD}"
            f"{action}"
            f"{RESET}"
        )

        print(
            f"  Shares:      "
            f"{GREEN}"
            f"{order['shares']:,}"
            f"{RESET}"
        )

        print(
            f"  Limit price: "
            f"{GREEN}"
            f"${float(order['limit_price']):,.2f}"
            f"{RESET}"
        )

        if order[
            "stop_loss"
        ] is None:
            print(
                "  Stop loss:   None"
            )
        else:
            print(
                f"  Stop loss:   "
                f"{YELLOW}"
                f"${float(order['stop_loss']):,.2f}"
                f"{RESET}"
            )

        print(
            f"  Confidence:  "
            f"{order['confidence']}"
        )

        print(
            f"  Date:        "
            f"{order['date']}"
        )

        print(
            f"  Rationale:   "
            f"{order['rationale']}"
        )

        print()

    print(
        f"{YELLOW}{BOLD}"
        + "=" * 60
        + f"{RESET}"
    )


def request_manual_approval():
    """
    Approval checkpoint.

    When AUTO_APPROVE_SIMULATED_ORDERS=true,
    valid simulated orders are automatically approved.

    Hard order validation still happens before this
    function is called.
    """

    auto_approve = (
        os.environ.get(
            "AUTO_APPROVE_SIMULATED_ORDERS",
            "",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "y",
        }
    )

    if auto_approve:
        print()
        print(
            f"{GREEN}{BOLD}"
            "AUTO-APPROVAL ENABLED"
            f"{RESET}"
        )
        print(
            "Validated simulated AI orders "
            "will be approved automatically."
        )
        return True

    while True:
        answer = input(
            f"{YELLOW}{BOLD}"
            "Approve these AI orders for the "
            "SIMULATED portfolio? [Y/N]: "
            f"{RESET}"
        ).strip().lower()

        if answer in {
            "y",
            "yes",
        }:
            return True

        if answer in {
            "n",
            "no",
        }:
            return False

        print(
            "Please enter Y or N."
        )

def run_experiment(
    experiment: str,
    run_date,
    next_session,
):
    print()
    print("=" * 60)
    print(
        f"RUNNING {experiment.upper()}"
    )
    print("=" * 60)

    model_path = (
        RUN_ROOT / experiment
    )

    config = load_existing_config(
        model_path
    )

    libb = LIBBmodel(
        model_path,
        run_date=run_date,
        config=config,
    )

    model_name, run_type = (
        choose_model(run_date)
    )

    print(
        f"Run type: {run_type}"
    )

    print(
        f"OpenAI model: {model_name}"
    )

    print(
        f"Cash before processing: "
        f"${float(libb.cash):,.2f}"
    )

    print(
        "Processing pending "
        "simulated orders..."
    )

    libb.process_portfolio()

    print(
        f"Cash after processing: "
        f"${float(libb.cash):,.2f}"
    )

    print(
        "Building approved "
        "candidate universe..."
    )

    (
        eligible_tickers,
        company_names,
    ) = get_eligible_universe(
        experiment
    )

    print(
        f"Eligible stocks: "
        f"{len(eligible_tickers)}"
    )

    print(
        "Building research prompt..."
    )

    prompt = (
        create_personal_deep_research_prompt(
            libb,
            experiment,
            next_session,
        )
    )

    libb.save_prompt(
        prompt
    )

    print(
        f"Calling OpenAI: "
        f"{model_name}"
    )

    (
        report,
        input_tokens,
        output_tokens,
    ) = call_openai(
        prompt,
        model_name,
    )

    print(
        "OpenAI response received."
    )

    cost_info = log_api_usage(
        run_date=run_date,
        experiment=experiment,
        run_type=run_type,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    print(
        f"Input tokens: "
        f"{input_tokens:,}"
    )

    print(
        f"Output tokens: "
        f"{output_tokens:,}"
    )

    print(
        f"Estimated API cost "
        f"this call: "
        f"${cost_info['total_cost_usd']:.4f} USD"
    )

    print(
        f"Cumulative experiment "
        f"API cost: "
        f"${cost_info['cumulative_cost_usd']:.4f} USD"
    )

    # Preserve the exact AI response even if
    # validation subsequently rejects it.
    libb.save_deep_research(
        report
    )

    libb.analyze_sentiment(
        report,
        report_type=(
            "Weekly_Deep_Research"
            if run_type == "weekly"
            else "Daily_Research"
        ),
    )

    orders = parse_json(
        report,
        "ORDERS_JSON",
    )

    print(
        "Running hard order "
        "validation..."
    )

    validate_orders(
        orders=orders,
        next_session=next_session,
        experiment=experiment,
        libb=libb,
        eligible_tickers=eligible_tickers,
    )

    print(
        "Order validation: PASSED"
    )

    orders = add_company_names_to_orders(
        orders,
        company_names,
    )

    display_orders_for_approval(
        experiment=experiment,
        orders=orders,
        current_cash=libb.cash,
        company_names=company_names,
    )

    approved = (
        request_manual_approval()
    )

    if not approved:
        print()
        print(
            "Manual approval declined."
        )
        print(
            "No pending simulated "
            "orders were saved."
        )
        print(
            "The AI recommendation itself "
            "remains saved for the record."
        )
        return

    libb.save_orders(
        orders
    )

    print()
    print(
        "APPROVED."
    )

    print(
        f"{len(orders['orders'])} "
        f"AI order(s) saved as "
        f"pending SIMULATED orders."
    )



def get_last_processed_session(experiment):
    """
    Read the most recent portfolio-history date.

    This is our authoritative record of which NYSE
    session has already been processed.
    """

    history_path = (
        RUN_ROOT
        / experiment
        / "portfolio"
        / "portfolio_history.csv"
    )

    if not history_path.exists():
        return None

    with open(
        history_path,
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        dates = [
            row.get("date")
            for row in reader
            if row.get("date")
        ]

    if not dates:
        return None

    return datetime.strptime(
        dates[-1],
        "%Y-%m-%d",
    ).date()


def is_nyse_session(session_date):
    """
    Confirm that a date is an actual NYSE
    trading session.
    """

    nyse = mcal.get_calendar("NYSE")

    schedule = nyse.schedule(
        start_date=session_date,
        end_date=session_date,
    )

    return not schedule.empty


def get_next_nyse_session_after(session_date):
    """
    Find the next real NYSE session after the
    supplied date.

    Weekends and exchange holidays are skipped.
    """

    nyse = mcal.get_calendar("NYSE")

    start_date = (
        session_date
        + timedelta(days=1)
    )

    end_date = (
        session_date
        + timedelta(days=14)
    )

    schedule = nyse.schedule(
        start_date=start_date,
        end_date=end_date,
    )

    if schedule.empty:
        raise RuntimeError(
            "Could not determine the next "
            "NYSE trading session."
        )

    return schedule.index[0].date()


def preflight_session_guard(run_date):
    """
    Stop BEFORE any OpenAI call unless there is
    exactly one new NYSE session to process.

    Returns True only when it is safe to continue.
    """

    print()
    print("=" * 60)
    print("SESSION / COST SAFETY CHECK")
    print("=" * 60)

    if not is_nyse_session(run_date):
        print(
            f"ABORTED: {run_date} is not "
            f"a valid NYSE trading session."
        )

        print(
            "No OpenAI API call was made."
        )

        return False

    microcap_last = (
        get_last_processed_session(
            "microcap"
        )
    )

    titans_last = (
        get_last_processed_session(
            "titans"
        )
    )

    print(
        f"Microcap last processed: "
        f"{microcap_last or 'None'}"
    )

    print(
        f"Titans last processed:   "
        f"{titans_last or 'None'}"
    )

    print(
        f"Latest completed NYSE:   "
        f"{run_date}"
    )

    # Both portfolios must remain synchronized.
    if microcap_last != titans_last:
        raise RuntimeError(
            "SAFETY ABORT: Microcap and Titans "
            "are not synchronized.\n"
            f"Microcap last session: {microcap_last}\n"
            f"Titans last session: {titans_last}\n"
            "No API calls will be made until "
            "the portfolio histories are reconciled."
        )

    # Brand-new experiment.
    if microcap_last is None:
        print(
            "No previous session exists."
        )

        print(
            "This is the first portfolio session, "
            "so processing is allowed."
        )

        return True

    last_processed = microcap_last

    # Same session = duplicate run.
    if run_date == last_processed:
        print()
        print(
            "NO NEW NYSE SESSION."
        )

        print(
            f"{run_date} has already been processed."
        )

        print(
            "This can happen when:"
        )

        print(
            "  - you run the workflow twice"
        )

        print(
            "  - it is a weekend"
        )

        print(
            "  - the U.S. market is closed "
            "for a holiday"
        )

        print()
        print(
            "Workflow stopped BEFORE OpenAI."
        )

        print(
            "API cost for this attempt: $0.00"
        )

        return False

    # Date moving backwards is never allowed.
    if run_date < last_processed:
        raise RuntimeError(
            "SAFETY ABORT: The latest completed "
            f"NYSE session ({run_date}) is earlier "
            f"than the last processed session "
            f"({last_processed})."
        )

    expected_next = (
        get_next_nyse_session_after(
            last_processed
        )
    )

    print(
        f"Expected next NYSE:       "
        f"{expected_next}"
    )

    # Important experiment-integrity rule:
    # do not silently skip a trading session.
    if run_date != expected_next:
        raise RuntimeError(
            "SAFETY ABORT: A NYSE session appears "
            "to have been missed.\n"
            f"Last processed: {last_processed}\n"
            f"Expected next:  {expected_next}\n"
            f"Latest now:     {run_date}\n\n"
            "The workflow will NOT skip directly "
            "to a later session because doing so "
            "could corrupt the experiment and "
            "produce misleading portfolio results.\n"
            "No new API call should be made."
        )

    print()
    print(
        "NEW NYSE SESSION CONFIRMED."
    )

    print(
        f"{last_processed} -> {run_date}"
    )

    print(
        "Safe to continue."
    )

    return True


def main():
    print("=" * 60)
    print(
        "PERSONAL LLM TRADING EXPERIMENT"
    )
    print(
        "SIMULATION ONLY - NO LIVE TRADING"
    )
    print("=" * 60)

    context = get_market_context()

    run_date = context[
        "latest_completed_nyse_session"
    ]

    next_session = context[
        "next_nyse_session"
    ]

    print(
        f"Latest completed NYSE session: "
        f"{run_date}"
    )

    print(
        f"Next intended NYSE session: "
        f"{next_session}"
    )

    if run_date is None:
        raise RuntimeError(
            "Could not determine run date."
        )

    if next_session is None:
        raise RuntimeError(
            "Could not determine "
            "next trading session."
        )

    # -------------------------------------------------
    # COST + SESSION PROTECTION
    #
    # Nothing below this point runs unless a genuinely
    # new NYSE trading session exists.
    # -------------------------------------------------

    if not preflight_session_guard(
        run_date
    ):
        print()
        print("=" * 60)
        print(
            "NOTHING TO PROCESS"
        )
        print(
            "NO OPENAI API COST INCURRED"
        )
        print("=" * 60)
        return

    run_experiment(
        "microcap",
        run_date,
        next_session,
    )

    run_experiment(
        "titans",
        run_date,
        next_session,
    )

    print()
    print(
        "Refreshing performance reports..."
    )

    refresh_reports()

    print()
    print(
        "Updating 4-week "
        "performance projection..."
    )

    projection_file = (
        generate_projection()
    )

    # Automatically open the progress chart.
    progress_chart = Path(
        "user_side/personal_experiment/"
        "reporting/output/"
        "equity_comparison.png"
    )

    if progress_chart.exists():
        try:
            os.startfile(
                progress_chart.resolve()
            )
        except Exception as exc:
            print(
                f"Could not automatically "
                f"open progress chart: {exc}"
            )

    # Open projection chart only once enough
    # weekly history exists to create it.
    if (
        projection_file is not None
        and Path(projection_file).exists()
    ):
        try:
            os.startfile(
                Path(projection_file).resolve()
            )
        except Exception as exc:
            print(
                f"Could not automatically "
                f"open projection chart: {exc}"
            )

    print()
    print(
        "Creating daily GitHub journal..."
    )

    create_daily_journal(
        run_date,
        next_session,
    )
    print(
        "Syncing experiment progress to GitHub..."
    )

    github_ok = commit_and_push(
        str(run_date)
    )

    if not github_ok:
        print(
            "\nWARNING: Experiment completed successfully, "
            "but GitHub synchronization did not complete."
        )

    print()
    print("=" * 60)
    print(
        "SIMULATION RUN COMPLETE"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()