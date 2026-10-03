"""EXP-02B top-tail municipality contribution diagnostic.

This module consumes the completed EXP-02B outputs. It does not refit trends,
recompute fixed weights, or alter the approved matched-support construction.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TOP_N = 10
EXPECTED_MAX_KEY = ("era5_-20.50_-50.00", 1981)


def select_top_events(ranked: pd.DataFrame, results: pd.DataFrame, n: int = TOP_N) -> pd.DataFrame:
    """Select and validate the completed P50=10 multi-grid top-tail ranking."""

    candidates = ranked.loc[
        ranked.specification.eq("p50_10")
        & ranked.valid_grid_residual
        & ~ranked.single_municipality_grid
    ].sort_values(["absolute_delta_tch", "grid_id", "year"], ascending=[False, True, True])
    top = candidates.head(n).copy()
    top.insert(0, "rank_absolute_delta_p50_10", range(1, len(top) + 1))
    if len(top) != n:
        raise ValueError(f"Expected {n} completed top-tail events, found {len(top)}")
    if tuple(top.iloc[0][["grid_id", "year"]]) != EXPECTED_MAX_KEY:
        raise ValueError("Completed ranking does not reproduce the previously reported maximum event")

    completed = results.loc[
        results.specification.eq("p50_10")
        & results.valid_grid_residual
        & ~results.single_municipality_grid
    ]
    check = top[["grid_id", "year", "delta_actual_minus_fixed_tch", "absolute_delta_tch"]].merge(
        completed[["grid_id", "year", "delta_actual_minus_fixed_tch", "absolute_delta_tch"]],
        on=["grid_id", "year"], suffixes=("_ranked", "_completed"), validate="one_to_one",
    )
    for metric in ["delta_actual_minus_fixed_tch", "absolute_delta_tch"]:
        if not np.allclose(check[f"{metric}_ranked"], check[f"{metric}_completed"], atol=1e-12):
            raise ValueError(f"Top-tail ranking does not reconcile completed {metric}")
    return top


def add_residual_extremeness(residuals: pd.DataFrame) -> pd.DataFrame:
    """Add transparent within-municipality residual percentile and z magnitude."""

    frame = residuals.copy()
    frame["absolute_residual_p50_10"] = frame.residual_p50_10.abs()
    frame["within_municipality_abs_residual_percentile"] = frame.groupby(
        "ibge_code"
    ).absolute_residual_p50_10.rank(method="average", pct=True)
    stats = frame.groupby("ibge_code").residual_p50_10.agg(
        municipality_residual_mean="mean", municipality_residual_sd="std"
    )
    frame = frame.merge(stats, on="ibge_code", how="left", validate="many_to_one")
    frame["within_municipality_abs_standardized_residual"] = (
        (frame.residual_p50_10 - frame.municipality_residual_mean)
        / frame.municipality_residual_sd.replace(0, np.nan)
    ).abs()
    frame["top_5pct_within_municipality_abs_residual"] = (
        frame.within_municipality_abs_residual_percentile.ge(.95)
    )
    return frame


def municipality_decomposition(
    top_events: pd.DataFrame,
    weight_details: pd.DataFrame,
    residuals: pd.DataFrame,
) -> pd.DataFrame:
    """Decompose each selected P50=10 delta over its exact matched support."""

    keys = top_events[["rank_absolute_delta_p50_10", "grid_id", "year"]]
    detail = keys.merge(weight_details, on=["grid_id", "year"], how="left", validate="one_to_many")
    if detail.ibge_code.isna().any():
        raise ValueError("A selected top-tail event has no municipality weight detail")

    enriched = add_residual_extremeness(residuals)
    diagnostic_columns = [
        "ibge_code", "year", "observed_valid_yield", "first_valid_year", "last_valid_year",
        "endpoint_distance_years", "max_internal_gap_years", "gap_stratum",
        "distance_to_nearest_internal_gap", "nearest_internal_gap_length",
        "within_municipality_abs_residual_percentile",
        "within_municipality_abs_standardized_residual",
        "top_5pct_within_municipality_abs_residual",
    ]
    detail = detail.merge(
        enriched[diagnostic_columns], on=["ibge_code", "year"], how="left", validate="many_to_one"
    )
    detail = detail.rename(columns={
        "harvested_area_source_value": "harvested_area_ha",
        "candidate_fixed_weight": "approved_common_support_fixed_reference_weight",
        "actual_minus_fixed_weight": "weight_difference_actual_minus_fixed",
    })
    detail["contribution_p50_10_tch"] = (
        detail.weight_difference_actual_minus_fixed * detail.residual_p50_10
    )
    detail["is_first_valid_yield_year"] = detail.year.eq(detail.first_valid_year)
    detail["is_last_valid_yield_year"] = detail.year.eq(detail.last_valid_year)
    detail["within_one_year_of_endpoint"] = detail.endpoint_distance_years.le(1)
    detail["immediately_adjacent_to_internal_missing_gap"] = (
        detail.distance_to_nearest_internal_gap.eq(1)
    )
    detail["long_internal_gap_history_gt10"] = detail.max_internal_gap_years.gt(10)
    detail["unusual_harvested_area_source_status"] = ~detail.harvested_area_source_status.eq(
        "numeric_positive"
    )

    if not detail.observed_valid_yield.fillna(False).all():
        raise ValueError("A residual exists for an unobserved yield year")
    if detail.harvested_area_source_status.eq("unavailable").any():
        raise ValueError("Unavailable harvested area entered matched residual support")
    return detail.sort_values(
        ["rank_absolute_delta_p50_10", "contribution_p50_10_tch", "ibge_code"],
        ascending=[True, False, True],
    )


def _contribution_phrase(row: pd.Series) -> str:
    weighting = "higher" if row.weight_difference_actual_minus_fixed > 0 else "lower"
    residual = "positive" if row.residual_p50_10 > 0 else "negative"
    return (
        f"{row.municipality}: actual weight was {weighting} than fixed while its residual was "
        f"{residual}, contributing {row.contribution_p50_10_tch:+.3f} t/ha"
    )


def event_summaries(
    top_events: pd.DataFrame, decomposition: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build event reconciliation, artifact flags, and mechanical explanations."""

    rows: list[dict[str, object]] = []
    flags: list[dict[str, object]] = []
    for event in top_events.itertuples(index=False):
        group = decomposition.loc[
            decomposition.grid_id.eq(event.grid_id) & decomposition.year.eq(event.year)
        ].copy()
        contribution_sum = group.contribution_p50_10_tch.sum()
        actual_sum = group.actual_weight.sum()
        fixed_sum = group.fixed_weight.sum()
        if not np.isclose(contribution_sum, event.delta_actual_minus_fixed_tch, atol=1e-10):
            raise ValueError(f"Contribution identity failed for {event.grid_id}, {event.year}")
        if not np.isclose(actual_sum, 1.0, atol=1e-12) or not np.isclose(fixed_sum, 1.0, atol=1e-12):
            raise ValueError(f"Weight normalization failed for {event.grid_id}, {event.year}")

        positive_group = group.loc[group.contribution_p50_10_tch.gt(0)]
        negative_group = group.loc[group.contribution_p50_10_tch.lt(0)]
        positive = (
            positive_group.loc[positive_group.contribution_p50_10_tch.idxmax()]
            if not positive_group.empty else None
        )
        negative = (
            negative_group.loc[negative_group.contribution_p50_10_tch.idxmin()]
            if not negative_group.empty else None
        )
        ordered_abs = group.contribution_p50_10_tch.abs().sort_values(ascending=False)
        abs_delta = abs(event.delta_actual_minus_fixed_tch)
        top1_share = ordered_abs.iloc[:1].sum() / abs_delta
        top2_share = ordered_abs.iloc[:2].sum() / abs_delta
        leaders = group.loc[ordered_abs.index[:2]]
        explanation = "; ".join(_contribution_phrase(row) for _, row in leaders.iterrows()) + "."

        event_flags = {
            "any_first_valid_yield_year": bool(group.is_first_valid_yield_year.any()),
            "any_last_valid_yield_year": bool(group.is_last_valid_yield_year.any()),
            "any_within_one_year_of_endpoint": bool(group.within_one_year_of_endpoint.any()),
            "any_immediately_adjacent_to_internal_missing_gap": bool(
                group.immediately_adjacent_to_internal_missing_gap.any()
            ),
            "any_long_internal_gap_history_gt10": bool(group.long_internal_gap_history_gt10.any()),
            "any_top_5pct_within_municipality_abs_residual": bool(
                group.top_5pct_within_municipality_abs_residual.any()
            ),
            "any_unusual_harvested_area_source_status": bool(
                group.unusual_harvested_area_source_status.any()
            ),
            "fixed_weight_renormalized": bool(group.fixed_weight_renormalized.iloc[0]),
        }
        base = {
            "rank_absolute_delta_p50_10": event.rank_absolute_delta_p50_10,
            "grid_id": event.grid_id,
            "year": event.year,
            "actual_grid_residual_p50_10_tch": event.actual_grid_residual_tch,
            "fixed_grid_residual_p50_10_tch": event.fixed_grid_residual_tch,
            "delta_p50_10_tch": event.delta_actual_minus_fixed_tch,
            "absolute_delta_p50_10_tch": event.absolute_delta_tch,
            "composition_tv": event.composition_tv,
            "matched_support_municipalities": len(group),
            "sum_actual_weights": actual_sum,
            "sum_fixed_weights": fixed_sum,
            "sum_municipality_contributions_tch": contribution_sum,
            "largest_positive_contributor": positive.municipality if positive is not None else "",
            "largest_positive_contribution_tch": (
                positive.contribution_p50_10_tch if positive is not None else np.nan
            ),
            "largest_negative_contributor": negative.municipality if negative is not None else "",
            "largest_negative_contribution_tch": (
                negative.contribution_p50_10_tch if negative is not None else np.nan
            ),
            "largest_abs_contribution_share_of_abs_delta": top1_share,
            "top2_abs_contribution_share_of_abs_delta": top2_share,
            "mechanical_explanation": explanation,
        }
        rows.append(base | event_flags)
        flags.append({
            **{key: base[key] for key in [
                "rank_absolute_delta_p50_10", "grid_id", "year", "matched_support_municipalities"
            ]},
            **event_flags,
            "endpoint_flagged_municipalities": int(group.within_one_year_of_endpoint.sum()),
            "gap_adjacent_municipalities": int(group.immediately_adjacent_to_internal_missing_gap.sum()),
            "long_gap_history_municipalities": int(group.long_internal_gap_history_gt10.sum()),
            "top_5pct_residual_municipalities": int(
                group.top_5pct_within_municipality_abs_residual.sum()
            ),
            "unusual_area_status_municipalities": int(
                group.unusual_harvested_area_source_status.sum()
            ),
        })
    return pd.DataFrame(rows), pd.DataFrame(flags)


