from pathlib import Path

import pandas as pd

from analysis.exp03_march_soil_moisture_depth import (
    FROZEN_REGIME_COUNTS,
    MOISTURE_VARIABLES,
    classify_depth_regimes,
)


def _synthetic_correlations() -> pd.DataFrame:
    signs = {
        "pp": (0.2, 0.4, 0.6, 0.8),
        "dr": (-0.2, -0.1, 0.4, 0.6),
        "pn": (-0.2, -0.1, -0.4, -0.6),
        "reverse": (0.2, 0.1, -0.4, -0.6),
    }
    rows = []
    for grid_id, values in signs.items():
        for variable, rho in zip(MOISTURE_VARIABLES, values):
            rows.append({
                "grid_id": grid_id,
                "relative_month_index": -1,
                "weather_variable": variable,
                "usable": True,
                "paired_years": 20,
                "spearman_rho": rho,
            })
    return pd.DataFrame(rows)


def test_depth_regimes_are_derived_from_surface_and_mean_deep_signs():
    result = classify_depth_regimes(_synthetic_correlations()).set_index("grid_id")
    assert result.loc["pp", "regime"] == "positive_positive"
    assert result.loc["dr", "regime"] == "depth_recovery"
    assert result.loc["pn", "regime"] == "persistent_negative"
    assert result.loc["reverse", "regime"] == "reverse"
    assert result.loc["dr", "deep_rho"] == 0.5


def test_real_correlations_reconstruct_frozen_regime_counts():
    root = Path(__file__).resolve().parents[3]
    source = pd.read_csv(
        root / "outputs/research/exp_03/yield_stratified_monthly_weather/"
        "checkpoint2/grid_specific_spearman_correlations.csv"
    )
    result = classify_depth_regimes(source)
    assert len(result) == 76
    assert result.regime.value_counts().to_dict() == FROZEN_REGIME_COUNTS
    assert result.regime.ne("boundary_zero").all()


def test_curated_march_outputs_have_expected_manifest_and_counts():
    root = Path(__file__).resolve().parents[3]
    output = root / "outputs/research/exp_03/march_soil_moisture_depth"
    expected = {
        "march_depth_summary.csv", "grid_depth_regimes.csv", "regime_summary.csv",
        "regime_rainfall_summary.csv", "regime_production_support_summary.csv",
        "EXP_03_march_soil_moisture_depth_report.md",
    }
    assert {path.name for path in output.iterdir()} == expected
    regimes = pd.read_csv(output / "grid_depth_regimes.csv")
    assert regimes.regime.value_counts().to_dict() == FROZEN_REGIME_COUNTS
