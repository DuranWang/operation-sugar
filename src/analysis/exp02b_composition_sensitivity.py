"""EXP-02B matched-support within-grid composition sensitivity.

The audit stage is intentionally runnable on its own. The full actual-vs-fixed
experiment may proceed only after the mapping/support stop gate is reviewed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


EXPECTED_ELIGIBLE = 511
USABLE_AREA_STATUSES = {"numeric_positive", "numeric_zero", "explicit_zero"}


def validate_mapping_frame(mapping: pd.DataFrame) -> pd.DataFrame:
    required = {"ibge_code", "municipality", "grid_id", "grid_latitude", "grid_longitude"}
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"Mapping is missing columns: {sorted(missing)}")
    if mapping.duplicated("ibge_code").any():
        raise ValueError("Municipality-to-grid mapping is not unique")
    if mapping["grid_id"].isna().any():
        raise ValueError("Mapping contains missing grid identifiers")
    return mapping


def canonical_mapping(mapping_path: Path) -> pd.DataFrame:
    mapping = pd.read_csv(mapping_path, dtype={"ibge_code": "string"})
    return validate_mapping_frame(mapping)


def validate_mapping_versions(mapping_files: list[Path]) -> pd.DataFrame:
    if not mapping_files:
        raise FileNotFoundError("No repository municipality-grid mappings found")
    reference = canonical_mapping(mapping_files[-1]).sort_values("ibge_code").reset_index(drop=True)
    columns = ["ibge_code", "grid_id", "grid_latitude", "grid_longitude"]
    rows = []
    for path in mapping_files:
        candidate = canonical_mapping(path).sort_values("ibge_code").reset_index(drop=True)
        stable = reference[columns].equals(candidate[columns])
        rows.append({
            "mapping_path": str(path.resolve()),
            "municipalities": len(candidate),
            "unique_grids": candidate.grid_id.nunique(),
            "content_matches_canonical": stable,
        })
    result = pd.DataFrame(rows)
    if not result.content_matches_canonical.all():
        raise ValueError("Repository mapping content changes across annual mapping files")
    return result


def eligible_mapping_audit(support: pd.DataFrame, mapping: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eligible = support.loc[
        support.n_valid_years.ge(15) & support.calendar_span_years.ge(20),
        ["ibge_code", "municipality", "n_valid_years", "calendar_span_years", "max_internal_gap_years"],
    ].copy()
    if len(eligible) != EXPECTED_ELIGIBLE:
        raise ValueError(f"Expected {EXPECTED_ELIGIBLE} eligible municipalities, found {len(eligible)}")
    joined = eligible.merge(
        mapping[["ibge_code", "grid_id", "grid_latitude", "grid_longitude"]],
        on="ibge_code", how="left", validate="one_to_one", indicator=True,
    )
    unmapped = joined.loc[joined._merge.ne("both")].drop(columns="_merge")
    mapped = joined.loc[joined._merge.eq("both")].drop(columns="_merge")
    counts = mapped.groupby(["grid_id", "grid_latitude", "grid_longitude"], as_index=False).agg(
        eligible_municipalities=("ibge_code", "nunique")
    )
    counts["grid_size_category"] = pd.cut(
        counts.eligible_municipalities,
        bins=[0, 1, 2, 5, np.inf], labels=["1", "2", "3-5", ">5"],
    ).astype("string")
    counts["single_municipality_grid"] = counts.eligible_municipalities.eq(1)
    return mapped, unmapped, counts


def grid_year_support_audit(
    panel: pd.DataFrame,
    residuals: pd.DataFrame,
    mapped: pd.DataFrame,
) -> pd.DataFrame:
    annual = panel.merge(
        mapped[["ibge_code", "grid_id", "grid_latitude", "grid_longitude"]],
        on="ibge_code", how="inner", validate="many_to_one",
    )
    primary = residuals[["ibge_code", "year", "residual_p50_10"]].copy()
    primary["has_primary_residual"] = primary.residual_p50_10.notna()
    annual = annual.merge(
        primary[["ibge_code", "year", "has_primary_residual"]],
        on=["ibge_code", "year"], how="left", validate="one_to_one",
    )
    annual["has_primary_residual"] = annual.has_primary_residual.eq(True)
    annual["usable_area_status"] = annual.harvested_area_source_status.isin(USABLE_AREA_STATUSES)
    annual["matched_support"] = annual.usable_area_status & annual.has_primary_residual
    if annual.loc[annual.matched_support, "harvested_area_source_value"].isna().any():
        raise ValueError("Matched support contains missing harvested area")

    rows = []
    for keys, group in annual.groupby(["grid_id", "grid_latitude", "grid_longitude", "year"], sort=True):
        grid_id, latitude, longitude, year = keys
        usable = group.usable_area_status
        matched = group.matched_support
        denominator = float(group.loc[usable, "harvested_area_source_value"].sum())
        numerator = float(group.loc[matched, "harvested_area_source_value"].sum())
        positive_denominator = denominator > 0
        coverage = numerator / denominator if positive_denominator else np.nan
        rows.append({
            "grid_id": grid_id, "grid_latitude": latitude, "grid_longitude": longitude, "year": int(year),
            "mapped_eligible_municipalities": group.ibge_code.nunique(),
            "usable_area_municipalities": int(usable.sum()),
            "unavailable_area_municipalities": int(group.harvested_area_source_status.eq("unavailable").sum()),
            "matched_support_municipalities": int(matched.sum()),
            "explicit_or_numeric_zero_area_municipalities": int((usable & group.harvested_area_source_value.eq(0)).sum()),
            "observed_harvested_area_denominator_ha": denominator,
            "matched_support_harvested_area_ha": numerator,
            "positive_area_denominator": positive_denominator,
            "support_coverage": coverage,
        })
    result = pd.DataFrame(rows)
    tolerance = 1e-12
    result["coverage_bucket"] = np.select(
        [
            ~result.positive_area_denominator,
            np.isclose(result.support_coverage, 1.0, atol=tolerance, rtol=0),
            result.support_coverage.ge(.99), result.support_coverage.ge(.95), result.support_coverage.ge(.90),
        ],
        ["invalid_nonpositive_denominator", "100%", "99-<100%", "95-<99%", "90-<95%"],
        default="<90%",
    )
    return result


def support_summaries(grid_year: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    valid = grid_year.loc[grid_year.positive_area_denominator]
    distribution = pd.DataFrame([
        {"criterion": "100%", "grid_years": int(np.isclose(valid.support_coverage, 1.0, atol=1e-12, rtol=0).sum())},
        {"criterion": ">=99%", "grid_years": int(valid.support_coverage.ge(.99).sum())},
        {"criterion": ">=95%", "grid_years": int(valid.support_coverage.ge(.95).sum())},
        {"criterion": "90-<95%", "grid_years": int(valid.support_coverage.ge(.90).mul(valid.support_coverage.lt(.95)).sum())},
        {"criterion": "<90%", "grid_years": int(valid.support_coverage.lt(.90).sum())},
        {"criterion": "invalid_nonpositive_denominator", "grid_years": int((~grid_year.positive_area_denominator).sum())},
    ])
    distribution["share_of_positive_denominator_grid_years"] = np.where(
        distribution.criterion.eq("invalid_nonpositive_denominator"), np.nan,
        distribution.grid_years / len(valid) if len(valid) else np.nan,
    )
    by_year = grid_year.groupby("year", as_index=False).agg(
        grids=("grid_id", "nunique"), valid_denominator_grid_years=("positive_area_denominator", "sum"),
        mean_support_coverage=("support_coverage", "mean"), minimum_support_coverage=("support_coverage", "min"),
        grid_years_below_90=("support_coverage", lambda values: int(values.lt(.90).sum())),
        invalid_denominator_grid_years=("positive_area_denominator", lambda values: int((~values).sum())),
    )
    by_grid = grid_year.groupby(["grid_id", "grid_latitude", "grid_longitude"], as_index=False).agg(
        years=("year", "nunique"), mapped_eligible_municipalities=("mapped_eligible_municipalities", "first"),
        valid_denominator_years=("positive_area_denominator", "sum"),
        mean_support_coverage=("support_coverage", "mean"), minimum_support_coverage=("support_coverage", "min"),
        years_below_90=("support_coverage", lambda values: int(values.lt(.90).sum())),
        invalid_denominator_years=("positive_area_denominator", lambda values: int((~values).sum())),
    )
    return distribution, by_year, by_grid


def fixed_reference_weights(panel: pd.DataFrame, mapped: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    annual = panel.merge(
        mapped[["ibge_code", "grid_id"]], on="ibge_code", how="inner", validate="many_to_one"
    )
    annual["usable_area_status"] = annual.harvested_area_source_status.isin(USABLE_AREA_STATUSES)
    denominators = annual.loc[annual.usable_area_status].groupby(["grid_id", "year"], as_index=False).agg(
        observed_grid_area_ha=("harvested_area_source_value", "sum")
    )
    annual = annual.merge(denominators, on=["grid_id", "year"], how="left", validate="many_to_one")
    reference_rows = annual.loc[
        annual.usable_area_status & annual.observed_grid_area_ha.gt(0)
    ].copy()
    reference_rows["observed_within_grid_share"] = (
        reference_rows.harvested_area_source_value / reference_rows.observed_grid_area_ha
    )
    reference = reference_rows.groupby(["grid_id", "ibge_code", "municipality"], as_index=False).agg(
        reference_observed_years=("year", "nunique"),
        reference_positive_area_years=("harvested_area_source_value", lambda values: int(values.gt(0).sum())),
        first_reference_year=("year", "min"), last_reference_year=("year", "max"),
        fixed_reference_weight_raw=("observed_within_grid_share", "mean"),
        minimum_observed_share=("observed_within_grid_share", "min"),
        maximum_observed_share=("observed_within_grid_share", "max"),
    )
    expected = set(mapped.ibge_code.astype(str))
    available = set(reference.ibge_code.astype(str))
    if available != expected:
        missing = sorted(expected - available)
        raise ValueError(f"Eligible mapped municipalities missing fixed-reference history: {missing[:10]}")
    reconciliation = reference.groupby("grid_id", as_index=False).agg(
        eligible_municipalities=("ibge_code", "nunique"),
        raw_fixed_weight_sum=("fixed_reference_weight_raw", "sum"),
        minimum_reference_observed_years=("reference_observed_years", "min"),
        median_reference_observed_years=("reference_observed_years", "median"),
        maximum_fixed_reference_weight=("fixed_reference_weight_raw", "max"),
    )
    reference = reference.merge(
        reconciliation[["grid_id", "raw_fixed_weight_sum"]], on="grid_id", how="left", validate="many_to_one"
    )
    reference["fixed_reference_weight_grid_normalized"] = (
        reference.fixed_reference_weight_raw / reference.raw_fixed_weight_sum
    )
    return reference, reconciliation


def add_grid_footprint(
    reconciliation: pd.DataFrame, panel: pd.DataFrame, mapped: pd.DataFrame
) -> pd.DataFrame:
    annual = panel.merge(mapped[["ibge_code", "grid_id"]], on="ibge_code", how="inner", validate="many_to_one")
    annual = annual.loc[annual.harvested_area_source_status.isin(USABLE_AREA_STATUSES)].copy()
    grid_year = annual.groupby(["grid_id", "year"], as_index=False).agg(
        observed_grid_area_ha=("harvested_area_source_value", "sum")
    )
    state_year = grid_year.groupby("year", as_index=False).agg(
        observed_state_area_ha=("observed_grid_area_ha", "sum")
    )
    grid_year = grid_year.merge(state_year, on="year", how="left", validate="many_to_one")
    grid_year["observed_state_area_share"] = np.where(
        grid_year.observed_state_area_ha.gt(0),
        grid_year.observed_grid_area_ha / grid_year.observed_state_area_ha,
        np.nan,
    )
    footprint = grid_year.groupby("grid_id", as_index=False).agg(
        mean_observed_state_area_share=("observed_state_area_share", "mean"),
        maximum_observed_state_area_share=("observed_state_area_share", "max"),
        total_observed_area_ha=("observed_grid_area_ha", "sum"),
    )
    result = reconciliation.merge(footprint, on="grid_id", how="left", validate="one_to_one")
    result["absolute_raw_weight_sum_deviation"] = (result.raw_fixed_weight_sum - 1).abs()
    return result


def common_support_reference_weights(
    panel: pd.DataFrame, mapped: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    grid_sizes = mapped.groupby("grid_id", as_index=False).agg(
        eligible_municipalities=("ibge_code", "nunique")
    )
    multi_grids = grid_sizes.loc[grid_sizes.eligible_municipalities.gt(1)].copy()
    annual = panel.merge(
        mapped[["ibge_code", "grid_id"]], on="ibge_code", how="inner", validate="many_to_one"
    ).merge(multi_grids, on="grid_id", how="inner", validate="many_to_one")
    annual["usable_area_status"] = annual.harvested_area_source_status.isin(USABLE_AREA_STATUSES)
    grid_year = annual.groupby(["grid_id", "year"], as_index=False).agg(
        eligible_municipalities=("eligible_municipalities", "first"),
        observed_status_municipalities=("usable_area_status", "sum"),
        observed_grid_area_ha=("harvested_area_source_value", lambda values: values.sum(min_count=1)),
    )
    grid_year["all_eligible_statuses_observed"] = grid_year.observed_status_municipalities.eq(
        grid_year.eligible_municipalities
    )
    grid_year["valid_within_grid_denominator"] = grid_year.observed_grid_area_ha.gt(0)
    grid_year["common_support_year"] = (
        grid_year.all_eligible_statuses_observed & grid_year.valid_within_grid_denominator
    )

    common_keys = grid_year.loc[grid_year.common_support_year, ["grid_id", "year", "observed_grid_area_ha"]]
    common_rows = annual.merge(common_keys, on=["grid_id", "year"], how="inner", validate="many_to_one")
    if not common_rows.usable_area_status.all():
        raise ValueError("Common-support rows contain unavailable harvested-area status")
    common_rows["annual_within_grid_share"] = (
        common_rows.harvested_area_source_value / common_rows.observed_grid_area_ha
    )
    annual_sums = common_rows.groupby(["grid_id", "year"]).annual_within_grid_share.sum()
    if not np.allclose(annual_sums.to_numpy(), 1.0, atol=1e-12, rtol=0):
        raise ValueError("Annual common-support shares do not sum to one")
    weights = common_rows.groupby(["grid_id", "ibge_code", "municipality"], as_index=False).agg(
        common_reference_years=("year", "nunique"),
        candidate_fixed_weight=("annual_within_grid_share", "mean"),
        minimum_common_year_share=("annual_within_grid_share", "min"),
        maximum_common_year_share=("annual_within_grid_share", "max"),
    )
    weight_sums = weights.groupby("grid_id", as_index=False).agg(
        candidate_fixed_weight_sum=("candidate_fixed_weight", "sum")
    )

    common_summary = grid_year.loc[grid_year.common_support_year].groupby("grid_id", as_index=False).agg(
        common_reference_years=("year", "nunique"),
        first_common_year=("year", "min"), last_common_year=("year", "max"),
    )
    grid_audit = multi_grids.merge(common_summary, on="grid_id", how="left", validate="one_to_one")
    grid_audit["common_reference_years"] = grid_audit.common_reference_years.fillna(0).astype(int)
    grid_audit["common_period_calendar_span"] = np.where(
        grid_audit.common_reference_years.gt(0),
        grid_audit.last_common_year - grid_audit.first_common_year + 1,
        0,
    ).astype(int)
    grid_audit = grid_audit.merge(weight_sums, on="grid_id", how="left", validate="one_to_one")
    grid_audit["candidate_fixed_weights_sum_to_one"] = np.where(
        grid_audit.common_reference_years.gt(0),
        np.isclose(grid_audit.candidate_fixed_weight_sum, 1.0, atol=1e-12, rtol=0),
        False,
    )

    footprint_base = add_grid_footprint(
        multi_grids.assign(raw_fixed_weight_sum=1.0), panel, mapped
    )[["grid_id", "mean_observed_state_area_share", "maximum_observed_state_area_share", "total_observed_area_ha"]]
    grid_audit = grid_audit.merge(footprint_base, on="grid_id", how="left", validate="one_to_one")
    grid_audit["support_group"] = pd.cut(
        grid_audit.common_reference_years,
        bins=[-1, 9, 14, 19, np.inf], labels=["<10", "10-14", "15-19", ">=20"],
    )
    distribution = grid_audit.groupby("support_group", observed=False, as_index=False).agg(
        grids=("grid_id", "size"),
        mean_common_reference_years=("common_reference_years", "mean"),
        minimum_common_reference_years=("common_reference_years", "min"),
        maximum_common_reference_years=("common_reference_years", "max"),
        share_of_statewide_observed_area=("mean_observed_state_area_share", "sum"),
    )
    return weights, grid_audit, distribution


def write_common_support_report(
    path: Path, weights: pd.DataFrame, grid_audit: pd.DataFrame, distribution: pd.DataFrame
) -> None:
    with_years = grid_audit.loc[grid_audit.common_reference_years.gt(0)]
    no_years = grid_audit.loc[grid_audit.common_reference_years.eq(0)]
    weight_failures = with_years.loc[~with_years.candidate_fixed_weights_sum_to_one]
    lowest = grid_audit.sort_values(["common_reference_years", "grid_id"]).iloc[0]
    view = distribution.copy()
    view["share_of_statewide_observed_area"] = 100 * view.share_of_statewide_observed_area
    text = f"""# EXP-02B Common-Support Reference-Weight Audit

