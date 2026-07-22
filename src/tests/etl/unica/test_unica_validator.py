"""Tests for the UNICA crushing-data validator."""

import pandas as pd
import pytest

from src.etl.unica.unica_validator import (
    EXPECTED_COLUMNS,
    UNIQUE_COLUMNS,
    validate_crush_tonnes,
    validate_expected_columns,
    validate_historical_crushing_dataframe,
    validate_no_duplicates,
    validate_no_missing_values,
    validate_period_end_date,
    validate_regions,
    validate_season_format,
)


def build_valid_dataframe() -> pd.DataFrame:
    """Build a small valid UNICA crushing dataframe."""

    return pd.DataFrame(
        {
            "season": [
                "25-26",
                "25-26",
                "25-26",
            ],
            "period_end_date": pd.to_datetime(
                [
                    "2025-04-16",
                    "2025-04-16",
                    "2025-04-16",
                ]
            ),
            "region": [
                "sao_paulo",
                "other_states",
                "centre_south",
            ],
            "crush_tonnes": [
                8_253_154,
                2_754_092,
                11_007_246,
            ],
            "variation_percent": [
                30.0,
                20.0,
                27.0,
            ],
        }
    )


def test_expected_columns_constant() -> None:
    """Confirm the expected UNICA schema."""

    assert EXPECTED_COLUMNS == [
        "season",
        "period_end_date",
        "region",
        "crush_tonnes",
        "variation_percent",
    ]


def test_unique_columns_constant() -> None:
    """Confirm the canonical record key."""

    assert UNIQUE_COLUMNS == [
        "season",
        "period_end_date",
        "region",
    ]


def test_validate_expected_columns_accepts_valid_dataframe() -> None:
    """Accept a dataframe containing every required column."""

    dataframe = build_valid_dataframe()

    validate_expected_columns(
        dataframe
    )


def test_validate_expected_columns_allows_extra_columns() -> None:
    """Allow additional non-required columns."""

    dataframe = build_valid_dataframe()

    dataframe["source_file"] = (
        "unica_report.pdf"
    )

    validate_expected_columns(
        dataframe
    )


@pytest.mark.parametrize(
    "missing_column",
    EXPECTED_COLUMNS,
)
def test_validate_expected_columns_rejects_missing_column(
    missing_column: str,
) -> None:
    """Reject a dataframe missing any required column."""

    dataframe = (
        build_valid_dataframe()
        .drop(columns=[missing_column])
    )

    with pytest.raises(
        ValueError,
        match="Missing columns",
    ):
        validate_expected_columns(
            dataframe
        )


def test_validate_no_missing_values_accepts_complete_dataframe() -> None:
    """Accept required columns without missing values."""

    dataframe = build_valid_dataframe()

    validate_no_missing_values(
        dataframe
    )


@pytest.mark.parametrize(
    "column_name",
    EXPECTED_COLUMNS,
)
def test_validate_no_missing_values_rejects_missing_required_value(
    column_name: str,
) -> None:
    """Reject missing values in any required column."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        column_name,
    ] = None

    with pytest.raises(
        ValueError,
        match="contains missing values",
    ):
        validate_no_missing_values(
            dataframe
        )


def test_validate_no_duplicates_accepts_unique_records() -> None:
    """Accept unique season-date-region records."""

    dataframe = build_valid_dataframe()

    validate_no_duplicates(
        dataframe
    )


def test_validate_no_duplicates_rejects_duplicate_key() -> None:
    """Reject two rows with the same canonical record key."""

    dataframe = build_valid_dataframe()

    duplicate_row = (
        dataframe
        .iloc[[0]]
        .copy()
    )

    dataframe = pd.concat(
        [
            dataframe,
            duplicate_row,
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "duplicate season-date-region records"
        ),
    ):
        validate_no_duplicates(
            dataframe
        )


def test_validate_no_duplicates_ignores_non_key_differences() -> None:
    """
    Reject duplicate keys even when observation values differ.
    """

    dataframe = build_valid_dataframe()

    conflicting_row = (
        dataframe
        .iloc[[0]]
        .copy()
    )

    conflicting_row[
        "crush_tonnes"
    ] = 999

    dataframe = pd.concat(
        [
            dataframe,
            conflicting_row,
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "duplicate season-date-region records"
        ),
    ):
        validate_no_duplicates(
            dataframe
        )


def test_validate_crush_tonnes_accepts_integer_values() -> None:
    """Accept integer crushing values."""

    dataframe = build_valid_dataframe()

    validate_crush_tonnes(
        dataframe
    )


def test_validate_crush_tonnes_accepts_float_values() -> None:
    """Accept numeric floating-point crushing values."""

    dataframe = build_valid_dataframe()

    dataframe["crush_tonnes"] = (
        dataframe["crush_tonnes"]
        .astype(float)
    )

    validate_crush_tonnes(
        dataframe
    )


def test_validate_crush_tonnes_accepts_zero() -> None:
    """Allow zero crushing for a valid reporting period."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "crush_tonnes",
    ] = 0

    validate_crush_tonnes(
        dataframe
    )


def test_validate_crush_tonnes_rejects_non_numeric_dtype() -> None:
    """Reject crushing values stored as strings."""

    dataframe = build_valid_dataframe()

    dataframe["crush_tonnes"] = (
        dataframe["crush_tonnes"]
        .astype(str)
    )

    with pytest.raises(
        ValueError,
        match="crush_tonnes must be numeric",
    ):
        validate_crush_tonnes(
            dataframe
        )


