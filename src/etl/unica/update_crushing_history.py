"""
Safely append normalized UNICA biweekly crushing observations
to the official historical crushing database.

Safety rules
------------
1. Existing historical observations are never overwritten.
2. Overlapping observations must contain identical crush values.
3. Only genuinely new season-date-region records are appended.
4. Both input files must follow the expected schema.
5. Duplicate keys are rejected before any file is modified.
6. The final dataset is validated before writing.
7. A timestamped backup is created before replacement.
8. Data is first written to a temporary file and then atomically moved.
"""

from datetime import datetime
from pathlib import Path
import os
import shutil

import pandas as pd


UNIQUE_COLUMNS = [
    "season",
    "period_end_date",
    "region",
]

HISTORY_COLUMNS = [
    "season",
    "period_end_date",
    "region",
    "crush_tonnes",
]

HISTORY_REGIONS = {
    "sao_paulo",
    "other_states",
}

ALLOWED_EXTRA_REPORT_REGIONS = {
    "centre_south",
}

def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
    dataframe_name: str,
) -> None:
    """Validate that a DataFrame contains all required columns."""

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataframe_name} is missing required columns: "
            f"{missing_columns}"
        )


def validate_no_duplicate_keys(
    dataframe: pd.DataFrame,
    dataframe_name: str,
) -> None:
    """Reject duplicate season-date-region keys."""

    duplicate_mask = dataframe.duplicated(
        subset=UNIQUE_COLUMNS,
        keep=False,
    )

    if not duplicate_mask.any():
        return

    duplicate_rows = (
        dataframe.loc[
            duplicate_mask,
            HISTORY_COLUMNS,
        ]
        .sort_values(
            UNIQUE_COLUMNS
        )
    )

    raise ValueError(
        f"Duplicate keys found in {dataframe_name}:\n"
        f"{duplicate_rows.to_string(index=False)}"
    )


def validate_crush_values(
    dataframe: pd.DataFrame,
    dataframe_name: str,
) -> None:
    """Validate crushing values are numeric, non-missing, and non-negative."""

    dataframe["crush_tonnes"] = pd.to_numeric(
        dataframe["crush_tonnes"],
        errors="raise",
    )

    if dataframe["crush_tonnes"].isna().any():
        invalid_rows = dataframe.loc[
            dataframe["crush_tonnes"].isna(),
            HISTORY_COLUMNS,
        ]

        raise ValueError(
            f"Missing crush_tonnes values found in "
            f"{dataframe_name}:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    negative_mask = (
        dataframe["crush_tonnes"] < 0
    )

    if negative_mask.any():
        invalid_rows = dataframe.loc[
            negative_mask,
            HISTORY_COLUMNS,
        ]

        raise ValueError(
            f"Negative crush_tonnes values found in "
            f"{dataframe_name}:\n"
            f"{invalid_rows.to_string(index=False)}"
        )


def validate_key_values(
    dataframe: pd.DataFrame,
    dataframe_name: str,
) -> None:
    """Validate that key columns contain no missing values."""

    missing_key_mask = dataframe[
        UNIQUE_COLUMNS
    ].isna().any(
        axis=1
    )

    if not missing_key_mask.any():
        return

    invalid_rows = dataframe.loc[
        missing_key_mask,
        HISTORY_COLUMNS,
    ]

    raise ValueError(
        f"Missing key values found in {dataframe_name}:\n"
        f"{invalid_rows.to_string(index=False)}"
    )


def prepare_crushing_dataframe(
    dataframe: pd.DataFrame,
    dataframe_name: str,
) -> pd.DataFrame:
    """
    Select, convert, and validate the official historical schema.
    """

    validate_required_columns(
        dataframe=dataframe,
        required_columns=HISTORY_COLUMNS,
        dataframe_name=dataframe_name,
    )

    prepared_df = dataframe[
        HISTORY_COLUMNS
    ].copy()

    prepared_df["season"] = (
        prepared_df["season"]
        .astype(str)
        .str.strip()
    )

    prepared_df["region"] = (
        prepared_df["region"]
        .astype(str)
        .str.strip()
    )

    prepared_df["period_end_date"] = pd.to_datetime(
        prepared_df["period_end_date"],
        errors="raise",
    )

    validate_key_values(
        dataframe=prepared_df,
        dataframe_name=dataframe_name,
    )

    validate_crush_values(
        dataframe=prepared_df,
        dataframe_name=dataframe_name,
    )

    validate_no_duplicate_keys(
        dataframe=prepared_df,
        dataframe_name=dataframe_name,
    )

    return prepared_df


