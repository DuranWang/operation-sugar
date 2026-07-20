from pathlib import Path

import pandas as pd


RAW_PATH = Path("data/raw/tabela5457.csv")

PROCESSED_PATH = Path(
    "data/processed/sp_sugarcane_production_tonnes.csv"
)


def process_ibge_sugar_production(
    raw_path: Path = RAW_PATH,
    output_path: Path = PROCESSED_PATH,
) -> pd.DataFrame:
    """Process São Paulo sugarcane production data from IBGE Table 5457."""

    if not raw_path.exists():
        raise FileNotFoundError(
            f"IBGE dataset not found: {raw_path}"
        )

    # Load the raw IBGE table.
    production_df = pd.read_csv(
        raw_path,
        skiprows=3,
    )

    if production_df.empty:
        raise ValueError(
            "IBGE production dataset is empty."
        )

    if production_df.shape[1] < 2:
        raise ValueError(
            "IBGE dataset does not contain production columns."
        )

    # Extract year labels.
    years = production_df.columns[1:].tolist()

    # The first data row contains the crop description
    # ("Cana-de-açúcar") rather than municipality data.
    # Municipality records therefore begin at row index 1.
    municipalities = production_df.iloc[1:, 0].tolist()
    production = production_df.iloc[1:, 1:]

    processed_df = pd.DataFrame(
        data=production.values,
        columns=years,
    )

    processed_df.insert(
        0,
        "municipality",
        municipalities,
    )

    # Keep only São Paulo municipalities.
    processed_df = processed_df[
        processed_df["municipality"]
        .astype(str)
        .str.endswith("(SP)", na=False)
    ].copy()

    if processed_df.empty:
        raise ValueError(
            "No São Paulo municipalities were found."
        )

    # Remove the "(SP)" suffix.
    processed_df["municipality"] = (
        processed_df["municipality"]
        .str.replace(
            " (SP)",
            "",
            regex=False,
        )
        .str.strip()
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Saved {len(processed_df)} municipalities "
        f"to {output_path}"
    )

    return processed_df


def main() -> None:
    """Run the IBGE processing pipeline."""

    process_ibge_sugar_production()


if __name__ == "__main__":
    main()