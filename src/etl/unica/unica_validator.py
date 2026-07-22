"""
Validate normalized UNICA cumulative crushing datasets.
"""

import pandas as pd
import re

EXPECTED_COLUMNS = [
    "season",
    "period_end_date",
    "region",
    "crush_tonnes",
    "variation_percent",
]

UNIQUE_COLUMNS = [
    "season",
    "period_end_date",
    "region",
]


def validate_expected_columns(
    dataframe: pd.DataFrame,
) -> None:
    """Validate that all required columns are present."""

    missing_columns = (
        set(EXPECTED_COLUMNS)
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing columns: "
            f"{sorted(missing_columns)}"
        )


def validate_no_missing_values(
    dataframe: pd.DataFrame,
) -> None:
    """Validate that required columns contain no missing values."""

    missing_counts = (
        dataframe[EXPECTED_COLUMNS]
        .isna()
        .sum()
    )

    columns_with_missing_values = (
        missing_counts[
            missing_counts > 0
        ]
    )

    if not columns_with_missing_values.empty:
        raise ValueError(
            "UNICA dataset contains missing values:\n"
            f"{columns_with_missing_values}"
        )


def validate_no_duplicates(
    dataframe: pd.DataFrame,
) -> None:
    """Validate uniqueness by season, date, and region."""

    duplicate_rows = dataframe.duplicated(
        subset=UNIQUE_COLUMNS,
        keep=False,
    )

    if duplicate_rows.any():
        raise ValueError(
            "UNICA dataset contains duplicate "
            "season-date-region records."
        )


def validate_crush_tonnes(
    dataframe: pd.DataFrame,
) -> None:
    """Validate cumulative crushing values."""

    if not pd.api.types.is_numeric_dtype(
        dataframe["crush_tonnes"]
    ):
        raise ValueError(
            "crush_tonnes must be numeric."
        )

    invalid_rows = dataframe[
        dataframe["crush_tonnes"] < 0
    ]

    if not invalid_rows.empty:
        raise ValueError(
            "crush_tonnes cannot contain negative values."
        )


def validate_period_end_date(
    dataframe: pd.DataFrame,
) -> None:
    """Validate reporting-date data type."""

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["period_end_date"]
    ):
        raise ValueError(
            "period_end_date must use a pandas datetime dtype."
        )


def validate_season_format(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate UNICA season labels in YY-YY format.

    Valid examples
    --------------
    10-11
    25-26
    99-00
    """

    invalid_seasons = []

    unique_seasons = (
        dataframe["season"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    for season in unique_seasons:
        if not re.fullmatch(
            r"\d{2}-\d{2}",
            season,
        ):
            invalid_seasons.append(
                season
            )
            continue

        start_text, end_text = season.split(
            "-"
        )

        start_year = int(
            start_text
        )

        end_year = int(
            end_text
        )

        expected_end_year = (
            start_year + 1
        ) % 100

        if end_year != expected_end_year:
            invalid_seasons.append(
                season
            )

    if invalid_seasons:
        raise ValueError(
            "Invalid UNICA season labels: "
            f"{invalid_seasons}"
        )   


def validate_regions(
    dataframe: pd.DataFrame,
) -> None:
    """Validate normalized UNICA region names."""

    expected_regions = {
        "sao_paulo",
        "centre_south",
        "other_states",
    }

    unexpected_regions = (
        set(dataframe["region"])
        - expected_regions
    )

    if unexpected_regions:
        raise ValueError(
            "Unexpected UNICA regions: "
            f"{sorted(unexpected_regions)}"
        )


def validate_historical_crushing_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    """Run all UNICA historical crushing validations."""

    if dataframe.empty:
        raise ValueError(
            "UNICA historical crushing dataset is empty."
        )

    validate_expected_columns(
        dataframe
    )

    validate_no_missing_values(
        dataframe
    )

    validate_no_duplicates(
        dataframe
    )

    validate_crush_tonnes(
        dataframe
    )

    validate_period_end_date(
        dataframe
    )

    validate_season_format(
        dataframe
    )

    validate_regions(
        dataframe
    )

    print(
        "Validation passed: "
        "historical UNICA crushing data is valid."
    )