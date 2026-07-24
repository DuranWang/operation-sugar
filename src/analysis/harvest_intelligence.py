"""
Historical Harvest Intelligence

Build comparable cross-season crushing snapshots and rank
cumulative crushing pace at equivalent season-relative dates.
"""

import pandas as pd


REQUIRED_HARVEST_COLUMNS = {
    "season",
    "period_end_date",
    "region",
    "crush_tonnes",
}

REPORT_PERIOD_ORDER = {
    (4, 16): 1,
    (5, 1): 2,
    (5, 16): 3,
    (6, 1): 4,
    (6, 16): 5,
    (7, 1): 6,
    (7, 16): 7,
    (8, 1): 8,
    (8, 16): 9,
    (9, 1): 10,
    (9, 16): 11,
    (10, 1): 12,
    (10, 16): 13,
    (11, 1): 14,
    (11, 16): 15,
    (12, 1): 16,
    (12, 16): 17,
    (1, 1): 18,
    (1, 16): 19,
    (2, 1): 20,
    (2, 16): 21,
    (3, 1): 22,
    (3, 16): 23,
    (4, 1): 24,
}

REPORT_PERIOD_LABELS = {
    1: "Apr 16",
    2: "May 01",
    3: "May 16",
    4: "Jun 01",
    5: "Jun 16",
    6: "Jul 01",
    7: "Jul 16",
    8: "Aug 01",
    9: "Aug 16",
    10: "Sep 01",
    11: "Sep 16",
    12: "Oct 01",
    13: "Oct 16",
    14: "Nov 01",
    15: "Nov 16",
    16: "Dec 01",
    17: "Dec 16",
    18: "Jan 01",
    19: "Jan 16",
    20: "Feb 01",
    21: "Feb 16",
    22: "Mar 01",
    23: "Mar 16",
    24: "Apr 01",
}


def extract_season_start_year(
    season: pd.Series,
) -> pd.Series:
    """
    Convert season labels such as '25-26' into
    four-digit starting years such as 2025.
    """

    season_start_year = (
        season
        .astype(str)
        .str.split("-")
        .str[0]
    )

    invalid_labels = (
        ~season_start_year.str.fullmatch(
            r"\d{2}"
        )
    )

    if invalid_labels.any():
        invalid_seasons = (
            season.loc[
                invalid_labels
            ]
            .astype(str)
            .unique()
        )

        raise ValueError(
            "Unable to parse season labels: "
            f"{sorted(invalid_seasons)}"
        )

    return (
        season_start_year.astype(int)
        + 2000
    )


