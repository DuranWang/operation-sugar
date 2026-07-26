"""
Month-Level Model Reporting

Create publication-style reporting figures for the seven
Operation Sugar month-level baseline models.

This module does not refit any model. It only reads the
locked comparison outputs produced by:

    python -m src.modeling.month_level_model_comparison

Figures:

1. LOSO RMSE comparison by harvest aggregation horizon
2. RMSE improvement relative to Block-Only OLS
3. Ridge alpha-boundary summary
4. Ridge effective weather degrees of freedom

The same model ordering is preserved across the two
seven-model figures so Matplotlib's default color cycle remains
consistent without hard-coded colors.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "month_level_baseline_results"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "docs"
    / "figures"
)

MODEL_COMPARISON_PATH = (
    INPUT_DIR
    / "month_level_model_comparison.csv"
)

RIDGE_DIAGNOSTICS_PATH = (
    INPUT_DIR
    / "month_level_ridge_diagnostics.csv"
)

RMSE_FIGURE_PATH = (
    FIGURE_DIR
    / "month_level_model_rmse_comparison.png"
)

IMPROVEMENT_FIGURE_PATH = (
    FIGURE_DIR
    / "month_level_model_improvement_vs_block.png"
)

RIDGE_BOUNDARY_FIGURE_PATH = (
    FIGURE_DIR
    / "month_level_ridge_boundary_diagnostics.png"
)

RIDGE_DF_FIGURE_PATH = (
    FIGURE_DIR
    / "month_level_ridge_effective_degrees_of_freedom.png"
)

HORIZONS = (
    1,
    2,
    3,
    4,
    5,
)

MODEL_ORDER = (
    "block_only_ols",
    "temperature_month_level_ridge",
    "aggregate_ols",
    "rainfall_month_level_ridge",
    "joint_month_level_ridge",
    "temperature_month_level_ols",
    "rainfall_month_level_ols",
)

RIDGE_MODEL_ORDER = (
    "temperature_month_level_ridge",
    "rainfall_month_level_ridge",
    "joint_month_level_ridge",
)

DISPLAY_LABELS = {
    "block_only_ols": "Block-Only OLS",
    "temperature_month_level_ridge": (
        "Temperature Month-Level Ridge"
    ),
    "aggregate_ols": "Aggregate Weather OLS",
    "rainfall_month_level_ridge": (
        "Rainfall Month-Level Ridge"
    ),
    "joint_month_level_ridge": (
        "Joint Month-Level Ridge"
    ),
    "temperature_month_level_ols": (
        "Temperature Month-Level OLS"
    ),
    "rainfall_month_level_ols": (
        "Rainfall Month-Level OLS"
    ),
}

RIDGE_DISPLAY_LABELS = {
    model: DISPLAY_LABELS[model]
    for model in RIDGE_MODEL_ORDER
}

REQUIRED_COMPARISON_COLUMNS = {
    "model",
    "horizon",
    "loso_rmse",
    "rmse_improvement_vs_block_percent",
}

REQUIRED_RIDGE_COLUMNS = {
    "model",
    "horizon",
    "minimum_alpha_boundary_fraction",
    "maximum_alpha_boundary_fraction",
    "weather_effective_df_mean",
    "weather_effective_df_median",
    "weather_effective_df_max",
}


def validate_expected_horizons(
    dataframe: pd.DataFrame,
    source_path: Path,
) -> None:
    """Validate that all expected horizons are present."""

    observed_horizons = set(
        pd.to_numeric(
            dataframe["horizon"],
            errors="raise",
        )
        .astype(int)
        .unique()
        .tolist()
    )

    expected_horizons = set(
        HORIZONS
    )

    if observed_horizons != expected_horizons:
        raise ValueError(
            f"Unexpected horizons in {source_path}: "
            f"observed={sorted(observed_horizons)}, "
            f"expected={sorted(expected_horizons)}"
        )


def validate_model_horizon_grid(
    dataframe: pd.DataFrame,
    expected_models: tuple[str, ...],
    source_path: Path,
) -> None:
    """Validate one row per model-horizon combination."""

    expected_pairs = {
        (
            model,
            horizon,
        )
        for model in expected_models
        for horizon in HORIZONS
    }

    observed_pairs = set(
        dataframe[
            [
                "model",
                "horizon",
            ]
        ]
        .itertuples(
            index=False,
            name=None,
        )
    )

    if observed_pairs != expected_pairs:
        missing_pairs = sorted(
            expected_pairs
            - observed_pairs
        )

        unexpected_pairs = sorted(
            observed_pairs
            - expected_pairs
        )

        raise ValueError(
            f"Unexpected model-horizon grid in "
            f"{source_path}. "
            f"Missing={missing_pairs}; "
            f"unexpected={unexpected_pairs}"
        )


def load_model_comparison() -> pd.DataFrame:
    """Load the locked seven-model comparison table."""

    if not MODEL_COMPARISON_PATH.exists():
        raise FileNotFoundError(
            "Model comparison output not found. Run "
            "`python -m "
            "src.modeling.month_level_model_comparison` "
            f"first: {MODEL_COMPARISON_PATH}"
        )

    dataframe = pd.read_csv(
        MODEL_COMPARISON_PATH
    )

    missing_columns = (
        REQUIRED_COMPARISON_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Model comparison is missing columns: "
            f"{sorted(missing_columns)}"
        )

    dataframe = dataframe.copy()

    dataframe["horizon"] = pd.to_numeric(
        dataframe["horizon"],
        errors="raise",
    ).astype(int)

    dataframe["loso_rmse"] = pd.to_numeric(
        dataframe["loso_rmse"],
        errors="raise",
    )

    dataframe[
        "rmse_improvement_vs_block_percent"
    ] = pd.to_numeric(
        dataframe[
            "rmse_improvement_vs_block_percent"
        ],
        errors="raise",
    )

    validate_expected_horizons(
        dataframe=dataframe,
        source_path=MODEL_COMPARISON_PATH,
    )

    validate_model_horizon_grid(
        dataframe=dataframe,
        expected_models=MODEL_ORDER,
        source_path=MODEL_COMPARISON_PATH,
    )

    if (
        dataframe["loso_rmse"] <= 0
    ).any():
        raise ValueError(
            "Model comparison contains non-positive RMSE."
        )

    dataframe["display_label"] = (
        dataframe["model"].map(
            DISPLAY_LABELS
        )
    )

    if dataframe["display_label"].isna().any():
        unknown_models = sorted(
            dataframe.loc[
                dataframe[
                    "display_label"
                ].isna(),
                "model",
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            f"Unknown model labels: {unknown_models}"
        )

    return dataframe


def load_ridge_diagnostics() -> pd.DataFrame:
    """Load the locked Ridge diagnostic summary."""

    if not RIDGE_DIAGNOSTICS_PATH.exists():
        raise FileNotFoundError(
            "Ridge diagnostic output not found. Run "
            "`python -m "
            "src.modeling.month_level_model_comparison` "
            f"first: {RIDGE_DIAGNOSTICS_PATH}"
        )

    dataframe = pd.read_csv(
        RIDGE_DIAGNOSTICS_PATH
    )

    missing_columns = (
        REQUIRED_RIDGE_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Ridge diagnostics are missing columns: "
            f"{sorted(missing_columns)}"
        )

    dataframe = dataframe.copy()

    dataframe["horizon"] = pd.to_numeric(
        dataframe["horizon"],
        errors="raise",
    ).astype(int)

    numeric_columns = (
        "minimum_alpha_boundary_fraction",
        "maximum_alpha_boundary_fraction",
        "weather_effective_df_mean",
        "weather_effective_df_median",
        "weather_effective_df_max",
    )

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="raise",
        )

    validate_expected_horizons(
        dataframe=dataframe,
        source_path=RIDGE_DIAGNOSTICS_PATH,
    )

    validate_model_horizon_grid(
        dataframe=dataframe,
        expected_models=RIDGE_MODEL_ORDER,
        source_path=RIDGE_DIAGNOSTICS_PATH,
    )

    boundary_columns = (
        "minimum_alpha_boundary_fraction",
        "maximum_alpha_boundary_fraction",
    )

    for column in boundary_columns:
        outside_unit_interval = (
            dataframe[column] < 0
        ) | (
            dataframe[column] > 1
        )

        if outside_unit_interval.any():
            raise ValueError(
                f"Ridge diagnostic column {column} "
                "contains values outside [0, 1]."
            )

    effective_df_columns = (
        "weather_effective_df_mean",
        "weather_effective_df_median",
        "weather_effective_df_max",
    )

    for column in effective_df_columns:
        if (
            dataframe[column] < 0
        ).any():
            raise ValueError(
                f"Ridge diagnostic column {column} "
                "contains negative values."
            )

    dataframe["display_label"] = (
        dataframe["model"].map(
            RIDGE_DISPLAY_LABELS
        )
    )

    if dataframe["display_label"].isna().any():
        unknown_models = sorted(
            dataframe.loc[
                dataframe[
                    "display_label"
                ].isna(),
                "model",
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            f"Unknown Ridge model labels: "
            f"{unknown_models}"
        )

    return dataframe


def create_rmse_comparison_figure(
    comparison_df: pd.DataFrame,
) -> None:
    """Plot LOSO RMSE by horizon for all seven models."""

    figure, axis = plt.subplots(
        figsize=(
            12,
            7,
        )
    )

    for model in MODEL_ORDER:
        model_data = (
            comparison_df.loc[
                comparison_df["model"].eq(
                    model
                )
            ]
            .sort_values(
                "horizon"
            )
        )

        axis.plot(
            model_data["horizon"],
            model_data["loso_rmse"]
            / 1_000_000,
            marker="o",
            label=DISPLAY_LABELS[model],
        )

    axis.set_title(
        "LOSO RMSE by Harvest Aggregation Horizon"
    )

    axis.set_xlabel(
        "Harvest aggregation horizon (h)"
    )

    axis.set_ylabel(
        "LOSO RMSE (million tonnes)"
    )

    axis.set_xticks(
        HORIZONS
    )

    axis.text(
        0.5,
        -0.14,
        (
            "Compare models within each horizon. "
            "Raw RMSE naturally increases as larger harvest "
            "blocks contain more tonnes."
        ),
        transform=axis.transAxes,
        ha="center",
    )

    axis.legend()

    figure.tight_layout()

    figure.savefig(
        RMSE_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )


def create_improvement_figure(
    comparison_df: pd.DataFrame,
) -> None:
    """
    Plot RMSE improvement relative to Block-Only OLS.

    Positive values indicate an improvement over Block-Only.
    Negative values indicate worse out-of-sample RMSE.
    Block-Only is included at zero so model colors remain
    consistent with the seven-model RMSE figure.
    """

    figure, axis = plt.subplots(
        figsize=(
            12,
            7,
        )
    )

    for model in MODEL_ORDER:
        model_data = (
            comparison_df.loc[
                comparison_df["model"].eq(
                    model
                )
            ]
            .sort_values(
                "horizon"
            )
        )

        axis.plot(
            model_data["horizon"],
            model_data[
                "rmse_improvement_vs_block_percent"
            ],
            marker="o",
            label=DISPLAY_LABELS[model],
        )

    axis.axhline(
        0,
        linewidth=1,
    )

    axis.set_title(
        "LOSO RMSE Improvement Relative to Block-Only OLS"
    )

    axis.set_xlabel(
        "Harvest aggregation horizon (h)"
    )

    axis.set_ylabel(
        "RMSE improvement versus Block-Only (%)"
    )

    axis.set_xticks(
        HORIZONS
    )

    axis.text(
        0.5,
        -0.14,
        (
            "Positive values beat Block-Only. "
            "All evaluated weather models remain below zero."
        ),
        transform=axis.transAxes,
        ha="center",
    )

    axis.legend()

    figure.tight_layout()

    figure.savefig(
        IMPROVEMENT_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )


def create_ridge_boundary_figure(
    ridge_df: pd.DataFrame,
) -> None:
    """
    Summarize minimum- and maximum-alpha boundary fractions.

    The figure uses cross-horizon averages. The observed
    fractions are constant across h=1,...,5 in the locked
    results, so repeating six horizontal lines adds no
    information.
    """

    summary = (
        ridge_df
        .groupby(
            [
                "model",
                "display_label",
            ],
            as_index=False,
        )
        .agg(
            minimum_boundary_mean=(
                "minimum_alpha_boundary_fraction",
                "mean",
            ),
            minimum_boundary_min=(
                "minimum_alpha_boundary_fraction",
                "min",
            ),
            minimum_boundary_max=(
                "minimum_alpha_boundary_fraction",
                "max",
            ),
            maximum_boundary_mean=(
                "maximum_alpha_boundary_fraction",
                "mean",
            ),
            maximum_boundary_min=(
                "maximum_alpha_boundary_fraction",
                "min",
            ),
            maximum_boundary_max=(
                "maximum_alpha_boundary_fraction",
                "max",
            ),
        )
    )

    for prefix in (
        "minimum_boundary",
        "maximum_boundary",
    ):
        if not np.allclose(
            summary[f"{prefix}_min"],
            summary[f"{prefix}_max"],
        ):
            raise ValueError(
                "Ridge boundary fractions vary across "
                "horizons. Restore a horizon-level plot "
                "before reporting these results."
            )

    summary["model_order"] = (
        summary["model"].map(
            {
                model: index
                for index, model in enumerate(
                    RIDGE_MODEL_ORDER
                )
            }
        )
    )

    summary = summary.sort_values(
        "model_order"
    )

    x_positions = np.arange(
        len(summary)
    )

    bar_width = 0.36

    figure, axis = plt.subplots(
        figsize=(
            11,
            7,
        )
    )

    maximum_bars = axis.bar(
        x_positions - bar_width / 2,
        summary[
            "maximum_boundary_mean"
        ]
        * 100,
        width=bar_width,
        label="Maximum alpha boundary",
    )

    minimum_bars = axis.bar(
        x_positions + bar_width / 2,
        summary[
            "minimum_boundary_mean"
        ]
        * 100,
        width=bar_width,
        label="Minimum alpha boundary",
    )

    axis.bar_label(
        maximum_bars,
        fmt="%.2f%%",
        padding=3,
    )

    axis.bar_label(
        minimum_bars,
        fmt="%.2f%%",
        padding=3,
    )

    axis.set_title(
        "Nested-LOSO Ridge Alpha Boundary Selection"
    )

    axis.set_ylabel(
        "Outer folds at alpha-grid boundary (%)"
    )

    axis.set_xticks(
        x_positions,
        summary["display_label"],
        rotation=12,
        ha="right",
    )

    axis.set_ylim(
        0,
        100,
    )

    axis.text(
        0.5,
        -0.18,
        (
            "Boundary fractions are identical across "
            "h=1,...,5 in the locked results."
        ),
        transform=axis.transAxes,
        ha="center",
    )

    axis.legend()

    figure.tight_layout()

    figure.savefig(
        RIDGE_BOUNDARY_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )


def create_ridge_effective_df_figure(
    ridge_df: pd.DataFrame,
) -> None:
    """
    Plot mean and maximum effective weather degrees of freedom.

    The median effective weather degrees of freedom is
    approximately zero for every Ridge model and horizon.
    Mean values show how influential folds affect the average;
    maximum values show the strongest retained complexity.
    """

    median_values = ridge_df[
        "weather_effective_df_median"
    ].to_numpy(
        dtype=float
    )

    if not np.allclose(
        median_values,
        0,
        atol=1e-5,
    ):
        raise ValueError(
            "Median effective weather degrees of freedom "
            "is no longer approximately zero. Restore the "
            "median series to the figure."
        )

    figure, axis = plt.subplots(
        figsize=(
            12,
            7,
        )
    )

    for model in RIDGE_MODEL_ORDER:
        model_data = (
            ridge_df.loc[
                ridge_df["model"].eq(
                    model
                )
            ]
            .sort_values(
                "horizon"
            )
        )

        axis.plot(
            model_data["horizon"],
            model_data[
                "weather_effective_df_mean"
            ],
            marker="o",
            label=(
                f"{RIDGE_DISPLAY_LABELS[model]} "
                "— mean"
            ),
        )

        axis.plot(
            model_data["horizon"],
            model_data[
                "weather_effective_df_max"
            ],
            marker="o",
            linestyle="--",
            label=(
                f"{RIDGE_DISPLAY_LABELS[model]} "
                "— maximum"
            ),
        )

    axis.axhline(
        0,
        linewidth=1,
    )

    axis.set_title(
        "Effective Weather Degrees of Freedom Across Outer Folds"
    )

    axis.set_xlabel(
        "Harvest aggregation horizon (h)"
    )

    axis.set_ylabel(
        "Effective weather degrees of freedom"
    )

    axis.set_xticks(
        HORIZONS
    )

    axis.set_ylim(
        bottom=0,
    )

    axis.text(
        0.5,
        -0.14,
        (
            "Median effective weather degrees of freedom "
            "is approximately zero for every Ridge model "
            "and horizon."
        ),
        transform=axis.transAxes,
        ha="center",
    )

    axis.legend()

    figure.tight_layout()

    figure.savefig(
        RIDGE_DF_FIGURE_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )


def main() -> None:
    """Generate all locked-model reporting figures."""

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison_df = (
        load_model_comparison()
    )

    ridge_df = (
        load_ridge_diagnostics()
    )

    print("=" * 76)
    print("Month-Level Model Reporting")
    print("=" * 76)

    create_rmse_comparison_figure(
        comparison_df
    )

    print(
        f"[OK] RMSE comparison: "
        f"{RMSE_FIGURE_PATH.name}"
    )

    create_improvement_figure(
        comparison_df
    )

    print(
        f"[OK] Block-only comparison: "
        f"{IMPROVEMENT_FIGURE_PATH.name}"
    )

    create_ridge_boundary_figure(
        ridge_df
    )

    print(
        f"[OK] Ridge boundary diagnostics: "
        f"{RIDGE_BOUNDARY_FIGURE_PATH.name}"
    )

    create_ridge_effective_df_figure(
        ridge_df
    )

    print(
        f"[OK] Ridge effective df: "
        f"{RIDGE_DF_FIGURE_PATH.name}"
    )

    print("=" * 76)
    print("Figures saved to:")
    print(FIGURE_DIR)
    print("=" * 76)


if __name__ == "__main__":
    main()