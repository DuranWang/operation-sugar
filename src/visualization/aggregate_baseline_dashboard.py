"""
Aggregate Baseline Comparison Dashboard

Compare two aggregate baseline specifications across
aggregation horizons h = 1, 2, 3, 4, 5:

1. block_only
   Harvest-block position fixed effects only.

2. weather_block
   Growing-season total rainfall, average temperature,
   and harvest-block position fixed effects.

The dashboard emphasizes the incremental out-of-sample
contribution of weather variables.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "aggregate_baseline"
    / "results"
)

SUMMARY_INPUT_PATH = (
    RESULTS_DIR
    / "aggregate_baseline_model_summary.csv"
)

COEFFICIENT_INPUT_PATH = (
    RESULTS_DIR
    / "aggregate_baseline_coefficients.csv"
)

COMPARISON_INPUT_PATH = (
    RESULTS_DIR
    / "aggregate_baseline_incremental_comparison.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "figures"
    / "aggregate_baseline_dashboard.png"
)

MODEL_LABELS = {
    "block_only": "Block Position Only",
    "weather_block": "Weather + Block Position",
}

WEATHER_FEATURE_LABELS = {
    "growing_season_total_rainfall": "Total Rainfall",
    "growing_season_average_temperature": "Average Temperature",
}

REQUIRED_SPECIFICATIONS = {
    "block_only",
    "weather_block",
}


def load_csv(
    input_path: Path,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Load one dashboard input dataset.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            f"{dataset_name} not found: {input_path}"
        )

    dataframe = pd.read_csv(
        input_path
    )

    if dataframe.empty:
        raise ValueError(
            f"{dataset_name} is empty."
        )

    return dataframe


def load_dashboard_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Load and validate all dashboard inputs.
    """

    summary_df = load_csv(
        SUMMARY_INPUT_PATH,
        "Aggregate baseline model summary",
    )

    coefficient_df = load_csv(
        COEFFICIENT_INPUT_PATH,
        "Aggregate baseline coefficients",
    )

    comparison_df = load_csv(
        COMPARISON_INPUT_PATH,
        "Incremental weather comparison",
    )

    summary_required_columns = {
        "specification",
        "horizon",
        "season_count",
        "observation_count",
        "cv_r_squared",
        "cv_normalized_rmse",
        "cv_normalized_mae",
    }

    coefficient_required_columns = {
        "specification",
        "horizon",
        "feature",
        "coefficient",
    }

    comparison_required_columns = {
        "horizon",
        "cv_r_squared_block_only",
        "cv_r_squared_weather_block",
        "cv_normalized_rmse_block_only",
        "cv_normalized_rmse_weather_block",
        "incremental_cv_r_squared",
        "incremental_cv_nrmse_improvement",
        "incremental_cv_nmae_improvement",
        "weather_improves_cv_r_squared",
        "weather_improves_cv_nrmse",
    }

    missing_summary_columns = (
        summary_required_columns
        - set(summary_df.columns)
    )

    missing_coefficient_columns = (
        coefficient_required_columns
        - set(coefficient_df.columns)
    )

    missing_comparison_columns = (
        comparison_required_columns
        - set(comparison_df.columns)
    )

    if missing_summary_columns:
        raise ValueError(
            "Model summary is missing columns: "
            f"{sorted(missing_summary_columns)}"
        )

    if missing_coefficient_columns:
        raise ValueError(
            "Coefficient dataset is missing columns: "
            f"{sorted(missing_coefficient_columns)}"
        )

    if missing_comparison_columns:
        raise ValueError(
            "Incremental comparison is missing columns: "
            f"{sorted(missing_comparison_columns)}"
        )

    observed_specifications = set(
        summary_df[
            "specification"
        ].unique()
    )

    missing_specifications = (
        REQUIRED_SPECIFICATIONS
        - observed_specifications
    )

    if missing_specifications:
        raise ValueError(
            "Model summary is missing specifications: "
            f"{sorted(missing_specifications)}"
        )

    return (
        summary_df.sort_values(
            [
                "horizon",
                "specification",
            ]
        ).reset_index(drop=True),
        coefficient_df.sort_values(
            [
                "horizon",
                "specification",
                "feature",
            ]
        ).reset_index(drop=True),
        comparison_df.sort_values(
            "horizon"
        ).reset_index(drop=True),
    )


