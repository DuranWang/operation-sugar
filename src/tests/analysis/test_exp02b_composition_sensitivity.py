from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.exp02b_composition_sensitivity import (
    canonical_mapping,
    common_support_reference_weights,
    eligible_mapping_audit,
    fixed_reference_weights,
    grid_year_support_audit,
    matched_composition_aggregation,
    validate_mapping_frame,
)


def test_mapping_validation_rejects_duplicate_municipality():
    mapping = pd.DataFrame({
        "ibge_code": ["1", "1"], "municipality": ["A", "A"],
        "grid_id": ["g", "g"], "grid_latitude": [0, 0], "grid_longitude": [0, 0],
    })
    with pytest.raises(ValueError, match="not unique"):
        validate_mapping_frame(mapping)


def _synthetic_panel():
    return pd.DataFrame({
        "ibge_code": ["1", "2", "1", "2"],
        "municipality": ["A", "B", "A", "B"],
        "year": [2000, 2000, 2001, 2001],
        "harvested_area_source_status": ["numeric_positive", "numeric_positive", "unavailable", "explicit_zero"],
        "harvested_area_source_value": [10.0, 20.0, float("nan"), 0.0],
    })


def _synthetic_mapping():
    return pd.DataFrame({
        "ibge_code": pd.Series(["1", "2"], dtype="string"),
        "grid_id": ["g", "g"], "grid_latitude": [0.0, 0.0], "grid_longitude": [0.0, 0.0],
    })


def test_support_coverage_uses_matched_residual_support_and_observed_area_only():
    residuals = pd.DataFrame({"ibge_code": pd.Series(["1"], dtype="string"), "year": [2000], "residual_p50_10": [2.0]})
    result = grid_year_support_audit(_synthetic_panel(), residuals, _synthetic_mapping()).set_index("year")
    assert result.loc[2000, "observed_harvested_area_denominator_ha"] == 30.0
    assert result.loc[2000, "matched_support_harvested_area_ha"] == 10.0
    assert result.loc[2000, "support_coverage"] == pytest.approx(1 / 3)
    assert result.loc[2000, "coverage_bucket"] == "<90%"
    assert not result.loc[2001, "positive_area_denominator"]
    assert pd.isna(result.loc[2001, "support_coverage"])


def test_fixed_reference_mean_exposes_differential_support_reconciliation():
    panel = _synthetic_panel().copy()
    panel.loc[panel.year.eq(2001) & panel.ibge_code.eq("1"), ["harvested_area_source_status", "harvested_area_source_value"]] = ["numeric_positive", 10.0]
    panel.loc[panel.year.eq(2001) & panel.ibge_code.eq("2"), ["harvested_area_source_status", "harvested_area_source_value"]] = ["numeric_positive", 10.0]
    panel.loc[panel.year.eq(2000) & panel.ibge_code.eq("2"), ["harvested_area_source_status", "harvested_area_source_value"]] = ["unavailable", float("nan")]
    reference, reconciliation = fixed_reference_weights(panel, _synthetic_mapping())
    weights = reference.set_index("ibge_code").fixed_reference_weight_raw
    assert weights.loc["1"] == pytest.approx(0.75)
    assert weights.loc["2"] == pytest.approx(0.5)
    assert reconciliation.iloc[0].raw_fixed_weight_sum == pytest.approx(1.25)
    assert reference.fixed_reference_weight_grid_normalized.sum() == pytest.approx(1.0)


def test_common_support_uses_only_years_with_every_status_observed():
    weights, audit, distribution = common_support_reference_weights(
        _synthetic_panel(), _synthetic_mapping()
    )
    assert audit.iloc[0].common_reference_years == 1
    assert audit.iloc[0].first_common_year == 2000
    assert audit.iloc[0].last_common_year == 2000
    assert audit.iloc[0].common_period_calendar_span == 1
    assert audit.iloc[0].candidate_fixed_weights_sum_to_one
    candidate = weights.set_index("ibge_code").candidate_fixed_weight
    assert candidate.loc["1"] == pytest.approx(1 / 3)
    assert candidate.loc["2"] == pytest.approx(2 / 3)
    counts = distribution.set_index("support_group").grids
    assert counts.loc["<10"] == 1
    assert counts.loc["10-14"] == 0


