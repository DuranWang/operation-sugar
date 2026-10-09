from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.exp01a_municipality_weather_correlation import WEATHER_VARIABLES
from analysis.exp03_yield_stratified_monthly_weather import (
    YIELD_COLUMN,
    add_weather_anomalies,
    assign_within_grid_yield_groups,
    build_alignment,
    relative_month_lookup,
)


def test_relative_month_lookup_matches_handover_exactly():
    lookup = relative_month_lookup().set_index("relative_month_index")
    assert len(lookup) == 16
    assert lookup.index.tolist() == list(range(-15, 1))
    assert (lookup.loc[-15, "source_year_offset"], lookup.loc[-15, "source_calendar_month"]) == (-1, 1)
    assert (lookup.loc[-12, "source_year_offset"], lookup.loc[-12, "source_calendar_month"]) == (-1, 4)
    assert (lookup.loc[-11, "source_year_offset"], lookup.loc[-11, "source_calendar_month"]) == (-1, 5)
    assert (lookup.loc[-4, "source_year_offset"], lookup.loc[-4, "source_calendar_month"]) == (-1, 12)
    assert (lookup.loc[-3, "source_year_offset"], lookup.loc[-3, "source_calendar_month"]) == (0, 1)
    assert (lookup.loc[0, "source_year_offset"], lookup.loc[0, "source_calendar_month"]) == (0, 4)
    assert lookup.loc[-11:0, "primary_window"].all()
    assert not lookup.loc[-15:-12, "primary_window"].any()


def test_alignment_expands_each_outcome_to_16_unique_months():
    outcome = pd.DataFrame({"grid_id": ["g"], "year": [1982], YIELD_COLUMN: [1.5]})
    aligned = build_alignment(outcome)
    assert len(aligned) == 16
    assert not aligned.duplicated(["grid_id", "year", "relative_month_index"]).any()
    observed = aligned.set_index("relative_month_index").source_month_label
    assert observed.loc[-15] == "1981-01"
    assert observed.loc[-11] == "1981-05"
    assert observed.loc[-4] == "1981-12"
    assert observed.loc[-3] == "1982-01"
    assert observed.loc[0] == "1982-04"


def test_average_rank_grouping_preserves_ties_and_25_50_25_split():
    values = [-2.0, -1.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0]
    outcome = pd.DataFrame({"grid_id": ["g"] * 8, "year": range(2000, 2008), YIELD_COLUMN: values})
    grouped = assign_within_grid_yield_groups(outcome)
    counts = grouped.yield_group.value_counts().to_dict()
    assert counts == {"Medium": 4, "Low": 2, "High": 2}
    tied = grouped.loc[grouped[YIELD_COLUMN].eq(0)]
    assert tied.within_grid_average_rank.eq(3.5).all()
    assert tied.within_grid_percentile_u.eq(0.375).all()
    assert tied.yield_group.astype("string").eq("Medium").all()


def test_anomalies_are_raw_grid_calendar_month_deviations():
    rows = []
    for year, rainfall in [(2000, 10.0), (2001, 14.0)]:
        row = {
            "grid_id": "g", "year": year, "source_calendar_month": 5,
            "primary_window": True,
        }
        row.update({variable: rainfall for variable in WEATHER_VARIABLES})
        rows.append(row)
    anomalies, baseline = add_weather_anomalies(pd.DataFrame(rows))
    rainfall_anomaly = f"{WEATHER_VARIABLES[0]}__anomaly"
    assert anomalies[rainfall_anomaly].tolist() == pytest.approx([-2.0, 2.0])
    rainfall_baseline = baseline.loc[baseline.weather_variable.eq(WEATHER_VARIABLES[0])].iloc[0]
    assert rainfall_baseline.historical_mean == pytest.approx(12.0)
    assert rainfall_baseline.historical_n == 2


def test_completed_checkpoint_outputs_have_expected_cardinality_and_constraints():
    root = Path(__file__).resolve().parents[3]
    output = root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1"
    groups = pd.read_csv(output / "yield_grid_year_groups.csv")
    aligned = pd.read_csv(output / "aligned_grid_year_month_weather_anomalies.csv")
    issues = pd.read_csv(output / "partial_weather_weight_coverage_issues.csv")
    windows = pd.read_csv(output / "grid_year_weather_window_status.csv")
    temporal = pd.read_csv(output / "temporal_source_coverage_audit.csv")
    spatial = pd.read_csv(output / "spatial_reconciliation_summary.csv").iloc[0]

    assert len(groups) == 3773
    assert groups.grid_id.nunique() == 78
    assert groups.year.nunique() == 52
    assert not groups.duplicated(["grid_id", "year"]).any()
    assert groups.yield_group.value_counts().to_dict() == {"Medium": 1877, "Low": 948, "High": 948}
    assert len(aligned) == 52272
    assert aligned[["grid_id", "year"]].drop_duplicates().shape[0] == 3267
    assert aligned.year.min() == 1982
    assert aligned.year.max() == 2025
    assert not aligned.duplicated(["grid_id", "year", "relative_month_index"]).any()
    assert aligned.groupby(["grid_id", "year"]).size().eq(16).all()
    assert issues.empty
    assert windows.window_status.value_counts().to_dict() == {
        "complete_16_months": 3267, "missing_window": 437, "partial_window": 69,
    }
    assert temporal.complete_from_1981_01.all()
    assert temporal.sufficient_for_complete_1982_window.all()
    assert temporal.missing_municipality_month_rows.eq(0).all()
    assert spatial.eligible_municipalities == 511
    assert spatial.represented_era5_grids == 78
    assert spatial.represented_nasa_groups == 76
    assert bool(spatial.grid_year_weight_sums_all_one)
    assert bool(spatial.residual_and_weight_grid_year_support_identical)

    primary = aligned.loc[aligned.primary_window]
    for variable in WEATHER_VARIABLES:
        anomaly = f"{variable}__anomaly"
        centered = primary.groupby(["grid_id", "source_calendar_month"])[anomaly].mean().dropna()
        assert np.allclose(centered, 0.0, atol=1e-10)
