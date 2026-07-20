from pathlib import Path

import pandas as pd
import pytest

from src.etl.loader import (
    load_csv,
    load_excel_sheet,
    load_yearly_csv_files,
)


def test_load_csv_passes(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "sample.csv"

    expected_df = pd.DataFrame(
        {
            "municipality": [
                "Adamantina",
                "Adolfo",
            ],
            "rainfall": [
                10.0,
                20.0,
            ],
        }
    )

    expected_df.to_csv(
        csv_path,
        index=False,
    )

    actual_df = load_csv(
        csv_path
    )

    pd.testing.assert_frame_equal(
        actual_df,
        expected_df,
    )


def test_load_csv_raises_when_file_is_missing(
    tmp_path: Path,
) -> None:
    missing_path = (
        tmp_path
        / "missing.csv"
    )

    with pytest.raises(
        FileNotFoundError,
        match="CSV file not found",
    ):
        load_csv(
            missing_path
        )


def test_load_yearly_csv_files_passes(
    tmp_path: Path,
) -> None:
    weather_2020 = pd.DataFrame(
        {
            "year": [
                2020,
                2020,
            ],
            "rainfall": [
                10.0,
                20.0,
            ],
        }
    )

    weather_2021 = pd.DataFrame(
        {
            "year": [
                2021,
                2021,
            ],
            "rainfall": [
                30.0,
                40.0,
            ],
        }
    )

    weather_2020.to_csv(
        tmp_path / "2020.csv",
        index=False,
    )

    weather_2021.to_csv(
        tmp_path / "2021.csv",
        index=False,
    )

    actual_df = load_yearly_csv_files(
        input_folder=tmp_path,
        years=[
            2020,
            2021,
        ],
    )

    expected_df = pd.concat(
        [
            weather_2020,
            weather_2021,
        ],
        ignore_index=True,
    )

    pd.testing.assert_frame_equal(
        actual_df,
        expected_df,
    )


def test_load_yearly_csv_files_raises_when_folder_is_missing(
    tmp_path: Path,
) -> None:
    missing_folder = (
        tmp_path
        / "missing_folder"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Input folder not found",
    ):
        load_yearly_csv_files(
            input_folder=missing_folder,
            years=[
                2020,
            ],
        )


def test_load_yearly_csv_files_raises_when_years_are_empty(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="At least one year must be provided",
    ):
        load_yearly_csv_files(
            input_folder=tmp_path,
            years=[],
        )


def test_load_yearly_csv_files_raises_when_year_file_is_missing(
    tmp_path: Path,
) -> None:
    existing_df = pd.DataFrame(
        {
            "year": [
                2020,
            ],
            "rainfall": [
                10.0,
            ],
        }
    )

    existing_df.to_csv(
        tmp_path / "2020.csv",
        index=False,
    )

    with pytest.raises(
        FileNotFoundError,
        match="CSV file not found",
    ):
        load_yearly_csv_files(
            input_folder=tmp_path,
            years=[
                2020,
                2021,
            ],
        )


def test_load_excel_sheet_passes(
    tmp_path: Path,
) -> None:
    excel_path = (
        tmp_path
        / "sample.xlsx"
    )

    expected_df = pd.DataFrame(
        {
            "municipality": [
                "Adamantina",
                "Adolfo",
            ],
            "rainfall": [
                10.0,
                20.0,
            ],
        }
    )

    expected_df.to_excel(
        excel_path,
        sheet_name="Weather",
        index=False,
    )

    actual_df = load_excel_sheet(
        excel_path=excel_path,
        sheet_name="Weather",
    )

    pd.testing.assert_frame_equal(
        actual_df,
        expected_df,
        check_dtype=False,
    )


def test_load_excel_sheet_raises_when_file_is_missing(
    tmp_path: Path,
) -> None:
    missing_path = (
        tmp_path
        / "missing.xlsx"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Excel workbook not found",
    ):
        load_excel_sheet(
            excel_path=missing_path,
            sheet_name="Weather",
        )