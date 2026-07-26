"""
Block-Only OLS Baseline

Fit harvest-block fixed-effect models for aggregation horizons
h = 1, 2, 3, 4, 5.

This baseline contains no weather predictors. It estimates the
historical average crushing profile across harvest blocks and
evaluates it using leave-one-season-out cross-validation.

The results are compared directly with the rainfall month-level
OLS model.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
)

from src.modeling.aggregate_baseline_data import HORIZONS
from src.modeling.month_level_baseline import (
    build_block_fixed_effects,
    calculate_condition_number,
    calculate_rmse,
    load_horizon_dataset,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "month_level_baseline_results"
)

RAINFALL_SUMMARY_PATH = (
    OUTPUT_DIR
    / "rainfall_month_level_ols_summary.csv"
)

TARGET_COLUMN = "block_crush_tonnes"


def build_coefficient_rows(
    horizon: int,
    held_out_season: str,
    model: LinearRegression,
    block_fixed_effect_names: list[str],
) -> list[dict[str, object]]:
    """
    Build block-only coefficient rows for one LOSO fold.

    The intercept represents the expected crushing amount
    for the first harvest block. Each dummy coefficient is
    the difference between another block and the first block.
    """

    rows = [
        {
            "model": "block_only_ols",
            "horizon": horizon,
            "held_out_season": held_out_season,
            "term": "intercept",
            "term_type": "intercept",
            "coefficient": float(
                model.intercept_
            ),
        }
    ]

    for term, coefficient in zip(
        block_fixed_effect_names,
        model.coef_,
        strict=True,
    ):
        rows.append(
            {
                "model": "block_only_ols",
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "term": term,
                "term_type": (
                    "block_fixed_effect"
                ),
                "coefficient": float(
                    coefficient
                ),
            }
        )

    return rows


def run_loso_for_horizon(
    dataframe: pd.DataFrame,
    horizon: int,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, object],
]:
    """
    Run block-only leave-one-season-out OLS for one horizon.
    """

    seasons = sorted(
        dataframe["season"].unique()
    )

    block_levels = sorted(
        dataframe[
            "harvest_block_order"
        ]
        .astype(int)
        .unique()
        .tolist()
    )

    prediction_rows = []
    coefficient_rows = []
    diagnostic_rows = []

    for held_out_season in seasons:
        train_dataframe = dataframe.loc[
            dataframe["season"]
            != held_out_season
        ].copy()

        test_dataframe = dataframe.loc[
            dataframe["season"]
            == held_out_season
        ].copy()

        (
            train_design_matrix,
            block_fixed_effect_names,
        ) = build_block_fixed_effects(
            dataframe=train_dataframe,
            block_levels=block_levels,
        )

        (
            test_design_matrix,
            _,
        ) = build_block_fixed_effects(
            dataframe=test_dataframe,
            block_levels=block_levels,
        )

        augmented_train_design = np.column_stack(
            [
                np.ones(
                    len(train_dataframe)
                ),
                train_design_matrix,
            ]
        )

        training_target = train_dataframe[
            TARGET_COLUMN
        ].to_numpy(
            dtype=float
        )

        test_target = test_dataframe[
            TARGET_COLUMN
        ].to_numpy(
            dtype=float
        )

        model = LinearRegression(
            fit_intercept=True
        )

        model.fit(
            train_design_matrix,
            training_target,
        )

        test_prediction = model.predict(
            test_design_matrix
        )

        for observation, predicted_value in zip(
            test_dataframe.itertuples(
                index=False
            ),
            test_prediction,
            strict=True,
        ):
            actual_value = float(
                getattr(
                    observation,
                    TARGET_COLUMN,
                )
            )

            prediction_rows.append(
                {
                    "model": "block_only_ols",
                    "horizon": horizon,
                    "held_out_season": (
                        held_out_season
                    ),
                    "season": observation.season,
                    "harvest_block_order": int(
                        observation.harvest_block_order
                    ),
                    "block_start_date": (
                        observation.block_start_date
                    ),
                    "block_end_date": (
                        observation.block_end_date
                    ),
                    "actual_block_crush_tonnes": (
                        actual_value
                    ),
                    "predicted_block_crush_tonnes": float(
                        predicted_value
                    ),
                    "residual_tonnes": float(
                        actual_value
                        - predicted_value
                    ),
                }
            )

        coefficient_rows.extend(
            build_coefficient_rows(
                horizon=horizon,
                held_out_season=(
                    held_out_season
                ),
                model=model,
                block_fixed_effect_names=(
                    block_fixed_effect_names
                ),
            )
        )

        diagnostic_rows.append(
            {
                "model": "block_only_ols",
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "training_seasons": (
                    train_dataframe[
                        "season"
                    ].nunique()
                ),
                "training_observations": len(
                    train_dataframe
                ),
                "test_observations": len(
                    test_dataframe
                ),
                "design_columns_including_intercept": (
                    augmented_train_design.shape[1]
                ),
                "design_rank": int(
                    np.linalg.matrix_rank(
                        augmented_train_design
                    )
                ),
                "design_full_column_rank": (
                    np.linalg.matrix_rank(
                        augmented_train_design
                    )
                    == augmented_train_design.shape[1]
                ),
                "design_condition_number": (
                    calculate_condition_number(
                        augmented_train_design
                    )
                ),
                "fold_rmse": calculate_rmse(
                    test_target,
                    test_prediction,
                ),
                "fold_mae": float(
                    mean_absolute_error(
                        test_target,
                        test_prediction,
                    )
                ),
                "fold_r_squared": float(
                    r2_score(
                        test_target,
                        test_prediction,
                    )
                ),
            }
        )

    predictions_df = pd.DataFrame(
        prediction_rows
    )

    coefficients_df = pd.DataFrame(
        coefficient_rows
    )

    diagnostics_df = pd.DataFrame(
        diagnostic_rows
    )

    actual_all = predictions_df[
        "actual_block_crush_tonnes"
    ].to_numpy(
        dtype=float
    )

    predicted_all = predictions_df[
        "predicted_block_crush_tonnes"
    ].to_numpy(
        dtype=float
    )

    summary = {
        "model": "block_only_ols",
        "horizon": horizon,
        "season_count": dataframe[
            "season"
        ].nunique(),
        "observation_count": len(
            dataframe
        ),
        "blocks_per_season": dataframe[
            "harvest_block_order"
        ].nunique(),
        "predictor_count_excluding_intercept": (
            len(block_levels) - 1
        ),
        "loso_rmse": calculate_rmse(
            actual_all,
            predicted_all,
        ),
        "loso_mae": float(
            mean_absolute_error(
                actual_all,
                predicted_all,
            )
        ),
        "loso_r_squared": float(
            r2_score(
                actual_all,
                predicted_all,
            )
        ),
        "all_folds_design_full_rank": bool(
            diagnostics_df[
                "design_full_column_rank"
            ].all()
        ),
        "maximum_fold_design_condition_number": float(
            diagnostics_df[
                "design_condition_number"
            ].max()
        ),
    }

    return (
        predictions_df,
        coefficients_df,
        diagnostics_df,
        summary,
    )


def build_coefficient_summary(
    coefficients_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize block coefficients across LOSO folds."""

    return (
        coefficients_df
        .groupby(
            [
                "horizon",
                "term",
                "term_type",
            ],
            as_index=False,
        )
        .agg(
            coefficient_mean=(
                "coefficient",
                "mean",
            ),
            coefficient_std=(
                "coefficient",
                "std",
            ),
            coefficient_min=(
                "coefficient",
                "min",
            ),
            coefficient_max=(
                "coefficient",
                "max",
            ),
        )
        .sort_values(
            [
                "horizon",
                "term_type",
                "term",
            ]
        )
        .reset_index(drop=True)
    )


