from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf


# ============================================================
# PATHS / SETTINGS
# ============================================================

STARTING_CAPITAL = 1000.0

ROOT = Path("user_side/runs/personal_v1")

MICROCAP_PATH = ROOT / "microcap"
TITANS_PATH = ROOT / "titans"

REPORT_ROOT = Path(
    "user_side/personal_experiment/reporting/output"
)

REPORT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD LIBB PORTFOLIO HISTORY
# ============================================================

def load_portfolio_history(run_path: Path) -> pd.DataFrame:

    path = (
        run_path
        / "portfolio"
        / "portfolio_history.csv"
    )

    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])

    return (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )


# ============================================================
# NORMALISE PORTFOLIOS TO $1,000
# ============================================================

def normalise_equity(
    df: pd.DataFrame,
    starting_value: float = STARTING_CAPITAL,
):

    if df.empty:
        return df

    out = df[
        ["date", "equity"]
    ].copy()

    first_equity = float(
        out["equity"].iloc[0]
    )

    if first_equity <= 0:
        raise RuntimeError(
            "Cannot normalise portfolio with "
            "zero or negative starting equity."
        )

    out["normalised_equity"] = (
        out["equity"]
        / first_equity
    ) * starting_value

    return out


# ============================================================
# BENCHMARK DATA
# ============================================================

def get_benchmark(
    ticker: str,
    start_date,
    end_date,
    starting_value: float = STARTING_CAPITAL,
):

    data = yf.download(
        ticker,
        start=start_date,
        end=end_date + pd.Timedelta(days=1),
        auto_adjust=True,
        progress=False,
    )

    if data.empty:
        return pd.DataFrame()

    close = data["Close"]

    # yfinance can return a DataFrame instead
    # of a Series depending on version.
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    benchmark = pd.DataFrame({
        "date": pd.to_datetime(close.index),
        "close": close.values,
    })

    first_close = float(
        benchmark["close"].iloc[0]
    )

    benchmark["normalised_equity"] = (
        benchmark["close"]
        / first_close
    ) * starting_value

    return benchmark


# ============================================================
# DRAWDOWN
# ============================================================

def calculate_drawdown(equity_series):

    rolling_peak = equity_series.cummax()

    drawdown = (
        equity_series
        - rolling_peak
    ) / rolling_peak

    return drawdown * 100


# ============================================================
# MAIN EQUITY COMPARISON CHART
# ============================================================

