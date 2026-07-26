"""
Aggregate Baseline Models

Estimate aggregate weather-harvest baseline models for
aggregation horizons h = 1, 2, 3, 4, 5.

Two model specifications are compared:

1. weather_block
   - growing-season total rainfall;
   - growing-season average temperature;
   - harvest-block position fixed effects.

2. block_only
   - harvest-block position fixed effects only.

Model performance is evaluated both in sample and through
leave-one-season-out cross-validation.

The comparison between weather_block and block_only measures
the incremental out-of-sample contribution of weather features.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "aggregate_baseline"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "aggregate_baseline"
    / "results"
)

HORIZONS = (
    1,
    2,
    3,
    4,
    5,
)

MODEL_SPECIFICATIONS = (
    "weather_block",
    "block_only",
)

TARGET_COLUMN = (
    "block_crush_tonnes"
)

WEATHER_FEATURES = [
    "growing_season_total_rainfall",
    "growing_season_average_temperature",
]

BLOCK_FEATURE = (
    "harvest_block_order"
)

REQUIRED_COLUMNS = [
    "season",
    "horizon",
    BLOCK_FEATURE,
    TARGET_COLUMN,
    *WEATHER_FEATURES,
]


def load_horizon_dataset(
    horizon: int,
) -> pd.DataFrame:
    """
    Load and validate one model-ready horizon dataset.
    """

    if horizon not in HORIZONS:
        raise ValueError(
            f"Unsupported horizon: {horizon}."
        )

    input_path = (
        INPUT_DIR
        / f"aggregate_baseline_h{horizon}.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(
            "Aggregate baseline dataset not found: "
            f"{input_path}"
        )

    model_df = pd.read_csv(
        input_path,
        parse_dates=[
            "block_start_date",
            "block_end_date",
        ],
    )

    if model_df.empty:
        raise ValueError(
            "Aggregate baseline dataset is empty "
            f"for h={horizon}."
        )

    missing_columns = (
        set(REQUIRED_COLUMNS)
        - set(model_df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Dataset for h={horizon} is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if model_df[
        REQUIRED_COLUMNS
    ].isna().any().any():
        raise ValueError(
            f"Dataset for h={horizon} contains missing values."
        )

    if not model_df[
        "horizon"
    ].eq(horizon).all():
        raise ValueError(
            "Dataset contains inconsistent horizon values "
            f"for h={horizon}."
        )

    duplicate_rows = model_df.duplicated(
        subset=[
            "season",
            BLOCK_FEATURE,
        ],
        keep=False,
    )

    if duplicate_rows.any():
        raise ValueError(
            "Dataset contains duplicate season-block rows "
            f"for h={horizon}."
        )

    if (
        model_df[TARGET_COLUMN]
        < 0
    ).any():
        raise ValueError(
            f"Target values cannot be negative for h={horizon}."
        )

    return (
        model_df
        .sort_values(
            [
                "season",
                BLOCK_FEATURE,
            ]
        )
        .reset_index(drop=True)
    )


def validate_specification(
    specification: str,
) -> None:
    """
    Validate one model specification name.
    """

    if specification not in MODEL_SPECIFICATIONS:
        raise ValueError(
            "Unsupported model specification: "
            f"{specification}."
        )


def get_feature_columns(
    specification: str,
) -> list[str]:
    """
    Return raw input columns required by one specification.
    """

    validate_specification(
        specification
    )

    if specification == "weather_block":
        return [
            *WEATHER_FEATURES,
            BLOCK_FEATURE,
        ]

    return [
        BLOCK_FEATURE,
    ]


def build_model_pipeline(
    specification: str,
) -> Pipeline:
    """
    Build one OLS preprocessing and estimation pipeline.

    Specifications
    --------------
    weather_block:
        Standardized growing-season weather predictors plus
        harvest-block position fixed effects.

    block_only:
        Harvest-block position fixed effects only.
    """

    validate_specification(
        specification
    )

    transformers = []

    if specification == "weather_block":
        transformers.append(
            (
                "weather",
                StandardScaler(),
                WEATHER_FEATURES,
            )
        )

    transformers.append(
        (
            "block_position",
            OneHotEncoder(
                drop="first",
                handle_unknown="ignore",
                sparse_output=False,
            ),
            [BLOCK_FEATURE],
        )
    )

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "model",
                LinearRegression(),
            ),
        ]
    )


def calculate_metrics(
    actual: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
) -> dict[str, float]:
    """
    Calculate regression performance metrics.
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
            "Actual and predicted arrays must have "
            "the same shape."
        )

    if actual_array.size == 0:
        raise ValueError(
            "Metrics cannot be calculated on empty arrays."
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


def extract_coefficients(
    fitted_pipeline: Pipeline,
    horizon: int,
    specification: str,
) -> pd.DataFrame:
    """
    Extract fitted coefficients from one complete-sample model.

    Weather coefficients are expressed in target tonnes per
    one-standard-deviation increase in the corresponding weather
    predictor.

    Block-position coefficients are measured relative to the
    first omitted block category.
    """

    validate_specification(
        specification
    )

    preprocessor = fitted_pipeline.named_steps[
        "preprocessor"
    ]

    linear_model = fitted_pipeline.named_steps[
        "model"
    ]

    feature_names = (
        preprocessor.get_feature_names_out()
    )

    coefficients = np.asarray(
        linear_model.coef_,
        dtype=float,
    )

    if len(feature_names) != len(coefficients):
        raise ValueError(
            "Feature-name and coefficient counts do not match."
        )

    coefficient_df = pd.DataFrame(
        {
            "specification": specification,
            "horizon": horizon,
            "feature": feature_names,
            "coefficient": coefficients,
        }
    )

    intercept_row = pd.DataFrame(
        {
            "specification": [
                specification
            ],
            "horizon": [
                horizon
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


def build_prediction_dataset(
    model_df: pd.DataFrame,
    predicted_values: np.ndarray,
    specification: str,
    evaluation_type: str,
    held_out_season: str | None = None,
) -> pd.DataFrame:
    """
    Build one standardized prediction output dataset.
    """

    validate_specification(
        specification
    )

    prediction_df = model_df[
        [
            "season",
            "horizon",
            BLOCK_FEATURE,
            "block_start_date",
            "block_end_date",
            TARGET_COLUMN,
        ]
    ].copy()

    prediction_df[
        "predicted_crush_tonnes"
    ] = predicted_values

    prediction_df[
        "residual_tonnes"
    ] = (
        prediction_df[TARGET_COLUMN]
        - prediction_df[
            "predicted_crush_tonnes"
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


def fit_full_sample_model(
    model_df: pd.DataFrame,
    horizon: int,
    specification: str,
) -> tuple[
    Pipeline,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, float],
]:
    """
    Fit one aggregate baseline model on the complete sample.
    """

    feature_columns = get_feature_columns(
        specification
    )

    features = model_df[
        feature_columns
    ]

    target = model_df[
        TARGET_COLUMN
    ]

    model_pipeline = build_model_pipeline(
        specification=specification
    )

    model_pipeline.fit(
        features,
        target,
    )

    fitted_values = model_pipeline.predict(
        features
    )

    prediction_df = build_prediction_dataset(
        model_df=model_df,
        predicted_values=fitted_values,
        specification=specification,
        evaluation_type="in_sample",
    )

    coefficient_df = extract_coefficients(
        fitted_pipeline=model_pipeline,
        horizon=horizon,
        specification=specification,
    )

    metrics = calculate_metrics(
        actual=target,
        predicted=fitted_values,
    )

    return (
        model_pipeline,
        prediction_df,
        coefficient_df,
        metrics,
    )


def run_leave_one_season_out_cv(
    model_df: pd.DataFrame,
    horizon: int,
    specification: str,
) -> tuple[
    pd.DataFrame,
    dict[str, float],
]:
    """
    Evaluate one model through leave-one-season-out
    cross-validation.

    Each fold excludes one complete harvest season. The scaler,
    block encoder, and regression model are estimated using only
    the remaining training seasons.
    """

    feature_columns = get_feature_columns(
        specification
    )

    seasons = sorted(
        model_df[
            "season"
        ].unique()
    )

    if len(seasons) < 3:
        raise ValueError(
            "At least three seasons are required for "
            "leave-one-season-out cross-validation."
        )

    fold_predictions = []

    for test_season in seasons:
        training_df = model_df.loc[
            model_df["season"].ne(
                test_season
            )
        ].copy()

        testing_df = model_df.loc[
            model_df["season"].eq(
                test_season
            )
        ].copy()

        if training_df.empty:
            raise ValueError(
                "Training dataset is empty for held-out season "
                f"{test_season}."
            )

        if testing_df.empty:
            raise ValueError(
                "Testing dataset is empty for held-out season "
                f"{test_season}."
            )

        model_pipeline = build_model_pipeline(
            specification=specification
        )

        model_pipeline.fit(
            training_df[
                feature_columns
            ],
            training_df[
                TARGET_COLUMN
            ],
        )

        predicted_values = (
            model_pipeline.predict(
                testing_df[
                    feature_columns
                ]
            )
        )

        fold_df = build_prediction_dataset(
            model_df=testing_df,
            predicted_values=predicted_values,
            specification=specification,
            evaluation_type="leave_one_season_out",
            held_out_season=test_season,
        )

        fold_predictions.append(
            fold_df
        )

    prediction_df = pd.concat(
        fold_predictions,
        ignore_index=True,
    )

    expected_prediction_count = len(
        model_df
    )

    if len(
        prediction_df
    ) != expected_prediction_count:
        raise ValueError(
            "Leave-one-season-out prediction count does not "
            "match the original dataset."
        )

    if prediction_df.duplicated(
        subset=[
            "specification",
            "season",
            "horizon",
            BLOCK_FEATURE,
        ],
        keep=False,
    ).any():
        raise ValueError(
            "Leave-one-season-out predictions contain "
            "duplicate season-block rows."
        )

    metrics = calculate_metrics(
        actual=prediction_df[
            TARGET_COLUMN
        ],
        predicted=prediction_df[
            "predicted_crush_tonnes"
        ],
    )

    return (
        prediction_df,
        metrics,
    )


def build_model_summary(
    horizon: int,
    specification: str,
    model_df: pd.DataFrame,
    in_sample_metrics: dict[str, float],
    cv_metrics: dict[str, float],
) -> pd.DataFrame:
    """
    Build one-row model performance summary.
    """

    validate_specification(
        specification
    )

    summary_row = {
        "specification": specification,
        "horizon": horizon,
        "season_count": (
            model_df[
                "season"
            ].nunique()
        ),
        "observation_count": len(
            model_df
        ),
        "blocks_per_season": (
            model_df[
                BLOCK_FEATURE
            ].nunique()
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
    Compare weather-plus-block models against block-only models.

    Positive incremental R-squared means that weather increases
    out-of-sample explanatory power.

    Positive NRMSE or NMAE improvement means that weather lowers
    out-of-sample normalized prediction error.
    """

    required_specifications = set(
        MODEL_SPECIFICATIONS
    )

    observed_specifications = set(
        summary_df[
            "specification"
        ].unique()
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

    comparison_df = summary_df.pivot(
        index="horizon",
        columns="specification",
        values=[
            "cv_r_squared",
            "cv_rmse_tonnes",
            "cv_mae_tonnes",
            "cv_normalized_rmse",
            "cv_normalized_mae",
        ],
    )

    comparison_df.columns = [
        f"{metric}_{specification}"
        for metric, specification
        in comparison_df.columns
    ]

    comparison_df = (
        comparison_df
        .reset_index()
        .sort_values(
            "horizon"
        )
        .reset_index(
            drop=True
        )
    )

    comparison_df[
        "incremental_cv_r_squared"
    ] = (
        comparison_df[
            "cv_r_squared_weather_block"
        ]
        - comparison_df[
            "cv_r_squared_block_only"
        ]
    )

    comparison_df[
        "incremental_cv_rmse_improvement_tonnes"
    ] = (
        comparison_df[
            "cv_rmse_tonnes_block_only"
        ]
        - comparison_df[
            "cv_rmse_tonnes_weather_block"
        ]
    )

    comparison_df[
        "incremental_cv_mae_improvement_tonnes"
    ] = (
        comparison_df[
            "cv_mae_tonnes_block_only"
        ]
        - comparison_df[
            "cv_mae_tonnes_weather_block"
        ]
    )

    comparison_df[
        "incremental_cv_nrmse_improvement"
    ] = (
        comparison_df[
            "cv_normalized_rmse_block_only"
        ]
        - comparison_df[
            "cv_normalized_rmse_weather_block"
        ]
    )

    comparison_df[
        "incremental_cv_nmae_improvement"
    ] = (
        comparison_df[
            "cv_normalized_mae_block_only"
        ]
        - comparison_df[
            "cv_normalized_mae_weather_block"
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


def validate_output_tables(
    summary_df: pd.DataFrame,
    coefficient_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
) -> None:
    """
    Validate final model output tables before saving.
    """

    expected_summary_rows = (
        len(HORIZONS)
        * len(MODEL_SPECIFICATIONS)
    )

    if len(summary_df) != expected_summary_rows:
        raise ValueError(
            "Unexpected number of model-summary rows. "
            f"Expected {expected_summary_rows}, "
            f"found {len(summary_df)}."
        )

    if summary_df.duplicated(
        subset=[
            "specification",
            "horizon",
        ],
        keep=False,
    ).any():
        raise ValueError(
            "Model summary contains duplicate "
            "specification-horizon rows."
        )

    if coefficient_df.empty:
        raise ValueError(
            "Coefficient output is empty."
        )

    if prediction_df.empty:
        raise ValueError(
            "Prediction output is empty."
        )

    if comparison_df[
        "horizon"
    ].nunique() != len(HORIZONS):
        raise ValueError(
            "Incremental comparison does not contain "
            "all model horizons."
        )


def main() -> None:
    """
    Fit and evaluate aggregate baseline models for all horizons.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_summaries = []
    all_coefficients = []
    all_predictions = []

    print(
        "=" * 72
    )
    print(
        "Aggregate Baseline Model Estimation"
    )
    print(
        "=" * 72
    )

    for horizon in HORIZONS:
        model_df = load_horizon_dataset(
            horizon=horizon
        )

        for specification in MODEL_SPECIFICATIONS:
            (
                _,
                in_sample_predictions,
                coefficient_df,
                in_sample_metrics,
            ) = fit_full_sample_model(
                model_df=model_df,
                horizon=horizon,
                specification=specification,
            )

            (
                cv_predictions,
                cv_metrics,
            ) = run_leave_one_season_out_cv(
                model_df=model_df,
                horizon=horizon,
                specification=specification,
            )

            summary_df = build_model_summary(
                horizon=horizon,
                specification=specification,
                model_df=model_df,
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
                f"[OK] {specification}, h={horizon}: "
                f"CV R²={cv_metrics['r_squared']:.4f}, "
                f"CV RMSE={cv_metrics['rmse_tonnes']:,.0f}, "
                f"CV NRMSE={cv_metrics['normalized_rmse']:.4f}"
            )

    summary_df = pd.concat(
        all_summaries,
        ignore_index=True,
    )

    summary_df = (
        summary_df
        .sort_values(
            [
                "horizon",
                "specification",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    coefficient_df = pd.concat(
        all_coefficients,
        ignore_index=True,
    )

    coefficient_df = (
        coefficient_df
        .sort_values(
            [
                "horizon",
                "specification",
                "feature",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    prediction_df = pd.concat(
        all_predictions,
        ignore_index=True,
    )

    prediction_df = (
        prediction_df
        .sort_values(
            [
                "horizon",
                "specification",
                "evaluation_type",
                "season",
                BLOCK_FEATURE,
            ]
        )
        .reset_index(
            drop=True
        )
    )

    comparison_df = (
        build_incremental_comparison(
            summary_df
        )
    )

    validate_output_tables(
        summary_df=summary_df,
        coefficient_df=coefficient_df,
        prediction_df=prediction_df,
        comparison_df=comparison_df,
    )

    summary_path = (
        OUTPUT_DIR
        / "aggregate_baseline_model_summary.csv"
    )

    coefficient_path = (
        OUTPUT_DIR
        / "aggregate_baseline_coefficients.csv"
    )

    prediction_path = (
        OUTPUT_DIR
        / "aggregate_baseline_predictions.csv"
    )

    comparison_path = (
        OUTPUT_DIR
        / "aggregate_baseline_incremental_comparison.csv"
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

    print(
        "-" * 72
    )
    print(
        "Model Summary"
    )
    print(
        "-" * 72
    )
    print(
        summary_df.to_string(
            index=False
        )
    )

    print(
        "-" * 72
    )
    print(
        "Incremental Weather Contribution"
    )
    print(
        "-" * 72
    )
    print(
        comparison_df.to_string(
            index=False
        )
    )

    print(
        "-" * 72
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
    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()