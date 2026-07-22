"""
Operation Sugar Dashboard

Create a static single-season dashboard from the processed
weather-harvest dataset.
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
    / "dashboard_v1.png"
)

REQUIRED_COLUMNS = [
    "state",
    "harvest_season",
    "growing_season_start",
    "growing_season_end",
    "latest_report_date",
    "municipality_count",
    "has_complete_growing_season",
    "total_growing_season_rainfall",
    "average_growing_season_temperature",
    "average_growing_season_humidity",
    "total_growing_season_rainy_days",
    "total_growing_season_dry_days",
    "average_max_consecutive_dry_days",
    "maximum_consecutive_dry_days",
    "cumulative_crush_tonnes",
    "weather_source",
    "harvest_source",
]


def load_dashboard_data(
    input_path: Path,
) -> pd.DataFrame:
    """Load and validate the dashboard dataset."""

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

    dashboard_df[
        "growing_season_start"
    ] = pd.to_datetime(
        dashboard_df["growing_season_start"],
        errors="raise",
    )

    dashboard_df[
        "growing_season_end"
    ] = pd.to_datetime(
        dashboard_df["growing_season_end"],
        errors="raise",
    )

    dashboard_df[
        "latest_report_date"
    ] = pd.to_datetime(
        dashboard_df["latest_report_date"],
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

    return dashboard_df


def format_metric(
    value: float,
    unit: str,
    decimals: int = 1,
) -> str:
    """Format one dashboard metric."""

    return (
        f"{value:,.{decimals}f} "
        f"{unit}"
    )


def build_dashboard(
    dashboard_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Build and save a single-season dashboard."""

    latest_row = (
        dashboard_df
        .iloc[-1]
    )

    season = latest_row[
        "harvest_season"
    ]

    state = latest_row[
        "state"
    ]

    growing_season_start = (
        latest_row[
            "growing_season_start"
        ]
        .strftime("%Y-%m-%d")
    )

    growing_season_end = (
        latest_row[
            "growing_season_end"
        ]
        .strftime("%Y-%m-%d")
    )

    latest_report_date = (
        latest_row[
            "latest_report_date"
        ]
        .strftime("%Y-%m-%d")
    )

    cumulative_crush_mt = (
        latest_row[
            "cumulative_crush_tonnes"
        ]
        / 1_000_000
    )

    metrics = [
        (
            "Growing-season rainfall",
            format_metric(
                latest_row[
                    "total_growing_season_rainfall"
                ],
                "mm",
                0,
            ),
        ),
        (
            "Average temperature",
            format_metric(
                latest_row[
                    "average_growing_season_temperature"
                ],
                "°C",
                1,
            ),
        ),
        (
            "Average humidity",
            format_metric(
                latest_row[
                    "average_growing_season_humidity"
                ],
                "%",
                1,
            ),
        ),
        (
            "Rainy days",
            format_metric(
                latest_row[
                    "total_growing_season_rainy_days"
                ],
                "days",
                1,
            ),
        ),
        (
            "Dry days",
            format_metric(
                latest_row[
                    "total_growing_season_dry_days"
                ],
                "days",
                1,
            ),
        ),
        (
            "Average maximum CDD",
            format_metric(
                latest_row[
                    "average_max_consecutive_dry_days"
                ],
                "days",
                1,
            ),
        ),
        (
            "Maximum CDD",
            format_metric(
                latest_row[
                    "maximum_consecutive_dry_days"
                ],
                "days",
                0,
            ),
        ),
        (
            "Cumulative crush",
            format_metric(
                cumulative_crush_mt,
                "Mt",
                2,
            ),
        ),
    ]

    figure = plt.figure(
        figsize=(14, 8)
    )

    figure.suptitle(
        "Operation Sugar Dashboard",
        fontsize=22,
        weight="bold",
        y=0.96,
    )

    figure.text(
        0.5,
        0.895,
        (
            f"São Paulo ({state}) | "
            f"Harvest Season {season}"
        ),
        ha="center",
        fontsize=15,
        weight="bold",
    )

    figure.text(
        0.5,
        0.855,
        (
            f"Growing season: "
            f"{growing_season_start} to "
            f"{growing_season_end}"
        ),
        ha="center",
        fontsize=11,
    )

    left_margin = 0.08
    right_column = 0.58

    top_y = 0.76
    row_spacing = 0.115

    for index, (
        metric_name,
        metric_value,
    ) in enumerate(metrics):
        column = (
            left_margin
            if index < 4
            else right_column
        )

        row_index = (
            index
            if index < 4
            else index - 4
        )

        y_position = (
            top_y
            - row_index * row_spacing
        )

        figure.text(
            column,
            y_position,
            metric_name,
            fontsize=11,
        )

        figure.text(
            column,
            y_position - 0.045,
            metric_value,
            fontsize=20,
            weight="bold",
        )

    status_text = (
        "Complete growing season"
        if bool(
            latest_row[
                "has_complete_growing_season"
            ]
        )
        else "Incomplete growing season"
    )

    figure.text(
        0.08,
        0.19,
        "Coverage",
        fontsize=11,
    )

    figure.text(
        0.08,
        0.145,
        (
            f"{int(latest_row['municipality_count'])} "
            f"municipalities | "
            f"{status_text}"
        ),
        fontsize=14,
        weight="bold",
    )

    figure.text(
        0.58,
        0.19,
        "Latest harvest report",
        fontsize=11,
    )

    figure.text(
        0.58,
        0.145,
        latest_report_date,
        fontsize=14,
        weight="bold",
    )

    figure.text(
        0.5,
        0.055,
        (
            f"Weather source: "
            f"{latest_row['weather_source']} | "
            f"Harvest source: "
            f"{latest_row['harvest_source']}"
        ),
        ha="center",
        fontsize=10,
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
        f"Dashboard saved successfully: "
        f"{output_path}"
    )


def main() -> None:
    """Run the dashboard visualization pipeline."""

    dashboard_df = load_dashboard_data(
        INPUT_PATH
    )

    build_dashboard(
        dashboard_df=dashboard_df,
        output_path=OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()