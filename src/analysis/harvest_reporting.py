"""
Harvest Intelligence Reporting

Generate human-readable summaries from historical harvest
ranking and benchmarking outputs.
"""

import pandas as pd


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