def test_matched_weights_handle_zero_unavailable_and_invalid_denominator():
    panel = pd.DataFrame({
        "ibge_code": pd.Series(["1", "2", "1", "2", "1", "2"], dtype="string"),
        "municipality": ["A", "B"] * 3,
        "year": [2000, 2000, 2001, 2001, 2002, 2002],
        "harvested_area_source_status": [
            "numeric_positive", "explicit_zero", "numeric_positive", "unavailable", "explicit_zero", "explicit_zero"
        ],
        "harvested_area_source_value": [10.0, 0.0, 10.0, float("nan"), 0.0, 0.0],
    })
    mapping = _synthetic_mapping()
    residuals = pd.DataFrame({
        "ibge_code": pd.Series(["1", "2", "1", "2", "1", "2"], dtype="string"),
        "year": [2000, 2000, 2001, 2001, 2002, 2002],
        "residual_p50_10": [2.0, 1.0, 2.0, 1.0, 2.0, 1.0],
        "residual_p50_12": [3.0, 1.5, 3.0, 1.5, 3.0, 1.5],
    })
    fixed = pd.DataFrame({
        "grid_id": ["g", "g"], "ibge_code": pd.Series(["1", "2"], dtype="string"),
        "candidate_fixed_weight": [.4, .6],
    })
    results, details = matched_composition_aggregation(panel, residuals, mapping, fixed)
    year_2000 = results.loc[(results.year.eq(2000)) & results.specification.eq("p50_10")].iloc[0]
    assert year_2000.matched_support_municipalities == 2
    assert year_2000.actual_grid_residual_tch == pytest.approx(2.0)
    assert year_2000.fixed_grid_residual_tch == pytest.approx(1.4)
    assert year_2000.composition_tv == pytest.approx(.6)
    zero_detail = details.loc[(details.year.eq(2000)) & details.ibge_code.eq("2")].iloc[0]
    assert zero_detail.actual_weight == 0
    year_2001 = results.loc[(results.year.eq(2001)) & results.specification.eq("p50_10")].iloc[0]
    assert year_2001.matched_support_municipalities == 1
    assert year_2001.fixed_weight_renormalized
    assert year_2001.delta_actual_minus_fixed_tch == pytest.approx(0)
    year_2002 = results.loc[(results.year.eq(2002)) & results.specification.eq("p50_10")].iloc[0]
    assert not year_2002.valid_grid_residual
    assert year_2002.invalid_reason == "nonpositive_actual_weight_denominator"


def test_single_municipality_grid_has_mechanical_equality():
    panel = pd.DataFrame({
        "ibge_code": pd.Series(["1"], dtype="string"), "municipality": ["A"], "year": [2000],
        "harvested_area_source_status": ["numeric_positive"], "harvested_area_source_value": [10.0],
    })
    mapping = pd.DataFrame({
        "ibge_code": pd.Series(["1"], dtype="string"), "grid_id": ["g"],
        "grid_latitude": [0.0], "grid_longitude": [0.0],
    })
    residuals = pd.DataFrame({
        "ibge_code": pd.Series(["1"], dtype="string"), "year": [2000],
        "residual_p50_10": [2.0], "residual_p50_12": [3.0],
    })
    results, details = matched_composition_aggregation(panel, residuals, mapping, pd.DataFrame(columns=["grid_id", "ibge_code", "candidate_fixed_weight"]))
    assert results.single_municipality_grid.all()
    assert results.delta_actual_minus_fixed_tch.eq(0).all()
    assert results.composition_tv.eq(0).all()
    assert details.actual_weight.eq(1).all()
    assert details.fixed_weight.eq(1).all()


