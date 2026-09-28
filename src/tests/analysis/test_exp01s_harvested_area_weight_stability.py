import pandas as pd
import pytest

from src.analysis.exp01s_harvested_area_weight_stability import (
    anchor_year_comparison,
    classify_ibge_area_value,
    top_k_overlap,
    total_variation,
    validate_nan_semantics,
    validate_processed_structure,
    validate_weight_vector,
)


def panel() -> pd.DataFrame:
    rows = []
    for year in range(1990, 2026):
        rows.extend(
            [
                {
                    "ibge_code": "3500001",
                    "municipality": "A",
                    "year": year,
                    "harvested_area_ha": 60.0,
                    "area_weight": 0.6,
                },
                {
                    "ibge_code": "3500002",
                    "municipality": "B",
                    "year": year,
                    "harvested_area_ha": 40.0,
                    "area_weight": 0.4,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_duplicate_municipality_year_is_rejected() -> None:
    data = pd.concat([panel(), panel().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_processed_structure(data)


def test_annual_weight_sum_validation() -> None:
    validate_weight_vector(pd.Series([0.6, 0.4]))
    with pytest.raises(ValueError, match="sum to 1"):
        validate_weight_vector(pd.Series([0.6, 0.3]))


def test_ibge_zero_and_unavailable_are_not_collapsed() -> None:
    zero_value, zero_status = classify_ibge_area_value("-")
    missing_value, missing_status = classify_ibge_area_value("...")
    assert zero_value == 0.0
    assert zero_status == "absolute_zero"
    assert pd.isna(missing_value)
    assert missing_status == "unavailable"


def test_nan_semantics_gate_blocks_unavailable_value() -> None:
    symbol_data = pd.DataFrame(
        {"area_value_status": ["numeric_positive", "absolute_zero", "unavailable"]}
    )
    result = validate_nan_semantics(symbol_data)
    assert result.status == "blocked"
    assert result.unavailable_rows == 1


def test_identical_vectors_have_zero_total_variation() -> None:
    weights = pd.Series([0.6, 0.4], index=["A", "B"])
    assert total_variation(weights, weights) == 0.0


def test_known_redistribution_has_expected_total_variation() -> None:
    first = pd.Series([1.0, 0.0], index=["A", "B"])
    second = pd.Series([0.5, 0.5], index=["A", "B"])
    assert total_variation(first, second) == 0.5
    assert 0.0 <= total_variation(first, second) <= 1.0


def test_top_k_overlap() -> None:
    first = pd.Series([0.4, 0.3, 0.2, 0.1], index=list("ABCD"))
    second = pd.Series([0.4, 0.1, 0.3, 0.2], index=list("ABCD"))
    assert top_k_overlap(first, second, 2) == 0.5


def test_anchor_year_comparison_requires_same_universe() -> None:
    weights = {
        1990: pd.Series([0.6, 0.4], index=["A", "B"]),
        2000: pd.Series([0.6, 0.4], index=["A", "C"]),
    }
    with pytest.raises(ValueError, match="same municipality universe"):
        anchor_year_comparison(weights, [(1990, 2000)])


def test_processed_panel_has_constant_universe() -> None:
    result = validate_processed_structure(panel())
    assert len(result) == 72
    assert result["ibge_code"].nunique() == 2

