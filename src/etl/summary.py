import pandas as pd



def summarize_dataframe(
    df: pd.DataFrame,
    name: str = "DATAFRAME",
    date_column: str | None = None,
) -> None:
    
    """
    Print a standardized summary of a dataframe.

    Parameters
    ----------
    df:
        Dataframe to inspect.

    name:
        Descriptive dataset name displayed in the summary.

    date_column:
        Optional datetime column used to report the date range.

    Raises
    ------
    ValueError
        If the requested date column does not exist.
    """
    
    print("\n" + "=" * 60)
    print(name.upper())
    print("=" * 60)

    print("\nHEAD")
    print(df.head(5))

    print("\nSHAPE")
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    print("\nCOLUMN NAMES")
    print(list(df.columns))

    print("\nDTYPES")
    print(df.dtypes)

    print("\nMISSING VALUES")
    print(df.isna().sum())

    print("\nDUPLICATE ROWS")
    print(df.duplicated().sum())

    if date_column is not None:
        if date_column not in df.columns:
            raise ValueError(
                f"Date column not found: {date_column}"
            )

        print("\nDATE RANGE")
        print(f"Start: {df[date_column].min()}")
        print(f"End:   {df[date_column].max()}")

    print("=" * 60)