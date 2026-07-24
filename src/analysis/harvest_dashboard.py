"""
Harvest Intelligence Dashboard

Build dashboard-ready datasets for historical harvest
benchmarking and current-season monitoring.
"""

import pandas as pd

from src.analysis.harvest_benchmark import (
    build_historical_percentile_bands,
)
from src.analysis.harvest_preprocessing import (
    assign_report_period_order,
)


def build_current_season_crush_curve(
    cumulative_df: pd.DataFrame,
    current_season: str,
) -> pd.DataFrame:
    """
    Build the current season cumulative-crushing curve
    using standardized reporting-period positions.
    """

    ordered_df = assign_report_period_order(
        cumulative_df
    )

    current_curve_df = ordered_df.loc[
        ordered_df["season"].eq(
            current_season
        ),
        [
            "season",
            "period_end_date",
            "report_period_order",
            "report_period_label",
            "cumulative_crush_tonnes",
        ],
    ].copy()

    if current_curve_df.empty:
        raise ValueError(
            f"Current season {current_season!r} "
            "was not found."
        )

    return (
        current_curve_df
        .sort_values(
            "report_period_order"
        )
        .reset_index(
            drop=True
        )
    )


def build_percentile_band_dashboard_dataset(
    cumulative_df: pd.DataFrame,
    current_season: str,
) -> pd.DataFrame:
    """
    Combine historical percentile bands with the current
    season cumulative-crushing curve.

    The resulting dataset supports visualization of:

    - the historical 5th–95th percentile range
    - the historical 25th–75th percentile range
    - the historical median and mean
    - the current-season cumulative crushing curve
    """

    percentile_bands_df = (
        build_historical_percentile_bands(
            cumulative_df=cumulative_df,
            current_season=current_season,
        )
    )

    current_curve_df = (
        build_current_season_crush_curve(
            cumulative_df=cumulative_df,
            current_season=current_season,
        )
    )

    dashboard_df = percentile_bands_df.merge(
        current_curve_df[
            [
                "period_end_date",
                "report_period_order",
                "cumulative_crush_tonnes",
            ]
        ].rename(
            columns={
                "period_end_date": (
                    "current_period_end_date"
                ),
                "cumulative_crush_tonnes": (
                    "current_cumulative_crush_tonnes"
                ),
            }
        ),
        on="report_period_order",
        how="left",
        validate="one_to_one",
    )

    dashboard_df["current_season"] = (
        current_season
    )

    output_columns = [
        "current_season",
        "report_period_order",
        "report_period_label",
        "current_period_end_date",
        "historical_season_count",
        "minimum_crush_tonnes",
        "percentile_05_crush_tonnes",
        "percentile_25_crush_tonnes",
        "median_crush_tonnes",
        "mean_crush_tonnes",
        "percentile_75_crush_tonnes",
        "percentile_95_crush_tonnes",
        "maximum_crush_tonnes",
        "interquartile_range_tonnes",
        "percentile_90_range_tonnes",
        "current_cumulative_crush_tonnes",
    ]

    return (
        dashboard_df[
            output_columns
        ]
        .sort_values(
            "report_period_order"
        )
        .reset_index(
            drop=True
        )
    )