def add_kpi_card(
    axis: plt.Axes,
    title: str,
    value: str,
    subtitle: str,
) -> None:
    """
    Draw one dashboard KPI card.
    """

    axis.set_xticks([])
    axis.set_yticks([])

    for spine in axis.spines.values():
        spine.set_visible(True)

    axis.text(
        0.5,
        0.75,
        title,
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        transform=axis.transAxes,
    )

    axis.text(
        0.5,
        0.45,
        value,
        ha="center",
        va="center",
        fontsize=21,
        fontweight="bold",
        transform=axis.transAxes,
    )

    axis.text(
        0.5,
        0.17,
        subtitle,
        ha="center",
        va="center",
        fontsize=8.5,
        transform=axis.transAxes,
    )


def add_line_labels(
    axis: plt.Axes,
    x_values: pd.Series,
    y_values: pd.Series,
    decimals: int = 3,
    vertical_offset: int = 7,
) -> None:
    """
    Add labels above line-chart observations.
    """

    for x_value, y_value in zip(
        x_values,
        y_values,
    ):
        axis.annotate(
            f"{y_value:.{decimals}f}",
            (
                x_value,
                y_value,
            ),
            textcoords="offset points",
            xytext=(
                0,
                vertical_offset,
            ),
            ha="center",
            fontsize=8,
        )


def add_bar_labels(
    axis: plt.Axes,
    bars,
    decimals: int = 3,
) -> None:
    """
    Add value labels to bar-chart observations.
    """

    for bar in bars:
        height = bar.get_height()

        vertical_offset = (
            3
            if height >= 0
            else -12
        )

        axis.annotate(
            f"{height:.{decimals}f}",
            (
                bar.get_x()
                + bar.get_width() / 2,
                height,
            ),
            textcoords="offset points",
            xytext=(
                0,
                vertical_offset,
            ),
            ha="center",
            fontsize=8,
        )