## Scope

This audit implements only the Chat-approved common-support reference construction for the 74 multi-municipality grids. It does not calculate actual-weight or fixed-weight grid residuals and does not run the composition experiment.

For grid `g`, a common year requires every EXP-02A-eligible municipality assigned to the grid to have observed harvested-area status and the within-grid observed-area denominator to be positive. Candidate weights are the municipality's mean annual within-grid share over exactly those common years.

## Validation

- Multi-municipality grids audited: **{len(grid_audit)}**.
- Grids with at least one common reference year: **{len(with_years)}**.
- Grids with zero common reference years: **{len(no_years)}**.
- Municipality fixed-weight rows created: **{len(weights)}**.
- Grids with common years whose candidate fixed weights fail to sum to one within numerical tolerance: **{len(weight_failures)}**.
- Common reference years across grids: minimum **{grid_audit.common_reference_years.min()}**, median **{grid_audit.common_reference_years.median():.1f}**, maximum **{grid_audit.common_reference_years.max()}**.

## Support distribution and observed-area footprint

The footprint column is the sum of each grid's mean annual share of statewide observed harvested area over 1974–2025. It is not a latent true-area share.

{markdown_table(view, ['support_group', 'grids', 'mean_common_reference_years', 'minimum_common_reference_years', 'maximum_common_reference_years', 'share_of_statewide_observed_area'])}

