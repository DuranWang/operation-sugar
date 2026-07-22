"""Tests for the UNICA crushing-data normalizer."""

import pandas as pd
import pytest

from src.etl.unica.unica_normalizer import (
    build_period_end_date,
    convert_cumulative_to_biweekly,
    extract_season_labels,
    normalize_harvest_season,
    parse_brazilian_integer,
    parse_region_cell,
)


def test_parse_brazilian_integer() -> None:
    """Convert a dot-separated Brazilian integer."""

    result = parse_brazilian_integer(
        "8.253.154"
    )

    assert result == 8_253_154


def test_parse_brazilian_integer_strips_whitespace() -> None:
    """Ignore surrounding whitespace."""

    result = parse_brazilian_integer(
        "  8.253.154  "
    )

    assert result == 8_253_154


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        "8,253,154",
        "8.253.154 tonnes",
        "abc",
    ],
)
def test_parse_brazilian_integer_rejects_invalid_values(
    invalid_value: str,
) -> None:
    """Reject values that are not Brazilian-formatted integers."""

    with pytest.raises(
        ValueError,
        match="Invalid Brazilian integer value",
    ):
        parse_brazilian_integer(
            invalid_value
        )


def test_parse_region_cell() -> None:
    """Parse previous tonnes, current tonnes, and variation."""

    result = parse_region_cell(
        "8.253.154 11.007.246 33%"
    )

    assert result == (
        8_253_154,
        11_007_246,
        33.0,
    )


def test_parse_region_cell_with_decimal_comma() -> None:
    """Convert a Brazilian decimal comma in percentage values."""

    result = parse_region_cell(
        "8.253.154 11.007.246 33,4%"
    )

    assert result == (
        8_253_154,
        11_007_246,
        33.4,
    )


def test_parse_region_cell_rejects_wrong_number_of_values() -> None:
    """Require exactly three components in a regional cell."""

    with pytest.raises(
        ValueError,
        match="Expected three values",
    ):
        parse_region_cell(
            "8.253.154 11.007.246"
        )


def test_normalize_harvest_season_short_format() -> None:
    """Normalize YY-YY season labels."""

    result = normalize_harvest_season(
        "25-26"
    )

    assert result == "25-26"


def test_normalize_harvest_season_long_format() -> None:
    """Normalize YYYY/YYYY season labels."""

    result = normalize_harvest_season(
        "2025/2026"
    )

    assert result == "25-26"


def test_normalize_harvest_season_mixed_format() -> None:
    """Preserve normalized YYYY/YY season labels."""

    result = normalize_harvest_season(
        "2025/26"
    )

    assert result == "25-26"


def test_normalize_harvest_season_strips_whitespace() -> None:
    """Ignore surrounding whitespace in a season label."""

    result = normalize_harvest_season(
        "  25-26  "
    )

    assert result == "25-26"


@pytest.mark.parametrize(
    "invalid_season",
    [
        "25-27",
        "2025/2027",
        "2025",
        "5-26",
        "20255-26",
    ],
)
def test_normalize_harvest_season_rejects_invalid_values(
    invalid_season: str,
) -> None:
    """Reject malformed or nonconsecutive season labels."""

    with pytest.raises(ValueError):
        normalize_harvest_season(
            invalid_season
        )


def test_extract_season_labels() -> None:
    """Extract and normalize two season labels from a header."""

    header_row = [
        "Período",
        "2024/2025",
        None,
        "2025/2026",
    ]

    result = extract_season_labels(
        header_row
    )

    assert result == (
        "24-25",
        "25-26",
    )


def test_extract_season_labels_removes_duplicates() -> None:
    """Do not count repeated region-level season labels twice."""

    header_row = [
        "2024/2025",
        "2024/2025",
        "2025/2026",
        "2025/2026",
    ]

    result = extract_season_labels(
        header_row
    )

    assert result == (
        "24-25",
        "25-26",
    )


def test_extract_season_labels_requires_two_seasons() -> None:
    """Raise an error when the header does not contain two seasons."""

    header_row = [
        "Período",
        "2025/2026",
        None,
    ]

    with pytest.raises(
        ValueError,
        match="Could not identify two harvest seasons",
    ):
        extract_season_labels(
            header_row
        )


@pytest.mark.parametrize(
    (
        "season",
        "period_text",
        "expected_date",
    ),
    [
        (
            "25-26",
            "16/04",
            pd.Timestamp("2025-04-16"),
        ),
        (
            "25-26",
            "01/08",
            pd.Timestamp("2025-08-01"),
        ),
        (
            "25-26",
            "16/12",
            pd.Timestamp("2025-12-16"),
        ),
        (
            "25-26",
            "01/01",
            pd.Timestamp("2026-01-01"),
        ),
        (
            "25-26",
            "16/03",
            pd.Timestamp("2026-03-16"),
        ),
    ],
)
def test_build_period_end_date(
    season: str,
    period_text: str,
    expected_date: pd.Timestamp,
) -> None:
    """Assign reporting periods to the correct calendar year."""

    result = build_period_end_date(
        season=season,
        period_text=period_text,
    )

    assert result == expected_date


