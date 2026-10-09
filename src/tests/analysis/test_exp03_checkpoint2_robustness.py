from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.exp01a_municipality_weather_correlation import WEATHER_VARIABLES
from analysis.exp03_checkpoint2_robustness import (
    YIELD_COLUMN,
    assign_percentile_groups,
    assign_zscore_pooled_groups,
    grid_specific_spearman,
    pooled_within_grid_rank_associations,
    within_grid_rank,
)


def test_within_grid_rank_handles_ties_and_missing_deterministically():
    values = pd.Series([1.0, 2.0, 2.0, np.nan, 4.0])
    result = within_grid_rank(values)
    assert result.iloc[[0, 1, 2, 4]].tolist() == pytest.approx([
        .125, .5, .5, .875
    ])
    assert pd.isna(result.iloc[3])


def test_percentile_grouping_is_independent_within_each_grid():
    frame = pd.DataFrame({
        "grid_id": ["a"] * 5 + ["b"] * 5,
        "year": list(range(5)) * 2,
        YIELD_COLUMN: [1, 2, 3, 4, 5, 101, 102, 103, 104, 105],
    })
    result = assign_percentile_groups(frame, .20, .80, "group")
    for grid in ["a", "b"]:
        ordered = result.loc[result.grid_id.eq(grid)].sort_values(YIELD_COLUMN)
        assert ordered.group.astype(str).tolist() == [
            "Low", "Medium", "Medium", "Medium", "High"
        ]


def test_zscore_pooled_grouping_uses_within_grid_standardization():
    frame = pd.DataFrame({
        "grid_id": ["a"] * 4 + ["b"] * 4,
        "year": list(range(4)) * 2,
        YIELD_COLUMN: [1, 2, 3, 4, 100, 200, 300, 400],
    })
    result, low, high = assign_zscore_pooled_groups(frame)
    assert result.groupby("grid_id").within_grid_residual_z.mean().abs().lt(1e-12).all()
    assert low < 0 < high
    assert result.yield_group_zscore_pooled.value_counts().to_dict() == {
        "Medium": 4, "Low": 2, "High": 2,
    }


def _continuous_frame() -> pd.DataFrame:
    rows = []
    for grid, yield_values, weather_values in [
        ("a", [1, 2, 3, 4], [10, 20, 30, 40]),
        ("b", [101, 102, 103, 104], [400, 300, 200, 100]),
    ]:
        for year, (yield_value, weather_value) in enumerate(zip(yield_values, weather_values)):
            row = {
                "grid_id": grid, "year": 2000 + year,
                "relative_month_index": -3, "relative_month": "m_-3",
                "calendar_month_label": "Jan_(t)", "primary_window": True,
                YIELD_COLUMN: yield_value,
            }
            row.update({f"{variable}__anomaly": weather_value for variable in WEATHER_VARIABLES})
            rows.append(row)
    return pd.DataFrame(rows)


def test_pooled_continuous_ranks_yield_and_weather_within_grid():
    result = pooled_within_grid_rank_associations(_continuous_frame())
    assert len(result) == len(WEATHER_VARIABLES)
    # Equal-size grids with perfectly opposite within-grid relationships cancel.
    assert result.pooled_within_grid_rank_rho.abs().lt(1e-12).all()


def test_grid_specific_spearman_uses_only_paired_valid_years():
    frame = _continuous_frame()
    weather = f"{WEATHER_VARIABLES[0]}__anomaly"
    frame.loc[(frame.grid_id.eq("a")) & frame.year.eq(2001), weather] = np.nan
    details, summary = grid_specific_spearman(frame, minimum_pairs=3)
    rain = details.loc[details.weather_variable.eq(WEATHER_VARIABLES[0])].set_index("grid_id")
    assert rain.loc["a", "paired_years"] == 3
    assert rain.loc["a", "spearman_rho"] == pytest.approx(1.0)
    assert rain.loc["b", "paired_years"] == 4
    assert rain.loc["b", "spearman_rho"] == pytest.approx(-1.0)
    rain_summary = summary.loc[summary.weather_variable.eq(WEATHER_VARIABLES[0])].iloc[0]
    assert rain_summary.usable_grids == 2
    assert rain_summary.pct_grids_positive == pytest.approx(.5)
    assert rain_summary.pct_grids_negative == pytest.approx(.5)


def test_real_checkpoint2_outputs_preserve_primary_and_expected_cardinality():
    root = Path(__file__).resolve().parents[3]
    cp1 = root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1"
    cp2 = root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint2"
    primary_groups = pd.read_csv(cp1 / "yield_grid_year_groups.csv")
    sensitivity = pd.read_csv(cp2 / "ranking_history_assignment_sensitivity.csv")
    pooled = pd.read_csv(cp2 / "pooled_within_grid_rank_associations.csv")
    grid_details = pd.read_csv(cp2 / "grid_specific_spearman_correlations.csv")
    robustness = pd.read_csv(cp2 / "checkpoint2_robustness_summary.csv")

    assert len(primary_groups) == 3773
    assert primary_groups.yield_group.value_counts().to_dict() == {
        "Medium": 1877, "Low": 948, "High": 948,
    }
    assert len(sensitivity) == 3267
    assert sensitivity.assignment_changed.sum() == 116
    assert len(pooled) == 16 * len(WEATHER_VARIABLES) == 176
    assert pooled.paired_observations.eq(3267).all()
    assert len(grid_details) == 78 * 16 * len(WEATHER_VARIABLES)
    assert grid_details.loc[grid_details.usable].paired_years.ge(15).all()
    assert len(robustness) == 4
    assert robustness.loc[0, "effect_correlation_vs_primary"] == pytest.approx(1.0)
