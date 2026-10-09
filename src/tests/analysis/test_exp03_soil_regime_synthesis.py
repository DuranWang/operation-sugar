from pathlib import Path

import pandas as pd
import pytest

from analysis.exp03_soil_regime_synthesis import (
    NATIVE_DEPTHS,
    thickness_weighted_profiles,
    validate_soil_table,
)


def _single_profile() -> pd.DataFrame:
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    rows = []
    for (top, bottom, label), value in zip(NATIVE_DEPTHS, values):
        rows.append({
            "era5_grid_id": "g", "soil_variable": "clay", "regime": "depth_recovery",
            "grid_lat": -22.0, "coverage_fraction": 1.0,
            "depth_top_cm": top, "depth_bottom_cm": bottom,
            "source_depth_label": label, "value": value,
        })
    return pd.DataFrame(rows)


def test_profiles_use_exact_native_interval_thicknesses():
    result = thickness_weighted_profiles(_single_profile()).iloc[0]
    expected_upper = (10 * 5 + 20 * 10 + 30 * 15) / 30
    expected_deep = (40 * 30 + 50 * 40 + 60 * 100) / 170
    assert result.upper_0_30 == pytest.approx(expected_upper)
    assert result.deep_30_200 == pytest.approx(expected_deep)
    assert result.deep_minus_upper == pytest.approx(expected_deep - expected_upper)


def test_real_soil_table_has_no_fabricated_200_255_and_valid_awc():
    root = Path(__file__).resolve().parents[3]
    soil = pd.read_csv(root / "data/processed/soil/soilgrids_era5_grid_properties.csv")
    validate_soil_table(soil)
    assert soil.depth_bottom_cm.max() == 200
    assert not soil.source_depth_label.str.contains("255").any()


def test_validation_rejects_fabricated_200_255_depth():
    root = Path(__file__).resolve().parents[3]
    soil = pd.read_csv(root / "data/processed/soil/soilgrids_era5_grid_properties.csv")
    soil.loc[soil.index[0], ["depth_top_cm", "depth_bottom_cm", "source_depth_label"]] = [200, 255, "200-255cm"]
    with pytest.raises(ValueError, match="six native"):
        validate_soil_table(soil)


def test_curated_soil_outputs_are_descriptive_only():
    root = Path(__file__).resolve().parents[3]
    output = root / "outputs/research/exp_03/soil_regime_synthesis"
    expected = {
        "regime_soil_profile_summary.csv", "regime_soil_contrasts.csv",
        "soil_latitude_association.csv", "EXP_03_soil_regime_synthesis_report.md",
    }
    assert {path.name for path in output.iterdir()} == expected
    assert not any("model" in path.name.lower() or "prediction" in path.name.lower() for path in output.iterdir())