def test_validate_crush_tonnes_rejects_negative_value() -> None:
    """Reject negative crushing values."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "crush_tonnes",
    ] = -1

    with pytest.raises(
        ValueError,
        match=(
            "crush_tonnes cannot contain negative values"
        ),
    ):
        validate_crush_tonnes(
            dataframe
        )


def test_validate_period_end_date_accepts_datetime_dtype() -> None:
    """Accept pandas datetime reporting dates."""

    dataframe = build_valid_dataframe()

    validate_period_end_date(
        dataframe
    )


def test_validate_period_end_date_rejects_string_dtype() -> None:
    """Reject reporting dates stored as strings."""

    dataframe = build_valid_dataframe()

    dataframe[
        "period_end_date"
    ] = dataframe[
        "period_end_date"
    ].dt.strftime(
        "%Y-%m-%d"
    )

    with pytest.raises(
        ValueError,
        match=(
            "period_end_date must use "
            "a pandas datetime dtype"
        ),
    ):
        validate_period_end_date(
            dataframe
        )


@pytest.mark.parametrize(
    "valid_season",
    [
        "10-11",
        "24-25",
        "25-26",
        "98-99",
        "99-00",
    ],
)
def test_validate_season_format_accepts_valid_season(
    valid_season: str,
) -> None:
    """Accept consecutive YY-YY season labels."""

    dataframe = build_valid_dataframe()

    dataframe["season"] = (
        valid_season
    )

    validate_season_format(
        dataframe
    )


@pytest.mark.parametrize(
    "invalid_season",
    [
        "2025/26",
        "2025/2026",
        "25/26",
        "2025-2026",
        "5-26",
        "025-26",
        "25-27",
        "99-01",
        "season 25-26",
        "",
    ],
)
def test_validate_season_format_rejects_invalid_season(
    invalid_season: str,
) -> None:
    """Reject malformed or nonconsecutive season labels."""

    dataframe = build_valid_dataframe()

    dataframe["season"] = (
        invalid_season
    )

    with pytest.raises(
        ValueError,
        match="Invalid UNICA season labels",
    ):
        validate_season_format(
            dataframe
        )


def test_validate_season_format_checks_all_unique_seasons() -> None:
    """Reject a dataframe containing one invalid season."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        2,
        "season",
    ] = "25-27"

    with pytest.raises(
        ValueError,
        match="25-27",
    ):
        validate_season_format(
            dataframe
        )


@pytest.mark.parametrize(
    "region",
    [
        "sao_paulo",
        "centre_south",
        "other_states",
    ],
)
def test_validate_regions_accepts_expected_region(
    region: str,
) -> None:
    """Accept each normalized UNICA region."""

    dataframe = build_valid_dataframe()

    dataframe["region"] = region

    validate_regions(
        dataframe
    )


@pytest.mark.parametrize(
    "invalid_region",
    [
        "south_central",
        "são_paulo",
        "SP",
        "other",
        "unknown_region",
    ],
)
def test_validate_regions_rejects_unexpected_region(
    invalid_region: str,
) -> None:
    """Reject a region outside the normalized schema."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "region",
    ] = invalid_region

    with pytest.raises(
        ValueError,
        match="Unexpected UNICA regions",
    ):
        validate_regions(
            dataframe
        )


def test_validate_historical_dataframe_accepts_valid_data(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run the complete validation pipeline successfully."""

    dataframe = build_valid_dataframe()

    validate_historical_crushing_dataframe(
        dataframe
    )

    captured = capsys.readouterr()

    assert (
        "historical UNICA crushing data is valid"
        in captured.out
    )


def test_validate_historical_dataframe_rejects_empty_data() -> None:
    """Reject an empty historical crushing dataframe."""

    dataframe = pd.DataFrame(
        columns=EXPECTED_COLUMNS
    )

    with pytest.raises(
        ValueError,
        match=(
            "historical crushing dataset is empty"
        ),
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_missing_column() -> None:
    """Run column validation before downstream checks."""

    dataframe = (
        build_valid_dataframe()
        .drop(
            columns=[
                "variation_percent",
            ]
        )
    )

    with pytest.raises(
        ValueError,
        match="Missing columns",
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_missing_value() -> None:
    """Reject missing required values through the full validator."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "variation_percent",
    ] = None

    with pytest.raises(
        ValueError,
        match="contains missing values",
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_duplicate() -> None:
    """Reject duplicate keys through the full validator."""

    dataframe = build_valid_dataframe()

    dataframe = pd.concat(
        [
            dataframe,
            dataframe.iloc[[0]],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "duplicate season-date-region records"
        ),
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_negative_crush() -> None:
    """Reject negative crushing through the full validator."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "crush_tonnes",
    ] = -100

    with pytest.raises(
        ValueError,
        match=(
            "crush_tonnes cannot contain negative values"
        ),
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_invalid_date_dtype() -> None:
    """Reject non-datetime reporting dates through the full validator."""

    dataframe = build_valid_dataframe()

    dataframe[
        "period_end_date"
    ] = "2025-04-16"

    with pytest.raises(
        ValueError,
        match=(
            "period_end_date must use "
            "a pandas datetime dtype"
        ),
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_invalid_season() -> None:
    """Reject invalid season labels through the full validator."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "season",
    ] = "25-27"

    with pytest.raises(
        ValueError,
        match="Invalid UNICA season labels",
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )


def test_validate_historical_dataframe_rejects_invalid_region() -> None:
    """Reject unknown regions through the full validator."""

    dataframe = build_valid_dataframe()

    dataframe.loc[
        0,
        "region",
    ] = "unknown_region"

    with pytest.raises(
        ValueError,
        match="Unexpected UNICA regions",
    ):
        validate_historical_crushing_dataframe(
            dataframe
        )