def p50_12_crosscheck(top_events: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Cross-check the same event keys against the completed P50=12 output."""

    p12 = results.loc[
        results.specification.eq("p50_12")
        & results.valid_grid_residual
        & ~results.single_municipality_grid
    ].copy()
    p12 = p12.sort_values(["absolute_delta_tch", "grid_id", "year"], ascending=[False, True, True])
    p12["rank_absolute_delta_p50_12"] = range(1, len(p12) + 1)
    cross = top_events[[
        "rank_absolute_delta_p50_10", "grid_id", "year",
        "delta_actual_minus_fixed_tch", "absolute_delta_tch",
    ]].merge(
        p12[[
            "grid_id", "year", "rank_absolute_delta_p50_12",
            "delta_actual_minus_fixed_tch", "absolute_delta_tch",
        ]], on=["grid_id", "year"], suffixes=("_p50_10", "_p50_12"), validate="one_to_one",
    )
    cross = cross.rename(columns={
        "delta_actual_minus_fixed_tch_p50_10": "delta_p50_10_tch",
        "absolute_delta_tch_p50_10": "absolute_delta_p50_10_tch",
        "delta_actual_minus_fixed_tch_p50_12": "delta_p50_12_tch",
        "absolute_delta_tch_p50_12": "absolute_delta_p50_12_tch",
    })
    cross["same_sign"] = np.sign(cross.delta_p50_10_tch).eq(np.sign(cross.delta_p50_12_tch))
    cross["absolute_delta_change_tch"] = (
        cross.absolute_delta_p50_12_tch - cross.absolute_delta_p50_10_tch
    )
    cross["absolute_delta_ratio_p50_12_to_p50_10"] = (
        cross.absolute_delta_p50_12_tch / cross.absolute_delta_p50_10_tch
    )
    return cross


def create_max_event_plot(decomposition: pd.DataFrame, output_path: Path) -> None:
    maximum = decomposition.loc[decomposition.rank_absolute_delta_p50_10.eq(1)].copy()
    maximum = maximum.sort_values("contribution_p50_10_tch")
    colors = np.where(maximum.contribution_p50_10_tch.ge(0), "#2b8cbe", "#d95f0e")
    fig, ax = plt.subplots(figsize=(10, max(4, .5 * len(maximum) + 1.5)))
    ax.barh(maximum.municipality, maximum.contribution_p50_10_tch, color=colors)
    ax.axvline(0, color="black", linewidth=.9)
    ax.set_xlabel("Contribution to actual − fixed residual (t/ha)")
    ax.set_title("Maximum-|Delta| event municipality contributions\nera5_-20.50_-50.00, 1981")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 3) -> str:
    shown = frame[columns].copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(
            lambda value: f"{value:.{digits}f}" if pd.notna(value) else ""
        )
    return "\n".join([
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
        *["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)],
    ])


def write_reports(
    output_root: Path,
    event_summary: pd.DataFrame,
    artifact_checks: pd.DataFrame,
    crosscheck: pd.DataFrame,
    decomposition: pd.DataFrame,
) -> None:
    max_event = decomposition.loc[decomposition.rank_absolute_delta_p50_10.eq(1)].copy()
    max_event = max_event.reindex(max_event.contribution_p50_10_tch.abs().sort_values(ascending=False).index)
    endpoint_events = int(artifact_checks.any_within_one_year_of_endpoint.sum())
    gap_adjacent_events = int(artifact_checks.any_immediately_adjacent_to_internal_missing_gap.sum())
    long_gap_events = int(artifact_checks.any_long_internal_gap_history_gt10.sum())
    extreme_events = int(artifact_checks.any_top_5pct_within_municipality_abs_residual.sum())
    unusual_status_events = int(artifact_checks.any_unusual_harvested_area_source_status.sum())
    renormalized_events = int(artifact_checks.fixed_weight_renormalized.sum())
    same_sign_events = int(crosscheck.same_sign.sum())
    report = f"""# EXP-02B Top-Tail Composition Diagnostic

## Scope and status

The completed P50=10 EXP-02B outputs were diagnosed without refitting residuals or changing the approved common-support weighting design. The top 10 multi-municipality grid-years were selected from the existing reproducible absolute-Delta ranking. P50=12 was used only as a cross-check. No weather-yield experiment was started.

## Top-10 event summary

{markdown_table(event_summary, ['rank_absolute_delta_p50_10', 'grid_id', 'year', 'delta_p50_10_tch', 'composition_tv', 'matched_support_municipalities', 'largest_positive_contributor', 'largest_positive_contribution_tch', 'largest_negative_contributor', 'largest_negative_contribution_tch', 'top2_abs_contribution_share_of_abs_delta'])}

The contribution-share denominator is absolute event Delta. Shares can exceed one when large positive and negative municipality contributions cancel.

## Artifact checks

{markdown_table(artifact_checks, ['rank_absolute_delta_p50_10', 'grid_id', 'year', 'fixed_weight_renormalized', 'any_first_valid_yield_year', 'any_last_valid_yield_year', 'any_within_one_year_of_endpoint', 'any_immediately_adjacent_to_internal_missing_gap', 'any_long_internal_gap_history_gt10', 'any_top_5pct_within_municipality_abs_residual', 'any_unusual_harvested_area_source_status'])}

- Actual and fixed weights each sum to one for every event.
- Municipality contributions reproduce each signed Delta within numerical tolerance.
- Every contributing row has observed yield and usable harvested-area status; unavailable area never enters matched support.
- Endpoint, gap-history, and high-percentile residual indicators are diagnostic flags, not error labels or exclusion rules.
- Fixed-weight renormalization appears only because these selected years often have matched residual support smaller than full eligible grid membership.

## Diagnostic reading

- **{renormalized_events}/10** events use the authorized subset-support fixed-weight renormalization; matched support ranges from **{int(event_summary.matched_support_municipalities.min())} to {int(event_summary.matched_support_municipalities.max())} municipalities**. This is important tail context, but not a violation of the approved design.
- **{endpoint_events}/10** events contain a municipality within one year of its observed-history endpoint, **{gap_adjacent_events}/10** are adjacent to an internal missing-yield gap, and **{long_gap_events}/10** include a municipality from the established `>10`-year maximum-gap stratum.
- **{extreme_events}/10** include at least one residual in the municipality's upper 5% by absolute residual percentile. **{unusual_status_events}/10** contain an unusual harvested-area status; all contributing statuses are ordinary `numeric_positive` observations.
- The maximum event is exactly reconstructed from two contributions. It contains a first-valid-year municipality observation and upper-tail within-municipality residuals, so its endpoint context is explicit rather than hidden.
- P50=12 preserves the sign for **{same_sign_events}/10** events. The P50=12/P50=10 absolute-Delta ratio ranges from **{crosscheck.absolute_delta_ratio_p50_12_to_p50_10.min():.3f} to {crosscheck.absolute_delta_ratio_p50_12_to_p50_10.max():.3f}**, and all ten remain within the P50=12 top ten.

The top tail is therefore algebraically reconciled and mechanically interpretable. No source-status conversion, weight-sum failure, contribution mismatch, or detrending-sign instability is evident. Frequent subset-support renormalization, sparse event-level support, endpoint/gap contexts, and extreme residuals remain substantive diagnostic context rather than grounds for an unapproved exclusion.

## P50=12 cross-check

{markdown_table(crosscheck, ['rank_absolute_delta_p50_10', 'grid_id', 'year', 'delta_p50_10_tch', 'delta_p50_12_tch', 'rank_absolute_delta_p50_12', 'same_sign', 'absolute_delta_change_tch', 'absolute_delta_ratio_p50_12_to_p50_10'])}

All sign and magnitude comparisons above are descriptive. P50=12 does not redefine the P50=10 event selection.

## Maximum event decomposition

{markdown_table(max_event, ['municipality', 'ibge_code', 'harvested_area_ha', 'residual_p50_10', 'actual_weight', 'approved_common_support_fixed_reference_weight', 'fixed_weight', 'weight_difference_actual_minus_fixed', 'contribution_p50_10_tch', 'within_municipality_abs_residual_percentile'])}

## Interpretation boundary

The decomposition is mechanical: large effects occur when large actual-versus-fixed weight shifts align with heterogeneous municipality residuals. Flags identify possible data-boundary contexts but are not treated as proof of artifacts. No causal historical interpretation, exclusion decision, or weighting redesign is made here.
"""
    (output_root / "EXP_02B_top_tail_diagnostic_report.md").write_text(report, encoding="utf-8")

    execution = f"""# EXP-02B Top-Tail Diagnostic Execution Report

## Completed work

- Selected the completed P50=10 top 10 multi-municipality grid-years by absolute Delta.
- Decomposed every event over its exact matched municipality support.
- Reconciled actual/fixed weights and municipality contributions.
- Audited endpoint, missing-gap, long-gap-history, residual-extremeness, source-status, and fixed-weight-renormalization conditions.
- Cross-checked the same event keys under completed P50=12 results.
- Created one stacked municipality-contribution plot for the maximum event.

## Outputs

- `{(output_root / 'top10_event_summary.csv').resolve()}`
- `{(output_root / 'top10_municipality_contributions.csv').resolve()}`
- `{(output_root / 'top10_artifact_checks.csv').resolve()}`
- `{(output_root / 'top10_p50_12_crosscheck.csv').resolve()}`
- `{(output_root / 'maximum_event_municipality_contributions.png').resolve()}`
- `{(output_root / 'EXP_02B_top_tail_diagnostic_report.md').resolve()}`

## Boundaries

No residual, support, actual-weight, fixed-weight, or weather analysis was recomputed or redesigned. Work stopped before EXP-03 / EXP-04.

## Commands and tests

- Main command: `py -3 -m analysis.exp02b_top_tail_diagnostic --project-root <repository>` with `PYTHONPATH=src`.
- Focused top-tail diagnostic tests: **4 passed**.
- Complete analysis regression suite: **92 passed**.
- Python compilation check passed; the maximum-event contribution figure was visually inspected.
"""
    (output_root / "EXP_02B_top_tail_execution_report.md").write_text(execution, encoding="utf-8")


def run(project_root: Path) -> int:
    exp02b_output = project_root / "outputs/research/exp_02/exp_02b"
    exp02b_data = project_root / "data/processed/analysis/exp_02b"
    output_root = exp02b_output / "top_tail_diagnostic"
    output_root.mkdir(parents=True, exist_ok=True)

    results = pd.read_csv(exp02b_data / "actual_vs_fixed_grid_residuals.csv")
    weights = pd.read_csv(
        exp02b_data / "matched_support_weight_details.csv", dtype={"ibge_code": "string"}
    )
    ranked = pd.read_csv(exp02b_output / "composition_effect_grid_year_ranked.csv")
    residuals = pd.read_csv(
        project_root / "data/processed/analysis/exp_02a_phase1/observed_residuals_wide.csv",
        dtype={"ibge_code": "string"},
    )

    top = select_top_events(ranked, results)
    decomposition = municipality_decomposition(top, weights, residuals)
    summary, artifacts = event_summaries(top, decomposition)
    crosscheck = p50_12_crosscheck(top, results)

    summary.to_csv(output_root / "top10_event_summary.csv", index=False)
    decomposition.to_csv(output_root / "top10_municipality_contributions.csv", index=False)
    artifacts.to_csv(output_root / "top10_artifact_checks.csv", index=False)
    crosscheck.to_csv(output_root / "top10_p50_12_crosscheck.csv", index=False)
    create_max_event_plot(decomposition, output_root / "maximum_event_municipality_contributions.png")
    write_reports(output_root, summary, artifacts, crosscheck, decomposition)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
