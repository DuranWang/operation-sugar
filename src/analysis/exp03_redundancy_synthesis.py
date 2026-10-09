"""Formalize EXP-03 Step 5 representation and temporal redundancy decisions.

The candidate universe is frozen research state, not newly optimized feature
selection.  Adjacent-month predictor correlations are derived from exactly
matched crop years within ERA5 grid; existing yield signatures are read only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analysis.exp03_march_soil_moisture_depth import markdown_table


MINIMUM_PAIRED_YEARS = 15
MONTHS = {
    -4: "Dec_(t-1)",
    -3: "Jan_t",
    -2: "Feb_t",
    -1: "Mar_t",
    0: "Apr_t",
}
ADJACENT_PAIRS = [
    (-4, -3, "Dec-Jan"),
    (-3, -2, "Jan-Feb"),
    (-2, -1, "Feb-Mar"),
    (-1, 0, "Mar-Apr"),
]
CANONICAL_VARIABLES = {
    "rainfall_input": {
        "weather_variable": "nasa_total_rainfall_mm", "depth": "",
        "conditional_flag": "HYDRO_CONDITIONAL", "spatial_status": "MIXED_HETEROGENEOUS",
    },
    "temperature": {
        "weather_variable": "nasa_average_temperature_c", "depth": "",
        "conditional_flag": "EXP05_CONDITIONAL", "spatial_status": "MIXED_HETEROGENEOUS",
    },
    "relative_humidity": {
        "weather_variable": "nasa_average_relative_humidity_pct", "depth": "",
        "conditional_flag": "ATMOSPHERIC_SECONDARY", "spatial_status": "STATEWIDE_COMMON",
    },
    "mean_vpd": {
        "weather_variable": "vpd_mean_kpa", "depth": "",
        "conditional_flag": "EXP05_CONDITIONAL", "spatial_status": "MIXED_HETEROGENEOUS",
    },
    "upper_soil_moisture": {
        "weather_variable": "soil_moisture_0_to_7cm_m3_m3", "depth": "0-7 cm",
        "conditional_flag": "HYDRO_CONDITIONAL", "spatial_status": "MIXED_HETEROGENEOUS",
    },
    "deep_soil_moisture_28_100": {
        "weather_variable": "soil_moisture_28_to_100cm_m3_m3", "depth": "28-100 cm",
        "conditional_flag": "HYDRO_CONDITIONAL", "spatial_status": "DEFERRED_CONDITIONAL",
    },
    "deep_soil_moisture_100_255": {
        "weather_variable": "soil_moisture_100_to_255cm_m3_m3", "depth": "100-255 cm",
        "conditional_flag": "HYDRO_CONDITIONAL", "spatial_status": "DEFERRED_CONDITIONAL",
    },
    "solar_energy": {
        "weather_variable": "solar_radiation_mean_daily_mj_m2", "depth": "",
        "conditional_flag": "NONE", "spatial_status": "MIXED_HETEROGENEOUS",
    },
}
APPROVED_DEC_JAN_AGGREGATES = {
    "relative_humidity",
    "deep_soil_moisture_28_100",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def representation_decisions() -> pd.DataFrame:
    """Return frozen canonical and archived representation decisions."""

    rows = [
        {
            "conceptual_family": "solar_energy",
            "canonical_variable": "solar_radiation_mean_daily_mj_m2",
            "archived_robustness_variable": "solar_radiation_total_mj_m2",
            "decision_basis": "representation duplicate; mean-daily avoids month-length scaling",
        },
        {
            "conceptual_family": "vpd",
            "canonical_variable": "vpd_mean_kpa",
            "archived_robustness_variable": "vpd_mean_daily_max_kpa",
            "decision_basis": "near-duplicate predictor and yield behavior; not a temperature-VPD decision",
        },
        {
            "conceptual_family": "upper_soil_moisture",
            "canonical_variable": "soil_moisture_0_to_7cm_m3_m3",
            "archived_robustness_variable": "soil_moisture_7_to_28cm_m3_m3",
            "decision_basis": "one upper-state family; 0-7 cm preserves EXP-01 and March-audit continuity",
        },
    ]
    return pd.DataFrame(rows)


def _within_grid_rank(values: pd.Series) -> pd.Series:
    return values.rank(method="average")


def adjacent_month_redundancy(
    aligned: pd.DataFrame, minimum_pairs: int = MINIMUM_PAIRED_YEARS,
) -> pd.DataFrame:
    """Calculate matched-year cross-month Spearman correlations by grid."""

    required = {"grid_id", "year", "relative_month_index"}
    missing = required - set(aligned.columns)
    if missing:
        raise ValueError(f"Missing aligned-panel columns: {sorted(missing)}")
    if aligned.duplicated(["grid_id", "year", "relative_month_index"]).any():
        raise ValueError("Aligned panel has duplicate grid-year-month keys")

    rows: list[dict[str, object]] = []
    for concept, metadata in CANONICAL_VARIABLES.items():
        variable = metadata["weather_variable"]
        column = f"{variable}__anomaly"
        if column not in aligned:
            raise ValueError(f"Missing anomaly column: {column}")
        for first, second, label in ADJACENT_PAIRS:
            pair = aligned.loc[
                aligned.relative_month_index.isin([first, second]),
                ["grid_id", "year", "relative_month_index", column],
            ].pivot(index=["grid_id", "year"], columns="relative_month_index", values=column).dropna()
            grid_rhos: list[float] = []
            paired_counts: list[int] = []
            for _, group in pair.reset_index().groupby("grid_id", sort=True):
                n = len(group)
                paired_counts.append(n)
                usable = (
                    n >= minimum_pairs
                    and group[first].nunique() > 1
                    and group[second].nunique() > 1
                )
                if usable:
                    grid_rhos.append(float(spearmanr(group[first], group[second]).statistic))
            rhos = pd.Series(grid_rhos, dtype=float)
            ranked = pair.reset_index()
            ranked["first_rank"] = ranked.groupby("grid_id")[first].transform(_within_grid_rank)
            ranked["second_rank"] = ranked.groupby("grid_id")[second].transform(_within_grid_rank)
            pooled = float(spearmanr(ranked.first_rank, ranked.second_rank).statistic)
            pct_positive = float(rhos.gt(0).mean())
            pct_negative = float(rhos.lt(0).mean())
            modal = "positive" if pct_positive >= pct_negative else "negative"
            rows.append({
                "conceptual_variable": concept,
                "weather_variable": variable,
                "month_pair": label,
                "first_relative_month": first,
                "second_relative_month": second,
                "total_grids": int(pair.reset_index().grid_id.nunique()),
                "usable_grids": len(rhos),
                "minimum_pairs_required": minimum_pairs,
                "minimum_paired_years_all_grids": min(paired_counts),
                "median_paired_years_all_grids": float(np.median(paired_counts)),
                "maximum_paired_years_all_grids": max(paired_counts),
                "median_grid_spearman": rhos.median(),
                "q25_grid_spearman": rhos.quantile(.25),
                "q75_grid_spearman": rhos.quantile(.75),
                "pct_grids_positive": pct_positive,
                "pct_grids_negative": pct_negative,
                "modal_direction": modal,
                "modal_direction_fraction": max(pct_positive, pct_negative),
                "pooled_within_grid_rank_rho": pooled,
            })
    return pd.DataFrame(rows)


def temporal_aggregation_decisions(
    redundancy: pd.DataFrame, existing_yield: pd.DataFrame,
) -> pd.DataFrame:
    """Attach existing yield/spatial evidence to the frozen temporal decisions."""

    required = {
        "relative_month_index", "weather_variable", "standardized_high_minus_low",
        "pooled_within_grid_rank_rho", "pct_grids_agree_with_pooled_direction",
    }
    missing = required - set(existing_yield.columns)
    if missing:
        raise ValueError(f"Missing existing yield-summary columns: {sorted(missing)}")
    rows = []
    for item in redundancy.itertuples(index=False):
        start = existing_yield.loc[
            existing_yield.weather_variable.eq(item.weather_variable)
            & existing_yield.relative_month_index.eq(item.first_relative_month)
        ]
        end = existing_yield.loc[
            existing_yield.weather_variable.eq(item.weather_variable)
            & existing_yield.relative_month_index.eq(item.second_relative_month)
        ]
        if len(start) != 1 or len(end) != 1:
            raise ValueError(f"Incomplete existing yield evidence for {item.weather_variable} {item.month_pair}")
        start_row, end_row = start.iloc[0], end.iloc[0]
        promoted = (
            item.month_pair == "Dec-Jan"
            and item.conceptual_variable in APPROVED_DEC_JAN_AGGREGATES
        )
        if promoted:
            status = "DEC_JAN_AGGREGATION_CANDIDATE"
            rationale = "Frozen Step-5 decision; predictor, existing yield, and spatial evidence jointly align"
        elif item.month_pair != "Dec-Jan":
            status = "KEEP_SEPARATE_HETEROGENEITY"
            rationale = "No Jan-Feb, Feb-Mar, or Mar-Apr aggregate is promoted"
        else:
            status = "KEEP_MONTHLY"
            rationale = "Frozen Step-5 decision; joint three-gate evidence does not justify aggregation"
        rows.append({
            **item._asdict(),
            "start_standardized_high_minus_low": start_row.standardized_high_minus_low,
            "end_standardized_high_minus_low": end_row.standardized_high_minus_low,
            "start_pooled_yield_rho": start_row.pooled_within_grid_rank_rho,
            "end_pooled_yield_rho": end_row.pooled_within_grid_rank_rho,
            "start_grid_direction_agreement": start_row.pct_grids_agree_with_pooled_direction,
            "end_grid_direction_agreement": end_row.pct_grids_agree_with_pooled_direction,
            "promoted_aggregate": promoted,
            "decision_status": status,
            "decision_rationale": rationale,
        })
    return pd.DataFrame(rows)


def _evidence_string(
    existing_yield: pd.DataFrame, variable: str, relative_months: list[int], column: str,
) -> str:
    indexed = existing_yield.loc[
        existing_yield.weather_variable.eq(variable)
        & existing_yield.relative_month_index.isin(relative_months)
    ].set_index("relative_month_index")
    if set(relative_months) - set(indexed.index):
        raise ValueError(f"Missing existing evidence for {variable}: {relative_months}")
    return ";".join(f"{month}:{indexed.loc[month, column]:.6f}" for month in relative_months)


def candidate_universe(
    redundancy: pd.DataFrame, existing_yield: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the frozen 38-row downstream candidate specification."""

    rows: list[dict[str, object]] = []
    for concept, metadata in CANONICAL_VARIABLES.items():
        aggregate = concept in APPROVED_DEC_JAN_AGGREGATES
        month_groups = [[-4, -3], [-2], [-1], [0]] if aggregate else [[month] for month in MONTHS]
        for relative_months in month_groups:
            is_aggregate = len(relative_months) == 2
            if is_aggregate:
                candidate_suffix = "dec_jan"
                status = "DEC_JAN_AGGREGATION_CANDIDATE"
                red = redundancy.loc[
                    redundancy.conceptual_variable.eq(concept)
                    & redundancy.month_pair.eq("Dec-Jan")
                ].iloc[0]
                temporal_median = red.median_grid_spearman
                temporal_q25 = red.q25_grid_spearman
                temporal_q75 = red.q75_grid_spearman
                temporal_modal_fraction = red.modal_direction_fraction
                temporal_note = "Dec-Jan aggregate candidate; values not constructed in Step 5"
            else:
                candidate_suffix = f"m_{relative_months[0]}"
                temporal_median = np.nan
                temporal_q25 = np.nan
                temporal_q75 = np.nan
                temporal_modal_fraction = np.nan
                temporal_note = "Monthly representation preserved by frozen Step-5 decision"
                if concept in {"temperature", "mean_vpd", "deep_soil_moisture_28_100", "deep_soil_moisture_100_255"}:
                    status = "KEEP_SEPARATE_CONDITIONAL"
                else:
                    status = "KEEP_MONTHLY"
            variable = metadata["weather_variable"]
            rows.append({
                "candidate_id": f"{concept}__{candidate_suffix}",
                "conceptual_variable": concept,
                "raw_source_variable": variable,
                "raw_source_depth": metadata["depth"],
                "source_relative_months": ";".join(str(month) for month in relative_months),
                "source_months": ";".join(MONTHS[month] for month in relative_months),
                "temporal_form": "multi_month_candidate" if is_aggregate else "monthly",
                "representation_decision": "CANONICAL",
                "candidate_status": status,
                "temporal_median_grid_spearman": temporal_median,
                "temporal_q25_grid_spearman": temporal_q25,
                "temporal_q75_grid_spearman": temporal_q75,
                "temporal_modal_direction_fraction": temporal_modal_fraction,
                "temporal_redundancy_evidence": temporal_note,
                "existing_standardized_high_minus_low": _evidence_string(
                    existing_yield, variable, relative_months, "standardized_high_minus_low"
                ),
                "existing_pooled_yield_rho": _evidence_string(
                    existing_yield, variable, relative_months, "pooled_within_grid_rank_rho"
                ),
                "existing_grid_direction_agreement": _evidence_string(
                    existing_yield, variable, relative_months,
                    "pct_grids_agree_with_pooled_direction",
                ),
                "spatial_status": metadata["spatial_status"],
                "conditional_information_flag": metadata["conditional_flag"],
                "downstream_recommendation": (
                    "Evaluate candidate without replacing protected monthly/depth concepts"
                    if is_aggregate else "Carry forward under frozen Step-5 specification"
                ),
            })
    result = pd.DataFrame(rows)
    if len(result) != 38 or result.candidate_id.duplicated().any():
        raise ValueError(f"Frozen candidate universe must contain 38 unique rows, found {len(result)}")
    return result