def build_weather_comparison(
    block_summary_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare block-only OLS with rainfall month-level OLS.

    Positive RMSE and MAE improvement values mean that
    adding weather improves predictive performance.
    """

    if not RAINFALL_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            "Rainfall month-level OLS summary not found: "
            f"{RAINFALL_SUMMARY_PATH}"
        )

    rainfall_summary_df = pd.read_csv(
        RAINFALL_SUMMARY_PATH
    )

    required_columns = {
        "horizon",
        "loso_rmse",
        "loso_mae",
        "loso_r_squared",
    }

    missing_columns = (
        required_columns
        - set(rainfall_summary_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Rainfall summary is missing columns: "
            f"{sorted(missing_columns)}"
        )

    rainfall_metrics = rainfall_summary_df[
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ]
    ].rename(
        columns={
            "loso_rmse": (
                "rainfall_ols_rmse"
            ),
            "loso_mae": (
                "rainfall_ols_mae"
            ),
            "loso_r_squared": (
                "rainfall_ols_r_squared"
            ),
        }
    )

    block_metrics = block_summary_df[
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ]
    ].rename(
        columns={
            "loso_rmse": (
                "block_only_rmse"
            ),
            "loso_mae": (
                "block_only_mae"
            ),
            "loso_r_squared": (
                "block_only_r_squared"
            ),
        }
    )

    comparison_df = block_metrics.merge(
        rainfall_metrics,
        on="horizon",
        how="inner",
        validate="one_to_one",
    )

    comparison_df[
        "rmse_improvement_tonnes"
    ] = (
        comparison_df["block_only_rmse"]
        - comparison_df["rainfall_ols_rmse"]
    )

    comparison_df[
        "rmse_improvement_percent"
    ] = (
        comparison_df[
            "rmse_improvement_tonnes"
        ]
        / comparison_df["block_only_rmse"]
        * 100
    )

    comparison_df[
        "mae_improvement_tonnes"
    ] = (
        comparison_df["block_only_mae"]
        - comparison_df["rainfall_ols_mae"]
    )

    comparison_df[
        "mae_improvement_percent"
    ] = (
        comparison_df[
            "mae_improvement_tonnes"
        ]
        / comparison_df["block_only_mae"]
        * 100
    )

    comparison_df[
        "r_squared_improvement"
    ] = (
        comparison_df[
            "rainfall_ols_r_squared"
        ]
        - comparison_df[
            "block_only_r_squared"
        ]
    )

    comparison_df[
        "weather_improves_rmse"
    ] = (
        comparison_df[
            "rmse_improvement_tonnes"
        ]
        > 0
    )

    comparison_df[
        "weather_improves_mae"
    ] = (
        comparison_df[
            "mae_improvement_tonnes"
        ]
        > 0
    )

    return (
        comparison_df
        .sort_values("horizon")
        .reset_index(drop=True)
    )


def main() -> None:
    """Run block-only OLS for all horizons."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_predictions = []
    all_coefficients = []
    all_diagnostics = []
    summary_rows = []

    print("=" * 72)
    print("Block-Only OLS Baseline")
    print("=" * 72)

    for horizon in HORIZONS:
        dataframe = load_horizon_dataset(
            horizon
        )

        (
            predictions_df,
            coefficients_df,
            diagnostics_df,
            summary,
        ) = run_loso_for_horizon(
            dataframe=dataframe,
            horizon=horizon,
        )

        all_predictions.append(
            predictions_df
        )

        all_coefficients.append(
            coefficients_df
        )

        all_diagnostics.append(
            diagnostics_df
        )

        summary_rows.append(
            summary
        )

        print(
            f"[OK] h={horizon}: "
            f"RMSE={summary['loso_rmse']:,.0f}, "
            f"MAE={summary['loso_mae']:,.0f}, "
            f"R²={summary['loso_r_squared']:.4f}"
        )

    predictions_output = pd.concat(
        all_predictions,
        ignore_index=True,
    )

    coefficients_output = pd.concat(
        all_coefficients,
        ignore_index=True,
    )

    diagnostics_output = pd.concat(
        all_diagnostics,
        ignore_index=True,
    )

    summary_output = pd.DataFrame(
        summary_rows
    )

    coefficient_summary_output = (
        build_coefficient_summary(
            coefficients_output
        )
    )

    comparison_output = (
        build_weather_comparison(
            summary_output
        )
    )

    predictions_output.to_csv(
        OUTPUT_DIR
        / "block_only_ols_predictions.csv",
        index=False,
    )

    coefficients_output.to_csv(
        OUTPUT_DIR
        / "block_only_ols_coefficients.csv",
        index=False,
    )

    coefficient_summary_output.to_csv(
        OUTPUT_DIR
        / "block_only_ols_coefficient_summary.csv",
        index=False,
    )

    diagnostics_output.to_csv(
        OUTPUT_DIR
        / "block_only_ols_fold_diagnostics.csv",
        index=False,
    )

    summary_output.to_csv(
        OUTPUT_DIR
        / "block_only_ols_summary.csv",
        index=False,
    )

    comparison_output.to_csv(
        OUTPUT_DIR
        / "rainfall_ols_vs_block_only.csv",
        index=False,
    )

    print("=" * 72)
    print("Rainfall OLS Improvement over Block-Only")
    print("=" * 72)

    for row in comparison_output.itertuples(
        index=False
    ):
        print(
            f"h={row.horizon}: "
            f"RMSE improvement="
            f"{row.rmse_improvement_percent:.2f}%, "
            f"MAE improvement="
            f"{row.mae_improvement_percent:.2f}%, "
            f"ΔR²="
            f"{row.r_squared_improvement:+.4f}"
        )

    print("=" * 72)
    print("Results saved to:")
    print(OUTPUT_DIR)
    print("=" * 72)


if __name__ == "__main__":
    main()