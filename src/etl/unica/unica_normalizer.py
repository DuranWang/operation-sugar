"""
Normalize extracted UNICA cumulative crushing tables.

This module converts reconstructed UNICA PDF table output
into a tidy season-region-date DataFrame.
"""

import re
from pathlib import Path

import pandas as pd

from src.etl.saver import save_dataframe_csv
from src.etl.unica.unica_table_extractor import (
    extract_historical_crushing_tables,
)
from src.etl.unica.unica_validator import (
    validate_historical_crushing_dataframe,
)


PERIOD_PATTERN = re.compile(
    r"^\d{2}/\d{2}$"
)

SEASON_PATTERN = re.compile(
    r"\d{4}/\d{4}"
)

REGION_COLUMNS = {
    1: "sao_paulo",
    2: "centre_south",
    3: "other_states",
}


def parse_brazilian_integer(
    value: str,
) -> int:
    """
    Convert a dot-separated Brazilian integer to int.

    Example
    -------
    '8.253.154' -> 8253154
    """

    normalized_value = (
        value
        .strip()
        .replace(".", "")
    )

    if not normalized_value.isdigit():
        raise ValueError(
            "Invalid Brazilian integer value: "
            f"{value!r}"
        )

    return int(
        normalized_value
    )


def parse_region_cell(
    cell: str,
) -> tuple[int, int, float]:
    """
    Parse previous-season value, current-season value,
    and percentage change from one regional cell.

    Example
    -------
    '8.253.154 11.007.246 33%'

    Returns
    -------
    tuple[int, int, float]
        Previous-season tonnes,
        current-season tonnes,
        variation percentage.
    """

    parts = cell.split()

    if len(parts) != 3:
        raise ValueError(
            "Expected three values in UNICA region cell: "
            f"{cell!r}"
        )

    previous_season_tonnes = (
        parse_brazilian_integer(
            parts[0]
        )
    )

    current_season_tonnes = (
        parse_brazilian_integer(
            parts[1]
        )
    )

    variation_percent = float(
        parts[2]
        .replace("%", "")
        .replace(",", ".")
    )

    return (
        previous_season_tonnes,
        current_season_tonnes,
        variation_percent,
    )


def extract_season_labels(
    season_header_row: list[str | None],
) -> tuple[str, str]:
    """
    Extract previous and current season labels from
    the reconstructed UNICA header row.
    """

    season_text = " ".join(
        cell
        for cell in season_header_row
        if cell is not None
    )

    seasons = SEASON_PATTERN.findall(
        season_text
    )

    unique_seasons = list(
        dict.fromkeys(
            seasons
        )
    )

    if len(unique_seasons) < 2:
        raise ValueError(
            "Could not identify two harvest seasons "
            "from the UNICA table header."
        )

    previous_season = normalize_harvest_season(
        unique_seasons[0]
    )

    current_season = normalize_harvest_season(
        unique_seasons[1]
    )

    return (
        previous_season,
        current_season,
    )


def normalize_harvest_season(
    season: str,
) -> str:
    """
    Normalize UNICA season labels into YY-YY format.

    Supported examples
    ------------------
    25-26      -> 25-26
    2025/2026  -> 25-26
    2025/26    -> 25-26
    """

    normalized_season = str(
        season
    ).strip()

    if "-" in normalized_season:
        season_parts = normalized_season.split(
            "-"
        )
    elif "/" in normalized_season:
        season_parts = normalized_season.split(
            "/"
        )
    else:
        raise ValueError(
            "Unsupported UNICA season format: "
            f"{season!r}"
        )

    if len(season_parts) != 2:
        raise ValueError(
            "UNICA season must contain exactly "
            f"two year components: {season!r}"
        )

    start_text, end_text = season_parts

    if len(start_text) == 2:
        start_year = int(
            f"20{start_text}"
        )
    elif len(start_text) == 4:
        start_year = int(
            start_text
        )
    else:
        raise ValueError(
            "Invalid UNICA season start year: "
            f"{season!r}"
        )

    if len(end_text) not in {
        2,
        4,
    }:
        raise ValueError(
            "Invalid UNICA season end year: "
            f"{season!r}"
        )

    expected_end_year = (
        start_year + 1
    )

    supplied_end_digits = (
        end_text[-2:]
    )

    expected_end_digits = str(
        expected_end_year
    )[-2:]

    if supplied_end_digits != expected_end_digits:
        raise ValueError(
            "UNICA season years are not consecutive: "
            f"{season!r}"
        )

    return (
        f"{str(start_year)[-2:]}-"
        f"{expected_end_digits}"
    )


