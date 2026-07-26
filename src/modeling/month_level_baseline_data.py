"""
Month-Level Baseline Dataset Construction

Build model-ready month-level weather-harvest datasets for
aggregation horizons h = 1, 2, 3, 4, 5.

The output contains:

- Eight monthly rainfall predictors
- Eight monthly temperature predictors
- Growing-season aggregate rainfall and temperature controls
- Harvest-block outcomes and positions

The same datasets support rainfall OLS, temperature OLS,
and joint regularized models.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.modeling.aggregate_baseline_data import (
    BASE_HARVEST_PERIODS,
    HARVEST_INPUT_PATH,
    HORIZONS,
    WEATHER_INPUT_PATH,
    build_base_harvest_periods,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "month_level_baseline"
)

GROWING_SEASON_MONTHS = (
    "sep",
    "oct",
    "nov",
    "dec",
    "jan",
    "feb",
    "mar",
    "apr",
)

RAINFALL_FEATURES = tuple(
    f"rainfall_{month}"
    for month in GROWING_SEASON_MONTHS
)

TEMPERATURE_FEATURES = tuple(
    f"temperature_{month}"
    for month in GROWING_SEASON_MONTHS
)

AGGREGATE_FEATURES = (
    "growing_season_total_rainfall",
    "growing_season_average_temperature",
)

MONTH_LEVEL_FEATURES = (
    *RAINFALL_FEATURES,
    *TEMPERATURE_FEATURES,
)


def load_month_level_weather_predictors(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load and validate complete São Paulo month-level
    weather predictors.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            "Weather dataset not found: "
            f"{input_path}"
        )

    weather_df = pd.read_csv(
        input_path
    )

    if weather_df.empty:
        raise ValueError(
            "Weather dataset is empty."
        )

    required_columns = {
        "state",
        "harvest_season",
        "has_complete_growing_season",
        "total_growing_season_rainfall",
        "average_growing_season_temperature",
        *MONTH_LEVEL_FEATURES,
    }

    missing_columns = (
        required_columns
        - set(weather_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Weather dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    weather_df = weather_df.loc[
        weather_df["state"].eq("SP")
    ].copy()

    if weather_df.empty:
        raise ValueError(
            "Weather dataset contains no São Paulo rows."
        )

    complete_flag = weather_df[
        "has_complete_growing_season"
    ]

    if complete_flag.dtype == object:
        normalized_flag = (
            complete_flag
            .astype(str)
            .str.strip()
            .str.lower()
        )

        invalid_flags = ~normalized_flag.isin(
            ["true", "false"]
        )

        if invalid_flags.any():
            raise ValueError(
                "Growing-season completion flag contains "
                "invalid values."
            )

        complete_flag = normalized_flag.eq(
            "true"
        )

    weather_df = weather_df.loc[
        complete_flag,
        [
            "harvest_season",
            "total_growing_season_rainfall",
            "average_growing_season_temperature",
            *MONTH_LEVEL_FEATURES,
        ],
    ].copy()

    if weather_df.empty:
        raise ValueError(
            "No complete growing seasons are available."
        )

    weather_df = weather_df.rename(
        columns={
            "harvest_season": "season",
            "total_growing_season_rainfall": (
                "growing_season_total_rainfall"
            ),
            "average_growing_season_temperature": (
                "growing_season_average_temperature"
            ),
        }
    )

    numeric_columns = [
        *MONTH_LEVEL_FEATURES,
        *AGGREGATE_FEATURES,
    ]

    for column in numeric_columns:
        weather_df[column] = pd.to_numeric(
            weather_df[column],
            errors="raise",
        )

    if weather_df[
        ["season", *numeric_columns]
    ].isna().any().any():
        raise ValueError(
            "Month-level weather predictors contain "
            "missing values."
        )

    duplicate_seasons = weather_df.duplicated(
        subset=["season"],
        keep=False,
    )

    if duplicate_seasons.any():
        duplicated_values = (
            weather_df.loc[
                duplicate_seasons,
                "season",
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            "Weather dataset contains duplicate seasons: "
            f"{sorted(duplicated_values)}"
        )

    if (
        weather_df[
            list(RAINFALL_FEATURES)
        ]
        < 0
    ).any().any():
        raise ValueError(
            "Monthly rainfall values cannot be negative."
        )

    monthly_rainfall_total = weather_df[
        list(RAINFALL_FEATURES)
    ].sum(axis=1)

    rainfall_matches = np.isclose(
        monthly_rainfall_total,
        weather_df[
            "growing_season_total_rainfall"
        ],
    )

    if not rainfall_matches.all():
        invalid_seasons = weather_df.loc[
            ~rainfall_matches,
            "season",
        ].tolist()

        raise ValueError(
            "Monthly rainfall does not reconcile with "
            "growing-season rainfall for seasons: "
            f"{invalid_seasons}"
        )

    monthly_temperature_average = weather_df[
        list(TEMPERATURE_FEATURES)
    ].mean(axis=1)

    temperature_matches = np.isclose(
        monthly_temperature_average,
        weather_df[
            "growing_season_average_temperature"
        ],
    )

    if not temperature_matches.all():
        invalid_seasons = weather_df.loc[
            ~temperature_matches,
            "season",
        ].tolist()

        raise ValueError(
            "Monthly temperature does not reconcile with "
            "growing-season temperature for seasons: "
            f"{invalid_seasons}"
        )

    return (
        weather_df
        .sort_values("season")
        .reset_index(drop=True)
    )


def build_month_level_horizon_dataset(
    base_period_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    horizon: int,
) -> pd.DataFrame:
    """
    Aggregate base harvest periods into non-overlapping
    blocks and attach month-level weather predictors.
    """

    if horizon not in HORIZONS:
        raise ValueError(
            f"Unsupported horizon: {horizon}."
        )

    usable_period_count = (
        BASE_HARVEST_PERIODS
        // horizon
    ) * horizon

    horizon_df = base_period_df.loc[
        base_period_df["base_period_order"]
        <= usable_period_count
    ].copy()

    horizon_df["harvest_block_order"] = (
        (
            horizon_df["base_period_order"]
            - 1
        )
        // horizon
        + 1
    )

    horizon_df = (
        horizon_df
        .groupby(
            [
                "season",
                "harvest_block_order",
            ],
            as_index=False,
        )
        .agg(
            block_start_date=(
                "base_period_start_date",
                "min",
            ),
            block_end_date=(
                "base_period_end_date",
                "max",
            ),
            block_crush_tonnes=(
                "base_period_crush_tonnes",
                "sum",
            ),
            base_period_count=(
                "base_period_order",
                "count",
            ),
        )
    )

    horizon_df["horizon"] = horizon

    model_df = horizon_df.merge(
        weather_df,
        on="season",
        how="inner",
        validate="many_to_one",
    )

    if model_df.empty:
        raise ValueError(
            "No overlapping month-level weather and "
            f"harvest seasons for h={horizon}."
        )

    if not model_df[
        "base_period_count"
    ].eq(horizon).all():
        raise ValueError(
            "Invalid harvest-block size detected "
            f"for h={horizon}."
        )

    expected_blocks_per_season = (
        BASE_HARVEST_PERIODS
        // horizon
    )

    block_counts = (
        model_df
        .groupby("season")[
            "harvest_block_order"
        ]
        .nunique()
    )

    if not block_counts.eq(
        expected_blocks_per_season
    ).all():
        raise ValueError(
            "Every season must contain exactly "
            f"{expected_blocks_per_season} blocks "
            f"for h={horizon}."
        )

    duplicate_rows = model_df.duplicated(
        subset=[
            "season",
            "harvest_block_order",
        ],
        keep=False,
    )

    if duplicate_rows.any():
        raise ValueError(
            "Month-level dataset contains duplicate "
            f"season-block rows for h={horizon}."
        )

    output_columns = [
        "season",
        "horizon",
        "harvest_block_order",
        "block_start_date",
        "block_end_date",
        "base_period_count",
        "block_crush_tonnes",
        *RAINFALL_FEATURES,
        "growing_season_average_temperature",
        *TEMPERATURE_FEATURES,
        "growing_season_total_rainfall",
    ]

    if model_df[
        output_columns
    ].isna().any().any():
        raise ValueError(
            "Month-level model dataset contains "
            f"missing values for h={horizon}."
        )

    return (
        model_df[
            output_columns
        ]
        .sort_values(
            [
                "season",
                "harvest_block_order",
            ]
        )
        .reset_index(drop=True)
    )


def main() -> None:
    """
    Build and save month-level datasets for
    h = 1, 2, 3, 4, 5.
    """

    weather_df = (
        load_month_level_weather_predictors(
            WEATHER_INPUT_PATH
        )
    )

    base_period_df = build_base_harvest_periods(
        HARVEST_INPUT_PATH
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 72)
    print("Month-Level Baseline Dataset Construction")
    print("=" * 72)

    print(
        "Complete weather seasons: "
        f"{weather_df['season'].nunique()}"
    )

    print(
        "Complete harvest seasons: "
        f"{base_period_df['season'].nunique()}"
    )

    for horizon in HORIZONS:
        model_df = (
            build_month_level_horizon_dataset(
                base_period_df=base_period_df,
                weather_df=weather_df,
                horizon=horizon,
            )
        )

        output_path = (
            OUTPUT_DIR
            / f"month_level_baseline_h{horizon}.csv"
        )

        model_df.to_csv(
            output_path,
            index=False,
        )

        print(
            f"[OK] h={horizon}: "
            f"{model_df['season'].nunique()} seasons, "
            f"{len(model_df)} observations, "
            f"{model_df['harvest_block_order'].nunique()} "
            "blocks/season"
        )

    print("=" * 72)


if __name__ == "__main__":
    main()