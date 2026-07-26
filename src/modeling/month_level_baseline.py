"""
Rainfall Month-Level OLS Baseline

Fit month-level rainfall OLS models for harvest aggregation
horizons h = 1, 2, 3, 4, 5.

Each model uses:

- September-April monthly rainfall
- Growing-season average temperature as a control
- Harvest-block fixed effects
- Leave-one-season-out cross-validation
- Fold-specific weather standardization

The module also reports matrix-rank, condition-number,
singular-value, prediction, and coefficient diagnostics.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import StandardScaler

from src.modeling.aggregate_baseline_data import HORIZONS
from src.modeling.month_level_baseline_data import (
    RAINFALL_FEATURES,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "month_level_baseline"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "month_level_baseline_results"
)

TEMPERATURE_CONTROL = (
    "growing_season_average_temperature"
)

WEATHER_FEATURES = (
    *RAINFALL_FEATURES,
    TEMPERATURE_CONTROL,
)

TARGET_COLUMN = "block_crush_tonnes"


def calculate_rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """Calculate root mean squared error."""

    return float(
        np.sqrt(
            mean_squared_error(
                actual,
                predicted,
            )
        )
    )


def calculate_condition_number(
    matrix: np.ndarray,
) -> float:
    """
    Calculate a condition number from singular values.

    Return infinity when the smallest singular value is
    numerically zero.
    """

    singular_values = np.linalg.svd(
        matrix,
        compute_uv=False,
    )

    if singular_values.size == 0:
        return float("nan")

    smallest_value = singular_values[-1]

    tolerance = (
        np.finfo(float).eps
        * max(matrix.shape)
        * singular_values[0]
    )

    if smallest_value <= tolerance:
        return float("inf")

    return float(
        singular_values[0]
        / smallest_value
    )


def load_horizon_dataset(
    horizon: int,
    weather_features: tuple[str, ...] = WEATHER_FEATURES,
) -> pd.DataFrame:
    """Load and validate one month-level horizon dataset."""

    if horizon not in HORIZONS:
        raise ValueError(
            f"Unsupported horizon: {horizon}."
        )

    input_path = (
        INPUT_DIR
        / f"month_level_baseline_h{horizon}.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(
            "Month-level baseline dataset not found: "
            f"{input_path}"
        )

    dataframe = pd.read_csv(
        input_path
    )

    if dataframe.empty:
        raise ValueError(
            f"Month-level h={horizon} dataset is empty."
        )

    required_columns = {
        "season",
        "horizon",
        "harvest_block_order",
        "block_start_date",
        "block_end_date",
        TARGET_COLUMN,
        *weather_features,
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Month-level h={horizon} dataset is "
            "missing columns: "
            f"{sorted(missing_columns)}"
        )

    if not dataframe["horizon"].eq(
        horizon
    ).all():
        raise ValueError(
            f"Unexpected horizon values in h={horizon} "
            "dataset."
        )

    numeric_columns = [
        "harvest_block_order",
        TARGET_COLUMN,
        *weather_features,
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="raise",
        )

    validation_columns = [
        "season",
        "horizon",
        "harvest_block_order",
        TARGET_COLUMN,
        *weather_features,
    ]

    if dataframe[
        validation_columns
    ].isna().any().any():
        raise ValueError(
            f"Month-level h={horizon} dataset contains "
            "missing model values."
        )

    duplicate_rows = dataframe.duplicated(
        subset=[
            "season",
            "harvest_block_order",
        ],
        keep=False,
    )

    if duplicate_rows.any():
        raise ValueError(
            f"Month-level h={horizon} dataset contains "
            "duplicate season-block rows."
        )

    if dataframe["season"].nunique() < 3:
        raise ValueError(
            "At least three seasons are required for "
            "leave-one-season-out evaluation."
        )

    block_levels = sorted(
        dataframe[
            "harvest_block_order"
        ].unique()
    )

    expected_block_levels = set(
        block_levels
    )

    for season, season_df in dataframe.groupby(
        "season"
    ):
        season_block_levels = set(
            season_df[
                "harvest_block_order"
            ].unique()
        )

        if (
            season_block_levels
            != expected_block_levels
        ):
            raise ValueError(
                f"Season {season} does not contain the "
                f"expected harvest blocks for h={horizon}."
            )

    return (
        dataframe
        .sort_values(
            [
                "season",
                "harvest_block_order",
            ]
        )
        .reset_index(drop=True)
    )


def build_block_fixed_effects(
    dataframe: pd.DataFrame,
    block_levels: list[int],
) -> tuple[np.ndarray, list[str]]:
    """
    Build block fixed-effect dummy variables.

    The first harvest block is the reference category.
    """

    fixed_effect_columns = []
    fixed_effect_names = []

    for block_level in block_levels[1:]:
        fixed_effect_columns.append(
            dataframe[
                "harvest_block_order"
            ]
            .eq(block_level)
            .astype(float)
            .to_numpy()
        )

        fixed_effect_names.append(
            f"block_fe_{block_level}"
        )

    if not fixed_effect_columns:
        return (
            np.empty(
                (
                    len(dataframe),
                    0,
                )
            ),
            fixed_effect_names,
        )

    return (
        np.column_stack(
            fixed_effect_columns
        ),
        fixed_effect_names,
    )


def get_unique_season_weather(
    dataframe: pd.DataFrame,
    weather_features: tuple[str, ...] = WEATHER_FEATURES,
) -> pd.DataFrame:
    """
    Return one weather-feature row per season.

    Weather values repeat across harvest blocks, so matrix
    diagnostics must operate at the season level.
    """

    season_weather = dataframe[
        [
            "season",
            *weather_features,
        ]
    ].drop_duplicates(
        subset=["season"]
    )

    if (
        len(season_weather)
        != dataframe["season"].nunique()
    ):
        raise ValueError(
            "Weather predictors are not constant within "
            "each season."
        )

    return (
        season_weather
        .sort_values("season")
        .reset_index(drop=True)
    )


def build_fold_diagnostics(
    horizon: int,
    held_out_season: str,
    train_dataframe: pd.DataFrame,
    test_dataframe: pd.DataFrame,
    scaled_season_weather: np.ndarray,
    augmented_design_matrix: np.ndarray,
    actual: np.ndarray,
    predicted: np.ndarray,
    weather_features: tuple[str, ...] = WEATHER_FEATURES,
) -> dict[str, object]:
    """Build matrix and prediction diagnostics for one fold."""

    weather_rank = int(
        np.linalg.matrix_rank(
            scaled_season_weather
        )
    )

    weather_singular_values = np.linalg.svd(
        scaled_season_weather,
        compute_uv=False,
    )

    augmented_design_rank = int(
        np.linalg.matrix_rank(
            augmented_design_matrix
        )
    )

    training_season_count = (
        train_dataframe["season"].nunique()
    )

    diagnostics: dict[str, object] = {
        "horizon": horizon,
        "held_out_season": held_out_season,
        "training_seasons": training_season_count,
        "training_observations": len(
            train_dataframe
        ),
        "test_observations": len(
            test_dataframe
        ),
        "weather_predictor_count": len(
            weather_features
        ),
        "weather_max_rank_after_centering": min(
            len(weather_features),
            training_season_count - 1,
        ),
        "weather_rank": weather_rank,
        "weather_full_column_rank": (
            weather_rank
            == len(weather_features)
        ),
        "weather_condition_number": (
            calculate_condition_number(
                scaled_season_weather
            )
        ),
        "augmented_design_columns": (
            augmented_design_matrix.shape[1]
        ),
        "augmented_design_rank": (
            augmented_design_rank
        ),
        "augmented_design_full_column_rank": (
            augmented_design_rank
            == augmented_design_matrix.shape[1]
        ),
        "augmented_design_condition_number": (
            calculate_condition_number(
                augmented_design_matrix
            )
        ),
        "fold_rmse": calculate_rmse(
            actual,
            predicted,
        ),
        "fold_mae": float(
            mean_absolute_error(
                actual,
                predicted,
            )
        ),
        "fold_r_squared": float(
            r2_score(
                actual,
                predicted,
            )
        ),
    }

    for index, singular_value in enumerate(
        weather_singular_values,
        start=1,
    ):
        diagnostics[
            f"weather_singular_value_{index}"
        ] = float(
            singular_value
        )

    return diagnostics


def build_coefficient_rows(
    horizon: int,
    held_out_season: str,
    model: LinearRegression,
    scaler: StandardScaler,
    block_fixed_effect_names: list[str],
    weather_features: tuple[str, ...] = WEATHER_FEATURES,
) -> list[dict[str, object]]:
    """
    Build standardized and raw-unit coefficient rows.

    Standardized weather coefficients measure the target
    response to a one-standard-deviation predictor change.
    """

    weather_predictor_count = len(
        weather_features
    )

    standardized_weather_coefficients = (
        model.coef_[
            :weather_predictor_count
        ]
    )

    raw_weather_coefficients = (
        standardized_weather_coefficients
        / scaler.scale_
    )

    raw_intercept = float(
        model.intercept_
        - np.sum(
            standardized_weather_coefficients
            * scaler.mean_
            / scaler.scale_
        )
    )

    rows = [
        {
            "horizon": horizon,
            "held_out_season": held_out_season,
            "term": "intercept",
            "term_type": "intercept",
            "coefficient_standardized": float(
                model.intercept_
            ),
            "coefficient_raw": raw_intercept,
        }
    ]

    for feature_index, feature_name in enumerate(
        weather_features
    ):
        rows.append(
            {
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "term": feature_name,
                "term_type": "weather",
                "coefficient_standardized": float(
                    standardized_weather_coefficients[
                        feature_index
                    ]
                ),
                "coefficient_raw": float(
                    raw_weather_coefficients[
                        feature_index
                    ]
                ),
            }
        )

    block_coefficients = model.coef_[
        weather_predictor_count:
    ]

    for block_name, coefficient in zip(
        block_fixed_effect_names,
        block_coefficients,
        strict=True,
    ):
        rows.append(
            {
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "term": block_name,
                "term_type": (
                    "block_fixed_effect"
                ),
                "coefficient_standardized": float(
                    coefficient
                ),
                "coefficient_raw": float(
                    coefficient
                ),
            }
        )

    return rows


def run_loso_for_horizon(
    dataframe: pd.DataFrame,
    horizon: int,
    weather_features: tuple[str, ...] = WEATHER_FEATURES,
    model_name: str = "rainfall_month_level_ols",
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, object],
]:
    """
    Run leave-one-season-out OLS for one horizon.
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

        training_season_weather = (
            get_unique_season_weather(
                dataframe=train_dataframe,
                weather_features=weather_features,
            )
        )

        scaler = StandardScaler()

        scaler.fit(
            training_season_weather[
                list(weather_features)
            ]
        )

        scaled_training_season_weather = (
            scaler.transform(
                training_season_weather[
                    list(weather_features)
                ]
            )
        )

        scaled_train_weather = scaler.transform(
            train_dataframe[
                list(weather_features)
            ]
        )

        scaled_test_weather = scaler.transform(
            test_dataframe[
                list(weather_features)
            ]
        )

        (
            train_block_fixed_effects,
            block_fixed_effect_names,
        ) = build_block_fixed_effects(
            dataframe=train_dataframe,
            block_levels=block_levels,
        )

        (
            test_block_fixed_effects,
            _,
        ) = build_block_fixed_effects(
            dataframe=test_dataframe,
            block_levels=block_levels,
        )

        train_design_matrix = np.column_stack(
            [
                scaled_train_weather,
                train_block_fixed_effects,
            ]
        )

        test_design_matrix = np.column_stack(
            [
                scaled_test_weather,
                test_block_fixed_effects,
            ]
        )

        augmented_train_design_matrix = (
            np.column_stack(
                [
                    np.ones(
                        len(train_design_matrix)
                    ),
                    train_design_matrix,
                ]
            )
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

        for row_index, (
            (_, observation),
            predicted_value,
        ) in enumerate(
            zip(
                test_dataframe.iterrows(),
                test_prediction,
                strict=True,
            )
        ):
            actual_value = float(
                observation[TARGET_COLUMN]
            )

            prediction_rows.append(
                {
                    "horizon": horizon,
                    "held_out_season": (
                        held_out_season
                    ),
                    "season": observation[
                        "season"
                    ],
                    "harvest_block_order": int(
                        observation[
                            "harvest_block_order"
                        ]
                    ),
                    "block_start_date": (
                        observation[
                            "block_start_date"
                        ]
                    ),
                    "block_end_date": (
                        observation[
                            "block_end_date"
                        ]
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
                    "test_row_order": row_index + 1,
                }
            )

        coefficient_rows.extend(
            build_coefficient_rows(
                horizon=horizon,
                held_out_season=(
                    held_out_season
                ),
                model=model,
                scaler=scaler,
                block_fixed_effect_names=(
                    block_fixed_effect_names
                ),
                weather_features=weather_features,
            )
        )

        diagnostic_rows.append(
            build_fold_diagnostics(
                horizon=horizon,
                held_out_season=(
                    held_out_season
                ),
                train_dataframe=(
                    train_dataframe
                ),
                test_dataframe=(
                    test_dataframe
                ),
                scaled_season_weather=(
                    scaled_training_season_weather
                ),
                augmented_design_matrix=(
                    augmented_train_design_matrix
                ),
                actual=test_target,
                predicted=test_prediction,
                weather_features=weather_features,
            )
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

    full_season_weather = (
        get_unique_season_weather(
            dataframe=dataframe,
            weather_features=weather_features,
        )
    )

    full_weather_scaler = StandardScaler()

    full_scaled_weather = (
        full_weather_scaler.fit_transform(
            full_season_weather[
                list(weather_features)
            ]
        )
    )

    actual_all = predictions_df[
        "actual_block_crush_tonnes"
    ].to_numpy()

    predicted_all = predictions_df[
        "predicted_block_crush_tonnes"
    ].to_numpy()

    summary = {
        "model": model_name,
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
        "weather_predictor_count": len(
            weather_features
        ),
        "full_sample_weather_rank": int(
            np.linalg.matrix_rank(
                full_scaled_weather
            )
        ),
        "full_sample_weather_max_rank": min(
            len(weather_features),
            dataframe["season"].nunique() - 1,
        ),
        "full_sample_weather_condition_number": (
            calculate_condition_number(
                full_scaled_weather
            )
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
        "all_folds_weather_full_rank": bool(
            diagnostics_df[
                "weather_full_column_rank"
            ].all()
        ),
        "all_folds_design_full_rank": bool(
            diagnostics_df[
                "augmented_design_full_column_rank"
            ].all()
        ),
        "maximum_fold_weather_condition_number": float(
            diagnostics_df[
                "weather_condition_number"
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
    """Summarize coefficient stability across LOSO folds."""

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
            coefficient_standardized_mean=(
                "coefficient_standardized",
                "mean",
            ),
            coefficient_standardized_std=(
                "coefficient_standardized",
                "std",
            ),
            coefficient_standardized_min=(
                "coefficient_standardized",
                "min",
            ),
            coefficient_standardized_max=(
                "coefficient_standardized",
                "max",
            ),
            coefficient_raw_mean=(
                "coefficient_raw",
                "mean",
            ),
            coefficient_raw_std=(
                "coefficient_raw",
                "std",
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


def main() -> None:
    """
    Run rainfall month-level OLS models for every horizon.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_predictions = []
    all_coefficients = []
    all_diagnostics = []
    summary_rows = []

    print("=" * 72)
    print("Rainfall Month-Level OLS Baseline")
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
            f"rank={summary['full_sample_weather_rank']}/"
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

    predictions_output.to_csv(
        OUTPUT_DIR
        / "rainfall_month_level_ols_predictions.csv",
        index=False,
    )

    coefficients_output.to_csv(
        OUTPUT_DIR
        / "rainfall_month_level_ols_coefficients.csv",
        index=False,
    )

    coefficient_summary_output.to_csv(
        OUTPUT_DIR
        / "rainfall_month_level_ols_coefficient_summary.csv",
        index=False,
    )

    diagnostics_output.to_csv(
        OUTPUT_DIR
        / "rainfall_month_level_ols_fold_diagnostics.csv",
        index=False,
    )

    summary_output.to_csv(
        OUTPUT_DIR
        / "rainfall_month_level_ols_summary.csv",
        index=False,
    )

    print("=" * 72)
    print(
        "Results saved to:"
    )
    print(OUTPUT_DIR)
    print("=" * 72)


if __name__ == "__main__":
    main()