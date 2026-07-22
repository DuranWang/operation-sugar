"""
Build an analysis-ready dataset by combining processed
NASA POWER weather features with historical UNICA harvest progress.

Pipeline

Processed Monthly Weather
        +
Historical UNICA Crushing Database
        ↓
Growing-Season Weather Summary
        +
Harvest Summary
        ↓
Weather-Harvest Dashboard Dataset
"""

from pathlib import Path

import pandas as pd

from src.etl.saver import save_dataframe_csv
from src.etl.unica.unica_normalizer import (
    normalize_harvest_season,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WEATHER_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "monthly_weather"
    / "SP"
    / "20240901_20260430_monthly.csv"
)

UNICA_HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "crushing"
    / "unica_biweekly_crush.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dashboard"
    / "weather_harvest_dataset.csv"
)

GROWING_SEASON_MONTHS = [
    9,
    10,
    11,
    12,
    1,
    2,
    3,
    4,
]

REGION_MAPPING = {
    "sao_paulo": "SP",
}

WEATHER_REQUIRED_COLUMNS = [
    "ibge_code",
    "state",
    "year",
    "month",
    "total_rainfall",
    "average_temperature",
    "average_humidity",
    "rainy_days",
    "dry_days",
    "max_daily_rainfall",
    "temperature_std",
    "max_consecutive_dry_days",
]

UNICA_REQUIRED_COLUMNS = [
    "season",
    "period_end_date",
    "region",
    "crush_tonnes",
]


def assign_harvest_season(
    year: int,
    month: int,
) -> str:
    """
    Assign a harvest-season label to a growing-season month.

    September to December belong to the season beginning
    in the same calendar year.

    January to April belong to the season beginning
    in the previous calendar year.
    """

    if month >= 9:
        start_year = year
    elif month <= 4:
        start_year = year - 1
    else:
        raise ValueError(
            f"Month {month} is outside the "
            "September-April growing season."
        )

    end_year = start_year + 1

    return (
        f"{str(start_year)[-2:]}-"
        f"{str(end_year)[-2:]}"
    )



