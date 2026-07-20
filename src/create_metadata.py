from pathlib import Path

import pandas as pd


PRODUCTION_PATH = Path(
    "data/processed/sp_sugarcane_production_tonnes.csv"
)
OUTPUT_PATH = Path(
    "data/metadata/sp_municipalities.csv"
)

MUNICIPALITY_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "kelvins/Municipios-Brasileiros/main/csv/municipios.csv"
)

SP_STATE_CODE = 35

# Known naming differences between the production dataset
# and the municipality-coordinate dataset.
CITY_NAME_FIXES = {
    "Biritiba Mirim": "Biritiba-Mirim",
    "Florínea": "Florínia",
    "Itaoca": "Itaóca",
}


def create_sp_metadata(
    production_path: Path = PRODUCTION_PATH,
    output_path: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    """Create municipality metadata for São Paulo sugarcane data."""

    # Load processed sugarcane production data.
    production_df = pd.read_csv(production_path)

    if production_df.empty:
        raise ValueError("Production dataset is empty.")

    required_columns = {"municipality"}
    missing_columns = required_columns - set(production_df.columns)

    if missing_columns:
        raise ValueError(
            f"Production dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    # Extract one record per municipality and normalize known name differences.
    sp_cities = (
        production_df["municipality"]
        .dropna()
        .drop_duplicates()
        .replace(CITY_NAME_FIXES)
        .sort_values()
        .reset_index(drop=True)
    )

    metadata_df = pd.DataFrame(
        {
            "municipality": sp_cities,
            "state": "SP",
        }
    )

    # Load Brazilian municipality coordinates.
    all_cities = pd.read_csv(MUNICIPALITY_DATA_URL)

    coordinate_columns = {
        "codigo_uf",
        "nome",
        "codigo_ibge",
        "latitude",
        "longitude",
    }
    missing_coordinate_columns = (
        coordinate_columns - set(all_cities.columns)
    )

    if missing_coordinate_columns:
        raise ValueError(
            f"Municipality dataset is missing columns: "
            f"{sorted(missing_coordinate_columns)}"
        )

    # Restrict the coordinate data to São Paulo before merging.
    sp_coordinates = (
        all_cities.loc[
            all_cities["codigo_uf"] == SP_STATE_CODE,
            ["nome", "codigo_ibge", "latitude", "longitude"],
        ]
        .drop_duplicates(subset=["codigo_ibge"])
        .copy()
    )

    # Match production municipalities with IBGE metadata.
    metadata_df = metadata_df.merge(
        sp_coordinates,
        left_on="municipality",
        right_on="nome",
        how="left",
        validate="one_to_one",
    )

    metadata_df = (
        metadata_df
        .drop(columns=["nome"])
        .rename(columns={"codigo_ibge": "ibge_code"})
    )

    metadata_df["ibge_code"] = metadata_df["ibge_code"].astype("Int64")

    # Validate merge completeness.
    missing_metadata = metadata_df[
        metadata_df[
            ["ibge_code", "latitude", "longitude"]
        ].isna().any(axis=1)
    ]

    if not missing_metadata.empty:
        missing_names = missing_metadata["municipality"].tolist()
        raise ValueError(
            "Metadata could not be found for these municipalities: "
            f"{missing_names}"
        )

    if metadata_df["municipality"].duplicated().any():
        duplicated_names = metadata_df.loc[
            metadata_df["municipality"].duplicated(keep=False),
            "municipality",
        ].tolist()

        raise ValueError(
            f"Duplicate municipalities found: {duplicated_names}"
        )

    # Create the output directory when necessary.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata_df.to_csv(output_path, index=False)

    print(
        f"Saved metadata for {len(metadata_df)} municipalities "
        f"to {output_path}"
    )

    return metadata_df


if __name__ == "__main__":
    create_sp_metadata()