from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from user_side.personal_experiment.reporting.performance_tracker import (
    MICROCAP_PATH,
    TITANS_PATH,
    REPORT_ROOT,
    load_portfolio_history,
    normalise_equity,
    get_benchmark,
)


def prepare_portfolio_series(run_path, name):
    df = load_portfolio_history(run_path)

    if df.empty:
        return pd.DataFrame()

    normalised = normalise_equity(df)

    result = normalised[
        ["date", "normalised_equity"]
    ].copy()

    result = result.rename(
        columns={"normalised_equity": name}
    )

    return result


def prepare_benchmark_series(
    ticker,
    name,
    start_date,
    end_date,
):
    df = get_benchmark(
        ticker,
        start_date,
        end_date,
    )

    if df.empty:
        return pd.DataFrame()

    result = df[
        ["date", "normalised_equity"]
    ].copy()

    result = result.rename(
        columns={"normalised_equity": name}
    )

    return result


def combine_series():
    microcap = prepare_portfolio_series(
        MICROCAP_PATH,
        "Microcap Growth",
    )

    titans = prepare_portfolio_series(
        TITANS_PATH,
        "Nasdaq Titan Growth",
    )

    dates = []

    if not microcap.empty:
        dates.extend(microcap["date"].tolist())

    if not titans.empty:
        dates.extend(titans["date"].tolist())

    if not dates:
        return pd.DataFrame()

    start_date = min(dates)
    end_date = max(dates)

    sp500 = prepare_benchmark_series(
        "^GSPC",
        "S&P 500",
        start_date,
        end_date,
    )

    nasdaq100 = prepare_benchmark_series(
        "^NDX",
        "Nasdaq-100",
        start_date,
        end_date,
    )

    frames = [
        x for x in [
            microcap,
            titans,
            sp500,
            nasdaq100,
        ]
        if not x.empty
    ]

    combined = frames[0]

    for frame in frames[1:]:
        combined = pd.merge(
            combined,
            frame,
            on="date",
            how="outer",
        )

    combined = combined.sort_values("date")

    combined = combined.ffill()

    return combined


def calculate_period_returns(df, frequency):
    if df.empty:
        return df

    indexed = (
        df
        .set_index("date")
        .sort_index()
    )

    period_end = indexed.resample(
        frequency
    ).last()

    returns = (
        period_end
        .pct_change()
        * 100
    )

    returns = returns.dropna(
        how="all"
    )

    return returns


def save_weekly_report(combined):
    weekly = calculate_period_returns(
        combined,
        "W-FRI",
    )

    csv_path = (
        REPORT_ROOT
        / "weekly_summary.csv"
    )

    weekly.to_csv(csv_path)

    if weekly.empty:
        return csv_path, None

    plt.figure(
        figsize=(13, 7)
    )

    for column in weekly.columns:
        plt.plot(
            weekly.index,
            weekly[column],
            marker="o",
            label=column,
        )

    plt.axhline(
        0,
        linewidth=1,
    )

    plt.title(
        "Weekly Performance Comparison"
    )

    plt.xlabel("Week")

    plt.ylabel(
        "Weekly return (%)"
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.legend()

    chart_path = (
        REPORT_ROOT
        / "weekly_performance.png"
    )

    plt.tight_layout()

    plt.savefig(
        chart_path,
        dpi=160,
    )

    plt.close()

    return csv_path, chart_path


def save_monthly_report(combined):
    monthly = calculate_period_returns(
        combined,
        "ME",
    )

    csv_path = (
        REPORT_ROOT
        / "monthly_summary.csv"
    )

    monthly.to_csv(csv_path)

    if monthly.empty:
        return csv_path, None

    plt.figure(
        figsize=(13, 7)
    )

    for column in monthly.columns:
        plt.plot(
            monthly.index,
            monthly[column],
            marker="o",
            label=column,
        )

    plt.axhline(
        0,
        linewidth=1,
    )

    plt.title(
        "Monthly Performance Comparison"
    )

    plt.xlabel("Month")

    plt.ylabel(
        "Monthly return (%)"
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.legend()

    chart_path = (
        REPORT_ROOT
        / "monthly_performance.png"
    )

    plt.tight_layout()

    plt.savefig(
        chart_path,
        dpi=160,
    )

    plt.close()

    return csv_path, chart_path


def generate_periodic_reports():
    print(
        "Generating weekly and monthly reports..."
    )

    combined = combine_series()

    if combined.empty:
        print(
            "No portfolio history yet."
        )
        print(
            "Weekly/monthly reports will begin automatically "
            "after trading history exists."
        )
        return

    combined_path = (
        REPORT_ROOT
        / "daily_comparison.csv"
    )

    combined.to_csv(
        combined_path,
        index=False,
    )

    weekly_csv, weekly_chart = (
        save_weekly_report(
            combined
        )
    )

    monthly_csv, monthly_chart = (
        save_monthly_report(
            combined
        )
    )

    print()
    print(
        f"Daily history: {combined_path}"
    )

    print(
        f"Weekly summary: {weekly_csv}"
    )

    if weekly_chart:
        print(
            f"Weekly chart: {weekly_chart}"
        )

    print(
        f"Monthly summary: {monthly_csv}"
    )

    if monthly_chart:
        print(
            f"Monthly chart: {monthly_chart}"
        )


if __name__ == "__main__":
    generate_periodic_reports()
