"""Reproduce EXP-03 March soil-moisture depth regimes and support summaries.

This module formalizes the completed Step 4A/4B descriptive analysis.  It
consumes existing EXP-03 grid-specific correlations and EXP-02B support
artifacts; it does not recalculate yield-weather correlations or infer cause.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


MARCH_RELATIVE_MONTH = -1
MINIMUM_PAIRED_YEARS = 15
MOISTURE_VARIABLES = [
    "soil_moisture_0_to_7cm_m3_m3",
    "soil_moisture_7_to_28cm_m3_m3",
    "soil_moisture_28_to_100cm_m3_m3",
    "soil_moisture_100_to_255cm_m3_m3",
]
SURFACE_VARIABLE = MOISTURE_VARIABLES[0]
DEEP_VARIABLES = MOISTURE_VARIABLES[2:]
RAINFALL_VARIABLE = "nasa_total_rainfall_mm"
FROZEN_REGIME_COUNTS = {
    "positive_positive": 42,
    "depth_recovery": 19,
    "persistent_negative": 13,
    "reverse": 2,
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    """Render a compact Markdown table without an optional dependency."""

    if frame.empty:
        return "_(no rows)_"
    formatted = frame.copy()
    for column in formatted.select_dtypes(include=["float"]).columns:
        formatted[column] = formatted[column].map(
            lambda value: "" if pd.isna(value) else f"{value:.{digits}f}"
        )
    headers = [str(column) for column in formatted.columns]
    rows = [[str(value) for value in row] for row in formatted.itertuples(index=False, name=None)]
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
        *["| " + " | ".join(row) + " |" for row in rows],
    ])


def classify_depth_regimes(march_correlations: pd.DataFrame) -> pd.DataFrame:
    """Derive the four frozen regimes from March grid-specific correlations."""

    required = {
        "grid_id", "relative_month_index", "weather_variable", "usable",
        "spearman_rho", "paired_years",
    }
    missing = required - set(march_correlations.columns)
    if missing:
        raise ValueError(f"Missing correlation columns: {sorted(missing)}")

    subset = march_correlations.loc[
        march_correlations.relative_month_index.eq(MARCH_RELATIVE_MONTH)
        & march_correlations.weather_variable.isin(MOISTURE_VARIABLES)
        & march_correlations.usable.astype(bool)
        & march_correlations.paired_years.ge(MINIMUM_PAIRED_YEARS)
    ].copy()
    if subset.duplicated(["grid_id", "weather_variable"]).any():
        raise ValueError("Duplicate March grid-variable correlation rows")

    pivot = subset.pivot(index="grid_id", columns="weather_variable", values="spearman_rho")
    absent = set(MOISTURE_VARIABLES) - set(pivot.columns)
    if absent or pivot[MOISTURE_VARIABLES].isna().any().any():
        raise ValueError(f"Incomplete usable March moisture correlations: {sorted(absent)}")

    result = pivot[MOISTURE_VARIABLES].reset_index().rename(columns={
        SURFACE_VARIABLE: "surface_0_7_rho",
        MOISTURE_VARIABLES[1]: "upper_7_28_rho",
        MOISTURE_VARIABLES[2]: "deep_28_100_rho",
        MOISTURE_VARIABLES[3]: "deep_100_255_rho",
    })
    paired_years = subset.groupby("grid_id", as_index=False).paired_years.min()
    result = result.merge(paired_years, on="grid_id", validate="one_to_one")
    result["deep_rho"] = result[["deep_28_100_rho", "deep_100_255_rho"]].mean(axis=1)
    surface = result.surface_0_7_rho
    deep = result.deep_rho
    result["regime"] = np.select(
        [
            surface.gt(0) & deep.gt(0),
            surface.lt(0) & deep.gt(0),
            surface.lt(0) & deep.lt(0),
            surface.gt(0) & deep.lt(0),
        ],
        ["positive_positive", "depth_recovery", "persistent_negative", "reverse"],
        default="boundary_zero",
    )
    result["surface_sign"] = np.sign(surface).astype(int)
    result["deep_sign"] = np.sign(deep).astype(int)
    return result.sort_values("grid_id").reset_index(drop=True)


def summarize_depth_relationships(regimes: pd.DataFrame) -> pd.DataFrame:
    """Summarize all four native ERA5 moisture relationships by regime."""

    long = regimes.melt(
        id_vars=["grid_id", "regime"],
        value_vars=[
            "surface_0_7_rho", "upper_7_28_rho",
            "deep_28_100_rho", "deep_100_255_rho", "deep_rho",
        ],
        var_name="relationship", value_name="spearman_rho",
    )
    return long.groupby(["regime", "relationship"], as_index=False).agg(
        n_grids=("grid_id", "nunique"),
        mean_rho=("spearman_rho", "mean"),
        median_rho=("spearman_rho", "median"),
        q25_rho=("spearman_rho", lambda values: values.quantile(.25)),
        q75_rho=("spearman_rho", lambda values: values.quantile(.75)),
        minimum_rho=("spearman_rho", "min"),
        maximum_rho=("spearman_rho", "max"),
        pct_positive=("spearman_rho", lambda values: values.gt(0).mean()),
        pct_negative=("spearman_rho", lambda values: values.lt(0).mean()),
    )


def grid_geography(mapping: pd.DataFrame) -> pd.DataFrame:
    """Return one canonical coordinate and municipality count per grid."""

    required = {"grid_id", "ibge_code", "grid_latitude", "grid_longitude"}
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"Missing municipality mapping columns: {sorted(missing)}")
    coordinate_counts = mapping.groupby("grid_id")[["grid_latitude", "grid_longitude"]].nunique()
    if coordinate_counts.gt(1).any().any():
        raise ValueError("A grid has inconsistent coordinates in the municipality mapping")
    return mapping.groupby("grid_id", as_index=False).agg(
        grid_latitude=("grid_latitude", "first"),
        grid_longitude=("grid_longitude", "first"),
        eligible_municipalities=("ibge_code", "nunique"),
    )


def summarize_geography(regimes: pd.DataFrame, geography: pd.DataFrame) -> pd.DataFrame:
    merged = regimes[["grid_id", "regime", "paired_years"]].merge(
        geography, on="grid_id", how="left", validate="one_to_one"
    )
    if merged[["grid_latitude", "grid_longitude", "eligible_municipalities"]].isna().any().any():
        raise ValueError("Missing geography/support mapping for a classified grid")
    return merged.groupby("regime", as_index=False).agg(
        n_grids=("grid_id", "nunique"),
        latitude_mean=("grid_latitude", "mean"),
        latitude_median=("grid_latitude", "median"),
        latitude_q25=("grid_latitude", lambda values: values.quantile(.25)),
        latitude_q75=("grid_latitude", lambda values: values.quantile(.75)),
        longitude_mean=("grid_longitude", "mean"),
        longitude_median=("grid_longitude", "median"),
        longitude_q25=("grid_longitude", lambda values: values.quantile(.25)),
        longitude_q75=("grid_longitude", lambda values: values.quantile(.75)),
        municipality_count_mean=("eligible_municipalities", "mean"),
        municipality_count_median=("eligible_municipalities", "median"),
    )


def summarize_rainfall(
    correlations: pd.DataFrame, regimes: pd.DataFrame,
) -> pd.DataFrame:
    rain = correlations.loc[
        correlations.relative_month_index.eq(MARCH_RELATIVE_MONTH)
        & correlations.weather_variable.eq(RAINFALL_VARIABLE)
        & correlations.usable.astype(bool),
        ["grid_id", "spearman_rho", "paired_years"],
    ].copy()
    rain = rain.merge(regimes[["grid_id", "regime"]], on="grid_id", validate="one_to_one")
    return rain.groupby("regime", as_index=False).agg(
        n_grids=("grid_id", "nunique"),
        paired_years_min=("paired_years", "min"),
        paired_years_median=("paired_years", "median"),
        rainfall_rho_mean=("spearman_rho", "mean"),
        rainfall_rho_median=("spearman_rho", "median"),
        rainfall_rho_q25=("spearman_rho", lambda values: values.quantile(.25)),
        rainfall_rho_q75=("spearman_rho", lambda values: values.quantile(.75)),
        pct_rainfall_positive=("spearman_rho", lambda values: values.gt(0).mean()),
        pct_rainfall_negative=("spearman_rho", lambda values: values.lt(0).mean()),
    )


def production_support_by_grid(
    grid_results: pd.DataFrame, weight_details: pd.DataFrame,
    fixed_weights: pd.DataFrame, geography: pd.DataFrame,
) -> pd.DataFrame:
    """Derive existing EXP-02B production-support summaries at grid level."""

    grids = grid_results.loc[
        grid_results.specification.eq("p50_10")
        & grid_results.valid_grid_residual.astype(bool)
    ].copy()
    annual_weights = weight_details.groupby(["grid_id", "year"], as_index=False).agg(
        weight_sum=("actual_weight", "sum"),
        hhi=("actual_weight", lambda values: float(np.square(values).sum())),
        dominant_municipality_share=("actual_weight", "max"),
    )
    if not np.allclose(annual_weights.weight_sum, 1.0, atol=1e-10):
        raise ValueError("EXP-02B actual weights do not sum to one by grid-year")
    dominant_reference = fixed_weights.groupby("grid_id", as_index=False).agg(
        dominant_fixed_reference_share=("fixed_reference_weight_grid_normalized", "max")
    )
    support = grids.groupby("grid_id", as_index=False).agg(
        valid_grid_years=("year", "nunique"),
        mean_annual_harvested_area_ha=("actual_weight_denominator_ha", "mean"),
        median_annual_harvested_area_ha=("actual_weight_denominator_ha", "median"),
    ).merge(
        annual_weights.groupby("grid_id", as_index=False).agg(
            mean_hhi=("hhi", "mean"),
            median_hhi=("hhi", "median"),
            mean_actual_dominant_share=("dominant_municipality_share", "mean"),
            median_actual_dominant_share=("dominant_municipality_share", "median"),
        ), on="grid_id", how="left", validate="one_to_one",
    ).merge(
        dominant_reference, on="grid_id", how="left", validate="one_to_one",
    ).merge(
        geography[["grid_id", "eligible_municipalities"]],
        on="grid_id", how="left", validate="one_to_one",
    )
    return support


def summarize_production_support(
    regimes: pd.DataFrame, support: pd.DataFrame,
) -> pd.DataFrame:
    merged = regimes[["grid_id", "regime", "paired_years"]].merge(
        support, on="grid_id", how="left", validate="one_to_one"
    )
    required = [
        "eligible_municipalities", "valid_grid_years", "mean_annual_harvested_area_ha",
        "mean_hhi", "dominant_fixed_reference_share",
    ]
    if merged[required].isna().any().any():
        raise ValueError("Missing production-support values for a classified grid")
    return merged.groupby("regime", as_index=False).agg(
        n_grids=("grid_id", "nunique"),
        municipality_count_mean=("eligible_municipalities", "mean"),
        municipality_count_median=("eligible_municipalities", "median"),
        valid_grid_years_min=("valid_grid_years", "min"),
        valid_grid_years_median=("valid_grid_years", "median"),
        paired_years_min=("paired_years", "min"),
        paired_years_median=("paired_years", "median"),
        harvested_area_mean_ha=("mean_annual_harvested_area_ha", "mean"),
        harvested_area_median_ha=("mean_annual_harvested_area_ha", "median"),
        hhi_mean=("mean_hhi", "mean"),
        hhi_median=("mean_hhi", "median"),
        dominant_share_mean=("dominant_fixed_reference_share", "mean"),
        dominant_share_median=("dominant_fixed_reference_share", "median"),
    )


def validate_frozen_regimes(regimes: pd.DataFrame) -> None:
    counts = regimes.regime.value_counts().to_dict()
    if len(regimes) != 76 or counts != FROZEN_REGIME_COUNTS:
        raise ValueError(
            "Reconstructed March regimes disagree with frozen research state: "
            f"n={len(regimes)}, counts={counts}, expected={FROZEN_REGIME_COUNTS}"
        )


def report_text(
    depth_summary: pd.DataFrame, geography_summary: pd.DataFrame,
    rainfall_summary: pd.DataFrame, production_summary: pd.DataFrame,
) -> str:
    return f"""# EXP-03 March soil-moisture depth and spatial-regime analysis

