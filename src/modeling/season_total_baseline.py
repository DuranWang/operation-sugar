"""
Season-Total Aggregate Baseline Models

Evaluate whether aggregate growing-season weather improves
out-of-sample prediction of complete-season São Paulo crushing.

Two specifications are compared:

1. mean_only
   Predict each held-out season using the mean total crushing
   volume of the training seasons.

2. weather
   Predict complete-season crushing using standardized:
   - growing-season total rainfall;
   - growing-season average temperature.

The models are evaluated using leave-one-season-out
cross-validation across complete historical seasons.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "aggregate_baseline"
    / "aggregate_baseline_h1.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "aggregate_baseline"
    / "season_total_results"
)

MODEL_SPECIFICATIONS = (
    "mean_only",
    "weather",
)

EXPECTED_BLOCKS_PER_SEASON = 12

TARGET_COLUMN = (
    "season_total_crush_tonnes"
)

WEATHER_FEATURES = [
    "growing_season_total_rainfall",
    "growing_season_average_temperature",
]

SOURCE_REQUIRED_COLUMNS = [
    "season",
    "horizon",
    "harvest_block_order",
    "block_crush_tonnes",
    *WEATHER_FEATURES,
]


def load_block_dataset(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load and validate the h=1 block-level baseline dataset.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            f"Block-level baseline dataset not found: {input_path}"
        )

    block_df = pd.read_csv(
        input_path
    )

    if block_df.empty:
        raise ValueError(
            "Block-level baseline dataset is empty."
        )

    missing_columns = (
        set(SOURCE_REQUIRED_COLUMNS)
        - set(block_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Block-level baseline dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if block_df[
        SOURCE_REQUIRED_COLUMNS
    ].isna().any().any():
        raise ValueError(
            "Block-level baseline dataset contains missing values."
        )

    if not block_df[
        "horizon"
    ].eq(1).all():
        raise ValueError(
            "Season-total construction requires the h=1 dataset."
        )

    if block_df.duplicated(
        subset=[
            "season",
            "harvest_block_order",
        ],
        keep=False,
    ).any():
        raise ValueError(
            "Block-level dataset contains duplicate season-block rows."
        )

    if (
        block_df["block_crush_tonnes"]
        < 0
    ).any():
        raise ValueError(
            "Block crushing values cannot be negative."
        )

    return (
        block_df
        .sort_values(
            [
                "season",
                "harvest_block_order",
            ]
        )
        .reset_index(drop=True)
    )


def validate_constant_season_weather(
    block_df: pd.DataFrame,
) -> None:
    """
    Confirm that each weather predictor has one value per season.
    """

    weather_value_counts = (
        block_df
        .groupby("season")[
            WEATHER_FEATURES
        ]
        .nunique()
    )

    invalid_seasons = weather_value_counts.loc[
        weather_value_counts.gt(1).any(axis=1)
    ]

    if not invalid_seasons.empty:
        raise ValueError(
            "Weather predictors vary within the following seasons:\n"
            f"{invalid_seasons.to_string()}"
        )


def build_season_total_dataset(
    block_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate 12 h=1 harvest blocks into one complete-season
    crushing total per season.
    """

    validate_constant_season_weather(
        block_df
    )

    block_counts = (
        block_df
        .groupby("season")[
            "harvest_block_order"
        ]
        .nunique()
    )

    invalid_block_counts = block_counts.loc[
        block_counts.ne(
            EXPECTED_BLOCKS_PER_SEASON
        )
    ]

    if not invalid_block_counts.empty:
        raise ValueError(
            "Every complete season must contain exactly "
            f"{EXPECTED_BLOCKS_PER_SEASON} h=1 blocks:\n"
            f"{invalid_block_counts.to_string()}"
        )

    season_df = (
        block_df
        .groupby(
            "season",
            as_index=False,
        )
        .agg(
            season_total_crush_tonnes=(
                "block_crush_tonnes",
                "sum",
            ),
            block_count=(
                "harvest_block_order",
                "nunique",
            ),
            growing_season_total_rainfall=(
                "growing_season_total_rainfall",
                "first",
            ),
            growing_season_average_temperature=(
                "growing_season_average_temperature",
                "first",
            ),
        )
        .sort_values("season")
        .reset_index(drop=True)
    )

    if season_df.empty:
        raise ValueError(
            "Season-total dataset is empty."
        )

    if season_df[
        [
            TARGET_COLUMN,
            *WEATHER_FEATURES,
        ]
    ].isna().any().any():
        raise ValueError(
            "Season-total dataset contains missing values."
        )

    if season_df[
        "season"
    ].duplicated().any():
        raise ValueError(
            "Season-total dataset contains duplicate seasons."
        )

    if not season_df[
        "block_count"
    ].eq(
        EXPECTED_BLOCKS_PER_SEASON
    ).all():
        raise ValueError(
            "Season-total dataset contains invalid block counts."
        )

    if (
        season_df[TARGET_COLUMN]
        < 0
    ).any():
        raise ValueError(
            "Season-total crushing values cannot be negative."
        )

    return season_df


