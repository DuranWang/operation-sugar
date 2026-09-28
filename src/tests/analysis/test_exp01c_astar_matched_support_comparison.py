import numpy as np
import pandas as pd
import pytest

from analysis.exp01a_municipality_weather_correlation import monthly_correlations, parse_month_fields
from analysis.exp01c_astar_matched_support_comparison import (
    add_comparison_deltas,
    astar_lag1_results,
    build_astar_panel,
    observed_support_keys,
    sign_changed,
)


def _full_year_panel() -> pd.DataFrame:
    rows = []
    for code, status, weight in [
        ("1", "numeric_positive", 1.0),
        ("2", "absolute_zero", 0.0),
        ("3", "unavailable", np.nan),
    ]:
        for month in range(1, 13):
            rows.append({
                "ibge_code": code,
                "year": 2000,
                "calendar_month": month,
                "source_status": status,
                "analysis_weight": weight,
                "x": float(month + int(code)),
                "y": float(2 * month - int(code)),
            })
    return pd.DataFrame(rows)


def test_astar_excludes_unavailable_area_rows():
    astar = build_astar_panel(_full_year_panel())
    assert set(astar.ibge_code) == {"1", "2"}
    assert not astar.source_status.eq("unavailable").any()


def test_astar_retains_explicit_zero_area_rows():
    astar = build_astar_panel(_full_year_panel())
    zero = astar.loc[astar.ibge_code.eq("2")]
    assert len(zero) == 12
    assert zero.analysis_weight.eq(0).all()


def test_astar_uses_ordinary_equal_weight_correlation():
    astar = build_astar_panel(_full_year_panel())
    result = monthly_correlations(astar, ["x", "y"])
    january = result.loc[result.month.eq(1)].iloc[0]
    expected = astar.loc[astar.calendar_month.eq(1), "x"].corr(
        astar.loc[astar.calendar_month.eq(1), "y"]
    )
    assert january.pearson_r == pytest.approx(expected)
    assert january.pearson_n == 2


def test_astar_and_b_observed_support_keys_are_identical():
    panel = _full_year_panel()
    astar = build_astar_panel(panel)
    assert observed_support_keys(astar).equals(observed_support_keys(panel))


def test_delta_identity_and_signed_values():
    frame = pd.DataFrame({"A_pearson": [0.2], "Astar_pearson": [0.1], "B_pearson": [-0.4]})
    result = add_comparison_deltas(frame, "pearson").iloc[0]
    assert result.delta_support_pearson == pytest.approx(-0.1)
    assert result.delta_weight_pearson == pytest.approx(-0.5)
    assert result.delta_total_pearson == pytest.approx(-0.6)
    assert result.delta_total_pearson == pytest.approx(result.delta_support_pearson + result.delta_weight_pearson)


def test_sign_change_flags_only_strict_reversals():
    left = pd.Series([-1.0, 1.0, 0.0, -1.0])
    right = pd.Series([1.0, -1.0, 1.0, 0.0])
    assert sign_changed(left, right).tolist() == [True, True, False, False]


def test_month_alignment_remains_calendar_specific():
    astar = build_astar_panel(_full_year_panel())
    result = monthly_correlations(astar, ["x", "y"])
    assert result.month.tolist() == list(range(1, 13))
    assert result.pearson_n.eq(2).all()


def test_lag1_preserves_december_to_january_before_support_filter():
    frame = parse_month_fields(pd.DataFrame({
        "ibge_code": ["1", "1", "2", "2"],
        "month": ["2000-12", "2001-01", "2000-12", "2001-01"],
        "x": [1.0, 2.0, 3.0, 8.0],
        # Prior-year unavailable status must not erase the weather lag when the
        # destination year is observed.
        "analysis_weight": [np.nan, 0.2, 0.0, 0.8],
    }))
    _, monthly = astar_lag1_results(frame, ["x"])
    january = monthly.loc[monthly.destination_month.eq(1)].iloc[0]
    assert january.pearson_n == 2
    assert january.pearson_r == pytest.approx(1.0)


def test_astar_rejects_partial_year_support():
    panel = _full_year_panel().drop(index=0)
    with pytest.raises(ValueError, match="12 months"):
        build_astar_panel(panel)
