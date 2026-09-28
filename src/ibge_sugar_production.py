"""Process IBGE SIDRA Table 5457 into one municipality-year CSV."""

from pathlib import Path

import pandas as pd

RAW_PATH = Path("data/raw/tabela5457.xlsx")
PROCESSED_PATH = Path("data/processed/sp_sugarcane_annual.csv")


def _read_variable(raw_path: Path, sheet: str, value_column: str):
    raw = pd.read_excel(raw_path, sheet_name=sheet, header=None, dtype=str)
    if raw.shape[0] < 7 or raw.shape[1] < 4:
        raise ValueError(f"Unexpected layout in sheet {sheet!r}.")
    if raw.iloc[2, :3].tolist() != ["Nível", "Cód.", "Unidade da Federação e Município"]:
        raise ValueError(f"Unexpected geographic headers in sheet {sheet!r}.")

    year_columns = {}
    for col in range(3, raw.shape[1]):
        label = raw.iat[3, col]
        if pd.isna(label):
            continue
        year_text = str(label).strip()
        if not (year_text.isdigit() and len(year_text) == 4):
            raise ValueError(f"Unexpected year label {label!r} in {sheet!r}.")
        if str(raw.iat[4, col]).strip() != "Cana-de-açúcar":
            raise ValueError(f"Unexpected crop for {year_text} in {sheet!r}.")
        year = int(year_text)
        if year in year_columns:
            raise ValueError(f"Duplicate year {year} in {sheet!r}.")
        year_columns[year] = col
    if not year_columns:
        raise ValueError(f"No year columns in {sheet!r}.")

    data = raw.loc[raw.iloc[:, 0].isin(["MU", "UF"])].copy()
    if data.empty:
        raise ValueError(f"No geographic records in {sheet!r}.")
    code = data.iloc[:, 1].astype("string").str.strip()
    name = data.iloc[:, 2].astype("string").str.strip()
    pieces = []
    for year, col in sorted(year_columns.items()):
        original = data.iloc[:, col].astype("string").str.strip()
        # '-' and '...' are different IBGE symbols; neither is assumed to be zero.
        missing = original.isna() | original.isin(["-", "...", "..", "X", "x", ""])
        numbers = pd.to_numeric(original.mask(missing), errors="coerce")
        invalid = ~missing & numbers.isna()
        if invalid.any():
            raise ValueError(f"Unrecognized {value_column} in {sheet!r}, year {year}.")
        if numbers.lt(0).any():
            raise ValueError(f"Negative {value_column} in {sheet!r}, year {year}.")
        pieces.append(pd.DataFrame({
            "level": data.iloc[:, 0].to_numpy(),
            "ibge_code": code.to_numpy(),
            "municipality": name.to_numpy(),
            "year": year,
            value_column: numbers.to_numpy(),
        }))
    result = pd.concat(pieces, ignore_index=True)
    state = result.loc[(result["level"] == "UF") & (result["ibge_code"] == "35")]
    municipality = result.loc[result["level"] == "MU"].copy()
    if len(state) != len(year_columns) or municipality.empty:
        raise ValueError(f"Expected one São Paulo state total per year in {sheet!r}.")
    if municipality["ibge_code"].isna().any() or ~municipality["ibge_code"].str.fullmatch(r"35\d{5}").all():
        raise ValueError(f"Invalid São Paulo municipality code in {sheet!r}.")
    if municipality.duplicated(["ibge_code", "year"]).any():
        raise ValueError(f"Duplicate municipality-year record in {sheet!r}.")
    municipality["municipality"] = municipality["municipality"].str.replace(
        r"\s*\(SP\)$", "", regex=True
    ).str.strip()
    return (municipality[["ibge_code", "municipality", "year", value_column]],
            state[["year", value_column]])


def process_ibge_sugar_production(
    raw_path: Path = RAW_PATH,
    output_path: Path = PROCESSED_PATH,
) -> pd.DataFrame:
    """Create one annual SP sugarcane table from IBGE production and harvested area."""
    if not raw_path.is_file():
        raise FileNotFoundError(f"IBGE dataset not found: {raw_path}")

    production, state_production = _read_variable(
        raw_path, "Quantidade produzida", "production_tonnes"
    )
    area, state_area = _read_variable(raw_path, "Área colhida", "harvested_area_ha")
    annual = production.merge(
        area, on=["ibge_code", "year"], how="outer", validate="one_to_one",
        suffixes=("_production", "_area"), indicator=True,
    )
    if not annual["_merge"].eq("both").all():
        raise ValueError("Area and production have different municipality-year records.")
    if not annual["municipality_production"].eq(annual["municipality_area"]).all():
        raise ValueError("Municipality names differ between area and production sheets.")
    annual = annual.rename(columns={"municipality_production": "municipality"}).drop(
        columns=["municipality_area", "_merge"]
    )

    # Check municipality aggregates against the IBGE São Paulo totals before weighting.
    for column, state in [
        ("production_tonnes", state_production),
        ("harvested_area_ha", state_area),
    ]:
        expected = state.set_index("year")[column].sort_index()
        observed = annual.groupby("year")[column].sum(min_count=1).sort_index()
        if not observed.index.equals(expected.index) or not observed.notna().all() or not expected.notna().all():
            raise ValueError(f"Missing state or municipal totals for {column}.")
        relative_difference = (observed - expected).abs() / expected.where(expected.ne(0))
        # A small discrepancy in 1998 and 2006 exists in the supplied IBGE export.
        # Accept up to 0.1%, but report it rather than implying exact reconciliation.
        if relative_difference.gt(0.001).any():
            years = observed.index[relative_difference.gt(0.001)].tolist()
            raise ValueError(f"State reconciliation exceeds 0.1% for {column}: {years}")
        for year in observed.index[relative_difference.gt(0.0000001)]:
            print(f"WARNING: {column} {year}: municipality sum={observed[year]:,.0f}, "
                  f"IBGE state total={expected[year]:,.0f}; "
                  f"difference={relative_difference[year]:.4%}")

    area_total = annual.groupby("year")["harvested_area_ha"].transform("sum")
    annual["area_weight"] = annual["harvested_area_ha"] / area_total
    annual["yield_tch"] = annual["production_tonnes"] / annual["harvested_area_ha"].where(
        annual["harvested_area_ha"].gt(0)
    )
    annual = annual[[
        "ibge_code", "municipality", "year", "harvested_area_ha",
        "production_tonnes", "yield_tch", "area_weight",
    ]].sort_values(["year", "ibge_code"]).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    annual.to_csv(output_path, index=False)
    print(f"Saved {len(annual):,} municipality-year records to {output_path}")
    print(f"Coverage: {annual['year'].min()}–{annual['year'].max()}, "
          f"{annual['ibge_code'].nunique()} municipalities")
    return annual


def main() -> None:
    process_ibge_sugar_production()


if __name__ == "__main__":
    main()
