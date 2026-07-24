"""
Historical Harvest Percentile-Band Visualization

Visualize the current São Paulo cumulative crushing season
against historical percentile ranges at standardized
biweekly reporting periods.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


MILLION_TONNES = 1_000_000

REQUIRED_COLUMNS = {
    "current_season",
    "report_period_order",
    "report_period_label",
    "historical_season_count",
    "percentile_05_crush_tonnes",
    "percentile_25_crush_tonnes",
    "median_crush_tonnes",
    "percentile_75_crush_tonnes",
    "percentile_95_crush_tonnes",
    "current_cumulative_crush_tonnes",
}


def validate_percentile_band_dataset(
    dashboard_df: pd.DataFrame,
) -> None:
    """
    Validate the dashboard-ready percentile-band dataset.
    """

    if dashboard_df.empty:
        raise ValueError(
            "Harvest percentile-band dataframe "
            "must not be empty."
        )

    missing_columns = (
        REQUIRED_COLUMNS
        - set(dashboard_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Harvest percentile-band dataframe is "
            "missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if (
        dashboard_df[
            "report_period_order"
        ].isna().any()
    ):
        raise ValueError(
            "Reporting-period order contains missing values."
        )

    if (
        dashboard_df[
            "report_period_order"
        ].duplicated().any()
    ):
        raise ValueError(
            "Reporting-period order must be unique."
        )

    historical_columns = [
        "percentile_05_crush_tonnes",
        "percentile_25_crush_tonnes",
        "median_crush_tonnes",
        "percentile_75_crush_tonnes",
        "percentile_95_crush_tonnes",
    ]

    if (
        dashboard_df[
            historical_columns
        ].isna().any().any()
    ):
        raise ValueError(
            "Historical percentile columns contain "
            "missing values."
        )

    if (
        dashboard_df[
            historical_columns
        ] < 0
    ).any().any():
        raise ValueError(
            "Historical percentile values cannot "
            "be negative."
        )

    invalid_percentile_order = (
        (
            dashboard_df[
                "percentile_05_crush_tonnes"
            ]
            > dashboard_df[
                "percentile_25_crush_tonnes"
            ]
        )
        | (
            dashboard_df[
                "percentile_25_crush_tonnes"
            ]
            > dashboard_df[
                "median_crush_tonnes"
            ]
        )
        | (
            dashboard_df[
                "median_crush_tonnes"
            ]
            > dashboard_df[
                "percentile_75_crush_tonnes"
            ]
        )
        | (
            dashboard_df[
                "percentile_75_crush_tonnes"
            ]
            > dashboard_df[
                "percentile_95_crush_tonnes"
            ]
        )
    )

    if invalid_percentile_order.any():
        raise ValueError(
            "Historical percentile boundaries are "
            "not monotonically ordered."
        )

    current_seasons = (
        dashboard_df[
            "current_season"
        ]
        .dropna()
        .unique()
    )

    if len(current_seasons) != 1:
        raise ValueError(
            "Percentile-band dataset must contain "
            "exactly one current season."
        )


def prepare_percentile_band_plot_data(
    dashboard_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare cumulative crushing values for visualization.

    Crushing volumes are converted from tonnes to
    million tonnes.
    """

    validate_percentile_band_dataset(
        dashboard_df
    )

    plot_df = (
        dashboard_df
        .sort_values(
            "report_period_order"
        )
        .reset_index(
            drop=True
        )
        .copy()
    )

    tonnage_columns = [
        "percentile_05_crush_tonnes",
        "percentile_25_crush_tonnes",
        "median_crush_tonnes",
        "percentile_75_crush_tonnes",
        "percentile_95_crush_tonnes",
        "current_cumulative_crush_tonnes",
    ]

    for column in tonnage_columns:
        plot_df[
            column.replace(
                "_tonnes",
                "_million_tonnes",
            )
        ] = (
            plot_df[column]
            / MILLION_TONNES
        )

    return plot_df