def validate_frozen_decisions(
    redundancy: pd.DataFrame, decisions: pd.DataFrame, candidates: pd.DataFrame,
) -> None:
    if not redundancy.usable_grids.eq(76).all():
        values = sorted(redundancy.usable_grids.unique())
        raise ValueError(f"Adjacent-month usable-grid count disagrees with frozen state: {values}")
    promoted = decisions.loc[decisions.promoted_aggregate, ["conceptual_variable", "month_pair"]]
    expected = {(concept, "Dec-Jan") for concept in APPROVED_DEC_JAN_AGGREGATES}
    observed = set(promoted.itertuples(index=False, name=None))
    if observed != expected:
        raise ValueError(f"Unexpected promoted temporal aggregates: {observed}")
    if len(candidates) != 38:
        raise ValueError("Frozen candidate universe does not contain 38 representations")


def report_text(
    representations: pd.DataFrame, redundancy: pd.DataFrame,
    decisions: pd.DataFrame, candidates: pd.DataFrame,
) -> str:
    dec_jan = decisions.loc[decisions.month_pair.eq("Dec-Jan"), [
        "conceptual_variable", "median_grid_spearman", "q25_grid_spearman",
        "q75_grid_spearman", "modal_direction_fraction",
        "start_standardized_high_minus_low", "end_standardized_high_minus_low",
        "start_grid_direction_agreement", "end_grid_direction_agreement",
        "decision_status",
    ]]
    adjacent_compact = redundancy[[
        "conceptual_variable", "month_pair", "usable_grids", "median_grid_spearman",
        "q25_grid_spearman", "q75_grid_spearman", "modal_direction",
        "modal_direction_fraction", "pooled_within_grid_rank_rho",
    ]]
    candidate_compact = candidates[[
        "candidate_id", "raw_source_variable", "source_months", "candidate_status",
        "spatial_status", "conditional_information_flag",
    ]]
    return f"""# EXP-03 Step 5 redundancy synthesis

## Scope and validation

This report formalizes the frozen Step-5 representation and temporal decisions. Adjacent-month correlations use exactly matched crop years within ERA5 grid and require at least 15 paired years. All **32 variable-pair summaries use 76 grids**. Existing yield and spatial summaries are read only; no candidate feature is constructed or optimized against yield.

## Approved representation reductions

{markdown_table(representations)}

## Adjacent-month predictor redundancy

{markdown_table(adjacent_compact)}

## Dec-Jan decision synthesis

{markdown_table(dec_jan)}

Only Dec-Jan relative humidity and Dec-Jan 28-100 cm soil moisture are promoted as aggregation candidates. No Jan-Feb, Feb-Mar, or Mar-Apr aggregate is promoted.

## Frozen downstream universe

Candidate representations: **{len(candidates)}**.

{markdown_table(candidate_compact)}

## Protected structure

- Temperature and mean VPD remain separate (`EXP05_CONDITIONAL`).
- Rainfall, upper moisture, and both deep-moisture layers remain distinct (`HYDRO_CONDITIONAL`).
- Static SoilGrids properties are not included.
- Total solar, daily-max VPD, and 7-28 cm moisture remain archived robustness representations rather than additional candidates.
"""


