"""Focused Phase 0 decomposition of four candidate yield-support gates.

This is a reporting extension only. It reuses the completed source-aware panel
and Phase 0 gate implementation and does not choose a gate or fit any trend.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analysis.exp02a_yield_support_audit import summarize_gate


CASES = (
    ("N15_only", "N >= 15 only", 15, 1, None),
    ("S20_only", "Calendar span >= 20 only", 1, 20, None),
    ("G10_only", "Maximum internal gap <= 10 only", 1, 1, 10),
    ("N15_S20_GU", "N >= 15 + calendar span >= 20; gap unrestricted", 15, 20, None),
)


def percent(value: float) -> str:
    return f"{100 * value:.3f}%"


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    shown = frame[columns].copy()
    headers = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)]
    return "\n".join([headers, separator, *rows])


def run(project_root: Path) -> int:
    data_path = project_root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv"
    output_root = project_root / "outputs/research/exp_02/exp_02a_phase0"
    support_path = output_root / "municipality_support.csv"
    panel = pd.read_csv(data_path, dtype={"ibge_code": "string"})
    support = pd.read_csv(support_path, dtype={"ibge_code": "string"})

    baseline, _, _ = summarize_gate(panel, support, "any_valid_history", 1, 1, None)
    summary_rows: list[dict[str, object]] = []
    yearly_frames: list[pd.DataFrame] = []
    for case_id, label, minimum, span, gap in CASES:
        result, yearly, _ = summarize_gate(panel, support, case_id, minimum, span, gap)
        early = yearly.loc[yearly["year"].between(1974, 1989), "retained_valid_yield_area_coverage"]
        full = yearly["retained_valid_yield_area_coverage"]
        recent = yearly.loc[yearly["year"].between(1990, 2025), "retained_valid_yield_area_coverage"]
        summary_rows.append({
            "case_id": case_id,
            "case_label": label,
            "retained_municipalities": result["retained_municipalities"],
            "municipalities_excluded_vs_any_valid": baseline["retained_municipalities"] - result["retained_municipalities"],
            "retained_valid_municipality_years": result["retained_valid_municipality_years"],
            "valid_observations_excluded_vs_any_valid": baseline["retained_valid_municipality_years"] - result["retained_valid_municipality_years"],
            "mean_area_coverage_1974_2025": result["mean_annual_area_coverage_1974_2025"],
            "minimum_area_coverage_1974_2025": result["minimum_annual_area_coverage_1974_2025"],
            "minimum_coverage_year_1974_2025": int(yearly.loc[full.idxmin(), "year"]),
            "mean_area_coverage_1990_2025": result["mean_annual_area_coverage_1990_2025"],
            "minimum_area_coverage_1990_2025": result["minimum_annual_area_coverage_1990_2025"],
            "minimum_coverage_year_1990_2025": int(yearly.loc[recent.idxmin(), "year"]),
            "mean_area_coverage_1974_1989": float(early.mean()),
            "minimum_area_coverage_1974_1989": float(early.min()),
            "minimum_coverage_year_1974_1989": int(yearly.loc[early.idxmin(), "year"]),
        })
        yearly = yearly[[
            "gate_id", "year", "valid_yield_municipality_count",
            "retained_valid_yield_share", "retained_valid_yield_harvested_area_ha",
            "all_observed_harvested_area_ha", "retained_valid_yield_area_coverage",
        ]].rename(columns={"gate_id": "case_id"})
        yearly.insert(1, "case_label", label)
        yearly_frames.append(yearly)

    summary = pd.DataFrame(summary_rows)
    yearly = pd.concat(yearly_frames, ignore_index=True)
    summary.to_csv(output_root / "focused_gate_decomposition_summary.csv", index=False)
    yearly.to_csv(output_root / "focused_gate_decomposition_yearly_coverage.csv", index=False)

    summary_view = summary.copy()
    for column in [
        "mean_area_coverage_1974_2025", "minimum_area_coverage_1974_2025",
        "mean_area_coverage_1990_2025", "minimum_area_coverage_1990_2025",
        "mean_area_coverage_1974_1989", "minimum_area_coverage_1974_1989",
    ]:
        summary_view[column] = summary_view[column].map(percent)

    early = yearly.loc[yearly["year"].between(1974, 1989)].pivot(
        index="year", columns="case_id", values="retained_valid_yield_area_coverage"
    ).reset_index()
    for column in [case[0] for case in CASES]:
        early[column] = early[column].map(percent)

    report = f"""# EXP-02A Phase 0 Focused Gate Decomposition

## Scope

This supplement applies each requested condition separately, then applies `N >= 15` and calendar span `>= 20` jointly with no gap restriction. “Separately” means the other dimensions use the minimal any-valid-history base (`N >= 1`, span `>= 1`, gap unrestricted). The comparison baseline contains {baseline['retained_municipalities']} municipalities and {baseline['retained_valid_municipality_years']} valid municipality-year observations. No gate is selected and no trend is fitted.

## Summary

{markdown_table(summary_view, [
    'case_label', 'retained_municipalities', 'municipalities_excluded_vs_any_valid',
    'retained_valid_municipality_years', 'valid_observations_excluded_vs_any_valid',
    'mean_area_coverage_1974_2025', 'minimum_area_coverage_1974_2025', 'minimum_coverage_year_1974_2025',
    'mean_area_coverage_1990_2025', 'minimum_area_coverage_1990_2025', 'minimum_coverage_year_1990_2025',
])}

## Early-period year-by-year observed-area coverage

{markdown_table(early, ['year', 'N15_only', 'S20_only', 'G10_only', 'N15_S20_GU'])}

The complete 1974–2025 year-by-year series, including retained valid municipality counts and area numerators/denominators, is in `focused_gate_decomposition_yearly_coverage.csv`.

## Interpretation without gate selection

- `N >= 15` has the smallest footprint effect: it removes short histories but retains nearly all observed harvested area in every year.
- Span `>= 20` is also almost neutral in 1974–2006, but its coverage declines gradually after 2007 because some materially active recent municipalities have shorter calendar histories.
- Gap `<= 10` has the largest independent effect. Its early-period coverage remains high, but it increasingly excludes observed area after the late 1990s, reaching the lowest coverage in 2019.
- Adding `N >= 15` to span `>= 20` changes the span-only footprint only slightly. Its main additional effect is excluding 14 municipalities and 132 valid observations relative to span `>= 20` alone.

These are descriptive support effects only. They do not establish the final eligibility gate.
"""
    (output_root / "EXP_02A_phase0_focused_gate_decomposition.md").write_text(report, encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
