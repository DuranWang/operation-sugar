"""
Monthly Weather Aggregation

Convert municipality-level daily NASA POWER weather observations
into monthly weather features and validate temporal coverage.
"""

from pathlib import Path

import pandas as pd

from src.etl.saver import save_dataframe_csv
from src.etl.summary import summarize_dataframe
from src.etl.validator import (
    validate_expected_columns,
    validate_no_duplicates,
    validate_no_missing_values,
    validate_non_negative,
)
from src.feature_engineering.rainfall import (
    calculate_max_consecutive_dry_days,
)
from src.feature_engineering.temperature import (
    calculate_average_temperature,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "nasa_power"
    / "daily_weather"
    / "SP"
    / "2020.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sp_monthly_weather_2020.csv"
)

DRY_DAY_THRESHOLD = 1.0

DAILY_WEATHER_COLUMNS = [
    "Date",
    "ibge_code",
    "municipality",
    "state",
    "latitude",
    "longitude",
    "PRECTOTCORR",
    "T2M",
    "RH2M",
]

GROUP_COLUMNS = [
    "ibge_code",
    "municipality",
    "state",
    "latitude",
    "longitude",
    "year",
    "month",
]

ROUND_COLUMNS = [
    "total_rainfall",
    "average_temperature",
    "average_humidity",
    "max_daily_rainfall",
    "temperature_std",
]


def load_daily_weather(
    input_path: Path,
) -> pd.DataFrame:
    """Load municipality-level daily NASA POWER weather data."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Daily weather dataset not found: {input_path}"
        )

    weather_df = pd.read_csv(
        input_path
    )

    if weather_df.empty:
        raise ValueError(
            "Daily weather dataset is empty."
        )

    missing_columns = (
        set(DAILY_WEATHER_COLUMNS)
        - set(weather_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Daily weather dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    return weather_df


def prepare_daily_weather(
    raw_df: pd.DataFrame,
) -> pd.DataFrame:
    """Clean daily weather data and add calendar fields."""

    weather_df = raw_df.copy()

    weather_df["Date"] = pd.to_datetime(
        weather_df["Date"],
        errors="coerce",
    )

    numeric_columns = [
        "latitude",
        "longitude",
        "PRECTOTCORR",
        "T2M",
        "RH2M",
    ]

    for column in numeric_columns:
        weather_df[column] = pd.to_numeric(
            weather_df[column],
            errors="coerce",
        )

    validate_no_missing_values(
        weather_df[DAILY_WEATHER_COLUMNS]
    )

    validate_non_negative(
        weather_df,
        column="PRECTOTCORR",
    )

    validate_no_duplicates(
        weather_df,
        subset=[
            "ibge_code",
            "Date",
        ],
    )

    weather_df["year"] = (
        weather_df["Date"].dt.year
    )

    weather_df["month"] = (
        weather_df["Date"].dt.month
    )

    weather_df = weather_df.sort_values(
        [
            "ibge_code",
            "Date",
        ]
    ).reset_index(drop=True)

    return weather_df


def aggregate_monthly_weather(
    weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate daily weather observations into monthly features."""

    monthly_weather = (
        weather_df
        .groupby(
            GROUP_COLUMNS,
            as_index=False,
        )
        .agg(
            total_rainfall=(
                "PRECTOTCORR",
                "sum",
            ),
            average_temperature=(
                "T2M",
                calculate_average_temperature,
            ),
            average_humidity=(
                "RH2M",
                "mean",
            ),
            rainy_days=(
                "PRECTOTCORR",
                lambda rainfall: (
                    rainfall.gt(
                        DRY_DAY_THRESHOLD
                    ).sum()
                ),
            ),
            dry_days=(
                "PRECTOTCORR",
                lambda rainfall: (
                    rainfall.le(
                        DRY_DAY_THRESHOLD
                    ).sum()
                ),
            ),
            max_daily_rainfall=(
                "PRECTOTCORR",
                "max",
            ),
            temperature_std=(
                "T2M",
                "std",
            ),
            weather_observation_days=(
                "Date",
                "count",
            ),
        )
    )

    # Maximum consecutive dry days cannot be calculated using a
    # simple aggregation because the chronological sequence of
    # dry days must be preserved within each municipality-month.
    monthly_cdd = (
        weather_df
        .groupby(
            GROUP_COLUMNS
        )[
            [
                "Date",
                "PRECTOTCORR",
            ]
        ]
        .apply(
            lambda group: (
                calculate_max_consecutive_dry_days(
                    rainfall=group["PRECTOTCORR"],
                    dates=group["Date"],
                    dry_day_threshold=DRY_DAY_THRESHOLD,
                )
            )
        )
        .rename(
            "max_consecutive_dry_days"
        )
        .reset_index()
    )

    monthly_weather = monthly_weather.merge(
        monthly_cdd,
        on=GROUP_COLUMNS,
        how="left",
        validate="one_to_one",
    )

    monthly_weather[ROUND_COLUMNS] = (
        monthly_weather[ROUND_COLUMNS]
        .round(2)
    )

    return monthly_weather


