"""
Temperature Month-Level OLS Baseline

Fit month-level temperature OLS models for harvest aggregation
horizons h = 1, 2, 3, 4, 5.

Each model uses:

- September-April monthly temperature
- Growing-season total rainfall as a control
- Harvest-block fixed effects
- Leave-one-season-out cross-validation
- Fold-specific weather standardization
"""

from pathlib import Path

import pandas as pd

from src.modeling.aggregate_baseline_data import HORIZONS
from src.modeling.month_level_baseline import (
    build_coefficient_summary,
    load_horizon_dataset,
    run_loso_for_horizon,
)
from src.modeling.month_level_baseline_data import (
    TEMPERATURE_FEATURES,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "month_level_baseline_results"
)

BLOCK_ONLY_SUMMARY_PATH = (
    OUTPUT_DIR
    / "block_only_ols_summary.csv"
)

RAINFALL_CONTROL = (
    "growing_season_total_rainfall"
)

WEATHER_FEATURES = (
    *TEMPERATURE_FEATURES,
    RAINFALL_CONTROL,
)

MODEL_NAME = "temperature_month_level_ols"


def load_block_only_metrics() -> pd.DataFrame:
    """Load block-only metrics for model comparison."""

    if not BLOCK_ONLY_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            "Block-only summary not found: "
            f"{BLOCK_ONLY_SUMMARY_PATH}"
        )

    block_df = pd.read_csv(
        BLOCK_ONLY_SUMMARY_PATH
    )

    required_columns = {
        "horizon",
        "loso_rmse",
        "loso_mae",
        "loso_r_squared",
    }

    missing_columns = (
        required_columns
        - set(block_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Block-only summary is missing columns: "
            f"{sorted(missing_columns)}"
        )

    return block_df[
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ]
    ].rename(
        columns={
            "loso_rmse": "block_only_rmse",
            "loso_mae": "block_only_mae",
            "loso_r_squared": (
                "block_only_r_squared"
            ),
        }
    )


def build_block_comparison(
    temperature_summary: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare temperature OLS with the block-only baseline.

    Positive improvement values mean that temperature
    predictors improve out-of-sample performance.
    """

    block_metrics = load_block_only_metrics()

    temperature_metrics = temperature_summary[
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ]
    ].rename(
        columns={
            "loso_rmse": (
                "temperature_ols_rmse"
            ),
            "loso_mae": (
                "temperature_ols_mae"
            ),
            "loso_r_squared": (
                "temperature_ols_r_squared"
            ),
        }
    )

    comparison_df = block_metrics.merge(
        temperature_metrics,
        on="horizon",
        how="inner",
        validate="one_to_one",
    )

    comparison_df[
        "rmse_improvement_tonnes"
    ] = (
        comparison_df["block_only_rmse"]
        - comparison_df[
            "temperature_ols_rmse"
        ]
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
        - comparison_df[
            "temperature_ols_mae"
        ]
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
            "temperature_ols_r_squared"
        ]
        - comparison_df[
            "block_only_r_squared"
        ]
    )

    comparison_df[
        "temperature_improves_rmse"
    ] = (
        comparison_df[
            "rmse_improvement_tonnes"
        ]
        > 0
    )

    comparison_df[
        "temperature_improves_mae"
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
    """Run temperature month-level OLS for every horizon."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_predictions = []
    all_coefficients = []
    all_diagnostics = []
    summary_rows = []

    print("=" * 72)
    print("Temperature Month-Level OLS Baseline")
    print("=" * 72)

    for horizon in HORIZONS:
        dataframe = load_horizon_dataset(
            horizon=horizon,
            weather_features=WEATHER_FEATURES,
        )

        (
            predictions_df,
            coefficients_df,
            diagnostics_df,
            summary,
        ) = run_loso_for_horizon(
            dataframe=dataframe,
            horizon=horizon,
            weather_features=WEATHER_FEATURES,
            model_name=MODEL_NAME,
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
            f"rank="
            f"{summary['full_sample_weather_rank']}/"
            f"{len(WEATHER_FEATURES)}, "
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

    comparison_output = build_block_comparison(
        summary_output
    )

    predictions_output.to_csv(
        OUTPUT_DIR
        / "temperature_month_level_ols_predictions.csv",
        index=False,
    )

    coefficients_output.to_csv(
        OUTPUT_DIR
        / "temperature_month_level_ols_coefficients.csv",
        index=False,
    )

    coefficient_summary_output.to_csv(
        OUTPUT_DIR
        / "temperature_month_level_ols_coefficient_summary.csv",
        index=False,
    )

    diagnostics_output.to_csv(
        OUTPUT_DIR
        / "temperature_month_level_ols_fold_diagnostics.csv",
        index=False,
    )

    summary_output.to_csv(
        OUTPUT_DIR
        / "temperature_month_level_ols_summary.csv",
        index=False,
    )

    comparison_output.to_csv(
        OUTPUT_DIR
        / "temperature_ols_vs_block_only.csv",
        index=False,
    )

    print("=" * 72)
    print("Temperature OLS Improvement over Block-Only")
    print("=" * 72)

    for row in comparison_output.itertuples(
        index=False
    ):
        print(
            f"h={row.horizon}: "
            f"RMSE improvement="
            f"{row.rmse_improvement_percent:+.2f}%, "
            f"MAE improvement="
            f"{row.mae_improvement_percent:+.2f}%, "
            f"ΔR²="
            f"{row.r_squared_improvement:+.4f}"
        )

    print("=" * 72)
    print("Results saved to:")
    print(OUTPUT_DIR)
    print("=" * 72)


if __name__ == "__main__":
    main()