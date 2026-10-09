from pathlib import Path

import pandas as pd
import pytest

from analysis.exp03_checkpoint2b_spatial_heterogeneity import (
    YIELD_COLUMN,
    direction_relation,
    identify_problematic_cells,
    leave_one_municipality_out_influence,
    municipality_weight_summary,
)


def test_direction_relation_excludes_exact_zero():
    assert direction_relation(.2, .1) == "agree"
    assert direction_relation(-.2, .1) == "disagree"
    assert direction_relation(0.0, .1) == "zero_excluded"


def test_problematic_cell_counts_grid_directions_explicitly():
    continuous = pd.DataFrame({
        "relative_month_index": [-2], "relative_month": ["m_-2"],
        "calendar_month_label": ["Feb_(t)"], "weather_variable": ["rain"],
        "pooled_within_grid_rank_rho": [.1], "median_grid_rho": [-.1],
        "mean_grid_rho": [-.05], "pct_grids_agree_with_pooled_direction": [.25],
        "standardized_high_minus_low": [.2],
        "categorical_continuous_sign_agreement": [True],
    })
    details = pd.DataFrame({
        "relative_month_index": [-2] * 4, "weather_variable": ["rain"] * 4,
        "usable": [True] * 4, "grid_id": ["a", "b", "c", "d"],
        "spearman_rho": [.2, -.2, -.3, 0.0],
    })
    problem, by_variable, by_month = identify_problematic_cells(continuous, details)
    row = problem.iloc[0]
    assert row.n_usable_grids == 4
    assert row.n_directional_grids == 3
    assert row.n_zero_rho_grids_excluded == 1
    assert row.n_grids_agreeing_with_pooled_direction == 1
    assert row.n_grids_disagreeing_with_pooled_direction == 2
    assert row.pct_grids_agreeing == pytest.approx(1 / 3)
    assert by_variable.problematic_cells.iloc[0] == 1
    assert by_month.problematic_cells.iloc[0] == 1


def test_weight_summary_treats_absent_support_year_as_zero():
    mapping = pd.DataFrame({
        "era5_grid_id": ["g", "g"], "ibge_code": ["1", "2"],
        "municipality": ["A", "B"], "nasa_weather_group_id": ["n1", "n2"],
        "era5_grid_latitude": [-22.0, -22.0], "era5_grid_longitude": [-48.0, -48.0],
    })
    valid = pd.DataFrame({"grid_id": ["g", "g"], "year": [2000, 2001]})
    weights = pd.DataFrame({
        "grid_id": ["g", "g", "g"], "year": [2000, 2000, 2001],
        "ibge_code": ["1", "2", "1"], "actual_weight": [.6, .4, 1.0],
    })
    result = municipality_weight_summary(mapping, weights, valid).set_index("ibge_code")
    assert result.loc["1", "mean_weight"] == pytest.approx(.8)
    assert result.loc["2", "mean_weight"] == pytest.approx(.2)
    assert result.loc["2", "number_valid_years"] == 1
    assert result.loc["2", "minimum_weight"] == 0


def test_leave_one_out_reaggregates_both_yield_and_weather_and_can_flip_sign():
    years = [2000, 2001, 2002, 2003]
    weights_rows = []
    weather_rows = []
    y_a, y_b = [1, 2, 3, 4], [4, 3, 2, 1]
    for index, year in enumerate(years):
        weights_rows.extend([
            {"grid_id": "g", "year": year, "ibge_code": "1", "actual_weight": .2, "residual_p50_10": y_a[index]},
            {"grid_id": "g", "year": year, "ibge_code": "2", "actual_weight": .8, "residual_p50_10": y_b[index]},
        ])
        weather_rows.extend([
            {"ibge_code": "1", "source_year": year, "source_calendar_month": 3, "weather": index + 1},
            {"ibge_code": "2", "source_year": year, "source_calendar_month": 3, "weather": index + 1},
        ])
    weights = pd.DataFrame(weights_rows)
    aligned = pd.DataFrame({
        "grid_id": ["g"] * 4, "year": years, "source_year": years,
        "source_calendar_month": [3] * 4, "relative_month_index": [-1] * 4,
        YIELD_COLUMN: [3.4, 2.8, 2.2, 1.6], "weather": [1, 2, 3, 4],
    })
    disagreeing = pd.DataFrame({
        "era5_grid_id": ["g"], "relative_month_index": [-1],
        "relative_month": ["m_-1"], "calendar_interpretation": ["Mar_(t)"],
        "weather_variable": ["weather"], "pooled_rho": [.1],
        "grid_specific_spearman_rho": [-1.0],
    })
    summary = pd.DataFrame({
        "grid_id": ["g", "g"], "ibge_code": ["1", "2"],
        "municipality": ["A", "B"], "mean_weight": [.2, .8],
        "maximum_weight": [.2, .8], "share_years_largest_weight": [0.0, 1.0],
    })
    result = leave_one_municipality_out_influence(
        disagreeing, aligned, weights, pd.DataFrame(weather_rows), summary
    ).set_index("ibge_code_removed")
    assert result.loc["2", "leave_one_out_rho"] == pytest.approx(1.0)
    assert bool(result.loc["2", "sign_flips"])
    assert bool(result.loc["2", "high_influence"])
    assert result.loc["1", "leave_one_out_rho"] == pytest.approx(-1.0)


def test_real_checkpoint2b_outputs_have_expected_cardinality():
    root = Path(__file__).resolve().parents[3]
    output = root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint2b"
    problem = pd.read_csv(output / "checkpoint2b_problematic_cells.csv")
    disagreeing = pd.read_csv(output / "checkpoint2b_disagreeing_grids.csv")
    frequency = pd.read_csv(output / "checkpoint2b_grid_disagreement_frequency.csv")
    composition = pd.read_csv(output / "checkpoint2b_disagreeing_grid_municipalities.csv")
    influence = pd.read_csv(output / "checkpoint2b_municipality_influence.csv")

    assert len(problem) == 11
    assert set(problem.relative_month) == {"m_-2", "m_-1"}
    assert len(disagreeing) == 379
    assert frequency.era5_grid_id.nunique() == 70
    assert len(composition) == 2501
    assert len(influence) == 2501
    assert influence.high_influence.sum() == 380
    assert influence.loc[influence.same_year_support_preserved, "leave_one_out_rho"].notna().all()
