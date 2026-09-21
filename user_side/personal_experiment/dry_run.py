from pathlib import Path
import json

from libb import LIBBmodel

from user_side.personal_experiment.market_clock import get_market_context
from user_side.personal_experiment.prompts.deep_research_prompt import (
    create_personal_deep_research_prompt,
)


RUN_ROOT = Path("user_side/runs/personal_v1")

OUTPUT_ROOT = Path(
    "user_side/personal_experiment/dry_run_output"
)

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


def load_existing_config(model_path: Path):
    config_path = model_path / "config.json"

    if not config_path.exists():
        raise RuntimeError(
            f"Missing LIBB config: {config_path}"
        )

    with open(
        config_path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def build_prompt(
    experiment: str,
    run_date,
    next_session,
):
    model_path = RUN_ROOT / experiment

    existing_config = load_existing_config(
        model_path
    )

    libb = LIBBmodel(
        model_path,
        run_date=run_date,
        config=existing_config,
    )

    print(
        f"{experiment}: loading candidate universe..."
    )

    prompt = create_personal_deep_research_prompt(
        libb,
        experiment,
        next_session,
    )

    output_path = (
        OUTPUT_ROOT
        / f"{experiment}_prompt.txt"
    )

    output_path.write_text(
        prompt,
        encoding="utf-8",
    )

    print(
        f"{experiment}: prompt saved to {output_path}"
    )

    print(
        f"{experiment}: cash = ${libb.cash:,.2f}"
    )

    print(
        f"{experiment}: active positions = {len(libb.portfolio)}"
    )

    print(
        f"{experiment}: prompt length = {len(prompt):,} characters"
    )

    print()

    return output_path


def main():
    print("=" * 60)
    print("PERSONAL LLM TRADING EXPERIMENT - DRY RUN")
    print("=" * 60)
    print()

    context = get_market_context()

    run_date = context[
        "latest_completed_nyse_session"
    ]

    next_session = context[
        "next_nyse_session"
    ]

    print(
        f"Latest completed NYSE session: {run_date}"
    )

    print(
        f"Next NYSE session: {next_session}"
    )

    print()

    if run_date is None:
        raise RuntimeError(
            "Could not determine latest completed NYSE session."
        )

    if next_session is None:
        raise RuntimeError(
            "Could not determine next NYSE session."
        )

    build_prompt(
        "microcap",
        run_date,
        next_session,
    )

    build_prompt(
        "titans",
        run_date,
        next_session,
    )

    print("=" * 60)
    print("DRY RUN COMPLETE")
    print("=" * 60)

    print()
    print("No OpenAI API call was made.")
    print("No trades or pending orders were created.")


if __name__ == "__main__":
    main()
