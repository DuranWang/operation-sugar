import pandas as pd
import pytest

from feature_engineering.month_level_weather import (
    get_month_level_feature_columns,
    pivot_monthly_weather_features,
)


MONTHS = [
    9,
    10,
    11,
    12,
    1,
    2,
    3,
    4,
]


def build_complete_weather() -> pd.DataFrame:
    """Build two complete state-season weather samples."""

    rows = []

    for season_index, harvest_season in enumerate(
        [
            "24-25",
            "25-26",
        ]
    ):
        for month_position, month in enumerate(MONTHS):
            rows.append(
                {
                    "state": "SP",
                    "harvest_season": harvest_season,
                    "month": month,
                    "average_municipality_rainfall": (
                        100.0
                        + 10.0 * season_index
                        + month_position
                    ),
                    "average_temperature": (
                        20.0
                        + season_index
                        + month_position / 10.0
                    ),
                }
            )

    rows.append(
        {
            "state": "SP",
            "harvest_season": "25-26",
            "month": 5,
            "average_municipality_rainfall": 999.0,
            "average_temperature": 99.0,
        }
    )

    return pd.DataFrame(rows).sample(
        frac=1.0,
        random_state=42,
    ).reset_index(drop=True)


def test_pivot_monthly_weather_features() -> None:
    monthly_weather = build_complete_weather()

    result = pivot_monthly_weather_features(
        monthly_weather
    )

    expected_columns = [
        "state",
        "harvest_season",
        "rainfall_sep",
        "rainfall_oct",
        "rainfall_nov",
        "rainfall_dec",
        "rainfall_jan",
        "rainfall_feb",
        "rainfall_mar",
        "rainfall_apr",
        "temperature_sep",
        "temperature_oct",
        "temperature_nov",
        "temperature_dec",
        "temperature_jan",
        "temperature_feb",
        "temperature_mar",
        "temperature_apr",
    ]

    assert list(result.columns) == expected_columns
    assert len(result) == 2

    first_season = result.loc[
        result["harvest_season"].eq("24-25")
    ].iloc[0]

    assert first_season["rainfall_sep"] == 100.0
    assert first_season["rainfall_dec"] == 103.0
    assert first_season["rainfall_jan"] == 104.0
    assert first_season["rainfall_apr"] == 107.0

    assert first_season["temperature_sep"] == 20.0
    assert first_season["temperature_apr"] == 20.7

    assert 999.0 not in result.to_numpy()
    assert 99.0 not in result.to_numpy()


def test_feature_column_order_is_temporal() -> None:
    assert get_month_level_feature_columns() == [
        "rainfall_sep",
        "rainfall_oct",
        "rainfall_nov",
        "rainfall_dec",
        "rainfall_jan",
        "rainfall_feb",
        "rainfall_mar",
        "rainfall_apr",
        "temperature_sep",
        "temperature_oct",
        "temperature_nov",
        "temperature_dec",
        "temperature_jan",
        "temperature_feb",
        "temperature_mar",
        "temperature_apr",
    ]


def test_missing_required_column_raises_error() -> None:
    monthly_weather = build_complete_weather().drop(
        columns=["average_temperature"]
    )

    with pytest.raises(
        ValueError,
        match="missing columns",
    ):
        pivot_monthly_weather_features(
            monthly_weather
        )


def test_duplicate_state_season_month_raises_error() -> None:
    monthly_weather = build_complete_weather()

    duplicate_row = monthly_weather.loc[
        monthly_weather["month"].eq(9)
        & monthly_weather["harvest_season"].eq("24-25")
    ].copy()

    monthly_weather = pd.concat(
        [
            monthly_weather,
            duplicate_row,
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicate state-season-month rows",
    ):
        pivot_monthly_weather_features(
            monthly_weather
        )


def test_incomplete_growing_season_raises_error() -> None:
    monthly_weather = build_complete_weather()

    monthly_weather = monthly_weather.loc[
        ~(
            monthly_weather["harvest_season"].eq("24-25")
            & monthly_weather["month"].eq(4)
        )
    ].copy()

    with pytest.raises(
        ValueError,
        match=r"missing months \[4\]",
    ):
        pivot_monthly_weather_features(
            monthly_weather
        )


def test_missing_weather_value_raises_error() -> None:
    monthly_weather = build_complete_weather()

    missing_value_index = monthly_weather.loc[
        monthly_weather["harvest_season"].eq("24-25")
        & monthly_weather["month"].eq(1)
    ].index[0]

    monthly_weather.loc[
        missing_value_index,
        "average_temperature",
    ] = pd.NA

    with pytest.raises(
        ValueError,
        match="contains missing values",
    ):
        pivot_monthly_weather_features(
            monthly_weather
        )


def test_no_growing_season_months_raises_error() -> None:
    monthly_weather = pd.DataFrame(
        {
            "state": ["SP"],
            "harvest_season": ["25-26"],
            "month": [5],
            "average_municipality_rainfall": [100.0],
            "average_temperature": [22.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="No September-April",
    ):
        pivot_monthly_weather_features(
            monthly_weather
        )