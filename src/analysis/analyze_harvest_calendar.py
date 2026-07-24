"""
Historical Harvest Calendar Analysis

Analyze historical UNICA sugarcane crushing progress,
construct monthly harvest summaries, calculate harvest
timing metrics, and generate a harvest calendar heatmap.
"""

from pathlib import Path

import pandas as pd

from src.analysis.harvest_intelligence import (
    build_comparable_crush_snapshot,
    build_cumulative_crush_history,
    build_harvest_ranking_summary,
    build_percentile_band_dashboard_dataset,
    rank_cumulative_crush,
)

from src.feature_engineering.harvest_metrics import (
    build_harvest_metrics,
)
from src.visualization.harvest_heatmap import (
    filter_complete_seasons,
    save_harvest_heatmap,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "crushing"
    / "unica_biweekly_crush.csv"
)

HARVEST_METRICS_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "harvest_metrics.csv"
)

HARVEST_INTELLIGENCE_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "harvest_intelligence"
)

CUMULATIVE_CRUSH_HISTORY_OUTPUT_PATH = (
    HARVEST_INTELLIGENCE_OUTPUT_DIR
    / "cumulative_crush_history.csv"
)

COMPARABLE_CRUSH_SNAPSHOT_OUTPUT_PATH = (
    HARVEST_INTELLIGENCE_OUTPUT_DIR
    / "comparable_crush_snapshot.csv"
)

CUMULATIVE_CRUSH_RANKING_OUTPUT_PATH = (
    HARVEST_INTELLIGENCE_OUTPUT_DIR
    / "cumulative_crush_ranking.csv"
)

HISTORICAL_PERCENTILE_BANDS_OUTPUT_PATH = (
    HARVEST_INTELLIGENCE_OUTPUT_DIR
    / "historical_percentile_bands.csv"
)

START_THRESHOLD = 0.10
END_THRESHOLD = 0.90

SHARE_SUM_TOLERANCE = 1e-9

CURRENT_SEASON = "26-27"
MAX_DAY_DIFFERENCE = 7

SEASON_MONTH_ORDER_MAPPING = {
    5: 2,
    6: 3,
    7: 4,
    8: 5,
    9: 6,
    10: 7,
    11: 8,
    12: 9,
    1: 10,
    2: 11,
    3: 12,
}