def add_weather_coverage_fields(
    monthly_weather: pd.DataFrame,
) -> pd.DataFrame:
    """Add monthly weather completeness and coverage fields."""

    coverage_df = monthly_weather.copy()

    month_start = pd.to_datetime(
        {
            "year": coverage_df["year"],
            "month": coverage_df["month"],
            "day": 1,
        }
    )

    expected_days = (
        month_start.dt.days_in_month
    )

    coverage_df["missing_weather_days"] = (
        expected_days
        - coverage_df["weather_observation_days"]
    )

    coverage_df["weather_coverage_ratio"] = (
        coverage_df["weather_observation_days"]
        / expected_days
    ).round(4)

    coverage_df["has_complete_weather_period"] = (
        coverage_df["missing_weather_days"] == 0
    )

    return coverage_df


def validate_monthly_weather(
    monthly_weather: pd.DataFrame,
) -> None:
    """Validate the processed monthly weather dataset."""

    expected_columns = [
        *GROUP_COLUMNS,
        "total_rainfall",
        "average_temperature",
        "average_humidity",
        "rainy_days",
        "dry_days",
        "max_daily_rainfall",
        "temperature_std",
        "weather_observation_days",
        "max_consecutive_dry_days",
        "missing_weather_days",
        "weather_coverage_ratio",
        "has_complete_weather_period",
    ]

    validate_expected_columns(
        monthly_weather,
        expected_columns,
    )

    validate_no_missing_values(
        monthly_weather
    )

    validate_no_duplicates(
        monthly_weather,
        subset=[
            "ibge_code",
            "year",
            "month",
        ],
    )

    non_negative_columns = [
        "total_rainfall",
        "rainy_days",
        "dry_days",
        "max_daily_rainfall",
        "weather_observation_days",
        "max_consecutive_dry_days",
        "missing_weather_days",
    ]

    for column in non_negative_columns:
        validate_non_negative(
            monthly_weather,
            column=column,
        )

    day_count_errors = monthly_weather[
        (
            monthly_weather["rainy_days"]
            + monthly_weather["dry_days"]
        )
        != monthly_weather["weather_observation_days"]
    ]

    if not day_count_errors.empty:
        raise ValueError(
            "Rainy days and dry days do not add up to "
            "weather observation days for "
            f"{len(day_count_errors)} monthly records."
        )

    invalid_coverage = monthly_weather[
        ~monthly_weather[
            "weather_coverage_ratio"
        ].between(
            0.0,
            1.0,
            inclusive="both",
        )
    ]

    if not invalid_coverage.empty:
        raise ValueError(
            "Weather coverage ratio must be between "
            "0 and 1."
        )

    invalid_cdd = monthly_weather[
        monthly_weather[
            "max_consecutive_dry_days"
        ]
        > monthly_weather["dry_days"]
    ]

    if not invalid_cdd.empty:
        raise ValueError(
            "Maximum consecutive dry days cannot exceed "
            "the total number of dry days."
        )

    invalid_months = monthly_weather[
        ~monthly_weather["month"].between(
            1,
            12,
            inclusive="both",
        )
    ]

    if not invalid_months.empty:
        raise ValueError(
            "Month values must be between 1 and 12."
        )

    print(
        "Validation passed: "
        "monthly weather data is valid."
    )


def main() -> None:
    """Run the monthly weather aggregation pipeline."""

    raw_df = load_daily_weather(
        INPUT_PATH
    )

    weather_df = prepare_daily_weather(
        raw_df
    )

    monthly_weather = aggregate_monthly_weather(
        weather_df
    )

    monthly_weather = add_weather_coverage_fields(
        monthly_weather
    )

    validate_monthly_weather(
        monthly_weather
    )

    summarize_dataframe(
        monthly_weather,
        name="Processed Monthly Weather Data",
    )

    save_dataframe_csv(
        monthly_weather,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()