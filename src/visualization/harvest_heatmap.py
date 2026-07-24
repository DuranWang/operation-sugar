"""
Historical Harvest Calendar Heatmap

Analyze and visualize the monthly share of annual sugarcane
crushing for completed UNICA crop seasons in São Paulo.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "crushing"
    / "unica_biweekly_crush.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "figures"
    / "harvest_heatmap.png"
)

EXPECTED_REPORT_COUNT = 24

SEASON_MONTH_ORDER = list(
    range(1, 14)
)

SEASON_MONTH_LABELS = [
    "Apr\nStart",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
    "Jan",
    "Feb",
    "Mar",
    "Apr\nEnd",
]


def load_unica_history(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load the historical UNICA biweekly crushing dataset.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            "UNICA historical dataset was not found: "
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
            "UNICA dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if harvest_df.empty:
        raise ValueError(
            "UNICA historical dataset is empty."
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
    their four-digit starting year, such as 2025.
    """

    season_start_two_digit = (
        season
        .astype(str)
        .str.split("-")
        .str[0]
        .astype(int)
    )

    return (
        season_start_two_digit
        + 2000
    )


def assign_season_month_order(
    harvest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign a season-relative month position.

    The UNICA crop season contains two April reporting
    periods:

    - April at the beginning of the crop season
    - April at the end of the crop season

    These are assigned separate positions so that harvest
    onset and the season tail remain distinct.
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

    month_order_mapping = {
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

    ordered_df["season_month_order"] = (
        ordered_df["month"]
        .map(
            month_order_mapping
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

    if ordered_df[
        "season_month_order"
    ].isna().any():
        invalid_rows = ordered_df.loc[
            ordered_df[
                "season_month_order"
            ].isna(),
            [
                "season",
                "period_end_date",
                "calendar_year",
                "month",
            ],
        ]

        raise ValueError(
            "Unable to assign season-relative month "
            "positions to all observations:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    ordered_df["season_month_order"] = (
        ordered_df[
            "season_month_order"
        ].astype(int)
    )

    return ordered_df


def build_monthly_crushing_summary(
    harvest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate monthly crushing and monthly shares
    of total season crushing.

    Starting April and ending April are retained as
    separate season-relative periods.
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
        .transform(
            "sum"
        )
    )

    if (
        season_totals <= 0
    ).any():
        raise ValueError(
            "Season crushing totals must be positive."
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

    return monthly_summary


def validate_monthly_summary(
    monthly_summary: pd.DataFrame,
) -> None:
    """
    Validate the monthly summary before visualization.
    """

    required_columns = {
        "season",
        "season_start_year",
        "season_month_order",
        "report_count",
        "monthly_share_of_season",
    }

    missing_columns = (
        required_columns
        - set(monthly_summary.columns)
    )

    if missing_columns:
        raise ValueError(
            "Monthly summary is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if monthly_summary.empty:
        raise ValueError(
            "Monthly summary is empty."
        )

    invalid_month_positions = (
        monthly_summary.loc[
            ~monthly_summary[
                "season_month_order"
            ].isin(
                SEASON_MONTH_ORDER
            ),
            "season_month_order",
        ]
    )

    if not invalid_month_positions.empty:
        raise ValueError(
            "Monthly summary contains invalid "
            "season-relative month positions: "
            f"{sorted(invalid_month_positions.unique())}"
        )

    invalid_report_counts = (
        monthly_summary.loc[
            monthly_summary[
                "report_count"
            ] < 0,
            "report_count",
        ]
    )

    if not invalid_report_counts.empty:
        raise ValueError(
            "Monthly summary contains negative "
            "report counts."
        )

    invalid_monthly_shares = (
        monthly_summary.loc[
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
    )

    if not invalid_monthly_shares.empty:
        raise ValueError(
            "Monthly crushing shares must be "
            "between 0 and 1."
        )


def filter_complete_seasons(
    monthly_summary: pd.DataFrame,
    expected_report_count: int = EXPECTED_REPORT_COUNT,
) -> pd.DataFrame:
    """
    Keep only completed crop seasons.

    A completed historical UNICA season is expected
    to contain 24 biweekly reports.
    """

    if expected_report_count <= 0:
        raise ValueError(
            "Expected report count must be positive."
        )

    season_report_counts = (
        monthly_summary
        .groupby(
            "season"
        )["report_count"]
        .transform(
            "sum"
        )
    )

    complete_seasons_df = (
        monthly_summary.loc[
            season_report_counts
            == expected_report_count
        ]
        .copy()
    )

    if complete_seasons_df.empty:
        raise ValueError(
            "No complete crop seasons were found."
        )

    return complete_seasons_df


def validate_complete_season_shares(
    monthly_summary: pd.DataFrame,
    tolerance: float = 1e-9,
) -> None:
    """
    Validate that monthly shares sum to one within
    each completed crop season.
    """

    season_share_totals = (
        monthly_summary
        .groupby(
            "season"
        )["monthly_share_of_season"]
        .sum()
    )

    invalid_seasons = (
        season_share_totals.loc[
            (
                season_share_totals
                - 1.0
            ).abs() > tolerance
        ]
    )

    if not invalid_seasons.empty:
        raise ValueError(
            "Monthly shares do not sum to one for "
            "the following seasons:\n"
            f"{invalid_seasons.to_string()}"
        )


def prepare_heatmap_dataframe(
    monthly_summary: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert the monthly crushing summary into a
    season-by-period heatmap matrix.

    Rows represent completed UNICA crop seasons.

    Columns represent season-relative monthly periods
    from the starting April through the ending April.

    Cell values represent each period's share of total
    season crushing.
    """

    validate_monthly_summary(
        monthly_summary
    )

    complete_seasons_df = (
        filter_complete_seasons(
            monthly_summary
        )
    )

    validate_complete_season_shares(
        complete_seasons_df
    )

    season_order = (
        complete_seasons_df[
            [
                "season",
                "season_start_year",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "season_start_year"
        )["season"]
        .tolist()
    )

    heatmap_df = (
        complete_seasons_df
        .pivot(
            index="season",
            columns="season_month_order",
            values="monthly_share_of_season",
        )
        .reindex(
            index=season_order,
            columns=SEASON_MONTH_ORDER,
        )
        .fillna(0.0)
    )

    heatmap_df.columns = (
        SEASON_MONTH_LABELS
    )

    return heatmap_df


def plot_harvest_heatmap(
    heatmap_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Plot and save the historical harvest calendar heatmap.
    """

    if heatmap_df.empty:
        raise ValueError(
            "Heatmap dataframe is empty."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig, ax = plt.subplots(
        figsize=(12, 8)
    )

    image = ax.imshow(
        heatmap_df.to_numpy(),
        cmap="Blues",
        aspect="auto",
        vmin=0,
        vmax=heatmap_df.to_numpy().max(),
    )

    ax.set_xticks(
        range(
            len(
                heatmap_df.columns
            )
        )
    )

    ax.set_xticklabels(
        heatmap_df.columns
    )

    ax.set_yticks(
        range(
            len(
                heatmap_df.index
            )
        )
    )

    ax.set_yticklabels(
        heatmap_df.index
    )

    ax.set_xlabel(
        "Crop-Season Month"
    )

    ax.set_ylabel(
        "UNICA Crop Season"
    )

    ax.set_title(
        "São Paulo Sugarcane Crushing Distribution "
        "by Crop Season"
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
    )

    colorbar.set_label(
        "Share of Total Season Crushing"
    )

    colorbar.ax.yaxis.set_major_formatter(
        plt.FuncFormatter(
            lambda value, _: f"{value:.0%}"
        )
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


def save_harvest_heatmap(
    monthly_summary: pd.DataFrame,
    output_path: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    """
    Prepare and save the historical harvest heatmap.

    Return the season-by-period dataframe used to
    generate the visualization.
    """

    heatmap_df = (
        prepare_heatmap_dataframe(
            monthly_summary
        )
    )

    plot_harvest_heatmap(
        heatmap_df=heatmap_df,
        output_path=output_path,
    )

    return heatmap_df


def main() -> None:
    """
    Run the historical harvest calendar analysis.
    """

    harvest_df = load_unica_history(
        INPUT_PATH
    )

    season_summary = (
        build_season_coverage_summary(
            harvest_df
        )
    )

    monthly_summary = (
        build_monthly_crushing_summary(
            harvest_df
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
        "\nMonthly crushing summary:\n"
    )

    print(
        monthly_summary.to_string(
            index=False
        )
    )

    heatmap_df = (
        save_harvest_heatmap(
            monthly_summary
        )
    )

    print(
        "\nHarvest heatmap dataframe:\n"
    )

    print(
        heatmap_df.to_string()
    )


if __name__ == "__main__":
    main()