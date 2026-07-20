from pathlib import Path

import pandas as pd



def save_dataframe_csv(
    df: pd.DataFrame,
    output_path: Path,
    *,
    encoding: str = "utf-8",
) -> None:
    
    """
    Save a DataFrame to a CSV file.

    The destination directory is created automatically
    if it does not already exist.


    Parameters
    ----------
    df:
        Dataframe to save.

    output_path:
        Destination CSV path.

    encoding:
        Text encoding used for the output file.
    """
    
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
        encoding=encoding,
    )

    print(
        "\nData saved successfully:"
        f"\n{output_path}"
    )