def validate_specification(
    specification: str,
) -> None:
    """
    Validate one model specification.
    """

    if specification not in MODEL_SPECIFICATIONS:
        raise ValueError(
            f"Unsupported model specification: {specification}."
        )


def build_estimator(
    specification: str,
):
    """
    Build one season-total estimator.
    """

    validate_specification(
        specification
    )

    if specification == "mean_only":
        return DummyRegressor(
            strategy="mean"
        )

    return Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LinearRegression(),
            ),
        ]
    )


def build_feature_matrix(
    model_df: pd.DataFrame,
    specification: str,
) -> pd.DataFrame | np.ndarray:
    """
    Build the raw feature matrix required by one specification.
    """

    validate_specification(
        specification
    )

    if specification == "mean_only":
        return np.zeros(
            (
                len(model_df),
                1,
            )
        )

    return model_df[
        WEATHER_FEATURES
    ]


def calculate_metrics(
    actual: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
) -> dict[str, float]:
    """
    Calculate season-total regression metrics.
    """

    actual_array = np.asarray(
        actual,
        dtype=float,
    )

    predicted_array = np.asarray(
        predicted,
        dtype=float,
    )

    if actual_array.shape != predicted_array.shape:
        raise ValueError(
            "Actual and predicted arrays must have the same shape."
        )

    if actual_array.size == 0:
        raise ValueError(
            "Metrics cannot be calculated using empty arrays."
        )

    rmse = (
        mean_squared_error(
            actual_array,
            predicted_array,
        )
        ** 0.5
    )

    mae = mean_absolute_error(
        actual_array,
        predicted_array,
    )

    r_squared = r2_score(
        actual_array,
        predicted_array,
    )

    mean_actual = float(
        np.mean(actual_array)
    )

    normalized_rmse = (
        rmse / mean_actual
        if mean_actual != 0
        else np.nan
    )

    normalized_mae = (
        mae / mean_actual
        if mean_actual != 0
        else np.nan
    )

    return {
        "r_squared": float(r_squared),
        "rmse_tonnes": float(rmse),
        "mae_tonnes": float(mae),
        "normalized_rmse": float(normalized_rmse),
        "normalized_mae": float(normalized_mae),
    }


def build_prediction_dataset(
    model_df: pd.DataFrame,
    predicted_values: np.ndarray,
    specification: str,
    evaluation_type: str,
    held_out_season: str | None = None,
) -> pd.DataFrame:
    """
    Build one standardized season-total prediction table.
    """

    prediction_df = model_df[
        [
            "season",
            TARGET_COLUMN,
            *WEATHER_FEATURES,
        ]
    ].copy()

    prediction_df[
        "predicted_season_total_crush_tonnes"
    ] = predicted_values

    prediction_df[
        "residual_tonnes"
    ] = (
        prediction_df[TARGET_COLUMN]
        - prediction_df[
            "predicted_season_total_crush_tonnes"
        ]
    )

    prediction_df[
        "absolute_error_tonnes"
    ] = (
        prediction_df[
            "residual_tonnes"
        ]
        .abs()
    )

    prediction_df[
        "squared_error_tonnes"
    ] = (
        prediction_df[
            "residual_tonnes"
        ]
        ** 2
    )

    prediction_df[
        "specification"
    ] = specification

    prediction_df[
        "evaluation_type"
    ] = evaluation_type

    prediction_df[
        "held_out_season"
    ] = held_out_season

    return prediction_df


