"""
Harvest Metrics

Calculate season-level harvest timing metrics from monthly
UNICA sugarcane crushing shares.
"""

import pandas as pd

SEASON_MONTH_LABELS = {
    1: "Apr Start",
    2: "May",
    3: "Jun",
    4: "Jul",
    5: "Aug",
    6: "Sep",
    7: "Oct",
    8: "Nov",
    9: "Dec",
    10: "Jan",
    11: "Feb",
    12: "Mar",
    13: "Apr End",
}

DEFAULT_START_THRESHOLD = 0.10
DEFAULT_END_THRESHOLD = 0.90


def validate_monthly_harvest_summary(
    monthly_summary: pd.DataFrame,
) -> None:
    """
    Validate the monthly harvest summary required to
    calculate harvest timing metrics.
    """

    required_columns = {
        "season",
        "season_month_order",
        "monthly_share_of_season",
    }

    missing_columns = (
        required_columns
        - set(monthly_summary.columns)
    )

    if missing_columns:
        raise ValueError(
            "Monthly harvest summary is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if monthly_summary.empty:
        raise ValueError(
            "Monthly harvest summary is empty."
        )

    if monthly_summary[
        "season"
    ].isna().any():
        raise ValueError(
            "Monthly harvest summary contains missing season values."
        )

    if monthly_summary[
        "season_month_order"
    ].isna().any():
        raise ValueError(
            "Monthly harvest summary contains missing "
            "season month order values."
        )

    invalid_month_orders = monthly_summary.loc[
        monthly_summary[
            "season_month_order"
        ] <= 0,
        "season_month_order",
    ]

    if not invalid_month_orders.empty:
        raise ValueError(
            "Season month order values must be positive."
        )

    invalid_shares = monthly_summary.loc[
        (
            monthly_summary[
                "monthly_share_of_season"
            ] < 0
        )
        |
        (
            monthly_summary[
                "monthly_share_of_season"
            ] > 1
        ),
        "monthly_share_of_season",
    ]

    if not invalid_shares.empty:
        raise ValueError(
            "Monthly harvest shares must be between 0 and 1."
        )

    duplicate_periods = monthly_summary.duplicated(
        subset=[
            "season",
            "season_month_order",
        ],
        keep=False,
    )

    if duplicate_periods.any():
        duplicate_rows = monthly_summary.loc[
            duplicate_periods,
            [
                "season",
                "season_month_order",
            ],
        ]

        raise ValueError(
            "Monthly harvest summary contains duplicate "
            "season-period combinations:\n"
            f"{duplicate_rows.to_string(index=False)}"
        )


def validate_thresholds(
    start_threshold: float,
    end_threshold: float,
) -> None:
    """
    Validate cumulative crushing thresholds.
    """

    if not 0 <= start_threshold <= 1:
        raise ValueError(
            "Start threshold must be between 0 and 1."
        )

    if not 0 <= end_threshold <= 1:
        raise ValueError(
            "End threshold must be between 0 and 1."
        )

    if start_threshold >= end_threshold:
        raise ValueError(
            "Start threshold must be smaller than end threshold."
        )


def add_cumulative_harvest_share(
    monthly_summary: pd.DataFrame,
) -> pd.DataFrame:
    """
    Sort monthly observations within each crop season
    and calculate cumulative seasonal crushing share.
    """

    ordered_summary = (
        monthly_summary
        .sort_values(
            [
                "season",
                "season_month_order",
            ]
        )
        .copy()
    )

    ordered_summary[
        "cumulative_share_of_season"
    ] = (
        ordered_summary
        .groupby(
            "season"
        )[
            "monthly_share_of_season"
        ]
        .cumsum()
    )

    return ordered_summary


def find_threshold_period(
    season_df: pd.DataFrame,
    threshold: float,
) -> pd.Series:
    """
    Return the first season period in which cumulative
    crushing reaches or exceeds the given threshold.
    """

    threshold_rows = season_df.loc[
        season_df[
            "cumulative_share_of_season"
        ] >= threshold
    ]

    if threshold_rows.empty:
        raise ValueError(
            f"Season {season_df['season'].iloc[0]} "
            f"never reaches cumulative threshold {threshold:.0%}."
        )

    return threshold_rows.iloc[0]


def calculate_harvest_start(
    season_df: pd.DataFrame,
    start_threshold: float = DEFAULT_START_THRESHOLD,
) -> pd.Series:
    """
    Return the first period in which cumulative seasonal
    crushing reaches or exceeds the start threshold.
    """

    return find_threshold_period(
        season_df=season_df,
        threshold=start_threshold,
    )


def calculate_harvest_end(
    season_df: pd.DataFrame,
    end_threshold: float = DEFAULT_END_THRESHOLD,
) -> pd.Series:
    """
    Return the first period in which cumulative seasonal
    crushing reaches or exceeds the end threshold.
    """

    return find_threshold_period(
        season_df=season_df,
        threshold=end_threshold,
    )


def calculate_harvest_duration(
    harvest_start_period: int,
    harvest_end_period: int,
) -> int:
    """
    Calculate the number of season-relative months between
    Harvest Start and Harvest End.
    """

    if harvest_end_period < harvest_start_period:
        raise ValueError(
            "Harvest end period cannot occur before "
            "harvest start period."
        )

    return (
        harvest_end_period
        - harvest_start_period
    )


def build_harvest_metrics(
    monthly_summary: pd.DataFrame,
    start_threshold: float = DEFAULT_START_THRESHOLD,
    end_threshold: float = DEFAULT_END_THRESHOLD,
) -> pd.DataFrame:
    """
    Build season-level harvest timing metrics.

    Harvest Start:
        First period in which cumulative seasonal crushing
        reaches or exceeds the start threshold.

    Harvest End:
        First period in which cumulative seasonal crushing
        reaches or exceeds the end threshold.

    Harvest Duration:
        Number of season-relative months between Harvest
        Start and Harvest End.
    """

    validate_monthly_harvest_summary(
        monthly_summary
    )

    validate_thresholds(
        start_threshold=start_threshold,
        end_threshold=end_threshold,
    )

    cumulative_summary = (
        add_cumulative_harvest_share(
            monthly_summary
        )
    )

    metric_records = []

    for season, season_df in cumulative_summary.groupby(
        "season",
        sort=False,
    ):
        season_df = (
            season_df
            .sort_values(
                "season_month_order"
            )
            .reset_index(
                drop=True
            )
        )

        harvest_start_row = (
            calculate_harvest_start(
                season_df=season_df,
                start_threshold=start_threshold,
            )
        )

        harvest_end_row = (
            calculate_harvest_end(
                season_df=season_df,
                end_threshold=end_threshold,
            )
        )

        harvest_start_period = int(
            harvest_start_row[
                "season_month_order"
            ]
        )

        harvest_end_period = int(
            harvest_end_row[
                "season_month_order"
            ]
        )

        harvest_duration_months = (
            calculate_harvest_duration(
                harvest_start_period=harvest_start_period,
                harvest_end_period=harvest_end_period,
            )
        )

        metric_record = {
            "season": season,
            "harvest_start_period": harvest_start_period,
            "harvest_start_label": SEASON_MONTH_LABELS[
                harvest_start_period
            ],
            "harvest_end_period": harvest_end_period,
            "harvest_end_label": SEASON_MONTH_LABELS[
                harvest_end_period
            ],
            "harvest_duration_months": (
                harvest_duration_months
            ),
            "harvest_start_cumulative_share": float(
                harvest_start_row[
                    "cumulative_share_of_season"
                ]
            ),
            "harvest_end_cumulative_share": float(
                harvest_end_row[
                    "cumulative_share_of_season"
                ]
            ),
        }

        if "calendar_year" in season_df.columns:
            metric_record[
                "harvest_start_year"
            ] = int(
                harvest_start_row[
                    "calendar_year"
                ]
            )

            metric_record[
                "harvest_end_year"
            ] = int(
                harvest_end_row[
                    "calendar_year"
                ]
            )

        if "month" in season_df.columns:
            metric_record[
                "harvest_start_month"
            ] = int(
                harvest_start_row[
                    "month"
                ]
            )

            metric_record[
                "harvest_end_month"
            ] = int(
                harvest_end_row[
                    "month"
                ]
            )

        metric_records.append(
            metric_record
        )

    harvest_metrics_df = (
        pd.DataFrame(
            metric_records
        )
    )

    if harvest_metrics_df.empty:
        raise ValueError(
            "No harvest metrics were generated."
        )

    return harvest_metrics_df