@pytest.fixture(scope="module")
def real_inputs():
    root = Path(__file__).resolve().parents[3]
    support = pd.read_csv(root / "outputs/research/exp_02/exp_02a_phase0/municipality_support.csv", dtype={"ibge_code": "string"})
    panel = pd.read_csv(
        root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv",
        dtype={"ibge_code": "string"},
    )
    residuals = pd.read_csv(root / "data/processed/analysis/exp_02a_phase1/observed_residuals_wide.csv", dtype={"ibge_code": "string"})
    mapping_path = root / "data/processed/advanced_weather/era5/sampling_0p5/SP/2025-01-01_2025-12-31/municipality_grid_mapping.csv"
    mapping = canonical_mapping(mapping_path)
    return support, panel, residuals, mapping


def test_real_mapping_reconciles_all_eligible_municipalities(real_inputs):
    support, _, _, mapping = real_inputs
    mapped, unmapped, grid_counts = eligible_mapping_audit(support, mapping)
    assert len(mapped) == 511
    assert unmapped.empty
    assert grid_counts.grid_id.nunique() == 78
    assert int(grid_counts.single_municipality_grid.sum()) == 4


def test_real_positive_denominator_grid_years_have_complete_area_coverage(real_inputs):
    support, panel, residuals, mapping = real_inputs
    mapped, _, _ = eligible_mapping_audit(support, mapping)
    audit = grid_year_support_audit(panel, residuals, mapped)
    valid = audit.loc[audit.positive_area_denominator]
    assert len(audit) == 4056
    assert len(valid) == 3773
    assert valid.support_coverage.eq(1.0).all()
    assert int((~audit.positive_area_denominator).sum()) == 283


def test_real_fixed_reference_history_and_reconciliation_issue(real_inputs):
    support, panel, _, mapping = real_inputs
    mapped, _, _ = eligible_mapping_audit(support, mapping)
    reference, reconciliation = fixed_reference_weights(panel, mapped)
    assert len(reference) == 511
    assert reference.reference_observed_years.min() == 15
    assert all(
        value == pytest.approx(1.0)
        for value in reference.groupby("grid_id").fixed_reference_weight_grid_normalized.sum()
    )
    assert reconciliation.raw_fixed_weight_sum.max() == pytest.approx(1.1495426797552781)


def test_real_common_support_reference_reconciles_all_multi_grids(real_inputs):
    support, panel, _, mapping = real_inputs
    mapped, _, _ = eligible_mapping_audit(support, mapping)
    weights, audit, distribution = common_support_reference_weights(panel, mapped)
    assert len(audit) == 74
    assert len(weights) == 507
    assert audit.common_reference_years.min() == 18
    assert audit.common_reference_years.max() == 52
    assert audit.candidate_fixed_weights_sum_to_one.all()
    counts = distribution.set_index("support_group").grids
    assert counts.to_dict() == {"<10": 0, "10-14": 0, "15-19": 1, ">=20": 73}


def test_real_matched_composition_support_and_weights_are_reconciled(real_inputs):
    support, panel, residuals, mapping = real_inputs
    mapped, _, _ = eligible_mapping_audit(support, mapping)
    weights, _, _ = common_support_reference_weights(panel, mapped)
    results, details = matched_composition_aggregation(panel, residuals, mapped, weights)

    valid = results.loc[results.valid_grid_residual]
    assert valid.groupby("specification").size().to_dict() == {"p50_10": 3773, "p50_12": 3773}
    assert valid.groupby("specification").matched_support_municipalities.sum().nunique() == 1
    assert valid.groupby("specification").composition_tv.sum().nunique() == 1
    assert not details.harvested_area_source_status.eq("unavailable").any()

    weight_sums = details.groupby(["grid_id", "year"])[["actual_weight", "fixed_weight"]].sum()
    assert np.allclose(weight_sums.actual_weight, 1.0)
    assert np.allclose(weight_sums.fixed_weight, 1.0)

    multi = valid.loc[~valid.single_municipality_grid]
    single = valid.loc[valid.single_municipality_grid]
    assert multi.groupby("specification").size().to_dict() == {"p50_10": 3694, "p50_12": 3694}
    assert single.groupby("specification").size().to_dict() == {"p50_10": 79, "p50_12": 79}
    assert single.delta_actual_minus_fixed_tch.eq(0.0).all()
    assert single.composition_tv.eq(0.0).all()
    assert valid.fixed_weight_renormalized.eq(~valid.full_membership_support).all()
