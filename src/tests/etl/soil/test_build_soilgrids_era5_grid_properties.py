import numpy as np
import pandas as pd
import pytest

from etl.soil.build_soilgrids_era5_grid_properties import (
    DEPTHS,
    DERIVED_AWC,
    NODATA,
    VARIABLES,
    add_awc,
    aggregate_raster,
    coverage_id,
    raster_shape,
    scale_raw_values,
    validate_output,
)


def test_expected_variable_and_depth_sets_are_bounded():
    assert set(VARIABLES) == {
        "clay", "sand", "silt", "bdod", "cfvo", "wv0033", "wv1500"
    }
    assert [depth for _, _, depth in DEPTHS] == [
        "0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"
    ]
    assert coverage_id("wv0033", "30-60cm") == "wv0033_30-60cm_mean"


def test_raster_shape_and_area_weighted_aggregation_are_deterministic():
    bounds = (-1.25, -1.25, -.75, -.75)
    assert raster_shape(bounds) == (200, 200)
    array = np.full((200, 200), 100, dtype=np.int32)
    array[0, 0] = NODATA
    grids = pd.DataFrame({"grid_id": ["g"], "grid_lat": [-1.0], "grid_lon": [-1.0]})
    first = aggregate_raster(array, grids, bounds)
    second = aggregate_raster(array, grids, bounds)
    pd.testing.assert_frame_equal(first, second)
    assert first.raw_area_weighted_mean.iloc[0] == pytest.approx(100.0)
    assert first.n_source_pixels.iloc[0] == 39999
    assert 0.99 < first.coverage_fraction.iloc[0] < 1.0


def _source_water_rows(theta33: float, theta1500: float) -> pd.DataFrame:
    rows = []
    for variable, value in [("wv0033", theta33), ("wv1500", theta1500)]:
        rows.append({
            "era5_grid_id": "g", "grid_lat": -22.0, "grid_lon": -48.0,
            "raw_area_weighted_mean": value * 10, "n_source_pixels": 4,
            "n_expected_pixels": 4, "coverage_fraction": 1.0,
            "soil_variable": variable, "depth_top_cm": 0, "depth_bottom_cm": 5,
            "source_depth_label": "0-5cm", "value": value,
            "unit": "percent_volume", "source_raw_unit": "10^-3 cm3 cm-3",
            "scale_divisor": 10.0, "source": "SoilGrids 2.0",
            "source_coverage_id": f"{variable}_0-5cm_mean",
            "aggregation_method": "test", "is_derived": False, "derived_from": "",
        })
    return pd.DataFrame(rows)


def test_awc_is_derived_after_compatible_unit_scaling():
    result = add_awc(_source_water_rows(31.0, 14.5))
    awc = result.loc[result.soil_variable.eq(DERIVED_AWC)].iloc[0]
    assert awc.value == pytest.approx(16.5)
    assert awc.unit == "percentage_points_volumetric"
    assert awc.derived_from == "wv0033;wv1500"


def test_documented_source_unit_scaling():
    assert scale_raw_values("clay", 425.0) == pytest.approx(42.5)
    assert scale_raw_values("bdod", 132.0) == pytest.approx(1.32)
    assert scale_raw_values("wv0033", 287.0) == pytest.approx(28.7)


def test_validation_rejects_negative_awc_and_water_order_violation():
    source = _source_water_rows(10.0, 12.0)
    # Add the remaining source variables so validation reaches the water checks.
    extra = []
    for variable, value in [
        ("clay", 30.0), ("sand", 50.0), ("silt", 20.0),
        ("bdod", 1.3), ("cfvo", 5.0),
    ]:
        row = source.iloc[0].copy()
        row["soil_variable"] = variable
        row["value"] = value
        extra.append(row)
    table = add_awc(pd.concat([source, pd.DataFrame(extra)], ignore_index=True))
    grids = pd.DataFrame({"grid_id": ["g"], "grid_lat": [-22.0], "grid_lon": [-48.0]})
    checks, _ = validate_output(table, grids)
    indexed = checks.set_index("check")
    assert not bool(indexed.loc["theta33_ge_theta1500", "passed"])
    assert not bool(indexed.loc["nonnegative_awc", "passed"])
