from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.exp02b_top_tail_diagnostic import (
    event_summaries,
    municipality_decomposition,
    p50_12_crosscheck,
    select_top_events,
)


def _event(specification="p50_10", delta=-19.271959625211203):
    return {
        "grid_id": "era5_-20.50_-50.00", "year": 1981, "specification": specification,
        "eligible_municipalities": 2, "matched_support_municipalities": 2,
        "single_municipality_grid": False, "full_membership_support": True,
        "fixed_weight_renormalized": False, "valid_grid_residual": True,
        "actual_grid_residual_tch": -19.0, "fixed_grid_residual_tch": -19.0 - delta,
        "delta_actual_minus_fixed_tch": delta, "absolute_delta_tch": abs(delta),
        "composition_tv": .5,
    }


def test_select_top_event_reproduces_reported_maximum():
    ranked = pd.DataFrame([_event()])
    results = pd.DataFrame([_event()])
    selected = select_top_events(ranked, results, n=1)
    assert selected.iloc[0].rank_absolute_delta_p50_10 == 1
    assert selected.iloc[0].grid_id == "era5_-20.50_-50.00"
    assert selected.iloc[0].year == 1981


def test_decomposition_reconciles_weights_contributions_and_artifact_flags():
    ranked = pd.DataFrame([_event(delta=6.0)])
    results = ranked.copy()
    top = select_top_events(ranked, results, n=1)
    weights = pd.DataFrame({
        "grid_id": ["era5_-20.50_-50.00"] * 2,
        "year": [1981, 1981],
        "ibge_code": pd.Series(["1", "2"], dtype="string"),
        "municipality": ["A", "B"], "eligible_municipalities": [2, 2],
        "harvested_area_source_status": ["numeric_positive", "numeric_positive"],
        "harvested_area_source_value": [90.0, 10.0],
        "candidate_fixed_weight": [.4, .6], "actual_weight": [.9, .1],
        "fixed_weight": [.4, .6], "actual_minus_fixed_weight": [.5, -.5],
        "fixed_weight_renormalized": [False, False],
        "residual_p50_10": [10.0, -2.0], "residual_p50_12": [9.0, -1.0],
    })
    residuals = pd.DataFrame({
        "ibge_code": pd.Series(["1", "2"], dtype="string"), "year": [1981, 1981],
        "observed_valid_yield": [True, True], "residual_p50_10": [10.0, -2.0],
        "first_valid_year": [1981, 1980], "last_valid_year": [2000, 2000],
        "endpoint_distance_years": [0, 1], "max_internal_gap_years": [0, 12],
        "gap_stratum": ["0", ">10"], "distance_to_nearest_internal_gap": [np.nan, 1],
        "nearest_internal_gap_length": [np.nan, 12],
    })
    decomposition = municipality_decomposition(top, weights, residuals)
    summary, artifacts = event_summaries(top, decomposition)
    assert decomposition.contribution_p50_10_tch.sum() == pytest.approx(6.0)
    assert summary.iloc[0].sum_actual_weights == pytest.approx(1.0)
    assert summary.iloc[0].sum_fixed_weights == pytest.approx(1.0)
    assert summary.iloc[0].largest_negative_contributor == ""
    assert pd.isna(summary.iloc[0].largest_negative_contribution_tch)
    assert artifacts.iloc[0].any_within_one_year_of_endpoint
    assert artifacts.iloc[0].any_immediately_adjacent_to_internal_missing_gap
    assert artifacts.iloc[0].any_long_internal_gap_history_gt10


def test_p50_12_crosscheck_keeps_same_event_support():
    p10 = _event(delta=-10.0)
    top = pd.DataFrame([p10])
    top.insert(0, "rank_absolute_delta_p50_10", [1])
    results = pd.DataFrame([p10, _event(specification="p50_12", delta=-11.0)])
    cross = p50_12_crosscheck(top, results)
    assert len(cross) == 1
    assert cross.iloc[0].same_sign
    assert cross.iloc[0].absolute_delta_change_tch == pytest.approx(1.0)


def test_real_top10_contribution_identity_and_source_semantics():
    root = Path(__file__).resolve().parents[3]
    output = root / "outputs/research/exp_02/exp_02b"
    data = root / "data/processed/analysis/exp_02b"
    results = pd.read_csv(data / "actual_vs_fixed_grid_residuals.csv")
    ranked = pd.read_csv(output / "composition_effect_grid_year_ranked.csv")
    weights = pd.read_csv(data / "matched_support_weight_details.csv", dtype={"ibge_code": "string"})
    residuals = pd.read_csv(
        root / "data/processed/analysis/exp_02a_phase1/observed_residuals_wide.csv",
        dtype={"ibge_code": "string"},
    )
    top = select_top_events(ranked, results)
    decomposition = municipality_decomposition(top, weights, residuals)
    summary, _ = event_summaries(top, decomposition)
    cross = p50_12_crosscheck(top, results)
    assert len(top) == 10
    assert decomposition.groupby(["grid_id", "year"]).ngroups == 10
    assert not decomposition.harvested_area_source_status.eq("unavailable").any()
    assert np.allclose(summary.sum_actual_weights, 1.0)
    assert np.allclose(summary.sum_fixed_weights, 1.0)
    assert np.allclose(summary.sum_municipality_contributions_tch, summary.delta_p50_10_tch)
    assert cross.same_sign.all()
    assert cross.rank_absolute_delta_p50_12.le(10).all()
