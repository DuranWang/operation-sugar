from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.exp02a_detrending import (
    SPECIFICATIONS,
    amplitude_response,
    fit_all,
    fit_linear,
    fit_second_difference,
    lambda_from_p50,
    long_output,
    second_difference_matrix,
)


@pytest.mark.parametrize("period", [6.0, 10.0, 12.0])
def test_lambda_definition_has_half_amplitude_response(period):
    penalty = lambda_from_p50(period)
    assert amplitude_response(period, penalty) == pytest.approx(0.5, abs=1e-12)


def test_lambda_values_are_numerically_stable():
    assert lambda_from_p50(6) == pytest.approx(1.0)
    assert lambda_from_p50(10) == pytest.approx(6.854101966249682)
    assert lambda_from_p50(12) == pytest.approx(13.928203230275503)


def test_second_difference_annihilates_linear_sequence():
    sequence = 3.0 + 2.5 * np.arange(12)
    assert np.allclose(second_difference_matrix(len(sequence)) @ sequence, 0.0)


def test_penalized_fit_satisfies_normal_equations_with_missing_years():
    values = np.array([10.0, np.nan, 13.0, 18.0, np.nan, 22.0])
    observed = np.isfinite(values)
    penalty = lambda_from_p50(10)
    fitted = fit_second_difference(values, observed, penalty)
    d2 = second_difference_matrix(len(values))
    system = np.diag(observed.astype(float)) + penalty * (d2.T @ d2)
    rhs = np.where(observed, values, 0.0)
    assert np.allclose(system @ fitted, rhs)
    assert np.isfinite(fitted).all()


def test_linear_fit_uses_only_observed_years():
    years = np.arange(2000, 2006)
    values = 5.0 + 2.0 * (years - 2000).astype(float)
    values[[1, 4]] = np.nan
    observed = np.isfinite(values)
    fitted = fit_linear(years, values, observed)
    assert np.allclose(fitted, 5.0 + 2.0 * (years - 2000))


@pytest.fixture(scope="module")
def real_phase1_fit():
    root = Path(__file__).resolve().parents[3]
    panel = pd.read_csv(
        root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv",
        dtype={"ibge_code": "string"},
    )
    support = pd.read_csv(
        root / "outputs/research/exp_02/exp_02a_phase0/municipality_support.csv",
        dtype={"ibge_code": "string"},
    )
    panel["valid_yield_for_detrending"] = panel["valid_yield_for_detrending"].astype(bool)
    wide, gaps = fit_all(panel, support)
    return panel, support, wide, gaps


def test_approved_gate_reconciles_to_511_municipalities(real_phase1_fit):
    _, support, wide, _ = real_phase1_fit
    eligible = support.n_valid_years.ge(15) & support.calendar_span_years.ge(20)
    assert int(eligible.sum()) == 511
    assert wide.ibge_code.nunique() == 511
    assert int(wide.observed_valid_yield.sum()) == 20931


def test_grids_match_first_and_last_valid_years(real_phase1_fit):
    _, _, wide, _ = real_phase1_fit
    check = wide.groupby("ibge_code").agg(
        grid_first=("year", "min"), grid_last=("year", "max"),
        first=("first_valid_year", "first"), last=("last_valid_year", "first"),
    )
    assert check.grid_first.eq(check["first"]).all()
    assert check.grid_last.eq(check["last"]).all()


def test_residuals_exist_only_for_observed_valid_yields(real_phase1_fit):
    panel, _, wide, _ = real_phase1_fit
    long = long_output(wide)
    assert long.loc[long.observed_valid_yield, "residual_tch"].notna().all()
    assert long.loc[~long.observed_valid_yield, "residual_tch"].isna().all()
    assert long.duplicated(["ibge_code", "year", "specification"]).sum() == 0
    assert set(long.specification) == set(SPECIFICATIONS)
    assert {"production_source_status", "harvested_area_source_status"}.issubset(long.columns)
    invalid_source = panel.loc[
        panel.harvested_area_source_status.isin(["explicit_zero", "unavailable", "numeric_zero"]),
        ["ibge_code", "year"],
    ]
    observed_keys = long.loc[long.observed_valid_yield, ["ibge_code", "year"]].drop_duplicates()
    assert invalid_source.merge(observed_keys, on=["ibge_code", "year"]).empty


def test_internal_gap_inventory_matches_municipality_maximum(real_phase1_fit):
    _, support, _, gaps = real_phase1_fit
    eligible = support.loc[support.n_valid_years.ge(15) & support.calendar_span_years.ge(20)]
    expected = eligible.set_index("ibge_code").max_internal_gap_years.astype(int)
    actual = gaps.groupby("ibge_code").gap_length.max().reindex(expected.index, fill_value=0).astype(int)
    assert actual.equals(expected)
