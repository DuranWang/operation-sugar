import numpy as np
import pandas as pd
import pytest

from analysis.exp01a_municipality_weather_correlation import (
    WEATHER_VARIABLES,
    construct_lag1,
    correlation_matrices,
    cross_month_matrices,
    detect_duplicate_keys,
    monthly_correlations,
    pairwise_correlation,
    parse_month_fields,
    variable_inventory,
)


def test_duplicate_keys_are_detected():
    frame = pd.DataFrame({"ibge_code": ["1", "1"], "year": [2000, 2000], "calendar_month": [1, 1]})
    assert len(detect_duplicate_keys(frame)) == 2


def test_month_parsing_produces_expected_dates():
    result = parse_month_fields(pd.DataFrame({"month": ["2000-01", "2000-12"]}))
    assert result["date"].tolist() == [pd.Timestamp("2000-01-01"), pd.Timestamp("2000-12-01")]
    assert result["calendar_month"].tolist() == [1, 12]


def _lag_frame():
    return parse_month_fields(pd.DataFrame({
        "ibge_code": ["1", "1", "1", "1", "2"],
        "month": ["2000-11", "2000-12", "2001-01", "2001-03", "2001-01"],
        "x": [1.0, 2.0, 3.0, 4.0, 99.0],
    }))


def test_lag_never_crosses_municipalities():
    result = construct_lag1(_lag_frame(), ["x"])
    assert pd.isna(result.loc[result["ibge_code"].eq("2"), "x_lag1"]).all()


def test_lag_accepts_december_to_january():
    result = construct_lag1(_lag_frame(), ["x"])
    value = result.loc[(result["ibge_code"].eq("1")) & result["month"].eq("2001-01"), "x_lag1"].iloc[0]
    assert value == 2.0


def test_lag_does_not_bridge_missing_month():
    result = construct_lag1(_lag_frame(), ["x"])
    value = result.loc[(result["ibge_code"].eq("1")) & result["month"].eq("2001-03"), "x_lag1"].iloc[0]
    assert pd.isna(value)


def test_pairwise_complete_uses_only_jointly_observed_rows():
    frame = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0], "y": [2.0, 4.0, 6.0, np.nan]})
    value, n, status = pairwise_correlation(frame, "x", "y", "pearson")
    assert n == 2 and value == pytest.approx(1.0) and status == "defined"


def test_pearson_matches_known_example():
    frame = pd.DataFrame({"x": [1, 2, 3, 4], "y": [2, 4, 6, 8]})
    assert pairwise_correlation(frame, "x", "y", "pearson")[0] == pytest.approx(1.0)


def test_spearman_matches_known_example():
    frame = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 30, 20, 40]})
    assert pairwise_correlation(frame, "x", "y", "spearman")[0] == pytest.approx(0.8)


def test_constant_variable_is_explicit():
    frame = pd.DataFrame({"x": [1, 1, 1], "y": [1, 2, 3]})
    value, n, status = pairwise_correlation(frame, "x", "y", "pearson")
    assert pd.isna(value) and n == 3 and status == "constant_variable"


def test_month_specific_calculation_uses_only_requested_month():
    frame = pd.DataFrame({
        "calendar_month": [1, 1, 1, 2, 2, 2],
        "x": [1, 2, 3, 1, 2, 3],
        "y": [1, 2, 3, 3, 2, 1],
    })
    result = monthly_correlations(frame, ["x", "y"])
    assert result.loc[result["month"].eq(1), "pearson_r"].iloc[0] == pytest.approx(1.0)
    assert result.loc[result["month"].eq(2), "pearson_r"].iloc[0] == pytest.approx(-1.0)


def test_metadata_columns_are_excluded_from_weather_universe():
    inventory = variable_inventory()
    included = inventory.loc[inventory["included_in_exp01a"], "column_name"].tolist()
    assert included == WEATHER_VARIABLES
    assert not {"ibge_code", "month", "nasa_observed_days", "era5_observed_days"} & set(included)


def test_output_pair_count_matches_variable_list():
    frame = pd.DataFrame({"calendar_month": np.repeat(np.arange(1, 13), 3)})
    for index, variable in enumerate(WEATHER_VARIABLES):
        frame[variable] = np.arange(len(frame), dtype=float) + index
    result = monthly_correlations(frame, WEATHER_VARIABLES)
    assert len(result) == 12 * len(WEATHER_VARIABLES) * (len(WEATHER_VARIABLES) - 1) // 2


def test_defined_correlations_are_bounded():
    rng = np.random.default_rng(123)
    frame = pd.DataFrame({variable: rng.normal(size=50) for variable in WEATHER_VARIABLES})
    pearson, spearman, _ = correlation_matrices(frame, WEATHER_VARIABLES)
    assert pearson.stack().between(-1, 1).all()
    assert spearman.stack().between(-1, 1).all()


def test_cross_month_matrices_align_on_municipality_and_year():
    frame = pd.DataFrame({
        "ibge_code": ["1", "1", "2", "2", "3", "3"],
        "year": [2000] * 6,
        "calendar_month": [1, 2, 1, 2, 1, 2],
        "weather": [1.0, 30.0, 2.0, 20.0, 3.0, 10.0],
    })
    pearson, spearman, counts = cross_month_matrices(frame, "weather")
    assert pearson.loc[1, 2] == pytest.approx(-1.0)
    assert spearman.loc[1, 2] == pytest.approx(-1.0)
    assert counts.loc[1, 2] == 3


def test_cross_month_matrices_use_pairwise_complete_without_imputation():
    frame = pd.DataFrame({
        "ibge_code": ["1", "1", "2", "2", "3", "3"],
        "year": [2000] * 6,
        "calendar_month": [1, 2, 1, 2, 1, 2],
        "weather": [1.0, 10.0, 2.0, np.nan, 3.0, 30.0],
    })
    pearson, _, counts = cross_month_matrices(frame, "weather")
    assert counts.loc[1, 2] == 2
    assert pearson.loc[1, 2] == pytest.approx(1.0)


def test_cross_month_matrices_reject_duplicate_keys():
    frame = pd.DataFrame({
        "ibge_code": ["1", "1"],
        "year": [2000, 2000],
        "calendar_month": [1, 1],
        "weather": [1.0, 2.0],
    })
    with pytest.raises(ValueError, match="duplicate"):
        cross_month_matrices(frame, "weather")
