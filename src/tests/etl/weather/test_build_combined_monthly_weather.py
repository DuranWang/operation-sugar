from pathlib import Path

import pandas as pd
import pytest

from src.etl.weather.build_combined_monthly_weather import (
    OUTPUT_COLUMNS,
    aggregate_nasa_monthly,
    build_combined_monthly,
    compare_dataframes,
    discover_nasa_files,
)


def nasa_rows(dates: list[str], rainfall: list[float | None]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": dates,
            "PRECTOTCORR": rainfall,
            "T2M": [20.0] * len(dates),
            "RH2M": [70.0] * len(dates),
            "municipality": ["Example"] * len(dates),
            "ibge_code": ["3500000"] * len(dates),
            "state": ["SP"] * len(dates),
            "latitude": [-22.0] * len(dates),
            "longitude": [-48.0] * len(dates),
        }
    )


def mapping_row() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "municipality": ["Example"],
            "ibge_code": ["3500000"],
            "latitude": [-22.0],
            "longitude": [-48.0],
            "era5_grid_latitude": [-22.0],
            "era5_grid_longitude": [-48.0],
            "era5_grid_id": ["era5_-22.00_-48.00"],
            "nasa_weather_group_id": ["POWER_WG_001"],
            "nasa_representative_municipality": ["Example"],
            "nasa_representative_latitude": [-22.0],
            "nasa_representative_longitude": [-48.0],
            "nasa_representative_ibge_code": ["3500000"],
        }
    )


def test_nasa_monthly_uses_only_days_with_all_three_valid_values() -> None:
    daily = nasa_rows(
        ["1981-01-01", "1981-01-02", "1981-01-03"],
        [1.0, None, 3.0],
    )
    monthly, report = aggregate_nasa_monthly(daily, 1981)
    assert monthly.loc[0, "nasa_observed_days"] == 2
    assert monthly.loc[0, "nasa_total_rainfall_mm"] == 4.0
    assert report["invalid_value_counts"]["PRECTOTCORR"] == 1
    assert report["incomplete_month_rows"] == 1


def test_nasa_monthly_rejects_duplicate_municipality_date() -> None:
    daily = nasa_rows(["1981-01-01", "1981-01-01"], [1.0, 2.0])
    with pytest.raises(ValueError, match="duplicate municipality-date"):
        aggregate_nasa_monthly(daily, 1981)


def test_nasa_monthly_handles_leap_day() -> None:
    dates = pd.date_range("1984-02-01", "1984-02-29").strftime("%Y-%m-%d").tolist()
    daily = nasa_rows(dates, [1.0] * len(dates))
    monthly, report = aggregate_nasa_monthly(daily, 1984)
    assert monthly.loc[0, "nasa_observed_days"] == 29
    assert monthly.loc[0, "nasa_total_rainfall_mm"] == 29.0
    assert report["incomplete_month_rows"] == 0


def test_discover_nasa_files_supports_segmented_periods(monkeypatch) -> None:
    folder = Path("nasa")
    paths = [
        folder / "19801215_19810630.csv",
        folder / "19810701_19811231.csv",
        folder / "19820101_19821231.csv",
    ]
    monkeypatch.setattr(Path, "is_dir", lambda self: self == folder)
    monkeypatch.setattr(Path, "glob", lambda self, pattern: iter(paths))
    assert [path.name for path in discover_nasa_files(folder, 1981)] == [
        "19801215_19810630.csv",
        "19810701_19811231.csv",
    ]


def test_combined_keeps_all_expected_months_when_sources_are_partial() -> None:
    mapping = mapping_row()
    nasa = pd.DataFrame(
        {
            "ibge_code": ["3500000"],
            "month": ["1981-01"],
            "nasa_observed_days": [31],
            "nasa_total_rainfall_mm": [10.0],
            "nasa_average_temperature_c": [20.0],
            "nasa_average_relative_humidity_pct": [70.0],
        }
    )
    era = pd.DataFrame(
        {
            "ibge_code": ["3500000"],
            "month": ["1981-01"],
            "grid_id": ["era5_-22.00_-48.00"],
            "observed_days": [31],
            **{column: [1.0] for column in OUTPUT_COLUMNS[10:]},
        }
    )
    combined, report = build_combined_monthly(mapping, nasa, era, 1981)
    assert len(combined) == 12
    assert report["missing_nasa_rows"] == 11
    assert report["missing_era5_rows"] == 11
    assert combined.loc[combined["month"].eq("1981-02"), "nasa_total_rainfall_mm"].isna().all()


def test_combined_rejects_era5_grid_mismatch() -> None:
    mapping = mapping_row()
    nasa = pd.DataFrame(
        {
            "ibge_code": ["3500000"],
            "month": ["1981-01"],
            "nasa_observed_days": [31],
            "nasa_total_rainfall_mm": [10.0],
            "nasa_average_temperature_c": [20.0],
            "nasa_average_relative_humidity_pct": [70.0],
        }
    )
    era = pd.DataFrame(
        {
            "ibge_code": ["3500000"],
            "month": ["1981-01"],
            "grid_id": ["era5_wrong"],
            "observed_days": [31],
            **{column: [1.0] for column in OUTPUT_COLUMNS[10:]},
        }
    )
    with pytest.raises(ValueError, match="grid mapping mismatch"):
        build_combined_monthly(mapping, nasa, era, 1981)


def test_pilot_comparison_detects_numeric_difference() -> None:
    row = {column: 1.0 for column in OUTPUT_COLUMNS}
    row.update(
        {
            "municipality": "Example",
            "ibge_code": "3500000",
            "month": "1981-01",
            "nasa_weather_group_id": "POWER_WG_001",
            "era5_grid_id": "era5_-22.00_-48.00",
        }
    )
    actual = pd.DataFrame([row])
    pilot = actual.copy()
    pilot.loc[0, "vpd_mean_kpa"] = 2.0
    result = compare_dataframes(actual, pilot)
    assert result["status"] == "failed"
    assert result["numeric_differences"]["vpd_mean_kpa"]["different_values"] == 1
