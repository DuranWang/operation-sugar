from pathlib import Path

import pandas as pd


PRODUCTION_PATH = Path(
    "data/processed/sp_sugarcane_annual.csv"
)

OUTPUT_PATH = Path(
    "data/metadata/sp_municipalities.csv"
)

MUNICIPALITY_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "kelvins/Municipios-Brasileiros/main/csv/municipios.csv"
)

SP_STATE_CODE = 35


def create_sp_metadata(
    production_path: Path = PRODUCTION_PATH,
    output_path: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    """Create São Paulo municipality metadata from annual IBGE data."""

    if not production_path.is_file():
        raise FileNotFoundError(
            f"IBGE dataset not found: {production_path}"
        )

    # Load the new municipality-year agricultural dataset.
    production_df = pd.read_csv(
        production_path,
        dtype={"ibge_code": "string"},
    )

    if production_df.empty:
        raise ValueError("IBGE dataset is empty.")

    required_columns = {"ibge_code", "municipality"}
    missing_columns = required_columns - set(production_df.columns)

    if missing_columns:
        raise ValueError(
            "IBGE dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    production_df["ibge_code"] = (
        production_df["ibge_code"].str.strip()
    )

    production_df["municipality"] = (
        production_df["municipality"].astype("string").str.strip()
    )

    if (
        production_df["ibge_code"].isna().any()
        or production_df["municipality"].isna().any()
        or production_df["municipality"].eq("").any()
    ):
        raise ValueError(
            "IBGE dataset contains missing municipality codes or names."
        )

    if not production_df["ibge_code"].str.fullmatch(r"\d{7}").all():
        raise ValueError(
            "IBGE dataset contains invalid municipality codes."
        )

    # Each IBGE code must refer to exactly one municipality name.
    names_per_code = (
        production_df.groupby("ibge_code")["municipality"]
        .nunique()
    )

    if (names_per_code > 1).any():
        conflicting_codes = names_per_code[
            names_per_code > 1
        ].index.tolist()

        raise ValueError(
            "Conflicting municipality names for IBGE codes: "
            f"{conflicting_codes}"
        )

    # Extract one record per municipality.
    municipalities = (
        production_df[["ibge_code", "municipality"]]
        .drop_duplicates(subset=["ibge_code"])
        .copy()
    )

    # Load municipality coordinates.
    all_cities = pd.read_csv(
        MUNICIPALITY_DATA_URL,
        dtype={"codigo_ibge": "string"},
    )

    coordinate_columns = {
        "codigo_uf",
        "codigo_ibge",
        "latitude",
        "longitude",
    }

    missing_coordinate_columns = (
        coordinate_columns - set(all_cities.columns)
    )

    if missing_coordinate_columns:
        raise ValueError(
            "Coordinate dataset is missing columns: "
            f"{sorted(missing_coordinate_columns)}"
        )

    sp_coordinates = all_cities.loc[
        pd.to_numeric(
            all_cities["codigo_uf"],
            errors="coerce",
        ) == SP_STATE_CODE,
        ["codigo_ibge", "latitude", "longitude"],
    ].copy()

    sp_coordinates = sp_coordinates.rename(
        columns={"codigo_ibge": "ibge_code"}
    )

    sp_coordinates["ibge_code"] = (
        sp_coordinates["ibge_code"].str.strip()
    )

    if sp_coordinates["ibge_code"].duplicated().any():
        raise ValueError(
            "Coordinate dataset contains duplicate SP IBGE codes."
        )

    # Match by IBGE code instead of municipality name.
    metadata_df = municipalities.merge(
        sp_coordinates,
        on="ibge_code",
        how="left",
        validate="one_to_one",
    )

    missing_metadata = metadata_df.loc[
        metadata_df[
            ["latitude", "longitude"]
        ].isna().any(axis=1)
    ]

    if not missing_metadata.empty:
        raise ValueError(
            "Coordinates not found for IBGE codes: "
            f"{missing_metadata['ibge_code'].tolist()}"
        )

    metadata_df["latitude"] = pd.to_numeric(
        metadata_df["latitude"],
        errors="raise",
    )

    metadata_df["longitude"] = pd.to_numeric(
        metadata_df["longitude"],
        errors="raise",
    )

    metadata_df.insert(1, "state", "SP")

    # Protect the existing metadata and ERA5 municipality mapping.
    if output_path.exists():
        existing_df = pd.read_csv(
            output_path,
            dtype={"ibge_code": "string"},
        )

        existing_columns = {
            "ibge_code",
            "municipality",
            "latitude",
            "longitude",
        }

        if not existing_columns.issubset(existing_df.columns):
            raise ValueError(
                "Existing metadata is missing required columns."
            )

        existing_df["ibge_code"] = (
            existing_df["ibge_code"].str.strip()
        )

        if existing_df["ibge_code"].duplicated().any():
            raise ValueError(
                "Existing metadata contains duplicate IBGE codes."
            )

        old_codes = set(existing_df["ibge_code"])
        new_codes = set(metadata_df["ibge_code"])

        if old_codes != new_codes:
            raise ValueError(
                "Municipality coverage differs from existing metadata. "
                f"Added codes: {sorted(new_codes - old_codes)}; "
                f"removed codes: {sorted(old_codes - new_codes)}. "
                "Existing metadata was not overwritten."
            )

        comparison = metadata_df.merge(
            existing_df[
                [
                    "ibge_code",
                    "municipality",
                    "latitude",
                    "longitude",
                ]
            ],
            on="ibge_code",
            how="inner",
            validate="one_to_one",
            suffixes=("", "_existing"),
        )

        for coordinate in ("latitude", "longitude"):
            old_values = pd.to_numeric(
                comparison[f"{coordinate}_existing"],
                errors="raise",
            )

            new_values = pd.to_numeric(
                comparison[coordinate],
                errors="raise",
            )

            changed = (
                old_values.isna()
                | new_values.isna()
                | ((new_values - old_values).abs() > 1e-6)
            )

            if changed.any():
                raise ValueError(
                    f"Existing {coordinate} differs for IBGE codes: "
                    f"{comparison.loc[changed, 'ibge_code'].tolist()}. "
                    "Existing metadata was not overwritten."
                )

        # Preserve the names already used by the existing metadata.
        existing_names = existing_df.set_index(
            "ibge_code"
        )["municipality"]

        metadata_df["municipality"] = (
            metadata_df["ibge_code"].map(existing_names)
        )

        print(
            "Existing municipality codes and coordinates verified; "
            "preserving existing municipality names."
        )

    # Preserve the established metadata column order.
    metadata_df["ibge_code"] = (
        metadata_df["ibge_code"].astype("Int64")
    )

    metadata_df = (
        metadata_df[
            [
                "municipality",
                "state",
                "ibge_code",
                "latitude",
                "longitude",
            ]
        ]
        .sort_values("municipality")
        .reset_index(drop=True)
    )

    if metadata_df["municipality"].duplicated().any():
        raise ValueError(
            "Duplicate municipality names found in metadata."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata_df = metadata_df.sort_values("ibge_code").reset_index(drop=True)
    
    metadata_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Saved metadata for {len(metadata_df)} municipalities "
        f"to {output_path}"
    )

    return metadata_df


if __name__ == "__main__":
    create_sp_metadata()