def test_convert_cumulative_to_biweekly() -> None:
    """Convert cumulative tonnes into period-specific tonnes."""

    input_df = pd.DataFrame(
        {
            "season": [
                "2025/26",
                "2025/26",
                "2025/26",
                "2025/26",
            ],
            "period_end_date": pd.to_datetime(
                [
                    "2025-04-16",
                    "2025-05-01",
                    "2025-05-16",
                    "2025-06-01",
                ]
            ),
            "region": [
                "sao_paulo",
                "sao_paulo",
                "sao_paulo",
                "sao_paulo",
            ],
            "cumulative_crush_tonnes": [
                100,
                250,
                400,
                650,
            ],
        }
    )

    result = convert_cumulative_to_biweekly(
        input_df
    )

    assert result["crush_tonnes"].tolist() == [
        100,
        150,
        150,
        250,
    ]


def test_convert_cumulative_to_biweekly_sorts_dates() -> None:
    """Sort each season-region group before calculating differences."""

    input_df = pd.DataFrame(
        {
            "season": [
                "2025/26",
                "2025/26",
                "2025/26",
            ],
            "period_end_date": pd.to_datetime(
                [
                    "2025-05-16",
                    "2025-04-16",
                    "2025-05-01",
                ]
            ),
            "region": [
                "sao_paulo",
                "sao_paulo",
                "sao_paulo",
            ],
            "cumulative_crush_tonnes": [
                400,
                100,
                250,
            ],
        }
    )

    result = convert_cumulative_to_biweekly(
        input_df
    )

    assert result["period_end_date"].tolist() == [
        pd.Timestamp("2025-04-16"),
        pd.Timestamp("2025-05-01"),
        pd.Timestamp("2025-05-16"),
    ]

    assert result["crush_tonnes"].tolist() == [
        100,
        150,
        150,
    ]


def test_convert_cumulative_to_biweekly_handles_multiple_regions() -> None:
    """Calculate differences independently for each region."""

    input_df = pd.DataFrame(
        {
            "season": [
                "2025/26",
                "2025/26",
                "2025/26",
                "2025/26",
            ],
            "period_end_date": pd.to_datetime(
                [
                    "2025-04-16",
                    "2025-05-01",
                    "2025-04-16",
                    "2025-05-01",
                ]
            ),
            "region": [
                "sao_paulo",
                "sao_paulo",
                "other_states",
                "other_states",
            ],
            "cumulative_crush_tonnes": [
                100,
                250,
                40,
                90,
            ],
        }
    )

    result = convert_cumulative_to_biweekly(
        input_df
    )

    sao_paulo_result = result.loc[
        result["region"] == "sao_paulo",
        "crush_tonnes",
    ].tolist()

    other_states_result = result.loc[
        result["region"] == "other_states",
        "crush_tonnes",
    ].tolist()

    assert sao_paulo_result == [
        100,
        150,
    ]

    assert other_states_result == [
        40,
        50,
    ]


def test_convert_cumulative_to_biweekly_requires_first_period() -> None:
    """Reject a cumulative series that does not begin on 16 April."""

    input_df = pd.DataFrame(
        {
            "season": [
                "2025/26",
                "2025/26",
            ],
            "period_end_date": pd.to_datetime(
                [
                    "2025-05-01",
                    "2025-05-16",
                ]
            ),
            "region": [
                "sao_paulo",
                "sao_paulo",
            ],
            "cumulative_crush_tonnes": [
                250,
                400,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="does not begin on 16 April",
    ):
        convert_cumulative_to_biweekly(
            input_df
        )


def test_convert_cumulative_to_biweekly_rejects_decrease() -> None:
    """Reject a cumulative series that decreases over time."""

    input_df = pd.DataFrame(
        {
            "season": [
                "2025/26",
                "2025/26",
                "2025/26",
            ],
            "period_end_date": pd.to_datetime(
                [
                    "2025-04-16",
                    "2025-05-01",
                    "2025-05-16",
                ]
            ),
            "region": [
                "sao_paulo",
                "sao_paulo",
                "sao_paulo",
            ],
            "cumulative_crush_tonnes": [
                100,
                250,
                230,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="Cumulative crushing tonnes decreased",
    ):
        convert_cumulative_to_biweekly(
            input_df
        )


def test_convert_cumulative_to_biweekly_rejects_missing_columns() -> None:
    """Require all columns needed for cumulative conversion."""

    input_df = pd.DataFrame(
        {
            "season": [
                "2025/26",
            ],
            "region": [
                "sao_paulo",
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="required columns are missing",
    ):
        convert_cumulative_to_biweekly(
            input_df
        )