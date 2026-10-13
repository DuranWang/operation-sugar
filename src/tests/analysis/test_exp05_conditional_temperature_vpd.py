"""Focused checks for frozen EXP-05 alignment and conditional diagnostics."""

import numpy as np
import pandas as pd
import pytest

from analysis.exp05_conditional_temperature_vpd import (
    TEMP, VPD, Y10, Y12, YFIX, _fast_partial_stats, _pooled_from_year_cube,
    build_grid_slot_panel, fit_linear_sample, partial_correlation, pooled_nonlinear,
    restricted_grid_nonlinear,
    sample_tier, strata_diagnostics, synchronized_bootstrap,
)


def _synthetic_series(n=36, grid="g1", slot=-2):
    rng = np.random.default_rng(19)
    t = rng.normal(size=n)
    v = .6 * t + rng.normal(size=n) * .8
    y = 2 * v - .5 * t + rng.normal(size=n)
    return pd.DataFrame({"grid_id": grid, "month_slot": slot,
                         "calendar_month_label": "Feb_(t)",
                         "yield_year": np.arange(1982, 1982 + n),
                         Y10: y, Y12: y + .1, YFIX: y - .1,
                         TEMP: t, VPD: v, "primary_eligible": True,
                         "actual_weight_denominator_ha": 100.0})


def test_linear_partial_is_two_sided_and_matches_partial_r2():
    sample = _synthetic_series()
    result = fit_linear_sample(sample)
    manual = partial_correlation(sample[Y10], sample[VPD], sample[TEMP])
    assert result["partial_r_y_vpd_given_t"] == pytest.approx(manual)
    assert result["partial_r2_vpd_given_t"] == pytest.approx(manual ** 2)
    assert result["partial_identity_max_error"] < 1e-10
    fast = _fast_partial_stats(sample[[Y10, TEMP, VPD]].to_numpy())
    assert fast[0] == pytest.approx(manual)
    assert fast[1] == pytest.approx(result["partial_r_y_t_given_vpd"])


def test_sample_tiers_and_restricted_nonlinear_gate():
    assert [sample_tier(n) for n in [14, 15, 19, 20, 29, 30]] == [
        "lt15", "15_19_low_n", "15_19_low_n", "20_29_primary_linear",
        "20_29_primary_linear", "ge30_linear_and_restricted_quadratic"]
    panel = pd.concat([_synthetic_series(29, "g1"), _synthetic_series(36, "g2")])
    result = restricted_grid_nonlinear(panel)
    assert set(result.grid_id) == {"g2"}
    assert set(result.direction) == {"VPD_given_T", "T_given_VPD"}
    assert result.status.eq("estimable").all()
    assert (result.delta_r2_after_quadratic_control >= -1e-10).all()


def test_tertiles_use_average_ranks_and_do_not_fit_sparse_slopes():
    sample = _synthetic_series(18)
    sample[TEMP] = np.repeat([1., 2., 3.], 6)
    result = strata_diagnostics(sample)
    assert len(result) == 6
    assert result.n_stratum.eq(6).all()
    assert result.descriptive_slope_tch_per_tested_unit.isna().all()
    assert result.slope_status.eq("not_fitted_n_lt_10_or_degenerate").all()
    assert result.tie_rule.str.contains("average ranks").all()


def test_alignment_and_paired_only_weather_gate_without_other_month_filter():
    targets = pd.DataFrame({"grid_id": ["g1"], "yield_year": [2000],
                            Y10: [2.], Y12: [2.], YFIX: [2.],
                            "actual_weight_denominator_ha": [100.],
                            "grid_latitude": [0.], "grid_longitude": [0.],
                            "single_municipality_grid": [False]})
    weights = pd.DataFrame({"grid_id": ["g1", "g1"], "year": [2000, 2000],
                            "ibge_code": pd.Series(["01", "02"], dtype="string"),
                            "actual_weight": [.5, .5]})
    slots = pd.DataFrame({"month_slot": [-2, -4], "relative_month": ["m_-2", "m_-4"],
                          "source_year_offset": [0, -1], "source_calendar_month": [2, 12],
                          "calendar_month_label": ["Feb_(t)", "Dec_(t-1)"],
                          "primary_window": [True, True], "extended_only": [False, False],
                          "yield_year_alignment": ["test", "test"], "source_artifact": ["test", "test"]})
    weather = pd.DataFrame({"grid_id": ["g1"] * 4,
                            "ibge_code": pd.Series(["01", "02", "01", "02"], dtype="string"),
                            "source_year": [2000, 2000, 1999, 1999],
                            "source_calendar_month": [2, 2, 12, 12],
                            TEMP: [20., 22., 19., np.nan], VPD: [1., 2., 1., 1.]})
    panel = build_grid_slot_panel(targets, weights, weather, slots)
    assert len(panel) == 2
    feb = panel.loc[panel.month_slot.eq(-2)].iloc[0]
    dec = panel.loc[panel.month_slot.eq(-4)].iloc[0]
    assert feb.source_year == 2000 and feb[TEMP] == pytest.approx(21.)
    assert feb[VPD] == pytest.approx(1.5) and feb.primary_eligible
    assert dec.source_year == 1999 and not dec.primary_eligible
    assert dec.missingness_reason == "temperature_missing_or_partial_weight_coverage"


def test_synchronized_bootstrap_keeps_grid_missingness_masks_and_is_reproducible():
    panel = pd.concat([_synthetic_series(30, "g1"), _synthetic_series(30, "g2")])
    panel.loc[(panel.grid_id == "g2") & (panel.yield_year == 1987), "primary_eligible"] = False
    a = synchronized_bootstrap(panel, replicates=3, seed=7)
    b = synchronized_bootstrap(panel, replicates=3, seed=7)
    pd.testing.assert_frame_equal(a, b)
    assert set(a.block_length_years) == {1, 3, 5}
    assert a.n_input_grids.eq(2).all()
    assert (a.n_estimable_grids + a.n_inestimable_grids).eq(2).all()


def test_pooled_resample_sufficient_statistics_match_direct_fixed_intercept_fit():
    panel = pd.concat([_synthetic_series(30, "g1"), _synthetic_series(30, "g2")])
    # Add a grid-specific outcome intercept; within-grid fit must remove it.
    panel.loc[panel.grid_id.eq("g2"), Y10] += 7
    direct = pooled_nonlinear(panel).iloc[0]
    cube = np.full((2, 45, 3), np.nan)
    for grid_idx, grid in enumerate(["g1", "g2"]):
        group = panel.loc[panel.grid_id.eq(grid)]
        cube[grid_idx, group.yield_year.to_numpy(int) - 1981] = group[[Y10, TEMP, VPD]].to_numpy()
    fast = _pooled_from_year_cube(cube, np.ones(45, dtype=int))
    assert fast["status"] == "estimable"
    for name in ["L", "Q_T", "Q_V", "Q", "I"]:
        assert fast[f"r2_{name}"] == pytest.approx(getattr(direct, f"r2_{name}"), abs=1e-10)
