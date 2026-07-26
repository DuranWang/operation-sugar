"""
Month-Level Model Comparison

Implementation version: aggregate-schema-fix-v2

Combine and compare the seven Operation Sugar baseline models
for harvest aggregation horizons h = 1, 2, 3, 4, 5.

Models:

1. Existing Aggregate OLS
2. Block-Only OLS
3. Rainfall Month-Level OLS
4. Rainfall Month-Level Ridge
5. Temperature Month-Level OLS
6. Temperature Month-Level Ridge
7. Joint Month-Level Ridge

The comparison reports:

- LOSO RMSE, MAE, and R-squared
- Per-horizon model rankings
- Improvement relative to Block-Only OLS
- Distance from the best model at each horizon
- Ridge alpha-boundary and effective-degree-of-freedom diagnostics
- Overall rankings across horizons
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.modeling.aggregate_baseline_data import HORIZONS


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODELING_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
)

MONTH_LEVEL_RESULTS_DIR = (
    MODELING_DIR
    / "month_level_baseline_results"
)

OUTPUT_DIR = MONTH_LEVEL_RESULTS_DIR

COMPARISON_OUTPUT_PATH = (
    OUTPUT_DIR
    / "month_level_model_comparison.csv"
)

OVERALL_RANKING_OUTPUT_PATH = (
    OUTPUT_DIR
    / "month_level_model_overall_ranking.csv"
)

RIDGE_DIAGNOSTICS_OUTPUT_PATH = (
    OUTPUT_DIR
    / "month_level_ridge_diagnostics.csv"
)

BEST_MODEL_OUTPUT_PATH = (
    OUTPUT_DIR
    / "month_level_best_model_by_horizon.csv"
)

REQUIRED_SUMMARY_COLUMNS = {
    "horizon",
    "loso_rmse",
    "loso_mae",
    "loso_r_squared",
}

REQUIRED_RIDGE_DIAGNOSTIC_COLUMNS = {
    "horizon",
    "held_out_season",
    "selected_alpha",
    "selected_alpha_at_minimum_grid",
    "selected_alpha_at_maximum_grid",
    "weather_effective_degrees_of_freedom",
}

AGGREGATE_SUMMARY_PATH = (
    MODELING_DIR
    / "aggregate_baseline"
    / "results"
    / "aggregate_baseline_model_summary.csv"
)

AGGREGATE_SPECIFICATION = "weather_block"


@dataclass(frozen=True)
class ModelSpecification:
    """Describe one model summary and optional Ridge diagnostics."""

    model: str
    model_label: str
    model_family: str
    model_order: int
    summary_path: Path | None
    diagnostics_path: Path | None = None


def resolve_aggregate_summary_path() -> Path:
    """Return the confirmed legacy Aggregate OLS summary."""

    if not AGGREGATE_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            "Aggregate OLS summary could not be found: "
            f"{AGGREGATE_SUMMARY_PATH}"
        )

    return AGGREGATE_SUMMARY_PATH


def get_model_specifications() -> tuple[
    ModelSpecification,
    ...,
]:
    """Build the ordered seven-model specification."""

    aggregate_summary_path = (
        resolve_aggregate_summary_path()
    )

    return (
        ModelSpecification(
            model="aggregate_ols",
            model_label="Existing Aggregate OLS",
            model_family="aggregate_ols",
            model_order=1,
            summary_path=aggregate_summary_path,
        ),
        ModelSpecification(
            model="block_only_ols",
            model_label="Block-Only OLS",
            model_family="block_only_ols",
            model_order=2,
            summary_path=(
                MONTH_LEVEL_RESULTS_DIR
                / "block_only_ols_summary.csv"
            ),
        ),
        ModelSpecification(
            model="rainfall_month_level_ols",
            model_label="Rainfall Month-Level OLS",
            model_family="month_level_ols",
            model_order=3,
            summary_path=(
                MONTH_LEVEL_RESULTS_DIR
                / "rainfall_month_level_ols_summary.csv"
            ),
        ),
        ModelSpecification(
            model="rainfall_month_level_ridge",
            model_label="Rainfall Month-Level Ridge",
            model_family="month_level_ridge",
            model_order=4,
            summary_path=(
                MONTH_LEVEL_RESULTS_DIR
                / "rainfall_month_level_ridge_summary.csv"
            ),
            diagnostics_path=(
                MONTH_LEVEL_RESULTS_DIR
                / (
                    "rainfall_month_level_ridge_"
                    "fold_diagnostics.csv"
                )
            ),
        ),
        ModelSpecification(
            model="temperature_month_level_ols",
            model_label="Temperature Month-Level OLS",
            model_family="month_level_ols",
            model_order=5,
            summary_path=(
                MONTH_LEVEL_RESULTS_DIR
                / "temperature_month_level_ols_summary.csv"
            ),
        ),
        ModelSpecification(
            model="temperature_month_level_ridge",
            model_label="Temperature Month-Level Ridge",
            model_family="month_level_ridge",
            model_order=6,
            summary_path=(
                MONTH_LEVEL_RESULTS_DIR
                / "temperature_month_level_ridge_summary.csv"
            ),
            diagnostics_path=(
                MONTH_LEVEL_RESULTS_DIR
                / (
                    "temperature_month_level_ridge_"
                    "fold_diagnostics.csv"
                )
            ),
        ),
        ModelSpecification(
            model="joint_month_level_ridge",
            model_label="Joint Month-Level Ridge",
            model_family="month_level_ridge",
            model_order=7,
            summary_path=(
                MONTH_LEVEL_RESULTS_DIR
                / "joint_month_level_ridge_summary.csv"
            ),
            diagnostics_path=(
                MONTH_LEVEL_RESULTS_DIR
                / (
                    "joint_month_level_ridge_"
                    "fold_diagnostics.csv"
                )
            ),
        ),
    )


def validate_horizons(
    dataframe: pd.DataFrame,
    source_path: Path,
) -> None:
    """Validate one summary or diagnostics horizon set."""

    observed_horizons = set(
        pd.to_numeric(
            dataframe["horizon"],
            errors="raise",
        )
        .astype(int)
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


def load_model_summary(
    specification: ModelSpecification,
) -> pd.DataFrame:
    """Load and standardize one model summary."""

    if specification.summary_path is None:
        raise ValueError(
            f"Summary path is missing for "
            f"{specification.model}."
        )

    if not specification.summary_path.exists():
        raise FileNotFoundError(
            "Required model summary not found: "
            f"{specification.summary_path}"
        )

    dataframe = pd.read_csv(
        specification.summary_path
    )

    if dataframe.empty:
        raise ValueError(
            f"Model summary is empty: "
            f"{specification.summary_path}"
        )

    if specification.model == "aggregate_ols":
        required_legacy_columns = {
            "specification",
            "horizon",
            "season_count",
            "observation_count",
            "blocks_per_season",
            "cv_r_squared",
            "cv_rmse_tonnes",
            "cv_mae_tonnes",
        }

        missing_columns = (
            required_legacy_columns
            - set(dataframe.columns)
        )

        if missing_columns:
            raise ValueError(
                f"Legacy Aggregate OLS summary "
                f"{specification.summary_path} "
                f"is missing columns: "
                f"{sorted(missing_columns)}"
            )

        dataframe = dataframe.loc[
            dataframe["specification"].eq(
                AGGREGATE_SPECIFICATION
            )
        ].copy()

        if dataframe.empty:
            raise ValueError(
                "Legacy Aggregate OLS summary does not "
                f"contain specification="
                f"{AGGREGATE_SPECIFICATION!r}."
            )

        dataframe = dataframe.rename(
            columns={
                "cv_rmse_tonnes": "loso_rmse",
                "cv_mae_tonnes": "loso_mae",
                "cv_r_squared": "loso_r_squared",
            }
        )

        dataframe["weather_predictor_count"] = 2

    else:
        missing_columns = (
            REQUIRED_SUMMARY_COLUMNS
            - set(dataframe.columns)
        )

        if missing_columns:
            raise ValueError(
                f"Model summary "
                f"{specification.summary_path} "
                f"is missing columns: "
                f"{sorted(missing_columns)}"
            )

    if dataframe["horizon"].duplicated().any():
        duplicate_horizons = (
            dataframe.loc[
                dataframe["horizon"].duplicated(
                    keep=False
                ),
                "horizon",
            ]
            .tolist()
        )

        raise ValueError(
            f"Model summary {specification.summary_path} "
            "contains duplicate horizons: "
            f"{duplicate_horizons}"
        )

    validate_horizons(
        dataframe=dataframe,
        source_path=specification.summary_path,
    )

    standardized = dataframe.copy()

    standardized["horizon"] = pd.to_numeric(
        standardized["horizon"],
        errors="raise",
    ).astype(int)

    for column in (
        "loso_rmse",
        "loso_mae",
        "loso_r_squared",
    ):
        standardized[column] = pd.to_numeric(
            standardized[column],
            errors="raise",
        )

    if (
        standardized[
            [
                "loso_rmse",
                "loso_mae",
                "loso_r_squared",
            ]
        ]
        .isna()
        .any()
        .any()
    ):
        raise ValueError(
            f"Model summary {specification.summary_path} "
            "contains missing performance metrics."
        )

    if (
        standardized["loso_rmse"] <= 0
    ).any():
        raise ValueError(
            f"Model summary {specification.summary_path} "
            "contains non-positive RMSE."
        )

    if (
        standardized["loso_mae"] < 0
    ).any():
        raise ValueError(
            f"Model summary {specification.summary_path} "
            "contains negative MAE."
        )

    metadata_columns = [
        column
        for column in (
            "season_count",
            "observation_count",
            "blocks_per_season",
            "weather_predictor_count",
        )
        if column in standardized.columns
    ]

    output = standardized[
        [
            "horizon",
            *metadata_columns,
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ]
    ].copy()

    output.insert(
        0,
        "model_order",
        specification.model_order,
    )

    output.insert(
        0,
        "model_family",
        specification.model_family,
    )

    output.insert(
        0,
        "model_label",
        specification.model_label,
    )

    output.insert(
        0,
        "model",
        specification.model,
    )

    output["summary_source"] = str(
        specification.summary_path.relative_to(
            PROJECT_ROOT
        )
    )

    return output


def coerce_boolean_series(
    series: pd.Series,
    column_name: str,
    source_path: Path,
) -> pd.Series:
    """Convert a CSV boolean column to strict booleans."""

    if pd.api.types.is_bool_dtype(
        series
    ):
        return series.astype(bool)

    normalized = (
        series
        .astype(str)
        .str.strip()
        .str.lower()
    )

    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }

    invalid_values = sorted(
        set(normalized)
        - set(mapping)
    )

    if invalid_values:
        raise ValueError(
            f"Column {column_name!r} in {source_path} "
            "contains invalid boolean values: "
            f"{invalid_values}"
        )

    return normalized.map(
        mapping
    ).astype(bool)


def load_ridge_diagnostics(
    specification: ModelSpecification,
) -> pd.DataFrame:
    """Load and summarize Ridge fold diagnostics."""

    if specification.diagnostics_path is None:
        raise ValueError(
            f"Diagnostics path is missing for "
            f"{specification.model}."
        )

    if not specification.diagnostics_path.exists():
        raise FileNotFoundError(
            "Required Ridge diagnostics not found: "
            f"{specification.diagnostics_path}"
        )

    dataframe = pd.read_csv(
        specification.diagnostics_path
    )

    if dataframe.empty:
        raise ValueError(
            f"Ridge diagnostics are empty: "
            f"{specification.diagnostics_path}"
        )

    missing_columns = (
        REQUIRED_RIDGE_DIAGNOSTIC_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Ridge diagnostics "
            f"{specification.diagnostics_path} "
            f"are missing columns: "
            f"{sorted(missing_columns)}"
        )

    dataframe = dataframe.copy()

    dataframe["horizon"] = pd.to_numeric(
        dataframe["horizon"],
        errors="raise",
    ).astype(int)

    dataframe["selected_alpha"] = pd.to_numeric(
        dataframe["selected_alpha"],
        errors="raise",
    )

    dataframe[
        "weather_effective_degrees_of_freedom"
    ] = pd.to_numeric(
        dataframe[
            "weather_effective_degrees_of_freedom"
        ],
        errors="raise",
    )

    for column in (
        "selected_alpha_at_minimum_grid",
        "selected_alpha_at_maximum_grid",
    ):
        dataframe[column] = coerce_boolean_series(
            series=dataframe[column],
            column_name=column,
            source_path=specification.diagnostics_path,
        )

    validate_horizons(
        dataframe=dataframe,
        source_path=specification.diagnostics_path,
    )

    duplicate_fold_keys = dataframe.duplicated(
        subset=[
            "horizon",
            "held_out_season",
        ],
        keep=False,
    )

    if duplicate_fold_keys.any():
        raise ValueError(
            f"Ridge diagnostics "
            f"{specification.diagnostics_path} "
            "contain duplicate horizon-season folds."
        )

    if (
        dataframe["selected_alpha"] <= 0
    ).any():
        raise ValueError(
            f"Ridge diagnostics "
            f"{specification.diagnostics_path} "
            "contain non-positive alpha values."
        )

    if (
        dataframe[
            "weather_effective_degrees_of_freedom"
        ]
        < 0
    ).any():
        raise ValueError(
            f"Ridge diagnostics "
            f"{specification.diagnostics_path} "
            "contain negative effective degrees of freedom."
        )

    summarized = (
        dataframe
        .groupby(
            "horizon",
            as_index=False,
        )
        .agg(
            outer_fold_count=(
                "held_out_season",
                "nunique",
            ),
            selected_alpha_min=(
                "selected_alpha",
                "min",
            ),
            selected_alpha_q25=(
                "selected_alpha",
                lambda values: float(
                    values.quantile(0.25)
                ),
            ),
            selected_alpha_median=(
                "selected_alpha",
                "median",
            ),
            selected_alpha_q75=(
                "selected_alpha",
                lambda values: float(
                    values.quantile(0.75)
                ),
            ),
            selected_alpha_max=(
                "selected_alpha",
                "max",
            ),
            minimum_alpha_boundary_fraction=(
                "selected_alpha_at_minimum_grid",
                "mean",
            ),
            maximum_alpha_boundary_fraction=(
                "selected_alpha_at_maximum_grid",
                "mean",
            ),
            weather_effective_df_min=(
                "weather_effective_degrees_of_freedom",
                "min",
            ),
            weather_effective_df_mean=(
                "weather_effective_degrees_of_freedom",
                "mean",
            ),
            weather_effective_df_median=(
                "weather_effective_degrees_of_freedom",
                "median",
            ),
            weather_effective_df_max=(
                "weather_effective_degrees_of_freedom",
                "max",
            ),
        )
    )

    summarized.insert(
        0,
        "model_label",
        specification.model_label,
    )

    summarized.insert(
        0,
        "model",
        specification.model,
    )

    summarized[
        "diagnostics_source"
    ] = str(
        specification.diagnostics_path.relative_to(
            PROJECT_ROOT
        )
    )

    return summarized


def add_block_only_comparisons(
    comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate performance relative to Block-Only OLS."""

    block_only = comparison_df.loc[
        comparison_df["model"].eq(
            "block_only_ols"
        ),
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ],
    ].rename(
        columns={
            "loso_rmse": "block_only_rmse",
            "loso_mae": "block_only_mae",
            "loso_r_squared": (
                "block_only_r_squared"
            ),
        }
    )

    if len(block_only) != len(
        HORIZONS
    ):
        raise ValueError(
            "Block-Only summary must contain exactly one "
            "row for every horizon."
        )

    output = comparison_df.merge(
        block_only,
        on="horizon",
        how="left",
        validate="many_to_one",
    )

    output[
        "rmse_improvement_vs_block_percent"
    ] = (
        (
            output["block_only_rmse"]
            - output["loso_rmse"]
        )
        / output["block_only_rmse"]
        * 100
    )

    output[
        "mae_improvement_vs_block_percent"
    ] = (
        (
            output["block_only_mae"]
            - output["loso_mae"]
        )
        / output["block_only_mae"]
        * 100
    )

    output[
        "r_squared_difference_vs_block"
    ] = (
        output["loso_r_squared"]
        - output["block_only_r_squared"]
    )

    output["beats_block_only_rmse"] = (
        output[
            "rmse_improvement_vs_block_percent"
        ]
        > 0
    )

    return output


