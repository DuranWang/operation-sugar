"""
Harvest Intelligence Preprocessing

Validate biweekly harvest observations, build cumulative
crushing histories, and assign standardized reporting periods.
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

    crush_tonnes = pd.to_numeric(
        harvest_df["crush_tonnes"],
        errors="raise",
    )

    if crush_tonnes.lt(0).any():
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

    duplicate_rows = working_df.duplicated(
        subset=[
            "season",
            "period_end_date",
        ],
        keep=False,
    )

    if duplicate_rows.any():
        duplicates = working_df.loc[
            duplicate_rows,
            [
                "season",
                "period_end_date",
            ],
        ]

        raise ValueError(
            "Duplicate season reporting dates were found:\n"
            f"{duplicates.to_string(index=False)}"
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

    ordered_df["period_end_date"] = (
        pd.to_datetime(
            ordered_df["period_end_date"],
            errors="raise",
        )
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

    duplicate_periods = ordered_df.duplicated(
        subset=[
            "season",
            "report_period_order",
        ],
        keep=False,
    )

    if duplicate_periods.any():
        duplicate_rows = ordered_df.loc[
            duplicate_periods,
            [
                "season",
                "period_end_date",
                "report_period_order",
            ],
        ]

        raise ValueError(
            "Duplicate observations were found within "
            "the same standardized reporting period:\n"
            f"{duplicate_rows.to_string(index=False)}"
        )

    return (
        ordered_df
        .sort_values(
            [
                "season",
                "report_period_order",
            ]
        )
        .reset_index(
            drop=True
        )
    )