"""
Operation Sugar Multi-Season Historical Benchmark Dashboard.

Create a static dashboard comparing complete historical
São Paulo growing seasons and matched-cutoff UNICA harvest progress.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dashboard"
    / "weather_harvest_dataset.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "dashboard_season_comparison.png"
)

REQUIRED_COLUMNS = [
    "state",
    "harvest_season",
    "growing_season_start",
    "growing_season_end",
    "latest_report_date",
    "matched_cutoff_date",
    "has_complete_growing_season",
    "total_growing_season_rainfall",
    "average_growing_season_temperature",
    "average_growing_season_humidity",
    "total_growing_season_rainy_days",
    "total_growing_season_dry_days",
    "average_max_consecutive_dry_days",
    "maximum_consecutive_dry_days",
    "cumulative_crush_tonnes",
]

TABLE_COLUMNS = [
    {
        "label": "Season",
        "column": "harvest_season",
    },
    {
        "label": "Rainfall\n(mm)",
        "column": "total_growing_season_rainfall",
        "decimals": 0,
        "scale": 1.0,
    },
    {
        "label": "Avg temp\n(°C)",
        "column": "average_growing_season_temperature",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Rainy days",
        "column": "total_growing_season_rainy_days",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Dry days",
        "column": "total_growing_season_dry_days",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Avg max\nCDD",
        "column": "average_max_consecutive_dry_days",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Crush\n(Mt)",
        "column": "cumulative_crush_tonnes",
        "decimals": 2,
        "scale": 1_000_000.0,
    },
]

TREND_METRICS = [
    {
        "title": "Growing-Season Rainfall",
        "column": "total_growing_season_rainfall",
        "unit": "mm",
        "scale": 1.0,
    },
    {
        "title": "Average Temperature",
        "column": "average_growing_season_temperature",
        "unit": "°C",
        "scale": 1.0,
    },
    {
        "title": "Average Maximum CDD",
        "column": "average_max_consecutive_dry_days",
        "unit": "days",
        "scale": 1.0,
    },
    {
        "title": "Matched-Cutoff Crush",
        "column": "cumulative_crush_tonnes",
        "unit": "Mt",
        "scale": 1_000_000.0,
    },
]

CURRENT_SEASON_COLOR = "#E8F5E9"
CURRENT_MARKER_COLOR = "#2E7D32"

TOP_RANK_COLOR = "#2E7D32"
MIDDLE_RANK_COLOR = "#616161"
BOTTOM_RANK_COLOR = "#C62828"


def extract_season_start_year(
    season: str,
) -> int:
    """Extract the four-digit starting year from a season label."""

    season_start = int(
        str(season).split("-")[0]
    )

    return 2000 + season_start


def load_comparison_data(
    input_path: Path,
) -> pd.DataFrame:
    """
    Load and validate complete historical weather-harvest seasons.

    Incomplete growing seasons are excluded from the benchmark.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            f"Dashboard dataset not found: {input_path}"
        )

    dashboard_df = pd.read_csv(
        input_path
    )

    if dashboard_df.empty:
        raise ValueError(
            "Dashboard dataset is empty."
        )

    missing_columns = (
        set(REQUIRED_COLUMNS)
        - set(dashboard_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Dashboard dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    date_columns = [
        "growing_season_start",
        "growing_season_end",
        "latest_report_date",
        "matched_cutoff_date",
    ]

    for column in date_columns:
        dashboard_df[column] = pd.to_datetime(
            dashboard_df[column],
            errors="raise",
        )

    dashboard_df[
        "has_complete_growing_season"
    ] = (
        dashboard_df[
            "has_complete_growing_season"
        ]
        .astype(str)
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
            }
        )
    )

    if dashboard_df[
        "has_complete_growing_season"
    ].isna().any():
        raise ValueError(
            "has_complete_growing_season contains "
            "invalid boolean values."
        )

    comparison_df = dashboard_df.loc[
        dashboard_df[
            "has_complete_growing_season"
        ]
    ].copy()

    if comparison_df.empty:
        raise ValueError(
            "No complete growing seasons are available "
            "for historical benchmarking."
        )

    comparison_df[
        "season_start_year"
    ] = (
        comparison_df[
            "harvest_season"
        ]
        .apply(
            extract_season_start_year
        )
    )

    comparison_df = (
        comparison_df
        .sort_values(
            [
                "state",
                "season_start_year",
            ]
        )
        .reset_index(drop=True)
    )

    duplicate_seasons = comparison_df.duplicated(
        subset=[
            "state",
            "harvest_season",
        ],
        keep=False,
    )

    if duplicate_seasons.any():
        raise ValueError(
            "Historical benchmark contains duplicate "
            "state-season records."
        )

    if len(comparison_df) < 3:
        raise ValueError(
            "At least three complete seasons are required "
            "for a historical benchmark dashboard. "
            f"Current complete season count: {len(comparison_df)}."
        )

    return comparison_df


