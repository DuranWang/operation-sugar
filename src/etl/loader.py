from pathlib import Path

import pandas as pd


def load_excel_sheet(
    excel_path: Path,
    sheet_name: str,
    **read_excel_kwargs,
) -> pd.DataFrame:
    """
    Load one worksheet from an Excel workbook.

    Parameters
    ----------
    excel_path:
        Path to the Excel workbook.

    sheet_name:
        Name of the worksheet to load.

    **read_excel_kwargs:
        Additional keyword arguments passed to pandas.read_excel().

    Returns
    -------
    pd.DataFrame
        Raw worksheet data with no transformations applied.

    Raises
    ------
    FileNotFoundError
        If the workbook does not exist.
    """

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Excel workbook not found: {excel_path}"
        )

    return pd.read_excel(
        excel_path,
        sheet_name=sheet_name,
        **read_excel_kwargs,
    )


def load_csv(
    csv_path: Path,
    **read_csv_kwargs,
) -> pd.DataFrame:
    """
    Load a CSV file.

    Parameters
    ----------
    csv_path:
        Path to the CSV file.

    **read_csv_kwargs:
        Additional keyword arguments passed to pandas.read_csv().

    Returns
    -------
    pd.DataFrame
        Raw CSV data with no transformations applied.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    """

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}"
        )

    return pd.read_csv(
        csv_path,
        **read_csv_kwargs,
    )


def load_yearly_csv_files(
    input_folder: Path,
    years: list[int],
    **read_csv_kwargs,
) -> pd.DataFrame:
    """
    Load and combine yearly CSV files.

    Each file is expected to follow the naming convention
    ``<year>.csv``.

    Parameters
    ----------
    input_folder:
        Folder containing yearly CSV files.

    years:
        Years to load.

    **read_csv_kwargs:
        Additional keyword arguments passed to pandas.read_csv().

    Returns
    -------
    pd.DataFrame
        Combined data from all requested yearly CSV files.

    Raises
    ------
    FileNotFoundError
        If the input folder or any requested yearly file does not exist.

    ValueError
        If no years are provided.
    """

    if not input_folder.exists():
        raise FileNotFoundError(
            f"Input folder not found: {input_folder}"
        )

    if not years:
        raise ValueError(
            "At least one year must be provided."
        )

    dataframes = []

    for year in years:
        input_path = input_folder / f"{year}.csv"

        yearly_df = load_csv(
            input_path,
            **read_csv_kwargs,
        )

        dataframes.append(yearly_df)

    return pd.concat(
        dataframes,
        ignore_index=True,
    )