def save_harvest_percentile_bands(
    dashboard_df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    """
    Generate and save the historical harvest percentile-band
    visualization.

    The chart contains:

    - historical 5th–95th percentile range
    - historical 25th–75th percentile range
    - historical median
    - current-season cumulative crushing curve
    - latest current-season observation
    """

    plot_df = prepare_percentile_band_plot_data(
        dashboard_df
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    current_season = str(
        plot_df[
            "current_season"
        ].iloc[0]
    )

    historical_season_count = int(
        plot_df[
            "historical_season_count"
        ].max()
    )

    x_values = (
        plot_df[
            "report_period_order"
        ]
    )

    percentile_05 = (
        plot_df[
            "percentile_05_crush_million_tonnes"
        ]
    )

    percentile_25 = (
        plot_df[
            "percentile_25_crush_million_tonnes"
        ]
    )

    historical_median = (
        plot_df[
            "median_crush_million_tonnes"
        ]
    )

    percentile_75 = (
        plot_df[
            "percentile_75_crush_million_tonnes"
        ]
    )

    percentile_95 = (
        plot_df[
            "percentile_95_crush_million_tonnes"
        ]
    )

    current_curve = (
        plot_df[
            "current_cumulative_crush_million_tonnes"
        ]
    )

    figure, axis = plt.subplots(
        figsize=(12, 7)
    )

    axis.fill_between(
        x_values,
        percentile_05,
        percentile_95,
        alpha=0.15,
        label="Historical 5th–95th percentile",
    )

    axis.fill_between(
        x_values,
        percentile_25,
        percentile_75,
        alpha=0.30,
        label="Historical 25th–75th percentile",
    )

    axis.plot(
        x_values,
        historical_median,
        linewidth=2,
        linestyle="--",
        label="Historical median",
    )

    axis.plot(
        x_values,
        current_curve,
        linewidth=2.5,
        marker="o",
        markersize=5,
        label=f"Current season {current_season}",
    )

    observed_current_df = plot_df.loc[
        plot_df[
            "current_cumulative_crush_million_tonnes"
        ].notna()
    ]

    if not observed_current_df.empty:
        latest_current_row = (
            observed_current_df.iloc[-1]
        )

        latest_x = int(
            latest_current_row[
                "report_period_order"
            ]
        )

        latest_y = float(
            latest_current_row[
                "current_cumulative_crush_million_tonnes"
            ]
        )

        latest_label = str(
            latest_current_row[
                "report_period_label"
            ]
        )

        axis.scatter(
            latest_x,
            latest_y,
            s=70,
            zorder=5,
        )

        axis.annotate(
            (
                f"{latest_y:.1f} Mt\n"
                f"{latest_label}"
            ),
            xy=(
                latest_x,
                latest_y,
            ),
            xytext=(
                10,
                12,
            ),
            textcoords="offset points",
            fontsize=9,
        )

    axis.set_title(
        "São Paulo Cumulative Sugarcane Crushing",
        fontsize=15,
        fontweight="bold",
        pad=14,
    )

    axis.set_xlabel(
        "Biweekly Reporting Period"
    )

    axis.set_ylabel(
        "Cumulative Crushing (Million Tonnes)"
    )

    axis.grid(
        axis="y",
        alpha=0.25,
    )

    axis.set_xlim(
        x_values.min(),
        x_values.max(),
    )

    tick_positions = (
        plot_df.loc[
            (
                plot_df[
                    "report_period_order"
                ]
                .sub(1)
                .mod(2)
                .eq(0)
            ),
            "report_period_order",
        ]
    )

    tick_labels = (
        plot_df.loc[
            plot_df[
                "report_period_order"
            ].isin(tick_positions),
            "report_period_label",
        ]
    )

    axis.set_xticks(
        tick_positions
    )

    axis.set_xticklabels(
        tick_labels,
        rotation=45,
        ha="right",
    )

    axis.legend(
        loc="upper left",
        frameon=False,
    )

    axis.text(
        0.99,
        0.02,
        (
            f"Historical benchmark: "
            f"{historical_season_count} seasons"
        ),
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
    )

    figure.tight_layout()

    figure.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )

    return plot_df