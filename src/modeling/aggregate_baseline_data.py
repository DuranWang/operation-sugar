"""
Aggregate Baseline Dataset Construction

Build model-ready weather-harvest datasets for aggregation
horizons h = 1, 2, 3, 4, 5.

Twenty-four biweekly UNICA observations are paired into
twelve approximately 30-day base harvest periods.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WEATHER_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dashboard"
    / "weather_harvest_dataset.csv"
)

HARVEST_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "crushing"
    / "unica_biweekly_crush.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "aggregate_baseline"
)

HORIZONS = (1, 2, 3, 4, 5)

EXPECTED_BIWEEKLY_PERIODS = 24
BASE_HARVEST_PERIODS = 12


def load_weather_predictors(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load complete season-level São Paulo weather predictors.
    """

    weather_df = pd.read_csv(input_path)

    required_columns = {
        "state",
        "harvest_season",
        "has_complete_growing_season",
        "total_growing_season_rainfall",
        "average_growing_season_temperature",
    }

    missing_columns = required_columns - set(weather_df.columns)

    if missing_columns:
        raise ValueError(
            "Weather dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    weather_df = weather_df.loc[
        weather_df["state"].eq("SP")
    ].copy()

    complete_flag = weather_df[
        "has_complete_growing_season"
    ]

    if complete_flag.dtype == object:
        complete_flag = (
            complete_flag
            .astype(str)
            .str.lower()
            .eq("true")
        )

    weather_df = weather_df.loc[
        complete_flag,
        [
            "harvest_season",
            "total_growing_season_rainfall",
            "average_growing_season_temperature",
        ],
    ].copy()

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

    if weather_df["season"].duplicated().any():
        duplicate_seasons = weather_df.loc[
            weather_df["season"].duplicated(keep=False),
            "season",
        ].unique()

        raise ValueError(
            "Weather dataset contains duplicate seasons: "
            f"{sorted(duplicate_seasons)}"
        )

    if weather_df.isna().any().any():
        raise ValueError(
            "Weather predictors contain missing values."
        )

    return weather_df.sort_values("season").reset_index(drop=True)


def build_base_harvest_periods(
    input_path: Path,
) -> pd.DataFrame:
    """
    Pair 24 biweekly observations into 12 sequential
    approximately 30-day harvest periods.
    """

    harvest_df = pd.read_csv(
        input_path,
        parse_dates=["period_end_date"],
    )

    required_columns = {
        "season",
        "period_end_date",
        "region",
        "crush_tonnes",
    }

    missing_columns = required_columns - set(harvest_df.columns)

    if missing_columns:
        raise ValueError(
            "Harvest dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    harvest_df = harvest_df.loc[
        harvest_df["region"].eq("sao_paulo")
    ].copy()

    report_counts = (
        harvest_df
        .groupby("season")["period_end_date"]
        .transform("count")
    )

    # Exclude incomplete seasons, including the current season.
    harvest_df = harvest_df.loc[
        report_counts.eq(EXPECTED_BIWEEKLY_PERIODS)
    ].copy()

    complete_season_count = (
        harvest_df["season"].nunique()
    )

    if complete_season_count == 0:
        raise ValueError(
            "No complete harvest seasons contain exactly "
            f"{EXPECTED_BIWEEKLY_PERIODS} biweekly observations."
        )

    harvest_df = harvest_df.sort_values(
        ["season", "period_end_date"]
    ).reset_index(drop=True)

    harvest_df["biweekly_period_order"] = (
        harvest_df.groupby("season").cumcount() + 1
    )

    harvest_df["base_period_order"] = (
        (harvest_df["biweekly_period_order"] - 1) // 2
        + 1
    )

    base_period_df = (
        harvest_df
        .groupby(
            ["season", "base_period_order"],
            as_index=False,
        )
        .agg(
            base_period_start_date=(
                "period_end_date",
                "min",
            ),
            base_period_end_date=(
                "period_end_date",
                "max",
            ),
            base_period_crush_tonnes=(
                "crush_tonnes",
                "sum",
            ),
            biweekly_report_count=(
                "period_end_date",
                "count",
            ),
        )
    )

    base_period_counts = (
        base_period_df
        .groupby("season")["base_period_order"]
        .count()
    )

    invalid_seasons = base_period_counts.loc[
        base_period_counts.ne(BASE_HARVEST_PERIODS)
    ]

    if not invalid_seasons.empty:
        raise ValueError(
            "Complete seasons must contain exactly "
            f"{BASE_HARVEST_PERIODS} base periods:\n"
            f"{invalid_seasons.to_string()}"
        )

    if not base_period_df[
        "biweekly_report_count"
    ].eq(2).all():
        raise ValueError(
            "Every base harvest period must contain "
            "exactly two biweekly reports."
        )

    return base_period_df