The support groups jointly represent **{100 * distribution.share_of_statewide_observed_area.sum():.4f}%** of mean statewide observed harvested area. The remaining **{100 * (1 - distribution.share_of_statewide_observed_area.sum()):.4f}%** belongs to the four single-municipality grids outside this multi-municipality reference audit.

The lowest-support grid is `{lowest.grid_id}`: {int(lowest.eligible_municipalities)} eligible municipalities, {int(lowest.common_reference_years)} common years, first/last common years {int(lowest.first_common_year)}–{int(lowest.last_common_year)}, calendar span {int(lowest.common_period_calendar_span)}, and **{100 * lowest.mean_observed_state_area_share:.4f}%** mean observed statewide harvested-area footprint.

## Per-grid output

`common_support_grid_audit.csv` reports, for every multi-municipality grid, the eligible municipality count, number of common reference years, first and last common year, common-period calendar span, candidate-weight sum and reconciliation flag, and observed harvested-area footprint.

`common_support_reference_weights.csv` contains the municipality candidate weights and their common-year share ranges. No candidate weight is applied to a residual in this audit.

## Stop

The common-support audit is complete. EXP-02B stops here for Chat interpretation; the actual-vs-fixed residual experiment remains unexecuted.
"""
    path.write_text(text, encoding="utf-8")


def write_common_support_execution_report(path: Path, output_root: Path) -> None:
    text = f"""# EXP-02B Common-Support Audit Execution Report

## Status

**COMMON-SUPPORT REFERENCE-WEIGHT AUDIT COMPLETED; STOPPED BEFORE THE RESIDUAL EXPERIMENT.**

## Created outputs

- `{(output_root / 'common_support_reference_weights.csv').resolve()}`
- `{(output_root / 'common_support_grid_audit.csv').resolve()}`
- `{(output_root / 'common_support_distribution.csv').resolve()}`
- `{(output_root / 'EXP_02B_common_support_reference_audit.md').resolve()}`

## Boundaries honored

- No actual-vs-fixed residual calculation was run.
- No support exclusion rule was selected.
- No weather result was used.
- No EXP-03 or EXP-04 work was started.

## Command and tests

