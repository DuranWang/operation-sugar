"""
Month-Level Weather Features

Recover the temporal information lost when September-April weather
is aggregated into one growing-season summary.

The module converts state-level monthly weather observations from
long format into one model-ready row per state and harvest season.
"""

import pandas as pd


GROWING_SEASON_MONTHS = (
    9,
    10,
    11,
    12,
    1,
    2,
    3,
    4,
)

MONTH_LABELS = {
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dec",
    1: "jan",
    2: "feb",
    3: "mar",
    4: "apr",
}

IDENTIFIER_COLUMNS = [
    "state",
    "harvest_season",
]

MONTHLY_WEATHER_FEATURES = {
    "average_municipality_rainfall": "rainfall",
    "average_temperature": "temperature",
}

REQUIRED_COLUMNS = [
    *IDENTIFIER_COLUMNS,
    "month",
    *MONTHLY_WEATHER_FEATURES,
]


def get_month_level_feature_columns() -> list[str]:
    """Return month-level weather columns in Sep-Apr temporal order."""

    return [
        f"{feature_prefix}_{MONTH_LABELS[month]}"
        for feature_prefix in MONTHLY_WEATHER_FEATURES.values()
        for month in GROWING_SEASON_MONTHS
    ]


def _validate_monthly_weather(
    monthly_weather: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and return growing-season monthly weather records."""

    if monthly_weather.empty:
        raise ValueError(
            "Monthly weather dataframe is empty."
        )

    missing_columns = (
        set(REQUIRED_COLUMNS)
        - set(monthly_weather.columns)
    )

    if missing_columns:
        raise ValueError(
            "Monthly weather dataframe is missing columns: "
            f"{sorted(missing_columns)}"
        )

    weather_df = monthly_weather.copy()

    weather_df["month"] = pd.to_numeric(
        weather_df["month"],
        errors="raise",
    ).astype(int)

    for feature_column in MONTHLY_WEATHER_FEATURES:
        weather_df[feature_column] = pd.to_numeric(
            weather_df[feature_column],
            errors="raise",
        )

    weather_df = weather_df.loc[
        weather_df["month"].isin(
            GROWING_SEASON_MONTHS
        )
    ].copy()

    if weather_df.empty:
        raise ValueError(
            "No September-April weather observations were found."
        )

    if weather_df[
        REQUIRED_COLUMNS
    ].isna().any().any():
        raise ValueError(
            "Growing-season monthly weather contains missing values."
        )

    duplicate_rows = weather_df.duplicated(
        subset=[
            *IDENTIFIER_COLUMNS,
            "month",
        ],
        keep=False,
    )

    if duplicate_rows.any():
        duplicate_keys = (
            weather_df.loc[
                duplicate_rows,
                [
                    *IDENTIFIER_COLUMNS,
                    "month",
                ],
            ]
            .drop_duplicates()
            .sort_values(
                [
                    *IDENTIFIER_COLUMNS,
                    "month",
                ]
            )
        )

        raise ValueError(
            "Monthly weather contains duplicate "
            "state-season-month rows:\n"
            f"{duplicate_keys.to_string(index=False)}"
        )

    month_sets = (
        weather_df
        .groupby(
            IDENTIFIER_COLUMNS,
            sort=True,
        )["month"]
        .agg(lambda months: set(months))
    )

    expected_months = set(
        GROWING_SEASON_MONTHS
    )

    incomplete_groups = month_sets.loc[
        month_sets.ne(expected_months)
    ]

    if not incomplete_groups.empty:
        incomplete_details = []

        for group_key, observed_months in (
            incomplete_groups.items()
        ):
            missing_months = [
                month
                for month in GROWING_SEASON_MONTHS
                if month not in observed_months
            ]

            state, harvest_season = group_key
            incomplete_details.append(
                f"{state} {harvest_season}: "
                f"missing months {missing_months}"
            )

        raise ValueError(
            "Every state-season must contain exactly "
            "September-April weather observations. "
            + "; ".join(incomplete_details)
        )

    return weather_df


def pivot_monthly_weather_features(
    monthly_weather: pd.DataFrame,
) -> pd.DataFrame:
    """
    Pivot state-level monthly weather into model-ready features.

    Parameters
    ----------
    monthly_weather:
        State-level monthly weather observations containing a
        normalized `harvest_season`, calendar `month`, average
        municipality rainfall, and average temperature.

        Months outside September-April are ignored.

    Returns
    -------
    pd.DataFrame
        One row per state and harvest season. Rainfall columns are
        followed by temperature columns, each ordered September-April.
    """

    weather_df = _validate_monthly_weather(
        monthly_weather
    )

    wide_feature_frames = []

    for source_column, feature_prefix in (
        MONTHLY_WEATHER_FEATURES.items()
    ):
        feature_df = weather_df.pivot(
            index=IDENTIFIER_COLUMNS,
            columns="month",
            values=source_column,
        )

        feature_df = feature_df.reindex(
            columns=GROWING_SEASON_MONTHS
        )

        feature_df.columns = [
            f"{feature_prefix}_{MONTH_LABELS[month]}"
            for month in GROWING_SEASON_MONTHS
        ]

        wide_feature_frames.append(
            feature_df
        )

    month_level_weather = (
        pd.concat(
            wide_feature_frames,
            axis=1,
        )
        .reset_index()
        .sort_values(
            IDENTIFIER_COLUMNS
        )
        .reset_index(drop=True)
    )

    expected_columns = [
        *IDENTIFIER_COLUMNS,
        *get_month_level_feature_columns(),
    ]

    month_level_weather = month_level_weather[
        expected_columns
    ]

    if month_level_weather[
        get_month_level_feature_columns()
    ].isna().any().any():
        raise ValueError(
            "Month-level weather features contain missing values."
        )

    if month_level_weather.duplicated(
        subset=IDENTIFIER_COLUMNS
    ).any():
        raise ValueError(
            "Month-level weather contains duplicate state-season rows."
        )

    return month_level_weather