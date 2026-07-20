import pandas as pd

from .growing_season import select_growing_season
from .rainfall import calculate_max_consecutive_dry_days
from .temperature import calculate_average_temperature


def calculate_growing_season_features(
    weather_df: pd.DataFrame,
    dry_day_threshold: float = 1.0,
) -> pd.DataFrame:
    
    """
    Calculate growing-season weather features for each municipality
    and harvest year.

    Features
    --------
    - growing_season_total_rainfall
    - growing_season_average_temperature
    - growing_season_max_consecutive_dry_days

    Parameters
    ----------
    weather_df:
        Daily weather observations containing municipality identifiers,
        calendar year, month, date, rainfall, and temperature.

    dry_day_threshold:
        Daily rainfall threshold below which a day is classified as dry.

    Returns
    -------
    pd.DataFrame
        One row per municipality and harvest year.
    """

    required_columns = {
        "ibge_code",
        "municipality",
        "state",
        "year",
        "month",
        "date",
        "PRECTOTCORR",
        "T2M",
    }

    missing_columns = required_columns - set(weather_df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    growing_season_weather = select_growing_season(weather_df)

    growing_season_weather = growing_season_weather.copy()

    growing_season_weather["date"] = pd.to_datetime(
        growing_season_weather["date"]
    )

    growing_season_weather = growing_season_weather.sort_values(
        [
            "ibge_code",
            "harvest_year",
            "date",
        ]
    )

    group_columns = [
        "ibge_code",
        "municipality",
        "state",
        "harvest_year",
    ]

    growing_season_summary = (
        growing_season_weather
        .groupby(
            group_columns,
            as_index=False,
        )
        .agg(
            growing_season_total_rainfall=(
                "PRECTOTCORR",
                "sum",
            ),
            growing_season_average_temperature=(
                "T2M",
                calculate_average_temperature,
            ),
             growing_season_observation_days=(
            "date",
            "count",
            ),
            growing_season_start_date=(
                "date",
                "min",
            ),
            growing_season_end_date=(
                "date",
                "max",
            ),
        )
    )

    growing_season_cdd = (
        growing_season_weather
        .groupby(group_columns)[["date", "PRECTOTCORR"]]
        .apply(
            lambda group: calculate_max_consecutive_dry_days(
                rainfall=group["PRECTOTCORR"],
                dates=group["date"],
                dry_day_threshold=dry_day_threshold,
            )
        )
        .rename("growing_season_max_consecutive_dry_days")
        .reset_index()
    )

    growing_season_features = growing_season_summary.merge(
        growing_season_cdd,
        on=group_columns,
        how="left",
    )

    growing_season_features[
        "growing_season_total_rainfall"
    ] = growing_season_features[
        "growing_season_total_rainfall"
    ].round(2)

    growing_season_features[
        "growing_season_average_temperature"
    ] = growing_season_features[
        "growing_season_average_temperature"
    ].round(2)

    return growing_season_features


