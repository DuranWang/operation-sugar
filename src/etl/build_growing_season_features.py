"""
Build Growing-Season Features

Read daily NASA POWER weather observations,
generate growing-season weather features,
validate the output, and save the processed dataset.
"""

from pathlib import Path

import pandas as pd

from src.etl.loader import load_yearly_csv_files
from src.etl.saver import save_dataframe_csv
from src.etl.summary import summarize_dataframe
from src.etl.validator import (
    validate_expected_columns,
    validate_no_duplicates,
    validate_no_missing_values,
    validate_non_negative,
)
from src.feature_engineering.pipeline import (
    calculate_growing_season_features,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

STATE = "SP"

INPUT_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "nasa_power"
    / "daily_weather"
    / STATE
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "growing_season"
    / STATE
    / "growing_season_features.csv"
)

INPUT_YEARS = [
    2019,
    2020,
    2021,
]

OUTPUT_HARVEST_YEARS = [
    2020,
    2021,
]

DAILY_WEATHER_COLUMNS = [
    "Date",
    "PRECTOTCORR",
    "T2M",
    "RH2M",
    "municipality",
    "ibge_code",
    "state",
    "latitude",
    "longitude",
]

GROWING_SEASON_COLUMNS = [
    "ibge_code",
    "municipality",
    "state",
    "harvest_year",
    "growing_season_total_rainfall",
    "growing_season_average_temperature",
    "growing_season_observation_days",
    "growing_season_start_date",
    "growing_season_end_date",
    "growing_season_max_consecutive_dry_days",
]

def prepare_daily_weather(
    weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert the date column and create calendar-year fields.
    """

    prepared_weather_df = weather_df.copy()

    prepared_weather_df["date"] = pd.to_datetime(
        prepared_weather_df["Date"],
        errors="raise",
    )

    prepared_weather_df["year"] = (
        prepared_weather_df["date"].dt.year
    )

    prepared_weather_df["month"] = (
        prepared_weather_df["date"].dt.month
    )

    return prepared_weather_df


def filter_output_harvest_years(
    growing_season_features: pd.DataFrame,
    harvest_years: list[int],
) -> pd.DataFrame:
    """
    Keep only the requested harvest years.
    """

    filtered_features = (
        growing_season_features[
            growing_season_features[
                "harvest_year"
            ].isin(harvest_years)
        ]
        .reset_index(drop=True)
    )

    return filtered_features


def main() -> None:
    weather_df = load_yearly_csv_files(
        input_folder=INPUT_FOLDER,
        years=INPUT_YEARS,
    )

    validate_expected_columns(
        weather_df,
        DAILY_WEATHER_COLUMNS,
    )

    validate_no_missing_values(
        weather_df,
        DAILY_WEATHER_COLUMNS,
    )

    validate_no_duplicates(
        weather_df,
        [
            "ibge_code",
            "Date",
        ],
    )

    validate_non_negative(
        weather_df,
        "PRECTOTCORR",
    )

    weather_df = prepare_daily_weather(
        weather_df
    )

    growing_season_features = (
        calculate_growing_season_features(
            weather_df
        )
    )

    growing_season_features = (
        filter_output_harvest_years(
            growing_season_features,
            OUTPUT_HARVEST_YEARS,
        )
    )

    validate_expected_columns(
        growing_season_features,
        GROWING_SEASON_COLUMNS,
    )

    validate_no_missing_values(
        growing_season_features,
        GROWING_SEASON_COLUMNS,
    )

    validate_no_duplicates(
        growing_season_features,
        [
            "ibge_code",
            "harvest_year",
        ],
    )

    validate_non_negative(
        growing_season_features,
        "growing_season_total_rainfall",
    )

    validate_non_negative(
        growing_season_features,
        "growing_season_observation_days",
    )

    validate_non_negative(
        growing_season_features,
        "growing_season_max_consecutive_dry_days",
    )

    summarize_dataframe(
        growing_season_features
    )

    save_dataframe_csv(
        growing_season_features,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()