def validate_harvest_intelligence_input(
    harvest_df: pd.DataFrame,
) -> None:
    """
    Validate biweekly harvest data used by the
    historical harvest intelligence analysis.
    """

    if harvest_df.empty:
        raise ValueError(
            "Harvest intelligence input dataframe "
            "must not be empty."
        )

    missing_columns = (
        REQUIRED_HARVEST_COLUMNS
        - set(harvest_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Harvest intelligence input is missing "
            "required columns: "
            f"{sorted(missing_columns)}"
        )

    required_columns = [
        "season",
        "period_end_date",
        "region",
        "crush_tonnes",
    ]

    if harvest_df[
        required_columns
    ].isna().any().any():
        raise ValueError(
            "Harvest intelligence input contains "
            "missing values in required columns."
        )

    if (
        harvest_df["crush_tonnes"] < 0
    ).any():
        raise ValueError(
            "Harvest intelligence input contains "
            "negative crushing values."
        )


def build_cumulative_crush_history(
    harvest_df: pd.DataFrame,
    region: str = "sao_paulo",
) -> pd.DataFrame:
    """
    Build cumulative crushing histories for each crop season.

    Season-relative time is measured from April 1 of the
    crop season's starting year.
    """

    validate_harvest_intelligence_input(
        harvest_df
    )

    working_df = harvest_df.loc[
        harvest_df["region"].eq(region)
    ].copy()

    if working_df.empty:
        raise ValueError(
            f"No observations were found for region "
            f"{region!r}."
        )

    working_df["period_end_date"] = (
        pd.to_datetime(
            working_df["period_end_date"],
            errors="raise",
        )
    )

    working_df["crush_tonnes"] = (
        pd.to_numeric(
            working_df["crush_tonnes"],
            errors="raise",
        )
    )

    working_df["season_start_year"] = (
        extract_season_start_year(
            working_df["season"]
        )
    )

    working_df["season_start_date"] = (
        pd.to_datetime(
            working_df[
                "season_start_year"
            ].astype(str)
            + "-04-01"
        )
    )

    working_df["season_day"] = (
        working_df["period_end_date"]
        - working_df["season_start_date"]
    ).dt.days

    invalid_season_days = (
        working_df["season_day"] < 0
    )

    if invalid_season_days.any():
        invalid_rows = working_df.loc[
            invalid_season_days,
            [
                "season",
                "period_end_date",
                "season_start_date",
            ],
        ]

        raise ValueError(
            "Some observations occur before their "
            "crop-season start date:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    working_df = (
        working_df
        .sort_values(
            [
                "season_start_year",
                "period_end_date",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    working_df[
        "cumulative_crush_tonnes"
    ] = (
        working_df
        .groupby(
            "season"
        )["crush_tonnes"]
        .cumsum()
    )

    output_columns = [
        "season",
        "season_start_year",
        "season_start_date",
        "period_end_date",
        "season_day",
        "crush_tonnes",
        "cumulative_crush_tonnes",
    ]

    return working_df[
        output_columns
    ]


def build_comparable_crush_snapshot(
    cumulative_df: pd.DataFrame,
    current_season: str,
    max_day_difference: int = 7,
) -> pd.DataFrame:
    """
    Match every crop season to the latest available
    season-relative date in the current season.
    """

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

    The overall percentile includes the current season.
    The historical percentile compares the current season
    only with all other seasons in the snapshot.
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
        historical_percentile = float("nan")
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


def format_ordinal(
    value: int,
) -> str:
    """
    Format an integer as an English ordinal.
    """

    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(
            value % 10,
            "th",
        )

    return f"{value}{suffix}"


def build_harvest_ranking_summary(
    ranking_df: pd.DataFrame,
    current_season: str,
) -> str:
    """
    Build a concise research summary for the current
    season's cumulative crushing pace ranking.
    """

    required_columns = {
        "season",
        "rank",
        "total_seasons",
        "historical_seasons",
        "historical_percentile",
        "cumulative_crush_tonnes",
        "period_end_date",
    }

    missing_columns = (
        required_columns
        - set(ranking_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Harvest ranking dataframe is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if ranking_df.empty:
        raise ValueError(
            "Harvest ranking dataframe "
            "must not be empty."
        )

    current_rows = ranking_df.loc[
        ranking_df["season"].eq(
            current_season
        )
    ]

    if current_rows.empty:
        raise ValueError(
            f"Current season {current_season!r} "
            "was not found in the ranking dataframe."
        )

    current_row = current_rows.iloc[0]

    rank = int(
        current_row["rank"]
    )

    total_seasons = int(
        current_row["total_seasons"]
    )

    historical_seasons = int(
        current_row["historical_seasons"]
    )

    cumulative_crush_million_tonnes = (
        current_row[
            "cumulative_crush_tonnes"
        ]
        / 1_000_000
    )

    historical_percentile = float(
        current_row[
            "historical_percentile"
        ]
    )

    reporting_timestamp = pd.to_datetime(
        current_row["period_end_date"]
    )

    reporting_date = (
        f"{reporting_timestamp.strftime('%B')} "
        f"{reporting_timestamp.day}, "
        f"{reporting_timestamp.year}"
    )

    ordinal_rank = format_ordinal(
        rank
    )

    return (
        f"As of {reporting_date}, the {current_season} "
        "São Paulo season has crushed "
        f"{cumulative_crush_million_tonnes:.1f} million tonnes, "
        f"ranking {ordinal_rank} out of {total_seasons} seasons "
        f"and ahead of {historical_percentile:.1f}% of the "
        f"{historical_seasons} completed historical seasons."
    )

def assign_report_period_order(
    cumulative_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign each biweekly UNICA observation a standardized
    crop-season reporting-period order.

    The reporting sequence begins on April 16 and ends
    on April 1 of the following calendar year.
    """

    required_columns = {
        "season",
        "period_end_date",
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

    ordered_df = cumulative_df.copy()

    ordered_df["period_end_date"] = pd.to_datetime(
        ordered_df["period_end_date"],
        errors="raise",
    )

    month_day_pairs = list(
        zip(
            ordered_df["period_end_date"].dt.month,
            ordered_df["period_end_date"].dt.day,
        )
    )

    ordered_df["report_period_order"] = [
        REPORT_PERIOD_ORDER.get(
            month_day_pair
        )
        for month_day_pair in month_day_pairs
    ]

    missing_period_orders = (
        ordered_df[
            "report_period_order"
        ].isna()
    )

    if missing_period_orders.any():
        invalid_rows = ordered_df.loc[
            missing_period_orders,
            [
                "season",
                "period_end_date",
            ],
        ]

        raise ValueError(
            "Unable to assign standardized UNICA "
            "reporting-period order:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    ordered_df["report_period_order"] = (
        ordered_df[
            "report_period_order"
        ].astype(int)
    )

    ordered_df["report_period_label"] = (
        ordered_df[
            "report_period_order"
        ].map(
            REPORT_PERIOD_LABELS
        )
    )

    return ordered_df


def build_historical_percentile_bands(
    cumulative_df: pd.DataFrame,
    current_season: str,
) -> pd.DataFrame:
    """
    Calculate historical cumulative-crushing percentile bands
    for every standardized biweekly reporting period.

    The current season is excluded from historical distribution
    calculations.

    Parameters
    ----------
    cumulative_df:
        Cumulative crushing histories generated by
        build_cumulative_crush_history().

    current_season:
        Ongoing crop season excluded from the historical sample.

    Returns
    -------
    pd.DataFrame
        Historical distribution statistics by reporting period.
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

    duplicate_periods = (
        historical_df.duplicated(
            subset=[
                "season",
                "report_period_order",
            ],
            keep=False,
        )
    )

    if duplicate_periods.any():
        duplicate_rows = historical_df.loc[
            duplicate_periods,
            [
                "season",
                "period_end_date",
                "report_period_order",
            ],
        ]

        raise ValueError(
            "Historical data contains duplicate observations "
            "within the same reporting period:\n"
            f"{duplicate_rows.to_string(index=False)}"
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

    return percentile_bands_df


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
        "percentile_25_crush_tonnes",
        "median_crush_tonnes",
        "mean_crush_tonnes",
        "percentile_75_crush_tonnes",
        "maximum_crush_tonnes",
        "interquartile_range_tonnes",
        "current_cumulative_crush_tonnes",
    ]

    return dashboard_df[
        output_columns
    ]