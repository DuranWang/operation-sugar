"""
Historical Harvest Benchmarking

Build comparable cross-season harvest snapshots, rank
cumulative crushing pace, and calculate historical
percentile bands.
"""

import pandas as pd

from src.analysis.harvest_preprocessing import (
    assign_report_period_order,
)


def build_comparable_crush_snapshot(
    cumulative_df: pd.DataFrame,
    current_season: str,
    max_day_difference: int = 7,
) -> pd.DataFrame:
    """
    Match every crop season to the latest available
    season-relative date in the current season.
    """

    required_columns = {
        "season",
        "period_end_date",
        "season_day",
        "cumulative_crush_tonnes",
    }

    missing_columns = (
        required_columns
        - set(cumulative_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Cumulative crushing dataframe is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if cumulative_df.empty:
        raise ValueError(
            "Cumulative crushing dataframe "
            "must not be empty."
        )

    if max_day_difference < 0:
        raise ValueError(
            "max_day_difference must be non-negative."
        )

    current_season_df = cumulative_df.loc[
        cumulative_df["season"].eq(
            current_season
        )
    ].copy()

    if current_season_df.empty:
        raise ValueError(
            f"Current season {current_season!r} "
            "was not found."
        )

    latest_current_row = (
        current_season_df
        .sort_values(
            "period_end_date"
        )
        .iloc[-1]
    )

    target_season_day = int(
        latest_current_row["season_day"]
    )

    target_reporting_date = (
        latest_current_row[
            "period_end_date"
        ]
    )

    working_df = cumulative_df.copy()

    working_df[
        "target_season_day"
    ] = target_season_day

    working_df["day_difference"] = (
        working_df["season_day"]
        - target_season_day
    )

    working_df[
        "absolute_day_difference"
    ] = (
        working_df[
            "day_difference"
        ].abs()
    )

    snapshot_df = (
        working_df
        .sort_values(
            [
                "season",
                "absolute_day_difference",
                "period_end_date",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .groupby(
            "season",
            as_index=False,
        )
        .first()
    )

    snapshot_df = snapshot_df.loc[
        snapshot_df[
            "absolute_day_difference"
        ].le(max_day_difference)
    ].copy()

    if snapshot_df.empty:
        raise ValueError(
            "No comparable observations were found "
            f"within ±{max_day_difference} season days."
        )

    snapshot_df[
        "target_reporting_date"
    ] = target_reporting_date

    output_columns = [
        "season",
        "period_end_date",
        "target_reporting_date",
        "season_day",
        "target_season_day",
        "day_difference",
        "absolute_day_difference",
        "cumulative_crush_tonnes",
    ]

    return (
        snapshot_df[
            output_columns
        ]
        .sort_values(
            "season"
        )
        .reset_index(
            drop=True
        )
    )


def rank_cumulative_crush(
    snapshot_df: pd.DataFrame,
    current_season: str,
) -> pd.DataFrame:
    """
    Rank crop seasons by cumulative crushing tonnage
    at comparable season-relative reporting dates.

    Rank 1 represents the greatest cumulative crushing
    volume at the aligned point in the season.
    """

    required_columns = {
        "season",
        "period_end_date",
        "season_day",
        "day_difference",
        "cumulative_crush_tonnes",
    }

    missing_columns = (
        required_columns
        - set(snapshot_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Comparable snapshot is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if snapshot_df.empty:
        raise ValueError(
            "Comparable snapshot dataframe "
            "must not be empty."
        )

    if current_season not in snapshot_df["season"].values:
        raise ValueError(
            f"Current season {current_season!r} "
            "was not found in the comparable snapshot."
        )

    ranking_df = snapshot_df.copy()

    ranking_df["rank"] = (
        ranking_df[
            "cumulative_crush_tonnes"
        ]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    total_seasons = (
        ranking_df["season"].nunique()
    )

    historical_seasons = (
        total_seasons - 1
    )

    ranking_df["total_seasons"] = (
        total_seasons
    )

    ranking_df["historical_seasons"] = (
        historical_seasons
    )

    ranking_df["percentile"] = (
        ranking_df[
            "cumulative_crush_tonnes"
        ]
        .rank(
            method="average",
            ascending=True,
            pct=True,
        )
        .mul(100)
    )

    current_crush_tonnes = (
        ranking_df.loc[
            ranking_df["season"].eq(
                current_season
            ),
            "cumulative_crush_tonnes",
        ]
        .iloc[0]
    )

    historical_df = ranking_df.loc[
        ~ranking_df["season"].eq(
            current_season
        )
    ]

    if historical_seasons == 0:
        historical_percentile = float(
            "nan"
        )
    else:
        historical_percentile = (
            historical_df[
                "cumulative_crush_tonnes"
            ]
            .lt(current_crush_tonnes)
            .sum()
            / historical_seasons
            * 100
        )

    ranking_df["historical_percentile"] = (
        float("nan")
    )

    ranking_df.loc[
        ranking_df["season"].eq(
            current_season
        ),
        "historical_percentile",
    ] = historical_percentile

    ranking_df["is_current_season"] = (
        ranking_df["season"].eq(
            current_season
        )
    )

    output_columns = [
        "rank",
        "season",
        "cumulative_crush_tonnes",
        "percentile",
        "historical_percentile",
        "period_end_date",
        "season_day",
        "day_difference",
        "total_seasons",
        "historical_seasons",
        "is_current_season",
    ]

    return (
        ranking_df[
            output_columns
        ]
        .sort_values(
            [
                "rank",
                "season",
            ]
        )
        .reset_index(
            drop=True
        )
    )


def build_historical_percentile_bands(
    cumulative_df: pd.DataFrame,
    current_season: str,
) -> pd.DataFrame:
    """
    Calculate historical cumulative-crushing percentile bands
    for every standardized biweekly reporting period.

    The current season is excluded from historical
    distribution calculations.

    The output includes:

    - minimum and maximum historical observations
    - 5th and 95th percentile boundaries
    - 25th and 75th percentile boundaries
    - historical median and mean
    """

    ordered_df = assign_report_period_order(
        cumulative_df
    )

    historical_df = ordered_df.loc[
        ~ordered_df["season"].eq(
            current_season
        )
    ].copy()

    if historical_df.empty:
        raise ValueError(
            "No completed historical seasons remain after "
            "excluding the current season."
        )

    percentile_bands_df = (
        historical_df
        .groupby(
            [
                "report_period_order",
                "report_period_label",
            ],
            as_index=False,
        )
        .agg(
            historical_season_count=(
                "season",
                "nunique",
            ),
            minimum_crush_tonnes=(
                "cumulative_crush_tonnes",
                "min",
            ),
            percentile_05_crush_tonnes=(
                "cumulative_crush_tonnes",
                lambda values: values.quantile(
                    0.05
                ),
            ),
            percentile_25_crush_tonnes=(
                "cumulative_crush_tonnes",
                lambda values: values.quantile(
                    0.25
                ),
            ),
            median_crush_tonnes=(
                "cumulative_crush_tonnes",
                "median",
            ),
            mean_crush_tonnes=(
                "cumulative_crush_tonnes",
                "mean",
            ),
            percentile_75_crush_tonnes=(
                "cumulative_crush_tonnes",
                lambda values: values.quantile(
                    0.75
                ),
            ),
            percentile_95_crush_tonnes=(
                "cumulative_crush_tonnes",
                lambda values: values.quantile(
                    0.95
                ),
            ),
            maximum_crush_tonnes=(
                "cumulative_crush_tonnes",
                "max",
            ),
        )
        .sort_values(
            "report_period_order"
        )
        .reset_index(
            drop=True
        )
    )

    percentile_bands_df[
        "interquartile_range_tonnes"
    ] = (
        percentile_bands_df[
            "percentile_75_crush_tonnes"
        ]
        - percentile_bands_df[
            "percentile_25_crush_tonnes"
        ]
    )

    percentile_bands_df[
        "percentile_90_range_tonnes"
    ] = (
        percentile_bands_df[
            "percentile_95_crush_tonnes"
        ]
        - percentile_bands_df[
            "percentile_05_crush_tonnes"
        ]
    )

    return percentile_bands_df