def format_table_value(
    value: float,
    decimals: int,
    scale: float,
) -> str:
    """Format one numeric value for the historical table."""

    scaled_value = (
        float(value)
        / scale
    )

    return f"{scaled_value:,.{decimals}f}"


def build_table_data(
    comparison_df: pd.DataFrame,
) -> list[list[str]]:
    """Build formatted rows for the multi-season table."""

    table_rows: list[list[str]] = []

    for _, row in comparison_df.iterrows():
        formatted_row: list[str] = []

        for table_column in TABLE_COLUMNS:
            column_name = table_column[
                "column"
            ]

            if column_name == "harvest_season":
                formatted_row.append(
                    str(row[column_name])
                )
                continue

            formatted_row.append(
                format_table_value(
                    value=row[column_name],
                    decimals=table_column[
                        "decimals"
                    ],
                    scale=table_column[
                        "scale"
                    ],
                )
            )

        table_rows.append(
            formatted_row
        )

    return table_rows


def calculate_descending_rank(
    comparison_df: pd.DataFrame,
    column: str,
) -> tuple[int, int]:
    """
    Calculate the current season's descending rank.

    Rank 1 represents the highest historical value.
    """

    if comparison_df[column].isna().any():
        raise ValueError(
            f"Cannot rank metric with missing values: {column}"
        )

    ranked_values = (
        comparison_df[column]
        .astype(float)
        .rank(
            method="min",
            ascending=False,
        )
    )

    current_rank = int(
        ranked_values.iloc[-1]
    )

    total_seasons = len(
        comparison_df
    )

    return (
        current_rank,
        total_seasons,
    )


def ordinal_suffix(
    rank: int,
) -> str:
    """Format an integer as an ordinal ranking."""

    if 10 <= rank % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(
            rank % 10,
            "th",
        )

    return f"{rank}{suffix}"


def get_rank_color(
    rank: int,
    total_seasons: int,
) -> str:
    """
    Return a display color based on historical rank.

    Top two observations are highlighted in green,
    bottom two in red, and middle ranks in neutral gray.
    """

    if rank <= 2:
        return TOP_RANK_COLOR

    if rank >= total_seasons - 1:
        return BOTTOM_RANK_COLOR

    return MIDDLE_RANK_COLOR


def draw_historical_table(
    axis: plt.Axes,
    comparison_df: pd.DataFrame,
) -> None:
    """Draw the multi-season historical metric table."""

    axis.axis(
        "off"
    )

    table_data = build_table_data(
        comparison_df
    )

    column_labels = [
        column["label"]
        for column in TABLE_COLUMNS
    ]

    table = axis.table(
        cellText=table_data,
        colLabels=column_labels,
        cellLoc="center",
        colLoc="center",
        bbox=[
            0.0,
            0.0,
            1.0,
            1.0,
        ],
    )

    table.auto_set_font_size(
        False
    )

    table.set_fontsize(
        9
    )

    table.scale(
        1.0,
        1.45,
    )

    current_row_index = len(
        comparison_df
    )

    for (
        row_index,
        column_index,
    ), cell in table.get_celld().items():
        cell.set_linewidth(
            0.5
        )

        if row_index == 0:
            cell.set_text_props(
                weight="bold"
            )

        if row_index == current_row_index:
            cell.set_facecolor(
                CURRENT_SEASON_COLOR
            )

            cell.set_text_props(
                weight="bold",
            )

    axis.set_title(
        "Historical Benchmark Table",
        fontsize=13,
        weight="bold",
        pad=12,
    )


def draw_current_season_ranking(
    axis: plt.Axes,
    comparison_df: pd.DataFrame,
) -> None:
    """Draw current-season rankings against complete history."""

    axis.axis(
        "off"
    )

    current_row = comparison_df.iloc[-1]

    current_season = current_row[
        "harvest_season"
    ]

    ranking_metrics = [
        (
            "Rainfall",
            "total_growing_season_rainfall",
        ),
        (
            "Average temperature",
            "average_growing_season_temperature",
        ),
        (
            "Average maximum CDD",
            "average_max_consecutive_dry_days",
        ),
        (
            "Matched-cutoff crush",
            "cumulative_crush_tonnes",
        ),
    ]

    axis.text(
        0.0,
        0.97,
        "Current-Season Ranking",
        fontsize=13,
        weight="bold",
        va="top",
    )

    axis.text(
        0.0,
        0.88,
        (
            f"{current_season} versus "
            f"{len(comparison_df) - 1} prior seasons"
        ),
        fontsize=10,
        va="top",
    )

    starting_y = 0.72
    spacing = 0.16

    for index, (
        label,
        column,
    ) in enumerate(
        ranking_metrics
    ):
        rank, total_seasons = (
            calculate_descending_rank(
                comparison_df,
                column,
            )
        )

        y_position = (
            starting_y
            - index * spacing
        )

        rank_color = get_rank_color(
            rank=rank,
            total_seasons=total_seasons,
        )

        axis.text(
            0.0,
            y_position,
            label,
            fontsize=10,
            weight="bold",
            va="top",
        )

        axis.text(
            0.0,
            y_position - 0.065,
            (
                f"{ordinal_suffix(rank)} "
                f"of {total_seasons} "
                "(high to low)"
            ),
            fontsize=10,
            weight="bold",
            color=rank_color,
            va="top",
        )

    matched_cutoff = (
        current_row[
            "matched_cutoff_date"
        ]
        .strftime("%B %d")
    )

    axis.text(
        0.0,
        0.02,
        (
            "Harvest comparison cutoff:\n"
            f"{matched_cutoff} in every season"
        ),
        fontsize=9,
        va="bottom",
    )


