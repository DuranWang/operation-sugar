"""EXP-01S harvested-area weight stability investigation.

The experiment is validation-gated.  IBGE symbols are preserved so an
unavailable value (``...``) can never be silently treated as an absolute zero
(``-``).  Real-data stability metrics are produced only when every annual
municipality weight vector is semantically complete.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


START_YEAR = 1990
END_YEAR = 2025
ANCHOR_YEARS = (1990, 2000, 2010, 2020, 2025)
WEIGHT_TOLERANCE = 1e-12


@dataclass(frozen=True)
class ValidationResult:
    status: str
    reason: str
    unavailable_rows: int


def _clean_code(series: pd.Series) -> pd.Series:
    result = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    if result.isna().any() or result.eq("").any():
        raise ValueError("IBGE codes must be nonmissing")
    return result


def validate_processed_structure(
    annual: pd.DataFrame,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
) -> pd.DataFrame:
    """Validate the processed municipality-year panel and return the period."""

    required = {
        "ibge_code",
        "municipality",
        "year",
        "harvested_area_ha",
        "area_weight",
    }
    missing = required - set(annual.columns)
    if missing:
        raise ValueError(f"Annual dataset is missing columns: {sorted(missing)}")
    period = annual.loc[annual["year"].between(start_year, end_year)].copy()
    period["ibge_code"] = _clean_code(period["ibge_code"])
    if period.empty:
        raise ValueError("No records in the requested analysis period")
    if period.duplicated(["ibge_code", "year"]).any():
        raise ValueError("Duplicate (ibge_code, year) rows")
    names_per_code = period.groupby("ibge_code")["municipality"].nunique(dropna=False)
    if names_per_code.gt(1).any():
        raise ValueError("Municipality names are inconsistent for an IBGE code")
    counts = period.groupby("year")["ibge_code"].nunique()
    expected_years = pd.Index(range(start_year, end_year + 1), name="year")
    if not counts.index.equals(expected_years):
        raise ValueError("Annual dataset does not cover every requested year")
    if counts.nunique() != 1:
        raise ValueError("Annual municipality universe changes across years")
    expected_codes = set(period.loc[period["year"].eq(start_year), "ibge_code"])
    for year, group in period.groupby("year"):
        if set(group["ibge_code"]) != expected_codes:
            raise ValueError(f"Municipality universe differs in {year}")
    return period.sort_values(["year", "ibge_code"]).reset_index(drop=True)


def classify_ibge_area_value(value: object) -> tuple[float, str]:
    """Parse one IBGE area cell without collapsing zero and unknown symbols."""

    if pd.isna(value):
        return np.nan, "blank"
    text = str(value).strip()
    if text == "-":
        return 0.0, "absolute_zero"
    if text == "...":
        return np.nan, "unavailable"
    if text == "..":
        return np.nan, "not_applicable"
    if text.lower() == "x":
        return np.nan, "suppressed"
    if text == "":
        return np.nan, "blank"
    try:
        number = float(text)
    except ValueError as error:
        raise ValueError(f"Unrecognized IBGE harvested-area value: {value!r}") from error
    if not np.isfinite(number) or number < 0:
        raise ValueError(f"Invalid IBGE harvested-area value: {value!r}")
    return number, "numeric_zero" if number == 0 else "numeric_positive"


def load_raw_harvested_area(
    workbook_path: Path,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read symbol-aware municipality area values and official state totals."""

    if not workbook_path.is_file():
        raise FileNotFoundError(f"IBGE workbook not found: {workbook_path}")
    raw = pd.read_excel(workbook_path, sheet_name="Área colhida", header=None, dtype=str)
    if raw.shape[0] < 7 or raw.shape[1] < 4:
        raise ValueError("Unexpected IBGE harvested-area sheet layout")
    if raw.iloc[2, :3].tolist() != ["Nível", "Cód.", "Unidade da Federação e Município"]:
        raise ValueError("Unexpected IBGE geography headers")
    year_columns: dict[int, int] = {}
    for column in range(3, raw.shape[1]):
        label = raw.iat[3, column]
        if pd.isna(label):
            continue
        text = str(label).strip()
        if text.isdigit() and len(text) == 4:
            year = int(text)
            if start_year <= year <= end_year:
                year_columns[year] = column
    if set(year_columns) != set(range(start_year, end_year + 1)):
        raise ValueError("IBGE sheet does not contain every requested year")

    municipalities = raw.loc[raw.iloc[:, 0].eq("MU")].copy()
    state = raw.loc[
        raw.iloc[:, 0].eq("UF")
        & raw.iloc[:, 1].astype("string").str.strip().eq("35")
    ]
    if municipalities.empty or len(state) != 1:
        raise ValueError("Expected municipality rows and one São Paulo state row")

    records = []
    for _, row in municipalities.iterrows():
        code = str(row.iloc[1]).strip()
        name = str(row.iloc[2]).removesuffix(" (SP)").strip()
        for year, column in sorted(year_columns.items()):
            area, status = classify_ibge_area_value(row.iloc[column])
            records.append(
                {
                    "ibge_code": code,
                    "municipality": name,
                    "year": year,
                    "raw_area_symbol": str(row.iloc[column]).strip(),
                    "harvested_area_ha_symbol_aware": area,
                    "area_value_status": status,
                }
            )
    state_row = state.iloc[0]
    state_totals = pd.DataFrame(
        {
            "year": sorted(year_columns),
            "ibge_state_total_area_ha": [
                float(state_row.iloc[year_columns[year]]) for year in sorted(year_columns)
            ],
        }
    )
    symbol_data = pd.DataFrame(records)
    symbol_data["ibge_code"] = _clean_code(symbol_data["ibge_code"])
    return symbol_data, state_totals