def extract_coefficients(
    fitted_estimator,
    specification: str,
) -> pd.DataFrame:
    """
    Extract complete-sample model coefficients.
    """

    validate_specification(
        specification
    )

    if specification == "mean_only":
        intercept = float(
            np.ravel(
                fitted_estimator.constant_
            )[0]
        )

        return pd.DataFrame(
            {
                "specification": [
                    specification
                ],
                "feature": [
                    "training_mean"
                ],
                "coefficient": [
                    intercept
                ],
            }
        )

    linear_model = fitted_estimator.named_steps[
        "model"
    ]

    coefficient_df = pd.DataFrame(
        {
            "specification": specification,
            "feature": WEATHER_FEATURES,
            "coefficient": linear_model.coef_,
        }
    )

    intercept_row = pd.DataFrame(
        {
            "specification": [
                specification
            ],
            "feature": [
                "intercept"
            ],
            "coefficient": [
                float(
                    linear_model.intercept_
                )
            ],
        }
    )

    return pd.concat(
        [
            intercept_row,
            coefficient_df,
        ],
        ignore_index=True,
    )


def fit_full_sample_model(
    model_df: pd.DataFrame,
    specification: str,
) -> tuple[
    object,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, float],
]:
    """
    Fit one season-total model using all complete seasons.
    """

    features = build_feature_matrix(
        model_df=model_df,
        specification=specification,
    )

    target = model_df[
        TARGET_COLUMN
    ]

    estimator = build_estimator(
        specification
    )

    estimator.fit(
        features,
        target,
    )

    fitted_values = estimator.predict(
        features
    )

    prediction_df = build_prediction_dataset(
        model_df=model_df,
        predicted_values=fitted_values,
        specification=specification,
        evaluation_type="in_sample",
    )

    coefficient_df = extract_coefficients(
        fitted_estimator=estimator,
        specification=specification,
    )

    metrics = calculate_metrics(
        actual=target,
        predicted=fitted_values,
    )

    return (
        estimator,
        prediction_df,
        coefficient_df,
        metrics,
    )


def run_leave_one_season_out_cv(
    model_df: pd.DataFrame,
    specification: str,
) -> tuple[
    pd.DataFrame,
    dict[str, float],
]:
    """
    Evaluate one model using leave-one-season-out
    cross-validation.
    """

    seasons = sorted(
        model_df[
            "season"
        ].unique()
    )

    if len(seasons) < 3:
        raise ValueError(
            "At least three seasons are required for "
            "leave-one-season-out validation."
        )

    fold_predictions = []

    for held_out_season in seasons:
        training_df = model_df.loc[
            model_df["season"].ne(
                held_out_season
            )
        ].copy()

        testing_df = model_df.loc[
            model_df["season"].eq(
                held_out_season
            )
        ].copy()

        if training_df.empty or testing_df.empty:
            raise ValueError(
                "Invalid leave-one-season-out split for "
                f"{held_out_season}."
            )

        training_features = build_feature_matrix(
            model_df=training_df,
            specification=specification,
        )

        testing_features = build_feature_matrix(
            model_df=testing_df,
            specification=specification,
        )

        estimator = build_estimator(
            specification
        )

        estimator.fit(
            training_features,
            training_df[
                TARGET_COLUMN
            ],
        )

        predicted_values = estimator.predict(
            testing_features
        )

        fold_df = build_prediction_dataset(
            model_df=testing_df,
            predicted_values=predicted_values,
            specification=specification,
            evaluation_type="leave_one_season_out",
            held_out_season=held_out_season,
        )

        fold_predictions.append(
            fold_df
        )

    prediction_df = pd.concat(
        fold_predictions,
        ignore_index=True,
    )

    if len(prediction_df) != len(model_df):
        raise ValueError(
            "Cross-validation prediction count does not match "
            "the season-total dataset."
        )

    if prediction_df[
        "season"
    ].duplicated().any():
        raise ValueError(
            "Cross-validation predictions contain duplicate seasons."
        )

    metrics = calculate_metrics(
        actual=prediction_df[
            TARGET_COLUMN
        ],
        predicted=prediction_df[
            "predicted_season_total_crush_tonnes"
        ],
    )

    return (
        prediction_df,
        metrics,
    )


