from collections.abc import Collection

import pandas as pd


def validate_expected_columns(
    df: pd.DataFrame,
    expected_columns: list[str],
) -> None:
    """
    Validate that a DataFrame contains exactly the expected columns
    in the expected order.

    Parameters
    ----------
    df:
        DataFrame to validate.

    expected_columns:
        Expected column names in their required order.

    Raises
    ------
    ValueError
        If the columns or their order do not match.
    """

    actual_columns = list(df.columns)

    if actual_columns != expected_columns:
        raise ValueError(
            "Unexpected columns or column order.\n"
            f"Expected: {expected_columns}\n"
            f"Found: {actual_columns}"
        )


def validate_no_missing_values(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> None:
    """
    Validate that selected DataFrame columns contain no missing values.

    If columns is None, every column is checked.

    Parameters
    ----------
    df:
        DataFrame to validate.

    columns:
        Columns to check. If omitted, all columns are checked.

    Raises
    ------
    ValueError
        If requested columns are absent or missing values are found.
    """

    if columns is None:
        checked_df = df
    else:
        missing_columns = set(columns) - set(df.columns)

        if missing_columns:
            raise ValueError(
                "Cannot check missing values because columns are absent: "
                f"{sorted(missing_columns)}"
            )

        checked_df = df[columns]

    missing_counts = checked_df.isna().sum()
    invalid_counts = missing_counts[
        missing_counts > 0
    ]

    if not invalid_counts.empty:
        raise ValueError(
            "Missing values found:\n"
            f"{invalid_counts}"
        )


def validate_no_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
) -> None:
    """
    Validate that a DataFrame contains no duplicate observations.

    Parameters
    ----------
    df:
        DataFrame to validate.

    subset:
        Columns used to identify duplicate observations.
        If omitted, all columns are used.

    Raises
    ------
    ValueError
        If requested columns are absent or duplicates are found.
    """

    if subset is not None:
        missing_columns = set(subset) - set(df.columns)

        if missing_columns:
            raise ValueError(
                "Cannot check duplicates because columns are absent: "
                f"{sorted(missing_columns)}"
            )

    duplicate_mask = df.duplicated(
        subset=subset,
        keep=False,
    )

    if duplicate_mask.any():
        raise ValueError(
            "Duplicate observations found:\n"
            f"{df.loc[duplicate_mask]}"
        )


def validate_non_negative(
    df: pd.DataFrame,
    column: str,
) -> None:
    """
    Validate that a numeric column contains no negative values.

    Parameters
    ----------
    df:
        DataFrame to validate.

    column:
        Numeric column to check.

    Raises
    ------
    ValueError
        If the column is absent, non-numeric, or contains negative values.
    """

    if column not in df.columns:
        raise ValueError(
            f"Column not found: {column}"
        )

    if not pd.api.types.is_numeric_dtype(
        df[column]
    ):
        raise ValueError(
            f"Column is not numeric: {column}"
        )

    negative_mask = df[column] < 0

    if negative_mask.any():
        raise ValueError(
            f"Negative values found in '{column}':\n"
            f"{df.loc[negative_mask]}"
        )


def validate_allowed_values(
    df: pd.DataFrame,
    column: str,
    allowed_values: Collection[str],
) -> None:
    """
    Validate that every non-missing value in a column belongs
    to an allowed collection.

    Parameters
    ----------
    df:
        DataFrame to validate.

    column:
        Column to check.

    allowed_values:
        Collection of permitted values.

    Raises
    ------
    ValueError
        If the column is absent or unexpected values are found.
    """

    if column not in df.columns:
        raise ValueError(
            f"Column not found: {column}"
        )

    allowed_value_set = set(
        allowed_values
    )

    actual_values = set(
        df[column]
        .dropna()
        .unique()
    )

    unexpected_values = (
        actual_values - allowed_value_set
    )

    if unexpected_values:
        raise ValueError(
            f"Unexpected values found in '{column}'.\n"
            f"Allowed: {sorted(allowed_value_set)}\n"
            f"Unexpected: {sorted(unexpected_values)}"
        )