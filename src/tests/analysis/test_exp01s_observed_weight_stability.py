import pandas as pd
import pytest

from src.analysis.exp01s_observed_weight_stability import (
    build_missingness_materiality,
    build_observed_panel,
    common_reported_spearman,
    reported_distribution_tv,
)


def test_observed_panel_preserves_unavailable_and_restores_explicit_zero() -> None:
    processed = pd.DataFrame(
        [
            {"ibge_code": "1", "municipality": "A", "year": 1990,
             "harvested_area_ha": 100.0, "area_weight": 1.0},
            {"ibge_code": "2", "municipality": "B", "year": 1990,
             "harvested_area_ha": None, "area_weight": None},
            {"ibge_code": "3", "municipality": "C", "year": 1990,
             "harvested_area_ha": None, "area_weight": None},
        ]
    )
    symbols = pd.DataFrame(
        [
            {"ibge_code": "1", "municipality": "A", "year": 1990,
             "raw_area_symbol": "100", "harvested_area_ha_symbol_aware": 100.0,
             "area_value_status": "numeric_positive"},
            {"ibge_code": "2", "municipality": "B", "year": 1990,
             "raw_area_symbol": "-", "harvested_area_ha_symbol_aware": 0.0,
             "area_value_status": "absolute_zero"},
            {"ibge_code": "3", "municipality": "C", "year": 1990,
             "raw_area_symbol": "...", "harvested_area_ha_symbol_aware": None,
             "area_value_status": "unavailable"},
        ]
    )
    panel = build_observed_panel(processed, symbols)
    assert panel.loc[panel["ibge_code"].eq("2"), "observed_area_weight"].item() == 0
    assert pd.isna(
        panel.loc[panel["ibge_code"].eq("3"), "observed_area_weight"].item()
    )


def test_materiality_gate_blocks_an_affected_top_50_municipality() -> None:
    rows = []
    for year in range(1990, 2026):
        for index in range(60):
            rows.append(
                {
                    "ibge_code": str(index),
                    "municipality": f"M{index}",
                    "year": year,
                    "source_status": (
                        "unavailable" if index == 0 and year == 1990 else "numeric_positive"
                    ),
                    "is_reported": not (index == 0 and year == 1990),
                    "reported_harvested_area_ha": (
                        None if index == 0 and year == 1990 else float(60 - index)
                    ),
                    "observed_area_weight": (
                        None if index == 0 and year == 1990 else float(60 - index) / 1830
                    ),
                }
            )
    panel = pd.DataFrame(rows)
    _, _, gate = build_missingness_materiality(panel)
    assert gate["status"] == "blocked"
    assert gate["material_municipality_count"] == 1


def test_reported_distribution_tv_extends_support_without_area_imputation() -> None:
    first = pd.Series([0.75, 0.25], index=["A", "B"])
    second = pd.Series([0.50, 0.50], index=["A", "C"])
    assert reported_distribution_tv(first, second) == 0.5


def test_spearman_uses_only_common_reported_municipalities() -> None:
    first = pd.Series([0.6, 0.3, 0.1], index=["A", "B", "C"])
    second = pd.Series([0.5, 0.2, 0.3], index=["A", "B", "D"])
    correlation, count = common_reported_spearman(first, second)
    assert correlation == pytest.approx(1.0)
    assert count == 2