def load_unica_history(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load the historical biweekly UNICA crushing database.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            "UNICA historical dataset not found: "
            f"{input_path}"
        )

    harvest_df = pd.read_csv(
        input_path,
        parse_dates=["period_end_date"],
    )

    required_columns = {
        "season",
        "period_end_date",
        "region",
        "crush_tonnes",
    }

    missing_columns = (
        required_columns
        - set(harvest_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "UNICA dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if harvest_df.empty:
        raise ValueError(
            "UNICA historical dataset is empty."
        )

    if harvest_df["season"].isna().any():
        raise ValueError(
            "UNICA dataset contains missing season values."
        )

    if harvest_df["period_end_date"].isna().any():
        raise ValueError(
            "UNICA dataset contains missing period end dates."
        )

    if harvest_df["region"].isna().any():
        raise ValueError(
            "UNICA dataset contains missing region values."
        )

    if harvest_df["crush_tonnes"].isna().any():
        raise ValueError(
            "UNICA dataset contains missing crushing values."
        )

    if (
        harvest_df["crush_tonnes"] < 0
    ).any():
        raise ValueError(
            "UNICA dataset contains negative crushing values."
        )

    return harvest_df


def filter_sao_paulo(
    harvest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep only São Paulo crushing observations.
    """

    sao_paulo_df = harvest_df.loc[
        harvest_df["region"] == "sao_paulo"
    ].copy()

    if sao_paulo_df.empty:
        raise ValueError(
            "No São Paulo observations were found."
        )

    return sao_paulo_df


def build_season_coverage_summary(
    harvest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarize temporal coverage and total crushing
    for each São Paulo crop season.
    """

    sao_paulo_df = filter_sao_paulo(
        harvest_df
    )

    season_summary = (
        sao_paulo_df
        .groupby(
            "season",
            as_index=False,
        )
        .agg(
            first_report_date=(
                "period_end_date",
                "min",
            ),
            last_report_date=(
                "period_end_date",
                "max",
            ),
            report_count=(
                "period_end_date",
                "count",
            ),
            season_total_crush_tonnes=(
                "crush_tonnes",
                "sum",
            ),
        )
        .sort_values(
            "first_report_date"
        )
        .reset_index(
            drop=True
        )
    )

    return season_summary


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

    invalid_season_labels = (
        ~season_start_year.str.fullmatch(
            r"\d{2}"
        )
    )

    if invalid_season_labels.any():
        invalid_labels = (
            season.loc[
                invalid_season_labels
            ]
            .astype(str)
            .unique()
        )

        raise ValueError(
            "Unable to parse season labels: "
            f"{sorted(invalid_labels)}"
        )

    return (
        season_start_year.astype(int)
        + 2000
    )


def assign_season_month_order(
    harvest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign each observation a season-relative month position.

    The crop-season sequence is:

    1  = starting April
    2  = May
    3  = June
    ...
    12 = March
    13 = ending April

    The two April periods are retained separately because
    they represent harvest initiation and harvest tail.
    """

    ordered_df = harvest_df.copy()

    ordered_df["calendar_year"] = (
        ordered_df[
            "period_end_date"
        ].dt.year
    )

    ordered_df["month"] = (
        ordered_df[
            "period_end_date"
        ].dt.month
    )

    ordered_df["season_start_year"] = (
        extract_season_start_year(
            ordered_df["season"]
        )
    )

    ordered_df["season_month_order"] = (
        ordered_df["month"].map(
            SEASON_MONTH_ORDER_MAPPING
        )
    )

    is_starting_april = (
        (ordered_df["month"] == 4)
        & (
            ordered_df["calendar_year"]
            == ordered_df["season_start_year"]
        )
    )

    is_ending_april = (
        (ordered_df["month"] == 4)
        & (
            ordered_df["calendar_year"]
            == ordered_df["season_start_year"] + 1
        )
    )

    ordered_df.loc[
        is_starting_april,
        "season_month_order",
    ] = 1

    ordered_df.loc[
        is_ending_april,
        "season_month_order",
    ] = 13

    missing_month_orders = (
        ordered_df[
            "season_month_order"
        ].isna()
    )

    if missing_month_orders.any():
        invalid_rows = ordered_df.loc[
            missing_month_orders,
            [
                "season",
                "period_end_date",
                "calendar_year",
                "month",
            ],
        ]

        raise ValueError(
            "Unable to assign season-relative month "
            "positions:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    ordered_df["season_month_order"] = (
        ordered_df[
            "season_month_order"
        ].astype(int)
    )

    return ordered_df


def validate_monthly_share_totals(
    monthly_summary: pd.DataFrame,
    tolerance: float = SHARE_SUM_TOLERANCE,
) -> None:
    """
    Validate that monthly crushing shares sum to one
    within each crop season.
    """

    if tolerance < 0:
        raise ValueError(
            "Share-sum tolerance cannot be negative."
        )

    season_share_totals = (
        monthly_summary
        .groupby(
            "season"
        )["monthly_share_of_season"]
        .sum()
    )

    invalid_season_totals = (
        season_share_totals.loc[
            (
                season_share_totals
                - 1.0
            ).abs() > tolerance
        ]
    )

    if not invalid_season_totals.empty:
        raise ValueError(
            "Monthly crushing shares do not sum to one "
            "for the following seasons:\n"
            f"{invalid_season_totals.to_string()}"
        )


def build_monthly_harvest_summary(
    harvest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate monthly crushing and monthly shares
    of total crop-season crushing.

    The starting April and ending April are retained
    as separate season-relative periods.
    """

    sao_paulo_df = filter_sao_paulo(
        harvest_df
    )

    sao_paulo_df = (
        assign_season_month_order(
            sao_paulo_df
        )
    )

    monthly_summary = (
        sao_paulo_df
        .groupby(
            [
                "season",
                "season_start_year",
                "season_month_order",
                "calendar_year",
                "month",
            ],
            as_index=False,
        )
        .agg(
            monthly_crush_tonnes=(
                "crush_tonnes",
                "sum",
            ),
            report_count=(
                "period_end_date",
                "count",
            ),
        )
    )

    season_totals = (
        monthly_summary
        .groupby(
            "season"
        )["monthly_crush_tonnes"]
        .transform("sum")
    )

    invalid_season_totals = (
        season_totals <= 0
    )

    if invalid_season_totals.any():
        invalid_seasons = (
            monthly_summary.loc[
                invalid_season_totals,
                "season",
            ]
            .unique()
        )

        raise ValueError(
            "Season crushing totals must be positive. "
            "Invalid seasons: "
            f"{sorted(invalid_seasons)}"
        )

    monthly_summary[
        "monthly_share_of_season"
    ] = (
        monthly_summary[
            "monthly_crush_tonnes"
        ]
        / season_totals
    )

    monthly_summary = (
        monthly_summary
        .sort_values(
            [
                "season_start_year",
                "season_month_order",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    validate_monthly_share_totals(
        monthly_summary
    )

    return monthly_summary

def save_harvest_metrics(
    harvest_metrics_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Save season-level harvest timing metrics.
    """

    if harvest_metrics_df.empty:
        raise ValueError(
            "Harvest metrics dataframe is empty."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    harvest_metrics_df.to_csv(
        output_path,
        index=False,
    )

    print(
        "\nHarvest metrics saved to:"
    )

    print(
        output_path
    )

def save_harvest_intelligence_outputs(
    cumulative_crush_df: pd.DataFrame,
    comparable_snapshot_df: pd.DataFrame,
    harvest_ranking_df: pd.DataFrame,
    cumulative_output_path: Path,
    snapshot_output_path: Path,
    ranking_output_path: Path,
) -> None:
    """
    Save processed historical harvest intelligence datasets.
    """

    output_dataframes = {
        cumulative_output_path: cumulative_crush_df,
        snapshot_output_path: comparable_snapshot_df,
        ranking_output_path: harvest_ranking_df,
    }

    for output_path, output_df in output_dataframes.items():
        if output_df.empty:
            raise ValueError(
                "Harvest intelligence output dataframe "
                f"for {output_path.name!r} is empty."
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_df.to_csv(
            output_path,
            index=False,
        )

        print(
            "\nHarvest intelligence dataset saved to:"
        )

        print(
            output_path
        )


def main() -> None:
    """
    Run the historical harvest calendar analysis.
    """

    harvest_df = load_unica_history(
        INPUT_PATH
    )

    cumulative_crush_df = (
        build_cumulative_crush_history(
            harvest_df=harvest_df,
            region="sao_paulo",
        )
    )

    comparable_snapshot_df = (
        build_comparable_crush_snapshot(
            cumulative_df=cumulative_crush_df,
            current_season=CURRENT_SEASON,
            max_day_difference=MAX_DAY_DIFFERENCE,
        )
    )

    harvest_ranking_df = (
        rank_cumulative_crush(
            snapshot_df=comparable_snapshot_df,
            current_season=CURRENT_SEASON,
        )
    )

    harvest_ranking_summary = (
        build_harvest_ranking_summary(
            ranking_df=harvest_ranking_df,
            current_season=CURRENT_SEASON,
        )
    )

    percentile_band_df = (
        build_percentile_band_dashboard_dataset(
            cumulative_df=cumulative_crush_df,
            current_season=CURRENT_SEASON,
        )
    )

    season_summary = (
        build_season_coverage_summary(
            harvest_df
        )
    )

    monthly_summary = (
        build_monthly_harvest_summary(
            harvest_df
        )
    )

    complete_monthly_summary = (
        filter_complete_seasons(
            monthly_summary
        )
    )

    harvest_metrics_df = (
        build_harvest_metrics(
            complete_monthly_summary,
            start_threshold=START_THRESHOLD,
            end_threshold=END_THRESHOLD,
        )
    )

    print(
        "\nComparable cumulative crush snapshot:\n"
    )

    print(
        comparable_snapshot_df.to_string(
            index=False
        )
    )

    print(
        "\nCumulative crushing pace ranking:\n"
    )

    print(
        harvest_ranking_df.to_string(
            index=False
        )
    )

    print(
        "\nHarvest ranking summary:\n"
    )

    print(
        harvest_ranking_summary
    )

    print(
        "\nHistorical percentile bands:\n"
    )

    print(
        percentile_band_df.to_string(
            index=False
        )
    )

    print(
        "\nSeason coverage summary:\n"
    )

    print(
        season_summary.to_string(
            index=False
        )
    )

    print(
        "\nMonthly harvest summary:\n"
    )

    print(
        monthly_summary.to_string(
            index=False
        )
    )

    print(
        "\nHarvest metrics:\n"
    )

    print(
        harvest_metrics_df.to_string(
            index=False
        )
    )

    heatmap_df = save_harvest_heatmap(
        monthly_summary
    )

    print(
        "\nHarvest heatmap dataframe:\n"
    )

    print(
        heatmap_df.to_string()
    )

    save_harvest_metrics(
        harvest_metrics_df=harvest_metrics_df,
        output_path=HARVEST_METRICS_OUTPUT_PATH,
    )

    save_harvest_intelligence_outputs(
        cumulative_crush_df=cumulative_crush_df,
        comparable_snapshot_df=comparable_snapshot_df,
        harvest_ranking_df=harvest_ranking_df,
        cumulative_output_path=(
            CUMULATIVE_CRUSH_HISTORY_OUTPUT_PATH
        ),
        snapshot_output_path=(
            COMPARABLE_CRUSH_SNAPSHOT_OUTPUT_PATH
        ),
        ranking_output_path=(
            CUMULATIVE_CRUSH_RANKING_OUTPUT_PATH
        ),
    )

    HISTORICAL_PERCENTILE_BANDS_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    percentile_band_df.to_csv(
        HISTORICAL_PERCENTILE_BANDS_OUTPUT_PATH,
        index=False,
    )

    print(
        "\nHistorical percentile-band dataset saved to:"
    )

    print(
        HISTORICAL_PERCENTILE_BANDS_OUTPUT_PATH
    )


if __name__ == "__main__":
    main()