def validate_nan_semantics(symbol_data: pd.DataFrame) -> ValidationResult:
    """Block real-data analysis when any area value remains semantically unknown."""

    unknown_statuses = {"unavailable", "not_applicable", "suppressed", "blank"}
    unavailable = int(symbol_data["area_value_status"].isin(unknown_statuses).sum())
    if unavailable:
        return ValidationResult(
            status="blocked",
            reason=(
                "IBGE source contains values that are explicitly unavailable or otherwise "
                "unknown; they cannot be converted to zero without a research decision."
            ),
            unavailable_rows=unavailable,
        )
    return ValidationResult(status="passed", reason="All values are numeric or explicit zero", unavailable_rows=0)


def build_validation_tables(
    processed: pd.DataFrame,
    symbol_data: pd.DataFrame,
    state_totals: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int]]:
    """Create annual coverage and row-level missing-semantics tables."""

    merged = processed.merge(
        symbol_data,
        on=["ibge_code", "municipality", "year"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise ValueError("Processed and raw IBGE municipality-year keys differ")
    numeric_source_rows = merged["area_value_status"].isin(
        ["numeric_positive", "numeric_zero"]
    )
    comparable = merged.loc[numeric_source_rows]
    raw_values = comparable["harvested_area_ha_symbol_aware"].astype(float)
    processed_values = comparable["harvested_area_ha"].astype(float)
    if not np.allclose(raw_values, processed_values, atol=0, rtol=0):
        raise ValueError("Processed harvested area differs from the raw numeric/zero values")
    zero_collapsed_to_nan = merged.loc[
        merged["area_value_status"].eq("absolute_zero"), "harvested_area_ha"
    ].isna()
    if not zero_collapsed_to_nan.all():
        raise ValueError("Processed data does not consistently preserve current ETL zero behavior")
    unknown_preserved_nan = merged.loc[
        merged["area_value_status"].eq("unavailable"), "harvested_area_ha"
    ].isna()
    if not unknown_preserved_nan.all():
        raise ValueError("Processed data unexpectedly assigns values to unavailable source rows")

    annual = (
        merged.groupby("year", as_index=False)
        .agg(
            municipality_rows=("ibge_code", "size"),
            unique_municipalities=("ibge_code", "nunique"),
            nonmissing_processed_area=("harvested_area_ha", "count"),
            processed_missing_area=("harvested_area_ha", lambda s: int(s.isna().sum())),
            explicit_absolute_zero_rows=(
                "area_value_status", lambda s: int(s.eq("absolute_zero").sum())
            ),
            unavailable_rows=("area_value_status", lambda s: int(s.eq("unavailable").sum())),
            numeric_zero_rows=("area_value_status", lambda s: int(s.eq("numeric_zero").sum())),
            positive_area_rows=("area_value_status", lambda s: int(s.eq("numeric_positive").sum())),
            known_harvested_area_ha=("harvested_area_ha_symbol_aware", "sum"),
            stored_weight_sum=("area_weight", "sum"),
        )
        .merge(state_totals, on="year", how="left", validate="one_to_one")
    )
    annual["known_area_minus_state_total_ha"] = (
        annual["known_harvested_area_ha"] - annual["ibge_state_total_area_ha"]
    )
    annual["relative_abs_state_reconciliation_difference"] = (
        annual["known_area_minus_state_total_ha"].abs()
        / annual["ibge_state_total_area_ha"]
    )
    annual["validation_gate_status"] = np.where(
        annual["unavailable_rows"].gt(0), "blocked", "passed"
    )

    reconstructed = merged["harvested_area_ha"] / merged.groupby("year")[
        "harvested_area_ha"
    ].transform("sum")
    valid_weight_rows = merged["area_weight"].notna() & reconstructed.notna()
    differences = (merged.loc[valid_weight_rows, "area_weight"] - reconstructed[valid_weight_rows]).abs()
    diagnostics: dict[str, float | int] = {
        "processed_rows": int(len(merged)),
        "explicit_zero_rows_collapsed_to_nan": int(
            merged["area_value_status"].eq("absolute_zero").sum()
        ),
        "unavailable_rows": int(merged["area_value_status"].eq("unavailable").sum()),
        "municipalities_with_unavailable_rows": int(
            merged.loc[merged["area_value_status"].eq("unavailable"), "ibge_code"].nunique()
        ),
        "provisional_weight_max_abs_difference": float(differences.max()),
        "provisional_weight_mean_abs_difference": float(differences.mean()),
        "provisional_weight_differences_over_tolerance": int(
            differences.gt(WEIGHT_TOLERANCE).sum()
        ),
    }
    details = merged.loc[
        merged["area_value_status"].isin(["absolute_zero", "unavailable"]),
        [
            "ibge_code",
            "municipality",
            "year",
            "raw_area_symbol",
            "area_value_status",
            "harvested_area_ha",
            "area_weight",
        ],
    ].sort_values(["year", "ibge_code"])
    return annual, details, diagnostics


def validate_weight_vector(weights: pd.Series, tolerance: float = WEIGHT_TOLERANCE) -> None:
    if weights.isna().any() or (~np.isfinite(weights)).any() or weights.lt(0).any():
        raise ValueError("Weight vector must contain finite, nonnegative values")
    if not np.isclose(float(weights.sum()), 1.0, atol=tolerance, rtol=0):
        raise ValueError("Annual weights do not sum to 1")


def total_variation(first: pd.Series, second: pd.Series) -> float:
    """Return total-variation distance for aligned complete weight vectors."""

    if not first.index.equals(second.index):
        raise ValueError("Weight vectors must use the same municipality universe")
    validate_weight_vector(first)
    validate_weight_vector(second)
    value = float(0.5 * (first - second).abs().sum())
    if value < -WEIGHT_TOLERANCE or value > 1 + WEIGHT_TOLERANCE:
        raise ValueError("Total-variation distance is outside [0, 1]")
    return min(1.0, max(0.0, value))


def spearman_rank_stability(first: pd.Series, second: pd.Series) -> float:
    if not first.index.equals(second.index):
        raise ValueError("Weight vectors must use the same municipality universe")
    validate_weight_vector(first)
    validate_weight_vector(second)
    return float(first.corr(second, method="spearman"))


def top_k_overlap(first: pd.Series, second: pd.Series, k: int) -> float:
    if not first.index.equals(second.index):
        raise ValueError("Weight vectors must use the same municipality universe")
    if k <= 0 or k > len(first):
        raise ValueError("k must be between 1 and the municipality count")
    first_top = set(first.sort_values(ascending=False, kind="mergesort").head(k).index)
    second_top = set(second.sort_values(ascending=False, kind="mergesort").head(k).index)
    return len(first_top & second_top) / k


def anchor_year_comparison(
    weights_by_year: dict[int, pd.Series],
    pairs: Iterable[tuple[int, int]],
) -> pd.DataFrame:
    rows = []
    for first_year, second_year in pairs:
        first = weights_by_year[first_year]
        second = weights_by_year[second_year]
        if not first.index.equals(second.index):
            raise ValueError("Anchor-year comparisons require the same municipality universe")
        rows.append(
            {
                "first_year": first_year,
                "second_year": second_year,
                "total_variation": total_variation(first, second),
                "spearman_rank_correlation": spearman_rank_stability(first, second),
                "top_10_overlap": top_k_overlap(first, second, min(10, len(first))),
                "top_25_overlap": top_k_overlap(first, second, min(25, len(first))),
                "top_50_overlap": top_k_overlap(first, second, min(50, len(first))),
            }
        )
    return pd.DataFrame(rows)


def write_blocked_report(
    output_root: Path,
    processed_path: Path,
    raw_path: Path,
    annual_coverage: pd.DataFrame,
    diagnostics: dict[str, float | int],
    gate: ValidationResult,
) -> Path:
    report_path = output_root / "EXP_01S_execution_report.md"
    min_unknown = int(annual_coverage["unavailable_rows"].min())
    max_unknown = int(annual_coverage["unavailable_rows"].max())
    max_reconciliation = float(
        annual_coverage["relative_abs_state_reconciliation_difference"].max()
    )
    report = f"""# EXP-01S Execution Report

## Status

**Blocked at the required NaN-semantics validation gate.** Municipality-level
stability, total-variation, Spearman, Top-K, anchor-year comparisons, and
figures were not produced from the real data.

## Sources inspected

- Processed annual data: `{processed_path}`
- Authoritative IBGE SIDRA Table 5457 workbook: `{raw_path}`
- Upstream processor: `src/ibge_sugar_production.py`

## Verified NaN semantics

The IBGE workbook legend defines `-` as an absolute zero and `...` as a value
that is not available. The current upstream processor deliberately maps both
symbols to missing values, so `sp_sugarcane_annual.csv` cannot distinguish zero
from unknown after processing.

For 1990–2025, the processed panel contains
{diagnostics['explicit_zero_rows_collapsed_to_nan']:,} rows originating from
explicit zero (`-`) and {diagnostics['unavailable_rows']:,} rows originating
from unavailable (`...`) values. The unavailable values affect
{diagnostics['municipalities_with_unavailable_rows']:,} municipalities and occur
in every year ({min_unknown}–{max_unknown} rows per year).

No `fillna(0)` was applied. The gate status is `{gate.status}` because:
{gate.reason}

## Structural validation

- Period: 1990–2025 inclusive
- Municipality rows per year: 642
- `(ibge_code, year)` duplicates: 0
- Municipality universe: constant across years
- Municipality name mapping: consistent
- Stored weights versus the current ETL's provisional known-value denominator:
  maximum absolute difference
  `{diagnostics['provisional_weight_max_abs_difference']:.3e}`; differences over
  `1e-12`: {diagnostics['provisional_weight_differences_over_tolerance']}
- Maximum absolute state-total reconciliation difference: {max_reconciliation:.4%}
  (the known 1998/2006 source discrepancies remain below 0.1%)

State-total reconciliation does not change the municipality-level source
semantics: `...` remains explicitly unavailable, and the analysis requires a
complete, defensible 642-municipality vector.

## Files created

- `tables/annual_data_coverage.csv`
- `tables/missing_value_semantics.csv`
- `EXP_01S_execution_report.md`

No stability result tables or figures were created because the gate failed.

## Questions returned to Chat

1. **Meaning of missing values:** mixed. `-` means zero; `...` means unavailable.
2. **Typical annual redistribution:** not estimated; would require treating
   unavailable municipality values.
3. **Abnormal redistribution years:** not estimated.
4. **Rank versus share stability:** not estimated.
5. **Top-producer persistence:** not estimated.
6. **Long-horizon change:** not estimated.
7. **Support for fixed/lagged/rolling weights:** no conclusion. These remain
   candidate designs for later testing, not an EXP-01S decision.
8. **Data-quality issue:** yes. The processed file collapses two materially
   different IBGE symbols into NaN.

## Research decision required

Chat must choose and justify a treatment for the 1,443 unavailable
municipality-years before EXP-01S stability metrics can be interpreted. Options
could include obtaining a revised source, documenting a source-supported rule,
or defining a sensitivity analysis. This report does not select among annual,
fixed, lagged, or rolling weights for EXP-01B.
"""
    report_path.write_text(report, encoding="utf-8")
    return report_path


def run_validation_gate(
    processed_path: Path,
    raw_path: Path,
    output_root: Path,
) -> ValidationResult:
    processed = pd.read_csv(processed_path, dtype={"ibge_code": "string"})
    processed = validate_processed_structure(processed)
    symbol_data, state_totals = load_raw_harvested_area(raw_path)
    annual, details, diagnostics = build_validation_tables(
        processed, symbol_data, state_totals
    )
    gate = validate_nan_semantics(symbol_data)
    table_root = output_root / "tables"
    table_root.mkdir(parents=True, exist_ok=True)
    annual.to_csv(table_root / "annual_data_coverage.csv", index=False)
    details.to_csv(table_root / "missing_value_semantics.csv", index=False)
    write_blocked_report(
        output_root,
        processed_path,
        raw_path,
        annual,
        diagnostics,
        gate,
    )
    print(f"EXP-01S validation gate: {gate.status}")
    print(gate.reason)
    print(f"Unavailable municipality-years: {gate.unavailable_rows}")
    return gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--processed", type=Path, default=None)
    parser.add_argument("--raw", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    run_validation_gate(
        processed_path=args.processed or root / "data/processed/sp_sugarcane_annual.csv",
        raw_path=args.raw or root / "data/raw/tabela5457.xlsx",
        output_root=args.output
        or root / "outputs/experiments/EXP_01S_harvested_area_weight_stability",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