def create_equity_chart(
    microcap: pd.DataFrame,
    titans: pd.DataFrame,
    sp500: pd.DataFrame,
    nasdaq100: pd.DataFrame,
):
    """
    Create the main experiment progress chart.

    Shows the value of the original $1,000 investment
    over time for both AI portfolios and both benchmarks.

    Also displays:
    - final cumulative return
    - maximum drawdown for AI portfolios
    - solid lines for AI strategies
    - dashed lines for benchmarks
    """

    import matplotlib.dates as mdates

    output_path = (
        REPORT_ROOT
        / "equity_comparison.png"
    )

    fig, ax = plt.subplots(
        figsize=(14, 8)
    )

    starting_capital = 1000.0

    def prepare_series(df):
        if df is None or df.empty:
            return None

        working = df.copy()

        # -----------------------------------------
        # Find date information.
        # -----------------------------------------

        if "date" in working.columns:
            dates = pd.to_datetime(
                working["date"],
                errors="coerce",
            )
        elif isinstance(
            working.index,
            pd.DatetimeIndex,
        ):
            dates = pd.to_datetime(
                working.index
            )
        else:
            return None

        # -----------------------------------------
        # Find equity/value column.
        # -----------------------------------------

        preferred_columns = [
            "equity",
            "normalized_equity",
            "normalised_equity",
            "value",
            "portfolio_value",
        ]

        value_column = None

        for column in preferred_columns:
            if column in working.columns:
                value_column = column
                break

        if value_column is None:
            numeric_columns = (
                working.select_dtypes(
                    include="number"
                ).columns.tolist()
            )

            if not numeric_columns:
                return None

            value_column = (
                numeric_columns[0]
            )

        values = pd.to_numeric(
            working[value_column],
            errors="coerce",
        )

        result = pd.DataFrame(
            {
                "date": dates,
                "equity": values,
            }
        )

        result = (
            result
            .dropna()
            .sort_values("date")
        )

        if result.empty:
            return None

        return result


    def plot_series(
        df,
        label,
        linestyle="-",
        linewidth=2.5,
        marker=None,
        annotate_drawdown=False,
    ):
        series = prepare_series(
            df
        )

        if series is None:
            return

        dates = series[
            "date"
        ]

        equity = series[
            "equity"
        ]

        if equity.empty:
            return

        # -----------------------------------------
        # Main line
        # -----------------------------------------

        line, = ax.plot(
            dates,
            equity,
            label=label,
            linestyle=linestyle,
            linewidth=linewidth,
            marker=marker,
            markersize=4,
        )

        # -----------------------------------------
        # Final return annotation
        # -----------------------------------------

        first_value = float(
            equity.iloc[0]
        )

        final_value = float(
            equity.iloc[-1]
        )

        if first_value != 0:
            final_return = (
                (
                    final_value
                    / first_value
                )
                - 1
            ) * 100
        else:
            final_return = 0.0

        return_text = (
            f"{final_return:+.1f}%"
        )

        ax.annotate(
            return_text,
            xy=(
                dates.iloc[-1],
                final_value,
            ),
            xytext=(
                8,
                0,
            ),
            textcoords=(
                "offset points"
            ),
            va="center",
            fontsize=9,
            fontweight="bold",
            color=line.get_color(),
        )

        # -----------------------------------------
        # Maximum drawdown annotation
        # -----------------------------------------

        if (
            annotate_drawdown
            and len(equity) >= 2
        ):
            running_max = (
                equity.cummax()
            )

            drawdown = (
                equity
                / running_max
                - 1
            )

            max_dd_index = (
                drawdown.idxmin()
            )

            max_dd = float(
                drawdown.loc[
                    max_dd_index
                ]
            )

            # Don't clutter chart with a
            # meaningless 0.0% annotation.
            if max_dd < -0.001:
                dd_date = series.loc[
                    max_dd_index,
                    "date",
                ]

                dd_equity = float(
                    series.loc[
                        max_dd_index,
                        "equity",
                    ]
                )

                ax.annotate(
                    (
                        f"{max_dd * 100:.1f}% "
                        f"max drawdown"
                    ),
                    xy=(
                        dd_date,
                        dd_equity,
                    ),
                    xytext=(
                        0,
                        -26,
                    ),
                    textcoords=(
                        "offset points"
                    ),
                    ha="center",
                    fontsize=8,
                    color=line.get_color(),
                    arrowprops={
                        "arrowstyle": "->",
                        "color": line.get_color(),
                        "alpha": 0.7,
                    },
                )


    # =====================================================
    # AI PORTFOLIOS
    # =====================================================

    plot_series(
        microcap,
        "Microcap Growth ($1,000 invested)",
        linestyle="-",
        linewidth=2.8,
        marker="o",
        annotate_drawdown=True,
    )

    plot_series(
        titans,
        "Nasdaq Titan Growth ($1,000 invested)",
        linestyle="-",
        linewidth=2.8,
        marker="o",
        annotate_drawdown=True,
    )


    # =====================================================
    # BENCHMARKS
    # =====================================================

    plot_series(
        sp500,
        "S&P 500 ($1,000 benchmark)",
        linestyle="--",
        linewidth=2.0,
        annotate_drawdown=False,
    )

    plot_series(
        nasdaq100,
        "Nasdaq-100 ($1,000 benchmark)",
        linestyle="--",
        linewidth=2.0,
        annotate_drawdown=False,
    )


    # =====================================================
    # Starting-capital reference line
    # =====================================================

    ax.axhline(
        y=starting_capital,
        linestyle=":",
        linewidth=1.2,
        alpha=0.6,
    )

    ax.text(
        0.01,
        starting_capital,
        "$1,000 starting capital",
        transform=ax.get_yaxis_transform(),
        fontsize=8,
        va="bottom",
        alpha=0.75,
    )


    # =====================================================
    # Formatting
    # =====================================================

    ax.set_title(
        "LLM Trading Experiment: Portfolio Progress",
        fontsize=15,
        fontweight="bold",
        pad=14,
    )

    ax.set_xlabel(
        "Date"
    )

    ax.set_ylabel(
        "Value of $1,000 investment (USD)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend(
        loc="best",
        frameon=True,
    )

    ax.xaxis.set_major_locator(
        mdates.AutoDateLocator(
            minticks=5,
            maxticks=10,
        )
    )

    ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(
            ax.xaxis.get_major_locator()
        )
    )

    # Leave space on the right for
    # final-return labels.
    ax.margins(
        x=0.08,
        y=0.10,
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=170,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    return output_path


def create_drawdown_chart(
    microcap: pd.DataFrame,
    titans: pd.DataFrame,
    sp500: pd.DataFrame,
    nasdaq100: pd.DataFrame,
):

    plt.figure(
        figsize=(13, 7)
    )

    datasets = [
        (
            microcap,
            "Microcap Growth",
        ),
        (
            titans,
            "Nasdaq Titan Growth",
        ),
        (
            sp500,
            "S&P 500",
        ),
        (
            nasdaq100,
            "Nasdaq-100",
        ),
    ]

    for df, label in datasets:

        if df.empty:
            continue

        drawdown = calculate_drawdown(
            df["normalised_equity"]
        )

        plt.plot(
            df["date"],
            drawdown,
            label=label,
        )

    plt.title(
        "LLM Trading Experiment - Drawdown Comparison"
    )

    plt.xlabel("Date")

    plt.ylabel(
        "Drawdown (%)"
    )

    plt.axhline(
        0,
        linewidth=1,
    )

    plt.legend()

    plt.grid(
        True,
        alpha=0.3,
    )

    output = (
        REPORT_ROOT
        / "drawdown_comparison.png"
    )

    plt.tight_layout()

    plt.savefig(
        output,
        dpi=160,
    )

    plt.close()

    return output


# ============================================================
# SUMMARY STATISTICS
# ============================================================

def summary_stats(
    name: str,
    df: pd.DataFrame,
):

    if df.empty:
        return {
            "strategy": name,
            "status": "no_data",
        }

    starting_equity = float(
        df["equity"].iloc[0]
    )

    ending_equity = float(
        df["equity"].iloc[-1]
    )

    total_return = (
        (
            ending_equity
            - starting_equity
        )
        / starting_equity
    ) * 100

    daily_returns = (
        df["equity"]
        .pct_change()
        .dropna()
    )

    volatility = None
    sharpe = None

    if not daily_returns.empty:

        daily_std = (
            daily_returns.std()
        )

        volatility = (
            daily_std
            * (252 ** 0.5)
            * 100
        )

        if daily_std > 0:

            sharpe = (
                daily_returns.mean()
                / daily_std
            ) * (252 ** 0.5)

    normalised = normalise_equity(
        df
    )

    max_drawdown = (
        calculate_drawdown(
            normalised[
                "normalised_equity"
            ]
        )
        .min()
    )

    return {
        "strategy": name,
        "status": "ok",
        "start_date": str(
            df["date"]
            .iloc[0]
            .date()
        ),
        "end_date": str(
            df["date"]
            .iloc[-1]
            .date()
        ),
        "starting_equity": round(
            starting_equity,
            2,
        ),
        "ending_equity": round(
            ending_equity,
            2,
        ),
        "profit_loss": round(
            ending_equity
            - starting_equity,
            2,
        ),
        "total_return_pct": round(
            total_return,
            2,
        ),
        "annualised_volatility_pct": (
            round(
                float(volatility),
                2,
            )
            if volatility is not None
            else None
        ),
        "sharpe_estimate": (
            round(
                float(sharpe),
                3,
            )
            if sharpe is not None
            else None
        ),
        "max_drawdown_pct": round(
            float(max_drawdown),
            2,
        ),
    }


# ============================================================
# BENCHMARK SUMMARY STATISTICS
# ============================================================

def benchmark_stats(
    name: str,
    df: pd.DataFrame,
):

    if df.empty:
        return {
            "strategy": name,
            "status": "no_data",
        }

    starting_value = float(
        df[
            "normalised_equity"
        ].iloc[0]
    )

    ending_value = float(
        df[
            "normalised_equity"
        ].iloc[-1]
    )

    total_return = (
        (
            ending_value
            - starting_value
        )
        / starting_value
    ) * 100

    daily_returns = (
        df[
            "normalised_equity"
        ]
        .pct_change()
        .dropna()
    )

    volatility = None
    sharpe = None

    if not daily_returns.empty:

        daily_std = (
            daily_returns.std()
        )

        volatility = (
            daily_std
            * (252 ** 0.5)
            * 100
        )

        if daily_std > 0:

            sharpe = (
                daily_returns.mean()
                / daily_std
            ) * (252 ** 0.5)

    max_drawdown = (
        calculate_drawdown(
            df[
                "normalised_equity"
            ]
        )
        .min()
    )

    return {
        "strategy": name,
        "status": "ok",
        "start_date": str(
            df["date"]
            .iloc[0]
            .date()
        ),
        "end_date": str(
            df["date"]
            .iloc[-1]
            .date()
        ),
        "starting_value": round(
            starting_value,
            2,
        ),
        "ending_value": round(
            ending_value,
            2,
        ),
        "profit_loss": round(
            ending_value
            - starting_value,
            2,
        ),
        "total_return_pct": round(
            total_return,
            2,
        ),
        "annualised_volatility_pct": (
            round(
                float(volatility),
                2,
            )
            if volatility is not None
            else None
        ),
        "sharpe_estimate": (
            round(
                float(sharpe),
                3,
            )
            if sharpe is not None
            else None
        ),
        "max_drawdown_pct": round(
            float(max_drawdown),
            2,
        ),
    }


# ============================================================
# REPORT GENERATOR
# ============================================================

def generate_report():

    print(
        "Loading portfolio histories..."
    )

    microcap_raw = (
        load_portfolio_history(
            MICROCAP_PATH
        )
    )

    titans_raw = (
        load_portfolio_history(
            TITANS_PATH
        )
    )

    microcap = (
        normalise_equity(
            microcap_raw
        )
        if not microcap_raw.empty
        else pd.DataFrame()
    )

    titans = (
        normalise_equity(
            titans_raw
        )
        if not titans_raw.empty
        else pd.DataFrame()
    )

    # --------------------------------------------------------
    # Find experiment date range
    # --------------------------------------------------------

    dates = []

    if not microcap.empty:
        dates.extend(
            microcap[
                "date"
            ].tolist()
        )

    if not titans.empty:
        dates.extend(
            titans[
                "date"
            ].tolist()
        )

    # --------------------------------------------------------
    # Download benchmarks
    # --------------------------------------------------------

    if dates:

        start_date = min(dates)

        end_date = max(dates)

        print(
            "Downloading S&P 500 benchmark..."
        )

        sp500 = get_benchmark(
            "^GSPC",
            start_date,
            end_date,
        )

        print(
            "Downloading Nasdaq-100 benchmark..."
        )

        nasdaq100 = get_benchmark(
            "^NDX",
            start_date,
            end_date,
        )

    else:

        sp500 = pd.DataFrame()

        nasdaq100 = pd.DataFrame()

    # --------------------------------------------------------
    # Charts
    # --------------------------------------------------------

    equity_chart = (
        create_equity_chart(
            microcap,
            titans,
            sp500,
            nasdaq100,
        )
    )

    drawdown_chart = (
        create_drawdown_chart(
            microcap,
            titans,
            sp500,
            nasdaq100,
        )
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = {

        "experiment": {
            "starting_capital_each": (
                STARTING_CAPITAL
            ),
            "portfolio_count": 2,
            "benchmarks": [
                "S&P 500",
                "Nasdaq-100",
            ],
        },

        "microcap_growth": (
            summary_stats(
                "Microcap Growth",
                microcap_raw,
            )
        ),

        "nasdaq_titan_growth": (
            summary_stats(
                "Nasdaq Titan Growth",
                titans_raw,
            )
        ),

        "sp500": (
            benchmark_stats(
                "S&P 500",
                sp500,
            )
        ),

        "nasdaq100": (
            benchmark_stats(
                "Nasdaq-100",
                nasdaq100,
            )
        ),
    }

    summary_path = (
        REPORT_ROOT
        / "performance_summary.json"
    )

    with open(
        summary_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------

    print()

    print(
        "Performance report generated."
    )

    print(
        f"Equity chart: {equity_chart}"
    )

    print(
        f"Drawdown chart: {drawdown_chart}"
    )

    print(
        f"Summary: {summary_path}"
    )

    print()

    print(
        "Tracked series:"
    )

    print(
        "1. Microcap Growth"
    )

    print(
        "2. Nasdaq Titan Growth"
    )

    print(
        "3. S&P 500"
    )

    print(
        "4. Nasdaq-100"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    generate_report()

