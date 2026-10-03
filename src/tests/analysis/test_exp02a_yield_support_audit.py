import numpy as np
import pandas as pd
import pytest

from analysis.exp02a_yield_support_audit import (
    annual_support_table,
    classify_ibge_value,
    derive_source_aware_yield,
    gate_mask,
    gate_yearly_support,
    municipality_support_metrics,
    summarize_gate,
    source_status_summary,
)


@pytest.mark.parametrize(
    ("raw", "value", "status"),
    [
        ("12", 12.0, "numeric_positive"),
        ("0", 0.0, "numeric_zero"),
        ("-", 0.0, "explicit_zero"),
        ("...", np.nan, "unavailable"),
    ],
)
def test_classify_ibge_value_preserves_semantics(raw, value, status):
    parsed, parsed_status, symbol = classify_ibge_value(raw)
    if np.isnan(value):
        assert np.isnan(parsed)
    else:
        assert parsed == value
    assert parsed_status == status
    assert symbol == raw


def test_classify_ibge_value_rejects_negative_and_unknown():
    with pytest.raises(ValueError, match="Invalid"):
        classify_ibge_value("-2")
    with pytest.raises(ValueError, match="Unrecognized"):
        classify_ibge_value("unknown")


def test_yield_validity_requires_positive_observed_area_and_preserves_zero_production():
    frame = pd.DataFrame({
        "production_source_status": ["numeric_positive", "numeric_zero", "explicit_zero", "unavailable"],
        "production_source_value": [100.0, 0.0, 0.0, np.nan],
        "harvested_area_source_status": ["numeric_positive"] * 4,
        "harvested_area_source_value": [10.0] * 4,
    })
    result = derive_source_aware_yield(frame)
    assert result.valid_yield_for_detrending.tolist() == [True, True, True, False]
    assert result.yield_tch_source_aware.iloc[:3].tolist() == [10.0, 0.0, 0.0]
    assert pd.isna(result.yield_tch_source_aware.iloc[3])


def test_numeric_and_explicit_zero_area_never_create_zero_yield():
    frame = pd.DataFrame({
        "production_source_status": ["numeric_zero", "explicit_zero", "unavailable"],
        "production_source_value": [0.0, 0.0, np.nan],
        "harvested_area_source_status": ["numeric_zero", "explicit_zero", "unavailable"],
        "harvested_area_source_value": [0.0, 0.0, np.nan],
    })
    result = derive_source_aware_yield(frame)
    assert not result.valid_yield_for_detrending.any()
    assert result.yield_tch_source_aware.isna().all()


def _history_panel() -> pd.DataFrame:
    rows = []
    validity = {
        "1": [True, True, False, False, True, True, False, True],
        "2": [False, False, False, True, True, True, True, True],
        "3": [False] * 8,
    }
    for code, flags in validity.items():
        for year, valid in zip(range(2000, 2008), flags):
            rows.append({
                "ibge_code": code,
                "municipality": f"M{code}",
                "year": year,
                "valid_yield_for_detrending": valid,
                "harvested_area_source_status": "numeric_positive" if valid else "explicit_zero",
                "harvested_area_source_value": 10.0 if valid else 0.0,
                "production_source_status": "numeric_positive" if valid else "explicit_zero",
            })
    return pd.DataFrame(rows)


def test_support_metrics_measure_span_and_internal_runs_exactly():
    support = municipality_support_metrics(_history_panel()).set_index("ibge_code")
    first = support.loc["1"]
    assert first.n_valid_years == 5
    assert first.first_valid_year == 2000
    assert first.last_valid_year == 2007
    assert first.calendar_span_years == 8
    assert first.n_missing_inside_span == 3
    assert first.max_internal_gap_years == 2
    assert first.n_internal_gaps == 2
    assert first.share_valid_within_span == pytest.approx(5 / 8)


def test_support_metrics_distinguish_late_start_and_no_history():
    support = municipality_support_metrics(_history_panel()).set_index("ibge_code")
    assert support.loc["2", "first_valid_year"] == 2003
    assert support.loc["2", "calendar_span_years"] == 5
    assert support.loc["2", "max_internal_gap_years"] == 0
    assert support.loc["3", "n_valid_years"] == 0
    assert support.loc["3", "calendar_span_years"] == 0
    assert pd.isna(support.loc["3", "first_valid_year"])


def test_gate_mask_enforces_all_three_dimensions_and_boundaries():
    support = municipality_support_metrics(_history_panel())
    strict = gate_mask(support, min_valid_years=5, min_calendar_span=8, max_internal_gap=2)
    assert strict.tolist() == [True, False, False]
    tighter_gap = gate_mask(support, min_valid_years=5, min_calendar_span=8, max_internal_gap=1)
    assert not tighter_gap.any()
    unrestricted = gate_mask(support, min_valid_years=5, min_calendar_span=5, max_internal_gap=None)
    assert unrestricted.tolist() == [True, True, False]


def test_gate_yearly_support_uses_observed_only_area_denominator():
    panel = _history_panel()
    result = gate_yearly_support(panel, {"1"}, "test")
    year = result.loc[result.year.eq(2000)].iloc[0]
    assert year.valid_yield_municipality_count == 1
    assert year.all_valid_yield_municipality_count == 1
    assert year.retained_valid_yield_area_coverage == pytest.approx(1.0)
    year_2003 = result.loc[result.year.eq(2003)].iloc[0]
    assert year_2003.all_observed_harvested_area_ha == pytest.approx(10.0)
    assert year_2003.retained_valid_yield_area_coverage == pytest.approx(0.0)


def test_source_status_summary_reconciles_counts():
    panel = _history_panel()
    result = source_status_summary(panel)
    overall = result.loc[result.period.eq("overall")].iloc[0]
    assert overall.municipality_year_rows == len(panel)
    assert overall.valid_yield_rows == int(panel.valid_yield_for_detrending.sum())
    assert overall.production_area_status_mismatches == 0


def test_annual_support_table_reconciles_valid_counts_and_area():
    panel = _history_panel()
    result = annual_support_table(panel)
    year = result.loc[result.year.eq(2004)].iloc[0]
    assert year.valid_yield_municipality_count == 2
    assert year.observed_harvested_area_ha == pytest.approx(20.0)
    assert year.valid_yield_observed_area_coverage == pytest.approx(1.0)


def test_gate_summary_reconciles_membership_observations_and_yearly_results():
    panel = _history_panel()
    support = municipality_support_metrics(panel)
    summary, yearly, membership = summarize_gate(
        panel,
        support,
        gate_id="synthetic",
        min_valid_years=5,
        min_calendar_span=5,
        max_internal_gap=None,
    )
    assert membership.tolist() == [True, True, False]
    assert summary["retained_municipalities"] == 2
    assert summary["retained_valid_municipality_years"] == 10
    assert summary["retained_valid_observation_share"] == pytest.approx(1.0)
    assert yearly["valid_yield_municipality_count"].sum() == 10
    assert yearly["retained_valid_yield_area_coverage"].dropna().eq(1.0).all()