def load_monthly_weather(
    input_path: Path,
) -> pd.DataFrame:
    """Load the processed municipality-level monthly weather file."""

    if not input_path.exists():
        raise FileNotFoundError(
            "Monthly weather dataset not found: "
            f"{input_path}"
        )

    weather_df = pd.read_csv(
        input_path
    )

    if weather_df.empty:
        raise ValueError(
            "Monthly weather dataset is empty."
        )

    missing_columns = (
        set(WEATHER_REQUIRED_COLUMNS)
        - set(weather_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Monthly weather dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    return weather_df


def load_unica_history(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load and validate the historical UNICA crushing database.

    The historical database contains normalized biweekly
    crushing observations across multiple harvest seasons.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            "Historical UNICA crushing dataset not found: "
            f"{input_path}"
        )

    harvest_df = pd.read_csv(
        input_path
    )

    if harvest_df.empty:
        raise ValueError(
            "Historical UNICA crushing dataset is empty."
        )

    missing_columns = (
        set(UNICA_REQUIRED_COLUMNS)
        - set(harvest_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Historical UNICA crushing dataset is "
            "missing required columns: "
            f"{sorted(missing_columns)}"
        )

    harvest_df = harvest_df.copy()

    harvest_df["period_end_date"] = pd.to_datetime(
        harvest_df["period_end_date"],
        errors="raise",
    )

    harvest_df["crush_tonnes"] = pd.to_numeric(
        harvest_df["crush_tonnes"],
        errors="raise",
    )

    if harvest_df[
        UNICA_REQUIRED_COLUMNS
    ].isna().any().any():
        raise ValueError(
            "Historical UNICA crushing dataset contains "
            "missing required values."
        )

    if (
        harvest_df["crush_tonnes"] < 0
    ).any():
        raise ValueError(
            "UNICA crush_tonnes cannot be negative."
        )

    harvest_df = (
        harvest_df
        .sort_values(
            [
                "season",
                "period_end_date",
                "region",
            ]
        )
        .drop_duplicates(
            subset=[
                "season",
                "period_end_date",
                "region",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    return harvest_df


def aggregate_weather_to_state(
    weather_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate municipality-level monthly weather features
    into state-level monthly weather features.

    Each municipality receives equal spatial weight.
    """

    missing_columns = (
        set(WEATHER_REQUIRED_COLUMNS)
        - set(weather_dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Weather dataframe is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    state_weather = (
        weather_dataframe
        .groupby(
            [
                "state",
                "year",
                "month",
            ],
            as_index=False,
        )
        .agg(
            municipality_count=(
                "ibge_code",
                "nunique",
            ),
            average_municipality_rainfall=(
                "total_rainfall",
                "mean",
            ),
            average_temperature=(
                "average_temperature",
                "mean",
            ),
            average_humidity=(
                "average_humidity",
                "mean",
            ),
            average_rainy_days=(
                "rainy_days",
                "mean",
            ),
            average_dry_days=(
                "dry_days",
                "mean",
            ),
            state_max_daily_rainfall=(
                "max_daily_rainfall",
                "max",
            ),
            average_temperature_std=(
                "temperature_std",
                "mean",
            ),
            average_max_consecutive_dry_days=(
                "max_consecutive_dry_days",
                "mean",
            ),
            state_max_consecutive_dry_days=(
                "max_consecutive_dry_days",
                "max",
            ),
        )
        .sort_values(
            [
                "state",
                "year",
                "month",
            ]
        )
        .reset_index(drop=True)
    )

    return state_weather


def aggregate_state_weather_to_growing_season(
    state_weather: pd.DataFrame,
) -> pd.DataFrame:
    """
    Filter state-level monthly weather to growing-season
    months and assign each month to a harvest season.
    """

    growing_season_weather = state_weather.loc[
        state_weather["month"].isin(
            GROWING_SEASON_MONTHS
        )
    ].copy()

    if growing_season_weather.empty:
        raise ValueError(
            "No growing-season weather observations were found."
        )

    growing_season_weather["harvest_season"] = (
        growing_season_weather.apply(
            lambda row: assign_harvest_season(
                year=int(row["year"]),
                month=int(row["month"]),
            ),
            axis=1,
        )
    )

    growing_season_weather = (
        growing_season_weather
        .sort_values(
            [
                "state",
                "harvest_season",
                "year",
                "month",
            ]
        )
        .reset_index(drop=True)
    )

    return growing_season_weather


def summarize_growing_season_weather(
    growing_season_weather: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate state-level monthly weather into one row
    per state and harvest season.
    """

    weather_summary = (
        growing_season_weather
        .groupby(
            [
                "state",
                "harvest_season",
            ],
            as_index=False,
        )
        .agg(
            municipality_count=(
                "municipality_count",
                "max",
            ),
            growing_season_month_count=(
                "month",
                "count",
            ),
            total_growing_season_rainfall=(
                "average_municipality_rainfall",
                "sum",
            ),
            average_growing_season_temperature=(
                "average_temperature",
                "mean",
            ),
            average_growing_season_humidity=(
                "average_humidity",
                "mean",
            ),
            total_growing_season_rainy_days=(
                "average_rainy_days",
                "sum",
            ),
            total_growing_season_dry_days=(
                "average_dry_days",
                "sum",
            ),
            maximum_daily_rainfall=(
                "state_max_daily_rainfall",
                "max",
            ),
            average_temperature_std=(
                "average_temperature_std",
                "mean",
            ),
            average_max_consecutive_dry_days=(
                "average_max_consecutive_dry_days",
                "mean",
            ),
            maximum_consecutive_dry_days=(
                "state_max_consecutive_dry_days",
                "max",
            ),
        )
        .sort_values(
            [
                "state",
                "harvest_season",
            ]
        )
        .reset_index(drop=True)
    )

    weather_summary[
        "has_complete_growing_season"
    ] = (
        weather_summary[
            "growing_season_month_count"
        ]
        == len(GROWING_SEASON_MONTHS)
    )

    return weather_summary


def build_growing_season_weather_summary(
    weather_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Build state-level growing-season weather summaries."""

    state_weather = aggregate_weather_to_state(
        weather_dataframe
    )

    growing_season_weather = (
        aggregate_state_weather_to_growing_season(
            state_weather
        )
    )

    weather_summary = (
        summarize_growing_season_weather(
            growing_season_weather
        )
    )

    return weather_summary


def build_harvest_summary(
    harvest_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build cumulative crushing totals through the latest
    available report date for every state and harvest season.
    """

    missing_columns = (
        set(UNICA_REQUIRED_COLUMNS)
        - set(harvest_dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Harvest dataframe is missing columns: "
            f"{sorted(missing_columns)}"
        )

    harvest_summary = harvest_dataframe.copy()

    harvest_summary["state"] = (
        harvest_summary["region"]
        .map(REGION_MAPPING)
    )

    # The current weather model is state-level.
    # Keep only UNICA regions that map to a state code.
    harvest_summary = harvest_summary.loc[
        harvest_summary["state"].notna()
    ].copy()

    if harvest_summary.empty:
        raise ValueError(
            "No UNICA regions could be mapped "
            "to state-level weather data."
        )

    harvest_summary["harvest_season"] = (
        harvest_summary["season"]
        .apply(normalize_harvest_season)
    )

    harvest_summary["period_end_date"] = pd.to_datetime(
        harvest_summary["period_end_date"],
        errors="raise",
    )

    harvest_summary["crush_tonnes"] = pd.to_numeric(
        harvest_summary["crush_tonnes"],
        errors="raise",
    )

    harvest_summary = (
        harvest_summary
        .groupby(
            [
                "state",
                "harvest_season",
            ],
            as_index=False,
        )
        .agg(
            latest_report_date=(
                "period_end_date",
                "max",
            ),
            cumulative_crush_tonnes=(
                "crush_tonnes",
                "sum",
            ),
            harvest_period_count=(
                "period_end_date",
                "count",
            ),
        )
        .sort_values(
            [
                "state",
                "harvest_season",
            ]
        )
        .reset_index(drop=True)
    )

    duplicate_keys = harvest_summary.duplicated(
        subset=[
            "state",
            "harvest_season",
        ],
        keep=False,
    )

    if duplicate_keys.any():
        raise ValueError(
            "Harvest summary contains duplicate "
            "state-season records."
        )

    return harvest_summary

def build_weather_harvest_dataset(
    weather_summary: pd.DataFrame,
    harvest_summary: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine growing-season weather with the latest
    cumulative harvest observations and add dashboard metadata.
    """

    dashboard_df = weather_summary.merge(
        harvest_summary,
        on=[
            "state",
            "harvest_season",
        ],
        how="inner",
        validate="one_to_one",
    )

    if dashboard_df.empty:
        raise ValueError(
            "Weather and harvest summaries have no "
            "matching state-season records."
        )

    growing_season_start_year = (
        2000
        + dashboard_df[
            "harvest_season"
        ]
        .str[:2]
        .astype(int)
    )

    dashboard_df[
        "growing_season_start"
    ] = pd.to_datetime(
        growing_season_start_year.astype(str)
        + "-09-01",
        errors="raise",
    )

    dashboard_df[
        "growing_season_end"
    ] = pd.to_datetime(
        (
            growing_season_start_year
            + 1
        )
        .astype(str)
        + "-04-30",
        errors="raise",
    )

    dashboard_df["weather_source"] = (
        "NASA POWER"
    )

    dashboard_df["harvest_source"] = (
        "UNICA"
    )

    dashboard_df = dashboard_df[
        [
            "state",
            "harvest_season",
            "growing_season_start",
            "growing_season_end",
            "latest_report_date",
            "municipality_count",
            "growing_season_month_count",
            "has_complete_growing_season",
            "total_growing_season_rainfall",
            "average_growing_season_temperature",
            "average_growing_season_humidity",
            "total_growing_season_rainy_days",
            "total_growing_season_dry_days",
            "maximum_daily_rainfall",
            "average_temperature_std",
            "average_max_consecutive_dry_days",
            "maximum_consecutive_dry_days",
            "harvest_period_count",
            "cumulative_crush_tonnes",
            "weather_source",
            "harvest_source",
        ]
    ]

    dashboard_df = (
        dashboard_df
        .sort_values(
            [
                "state",
                "harvest_season",
            ]
        )
        .reset_index(drop=True)
    )

    return dashboard_df


def main() -> None:
    """Build the Operation Sugar dashboard dataset."""

    weather_df = load_monthly_weather(
        WEATHER_INPUT_PATH
    )

    weather_summary = (
        build_growing_season_weather_summary(
            weather_df
        )
    )

    harvest_df = load_unica_history(
        UNICA_HISTORY_PATH
    )

    harvest_summary = build_harvest_summary(
        harvest_df
    )

    dashboard_df = build_weather_harvest_dataset(
        weather_summary=weather_summary,
        harvest_summary=harvest_summary,
    )

    print("\nWEATHER SUMMARY")

    print(
        weather_summary.to_string(
            index=False
        )
    )

    print("\nHARVEST SUMMARY")

    print(
        harvest_summary.to_string(
            index=False
        )
    )

    print("\nDASHBOARD DATASET")

    print(
        dashboard_df.to_string(
            index=False
        )
    )

    save_dataframe_csv(
        dashboard_df,
        OUTPUT_PATH,
    )

    print(
        "\nWeather-harvest dashboard dataset "
        "built successfully."
    )


if __name__ == "__main__":
    main()