def build_horizon_dataset(
    base_period_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    horizon: int,
) -> pd.DataFrame:
    """
    Aggregate base harvest periods into non-overlapping
    blocks of length h and attach season-level weather.
    """

    if horizon not in HORIZONS:
        raise ValueError(
            f"Unsupported horizon: {horizon}."
        )

    usable_period_count = (
        BASE_HARVEST_PERIODS // horizon
    ) * horizon

    horizon_df = base_period_df.loc[
        base_period_df["base_period_order"]
        <= usable_period_count
    ].copy()

    horizon_df["harvest_block_order"] = (
        (horizon_df["base_period_order"] - 1) // horizon
        + 1
    )

    horizon_df = (
        horizon_df
        .groupby(
            ["season", "harvest_block_order"],
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
            f"No overlapping weather-harvest seasons for h={horizon}."
        )

    if not model_df["base_period_count"].eq(horizon).all():
        raise ValueError(
            f"Invalid block size detected for h={horizon}."
        )

    expected_blocks_per_season = (
        BASE_HARVEST_PERIODS // horizon
    )

    block_counts = (
        model_df
        .groupby("season")["harvest_block_order"]
        .nunique()
    )

    if not block_counts.eq(
        expected_blocks_per_season
    ).all():
        raise ValueError(
            f"Every season must contain exactly "
            f"{expected_blocks_per_season} blocks "
            f"for h={horizon}."
        )

    return (
        model_df[
            [
                "season",
                "horizon",
                "harvest_block_order",
                "block_start_date",
                "block_end_date",
                "base_period_count",
                "block_crush_tonnes",
                "growing_season_total_rainfall",
                "growing_season_average_temperature",
            ]
        ]
        .sort_values(
            ["season", "harvest_block_order"]
        )
        .reset_index(drop=True)
    )


def main() -> None:
    """
    Build and save datasets for h = 1, 2, 3, 4, 5.
    """

    weather_df = load_weather_predictors(
        WEATHER_INPUT_PATH
    )

    base_period_df = build_base_harvest_periods(
        HARVEST_INPUT_PATH
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 72)
    print("Aggregate Baseline Dataset Construction")
    print("=" * 72)

    print(
        f"Complete weather seasons: "
        f"{weather_df['season'].nunique()}"
    )
    print(
        f"Complete harvest seasons: "
        f"{base_period_df['season'].nunique()}"
    )

    for horizon in HORIZONS:
        model_df = build_horizon_dataset(
            base_period_df=base_period_df,
            weather_df=weather_df,
            horizon=horizon,
        )

        output_path = (
            OUTPUT_DIR
            / f"aggregate_baseline_h{horizon}.csv"
        )

        model_df.to_csv(
            output_path,
            index=False,
        )

        print(
            f"[OK] h={horizon}: "
            f"{model_df['season'].nunique()} seasons, "
            f"{len(model_df)} observations, "
            f"{model_df['harvest_block_order'].nunique()} blocks/season"
        )

    print("=" * 72)


if __name__ == "__main__":
    main()