def build_model_summary(
    specification: str,
    model_df: pd.DataFrame,
    in_sample_metrics: dict[str, float],
    cv_metrics: dict[str, float],
) -> pd.DataFrame:
    """
    Build one season-total model-summary row.
    """

    summary_row = {
        "specification": specification,
        "season_count": (
            model_df[
                "season"
            ].nunique()
        ),
        "observation_count": len(
            model_df
        ),
        "in_sample_r_squared": (
            in_sample_metrics[
                "r_squared"
            ]
        ),
        "in_sample_rmse_tonnes": (
            in_sample_metrics[
                "rmse_tonnes"
            ]
        ),
        "in_sample_mae_tonnes": (
            in_sample_metrics[
                "mae_tonnes"
            ]
        ),
        "in_sample_normalized_rmse": (
            in_sample_metrics[
                "normalized_rmse"
            ]
        ),
        "in_sample_normalized_mae": (
            in_sample_metrics[
                "normalized_mae"
            ]
        ),
        "cv_r_squared": (
            cv_metrics[
                "r_squared"
            ]
        ),
        "cv_rmse_tonnes": (
            cv_metrics[
                "rmse_tonnes"
            ]
        ),
        "cv_mae_tonnes": (
            cv_metrics[
                "mae_tonnes"
            ]
        ),
        "cv_normalized_rmse": (
            cv_metrics[
                "normalized_rmse"
            ]
        ),
        "cv_normalized_mae": (
            cv_metrics[
                "normalized_mae"
            ]
        ),
    }

    return pd.DataFrame(
        [
            summary_row
        ]
    )


