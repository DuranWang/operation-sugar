import pandas as pd
import pytest

from src.etl.validator import (
    validate_expected_columns,
    validate_no_duplicates,
    validate_no_missing_values,
    validate_non_negative,
)


def test_validate_expected_columns_passes() -> None:
    df = pd.DataFrame(
        {
            "municipality": ["Adamantina"],
            "rainfall": [10.0],
        }
    )

    validate_expected_columns(
        df,
        [
            "municipality",
            "rainfall",
        ],
    )


def test_validate_expected_columns_raises_for_wrong_order() -> None:
    df = pd.DataFrame(
        {
            "municipality": ["Adamantina"],
            "rainfall": [10.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="Unexpected columns or column order",
    ):
        validate_expected_columns(
            df,
            [
                "rainfall",
                "municipality",
            ],
        )


def test_validate_no_missing_values_passes() -> None:
    df = pd.DataFrame(
        {
            "municipality": ["Adamantina"],
            "rainfall": [10.0],
        }
    )

    validate_no_missing_values(
        df,
        [
            "municipality",
            "rainfall",
        ],
    )


def test_validate_no_missing_values_raises() -> None:
    df = pd.DataFrame(
        {
            "municipality": ["Adamantina", "Adolfo"],
            "rainfall": [10.0, None],
        }
    )

    with pytest.raises(
        ValueError,
        match="Missing values found",
    ):
        validate_no_missing_values(
            df,
            [
                "rainfall",
            ],
        )


def test_validate_no_duplicates_passes() -> None:
    df = pd.DataFrame(
        {
            "ibge_code": [3500105, 3500204],
            "year": [2020, 2020],
        }
    )

    validate_no_duplicates(
        df,
        [
            "ibge_code",
            "year",
        ],
    )


def test_validate_no_duplicates_raises() -> None:
    df = pd.DataFrame(
        {
            "ibge_code": [3500105, 3500105],
            "year": [2020, 2020],
        }
    )

    with pytest.raises(
        ValueError,
        match="Duplicate observations found",
    ):
        validate_no_duplicates(
            df,
            [
                "ibge_code",
                "year",
            ],
        )


def test_validate_non_negative_passes() -> None:
    df = pd.DataFrame(
        {
            "rainfall": [0.0, 10.0, 25.5],
        }
    )

    validate_non_negative(
        df,
        "rainfall",
    )


def test_validate_non_negative_raises_for_negative_values() -> None:
    df = pd.DataFrame(
        {
            "rainfall": [0.0, -1.0, 10.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="Negative values found",
    ):
        validate_non_negative(
            df,
            "rainfall",
        )


def test_validate_non_negative_raises_for_non_numeric_column() -> None:
    df = pd.DataFrame(
        {
            "rainfall": ["low", "high"],
        }
    )

    with pytest.raises(
        ValueError,
        match="Column is not numeric",
    ):
        validate_non_negative(
            df,
            "rainfall",
        )