- Command: `py -3 -m analysis.exp02b_composition_sensitivity --stage common-support-audit --project-root <repository>` with `PYTHONPATH=src`.
- Focused common-support tests plus relevant EXP-02A and source-semantics regressions: **46 passed**.
- Python compilation check passed.
"""
    path.write_text(text, encoding="utf-8")


def matched_composition_aggregation(
    panel: pd.DataFrame,
    residuals: pd.DataFrame,
    mapped: pd.DataFrame,
    common_weights: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate P50=10/12 residuals with actual and approved fixed weights."""

    grid_sizes = mapped.groupby("grid_id", as_index=False).agg(
        eligible_municipalities=("ibge_code", "nunique")
    )
    weights = common_weights[["grid_id", "ibge_code", "candidate_fixed_weight"]].copy()
    single = mapped.merge(grid_sizes, on="grid_id", how="left", validate="many_to_one")
    single = single.loc[single.eligible_municipalities.eq(1), ["grid_id", "ibge_code"]].copy()
    single["candidate_fixed_weight"] = 1.0
    if weights.empty:
        weights = single.copy()
    elif not single.empty:
        weights = pd.concat([weights, single], ignore_index=True)
    if weights.duplicated(["grid_id", "ibge_code"]).any():
        raise ValueError("Duplicate approved fixed-weight key")
    if set(weights.ibge_code.astype(str)) != set(mapped.ibge_code.astype(str)):
        raise ValueError("Approved fixed weights do not reconcile all eligible mapped municipalities")

    annual = panel.merge(
        mapped[["ibge_code", "grid_id", "grid_latitude", "grid_longitude"]],
        on="ibge_code", how="inner", validate="many_to_one",
    ).merge(grid_sizes, on="grid_id", how="left", validate="many_to_one")
    annual = annual.merge(
        weights, on=["grid_id", "ibge_code"], how="left", validate="many_to_one"
    )
    residual_columns = ["residual_p50_10", "residual_p50_12"]
    annual = annual.merge(
        residuals[["ibge_code", "year", *residual_columns]],
        on=["ibge_code", "year"], how="left", validate="one_to_one",
    )
    annual["usable_area_status"] = annual.harvested_area_source_status.isin(USABLE_AREA_STATUSES)
    annual["support_p50_10"] = annual.usable_area_status & annual.residual_p50_10.notna()
    annual["support_p50_12"] = annual.usable_area_status & annual.residual_p50_12.notna()
    if not annual.support_p50_10.equals(annual.support_p50_12):
        raise ValueError("P50=10 and P50=12 residual support differs")
    annual["matched_support"] = annual.support_p50_10

    detail_frames: list[pd.DataFrame] = []
    result_rows: list[dict[str, object]] = []
    for keys, group in annual.groupby(
        ["grid_id", "grid_latitude", "grid_longitude", "year"], sort=True
    ):
        grid_id, latitude, longitude, year = keys
        supported = group.loc[group.matched_support].copy()
        eligible_count = int(group.eligible_municipalities.iloc[0])
        matched_count = len(supported)
        actual_denominator = float(supported.harvested_area_source_value.sum())
        fixed_denominator = float(supported.candidate_fixed_weight.sum())
        valid = matched_count > 0 and actual_denominator > 0 and fixed_denominator > 0
        single_grid = eligible_count == 1
        full_membership_support = matched_count == eligible_count
        invalid_reason = ""
        if matched_count == 0:
            invalid_reason = "no_matched_residual_support"
        elif actual_denominator <= 0:
            invalid_reason = "nonpositive_actual_weight_denominator"
        elif fixed_denominator <= 0:
            invalid_reason = "nonpositive_fixed_weight_denominator"

        if valid:
            supported["actual_weight"] = supported.harvested_area_source_value / actual_denominator
            if full_membership_support:
                supported["fixed_weight"] = supported.candidate_fixed_weight
            else:
                supported["fixed_weight"] = supported.candidate_fixed_weight / fixed_denominator
            if not np.isclose(supported.actual_weight.sum(), 1.0, atol=1e-12, rtol=0):
                raise ValueError(f"Actual weights do not sum to one for {grid_id}, {year}")
            if not np.isclose(supported.fixed_weight.sum(), 1.0, atol=1e-12, rtol=0):
                raise ValueError(f"Fixed weights do not sum to one for {grid_id}, {year}")
            supported["actual_minus_fixed_weight"] = supported.actual_weight - supported.fixed_weight
            supported["fixed_weight_renormalized"] = not full_membership_support
            detail_frames.append(supported[[
                "grid_id", "grid_latitude", "grid_longitude", "year", "ibge_code", "municipality",
                "eligible_municipalities", "harvested_area_source_status", "harvested_area_source_value",
                "candidate_fixed_weight", "actual_weight", "fixed_weight", "actual_minus_fixed_weight",
                "fixed_weight_renormalized", *residual_columns,
            ]])
            tv = float(0.5 * supported.actual_minus_fixed_weight.abs().sum())
        else:
            tv = np.nan

        for specification, residual_column in [("p50_10", "residual_p50_10"), ("p50_12", "residual_p50_12")]:
            if valid:
                actual_residual = float(np.sum(supported.actual_weight * supported[residual_column]))
                fixed_residual = float(np.sum(supported.fixed_weight * supported[residual_column]))
                delta = actual_residual - fixed_residual
            else:
                actual_residual = fixed_residual = delta = np.nan
            result_rows.append({
                "grid_id": grid_id, "grid_latitude": latitude, "grid_longitude": longitude,
                "year": int(year), "specification": specification,
                "eligible_municipalities": eligible_count, "matched_support_municipalities": matched_count,
                "single_municipality_grid": single_grid,
                "full_membership_support": full_membership_support,
                "fixed_weight_renormalized": bool(valid and not full_membership_support),
                "actual_weight_denominator_ha": actual_denominator,
                "fixed_weight_denominator": fixed_denominator,
                "valid_grid_residual": valid, "invalid_reason": invalid_reason,
                "actual_grid_residual_tch": actual_residual,
                "fixed_grid_residual_tch": fixed_residual,
                "delta_actual_minus_fixed_tch": delta,
                "absolute_delta_tch": abs(delta) if valid else np.nan,
                "composition_tv": tv,
            })
    results = pd.DataFrame(result_rows)
    details = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    if results.duplicated(["grid_id", "year", "specification"]).any():
        raise ValueError("Duplicate grid-year-specification output keys")
    if not details.empty and details.duplicated(["grid_id", "year", "ibge_code"]).any():
        raise ValueError("Duplicate matched-support weight-detail keys")
    return results, details