def build_incremental_comparison(
    summary_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare the weather model against the mean-only benchmark.
    """

    observed_specifications = set(
        summary_df[
            "specification"
        ].unique()
    )

    required_specifications = set(
        MODEL_SPECIFICATIONS
    )

    missing_specifications = (
        required_specifications
        - observed_specifications
    )

    if missing_specifications:
        raise ValueError(
            "Model summary is missing specifications: "
            f"{sorted(missing_specifications)}"
        )

    metric_columns = [
        "cv_r_squared",
        "cv_rmse_tonnes",
        "cv_mae_tonnes",
        "cv_normalized_rmse",
        "cv_normalized_mae",
    ]

    comparison_values = {}

    for metric in metric_columns:
        metric_values = (
            summary_df
            .set_index(
                "specification"
            )[metric]
        )

        comparison_values[
            f"{metric}_mean_only"
        ] = metric_values[
            "mean_only"
        ]

        comparison_values[
            f"{metric}_weather"
        ] = metric_values[
            "weather"
        ]

    comparison_df = pd.DataFrame(
        [
            comparison_values
        ]
    )

    comparison_df[
        "incremental_cv_r_squared"
    ] = (
        comparison_df[
            "cv_r_squared_weather"
        ]
        - comparison_df[
            "cv_r_squared_mean_only"
        ]
    )

    comparison_df[
        "incremental_cv_rmse_improvement_tonnes"
    ] = (
        comparison_df[
            "cv_rmse_tonnes_mean_only"
        ]
        - comparison_df[
            "cv_rmse_tonnes_weather"
        ]
    )

    comparison_df[
        "incremental_cv_mae_improvement_tonnes"
    ] = (
        comparison_df[
            "cv_mae_tonnes_mean_only"
        ]
        - comparison_df[
            "cv_mae_tonnes_weather"
        ]
    )

    comparison_df[
        "incremental_cv_nrmse_improvement"
    ] = (
        comparison_df[
            "cv_normalized_rmse_mean_only"
        ]
        - comparison_df[
            "cv_normalized_rmse_weather"
        ]
    )

    comparison_df[
        "incremental_cv_nmae_improvement"
    ] = (
        comparison_df[
            "cv_normalized_mae_mean_only"
        ]
        - comparison_df[
            "cv_normalized_mae_weather"
        ]
    )

    comparison_df[
        "weather_improves_cv_r_squared"
    ] = (
        comparison_df[
            "incremental_cv_r_squared"
        ]
        > 0
    )

    comparison_df[
        "weather_improves_cv_nrmse"
    ] = (
        comparison_df[
            "incremental_cv_nrmse_improvement"
        ]
        > 0
    )

    return comparison_df


def main() -> None:
    """
    Build, fit, evaluate, and save season-total baselines.
    """

    block_df = load_block_dataset(
        INPUT_PATH
    )

    season_df = build_season_total_dataset(
        block_df
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_summaries = []
    all_coefficients = []
    all_predictions = []

    print("=" * 72)
    print("Season-Total Aggregate Baseline Estimation")
    print("=" * 72)

    print(
        f"Complete seasons: "
        f"{season_df['season'].nunique()}"
    )

    for specification in MODEL_SPECIFICATIONS:
        (
            _,
            in_sample_predictions,
            coefficient_df,
            in_sample_metrics,
        ) = fit_full_sample_model(
            model_df=season_df,
            specification=specification,
        )

        (
            cv_predictions,
            cv_metrics,
        ) = run_leave_one_season_out_cv(
            model_df=season_df,
            specification=specification,
        )

        summary_df = build_model_summary(
            specification=specification,
            model_df=season_df,
            in_sample_metrics=in_sample_metrics,
            cv_metrics=cv_metrics,
        )

        all_summaries.append(
            summary_df
        )

        all_coefficients.append(
            coefficient_df
        )

        all_predictions.extend(
            [
                in_sample_predictions,
                cv_predictions,
            ]
        )

        print(
            f"[OK] {specification}: "
            f"CV R²={cv_metrics['r_squared']:.4f}, "
            f"CV RMSE={cv_metrics['rmse_tonnes']:,.0f}, "
            f"CV NRMSE={cv_metrics['normalized_rmse']:.4f}"
        )

    summary_df = pd.concat(
        all_summaries,
        ignore_index=True,
    )

    coefficient_df = pd.concat(
        all_coefficients,
        ignore_index=True,
    )

    prediction_df = pd.concat(
        all_predictions,
        ignore_index=True,
    )

    comparison_df = build_incremental_comparison(
        summary_df
    )

    dataset_path = (
        OUTPUT_DIR
        / "season_total_dataset.csv"
    )

    summary_path = (
        OUTPUT_DIR
        / "season_total_model_summary.csv"
    )

    coefficient_path = (
        OUTPUT_DIR
        / "season_total_coefficients.csv"
    )

    prediction_path = (
        OUTPUT_DIR
        / "season_total_predictions.csv"
    )

    comparison_path = (
        OUTPUT_DIR
        / "season_total_incremental_comparison.csv"
    )

    season_df.to_csv(
        dataset_path,
        index=False,
    )

    summary_df.to_csv(
        summary_path,
        index=False,
    )

    coefficient_df.to_csv(
        coefficient_path,
        index=False,
    )

    prediction_df.to_csv(
        prediction_path,
        index=False,
    )

    comparison_df.to_csv(
        comparison_path,
        index=False,
    )

    print("-" * 72)
    print("Model Summary")
    print("-" * 72)
    print(
        summary_df.to_string(
            index=False
        )
    )

    print("-" * 72)
    print("Incremental Weather Contribution")
    print("-" * 72)
    print(
        comparison_df.to_string(
            index=False
        )
    )

    print("-" * 72)
    print(
        f"Saved season-total dataset: {dataset_path}"
    )
    print(
        f"Saved model summary: {summary_path}"
    )
    print(
        f"Saved coefficients: {coefficient_path}"
    )
    print(
        f"Saved predictions: {prediction_path}"
    )
    print(
        f"Saved incremental comparison: {comparison_path}"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()