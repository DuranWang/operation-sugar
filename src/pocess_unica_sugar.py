from pathlib import Path

import pandas as pd

from etl.loader import load_excel_sheet
from etl.saver import save_dataframe_csv
from etl.summary import summarize_dataframe
from etl.validator import (
    validate_allowed_values,
    validate_expected_columns,
    validate_no_duplicates,
    validate_no_missing_values,
    validate_non_negative,
)
from schemas.unica_schema import (
    UNICA_REGION_MAP,
    UNICA_SUGAR_COLUMN_MAP,
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
    / "sugar"
    / "unica_biweekly_sugar.csv"
)


def load_unica_sugar(
    excel_path: Path,
) -> pd.DataFrame:
    """Load the raw UNICA biweekly sugar production table."""

    return load_excel_sheet(
        excel_path,
        sheet_name="TB_04",
    )


def transform_unica_sugar(
    raw_df: pd.DataFrame,
) -> pd.DataFrame:
    """Transform raw UNICA sugar data into the standard schema."""

    required_columns = set(
        UNICA_SUGAR_COLUMN_MAP
    )

    missing_columns = (
        required_columns
        - set(raw_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "TB_04 is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    sugar_df = raw_df.copy()

    sugar_df = sugar_df.rename(
        columns=UNICA_SUGAR_COLUMN_MAP
    )

    sugar_df["season"] = (
        sugar_df["season"]
        .astype("string")
        .str.strip()
    )

    sugar_df["region"] = (
        sugar_df["region"]
        .astype("string")
        .str.strip()
        .replace(UNICA_REGION_MAP)
    )

    sugar_df["period_end_date"] = pd.to_datetime(
        sugar_df["period_end_date"],
        errors="coerce",
    )

    sugar_df["sugar_tonnes"] = pd.to_numeric(
        sugar_df["sugar_tonnes"],
        errors="coerce",
    )

    sugar_df = sugar_df[
        [
            "season",
            "period_end_date",
            "region",
            "sugar_tonnes",
        ]
    ]

    return sugar_df


def validate_unica_sugar(
    sugar_df: pd.DataFrame,
) -> None:
    """Validate the processed UNICA biweekly sugar dataset."""

    expected_columns = [
        "season",
        "period_end_date",
        "region",
        "sugar_tonnes",
    ]

    validate_expected_columns(
        sugar_df,
        expected_columns,
    )

    validate_no_missing_values(
        sugar_df,
    )

    validate_allowed_values(
        sugar_df,
        column="region",
        allowed_values={
            "sao_paulo",
            "other_states",
        },
    )

    validate_non_negative(
        sugar_df,
        column="sugar_tonnes",
    )

    validate_no_duplicates(
        sugar_df,
        subset=[
            "season",
            "period_end_date",
            "region",
        ],
    )

    if not pd.api.types.is_datetime64_any_dtype(
        sugar_df["period_end_date"]
    ):
        raise ValueError(
            "'period_end_date' must have a datetime dtype."
        )

    if not pd.api.types.is_numeric_dtype(
        sugar_df["sugar_tonnes"]
    ):
        raise ValueError(
            "'sugar_tonnes' must have a numeric dtype."
        )

    print(
        "Validation passed: "
        "UNICA sugar data is valid."
    )


def main() -> None:
    """Run the UNICA biweekly sugar processing pipeline."""

    raw_df = load_unica_sugar(
        INPUT_PATH
    )

    sugar_df = transform_unica_sugar(
        raw_df
    )

    validate_unica_sugar(
        sugar_df
    )

    summarize_dataframe(
        sugar_df,
        name="Processed UNICA Biweekly Sugar Data",
        date_column="period_end_date",
    )

    save_dataframe_csv(
        sugar_df,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()