def prepare_summary_pivot(
    summary_df: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    """
    Pivot one performance metric by horizon and specification.
    """

    pivot_df = (
        summary_df
        .pivot(
            index="horizon",
            columns="specification",
            values=metric,
        )
        .sort_index()
    )

    missing_columns = (
        REQUIRED_SPECIFICATIONS
        - set(pivot_df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Metric {metric} is missing specifications: "
            f"{sorted(missing_columns)}"
        )

    return pivot_df


def prepare_weather_coefficients(
    coefficient_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep standardized weather coefficients from weather-block models.
    """

    weather_coefficients = coefficient_df.loc[
        coefficient_df[
            "specification"
        ].eq(
            "weather_block"
        )
        & coefficient_df[
            "feature"
        ].isin(
            WEATHER_FEATURE_LABELS
        )
    ].copy()

    if weather_coefficients.empty:
        raise ValueError(
            "No weather coefficients were found."
        )

    weather_coefficients[
        "feature_label"
    ] = (
        weather_coefficients[
            "feature"
        ]
        .map(
            WEATHER_FEATURE_LABELS
        )
    )

    return weather_coefficients


def build_dashboard(
    summary_df: pd.DataFrame,
    coefficient_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
) -> plt.Figure:
    """
    Build the aggregate baseline comparison dashboard.
    """

    horizons = comparison_df[
        "horizon"
    ]

    season_count = int(
        summary_df[
            "season_count"
        ].max()
    )

    improved_horizon_count = int(
        comparison_df[
            "weather_improves_cv_r_squared"
        ].sum()
    )

    best_incremental_r_squared_row = (
        comparison_df.loc[
            comparison_df[
                "incremental_cv_r_squared"
            ].idxmax()
        ]
    )

    best_nrmse_improvement_row = (
        comparison_df.loc[
            comparison_df[
                "incremental_cv_nrmse_improvement"
            ].idxmax()
        ]
    )

    r_squared_pivot = prepare_summary_pivot(
        summary_df=summary_df,
        metric="cv_r_squared",
    )

    nrmse_pivot = prepare_summary_pivot(
        summary_df=summary_df,
        metric="cv_normalized_rmse",
    )

    weather_coefficients = (
        prepare_weather_coefficients(
            coefficient_df
        )
    )

    coefficient_pivot = (
        weather_coefficients
        .pivot(
            index="horizon",
            columns="feature_label",
            values="coefficient",
        )
        .sort_index()
    )

    figure = plt.figure(
        figsize=(
            16,
            11,
        ),
        constrained_layout=True,
    )

    grid = figure.add_gridspec(
        nrows=4,
        ncols=12,
        height_ratios=[
            0.8,
            2.4,
            2.4,
            0.45,
        ],
    )

    kpi_1 = figure.add_subplot(
        grid[
            0,
            0:3,
        ]
    )

    kpi_2 = figure.add_subplot(
        grid[
            0,
            3:6,
        ]
    )

    kpi_3 = figure.add_subplot(
        grid[
            0,
            6:9,
        ]
    )

    kpi_4 = figure.add_subplot(
        grid[
            0,
            9:12,
        ]
    )

    r_squared_axis = figure.add_subplot(
        grid[
            1,
            0:6,
        ]
    )

    nrmse_axis = figure.add_subplot(
        grid[
            1,
            6:12,
        ]
    )

    incremental_axis = figure.add_subplot(
        grid[
            2,
            0:6,
        ]
    )

    coefficient_axis = figure.add_subplot(
        grid[
            2,
            6:12,
        ]
    )

    note_axis = figure.add_subplot(
        grid[
            3,
            :,
        ]
    )

    figure.suptitle(
        "Operation Sugar — Incremental Weather Contribution",
        fontsize=20,
        fontweight="bold",
    )

    figure.text(
        0.5,
        0.955,
        (
            "Weather + block-position fixed effects compared with "
            "a block-position-only benchmark | "
            "Leave-one-season-out validation"
        ),
        ha="center",
        fontsize=10.5,
    )

    add_kpi_card(
        axis=kpi_1,
        title="Best Incremental CV R²",
        value=(
            f"{best_incremental_r_squared_row['incremental_cv_r_squared']:+.3f}"
        ),
        subtitle=(
            f"h = "
            f"{int(best_incremental_r_squared_row['horizon'])}"
        ),
    )

    add_kpi_card(
        axis=kpi_2,
        title="Best CV NRMSE Improvement",
        value=(
            f"{best_nrmse_improvement_row['incremental_cv_nrmse_improvement']:+.3f}"
        ),
        subtitle=(
            f"h = "
            f"{int(best_nrmse_improvement_row['horizon'])}"
        ),
    )

    add_kpi_card(
        axis=kpi_3,
        title="Horizons Improved",
        value=(
            f"{improved_horizon_count}/"
            f"{len(comparison_df)}"
        ),
        subtitle="Positive incremental CV R²",
    )

    add_kpi_card(
        axis=kpi_4,
        title="Historical Seasons",
        value=str(
            season_count
        ),
        subtitle="Complete São Paulo seasons",
    )

    for specification in [
        "block_only",
        "weather_block",
    ]:
        r_squared_axis.plot(
            r_squared_pivot.index,
            r_squared_pivot[
                specification
            ],
            marker="o",
            label=MODEL_LABELS[
                specification
            ],
        )

    add_line_labels(
        axis=r_squared_axis,
        x_values=r_squared_pivot.index,
        y_values=r_squared_pivot[
            "weather_block"
        ],
    )

    r_squared_axis.set_title(
        "LOSO-CV R² by Model Specification",
        fontweight="bold",
    )

    r_squared_axis.set_xlabel(
        "Aggregation horizon h"
    )

    r_squared_axis.set_ylabel(
        "Cross-validated R²"
    )

    r_squared_axis.set_xticks(
        r_squared_pivot.index
    )

    r_squared_axis.grid(
        alpha=0.25
    )

    r_squared_axis.legend(
        frameon=False
    )

    for specification in [
        "block_only",
        "weather_block",
    ]:
        nrmse_axis.plot(
            nrmse_pivot.index,
            nrmse_pivot[
                specification
            ],
            marker="o",
            label=MODEL_LABELS[
                specification
            ],
        )

    add_line_labels(
        axis=nrmse_axis,
        x_values=nrmse_pivot.index,
        y_values=nrmse_pivot[
            "weather_block"
        ],
    )

    nrmse_axis.set_title(
        "LOSO-CV Normalized RMSE",
        fontweight="bold",
    )

    nrmse_axis.set_xlabel(
        "Aggregation horizon h"
    )

    nrmse_axis.set_ylabel(
        "Normalized RMSE"
    )

    nrmse_axis.set_xticks(
        nrmse_pivot.index
    )

    nrmse_axis.grid(
        alpha=0.25
    )

    nrmse_axis.legend(
        frameon=False
    )

    bar_width = 0.34

    horizon_positions = np.arange(
        len(
            horizons
        )
    )

    r_squared_bars = incremental_axis.bar(
        horizon_positions
        - bar_width / 2,
        comparison_df[
            "incremental_cv_r_squared"
        ],
        width=bar_width,
        label="Incremental CV R²",
    )

    nrmse_bars = incremental_axis.bar(
        horizon_positions
        + bar_width / 2,
        comparison_df[
            "incremental_cv_nrmse_improvement"
        ],
        width=bar_width,
        label="CV NRMSE Improvement",
    )

    incremental_axis.axhline(
        0,
        linewidth=1,
    )

    add_bar_labels(
        axis=incremental_axis,
        bars=r_squared_bars,
    )

    add_bar_labels(
        axis=incremental_axis,
        bars=nrmse_bars,
    )

    incremental_axis.set_title(
        "Incremental Out-of-Sample Weather Contribution",
        fontweight="bold",
    )

    incremental_axis.set_xlabel(
        "Aggregation horizon h"
    )

    incremental_axis.set_ylabel(
        "Improvement over block-only model"
    )

    incremental_axis.set_xticks(
        horizon_positions
    )

    incremental_axis.set_xticklabels(
        horizons.astype(int)
    )

    incremental_axis.grid(
        axis="y",
        alpha=0.25,
    )

    incremental_axis.legend(
        frameon=False
    )

    for feature_name in coefficient_pivot.columns:
        coefficient_axis.plot(
            coefficient_pivot.index,
            coefficient_pivot[
                feature_name
            ]
            / 1_000_000,
            marker="o",
            label=feature_name,
        )

    coefficient_axis.axhline(
        0,
        linewidth=1,
    )

    coefficient_axis.set_title(
        "Weather Coefficients in Weather + Block Models",
        fontweight="bold",
    )

    coefficient_axis.set_xlabel(
        "Aggregation horizon h"
    )

    coefficient_axis.set_ylabel(
        "Change in block crush\n"
        "per 1 SD predictor increase "
        "(million tonnes)"
    )

    coefficient_axis.set_xticks(
        coefficient_pivot.index
    )

    coefficient_axis.grid(
        alpha=0.25
    )

    coefficient_axis.legend(
        frameon=False
    )

    note_axis.axis(
        "off"
    )

    note_axis.text(
        0.5,
        0.62,
        (
            "Positive incremental CV R² means weather adds "
            "out-of-sample explanatory power beyond the historical "
            "harvest calendar. Positive NRMSE improvement means "
            "weather reduces normalized prediction error."
        ),
        ha="center",
        va="center",
        fontsize=9,
        wrap=True,
    )

    note_axis.text(
        0.5,
        0.18,
        (
            "Coefficient magnitudes should not be compared mechanically "
            "across horizons because the target block contains more "
            "crushing as h increases. Coefficient direction and "
            "incremental validation performance are more informative."
        ),
        ha="center",
        va="center",
        fontsize=8.5,
        wrap=True,
    )

    return figure


def main() -> None:
    """
    Build and save the aggregate baseline comparison dashboard.
    """

    (
        summary_df,
        coefficient_df,
        comparison_df,
    ) = load_dashboard_data()

    figure = build_dashboard(
        summary_df=summary_df,
        coefficient_df=coefficient_df,
        comparison_df=comparison_df,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.savefig(
        OUTPUT_PATH,
        dpi=220,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )

    print(
        "=" * 72
    )

    print(
        "Aggregate Baseline Comparison Dashboard"
    )

    print(
        "=" * 72
    )

    print(
        f"Dashboard saved successfully: {OUTPUT_PATH}"
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()