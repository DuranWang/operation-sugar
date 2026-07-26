"""
Temperature Month-Level Ridge Baseline

Fit partially penalized Ridge models for harvest aggregation
horizons h = 1, 2, 3, 4, 5.

Penalized predictors:

- September-April monthly rainfall
- September-April monthly temperature

Unpenalized predictors:

- Intercept
- Harvest-block fixed effects

Model evaluation uses nested leave-one-season-out
cross-validation:

- Outer LOSO estimates generalization performance.
- Inner LOSO selects the Ridge penalty alpha.
- Weather standardization is fitted separately inside every
  training fold to avoid data leakage.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
)
from sklearn.preprocessing import StandardScaler

from src.modeling.aggregate_baseline_data import HORIZONS
from src.modeling.month_level_baseline_data import (
    RAINFALL_FEATURES,
    TEMPERATURE_FEATURES,
)
from src.modeling.month_level_baseline import (
    TARGET_COLUMN,
    build_block_fixed_effects,
    calculate_condition_number,
    calculate_rmse,
    get_unique_season_weather,
    load_horizon_dataset,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WEATHER_FEATURES = (
    *RAINFALL_FEATURES,
    *TEMPERATURE_FEATURES,
)

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

RAINFALL_RIDGE_SUMMARY_PATH = (
    OUTPUT_DIR
    / "rainfall_month_level_ridge_summary.csv"
)

TEMPERATURE_RIDGE_SUMMARY_PATH = (
    OUTPUT_DIR
    / "temperature_month_level_ridge_summary.csv"
)

ALPHA_GRID = tuple(
    float(value)
    for value in np.logspace(
        -4,
        8,
        49,
    )
)


def build_unpenalized_design_matrix(
    dataframe: pd.DataFrame,
    block_levels: list[int],
) -> tuple[np.ndarray, list[str]]:
    """
    Build the intercept and harvest-block fixed effects.

    These columns are not penalized by Ridge.
    """

    (
        block_fixed_effects,
        block_fixed_effect_names,
    ) = build_block_fixed_effects(
        dataframe=dataframe,
        block_levels=block_levels,
    )

    design_matrix = np.column_stack(
        [
            np.ones(
                len(dataframe),
                dtype=float,
            ),
            block_fixed_effects,
        ]
    )

    term_names = [
        "intercept",
        *block_fixed_effect_names,
    ]

    return (
        design_matrix,
        term_names,
    )


def fit_weather_scaler(
    training_dataframe: pd.DataFrame,
) -> StandardScaler:
    """
    Fit a weather scaler using one observation per season.

    Weather values repeat across harvest blocks, so the scaler
    is fitted at the season level rather than giving seasons
    with repeated block rows additional conceptual weight.
    """

    season_weather = get_unique_season_weather(
        dataframe=training_dataframe,
        weather_features=WEATHER_FEATURES,
    )

    scaler = StandardScaler()

    scaler.fit(
        season_weather[
            list(WEATHER_FEATURES)
        ]
    )

    return scaler


def residualize_against_unpenalized(
    values: np.ndarray,
    unpenalized_design: np.ndarray,
) -> np.ndarray:
    """
    Remove the linear projection of values onto the
    unpenalized design matrix.
    """

    projection_coefficients = np.linalg.lstsq(
        unpenalized_design,
        values,
        rcond=None,
    )[0]

    return (
        values
        - unpenalized_design
        @ projection_coefficients
    )


def fit_partially_penalized_ridge(
    weather_matrix: np.ndarray,
    unpenalized_design: np.ndarray,
    target: np.ndarray,
    alpha: float,
) -> tuple[
    np.ndarray,
    np.ndarray,
    float,
]:
    """
    Fit Ridge while penalizing only weather coefficients.

    The objective is:

        mean squared error
        + alpha * sum(weather coefficient squared)

    Intercept and harvest-block fixed effects are not
    penalized.
    """

    if alpha <= 0:
        raise ValueError(
            "Ridge alpha must be positive."
        )

    if len(weather_matrix) != len(target):
        raise ValueError(
            "Weather matrix and target have different "
            "numbers of observations."
        )

    if len(unpenalized_design) != len(target):
        raise ValueError(
            "Unpenalized design and target have different "
            "numbers of observations."
        )

    residual_weather = (
        residualize_against_unpenalized(
            values=weather_matrix,
            unpenalized_design=(
                unpenalized_design
            ),
        )
    )

    residual_target = (
        residualize_against_unpenalized(
            values=target,
            unpenalized_design=(
                unpenalized_design
            ),
        )
    )

    observation_count = len(target)

    weather_gram_matrix = (
        residual_weather.T
        @ residual_weather
        / observation_count
    )

    weather_target_product = (
        residual_weather.T
        @ residual_target
        / observation_count
    )

    penalized_matrix = (
        weather_gram_matrix
        + alpha
        * np.eye(
            weather_matrix.shape[1]
        )
    )

    weather_coefficients = np.linalg.solve(
        penalized_matrix,
        weather_target_product,
    )

    unpenalized_coefficients = np.linalg.lstsq(
        unpenalized_design,
        (
            target
            - weather_matrix
            @ weather_coefficients
        ),
        rcond=None,
    )[0]

    weather_effective_degrees_of_freedom = float(
        np.trace(
            np.linalg.solve(
                penalized_matrix,
                weather_gram_matrix,
            )
        )
    )

    return (
        unpenalized_coefficients,
        weather_coefficients,
        weather_effective_degrees_of_freedom,
    )


def predict_partially_penalized_ridge(
    weather_matrix: np.ndarray,
    unpenalized_design: np.ndarray,
    unpenalized_coefficients: np.ndarray,
    weather_coefficients: np.ndarray,
) -> np.ndarray:
    """Generate predictions from a partially penalized model."""

    return (
        unpenalized_design
        @ unpenalized_coefficients
        + weather_matrix
        @ weather_coefficients
    )


def evaluate_inner_alpha(
    outer_training_dataframe: pd.DataFrame,
    block_levels: list[int],
    alpha: float,
) -> dict[str, float]:
    """
    Evaluate one alpha with inner leave-one-season-out CV.
    """

    inner_seasons = sorted(
        outer_training_dataframe[
            "season"
        ].unique()
    )

    actual_values = []
    predicted_values = []

    for inner_held_out_season in inner_seasons:
        inner_training_dataframe = (
            outer_training_dataframe.loc[
                outer_training_dataframe["season"]
                != inner_held_out_season
            ].copy()
        )

        inner_test_dataframe = (
            outer_training_dataframe.loc[
                outer_training_dataframe["season"]
                == inner_held_out_season
            ].copy()
        )

        scaler = fit_weather_scaler(
            inner_training_dataframe
        )

        inner_training_weather = scaler.transform(
            inner_training_dataframe[
                list(WEATHER_FEATURES)
            ]
        )

        inner_test_weather = scaler.transform(
            inner_test_dataframe[
                list(WEATHER_FEATURES)
            ]
        )

        (
            inner_training_unpenalized,
            _,
        ) = build_unpenalized_design_matrix(
            dataframe=inner_training_dataframe,
            block_levels=block_levels,
        )

        (
            inner_test_unpenalized,
            _,
        ) = build_unpenalized_design_matrix(
            dataframe=inner_test_dataframe,
            block_levels=block_levels,
        )

        inner_training_target = (
            inner_training_dataframe[
                TARGET_COLUMN
            ].to_numpy(
                dtype=float
            )
        )

        inner_test_target = (
            inner_test_dataframe[
                TARGET_COLUMN
            ].to_numpy(
                dtype=float
            )
        )

        (
            unpenalized_coefficients,
            weather_coefficients,
            _,
        ) = fit_partially_penalized_ridge(
            weather_matrix=(
                inner_training_weather
            ),
            unpenalized_design=(
                inner_training_unpenalized
            ),
            target=inner_training_target,
            alpha=alpha,
        )

        inner_prediction = (
            predict_partially_penalized_ridge(
                weather_matrix=inner_test_weather,
                unpenalized_design=(
                    inner_test_unpenalized
                ),
                unpenalized_coefficients=(
                    unpenalized_coefficients
                ),
                weather_coefficients=(
                    weather_coefficients
                ),
            )
        )

        actual_values.extend(
            inner_test_target.tolist()
        )

        predicted_values.extend(
            inner_prediction.tolist()
        )

    actual_array = np.asarray(
        actual_values,
        dtype=float,
    )

    predicted_array = np.asarray(
        predicted_values,
        dtype=float,
    )

    return {
        "alpha": alpha,
        "inner_rmse": calculate_rmse(
            actual_array,
            predicted_array,
        ),
        "inner_mae": float(
            mean_absolute_error(
                actual_array,
                predicted_array,
            )
        ),
        "inner_r_squared": float(
            r2_score(
                actual_array,
                predicted_array,
            )
        ),
    }


def select_alpha_with_inner_loso(
    outer_training_dataframe: pd.DataFrame,
    block_levels: list[int],
) -> tuple[
    float,
    pd.DataFrame,
]:
    """
    Select alpha using inner leave-one-season-out CV.

    In an exact tie, the larger alpha is selected because it
    produces the more strongly regularized model.
    """

    score_rows = []

    for alpha in ALPHA_GRID:
        score_rows.append(
            evaluate_inner_alpha(
                outer_training_dataframe=(
                    outer_training_dataframe
                ),
                block_levels=block_levels,
                alpha=alpha,
            )
        )

    scores_df = pd.DataFrame(
        score_rows
    )

    best_index = (
        scores_df
        .sort_values(
            [
                "inner_rmse",
                "alpha",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .index[0]
    )

    scores_df["selected_alpha"] = False

    scores_df.loc[
        best_index,
        "selected_alpha",
    ] = True

    selected_alpha = float(
        scores_df.loc[
            best_index,
            "alpha",
        ]
    )

    return (
        selected_alpha,
        scores_df,
    )


def build_coefficient_rows(
    horizon: int,
    held_out_season: str,
    scaler: StandardScaler,
    unpenalized_term_names: list[str],
    unpenalized_coefficients: np.ndarray,
    weather_coefficients: np.ndarray,
    selected_alpha: float,
) -> list[dict[str, object]]:
    """
    Export standardized and raw-unit Ridge coefficients.
    """

    raw_weather_coefficients = (
        weather_coefficients
        / scaler.scale_
    )

    raw_intercept = float(
        unpenalized_coefficients[0]
        - np.sum(
            weather_coefficients
            * scaler.mean_
            / scaler.scale_
        )
    )

    rows = []

    for term_index, term_name in enumerate(
        unpenalized_term_names
    ):
        standardized_coefficient = float(
            unpenalized_coefficients[
                term_index
            ]
        )

        if term_name == "intercept":
            raw_coefficient = raw_intercept
            term_type = "intercept"
        else:
            raw_coefficient = (
                standardized_coefficient
            )
            term_type = "block_fixed_effect"

        rows.append(
            {
                "model": (
                    "joint_month_level_ridge"
                ),
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "selected_alpha": (
                    selected_alpha
                ),
                "term": term_name,
                "term_type": term_type,
                "coefficient_standardized": (
                    standardized_coefficient
                ),
                "coefficient_raw": (
                    raw_coefficient
                ),
            }
        )

    for feature_index, feature_name in enumerate(
        WEATHER_FEATURES
    ):
        rows.append(
            {
                "model": (
                    "joint_month_level_ridge"
                ),
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "selected_alpha": (
                    selected_alpha
                ),
                "term": feature_name,
                "term_type": "weather",
                "coefficient_standardized": float(
                    weather_coefficients[
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

    return rows


def run_nested_loso_for_horizon(
    dataframe: pd.DataFrame,
    horizon: int,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, object],
]:
    """
    Run nested leave-one-season-out Ridge evaluation.
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
    inner_score_outputs = []

    for held_out_season in seasons:
        outer_training_dataframe = dataframe.loc[
            dataframe["season"]
            != held_out_season
        ].copy()

        outer_test_dataframe = dataframe.loc[
            dataframe["season"]
            == held_out_season
        ].copy()

        (
            selected_alpha,
            inner_scores_df,
        ) = select_alpha_with_inner_loso(
            outer_training_dataframe=(
                outer_training_dataframe
            ),
            block_levels=block_levels,
        )

        inner_scores_df.insert(
            0,
            "outer_held_out_season",
            held_out_season,
        )

        inner_scores_df.insert(
            0,
            "horizon",
            horizon,
        )

        inner_score_outputs.append(
            inner_scores_df
        )

        scaler = fit_weather_scaler(
            outer_training_dataframe
        )

        outer_training_weather = (
            scaler.transform(
                outer_training_dataframe[
                    list(WEATHER_FEATURES)
                ]
            )
        )

        outer_test_weather = scaler.transform(
            outer_test_dataframe[
                list(WEATHER_FEATURES)
            ]
        )

        (
            outer_training_unpenalized,
            unpenalized_term_names,
        ) = build_unpenalized_design_matrix(
            dataframe=outer_training_dataframe,
            block_levels=block_levels,
        )

        (
            outer_test_unpenalized,
            _,
        ) = build_unpenalized_design_matrix(
            dataframe=outer_test_dataframe,
            block_levels=block_levels,
        )

        outer_training_target = (
            outer_training_dataframe[
                TARGET_COLUMN
            ].to_numpy(
                dtype=float
            )
        )

        outer_test_target = (
            outer_test_dataframe[
                TARGET_COLUMN
            ].to_numpy(
                dtype=float
            )
        )

        (
            unpenalized_coefficients,
            weather_coefficients,
            weather_effective_df,
        ) = fit_partially_penalized_ridge(
            weather_matrix=(
                outer_training_weather
            ),
            unpenalized_design=(
                outer_training_unpenalized
            ),
            target=outer_training_target,
            alpha=selected_alpha,
        )

        outer_test_prediction = (
            predict_partially_penalized_ridge(
                weather_matrix=outer_test_weather,
                unpenalized_design=(
                    outer_test_unpenalized
                ),
                unpenalized_coefficients=(
                    unpenalized_coefficients
                ),
                weather_coefficients=(
                    weather_coefficients
                ),
            )
        )

        for observation, predicted_value in zip(
            outer_test_dataframe.itertuples(
                index=False
            ),
            outer_test_prediction,
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
                    "model": (
                        "joint_month_level_ridge"
                    ),
                    "horizon": horizon,
                    "held_out_season": (
                        held_out_season
                    ),
                    "selected_alpha": (
                        selected_alpha
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
                scaler=scaler,
                unpenalized_term_names=(
                    unpenalized_term_names
                ),
                unpenalized_coefficients=(
                    unpenalized_coefficients
                ),
                weather_coefficients=(
                    weather_coefficients
                ),
                selected_alpha=selected_alpha,
            )
        )

        training_season_weather = (
            get_unique_season_weather(
                dataframe=outer_training_dataframe,
                weather_features=WEATHER_FEATURES,
            )
        )

        scaled_training_season_weather = (
            scaler.transform(
                training_season_weather[
                    list(WEATHER_FEATURES)
                ]
            )
        )

        diagnostic_rows.append(
            {
                "model": (
                    "joint_month_level_ridge"
                ),
                "horizon": horizon,
                "held_out_season": (
                    held_out_season
                ),
                "training_seasons": (
                    outer_training_dataframe[
                        "season"
                    ].nunique()
                ),
                "training_observations": len(
                    outer_training_dataframe
                ),
                "test_observations": len(
                    outer_test_dataframe
                ),
                "selected_alpha": (
                    selected_alpha
                ),
                "selected_alpha_at_minimum_grid": (
                    selected_alpha
                    == min(ALPHA_GRID)
                ),
                "selected_alpha_at_maximum_grid": (
                    selected_alpha
                    == max(ALPHA_GRID)
                ),
                "weather_rank": int(
                    np.linalg.matrix_rank(
                        scaled_training_season_weather
                    )
                ),
                "weather_condition_number": (
                    calculate_condition_number(
                        scaled_training_season_weather
                    )
                ),
                "weather_effective_degrees_of_freedom": (
                    weather_effective_df
                ),
                "fold_rmse": calculate_rmse(
                    outer_test_target,
                    outer_test_prediction,
                ),
                "fold_mae": float(
                    mean_absolute_error(
                        outer_test_target,
                        outer_test_prediction,
                    )
                ),
                "fold_r_squared": float(
                    r2_score(
                        outer_test_target,
                        outer_test_prediction,
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

    inner_scores_output = pd.concat(
        inner_score_outputs,
        ignore_index=True,
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
        "model": "joint_month_level_ridge",
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
            WEATHER_FEATURES
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
        "selected_alpha_min": float(
            diagnostics_df[
                "selected_alpha"
            ].min()
        ),
        "selected_alpha_median": float(
            diagnostics_df[
                "selected_alpha"
            ].median()
        ),
        "selected_alpha_max": float(
            diagnostics_df[
                "selected_alpha"
            ].max()
        ),
        "mean_weather_effective_degrees_of_freedom": float(
            diagnostics_df[
                "weather_effective_degrees_of_freedom"
            ].mean()
        ),
        "maximum_alpha_boundary_fraction": float(
            diagnostics_df[
                "selected_alpha_at_maximum_grid"
            ].mean()
        ),
    }

    return (
        predictions_df,
        coefficients_df,
        diagnostics_df,
        inner_scores_output,
        summary,
    )


def build_coefficient_summary(
    coefficients_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize Ridge coefficients across outer folds."""

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


def load_summary_metrics(
    path: Path,
    prefix: str,
) -> pd.DataFrame:
    """Load model summary metrics for comparison."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required summary not found: {path}"
        )

    dataframe = pd.read_csv(
        path
    )

    required_columns = {
        "horizon",
        "loso_rmse",
        "loso_mae",
        "loso_r_squared",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Summary is missing columns: "
            f"{sorted(missing_columns)}"
        )

    return dataframe[
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
        ]
    ].rename(
        columns={
            "loso_rmse": f"{prefix}_rmse",
            "loso_mae": f"{prefix}_mae",
            "loso_r_squared": (
                f"{prefix}_r_squared"
            ),
        }
    )


def build_model_comparison(
    ridge_summary_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare Joint Ridge with block-only and the two
    single-weather-family Ridge models.
    """

    block_metrics = load_summary_metrics(
        BLOCK_ONLY_SUMMARY_PATH,
        "block_only",
    )

    rainfall_ridge_metrics = load_summary_metrics(
        RAINFALL_RIDGE_SUMMARY_PATH,
        "rainfall_ridge",
    )

    temperature_ridge_metrics = load_summary_metrics(
        TEMPERATURE_RIDGE_SUMMARY_PATH,
        "temperature_ridge",
    )

    joint_ridge_metrics = ridge_summary_df[
        [
            "horizon",
            "loso_rmse",
            "loso_mae",
            "loso_r_squared",
            "selected_alpha_min",
            "selected_alpha_median",
            "selected_alpha_max",
            (
                "mean_weather_effective_"
                "degrees_of_freedom"
            ),
            "maximum_alpha_boundary_fraction",
        ]
    ].rename(
        columns={
            "loso_rmse": "joint_ridge_rmse",
            "loso_mae": "joint_ridge_mae",
            "loso_r_squared": (
                "joint_ridge_r_squared"
            ),
        }
    )

    comparison_df = (
        block_metrics
        .merge(
            rainfall_ridge_metrics,
            on="horizon",
            how="inner",
            validate="one_to_one",
        )
        .merge(
            temperature_ridge_metrics,
            on="horizon",
            how="inner",
            validate="one_to_one",
        )
        .merge(
            joint_ridge_metrics,
            on="horizon",
            how="inner",
            validate="one_to_one",
        )
    )

    comparison_df[
        "joint_vs_block_rmse_improvement_percent"
    ] = (
        (
            comparison_df["block_only_rmse"]
            - comparison_df["joint_ridge_rmse"]
        )
        / comparison_df["block_only_rmse"]
        * 100
    )

    comparison_df[
        "joint_vs_block_mae_improvement_percent"
    ] = (
        (
            comparison_df["block_only_mae"]
            - comparison_df["joint_ridge_mae"]
        )
        / comparison_df["block_only_mae"]
        * 100
    )

    comparison_df[
        "joint_vs_block_r_squared_improvement"
    ] = (
        comparison_df["joint_ridge_r_squared"]
        - comparison_df["block_only_r_squared"]
    )

    comparison_df[
        "joint_vs_rainfall_ridge_rmse_improvement_percent"
    ] = (
        (
            comparison_df["rainfall_ridge_rmse"]
            - comparison_df["joint_ridge_rmse"]
        )
        / comparison_df["rainfall_ridge_rmse"]
        * 100
    )

    comparison_df[
        "joint_vs_rainfall_ridge_mae_improvement_percent"
    ] = (
        (
            comparison_df["rainfall_ridge_mae"]
            - comparison_df["joint_ridge_mae"]
        )
        / comparison_df["rainfall_ridge_mae"]
        * 100
    )

    comparison_df[
        "joint_vs_temperature_ridge_rmse_improvement_percent"
    ] = (
        (
            comparison_df["temperature_ridge_rmse"]
            - comparison_df["joint_ridge_rmse"]
        )
        / comparison_df["temperature_ridge_rmse"]
        * 100
    )

    comparison_df[
        "joint_vs_temperature_ridge_mae_improvement_percent"
    ] = (
        (
            comparison_df["temperature_ridge_mae"]
            - comparison_df["joint_ridge_mae"]
        )
        / comparison_df["temperature_ridge_mae"]
        * 100
    )

    return (
        comparison_df
        .sort_values("horizon")
        .reset_index(drop=True)
    )


def main() -> None:
    """Run nested-LOSO joint Ridge models."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_predictions = []
    all_coefficients = []
    all_diagnostics = []
    all_inner_scores = []
    summary_rows = []

    print("=" * 72)
    print("Joint Month-Level Ridge")
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
            inner_scores_df,
            summary,
        ) = run_nested_loso_for_horizon(
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

        all_inner_scores.append(
            inner_scores_df
        )

        summary_rows.append(
            summary
        )

        print(
            f"[OK] h={horizon}: "
            f"alpha median="
            f"{summary['selected_alpha_median']:.6g}, "
            f"weather df="
            f"{summary['mean_weather_effective_degrees_of_freedom']:.2f}, "
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

    inner_scores_output = pd.concat(
        all_inner_scores,
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
        build_model_comparison(
            summary_output
        )
    )

    predictions_output.to_csv(
        OUTPUT_DIR
        / "joint_month_level_ridge_predictions.csv",
        index=False,
    )

    coefficients_output.to_csv(
        OUTPUT_DIR
        / "joint_month_level_ridge_coefficients.csv",
        index=False,
    )

    coefficient_summary_output.to_csv(
        OUTPUT_DIR
        / "joint_month_level_ridge_coefficient_summary.csv",
        index=False,
    )

    diagnostics_output.to_csv(
        OUTPUT_DIR
        / "joint_month_level_ridge_fold_diagnostics.csv",
        index=False,
    )

    inner_scores_output.to_csv(
        OUTPUT_DIR
        / "joint_month_level_ridge_inner_cv_scores.csv",
        index=False,
    )

    summary_output.to_csv(
        OUTPUT_DIR
        / "joint_month_level_ridge_summary.csv",
        index=False,
    )

    comparison_output.to_csv(
        OUTPUT_DIR
        / "temperature_ridge_model_comparison.csv",
        index=False,
    )

    print("=" * 72)
    print("Joint Ridge Model Comparison")
    print("=" * 72)

    for row in comparison_output.itertuples(
        index=False
    ):
        print(
            f"h={row.horizon}: "
            f"vs block RMSE="
            f"{row.joint_vs_block_rmse_improvement_percent:+.2f}%, "
            f"vs rainfall Ridge RMSE="
            f"{row.joint_vs_rainfall_ridge_rmse_improvement_percent:+.2f}%, "
            f"vs temperature Ridge RMSE="
            f"{row.joint_vs_temperature_ridge_rmse_improvement_percent:+.2f}%, "
            f"ΔR² vs block="
            f"{row.joint_vs_block_r_squared_improvement:+.4f}"
        )

    print("=" * 72)
    print("Results saved to:")
    print(OUTPUT_DIR)
    print("=" * 72)


if __name__ == "__main__":
    main()