def agreement_diagnostics(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    valid = results.loc[results.valid_grid_residual]
    for sample, group in [
        ("multi_municipality_primary", valid.loc[~valid.single_municipality_grid]),
        ("all_grids_secondary", valid),
        ("single_municipality_mechanical", valid.loc[valid.single_municipality_grid]),
    ]:
        for specification, subset in group.groupby("specification", sort=False):
            actual = subset.actual_grid_residual_tch
            fixed = subset.fixed_grid_residual_tch
            delta = subset.delta_actual_minus_fixed_tch
            absolute = delta.abs()
            rows.append({
                "sample": sample, "specification": specification,
                "grid_years": len(subset), "grids": subset.grid_id.nunique(),
                "pearson_correlation": actual.corr(fixed, method="pearson") if len(subset) > 1 else np.nan,
                "spearman_correlation": actual.corr(fixed, method="spearman") if len(subset) > 1 else np.nan,
                "mean_absolute_difference": absolute.mean(),
                "rmse_difference": float(np.sqrt(np.mean(delta**2))) if len(subset) else np.nan,
                "sign_agreement": float(np.mean(np.sign(actual) == np.sign(fixed))) if len(subset) else np.nan,
                "mean_delta": delta.mean(),
                "delta_standard_deviation": delta.std(ddof=1),
                "p05_delta": delta.quantile(.05),
                "median_delta": delta.median(),
                "p95_delta": delta.quantile(.95),
                "median_absolute_delta": absolute.median(),
                "p90_absolute_delta": absolute.quantile(.90),
                "p95_absolute_delta": absolute.quantile(.95),
                "p99_absolute_delta": absolute.quantile(.99),
                "maximum_absolute_delta": absolute.max(),
                "mean_composition_tv": subset.composition_tv.mean(),
                "median_composition_tv": subset.composition_tv.median(),
            })
    return pd.DataFrame(rows)


def composition_rankings(
    results: pd.DataFrame, grid_audit: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primary = results.loc[results.valid_grid_residual & ~results.single_municipality_grid].copy()
    by_grid = primary.groupby(["specification", "grid_id"], as_index=False).agg(
        grid_years=("year", "nunique"),
        eligible_municipalities=("eligible_municipalities", "first"),
        mean_absolute_delta=("absolute_delta_tch", "mean"),
        median_absolute_delta=("absolute_delta_tch", "median"),
        p95_absolute_delta=("absolute_delta_tch", lambda values: values.quantile(.95)),
        maximum_absolute_delta=("absolute_delta_tch", "max"),
        mean_composition_tv=("composition_tv", "mean"),
        maximum_composition_tv=("composition_tv", "max"),
    ).merge(
        grid_audit[["grid_id", "mean_observed_state_area_share", "common_reference_years"]],
        on="grid_id", how="left", validate="many_to_one",
    )
    by_grid = by_grid.sort_values(
        ["specification", "mean_absolute_delta", "grid_id"], ascending=[True, False, True]
    )
    by_year = primary.groupby(["specification", "year"], as_index=False).agg(
        grid_years=("grid_id", "nunique"),
        mean_absolute_delta=("absolute_delta_tch", "mean"),
        median_absolute_delta=("absolute_delta_tch", "median"),
        p95_absolute_delta=("absolute_delta_tch", lambda values: values.quantile(.95)),
        maximum_absolute_delta=("absolute_delta_tch", "max"),
        mean_composition_tv=("composition_tv", "mean"),
    ).sort_values(["specification", "mean_absolute_delta", "year"], ascending=[True, False, True])
    grid_year = primary.sort_values(
        ["specification", "absolute_delta_tch", "grid_id", "year"], ascending=[True, False, True, True]
    )

    tv_rows = []
    concentration_rows = []
    for specification, group in primary.groupby("specification", sort=False):
        tv_rows.append({
            "specification": specification, "grid_years": len(group),
            "pearson_tv_vs_absolute_delta": group.composition_tv.corr(group.absolute_delta_tch, method="pearson"),
            "spearman_tv_vs_absolute_delta": group.composition_tv.corr(group.absolute_delta_tch, method="spearman"),
        })
        ordered = group.absolute_delta_tch.sort_values(ascending=False)
        total = ordered.sum()
        grid_totals = group.groupby("grid_id").absolute_delta_tch.sum().sort_values(ascending=False)
        year_totals = group.groupby("year").absolute_delta_tch.sum().sort_values(ascending=False)
        for label, count, source in [
            ("top_1_percent_grid_years", max(1, int(np.ceil(.01 * len(ordered)))), ordered),
            ("top_5_percent_grid_years", max(1, int(np.ceil(.05 * len(ordered)))), ordered),
            ("top_10_percent_grid_years", max(1, int(np.ceil(.10 * len(ordered)))), ordered),
            ("top_5_grids", min(5, len(grid_totals)), grid_totals),
            ("top_10_grids", min(10, len(grid_totals)), grid_totals),
            ("top_5_years", min(5, len(year_totals)), year_totals),
            ("top_10_years", min(10, len(year_totals)), year_totals),
        ]:
            selected = source.iloc[:count]
            concentration_rows.append({
                "specification": specification, "concentration_set": label,
                "items": count, "share_of_total_absolute_delta": selected.sum() / total if total > 0 else np.nan,
            })
    return by_grid, by_year, grid_year, pd.DataFrame(tv_rows), pd.DataFrame(concentration_rows)


def detrending_robustness(results: pd.DataFrame) -> pd.DataFrame:
    primary = results.loc[results.valid_grid_residual & ~results.single_municipality_grid]
    wide = primary.pivot(index=["grid_id", "year"], columns="specification", values=[
        "actual_grid_residual_tch", "fixed_grid_residual_tch", "delta_actual_minus_fixed_tch", "composition_tv"
    ])
    rows = []
    for metric in ["actual_grid_residual_tch", "fixed_grid_residual_tch", "delta_actual_minus_fixed_tch"]:
        left, right = wide[(metric, "p50_10")], wide[(metric, "p50_12")]
        rows.append({
            "metric": metric, "grid_years": len(wide),
            "pearson_correlation": left.corr(right, method="pearson"),
            "spearman_correlation": left.corr(right, method="spearman"),
            "sign_agreement": float(np.mean(np.sign(left) == np.sign(right))),
            "mean_absolute_difference": (left - right).abs().mean(),
            "p95_absolute_difference": (left - right).abs().quantile(.95),
            "maximum_absolute_difference": (left - right).abs().max(),
        })
    return pd.DataFrame(rows)


def representative_grids(by_grid: pd.DataFrame) -> pd.DataFrame:
    primary = by_grid.loc[by_grid.specification.eq("p50_10")].copy()
    selected: list[dict[str, object]] = []
    used: set[str] = set()

    def choose(reason: str, sort_columns: list[str], ascending: list[bool]) -> None:
        available = primary.loc[~primary.grid_id.isin(used)].sort_values(sort_columns, ascending=ascending)
        row = available.iloc[0]
        used.add(row.grid_id)
        record = row.to_dict()
        record["selection_reason"] = reason
        selected.append(record)

    choose("high_harvested_area", ["mean_observed_state_area_share", "grid_id"], [False, True])
    choose("low_composition_change", ["mean_composition_tv", "grid_id"], [True, True])
    choose("high_composition_change", ["mean_composition_tv", "grid_id"], [False, True])
    choose("large_composition_effect", ["mean_absolute_delta", "grid_id"], [False, True])
    choose("many_municipalities", ["eligible_municipalities", "grid_id"], [False, True])
    return pd.DataFrame(selected)


def create_composition_figures(
    results: pd.DataFrame, representatives: pd.DataFrame, figure_root: Path
) -> None:
    figure_root.mkdir(parents=True, exist_ok=True)
    primary = results.loc[results.valid_grid_residual & ~results.single_municipality_grid]
    colors = {"p50_10": "#1f77b4", "p50_12": "#2ca02c"}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (specification, group) in zip(axes, primary.groupby("specification", sort=False)):
        ax.scatter(group.fixed_grid_residual_tch, group.actual_grid_residual_tch, alpha=.35, s=12, color=colors[specification])
        bounds = [min(group.fixed_grid_residual_tch.min(), group.actual_grid_residual_tch.min()), max(group.fixed_grid_residual_tch.max(), group.actual_grid_residual_tch.max())]
        ax.plot(bounds, bounds, color="black", linewidth=1)
        ax.set_title(specification)
        ax.set_xlabel("Fixed-composition residual (t/ha)")
        ax.set_ylabel("Actual-composition residual (t/ha)")
        ax.grid(alpha=.2)
    fig.suptitle("Actual versus fixed grid residuals: multi-municipality grids")
    fig.tight_layout()
    fig.savefig(figure_root / "actual_vs_fixed_scatter.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, (specification, group) in zip(axes, primary.groupby("specification", sort=False)):
        ax.hist(group.delta_actual_minus_fixed_tch, bins=50, color=colors[specification], alpha=.85)
        ax.axvline(0, color="black", linewidth=1)
        ax.set_title(specification)
        ax.set_xlabel("Actual − fixed residual (t/ha)")
        ax.set_ylabel("Grid-years")
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Composition-effect distribution")
    fig.tight_layout()
    fig.savefig(figure_root / "composition_effect_distribution.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, (specification, group) in zip(axes, primary.groupby("specification", sort=False)):
        ax.scatter(group.composition_tv, group.absolute_delta_tch, alpha=.35, s=12, color=colors[specification])
        ax.set_title(specification)
        ax.set_xlabel("Composition TV distance")
        ax.set_ylabel("Absolute composition effect (t/ha)")
        ax.grid(alpha=.2)
    fig.suptitle("Composition distance versus anomaly shift")
    fig.tight_layout()
    fig.savefig(figure_root / "absolute_delta_vs_composition_tv.png", dpi=180)
    plt.close(fig)

    representative_root = figure_root / "representative_grids"
    representative_root.mkdir(parents=True, exist_ok=True)
    for row in representatives.itertuples(index=False):
        group = primary.loc[primary.grid_id.eq(row.grid_id)].sort_values(["specification", "year"])
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        for specification, subset in group.groupby("specification", sort=False):
            # Leave gaps where no valid matched-support residual exists; do not
            # visually connect observations across missing calendar years.
            plotted = subset.set_index("year").reindex(range(1974, 2026))
            axes[0].plot(plotted.index, plotted.actual_grid_residual_tch, color=colors[specification], linestyle="-", label=f"{specification} actual")
            axes[0].plot(plotted.index, plotted.fixed_grid_residual_tch, color=colors[specification], linestyle="--", label=f"{specification} fixed")
            axes[1].plot(plotted.index, plotted.delta_actual_minus_fixed_tch, color=colors[specification], label=specification)
        axes[1].axhline(0, color="black", linewidth=.8)
        axes[0].set_ylabel("Grid residual (t/ha)")
        axes[1].set_ylabel("Actual − fixed (t/ha)")
        axes[1].set_xlabel("Year")
        axes[0].legend(ncol=2, fontsize=8)
        for ax in axes:
            ax.grid(alpha=.2)
        fig.suptitle(f"{row.grid_id} — {row.selection_reason}")
        fig.tight_layout()
        safe_grid = row.grid_id.replace(".", "p")
        fig.savefig(representative_root / f"{row.selection_reason}_{safe_grid}.png", dpi=180)
        plt.close(fig)


def write_full_exp02b_reports(
    output_root: Path, data_root: Path, results: pd.DataFrame, diagnostics: pd.DataFrame,
    by_grid: pd.DataFrame, by_year: pd.DataFrame, grid_year_ranked: pd.DataFrame,
    tv_diagnostics: pd.DataFrame, concentration: pd.DataFrame, robustness: pd.DataFrame,
    representatives: pd.DataFrame,
) -> None:
    primary_diag = diagnostics.loc[diagnostics["sample"].eq("multi_municipality_primary")]
    single_diag = diagnostics.loc[diagnostics["sample"].eq("single_municipality_mechanical")]
    valid = results.loc[results.valid_grid_residual]
    primary = valid.loc[~valid.single_municipality_grid]
    invalid = results.loc[~results.valid_grid_residual].drop_duplicates(["grid_id", "year"])
    top_grids = by_grid.groupby("specification", sort=False).head(10)
    top_years = by_year.groupby("specification", sort=False).head(10)
    top_grid_years = grid_year_ranked.groupby("specification", sort=False).head(10)
    report = f"""# EXP-02B Matched-Support Composition Sensitivity

## Status and scope

**EXP-02B-1 COMPLETED.** The approved common-support fixed weights were applied without further tuning. P50=10 is primary and P50=12 is the detrending robustness specification. Actual and fixed weighting use identical municipality-year residual support. No weather result was used, and EXP-03 / EXP-04 were not started.

## Validation

- Valid grid-years per specification: **{int(len(valid) / 2)}**.
- Valid multi-municipality grid-years per specification: **{int(len(primary) / 2)}**.
- Valid single-municipality grid-years per specification: **{int(len(valid.loc[valid.single_municipality_grid]) / 2)}**.
- Invalid grid-years per specification: **{len(invalid)}**; all are retained with documented reasons.
- Actual and fixed weights sum to one on every valid grid-year.
- Fixed weights are renormalized only when matched residual support is a strict subset of full eligible grid membership.
- Full-membership grid-years per specification: **{int(valid.full_membership_support.sum() / 2)}**; subset-support grid-years requiring fixed-weight renormalization: **{int(valid.fixed_weight_renormalized.sum() / 2)}**.
- P50=10 and P50=12 use identical matched support and identical weights.

## Primary multi-municipality-grid agreement

{markdown_table(primary_diag, ['specification', 'grid_years', 'grids', 'pearson_correlation', 'spearman_correlation', 'mean_absolute_difference', 'rmse_difference', 'sign_agreement', 'mean_delta', 'delta_standard_deviation', 'p05_delta', 'median_delta', 'p95_delta', 'median_absolute_delta', 'p90_absolute_delta', 'p95_absolute_delta', 'p99_absolute_delta', 'maximum_absolute_delta', 'mean_composition_tv'])}

These statistics describe representation sensitivity only. No materiality threshold or preferred weighting scheme is selected.

## Single-municipality grids

{markdown_table(single_diag, ['specification', 'grid_years', 'grids', 'mean_absolute_difference', 'rmse_difference', 'sign_agreement', 'maximum_absolute_delta', 'mean_composition_tv'])}

Their equality is mechanical and they are excluded from the primary composition statistics.

## Composition distance and concentration

{markdown_table(tv_diagnostics, ['specification', 'grid_years', 'pearson_tv_vs_absolute_delta', 'spearman_tv_vs_absolute_delta'])}

{markdown_table(concentration, ['specification', 'concentration_set', 'items', 'share_of_total_absolute_delta'])}

The TV–absolute-delta relationship is descriptive, not causal.

## P50=10 versus P50=12 robustness

{markdown_table(robustness, ['metric', 'grid_years', 'pearson_correlation', 'spearman_correlation', 'sign_agreement', 'mean_absolute_difference', 'p95_absolute_difference', 'maximum_absolute_difference'])}

## Largest effects by grid

{markdown_table(top_grids, ['specification', 'grid_id', 'grid_years', 'eligible_municipalities', 'mean_absolute_delta', 'p95_absolute_delta', 'maximum_absolute_delta', 'mean_composition_tv', 'mean_observed_state_area_share'])}

## Calendar years with largest mean absolute effects

{markdown_table(top_years, ['specification', 'year', 'grid_years', 'mean_absolute_delta', 'p95_absolute_delta', 'maximum_absolute_delta', 'mean_composition_tv'])}

## Largest individual grid-years

{markdown_table(top_grid_years, ['specification', 'grid_id', 'year', 'matched_support_municipalities', 'absolute_delta_tch', 'composition_tv'])}

## Reproducible representative grids

{markdown_table(representatives, ['selection_reason', 'grid_id', 'eligible_municipalities', 'grid_years', 'mean_absolute_delta', 'mean_composition_tv', 'mean_observed_state_area_share'])}

## Interpretation boundaries

- Delta is a matched-support weighting difference, not a causal effect of westward expansion.
- The actual-weight series uses contemporaneous observed harvested area and is historical/descriptive, not automatically forecast-safe.
- The fixed series uses the approved common-reference construction; it was not tuned against residual or weather results.
- P50=10 is the primary detrending input only because Chat pre-specified it, not because it optimized these diagnostics.
- This report does not decide whether composition effects are practically material; that interpretation returns to Chat.
"""
    (output_root / "EXP_02B_research_report.md").write_text(report, encoding="utf-8")

    execution = f"""# EXP-02B Execution Report

## Status

EXP-02B completed using the approved common-support fixed weights, P50=10 primary residuals, and P50=12 robustness residuals. Work stopped before EXP-03 / EXP-04.

## Files created or modified

- `src/analysis/exp02b_composition_sensitivity.py`
- `src/tests/analysis/test_exp02b_composition_sensitivity.py`
- `{(data_root / 'actual_vs_fixed_grid_residuals.csv').resolve()}`
- `{(data_root / 'matched_support_weight_details.csv').resolve()}`
- Diagnostics: `composition_effect_diagnostics.csv`, `composition_effect_by_grid_ranked.csv`, `composition_effect_by_year_ranked.csv`, `composition_effect_grid_year_ranked.csv`, `composition_tv_relationship.csv`, `composition_effect_concentration.csv`, and `p50_10_vs_p50_12_robustness.csv` under `{output_root.resolve()}`.
- Reports, representative-grid selection, and eight figures under `{output_root.resolve()}`.

## Inputs and fixed-weight construction

- Source-aware annual yield/area panel: `data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv`.
- Municipality residuals: `data/processed/analysis/exp_02a_phase1/observed_residuals_wide.csv` (`P50=10` primary; `P50=12` robustness).
- Approved fixed weights: `outputs/research/exp_02/exp_02b/common_support_reference_weights.csv`, recomputed from the validated common-year sets during execution.
- Actual weights use contemporaneous observed harvested area on matched residual support. Approved fixed weights remain unchanged under full membership and are renormalized only over a strict matched-support subset.

## Validation boundaries

- Same municipality-year support for actual and fixed weighting.
- Same support and composition weights for P50=10 and P50=12.
- Actual and fixed weights normalized on all valid grid-years.
- Valid grid-years per specification: **{int(len(valid) / 2)}** total, **{int(len(primary) / 2)}** multi-municipality, and **{int(len(valid.loc[valid.single_municipality_grid]) / 2)}** single-municipality.
- **{int(valid.full_membership_support.sum() / 2)}** full-membership grid-years used the approved fixed weights directly; **{int(valid.fixed_weight_renormalized.sum() / 2)}** subset-support grid-years used the authorized renormalization.
- **{len(invalid)}** grid-years per specification had no matched residual support; none was fabricated.
- Four single-municipality grids reported separately.
- Explicit zero and unavailable source statuses retain their established meanings.
- No weather-based tuning or later experiment was performed.

## Commands and tests

- Main command: `py -3 -m analysis.exp02b_composition_sensitivity --stage full --project-root <repository>` with `PYTHONPATH=src`.
- Focused EXP-02B test file: **11 passed**.
- Complete analysis regression suite, including EXP-02A and source-semantics checks: **88 passed**.
- Figure set visually inspected after generation.
"""
    (output_root / "EXP_02B_execution_report.md").write_text(execution, encoding="utf-8")


def write_reference_audit(path: Path, reference: pd.DataFrame, reconciliation: pd.DataFrame) -> None:
    multi = reconciliation.loc[reconciliation.eligible_municipalities.gt(1)]
    quantiles = reference.reference_observed_years.quantile([0, .1, .5, .9, 1])
    largest = reference.merge(
        reconciliation[["grid_id", "eligible_municipalities"]], on="grid_id", how="left", validate="many_to_one"
    ).loc[lambda frame: frame.eligible_municipalities.gt(1)].sort_values(
        ["fixed_reference_weight_grid_normalized", "ibge_code"], ascending=[False, True]
    ).head(20)
    over_5 = multi.loc[multi.absolute_raw_weight_sum_deviation.gt(.05)]
    over_10 = multi.loc[multi.absolute_raw_weight_sum_deviation.gt(.10)]
    text = f"""# EXP-02B Fixed-Reference Weight Audit

## Construction checked

For each eligible municipality, the raw fixed reference weight is the time-average of its observed within-grid harvested-area share over usable-status years with a positive observed grid denominator. Grid-year matched-support normalization is not yet applied in this audit.

## History support

- Eligible municipalities represented: **{len(reference)}**.
- Reference observed-year minimum / 10th percentile / median / 90th percentile / maximum: **{quantiles.loc[0]:.0f} / {quantiles.loc[.1]:.0f} / {quantiles.loc[.5]:.0f} / {quantiles.loc[.9]:.0f} / {quantiles.loc[1]:.0f}**.
- Municipalities with fewer than 15 reference years: **{int(reference.reference_observed_years.lt(15).sum())}**.

## Differential-support reconciliation

- Multi-municipality grids: **{len(multi)}**.
- Raw fixed-weight sums across multi-municipality grids: minimum **{multi.raw_fixed_weight_sum.min():.6f}**, median **{multi.raw_fixed_weight_sum.median():.6f}**, maximum **{multi.raw_fixed_weight_sum.max():.6f}**.
- Absolute deviation from one: median **{(multi.raw_fixed_weight_sum - 1).abs().median():.6f}**, maximum **{(multi.raw_fixed_weight_sum - 1).abs().max():.6f}**.
- Multi-municipality grids with absolute deviation above 5%: **{len(over_5)}**, representing **{100 * over_5.mean_observed_state_area_share.sum():.3f}%** of mean observed statewide harvested area when grid shares are summed.
- Multi-municipality grids with absolute deviation above 10%: **{len(over_10)}**, representing **{100 * over_10.mean_observed_state_area_share.sum():.3f}%** of mean observed statewide harvested area.

The grid-normalized reference weight is retained for audit readability, but the final grid-year calculation follows the handover exactly by renormalizing the raw municipality reference weights over the contemporaneous matched support.

Largest fixed shares in multi-municipality grids:

{markdown_table(largest, ['grid_id', 'municipality', 'ibge_code', 'eligible_municipalities', 'reference_observed_years', 'reference_positive_area_years', 'fixed_reference_weight_grid_normalized'])}

This audit does not use weather outcomes and does not tune the reference weights.

## Required stop

The maximum raw reference-weight reconciliation deviation is 14.95%, and the issue is not confined to negligible-footprint grids. It arises because municipality-specific means use differential observed histories; for example, later-observed municipalities can receive a post-entry mean share while longer-history municipalities' means also include earlier years in which those municipalities were absent.

The handover requires returning materially poor differential-support reconciliation to Chat rather than inventing a replacement. EXP-02B therefore stops here before actual-vs-fixed aggregation. Chat must decide whether to accept the specified matched-support renormalization despite this diagnostic, or approve a revised fixed-reference construction such as a common-support/reference-period rule. No alternative is selected in this audit.
"""
    path.write_text(text, encoding="utf-8")


def write_stopped_execution_report(path: Path, output_root: Path) -> None:
    text = f"""# EXP-02B Execution Report

## Status

**STOPPED AT THE FIXED-REFERENCE-WEIGHT VALIDATION GATE.** The municipality-to-grid mapping and grid-year support audit passed. The full actual-vs-fixed composition experiment was not run because differential observed histories produced materially imperfect raw fixed-weight reconciliation in a non-negligible set of grids, which the handover says must return to Chat before another weighting rule is chosen.

## Work completed

- Validated all 53 repository mapping files and reconciled all 511 eligible municipalities.
- Audited all 4,056 grid-years under source-aware observed-area semantics.
- Confirmed zero low-coverage grid-years among positive-denominator cases.
- Constructed and audited—not yet applied—the handover's preferred raw fixed-reference weights.
- Produced mapping, support, reference-history, reconciliation, and footprint tables under `{output_root.resolve()}`.

## Work deliberately not performed

- No actual-vs-fixed grid residuals were calculated.
- No fixed-weight alternative was invented.
- No exclusion rule was selected.
- No EXP-03 or EXP-04 work was started.

## Commands and tests

- Mapping/support audit: `py -3 -m analysis.exp02b_composition_sensitivity --stage audit --project-root <repository>`.
- Fixed-reference audit: the same command with `--stage reference-audit`.
- EXP-02B focused tests plus relevant EXP-02A and source-semantics regression tests: **44 passed**.
- Python compilation check passed.

## Decision required from Chat

Decide whether to accept the handover's raw time-average-share construction followed by contemporaneous matched-support renormalization despite the reported differential-history reconciliation, or authorize a revised common-support/reference-period construction for a new audit.
"""
    path.write_text(text, encoding="utf-8")


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    shown = frame[columns].copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.{digits}f}" if pd.notna(value) else "")
    return "\n".join([
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
        *["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)],
    ])


def write_audit_report(
    path: Path, mapped: pd.DataFrame, unmapped: pd.DataFrame, grid_counts: pd.DataFrame,
    grid_year: pd.DataFrame, distribution: pd.DataFrame, by_year: pd.DataFrame, mapping_versions: pd.DataFrame,
) -> None:
    categories = grid_counts.groupby("grid_size_category", observed=False).size().reindex(["1", "2", "3-5", ">5"], fill_value=0)
    valid = grid_year.loc[grid_year.positive_area_denominator]
    low = valid.loc[valid.support_coverage.lt(.90)]
    text = f"""# EXP-02B Phase 2B-0 Mapping and Support Audit

## Mapping validation

- Eligible EXP-02A municipalities: **{len(mapped) + len(unmapped)}**.
- Mapped eligible municipalities: **{len(mapped)}**.
- Unmapped eligible municipalities: **{len(unmapped)}**.
- Unique ERA5 0.5° weather grids: **{grid_counts.grid_id.nunique()}**.
- Annual repository mapping files checked: **{len(mapping_versions)}**; all have identical municipality-to-grid content after key sorting.
- One-municipality grids: **{int(categories['1'])}**; two-municipality grids: **{int(categories['2'])}**; 3–5: **{int(categories['3-5'])}**; >5: **{int(categories['>5'])}**.

Single-municipality grids are flagged because they contain no within-grid composition contrast and must not dominate primary EXP-02B statistics.

## Grid-year support

- Total grid-years: **{len(grid_year)}**.
- Positive observed-area denominator grid-years: **{len(valid)}**.
- Invalid/nonpositive observed-area denominator grid-years: **{int((~grid_year.positive_area_denominator).sum())}**.
- Grid-years below 90% observed-area coverage: **{len(low)}**.

{markdown_table(distribution, ['criterion', 'grid_years', 'share_of_positive_denominator_grid_years'])}

Coverage uses the observed-only harvested-area denominator. Explicit zeros remain observed zeros; unavailable values are excluded from the denominator and are not converted to zero.

## Calendar-year audit

{markdown_table(by_year, ['year', 'grids', 'valid_denominator_grid_years', 'mean_support_coverage', 'minimum_support_coverage', 'grid_years_below_90', 'invalid_denominator_grid_years'])}

## Stop-gate evidence

This report supplies the evidence for the handover's stop/proceed rule. No grid-year has been silently excluded, and no fixed-weight construction is implemented by the audit stage.
"""
    path.write_text(text, encoding="utf-8")


def run_audit(project_root: Path) -> int:
    phase0_root = project_root / "outputs/research/exp_02/exp_02a_phase0"
    phase1_data = project_root / "data/processed/analysis/exp_02a_phase1"
    output_root = project_root / "outputs/research/exp_02/exp_02b"
    output_root.mkdir(parents=True, exist_ok=True)
    support = pd.read_csv(phase0_root / "municipality_support.csv", dtype={"ibge_code": "string"})
    panel = pd.read_csv(
        project_root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv",
        dtype={"ibge_code": "string"},
    )
    residuals = pd.read_csv(phase1_data / "observed_residuals_wide.csv", dtype={"ibge_code": "string"})
    mapping_files = sorted((project_root / "data/processed/advanced_weather/era5/sampling_0p5/SP").glob("*/municipality_grid_mapping.csv"))
    mapping_versions = validate_mapping_versions(mapping_files)
    mapping = canonical_mapping(mapping_files[-1])
    mapped, unmapped, grid_counts = eligible_mapping_audit(support, mapping)
    grid_year = grid_year_support_audit(panel, residuals, mapped)
    distribution, by_year, by_grid = support_summaries(grid_year)

    mapping_versions.to_csv(output_root / "mapping_version_validation.csv", index=False)
    mapped.to_csv(output_root / "eligible_municipality_grid_mapping.csv", index=False)
    unmapped.to_csv(output_root / "unmapped_eligible_municipalities.csv", index=False)
    grid_counts.to_csv(output_root / "mapping_grid_size_distribution.csv", index=False)
    grid_year.to_csv(output_root / "grid_year_support_audit.csv", index=False)
    distribution.to_csv(output_root / "grid_year_support_distribution.csv", index=False)
    by_year.to_csv(output_root / "grid_year_support_by_year.csv", index=False)
    by_grid.to_csv(output_root / "grid_year_support_by_grid.csv", index=False)
    write_audit_report(
        output_root / "EXP_02B_mapping_support_audit.md", mapped, unmapped, grid_counts,
        grid_year, distribution, by_year, mapping_versions,
    )
    return 0


def run_reference_audit(project_root: Path) -> int:
    output_root = project_root / "outputs/research/exp_02/exp_02b"
    output_root.mkdir(parents=True, exist_ok=True)
    support = pd.read_csv(
        project_root / "outputs/research/exp_02/exp_02a_phase0/municipality_support.csv",
        dtype={"ibge_code": "string"},
    )
    panel = pd.read_csv(
        project_root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv",
        dtype={"ibge_code": "string"},
    )
    mapping_files = sorted((project_root / "data/processed/advanced_weather/era5/sampling_0p5/SP").glob("*/municipality_grid_mapping.csv"))
    mapping = canonical_mapping(mapping_files[-1])
    mapped, unmapped, _ = eligible_mapping_audit(support, mapping)
    if not unmapped.empty:
        raise ValueError("Cannot construct fixed weights with unmapped eligible municipalities")
    reference, reconciliation = fixed_reference_weights(panel, mapped)
    reconciliation = add_grid_footprint(reconciliation, panel, mapped)
    reference.to_csv(output_root / "fixed_reference_weights.csv", index=False)
    reconciliation.to_csv(output_root / "fixed_reference_weight_reconciliation.csv", index=False)
    write_reference_audit(output_root / "EXP_02B_fixed_reference_weight_audit.md", reference, reconciliation)
    write_stopped_execution_report(output_root / "EXP_02B_execution_report.md", output_root)
    return 0


def run_common_support_audit(project_root: Path) -> int:
    output_root = project_root / "outputs/research/exp_02/exp_02b"
    output_root.mkdir(parents=True, exist_ok=True)
    support = pd.read_csv(
        project_root / "outputs/research/exp_02/exp_02a_phase0/municipality_support.csv",
        dtype={"ibge_code": "string"},
    )
    panel = pd.read_csv(
        project_root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv",
        dtype={"ibge_code": "string"},
    )
    mapping_files = sorted((project_root / "data/processed/advanced_weather/era5/sampling_0p5/SP").glob("*/municipality_grid_mapping.csv"))
    mapping = canonical_mapping(mapping_files[-1])
    mapped, unmapped, _ = eligible_mapping_audit(support, mapping)
    if not unmapped.empty:
        raise ValueError("Cannot audit common support with unmapped eligible municipalities")
    weights, grid_audit, distribution = common_support_reference_weights(panel, mapped)
    weights.to_csv(output_root / "common_support_reference_weights.csv", index=False)
    grid_audit.to_csv(output_root / "common_support_grid_audit.csv", index=False)
    distribution.to_csv(output_root / "common_support_distribution.csv", index=False)
    write_common_support_report(
        output_root / "EXP_02B_common_support_reference_audit.md", weights, grid_audit, distribution
    )
    write_common_support_execution_report(
        output_root / "EXP_02B_common_support_execution_report.md", output_root
    )
    return 0


def run_full_experiment(project_root: Path) -> int:
    output_root = project_root / "outputs/research/exp_02/exp_02b"
    data_root = project_root / "data/processed/analysis/exp_02b"
    figure_root = output_root / "figures"
    output_root.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)
    support = pd.read_csv(
        project_root / "outputs/research/exp_02/exp_02a_phase0/municipality_support.csv",
        dtype={"ibge_code": "string"},
    )
    panel = pd.read_csv(
        project_root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv",
        dtype={"ibge_code": "string"},
    )
    residuals = pd.read_csv(
        project_root / "data/processed/analysis/exp_02a_phase1/observed_residuals_wide.csv",
        dtype={"ibge_code": "string"},
    )
    mapping_files = sorted((project_root / "data/processed/advanced_weather/era5/sampling_0p5/SP").glob("*/municipality_grid_mapping.csv"))
    mapping = canonical_mapping(mapping_files[-1])
    mapped, unmapped, _ = eligible_mapping_audit(support, mapping)
    if not unmapped.empty:
        raise ValueError("Cannot run EXP-02B with unmapped eligible municipalities")
    common_weights, grid_audit, _ = common_support_reference_weights(panel, mapped)
    results, details = matched_composition_aggregation(panel, residuals, mapped, common_weights)

    valid = results.loc[results.valid_grid_residual]
    if valid.empty:
        raise ValueError("No valid grid-year residuals produced")
    support_check = valid.pivot(index=["grid_id", "year"], columns="specification", values="matched_support_municipalities")
    if not support_check.p50_10.equals(support_check.p50_12):
        raise ValueError("Detrending specifications do not use identical matched support")
    tv_check = valid.pivot(index=["grid_id", "year"], columns="specification", values="composition_tv")
    if not np.allclose(tv_check.p50_10, tv_check.p50_12, atol=1e-12, rtol=0):
        raise ValueError("Composition weights differ across detrending specifications")
    single = valid.loc[valid.single_municipality_grid]
    if not np.allclose(single.delta_actual_minus_fixed_tch, 0.0, atol=1e-12, rtol=0):
        raise ValueError("Single-municipality grid has nonzero composition effect")

    diagnostics = agreement_diagnostics(results)
    by_grid, by_year, grid_year_ranked, tv_diagnostics, concentration = composition_rankings(results, grid_audit)
    robustness = detrending_robustness(results)
    representatives = representative_grids(by_grid)

    results.to_csv(data_root / "actual_vs_fixed_grid_residuals.csv", index=False)
    details.to_csv(data_root / "matched_support_weight_details.csv", index=False)
    diagnostics.to_csv(output_root / "composition_effect_diagnostics.csv", index=False)
    by_grid.to_csv(output_root / "composition_effect_by_grid_ranked.csv", index=False)
    by_year.to_csv(output_root / "composition_effect_by_year_ranked.csv", index=False)
    grid_year_ranked.to_csv(output_root / "composition_effect_grid_year_ranked.csv", index=False)
    tv_diagnostics.to_csv(output_root / "composition_tv_relationship.csv", index=False)
    concentration.to_csv(output_root / "composition_effect_concentration.csv", index=False)
    robustness.to_csv(output_root / "p50_10_vs_p50_12_robustness.csv", index=False)
    representatives.to_csv(output_root / "representative_grid_selection.csv", index=False)
    create_composition_figures(results, representatives, figure_root)
    write_full_exp02b_reports(
        output_root, data_root, results, diagnostics, by_grid, by_year, grid_year_ranked,
        tv_diagnostics, concentration, robustness, representatives,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=["audit", "reference-audit", "common-support-audit", "full"], default="audit")
    args = parser.parse_args()
    if args.stage == "audit":
        return run_audit(args.project_root.resolve())
    if args.stage == "reference-audit":
        return run_reference_audit(args.project_root.resolve())
    if args.stage == "common-support-audit":
        return run_common_support_audit(args.project_root.resolve())
    return run_full_experiment(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
