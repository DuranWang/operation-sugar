import numpy as np
import pandas as pd
import pytest

from analysis.exp01a_municipality_weather_correlation import parse_month_fields
from analysis.exp01b_harvested_area_weighted_weather_correlation import (
    build_weighted_panel,
    kish_effective_n,
    weighted_cross_month,
    weighted_lag1,
    weighted_monthly_correlations,
    weighted_pearson,
    weighted_spearman,
)


def test_weighted_pearson_matches_integer_row_replication():
    frame = pd.DataFrame({"x": [1.0, 2.0, 4.0], "y": [2.0, 1.0, 5.0], "analysis_weight": [1.0, 2.0, 3.0]})
    result = weighted_pearson(frame, "x", "y")
    repeated = frame.loc[frame.index.repeat(frame.analysis_weight.astype(int))]
    assert result.value == pytest.approx(repeated.x.corr(repeated.y))


def test_weighted_pearson_zero_weight_has_no_effect():
    base = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [1.0, 4.0, 2.0], "analysis_weight": [1.0, 1.0, 1.0]})
    extended = pd.concat([base, pd.DataFrame({"x": [1000.0], "y": [-1000.0], "analysis_weight": [0.0]})], ignore_index=True)
    assert weighted_pearson(base, "x", "y").value == pytest.approx(weighted_pearson(extended, "x", "y").value)


def test_weighted_spearman_zero_weight_does_not_change_ranks():
    base = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [3.0, 1.0, 2.0], "analysis_weight": [1.0, 2.0, 1.0]})
    extended = pd.concat([base, pd.DataFrame({"x": [2.5], "y": [2.5], "analysis_weight": [0.0]})], ignore_index=True)
    assert weighted_spearman(base, "x", "y").value == pytest.approx(weighted_spearman(extended, "x", "y").value)


def test_weighted_spearman_uses_average_ties():
    frame = pd.DataFrame({"x": [1.0, 1.0, 3.0], "y": [3.0, 2.0, 1.0], "analysis_weight": [1.0, 2.0, 1.0]})
    ranks = pd.DataFrame({"rx": [1.5, 1.5, 3.0], "ry": [3.0, 2.0, 1.0], "analysis_weight": [1.0, 2.0, 1.0]})
    assert weighted_spearman(frame, "x", "y").value == pytest.approx(weighted_pearson(ranks, "rx", "ry").value)


def test_pairwise_complete_excludes_missing_and_unavailable_weights():
    frame = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0], "y": [1.0, 3.0, 4.0, 8.0], "analysis_weight": [0.5, 0.5, 0.2, np.nan]})
    result = weighted_pearson(frame, "x", "y")
    assert result.observed_n == 2
    assert result.positive_weight_n == 2
    assert result.weight_sum == pytest.approx(1.0)


def test_constant_variable_is_explicit():
    frame = pd.DataFrame({"x": [1.0, 1.0, 1.0], "y": [1.0, 2.0, 3.0], "analysis_weight": [1.0, 1.0, 1.0]})
    result = weighted_pearson(frame, "x", "y")
    assert pd.isna(result.value)
    assert result.status == "constant_variable"


def test_negative_weight_is_rejected():
    frame = pd.DataFrame({"x": [1.0, 2.0], "y": [1.0, 2.0], "analysis_weight": [1.0, -1.0]})
    with pytest.raises(ValueError, match="non-negative"):
        weighted_pearson(frame, "x", "y")


def test_kish_effective_n_equal_weights():
    assert kish_effective_n(pd.Series([0.25, 0.25, 0.25, 0.25])) == pytest.approx(4.0)


def _panel_inputs():
    weather = parse_month_fields(pd.DataFrame({
        "ibge_code": ["1", "1", "2", "2"],
        "municipality": ["A", "A", "B", "B"],
        "month": ["2000-01", "2000-02", "2000-01", "2000-02"],
        "x": [1.0, 2.0, 3.0, 4.0],
    }))
    area = pd.DataFrame({
        "ibge_code": ["1", "2"], "municipality": ["A", "B"], "year": [2000, 2000],
        "analysis_weight": [1.0, 0.0], "source_status": ["numeric_positive", "absolute_zero"],
        "raw_area_symbol": ["10", "-"], "harvested_area_ha_symbol_aware": [10.0, 0.0], "area_weight": [1.0, np.nan],
    })
    return weather, area


def test_merge_preserves_panel_and_normalization():
    weather, area = _panel_inputs()
    result = build_weighted_panel(weather, area)
    assert len(result.panel) == len(weather)
    assert result.annual.loc[0, "annual_weight_sum"] == pytest.approx(1.0)
    assert result.annual.loc[0, "zero_weight_municipalities"] == 1


def test_merge_rejects_key_mismatch():
    weather, area = _panel_inputs()
    area.loc[1, "ibge_code"] = "3"
    with pytest.raises(ValueError, match="keys do not match"):
        build_weighted_panel(weather, area)


def test_month_specific_calculation_uses_only_that_month():
    frame = pd.DataFrame({
        "calendar_month": [1, 1, 1, 2, 2, 2],
        "x": [1, 2, 3, 1, 2, 3], "y": [1, 2, 3, 3, 2, 1],
        "analysis_weight": [1, 1, 1, 1, 1, 1],
    })
    result = weighted_monthly_correlations(frame, ["x", "y"])
    assert result.loc[result.month.eq(1), "weighted_pearson_r"].iloc[0] == pytest.approx(1.0)
    assert result.loc[result.month.eq(2), "weighted_pearson_r"].iloc[0] == pytest.approx(-1.0)


def test_cross_month_aligns_on_municipality_year():
    frame = pd.DataFrame({
        "ibge_code": ["1", "1", "2", "2", "3", "3"], "year": [2000] * 6,
        "calendar_month": [1, 2, 1, 2, 1, 2], "weather": [1, 30, 2, 20, 3, 10],
        "analysis_weight": [0.2, 0.2, 0.3, 0.3, 0.5, 0.5],
    })
    matrices = weighted_cross_month(frame, "weather")
    assert matrices["pearson"].loc[1, 2] == pytest.approx(-1.0)
    assert matrices["weight_sum"].loc[1, 2] == pytest.approx(1.0)


def test_lag_uses_destination_row_weight_across_year_boundary():
    frame = parse_month_fields(pd.DataFrame({
        "ibge_code": ["1", "1", "2", "2"],
        "month": ["2000-12", "2001-01", "2000-12", "2001-01"],
        "x": [1.0, 2.0, 3.0, 8.0],
        "analysis_weight": [0.9, 0.2, 0.1, 0.8],
    }))
    _, monthly = weighted_lag1(frame, ["x"])
    january = monthly.loc[monthly.destination_month.eq(1)].iloc[0]
    assert january.weighted_pearson_r_weight_sum == pytest.approx(1.0)
    assert january.weighted_pearson_r_positive_weight_n == 2


def test_defined_coefficients_are_bounded():
    rng = np.random.default_rng(22)
    frame = pd.DataFrame({"x": rng.normal(size=100), "y": rng.normal(size=100), "analysis_weight": rng.uniform(size=100)})
    assert -1 <= weighted_pearson(frame, "x", "y").value <= 1
    assert -1 <= weighted_spearman(frame, "x", "y").value <= 1