## Scope

This report reproduces the completed Step 4A/4B descriptive analysis from existing grid-specific March correlations. It does not refit EXP-03, use SoilGrids, or infer causality.

## Frozen regime reconstruction

- Usable grids: **76** under the existing minimum of **15 paired years**.
- Surface definition: March 0–7 cm grid-specific Spearman rho.
- Deep definition: arithmetic mean of March 28–100 and 100–255 cm grid-specific Spearman rho.
- Regime counts reconstructed from the correlations: **42 positive-positive, 19 depth-recovery, 13 persistent-negative, and 2 reverse**.

## Depth relationships

{markdown_table(depth_summary)}

## Geography

{markdown_table(geography_summary)}

## March rainfall correspondence

{markdown_table(rainfall_summary)}

## Existing production support

{markdown_table(production_summary)}

## Interpretation boundary

The regime split is spatially structured and differs in municipality composition and production support. March rainfall correspondence overlaps the soil-moisture regimes only partially. These are descriptive competing explanations; none establishes a causal mechanism.
"""


def build(root: Path, output_dir: Path | None = None) -> dict[str, Path]:
    root = root.resolve()
    correlation_path = root / (
        "outputs/research/exp_03/yield_stratified_monthly_weather/"
        "checkpoint2/grid_specific_spearman_correlations.csv"
    )
    mapping_path = root / "outputs/research/exp_02/exp_02b/eligible_municipality_grid_mapping.csv"
    grid_results_path = root / "data/processed/analysis/exp_02b/actual_vs_fixed_grid_residuals.csv"
    weights_path = root / "data/processed/analysis/exp_02b/matched_support_weight_details.csv"
    fixed_weights_path = root / "outputs/research/exp_02/exp_02b/fixed_reference_weights.csv"
    for path in [correlation_path, mapping_path, grid_results_path, weights_path, fixed_weights_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required upstream artifact not found: {path}")

    correlations = pd.read_csv(correlation_path)
    mapping = pd.read_csv(mapping_path)
    grid_results = pd.read_csv(grid_results_path)
    weights = pd.read_csv(weights_path)
    fixed_weights = pd.read_csv(fixed_weights_path)

    regimes = classify_depth_regimes(correlations)
    validate_frozen_regimes(regimes)
    geography = grid_geography(mapping)
    regimes = regimes.merge(geography, on="grid_id", validate="one_to_one")
    depth_summary = summarize_depth_relationships(regimes)
    geography_summary = summarize_geography(regimes, geography)
    rainfall_summary = summarize_rainfall(correlations, regimes)
    support = production_support_by_grid(grid_results, weights, fixed_weights, geography)
    production_summary = summarize_production_support(regimes, support)

    output = output_dir or root / "outputs/research/exp_03/march_soil_moisture_depth"
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "march_depth_summary": output / "march_depth_summary.csv",
        "grid_depth_regimes": output / "grid_depth_regimes.csv",
        "regime_summary": output / "regime_summary.csv",
        "regime_rainfall_summary": output / "regime_rainfall_summary.csv",
        "regime_production_support_summary": output / "regime_production_support_summary.csv",
        "report": output / "EXP_03_march_soil_moisture_depth_report.md",
    }
    depth_summary.to_csv(paths["march_depth_summary"], index=False)
    regimes.to_csv(paths["grid_depth_regimes"], index=False)
    geography_summary.to_csv(paths["regime_summary"], index=False)
    rainfall_summary.to_csv(paths["regime_rainfall_summary"], index=False)
    production_summary.to_csv(paths["regime_production_support_summary"], index=False)
    paths["report"].write_text(
        report_text(depth_summary, geography_summary, rainfall_summary, production_summary),
        encoding="utf-8",
    )
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=project_root())
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(args.project_root, args.output_dir)


if __name__ == "__main__":
    main()
