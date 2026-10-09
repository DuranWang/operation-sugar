from pathlib import Path

import numpy as np
import pandas as pd

from analysis.exp03_redundancy_synthesis import (
    ADJACENT_PAIRS,
    APPROVED_DEC_JAN_AGGREGATES,
    CANONICAL_VARIABLES,
    MONTHS,
    adjacent_month_redundancy,
    candidate_universe,
    representation_decisions,
    temporal_aggregation_decisions,
)


def _synthetic_aligned() -> pd.DataFrame:
    rows = []
    for grid_index in range(2):
        for year_index, year in enumerate(range(2000, 2015)):
            for month in MONTHS:
                row = {
                    "grid_id": f"g{grid_index}", "year": year,
                    "relative_month_index": month,
                }
                for metadata in CANONICAL_VARIABLES.values():
                    row[f"{metadata['weather_variable']}__anomaly"] = year_index + month / 10
                rows.append(row)
    return pd.DataFrame(rows)


def _synthetic_existing_yield() -> pd.DataFrame:
    rows = []
    for metadata in CANONICAL_VARIABLES.values():
        for month in MONTHS:
            rows.append({
                "relative_month_index": month,
                "weather_variable": metadata["weather_variable"],
                "standardized_high_minus_low": month / 10,
                "pooled_within_grid_rank_rho": month / 100,
                "pct_grids_agree_with_pooled_direction": .75,
            })
    return pd.DataFrame(rows)


def test_adjacent_redundancy_uses_exact_matched_years_and_minimum_support():
    result = adjacent_month_redundancy(_synthetic_aligned())
    assert len(result) == len(CANONICAL_VARIABLES) * len(ADJACENT_PAIRS)
    assert result.usable_grids.eq(2).all()
    assert np.allclose(result.median_grid_spearman, 1.0)
    assert result.minimum_paired_years_all_grids.eq(15).all()


def test_frozen_representation_decisions_are_canonical():
    decisions = representation_decisions().set_index("conceptual_family")
    assert decisions.loc["solar_energy", "canonical_variable"] == "solar_radiation_mean_daily_mj_m2"
    assert decisions.loc["vpd", "canonical_variable"] == "vpd_mean_kpa"
    assert decisions.loc["upper_soil_moisture", "canonical_variable"] == "soil_moisture_0_to_7cm_m3_m3"


def test_only_two_dec_jan_aggregates_and_candidate_count_is_38():
    redundancy = adjacent_month_redundancy(_synthetic_aligned())
    existing = _synthetic_existing_yield()
    decisions = temporal_aggregation_decisions(redundancy, existing)
    promoted = decisions.loc[decisions.promoted_aggregate]
    assert set(promoted.conceptual_variable) == APPROVED_DEC_JAN_AGGREGATES
    assert set(promoted.month_pair) == {"Dec-Jan"}
    assert not decisions.loc[decisions.month_pair.ne("Dec-Jan"), "promoted_aggregate"].any()

    candidates = candidate_universe(redundancy, existing)
    assert len(candidates) == 38
    assert candidates.candidate_id.nunique() == 38
    assert set(candidates.loc[
        candidates.candidate_status.eq("DEC_JAN_AGGREGATION_CANDIDATE"),
        "conceptual_variable",
    ]) == APPROVED_DEC_JAN_AGGREGATES
    assert {"temperature", "mean_vpd"}.issubset(set(candidates.conceptual_variable))
    assert {
        "rainfall_input", "upper_soil_moisture", "deep_soil_moisture_28_100",
        "deep_soil_moisture_100_255",
    }.issubset(set(candidates.conceptual_variable))


def test_curated_redundancy_outputs_match_frozen_downstream_invariants():
    root = Path(__file__).resolve().parents[3]
    output = root / "outputs/research/exp_03/redundancy"
    candidates = pd.read_csv(output / "exp04_candidate_universe.csv")
    adjacent = pd.read_csv(output / "adjacent_month_redundancy.csv")
    temporal = pd.read_csv(output / "temporal_aggregation_decisions.csv")
    assert len(candidates) == 38
    assert adjacent.usable_grids.eq(76).all()
    assert temporal.promoted_aggregate.sum() == 2
