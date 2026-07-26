"""
Season-Total Aggregate Baseline Dashboard

Visualize whether aggregate growing-season weather improves
leave-one-season-out prediction of complete-season São Paulo
sugarcane crushing relative to a mean-only benchmark.

Dashboard components:

- incremental cross-validated performance;
- mean-only versus weather-model performance;
- leave-one-season-out predictions by season;
- actual versus predicted season-total crushing;
- standardized weather coefficients.
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
    / "season_total_results"
)

SUMMARY_INPUT_PATH = (
    RESULTS_DIR
    / "season_total_model_summary.csv"
)

COEFFICIENT_INPUT_PATH = (
    RESULTS_DIR
    / "season_total_coefficients.csv"
)

PREDICTION_INPUT_PATH = (
    RESULTS_DIR
    / "season_total_predictions.csv"
)

COMPARISON_INPUT_PATH = (
    RESULTS_DIR
    / "season_total_incremental_comparison.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "figures"
    / "season_total_baseline_dashboard.png"
)

MODEL_LABELS = {
    "mean_only": "Mean-only benchmark",
    "weather": "Aggregate weather",
}

WEATHER_FEATURE_LABELS = {
    "growing_season_total_rainfall": "Total rainfall",
    "growing_season_average_temperature": "Average temperature",
}

REQUIRED_SPECIFICATIONS = {
    "mean_only",
    "weather",
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
    pd.DataFrame,
]:
    """
    Load and validate all season-total dashboard inputs.
    """

    summary_df = load_csv(
        SUMMARY_INPUT_PATH,
        "Season-total model summary",
    )

    coefficient_df = load_csv(
        COEFFICIENT_INPUT_PATH,
        "Season-total coefficients",
    )

    prediction_df = load_csv(
        PREDICTION_INPUT_PATH,
        "Season-total predictions",
    )

    comparison_df = load_csv(
        COMPARISON_INPUT_PATH,
        "Season-total incremental comparison",
    )

    summary_required_columns = {
        "specification",
        "season_count",
        "observation_count",
        "in_sample_r_squared",
        "cv_r_squared",
        "cv_rmse_tonnes",
        "cv_mae_tonnes",
        "cv_normalized_rmse",
        "cv_normalized_mae",
    }

    coefficient_required_columns = {
        "specification",
        "feature",
        "coefficient",
    }

    prediction_required_columns = {
        "season",
        "season_total_crush_tonnes",
        "predicted_season_total_crush_tonnes",
        "residual_tonnes",
        "specification",
        "evaluation_type",
    }

    comparison_required_columns = {
        "cv_r_squared_mean_only",
        "cv_r_squared_weather",
        "cv_normalized_rmse_mean_only",
        "cv_normalized_rmse_weather",
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

    missing_prediction_columns = (
        prediction_required_columns
        - set(prediction_df.columns)
    )

    missing_comparison_columns = (
        comparison_required_columns
        - set(comparison_df.columns)
    )

    if missing_summary_columns:
        raise ValueError(
            "Season-total summary is missing columns: "
            f"{sorted(missing_summary_columns)}"
        )

    if missing_coefficient_columns:
        raise ValueError(
            "Season-total coefficient dataset is missing columns: "
            f"{sorted(missing_coefficient_columns)}"
        )

    if missing_prediction_columns:
        raise ValueError(
            "Season-total prediction dataset is missing columns: "
            f"{sorted(missing_prediction_columns)}"
        )

    if missing_comparison_columns:
        raise ValueError(
            "Season-total comparison is missing columns: "
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
            "Season-total summary is missing specifications: "
            f"{sorted(missing_specifications)}"
        )

    return (
        summary_df.sort_values(
            "specification"
        ).reset_index(drop=True),
        coefficient_df.sort_values(
            [
                "specification",
                "feature",
            ]
        ).reset_index(drop=True),
        prediction_df.sort_values(
            [
                "evaluation_type",
                "specification",
                "season",
            ]
        ).reset_index(drop=True),
        comparison_df.reset_index(drop=True),
    )


def add_kpi_card(
    axis: plt.Axes,
    title: str,
    value: str,
    subtitle: str,
) -> None:
    """
    Draw one KPI card.
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