def add_per_horizon_rankings(
    comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add model rankings and best-model gaps within each horizon."""

    output = comparison_df.copy()

    output["rmse_rank"] = (
        output
        .groupby("horizon")["loso_rmse"]
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int)
    )

    output["mae_rank"] = (
        output
        .groupby("horizon")["loso_mae"]
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int)
    )

    output["r_squared_rank"] = (
        output
        .groupby("horizon")["loso_r_squared"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    best_rmse = (
        output
        .groupby(
            "horizon",
            as_index=False,
        )["loso_rmse"]
        .min()
        .rename(
            columns={
                "loso_rmse": "best_rmse",
            }
        )
    )

    output = output.merge(
        best_rmse,
        on="horizon",
        how="left",
        validate="many_to_one",
    )

    output[
        "rmse_gap_from_best_percent"
    ] = (
        (
            output["loso_rmse"]
            - output["best_rmse"]
        )
        / output["best_rmse"]
        * 100
    )

    output["is_best_rmse"] = (
        output["rmse_rank"] == 1
    )

    return output


def build_comparison_table(
    specifications: tuple[
        ModelSpecification,
        ...,
    ],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Load all model summaries and attach Ridge diagnostics.

    Return the complete seven-model comparison and the
    Ridge-only diagnostic table.
    """

    summary_frames = [
        load_model_summary(
            specification
        )
        for specification in specifications
    ]

    comparison_df = pd.concat(
        summary_frames,
        ignore_index=True,
        sort=False,
    )

    duplicate_model_horizons = (
        comparison_df.duplicated(
            subset=[
                "model",
                "horizon",
            ],
            keep=False,
        )
    )

    if duplicate_model_horizons.any():
        raise ValueError(
            "Combined model summaries contain duplicate "
            "model-horizon rows."
        )

    expected_row_count = (
        len(specifications)
        * len(HORIZONS)
    )

    if len(comparison_df) != expected_row_count:
        raise ValueError(
            "Combined comparison has an unexpected number "
            f"of rows: observed={len(comparison_df)}, "
            f"expected={expected_row_count}."
        )

    ridge_frames = [
        load_ridge_diagnostics(
            specification
        )
        for specification in specifications
        if specification.diagnostics_path is not None
    ]

    ridge_diagnostics_df = pd.concat(
        ridge_frames,
        ignore_index=True,
    )

    comparison_df = comparison_df.merge(
        ridge_diagnostics_df.drop(
            columns=[
                "model_label",
                "diagnostics_source",
            ]
        ),
        on=[
            "model",
            "horizon",
        ],
        how="left",
        validate="one_to_one",
    )

    diagnostics_sources = (
        ridge_diagnostics_df[
            [
                "model",
                "horizon",
                "diagnostics_source",
            ]
        ]
    )

    comparison_df = comparison_df.merge(
        diagnostics_sources,
        on=[
            "model",
            "horizon",
        ],
        how="left",
        validate="one_to_one",
    )

    comparison_df = add_block_only_comparisons(
        comparison_df
    )

    comparison_df = add_per_horizon_rankings(
        comparison_df
    )

    preferred_columns = [
        "model",
        "model_label",
        "model_family",
        "model_order",
        "horizon",
        "season_count",
        "observation_count",
        "blocks_per_season",
        "weather_predictor_count",
        "loso_rmse",
        "loso_mae",
        "loso_r_squared",
        "rmse_rank",
        "mae_rank",
        "r_squared_rank",
        "rmse_improvement_vs_block_percent",
        "mae_improvement_vs_block_percent",
        "r_squared_difference_vs_block",
        "beats_block_only_rmse",
        "best_rmse",
        "rmse_gap_from_best_percent",
        "is_best_rmse",
        "outer_fold_count",
        "selected_alpha_min",
        "selected_alpha_q25",
        "selected_alpha_median",
        "selected_alpha_q75",
        "selected_alpha_max",
        "minimum_alpha_boundary_fraction",
        "maximum_alpha_boundary_fraction",
        "weather_effective_df_min",
        "weather_effective_df_mean",
        "weather_effective_df_median",
        "weather_effective_df_max",
        "summary_source",
        "diagnostics_source",
    ]

    existing_preferred_columns = [
        column
        for column in preferred_columns
        if column in comparison_df.columns
    ]

    remaining_columns = [
        column
        for column in comparison_df.columns
        if column not in existing_preferred_columns
        and not column.startswith("block_only_")
    ]

    comparison_df = comparison_df[
        [
            *existing_preferred_columns,
            *remaining_columns,
        ]
    ]

    comparison_df = (
        comparison_df
        .sort_values(
            [
                "horizon",
                "rmse_rank",
                "model_order",
            ]
        )
        .reset_index(drop=True)
    )

    ridge_diagnostics_df = (
        ridge_diagnostics_df
        .merge(
            comparison_df[
                [
                    "model",
                    "horizon",
                    "loso_rmse",
                    "loso_mae",
                    "loso_r_squared",
                    "rmse_rank",
                    (
                        "rmse_improvement_"
                        "vs_block_percent"
                    ),
                ]
            ],
            on=[
                "model",
                "horizon",
            ],
            how="left",
            validate="one_to_one",
        )
        .sort_values(
            [
                "horizon",
                "rmse_rank",
                "model",
            ]
        )
        .reset_index(drop=True)
    )

    return (
        comparison_df,
        ridge_diagnostics_df,
    )


def build_overall_ranking(
    comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize model performance across all horizons."""

    ranking = (
        comparison_df
        .groupby(
            [
                "model",
                "model_label",
                "model_family",
                "model_order",
            ],
            as_index=False,
        )
        .agg(
            horizon_count=(
                "horizon",
                "nunique",
            ),
            mean_rmse_rank=(
                "rmse_rank",
                "mean",
            ),
            median_rmse_rank=(
                "rmse_rank",
                "median",
            ),
            mean_mae_rank=(
                "mae_rank",
                "mean",
            ),
            mean_r_squared_rank=(
                "r_squared_rank",
                "mean",
            ),
            horizons_won_by_rmse=(
                "is_best_rmse",
                "sum",
            ),
            horizons_beating_block_only=(
                "beats_block_only_rmse",
                "sum",
            ),
            mean_rmse_improvement_vs_block_percent=(
                "rmse_improvement_vs_block_percent",
                "mean",
            ),
            mean_mae_improvement_vs_block_percent=(
                "mae_improvement_vs_block_percent",
                "mean",
            ),
            mean_r_squared_difference_vs_block=(
                "r_squared_difference_vs_block",
                "mean",
            ),
            mean_rmse_gap_from_best_percent=(
                "rmse_gap_from_best_percent",
                "mean",
            ),
        )
    )

    ranking["overall_rank"] = (
        ranking[
            [
                "mean_rmse_rank",
                "mean_mae_rank",
                "mean_r_squared_rank",
            ]
        ]
        .mean(axis=1)
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int)
    )

    return (
        ranking
        .sort_values(
            [
                "overall_rank",
                "mean_rmse_rank",
                "model_order",
            ]
        )
        .reset_index(drop=True)
    )


def build_best_model_by_horizon(
    comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """Extract the lowest-RMSE model for each horizon."""

    best_models = (
        comparison_df.loc[
            comparison_df["is_best_rmse"]
        ]
        [
            [
                "horizon",
                "model_order",
                "model",
                "model_label",
                "loso_rmse",
                "loso_mae",
                "loso_r_squared",
                "rmse_improvement_vs_block_percent",
            ]
        ]
        .sort_values(
            [
                "horizon",
                "model_order",
            ]
        )
        .drop(
            columns=[
                "model_order",
            ]
        )
        .reset_index(drop=True)
    )

    return best_models


def print_horizon_rankings(
    comparison_df: pd.DataFrame,
) -> None:
    """Print concise per-horizon RMSE rankings."""

    print("=" * 84)
    print("Seven-Model LOSO Comparison")
    print("=" * 84)

    for horizon in HORIZONS:
        horizon_rows = comparison_df.loc[
            comparison_df["horizon"].eq(
                horizon
            )
        ].sort_values(
            [
                "rmse_rank",
                "model_order",
            ]
        )

        print()
        print(f"h={horizon}")

        for row in horizon_rows.itertuples(
            index=False
        ):
            print(
                f"  {row.rmse_rank}. "
                f"{row.model_label}: "
                f"RMSE={row.loso_rmse:,.0f}, "
                f"MAE={row.loso_mae:,.0f}, "
                f"R²={row.loso_r_squared:.4f}, "
                f"vs block="
                f"{row.rmse_improvement_vs_block_percent:+.2f}%"
            )


def print_overall_ranking(
    overall_ranking_df: pd.DataFrame,
) -> None:
    """Print the overall cross-horizon ranking."""

    print()
    print("=" * 84)
    print("Overall Cross-Horizon Ranking")
    print("=" * 84)

    for row in overall_ranking_df.itertuples(
        index=False
    ):
        print(
            f"{row.overall_rank}. "
            f"{row.model_label}: "
            f"mean RMSE rank="
            f"{row.mean_rmse_rank:.2f}, "
            f"horizons won="
            f"{int(row.horizons_won_by_rmse)}, "
            f"horizons beating block="
            f"{int(row.horizons_beating_block_only)}, "
            f"mean vs block="
            f"{row.mean_rmse_improvement_vs_block_percent:+.2f}%"
        )


def print_ridge_diagnostics(
    ridge_diagnostics_df: pd.DataFrame,
) -> None:
    """Print Ridge penalty-boundary diagnostics."""

    print()
    print("=" * 84)
    print("Ridge Penalty Diagnostics")
    print("=" * 84)

    for row in ridge_diagnostics_df.itertuples(
        index=False
    ):
        print(
            f"{row.model_label}, h={row.horizon}: "
            f"alpha median="
            f"{row.selected_alpha_median:.6g}, "
            f"min-boundary="
            f"{row.minimum_alpha_boundary_fraction:.2%}, "
            f"max-boundary="
            f"{row.maximum_alpha_boundary_fraction:.2%}, "
            f"weather df median="
            f"{row.weather_effective_df_median:.3f}, "
            f"weather df max="
            f"{row.weather_effective_df_max:.3f}"
        )


def main() -> None:
    """Build and export the unified seven-model comparison."""

    print("Comparison implementation: aggregate-schema-fix-v2")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    specifications = (
        get_model_specifications()
    )

    print(
        "Resolved Aggregate OLS summary:"
    )
    print(
        specifications[0].summary_path
    )

    (
        comparison_df,
        ridge_diagnostics_df,
    ) = build_comparison_table(
        specifications
    )

    overall_ranking_df = (
        build_overall_ranking(
            comparison_df
        )
    )

    best_model_df = (
        build_best_model_by_horizon(
            comparison_df
        )
    )

    comparison_df.to_csv(
        COMPARISON_OUTPUT_PATH,
        index=False,
    )

    overall_ranking_df.to_csv(
        OVERALL_RANKING_OUTPUT_PATH,
        index=False,
    )

    ridge_diagnostics_df.to_csv(
        RIDGE_DIAGNOSTICS_OUTPUT_PATH,
        index=False,
    )

    best_model_df.to_csv(
        BEST_MODEL_OUTPUT_PATH,
        index=False,
    )

    print_horizon_rankings(
        comparison_df
    )

    print_overall_ranking(
        overall_ranking_df
    )

    print_ridge_diagnostics(
        ridge_diagnostics_df
    )

    print()
    print("=" * 84)
    print("Results saved to:")
    print(OUTPUT_DIR)
    print("=" * 84)


if __name__ == "__main__":
    main()