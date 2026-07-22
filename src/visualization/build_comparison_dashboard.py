"""
Operation Sugar Season Comparison Dashboard

Create a static comparison dashboard for the two most recent
matched weather-harvest seasons.
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
    "total_growing_season_rainfall",
    "average_growing_season_temperature",
    "average_growing_season_humidity",
    "total_growing_season_rainy_days",
    "total_growing_season_dry_days",
    "average_max_consecutive_dry_days",
    "maximum_consecutive_dry_days",
    "cumulative_crush_tonnes",
]


METRICS = [
    {
        "label": "Growing-season rainfall",
        "column": "total_growing_season_rainfall",
        "unit": "mm",
        "decimals": 0,
        "scale": 1.0,
    },
    {
        "label": "Average temperature",
        "column": "average_growing_season_temperature",
        "unit": "°C",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Average humidity",
        "column": "average_growing_season_humidity",
        "unit": "%",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Rainy days",
        "column": "total_growing_season_rainy_days",
        "unit": "days",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Dry days",
        "column": "total_growing_season_dry_days",
        "unit": "days",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Average maximum CDD",
        "column": "average_max_consecutive_dry_days",
        "unit": "days",
        "decimals": 1,
        "scale": 1.0,
    },
    {
        "label": "Maximum CDD",
        "column": "maximum_consecutive_dry_days",
        "unit": "days",
        "decimals": 0,
        "scale": 1.0,
    },
    {
        "label": "Cumulative crush",
        "column": "cumulative_crush_tonnes",
        "unit": "Mt",
        "decimals": 2,
        "scale": 1_000_000.0,
    },
]


def load_comparison_data(
    input_path: Path,
) -> pd.DataFrame:
    """Load and validate the weather-harvest dashboard dataset."""

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
    ]

    for column in date_columns:
        dashboard_df[column] = pd.to_datetime(
            dashboard_df[column],
            errors="raise",
        )

    dashboard_df = (
        dashboard_df
        .sort_values(
            [
                "state",
                "harvest_season",
            ]
        )
        .reset_index(drop=True)
    )

    if len(dashboard_df) < 2:
        raise ValueError(
            "At least two matched harvest seasons are required "
            "to build the season-comparison dashboard. "
            f"Current matched season count: {len(dashboard_df)}."
        )

    return dashboard_df


def format_value(
    value: float,
    unit: str,
    decimals: int,
) -> str:
    """Format one metric value."""

    return (
        f"{value:,.{decimals}f} "
        f"{unit}"
    )


def format_difference(
    difference: float,
    unit: str,
    decimals: int,
) -> str:
    """Format a signed season-to-season difference."""

    return (
        f"{difference:+,.{decimals}f} "
        f"{unit}"
    )


def format_percent_change(
    previous_value: float,
    current_value: float,
) -> str:
    """Calculate and format percentage change."""

    if previous_value == 0:
        return "N/A"

    percent_change = (
        (
            current_value
            - previous_value
        )
        / abs(previous_value)
        * 100
    )

    return f"{percent_change:+.1f}%"


def build_comparison_dashboard(
    dashboard_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Build and save the two-season comparison dashboard."""

    comparison_df = (
        dashboard_df
        .tail(2)
        .copy()
        .reset_index(drop=True)
    )

    previous_row = comparison_df.iloc[0]
    current_row = comparison_df.iloc[1]

    previous_season = previous_row[
        "harvest_season"
    ]

    current_season = current_row[
        "harvest_season"
    ]

    state = current_row[
        "state"
    ]

    figure = plt.figure(
        figsize=(15, 10)
    )

    figure.suptitle(
        "Operation Sugar Dashboard",
        fontsize=23,
        weight="bold",
        y=0.965,
    )

    figure.text(
        0.5,
        0.915,
        (
            "São Paulo Growing-Season "
            "and Harvest Comparison"
        ),
        ha="center",
        fontsize=16,
        weight="bold",
    )

    figure.text(
        0.5,
        0.875,
        (
            f"{previous_season} vs {current_season} "
            f"| State: {state}"
        ),
        ha="center",
        fontsize=12,
    )

    column_positions = {
        "metric": 0.07,
        "previous": 0.43,
        "current": 0.62,
        "difference": 0.80,
        "percent": 0.93,
    }

    header_y = 0.81

    figure.text(
        column_positions["metric"],
        header_y,
        "Metric",
        fontsize=12,
        weight="bold",
    )

    figure.text(
        column_positions["previous"],
        header_y,
        previous_season,
        fontsize=12,
        weight="bold",
        ha="right",
    )

    figure.text(
        column_positions["current"],
        header_y,
        current_season,
        fontsize=12,
        weight="bold",
        ha="right",
    )

    figure.text(
        column_positions["difference"],
        header_y,
        "Difference",
        fontsize=12,
        weight="bold",
        ha="right",
    )

    figure.text(
        column_positions["percent"],
        header_y,
        "% change",
        fontsize=12,
        weight="bold",
        ha="right",
    )

    line = plt.Line2D(
        [
            0.06,
            0.94,
        ],
        [
            0.79,
            0.79,
        ],
        transform=figure.transFigure,
        linewidth=1,
    )

    figure.add_artist(
        line
    )

    first_row_y = 0.745
    row_spacing = 0.075

    for index, metric in enumerate(METRICS):
        y_position = (
            first_row_y
            - index * row_spacing
        )

        previous_raw = float(
            previous_row[
                metric["column"]
            ]
        )

        current_raw = float(
            current_row[
                metric["column"]
            ]
        )

        previous_value = (
            previous_raw
            / metric["scale"]
        )

        current_value = (
            current_raw
            / metric["scale"]
        )

        difference = (
            current_value
            - previous_value
        )

        figure.text(
            column_positions["metric"],
            y_position,
            metric["label"],
            fontsize=11,
        )

        figure.text(
            column_positions["previous"],
            y_position,
            format_value(
                previous_value,
                metric["unit"],
                metric["decimals"],
            ),
            fontsize=11,
            ha="right",
        )

        figure.text(
            column_positions["current"],
            y_position,
            format_value(
                current_value,
                metric["unit"],
                metric["decimals"],
            ),
            fontsize=11,
            ha="right",
            weight="bold",
        )

        figure.text(
            column_positions["difference"],
            y_position,
            format_difference(
                difference,
                metric["unit"],
                metric["decimals"],
            ),
            fontsize=11,
            ha="right",
        )

        figure.text(
            column_positions["percent"],
            y_position,
            format_percent_change(
                previous_value,
                current_value,
            ),
            fontsize=11,
            ha="right",
        )

        if index < len(METRICS) - 1:
            separator_y = (
                y_position
                - row_spacing / 2
            )

            separator = plt.Line2D(
                [
                    0.06,
                    0.94,
                ],
                [
                    separator_y,
                    separator_y,
                ],
                transform=figure.transFigure,
                linewidth=0.4,
                alpha=0.35,
            )

            figure.add_artist(
                separator
            )

    previous_growing_period = (
        f"{previous_row['growing_season_start']:%Y-%m-%d}"
        f" to "
        f"{previous_row['growing_season_end']:%Y-%m-%d}"
    )

    current_growing_period = (
        f"{current_row['growing_season_start']:%Y-%m-%d}"
        f" to "
        f"{current_row['growing_season_end']:%Y-%m-%d}"
    )

    previous_report_date = (
        previous_row[
            "latest_report_date"
        ]
        .strftime("%Y-%m-%d")
    )

    current_report_date = (
        current_row[
            "latest_report_date"
        ]
        .strftime("%Y-%m-%d")
    )

    figure.text(
        0.07,
        0.095,
        (
            f"{previous_season} growing season: "
            f"{previous_growing_period}\n"
            f"Latest matched UNICA report: "
            f"{previous_report_date}"
        ),
        fontsize=9,
        va="bottom",
    )

    figure.text(
        0.57,
        0.095,
        (
            f"{current_season} growing season: "
            f"{current_growing_period}\n"
            f"Latest matched UNICA report: "
            f"{current_report_date}"
        ),
        fontsize=9,
        va="bottom",
    )

    figure.text(
        0.5,
        0.035,
        (
            "Weather source: NASA POWER | "
            "Harvest source: UNICA | "
            "Difference = current season minus previous season"
        ),
        ha="center",
        fontsize=9,
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
        "Season comparison dashboard saved successfully: "
        f"{output_path}"
    )


def main() -> None:
    """Run the season-comparison visualization pipeline."""

    dashboard_df = load_comparison_data(
        INPUT_PATH
    )

    build_comparison_dashboard(
        dashboard_df=dashboard_df,
        output_path=OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()