def build(root: Path, output_dir: Path | None = None) -> dict[str, Path]:
    root = root.resolve()
    aligned_path = root / (
        "outputs/research/exp_03/yield_stratified_monthly_weather/"
        "checkpoint1/aligned_grid_year_month_weather_anomalies.csv"
    )
    yield_path = root / (
        "outputs/research/exp_03/yield_stratified_monthly_weather/"
        "checkpoint2/categorical_vs_continuous_comparison.csv"
    )
    for path in [aligned_path, yield_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required upstream artifact not found: {path}")

    aligned = pd.read_csv(aligned_path)
    existing_yield = pd.read_csv(yield_path)
    representations = representation_decisions()
    redundancy = adjacent_month_redundancy(aligned)
    decisions = temporal_aggregation_decisions(redundancy, existing_yield)
    candidates = candidate_universe(redundancy, existing_yield)
    validate_frozen_decisions(redundancy, decisions, candidates)

    output = output_dir or root / "outputs/research/exp_03/redundancy"
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "representations": output / "representation_decisions.csv",
        "adjacent": output / "adjacent_month_redundancy.csv",
        "temporal": output / "temporal_aggregation_decisions.csv",
        "candidates": output / "exp04_candidate_universe.csv",
        "report": output / "EXP_03_redundancy_synthesis_report.md",
    }
    representations.to_csv(paths["representations"], index=False)
    redundancy.to_csv(paths["adjacent"], index=False)
    decisions.to_csv(paths["temporal"], index=False)
    candidates.to_csv(paths["candidates"], index=False)
    paths["report"].write_text(
        report_text(representations, redundancy, decisions, candidates), encoding="utf-8"
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