def find_conflicting_observations(
    history_df: pd.DataFrame,
    new_report_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Find overlapping keys whose crush values disagree.
    """

    overlap_df = history_df.merge(
        new_report_df,
        on=UNIQUE_COLUMNS,
        how="inner",
        suffixes=(
            "_history",
            "_report",
        ),
        validate="one_to_one",
    )

    conflict_mask = (
        overlap_df["crush_tonnes_history"]
        != overlap_df["crush_tonnes_report"]
    )

    return overlap_df.loc[
        conflict_mask
    ].copy()


def find_new_observations(
    history_df: pd.DataFrame,
    new_report_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return report observations whose keys do not exist in history.
    """

    existing_keys_df = history_df[
        UNIQUE_COLUMNS
    ].copy()

    new_rows_df = new_report_df.merge(
        existing_keys_df,
        on=UNIQUE_COLUMNS,
        how="left",
        indicator=True,
        validate="many_to_one",
    )

    new_rows_df = (
        new_rows_df.loc[
            new_rows_df["_merge"] == "left_only",
            HISTORY_COLUMNS,
        ]
        .copy()
    )

    return new_rows_df


def validate_existing_history_preserved(
    original_history_df: pd.DataFrame,
    combined_df: pd.DataFrame,
) -> None:
    """
    Confirm every original historical observation remains unchanged.
    """

    preservation_check_df = original_history_df.merge(
        combined_df,
        on=UNIQUE_COLUMNS,
        how="left",
        suffixes=(
            "_original",
            "_combined",
        ),
        indicator=True,
        validate="one_to_one",
    )

    missing_original_mask = (
        preservation_check_df["_merge"] != "both"
    )

    if missing_original_mask.any():
        missing_rows = preservation_check_df.loc[
            missing_original_mask
        ]

        raise ValueError(
            "Some historical observations disappeared during "
            "the merge. No file was modified:\n"
            f"{missing_rows.to_string(index=False)}"
        )

    changed_value_mask = (
        preservation_check_df["crush_tonnes_original"]
        != preservation_check_df["crush_tonnes_combined"]
    )

    if changed_value_mask.any():
        changed_rows = preservation_check_df.loc[
            changed_value_mask
        ]

        raise ValueError(
            "Some historical crush values changed during "
            "the merge. No file was modified:\n"
            f"{changed_rows.to_string(index=False)}"
        )


def validate_final_dataframe(
    combined_df: pd.DataFrame,
    expected_row_count: int,
) -> None:
    """Run final validations before the historical file is written."""

    validate_required_columns(
        dataframe=combined_df,
        required_columns=HISTORY_COLUMNS,
        dataframe_name="combined historical database",
    )

    validate_key_values(
        dataframe=combined_df,
        dataframe_name="combined historical database",
    )

    validate_crush_values(
        dataframe=combined_df,
        dataframe_name="combined historical database",
    )

    validate_no_duplicate_keys(
        dataframe=combined_df,
        dataframe_name="combined historical database",
    )

    if len(combined_df) != expected_row_count:
        raise ValueError(
            "Unexpected final row count. "
            f"Expected {expected_row_count}, "
            f"but obtained {len(combined_df)}."
        )


def create_timestamped_backup(
    history_path: Path,
) -> Path:
    """Create a timestamped copy of the historical CSV."""

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = history_path.with_name(
        f"{history_path.stem}_"
        f"{timestamp}.backup"
        f"{history_path.suffix}"
    )

    shutil.copy2(
        history_path,
        backup_path,
    )

    return backup_path


def write_dataframe_safely(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Write through a temporary file and atomically replace the target.
    """

    temporary_path = output_path.with_name(
        f"{output_path.stem}.tmp"
        f"{output_path.suffix}"
    )

    if temporary_path.exists():
        temporary_path.unlink()

    try:
        dataframe.to_csv(
            temporary_path,
            index=False,
        )

        # Confirm the temporary file can be read before replacement.
        verification_df = pd.read_csv(
            temporary_path
        )

        if len(verification_df) != len(dataframe):
            raise ValueError(
                "Temporary CSV verification failed: "
                "row count changed after writing."
            )

        os.replace(
            temporary_path,
            output_path,
        )

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()

        raise


def update_crushing_history(
    history_path: Path,
    new_report_path: Path,
) -> pd.DataFrame:
    """
    Safely append missing UNICA observations to historical data.

    Existing historical rows are never overwritten. Any disagreement
    between an existing historical observation and an overlapping PDF
    observation stops execution before the history file is modified.
    """

    if not history_path.exists():
        raise FileNotFoundError(
            "Historical database does not exist: "
            f"{history_path}"
        )

    if not new_report_path.exists():
        raise FileNotFoundError(
            "Normalized report does not exist: "
            f"{new_report_path}"
        )

    raw_history_df = pd.read_csv(
        history_path
    )

    raw_new_report_df = pd.read_csv(
        new_report_path
    )

    history_df = prepare_crushing_dataframe(
        dataframe=raw_history_df,
        dataframe_name="historical database",
    )

    new_report_df = prepare_crushing_dataframe(
        dataframe=raw_new_report_df,
        dataframe_name="normalized report",
    )

    history_regions = set(
        history_df["region"].unique()
    )

    unexpected_history_regions = (
        history_regions
        - HISTORY_REGIONS
    )

    if unexpected_history_regions:
        raise ValueError(
            "Historical database contains unsupported regions: "
            f"{sorted(unexpected_history_regions)}"
        )

    report_regions = set(
        new_report_df["region"].unique()
    )

    unsupported_report_regions = (
        report_regions
        - HISTORY_REGIONS
        - ALLOWED_EXTRA_REPORT_REGIONS
    )

    if unsupported_report_regions:
        raise ValueError(
            "Normalized report contains unsupported regions: "
            f"{sorted(unsupported_report_regions)}"
        )

    excluded_report_rows = new_report_df.loc[
        ~new_report_df["region"].isin(
            HISTORY_REGIONS
        )
    ].copy()

    new_report_df = (
        new_report_df.loc[
            new_report_df["region"].isin(
                HISTORY_REGIONS
            )
        ]
        .copy()
    )

    if new_report_df.empty:
        raise ValueError(
            "Normalized report contains no rows for the "
            "historical database regions."
        )

    overlap_df = history_df.merge(
        new_report_df,
        on=UNIQUE_COLUMNS,
        how="inner",
        suffixes=(
            "_history",
            "_report",
        ),
        validate="one_to_one",
    )

    conflicts_df = find_conflicting_observations(
        history_df=history_df,
        new_report_df=new_report_df,
    )

    if not conflicts_df.empty:
        raise ValueError(
            "Conflicting UNICA observations detected. "
            "The historical database was not modified:\n"
            f"{conflicts_df.to_string(index=False)}"
        )

    new_rows_df = find_new_observations(
        history_df=history_df,
        new_report_df=new_report_df,
    )

    combined_df = pd.concat(
        [
            history_df,
            new_rows_df,
        ],
        ignore_index=True,
    )

    combined_df = (
        combined_df
        .sort_values(
            [
                "season",
                "period_end_date",
                "region",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    expected_row_count = (
        len(history_df)
        + len(new_rows_df)
    )

    validate_final_dataframe(
        combined_df=combined_df,
        expected_row_count=expected_row_count,
    )

    validate_existing_history_preserved(
        original_history_df=history_df,
        combined_df=combined_df,
    )

    output_df = combined_df.copy()

    output_df["period_end_date"] = (
        output_df["period_end_date"]
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    backup_path = create_timestamped_backup(
        history_path=history_path,
    )

    try:
        write_dataframe_safely(
            dataframe=output_df,
            output_path=history_path,
        )

    except Exception:
        # Restore the original file if writing or replacement fails.
        shutil.copy2(
            backup_path,
            history_path,
        )

        raise

    print(
        f"Historical rows before update: "
        f"{len(history_df)}"
    )

    print(
        f"Report rows excluded from historical schema: "
        f"{len(excluded_report_rows)}"
    )

    print(
        f"Overlapping validated rows: "
        f"{len(overlap_df)}"
    )

    print(
        f"New rows appended: "
        f"{len(new_rows_df)}"
    )

    print(
        f"Historical rows after update: "
        f"{len(output_df)}"
    )

    print(
        f"Backup created at: "
        f"{backup_path}"
    )

    return output_df


if __name__ == "__main__":
    project_root = Path(
        __file__
    ).resolve().parents[3]

    history_path = (
        project_root
        / "data"
        / "processed"
        / "unica"
        / "crushing"
        / "unica_biweekly_crush.csv"
    )

    new_report_path = (
        project_root
        / "data"
        / "processed"
        / "unica"
        / "crushing"
        / "reports"
        / "unica_crushing_2026-06-01.csv"
    )

    updated_history_df = update_crushing_history(
        history_path=history_path,
        new_report_path=new_report_path,
    )

    print(
        "UNICA crushing history updated successfully."
    )

    print(
        updated_history_df.tail(
            20
        ).to_string(
            index=False
        )
    )