def build_period_end_date(
    season: str,
    period_text: str,
) -> pd.Timestamp:
    """
    Build the calendar date for one UNICA reporting period.

    UNICA harvest seasons run from April to March.

    Therefore:

    April–December belong to the season start year.

    January–March belong to the following calendar year.

    Examples
    --------
    season = "25-26"

    01/04 -> 2025-04-01

    16/08 -> 2025-08-16

    16/12 -> 2025-12-16

    01/01 -> 2026-01-01

    16/03 -> 2026-03-16
    """

    normalized_season = normalize_harvest_season(
        season
    )

    start_year_short = int(
        normalized_season[:2]
    )

    start_year = 2000 + start_year_short

    day_text, month_text = period_text.split(
        "/"
    )

    day = int(
        day_text
    )

    month = int(
        month_text
    )

    if month >= 4:
        calendar_year = start_year
    else:
        calendar_year = start_year + 1

    return pd.Timestamp(
        year=calendar_year,
        month=month,
        day=day,
    )


def convert_cumulative_to_biweekly(
    crushing_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert cumulative crushing tonnes into biweekly tonnes.

    Each season-region series must start on 16 April, the first
    reporting period in the UNICA table. The first cumulative value
    therefore equals the first biweekly value; subsequent biweekly
    values are calculated as differences between consecutive
    cumulative observations.
    """

    required_columns = {
        "season",
        "period_end_date",
        "region",
        "cumulative_crush_tonnes",
    }

    missing_columns = required_columns.difference(
        crushing_df.columns
    )

    if missing_columns:
        raise ValueError(
            "Cannot convert cumulative crushing data because "
            "required columns are missing: "
            f"{sorted(missing_columns)}"
        )

    converted_groups: list[pd.DataFrame] = []

    for (
        season,
        region,
    ), group_df in crushing_df.groupby(
        [
            "season",
            "region",
        ],
        sort=False,
    ):
        ordered_group = (
            group_df
            .sort_values(
                "period_end_date"
            )
            .copy()
        )

        first_period = ordered_group.iloc[0][
            "period_end_date"
        ]

        if not (
            first_period.month == 4
            and first_period.day == 16
        ):
            raise ValueError(
                "Cannot derive the first biweekly crushing value "
                "because the cumulative series does not begin on "
                f"16 April: season={season!r}, region={region!r}, "
                f"first_period={first_period.date()}"
            )

        cumulative_tonnes = ordered_group[
            "cumulative_crush_tonnes"
        ]

        biweekly_tonnes = cumulative_tonnes.diff()
        biweekly_tonnes.iloc[0] = cumulative_tonnes.iloc[0]

        if (biweekly_tonnes < 0).any():
            invalid_rows = ordered_group.loc[
                biweekly_tonnes < 0,
                [
                    "period_end_date",
                    "cumulative_crush_tonnes",
                ],
            ]

            raise ValueError(
                "Cumulative crushing tonnes decreased within a "
                f"season-region series: season={season!r}, "
                f"region={region!r}, rows={invalid_rows.to_dict('records')}"
            )

        ordered_group["crush_tonnes"] = (
            biweekly_tonnes.astype("int64")
        )

        converted_groups.append(
            ordered_group
        )

    converted_df = pd.concat(
        converted_groups,
        ignore_index=True,
    )

    return converted_df


def normalize_historical_crushing_table(
    pdf_path: Path,
) -> pd.DataFrame:
    """
    Convert a UNICA cumulative crushing table into tidy biweekly format.

    The PDF table contains cumulative tonnes. This function converts
    them into period-specific biweekly tonnes so the output matches the
    official UNICA TB_02 historical database.

    The output contains one row for each:

    harvest season × reporting date × region
    """

    tables = extract_historical_crushing_tables(
        pdf_path
    )

    if len(tables) != 1:
        raise ValueError(
            "Expected exactly one historical crushing table, "
            f"but found {len(tables)}."
        )

    table = tables[0]

    if len(table) < 4:
        raise ValueError(
            "UNICA table does not contain the expected "
            "header and data rows."
        )

    season_header_row = table[2]

    (
        previous_season,
        current_season,
    ) = extract_season_labels(
        season_header_row
    )

    data_rows = table[3:]

    records: list[dict] = []

    for row in data_rows:
        period = row[0]

        if (
            period is None
            or not PERIOD_PATTERN.fullmatch(
                period
            )
        ):
            continue

        for column_index, region in (
            REGION_COLUMNS.items()
        ):
            region_cell = row[
                column_index
            ]

            # Future reporting dates are printed in the table
            # but contain no observations yet.
            if region_cell is None:
                continue

            (
                previous_tonnes,
                current_tonnes,
                variation_percent,
            ) = parse_region_cell(
                region_cell
            )

            records.extend(
                [
                    {
                        "season": previous_season,
                        "period_end_date":
                            build_period_end_date(
                                season=previous_season,
                                period_text=period,
                            ),
                        "region": region,
                        "cumulative_crush_tonnes":
                            previous_tonnes,
                        "variation_percent":
                            variation_percent,
                    },
                    {
                        "season": current_season,
                        "period_end_date":
                            build_period_end_date(
                                season=current_season,
                                period_text=period,
                            ),
                        "region": region,
                        "cumulative_crush_tonnes":
                            current_tonnes,
                        "variation_percent":
                            variation_percent,
                    },
                ]
            )
    crushing_df = pd.DataFrame(
        records
    )

    if crushing_df.empty:
        raise ValueError(
            "No cumulative crushing observations "
            "were normalized."
        )
    
    crushing_df["period_end_date"] = pd.to_datetime(
        crushing_df["period_end_date"],
        errors="raise",
    )

    crushing_df = convert_cumulative_to_biweekly(
        crushing_df
    )

    crushing_df = (
        crushing_df
        .sort_values(
            [
                "season",
                "period_end_date",
                "region",
            ]
        )
        .reset_index(drop=True)
    )

    return crushing_df[
        [
            "season",
            "period_end_date",
            "region",
            "crush_tonnes",
            "variation_percent",
        ]
    ]


if __name__ == "__main__":
    project_root = Path(
        __file__
    ).resolve().parents[3]

    input_path = (
        project_root
        / "data"
        / "raw"
        / "unica"
        / "biweekly_reports"
        / "unica_report_2026-06-01.pdf"
    )

    output_path = (
        project_root
        / "data"
        / "processed"
        / "unica"
        / "crushing"
        / "reports"
        / "unica_crushing_2026-06-01.csv"
    )

    crushing_df = (
        normalize_historical_crushing_table(
            pdf_path=input_path,
        )
    )

    validate_historical_crushing_dataframe(
        crushing_df,
    )

    print(
        "UNICA historical crushing data "
        "passed validation."
    )

    save_dataframe_csv(
        crushing_df,
        output_path,
    )

    print(
        f"Saved normalized UNICA data to: "
        f"{output_path}"
    )

    print(
        crushing_df.to_string(
            index=False
        )
    )