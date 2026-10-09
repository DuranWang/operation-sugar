from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.exp03_harvest_profile_stability_audit import (
    build_normalized_profiles,
    early_late_comparison,
    interpolated_profile_quantile,
    representative_seasons,
    season_coverage_audit,
    season_metrics,
    temporal_trends,
)
from visualization.harvest_heatmap import load_unica_history


def test_interpolated_monthly_quantile_uses_uniform_within_bin_rule():
    profile = pd.DataFrame({
        "season_month_order": [1, 2],
        "monthly_share_of_season": [.5, .5],
    })
    assert interpolated_profile_quantile(profile, .10) == pytest.approx(.7)
    assert interpolated_profile_quantile(profile, .25) == pytest.approx(1.0)
    assert interpolated_profile_quantile(profile, .50) == pytest.approx(1.5)
    assert interpolated_profile_quantile(profile, .75) == pytest.approx(2.0)
    assert interpolated_profile_quantile(profile, .90) == pytest.approx(2.3)


@pytest.fixture(scope="module")
def real_audit_inputs():
    root = Path(__file__).resolve().parents[3]
    source = root / "data/processed/unica/crushing/unica_biweekly_crush.csv"
    cumulative = root / "data/processed/unica/harvest_intelligence/cumulative_crush_history.csv"
    raw = load_unica_history(source)
    coverage = season_coverage_audit(raw)
    profiles = build_normalized_profiles(raw, coverage, cumulative)
    metrics, profiles = season_metrics(profiles)
    return coverage, profiles, metrics


def test_real_coverage_gate_identifies_16_complete_and_one_partial(real_audit_inputs):
    coverage, _, _ = real_audit_inputs
    complete = coverage.loc[coverage.comparable_complete_season]
    partial = coverage.loc[~coverage.comparable_complete_season]
    assert complete.season.tolist() == [
        "10-11", "11-12", "12-13", "13-14", "14-15", "15-16", "16-17", "17-18",
        "18-19", "19-20", "20-21", "21-22", "22-23", "23-24", "24-25", "25-26",
    ]
    assert partial.season.tolist() == ["26-27"]
    assert partial.iloc[0].exclusion_reason == "partial_report_count"


def test_real_profiles_and_metrics_pass_structural_validation(real_audit_inputs):
    _, profiles, metrics = real_audit_inputs
    assert len(profiles) == 16 * 13
    assert not profiles.duplicated(["season", "season_month_order"]).any()
    assert np.allclose(profiles.groupby("season").monthly_share_of_season.sum(), 1.0)
    assert profiles.monthly_share_of_season.ge(0).all()
    assert metrics.hhi_concentration.between(1 / 13, 1).all()
    assert metrics.tv_from_average_profile.between(0, 1).all()
    assert (
        metrics.harvest_month_p10.le(metrics.harvest_month_p25)
        & metrics.harvest_month_p25.le(metrics.median_harvest_month)
        & metrics.median_harvest_month.le(metrics.harvest_month_p75)
        & metrics.harvest_month_p75.le(metrics.harvest_month_p90)
    ).all()


def test_real_trends_and_early_late_comparison_are_reproducible(real_audit_inputs):
    _, profiles, metrics = real_audit_inputs
    trends = temporal_trends(metrics)
    comparison, summary = early_late_comparison(profiles, metrics)
    assert len(trends) == 7
    assert comparison.profile_half.nunique() == 2
    assert summary.iloc[0].seasons_per_half == 8
    assert summary.iloc[0].early_vs_late_tv == pytest.approx(0.04998616820387148)
    assert summary.iloc[0].late_minus_early_center_months == pytest.approx(-0.2868238149432685)


def test_representative_selection_is_deterministic_and_preserves_roles(real_audit_inputs):
    _, _, metrics = real_audit_inputs
    first = representative_seasons(metrics)
    second = representative_seasons(metrics)
    pd.testing.assert_frame_equal(first, second)
    assert first.selection_role.tolist() == [
        "earliest_available", "latest_available", "largest_distance_from_average",
        "largest_year_to_year_change", "closest_to_average",
    ]
    assert first.loc[first.selection_role.eq("largest_distance_from_average"), "season"].item() == "12-13"