def add_bar_labels(
    axis: plt.Axes,
    bars,
    decimals: int = 3,
) -> None:
    """
    Add labels to bars.
    """

    for bar in bars:
        height = bar.get_height()

        vertical_offset = (
            4
            if height >= 0
            else -14
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


def get_summary_row(
    summary_df: pd.DataFrame,
    specification: str,
) -> pd.Series:
    """
    Return one model-summary row.
    """

    matching_rows = summary_df.loc[
        summary_df[
            "specification"
        ].eq(
            specification
        )
    ]

    if len(matching_rows) != 1:
        raise ValueError(
            "Expected exactly one summary row for "
            f"{specification}, found {len(matching_rows)}."
        )

    return matching_rows.iloc[0]


def prepare_cv_predictions(
    prediction_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep leave-one-season-out predictions.
    """

    cv_prediction_df = prediction_df.loc[
        prediction_df[
            "evaluation_type"
        ].eq(
            "leave_one_season_out"
        )
    ].copy()

    if cv_prediction_df.empty:
        raise ValueError(
            "No leave-one-season-out season-total predictions found."
        )

    duplicate_rows = cv_prediction_df.duplicated(
        subset=[
            "season",
            "specification",
        ],
        keep=False,
    )

    if duplicate_rows.any():
        raise ValueError(
            "Season-total CV predictions contain duplicate "
            "season-specification rows."
        )

    return (
        cv_prediction_df
        .sort_values(
            [
                "season",
                "specification",
            ]
        )
        .reset_index(drop=True)
    )


def prepare_weather_coefficients(
    coefficient_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep standardized aggregate-weather coefficients.
    """

    weather_coefficient_df = coefficient_df.loc[
        coefficient_df[
            "specification"
        ].eq(
            "weather"
        )
        & coefficient_df[
            "feature"
        ].isin(
            WEATHER_FEATURE_LABELS
        )
    ].copy()

    if weather_coefficient_df.empty:
        raise ValueError(
            "No season-total weather coefficients found."
        )

    weather_coefficient_df[
        "feature_label"
    ] = (
        weather_coefficient_df[
            "feature"
        ]
        .map(
            WEATHER_FEATURE_LABELS
        )
    )

    weather_coefficient_df[
        "coefficient_million_tonnes"
    ] = (
        weather_coefficient_df[
            "coefficient"
        ]
        / 1_000_000
    )

    return weather_coefficient_df


def build_dashboard(
    summary_df: pd.DataFrame,
    coefficient_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
) -> plt.Figure:
    """
    Build the season-total aggregate baseline dashboard.
    """

    if len(comparison_df) != 1:
        raise ValueError(
            "Season-total incremental comparison must contain "
            "exactly one row."
        )

    comparison_row = comparison_df.iloc[0]

    mean_summary = get_summary_row(
        summary_df=summary_df,
        specification="mean_only",
    )

    weather_summary = get_summary_row(
        summary_df=summary_df,
        specification="weather",
    )

    cv_prediction_df = prepare_cv_predictions(
        prediction_df
    )

    weather_coefficient_df = (
        prepare_weather_coefficients(
            coefficient_df
        )
    )

    season_count = int(
        weather_summary[
            "season_count"
        ]
    )

    weather_improves = bool(
        comparison_row[
            "weather_improves_cv_r_squared"
        ]
    )

    preferred_model = (
        "Aggregate weather"
        if weather_improves
        else "Mean-only"
    )

    mean_predictions = cv_prediction_df.loc[
        cv_prediction_df[
            "specification"
        ].eq(
            "mean_only"
        )
    ].copy()

    weather_predictions = cv_prediction_df.loc[
        cv_prediction_df[
            "specification"
        ].eq(
            "weather"
        )
    ].copy()

    if (
        set(
            mean_predictions[
                "season"
            ]
        )
        != set(
            weather_predictions[
                "season"
            ]
        )
    ):
        raise ValueError(
            "Mean-only and weather predictions contain "
            "different season sets."
        )

    prediction_comparison = (
        mean_predictions[
            [
                "season",
                "season_total_crush_tonnes",
                "predicted_season_total_crush_tonnes",
                "residual_tonnes",
            ]
        ]
        .rename(
            columns={
                "predicted_season_total_crush_tonnes": (
                    "mean_only_prediction"
                ),
                "residual_tonnes": (
                    "mean_only_residual"
                ),
            }
        )
        .merge(
            weather_predictions[
                [
                    "season",
                    "predicted_season_total_crush_tonnes",
                    "residual_tonnes",
                ]
            ].rename(
                columns={
                    "predicted_season_total_crush_tonnes": (
                        "weather_prediction"
                    ),
                    "residual_tonnes": (
                        "weather_residual"
                    ),
                }
            ),
            on="season",
            how="inner",
            validate="one_to_one",
        )
        .sort_values(
            "season"
        )
        .reset_index(drop=True)
    )

    prediction_comparison[
        "actual_million_tonnes"
    ] = (
        prediction_comparison[
            "season_total_crush_tonnes"
        ]
        / 1_000_000
    )

    prediction_comparison[
        "mean_only_prediction_million_tonnes"
    ] = (
        prediction_comparison[
            "mean_only_prediction"
        ]
        / 1_000_000
    )

    prediction_comparison[
        "weather_prediction_million_tonnes"
    ] = (
        prediction_comparison[
            "weather_prediction"
        ]
        / 1_000_000
    )

    prediction_comparison[
        "mean_only_residual_million_tonnes"
    ] = (
        prediction_comparison[
            "mean_only_residual"
        ]
        / 1_000_000
    )

    prediction_comparison[
        "weather_residual_million_tonnes"
    ] = (
        prediction_comparison[
            "weather_residual"
        ]
        / 1_000_000
    )

    figure = plt.figure(
        figsize=(
            16,
            12,
        ),
        constrained_layout=True,
    )

    grid = figure.add_gridspec(
        nrows=4,
        ncols=12,
        height_ratios=[
            0.8,
            2.5,
            2.5,
            0.55,
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

    performance_axis = figure.add_subplot(
        grid[
            1,
            0:5,
        ]
    )

    prediction_axis = figure.add_subplot(
        grid[
            1,
            5:12,
        ]
    )

    residual_axis = figure.add_subplot(
        grid[
            2,
            0:7,
        ]
    )

    coefficient_axis = figure.add_subplot(
        grid[
            2,
            7:12,
        ]
    )

    note_axis = figure.add_subplot(
        grid[
            3,
            :,
        ]
    )

    figure.suptitle(
        "Operation Sugar — Season-Total Aggregate Weather Baseline",
        fontsize=20,
        fontweight="bold",
    )

    figure.text(
        0.5,
        0.955,
        (
            "Complete-season São Paulo crushing | "
            "Aggregate rainfall and temperature versus "
            "mean-only benchmark | "
            "Leave-one-season-out validation"
        ),
        ha="center",
        fontsize=10.5,
    )

    add_kpi_card(
        axis=kpi_1,
        title="Incremental CV R²",
        value=(
            f"{comparison_row['incremental_cv_r_squared']:+.3f}"
        ),
        subtitle="Weather minus mean-only",
    )

    add_kpi_card(
        axis=kpi_2,
        title="CV NRMSE Improvement",
        value=(
            f"{comparison_row['incremental_cv_nrmse_improvement']:+.3f}"
        ),
        subtitle="Positive means lower error",
    )

    add_kpi_card(
        axis=kpi_3,
        title="Preferred CV Model",
        value=preferred_model,
        subtitle="Based on LOSO-CV R²",
    )

    add_kpi_card(
        axis=kpi_4,
        title="Historical Seasons",
        value=str(
            season_count
        ),
        subtitle="Complete São Paulo seasons",
    )

    model_positions = np.arange(
        2
    )

    bar_width = 0.36

    r_squared_values = [
        mean_summary[
            "cv_r_squared"
        ],
        weather_summary[
            "cv_r_squared"
        ],
    ]

    nrmse_values = [
        mean_summary[
            "cv_normalized_rmse"
        ],
        weather_summary[
            "cv_normalized_rmse"
        ],
    ]

    r_squared_bars = performance_axis.bar(
        model_positions
        - bar_width / 2,
        r_squared_values,
        width=bar_width,
        label="CV R²",
    )

    nrmse_bars = performance_axis.bar(
        model_positions
        + bar_width / 2,
        nrmse_values,
        width=bar_width,
        label="CV NRMSE",
    )

    performance_axis.axhline(
        0,
        linewidth=1,
    )

    add_bar_labels(
        axis=performance_axis,
        bars=r_squared_bars,
    )

    add_bar_labels(
        axis=performance_axis,
        bars=nrmse_bars,
    )

    performance_axis.set_title(
        "Out-of-Sample Model Comparison",
        fontweight="bold",
    )

    performance_axis.set_ylabel(
        "Metric value"
    )

    performance_axis.set_xticks(
        model_positions
    )

    performance_axis.set_xticklabels(
        [
            MODEL_LABELS[
                "mean_only"
            ],
            MODEL_LABELS[
                "weather"
            ],
        ]
    )

    performance_axis.grid(
        axis="y",
        alpha=0.25,
    )

    performance_axis.legend(
        frameon=False
    )

    seasons = prediction_comparison[
        "season"
    ]

    prediction_axis.plot(
        seasons,
        prediction_comparison[
            "actual_million_tonnes"
        ],
        marker="o",
        linewidth=2,
        label="Actual",
    )

    prediction_axis.plot(
        seasons,
        prediction_comparison[
            "mean_only_prediction_million_tonnes"
        ],
        marker="o",
        label="Mean-only prediction",
    )

    prediction_axis.plot(
        seasons,
        prediction_comparison[
            "weather_prediction_million_tonnes"
        ],
        marker="o",
        label="Weather prediction",
    )

    prediction_axis.set_title(
        "LOSO-CV Season-Total Predictions",
        fontweight="bold",
    )

    prediction_axis.set_xlabel(
        "Harvest season"
    )

    prediction_axis.set_ylabel(
        "Season-total crush (million tonnes)"
    )

    prediction_axis.tick_params(
        axis="x",
        rotation=45,
    )

    prediction_axis.grid(
        alpha=0.25
    )

    prediction_axis.legend(
        frameon=False
    )

    residual_axis.axhline(
        0,
        linewidth=1,
    )

    residual_axis.plot(
        seasons,
        prediction_comparison[
            "mean_only_residual_million_tonnes"
        ],
        marker="o",
        label="Mean-only residual",
    )

    residual_axis.plot(
        seasons,
        prediction_comparison[
            "weather_residual_million_tonnes"
        ],
        marker="o",
        label="Weather residual",
    )

    residual_axis.set_title(
        "LOSO-CV Residuals by Harvest Season",
        fontweight="bold",
    )

    residual_axis.set_xlabel(
        "Harvest season"
    )

    residual_axis.set_ylabel(
        "Actual minus predicted "
        "(million tonnes)"
    )

    residual_axis.tick_params(
        axis="x",
        rotation=45,
    )

    residual_axis.grid(
        alpha=0.25
    )

    residual_axis.legend(
        frameon=False
    )

    coefficient_bars = coefficient_axis.bar(
        weather_coefficient_df[
            "feature_label"
        ],
        weather_coefficient_df[
            "coefficient_million_tonnes"
        ],
    )

    coefficient_axis.axhline(
        0,
        linewidth=1,
    )

    add_bar_labels(
        axis=coefficient_axis,
        bars=coefficient_bars,
        decimals=2,
    )

    coefficient_axis.set_title(
        "Standardized Aggregate-Weather Coefficients",
        fontweight="bold",
    )

    coefficient_axis.set_ylabel(
        "Change in season-total crush\n"
        "per 1 SD predictor increase "
        "(million tonnes)"
    )

    coefficient_axis.tick_params(
        axis="x",
        rotation=15,
    )

    coefficient_axis.grid(
        axis="y",
        alpha=0.25,
    )

    note_axis.axis(
        "off"
    )

    note_axis.text(
        0.5,
        0.68,
        (
            "Positive incremental CV R² means aggregate weather "
            "provides out-of-sample explanatory power beyond the "
            "training-season mean. Positive NRMSE improvement means "
            "aggregate weather lowers normalized prediction error."
        ),
        ha="center",
        va="center",
        fontsize=9,
        wrap=True,
    )

    note_axis.text(
        0.5,
        0.24,
        (
            "Weather coefficients are estimated from the full sample "
            "after standardizing rainfall and temperature. They describe "
            "association, not causal effects. LOSO-CV performance is the "
            "primary criterion for evaluating predictive value."
        ),
        ha="center",
        va="center",
        fontsize=8.5,
        wrap=True,
    )

    return figure


def main() -> None:
    """
    Build and save the season-total baseline dashboard.
    """

    (
        summary_df,
        coefficient_df,
        prediction_df,
        comparison_df,
    ) = load_dashboard_data()

    figure = build_dashboard(
        summary_df=summary_df,
        coefficient_df=coefficient_df,
        prediction_df=prediction_df,
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
        "Season-Total Aggregate Baseline Dashboard"
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