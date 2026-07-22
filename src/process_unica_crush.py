from pathlib import Path

import pandas as pd

from src.etl.loader import load_excel_sheet
from src.etl.saver import save_dataframe_csv
from src.etl.summary import summarize_dataframe
from src.etl.validator import (
    validate_allowed_values,
    validate_expected_columns,
    validate_no_duplicates,
    validate_no_missing_values,
    validate_non_negative,
)
from src.schemas.unica_schema import (
    UNICA_CRUSH_COLUMN_MAP,
    UNICA_REGION_MAP,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "unica"
    / "unica_historical_database.xlsx"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unica"
    / "crushing"
    / "unica_biweekly_crush.csv"
)


def load_unica_crush(
    excel_path: Path,
) -> pd.DataFrame:
    """Load the raw UNICA biweekly sugarcane crush table."""

    return load_excel_sheet(
        excel_path,
        sheet_name="TB_02",
    )


def transform_unica_crush(
    raw_df: pd.DataFrame,
) -> pd.DataFrame:
    """Transform raw UNICA crush data into the standard schema."""

    required_columns = set(
        UNICA_CRUSH_COLUMN_MAP
    )

    missing_columns = (
        required_columns
        - set(raw_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "TB_02 is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    crush_df = raw_df.copy()

    crush_df = crush_df.rename(
        columns=UNICA_CRUSH_COLUMN_MAP
    )

    crush_df["season"] = (
        crush_df["season"]
        .astype("string")
        .str.strip()
    )

    crush_df["region"] = (
        crush_df["region"]
        .astype("string")
        .str.strip()
        .replace(UNICA_REGION_MAP)
    )

    crush_df["period_end_date"] = pd.to_datetime(
        crush_df["period_end_date"],
        errors="coerce",
    )

    crush_df["crush_tonnes"] = pd.to_numeric(
        crush_df["crush_tonnes"],
        errors="coerce",
    )

    crush_df = crush_df[
        [
            "season",
            "period_end_date",
            "region",
            "crush_tonnes",
        ]
    ]

    return crush_df


def validate_unica_crush(
    crush_df: pd.DataFrame,
) -> None:
    """Validate the processed UNICA biweekly crush dataset."""

    expected_columns = [
        "season",
        "period_end_date",
        "region",
        "crush_tonnes",
    ]

    validate_expected_columns(
        crush_df,
        expected_columns,
    )

    validate_no_missing_values(
        crush_df,
    )

    validate_allowed_values(
        crush_df,
        column="region",
        allowed_values={
            "sao_paulo",
            "other_states",
        },
    )

    validate_non_negative(
        crush_df,
        column="crush_tonnes",
    )

    validate_no_duplicates(
        crush_df,
        subset=[
            "season",
            "period_end_date",
            "region",
        ],
    )

    if not pd.api.types.is_datetime64_any_dtype(
        crush_df["period_end_date"]
    ):
        raise ValueError(
            "'period_end_date' must have a datetime dtype."
        )

    if not pd.api.types.is_numeric_dtype(
        crush_df["crush_tonnes"]
    ):
        raise ValueError(
            "'crush_tonnes' must have a numeric dtype."
        )

    print(
        "Validation passed: "
        "UNICA crush data is valid."
    )


def main() -> None:
    """Run the UNICA biweekly crush processing pipeline."""

    raw_df = load_unica_crush(
        INPUT_PATH
    )

    crush_df = transform_unica_crush(
        raw_df
    )

    validate_unica_crush(
        crush_df
    )

    summarize_dataframe(
        crush_df,
        name="Processed UNICA Biweekly Crush Data",
        date_column="period_end_date",
    )

    save_dataframe_csv(
        crush_df,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()