def draw_trend_chart(
    axis: plt.Axes,
    comparison_df: pd.DataFrame,
    metric: dict,
) -> None:
    """Draw one historical trend chart."""

    seasons = (
        comparison_df[
            "harvest_season"
        ]
        .astype(str)
        .tolist()
    )

    values = (
        comparison_df[
            metric["column"]
        ]
        .astype(float)
        / metric["scale"]
    )

    axis.plot(
        seasons,
        values,
        marker="o",
        linewidth=1.8,
    )

    axis.scatter(
        seasons[-1],
        values.iloc[-1],
        s=110,
        color=CURRENT_MARKER_COLOR,
        edgecolor="white",
        linewidth=1.2,
        zorder=4,
    )

    axis.set_title(
        metric["title"],
        fontsize=11,
        weight="bold",
    )

    axis.set_ylabel(
        metric["unit"],
        fontsize=9,
    )

    axis.tick_params(
        axis="x",
        labelrotation=45,
        labelsize=8,
    )

    axis.tick_params(
        axis="y",
        labelsize=8,
    )

    axis.grid(
        axis="y",
        alpha=0.25,
    )

    axis.annotate(
        f"{values.iloc[-1]:,.1f}",
        xy=(
            seasons[-1],
            values.iloc[-1],
        ),
        xytext=(
            6,
            7,
        ),
        textcoords="offset points",
        fontsize=8,
        weight="bold",
        color=CURRENT_MARKER_COLOR,
    )


def build_comparison_dashboard(
    dashboard_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Build and save the multi-season historical dashboard."""

    comparison_df = dashboard_df.copy()

    current_row = comparison_df.iloc[-1]

    current_season = current_row[
        "harvest_season"
    ]

    first_season = comparison_df.iloc[0][
        "harvest_season"
    ]

    state = current_row[
        "state"
    ]

    matched_cutoff = (
        current_row[
            "matched_cutoff_date"
        ]
        .strftime("%B %d")
    )

    figure = plt.figure(
        figsize=(
            17,
            12,
        ),
        constrained_layout=True,
    )

    grid = figure.add_gridspec(
        nrows=3,
        ncols=4,
        height_ratios=[
            0.18,
            1.05,
            0.9,
        ],
    )

    title_axis = figure.add_subplot(
        grid[0, :]
    )

    table_axis = figure.add_subplot(
        grid[1, :3]
    )

    ranking_axis = figure.add_subplot(
        grid[1, 3]
    )

    trend_axes = [
        figure.add_subplot(
            grid[2, column_index]
        )
        for column_index in range(4)
    ]

    title_axis.axis(
        "off"
    )

    title_axis.text(
        0.5,
        0.82,
        "Operation Sugar Dashboard",
        ha="center",
        fontsize=24,
        weight="bold",
    )

    title_axis.text(
        0.5,
        0.48,
        (
            "São Paulo Multi-Season "
            "Historical Benchmark"
        ),
        ha="center",
        fontsize=17,
        weight="bold",
    )

    title_axis.text(
        0.5,
        0.14,
        (
            f"{first_season} through "
            f"{current_season} | "
            f"State: {state} | "
            f"Matched harvest cutoff: {matched_cutoff}"
        ),
        ha="center",
        fontsize=11,
    )

    draw_historical_table(
        axis=table_axis,
        comparison_df=comparison_df,
    )

    draw_current_season_ranking(
        axis=ranking_axis,
        comparison_df=comparison_df,
    )

    for axis, metric in zip(
        trend_axes,
        TREND_METRICS,
        strict=True,
    ):
        draw_trend_chart(
            axis=axis,
            comparison_df=comparison_df,
            metric=metric,
        )

    figure.text(
        0.5,
        0.008,
        (
            "Weather source: NASA POWER | "
            "Harvest source: UNICA | "
            "Weather aggregated over complete September-April "
            "growing seasons | "
            "Harvest totals normalized using a June 1 "
            "reporting cutoff across all seasons"
        ),
        ha="center",
        fontsize=8.5,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )

    print(
        "Multi-season historical benchmark dashboard "
        f"saved successfully: {output_path}"
    )


def main() -> None:
    """Run the multi-season comparison visualization pipeline."""

    dashboard_df = load_comparison_data(
        INPUT_PATH
    )

    build_comparison_dashboard(
        dashboard_df=dashboard_df,
        output_path=OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()