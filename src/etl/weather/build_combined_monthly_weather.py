"""Build a municipality-month table from local NASA POWER and ERA5 data.

This module never downloads data.  It combines the existing NASA POWER daily
CSV files with the existing ERA5 municipality monthly CSV files through the
authoritative municipality mapping workbook.
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


OUTPUT_COLUMNS = [
    "municipality",
    "ibge_code",
    "month",
    "nasa_weather_group_id",
    "era5_grid_id",
    "nasa_observed_days",
    "era5_observed_days",
    "nasa_total_rainfall_mm",
    "nasa_average_temperature_c",
    "nasa_average_relative_humidity_pct",
    "vpd_mean_kpa",
    "vpd_mean_daily_max_kpa",
    "soil_moisture_0_to_7cm_m3_m3",
    "soil_moisture_7_to_28cm_m3_m3",
    "soil_moisture_28_to_100cm_m3_m3",
    "soil_moisture_100_to_255cm_m3_m3",
    "solar_radiation_total_mj_m2",
    "solar_radiation_mean_daily_mj_m2",
]

MAPPING_COLUMNS = [
    "municipality",
    "ibge_code",
    "latitude",
    "longitude",
    "era5_grid_latitude",
    "era5_grid_longitude",
    "era5_grid_id",
    "nasa_weather_group_id",
    "nasa_representative_municipality",
    "nasa_representative_latitude",
    "nasa_representative_longitude",
    "nasa_representative_ibge_code",
]

NASA_COLUMNS = [
    "Date",
    "PRECTOTCORR",
    "T2M",
    "RH2M",
    "municipality",
    "ibge_code",
    "state",
    "latitude",
    "longitude",
]

ERA5_COLUMNS = [
    "municipality",
    "state",
    "ibge_code",
    "latitude",
    "longitude",
    "grid_id",
    "grid_latitude",
    "grid_longitude",
    "month",
    "observed_days",
    "expected_days",
    "complete_month",
    "vpd_mean_kpa",
    "vpd_mean_daily_max_kpa",
    "soil_moisture_0_to_7cm_m3_m3",
    "soil_moisture_7_to_28cm_m3_m3",
    "soil_moisture_28_to_100cm_m3_m3",
    "soil_moisture_100_to_255cm_m3_m3",
    "solar_radiation_total_mj_m2",
    "solar_radiation_mean_daily_mj_m2",
]

NASA_VALUE_COLUMNS = ["PRECTOTCORR", "T2M", "RH2M"]
ERA5_VALUE_COLUMNS = OUTPUT_COLUMNS[10:]
PERIOD_FILENAME = re.compile(r"^(\d{8})_(\d{8})\.csv$")


def _require_columns(
    dataframe: pd.DataFrame,
    required: list[str],
    label: str,
) -> None:
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def _clean_ibge(series: pd.Series, label: str) -> pd.Series:
    cleaned = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    if cleaned.isna().any() or cleaned.eq("").any():
        raise ValueError(f"{label} contains missing IBGE codes")
    return cleaned


def load_mapping(path: Path) -> pd.DataFrame:
    """Load and validate the authoritative combined source mapping."""

    if not path.is_file():
        raise FileNotFoundError(f"Combined weather mapping not found: {path}")
    mapping = pd.read_excel(
        path,
        dtype={
            "ibge_code": "string",
            "nasa_representative_ibge_code": "string",
        },
    )
    _require_columns(mapping, MAPPING_COLUMNS, "Combined weather mapping")
    mapping = mapping[MAPPING_COLUMNS].copy()
    mapping["ibge_code"] = _clean_ibge(mapping["ibge_code"], "Mapping")
    mapping["nasa_representative_ibge_code"] = _clean_ibge(
        mapping["nasa_representative_ibge_code"], "Mapping representative"
    )
    if mapping["ibge_code"].duplicated().any():
        raise ValueError("Mapping must contain exactly one row per IBGE code")
    required_text = [
        "municipality",
        "era5_grid_id",
        "nasa_weather_group_id",
        "nasa_representative_municipality",
    ]
    if mapping[required_text].isna().any().any():
        raise ValueError("Mapping contains missing source identifiers")
    return mapping.sort_values("ibge_code").reset_index(drop=True)


def discover_nasa_files(folder: Path, year: int) -> list[Path]:
    """Find all local NASA CSV periods that overlap ``year``."""

    if not folder.is_dir():
        raise FileNotFoundError(f"NASA POWER daily folder not found: {folder}")
    first_day = pd.Timestamp(year=year, month=1, day=1)
    last_day = pd.Timestamp(year=year, month=12, day=31)
    matches: list[Path] = []
    for path in sorted(folder.glob("*.csv")):
        match = PERIOD_FILENAME.fullmatch(path.name)
        if not match:
            continue
        start = pd.to_datetime(match.group(1), format="%Y%m%d")
        end = pd.to_datetime(match.group(2), format="%Y%m%d")
        if start > end:
            raise ValueError(f"NASA filename has an invalid period: {path.name}")
        if start <= last_day and end >= first_day:
            matches.append(path)
    if not matches:
        raise FileNotFoundError(
            f"No NASA POWER daily CSV overlaps {year} in {folder}"
        )
    return matches


def load_nasa_daily(paths: list[Path], year: int) -> pd.DataFrame:
    """Load, validate, and retain one calendar year of NASA daily data."""

    frames: list[pd.DataFrame] = []
    for path in paths:
        match = PERIOD_FILENAME.fullmatch(path.name)
        if not match:
            raise ValueError(f"NASA filename must be YYYYMMDD_YYYYMMDD.csv: {path.name}")
        start = pd.to_datetime(match.group(1), format="%Y%m%d")
        end = pd.to_datetime(match.group(2), format="%Y%m%d")
        frame = pd.read_csv(path, dtype={"ibge_code": "string"})
        _require_columns(frame, NASA_COLUMNS, f"NASA file {path.name}")
        frame = frame[NASA_COLUMNS].copy()
        frame["ibge_code"] = _clean_ibge(frame["ibge_code"], path.name)
        frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
        outside_filename_period = ~frame["Date"].between(start, end)
        if outside_filename_period.any():
            raise ValueError(f"NASA dates fall outside the filename period: {path.name}")
        frame = frame.loc[frame["Date"].dt.year.eq(year)].copy()
        if not frame.empty:
            frames.append(frame)
    if not frames:
        raise ValueError(f"NASA files contain no rows for {year}")
    daily = pd.concat(frames, ignore_index=True)
    duplicate_count = int(daily.duplicated(["ibge_code", "Date"]).sum())
    if duplicate_count:
        raise ValueError(
            f"NASA data contains {duplicate_count} duplicate municipality-date rows"
        )
    if not daily["state"].astype("string").str.strip().eq("SP").all():
        raise ValueError("NASA input contains non-SP rows")
    return daily.sort_values(["ibge_code", "Date"]).reset_index(drop=True)


def aggregate_nasa_monthly(
    daily: pd.DataFrame,
    year: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate valid NASA daily observations to municipality-month rows."""

    _require_columns(daily, NASA_COLUMNS, "NASA daily data")
    prepared = daily.copy()
    prepared["ibge_code"] = _clean_ibge(prepared["ibge_code"], "NASA data")
    prepared["Date"] = pd.to_datetime(prepared["Date"], errors="raise")
    if not prepared["Date"].dt.year.eq(year).all():
        raise ValueError(f"NASA daily data contains dates outside {year}")
    if prepared.duplicated(["ibge_code", "Date"]).any():
        raise ValueError("NASA data contains duplicate municipality-date rows")

    invalid_counts: dict[str, int] = {}
    for column in NASA_VALUE_COLUMNS:
        numeric = pd.to_numeric(prepared[column], errors="coerce")
        invalid = ~np.isfinite(numeric) | numeric.eq(-999)
        invalid_counts[column] = int(invalid.sum())
        prepared[column] = numeric.mask(invalid)

    prepared["valid_weather_day"] = prepared[NASA_VALUE_COLUMNS].notna().all(axis=1)
    valid = prepared.loc[prepared["valid_weather_day"]].copy()
    valid["month"] = valid["Date"].dt.strftime("%Y-%m")
    monthly = (
        valid.groupby(["ibge_code", "month"], as_index=False)
        .agg(
            nasa_observed_days=("Date", "nunique"),
            nasa_total_rainfall_mm=("PRECTOTCORR", "sum"),
            nasa_average_temperature_c=("T2M", "mean"),
            nasa_average_relative_humidity_pct=("RH2M", "mean"),
        )
        .sort_values(["ibge_code", "month"])
        .reset_index(drop=True)
    )
    expected = monthly["month"].map(
        lambda value: calendar.monthrange(*map(int, value.split("-")))[1]
    )
    incomplete = monthly.loc[monthly["nasa_observed_days"].ne(expected)]
    report = {
        "input_rows": int(len(prepared)),
        "municipalities": int(prepared["ibge_code"].nunique()),
        "unique_dates": int(prepared["Date"].nunique()),
        "invalid_value_counts": invalid_counts,
        "valid_weather_rows": int(prepared["valid_weather_day"].sum()),
        "monthly_rows": int(len(monthly)),
        "incomplete_month_rows": int(len(incomplete)),
    }
    return monthly, report


def load_era5_monthly(folder: Path, year: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load existing ERA5 municipality monthly output for one year."""

    if not folder.is_dir():
        raise FileNotFoundError(f"ERA5 municipality monthly folder not found: {folder}")
    paths = sorted(folder.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No ERA5 monthly CSV files found in {folder}")
    frames = []
    for path in paths:
        frame = pd.read_csv(path, dtype={"ibge_code": "string"})
        _require_columns(frame, ERA5_COLUMNS, f"ERA5 file {path.name}")
        frame = frame[ERA5_COLUMNS].copy()
        if not frame["grid_id"].astype("string").eq(path.stem).all():
            raise ValueError(f"ERA5 grid_id does not match filename: {path.name}")
        frames.append(frame)
    era5 = pd.concat(frames, ignore_index=True)
    era5["ibge_code"] = _clean_ibge(era5["ibge_code"], "ERA5 data")
    if era5.duplicated(["ibge_code", "month"]).any():
        raise ValueError("ERA5 data contains duplicate municipality-month rows")
    expected_prefix = f"{year}-"
    if not era5["month"].astype("string").str.startswith(expected_prefix).all():
        raise ValueError(f"ERA5 monthly data contains months outside {year}")
    parsed_month = pd.to_datetime(era5["month"], format="%Y-%m", errors="raise")
    calculated_days = parsed_month.dt.days_in_month
    observed = pd.to_numeric(era5["observed_days"], errors="raise")
    stated_expected = pd.to_numeric(era5["expected_days"], errors="raise")
    complete_text = era5["complete_month"].astype("string").str.strip().str.lower()
    valid_complete_text = complete_text.isin(["true", "false"])
    if not valid_complete_text.all():
        raise ValueError("ERA5 complete_month contains non-boolean values")
    complete = complete_text.eq("true")
    if not stated_expected.eq(calculated_days).all():
        raise ValueError("ERA5 expected_days does not match the calendar month")
    internally_complete = observed.eq(stated_expected)
    if not complete.eq(internally_complete).all():
        raise ValueError("ERA5 complete_month disagrees with observed/expected days")
    for column in ERA5_VALUE_COLUMNS:
        values = pd.to_numeric(era5[column], errors="coerce")
        if (~np.isfinite(values)).any():
            raise ValueError(f"ERA5 contains missing or non-finite values in {column}")
        era5[column] = values
    era5["observed_days"] = observed
    report = {
        "source_files": int(len(paths)),
        "rows": int(len(era5)),
        "municipalities": int(era5["ibge_code"].nunique()),
        "months": int(era5["month"].nunique()),
        "incomplete_month_rows": int((~complete).sum()),
    }
    return era5, report


def build_combined_monthly(
    mapping: pd.DataFrame,
    nasa_monthly: pd.DataFrame,
    era5_monthly: pd.DataFrame,
    year: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build all expected municipality-month keys and join both sources."""

    _require_columns(mapping, MAPPING_COLUMNS, "Combined weather mapping")
    mapping = mapping.copy()
    mapping["ibge_code"] = _clean_ibge(mapping["ibge_code"], "Mapping")
    if mapping["ibge_code"].duplicated().any():
        raise ValueError("Mapping must contain unique IBGE codes")
    mapping_codes = set(mapping["ibge_code"])

    nasa_extra = sorted(set(nasa_monthly["ibge_code"]) - mapping_codes)
    era5_extra = sorted(set(era5_monthly["ibge_code"]) - mapping_codes)
    if nasa_extra or era5_extra:
        raise ValueError(
            "Source contains IBGE codes absent from mapping: "
            f"NASA={nasa_extra[:5]}, ERA5={era5_extra[:5]}"
        )

    months = pd.DataFrame({"month": [f"{year}-{month:02d}" for month in range(1, 13)]})
    expected = mapping[[
        "municipality",
        "ibge_code",
        "nasa_weather_group_id",
        "era5_grid_id",
    ]].merge(months, how="cross")

    nasa_columns = [
        "ibge_code",
        "month",
        "nasa_observed_days",
        "nasa_total_rainfall_mm",
        "nasa_average_temperature_c",
        "nasa_average_relative_humidity_pct",
    ]
    era_columns = [
        "ibge_code",
        "month",
        "grid_id",
        "observed_days",
        *ERA5_VALUE_COLUMNS,
    ]
    combined = expected.merge(
        nasa_monthly[nasa_columns],
        on=["ibge_code", "month"],
        how="left",
        validate="one_to_one",
    )
    combined = combined.merge(
        era5_monthly[era_columns],
        on=["ibge_code", "month"],
        how="left",
        validate="one_to_one",
    )
    grid_mismatch = combined["grid_id"].notna() & combined["grid_id"].ne(
        combined["era5_grid_id"]
    )
    if grid_mismatch.any():
        examples = combined.loc[
            grid_mismatch, ["ibge_code", "era5_grid_id", "grid_id"]
        ].head().to_dict("records")
        raise ValueError(f"ERA5 grid mapping mismatch: {examples}")
    combined = combined.rename(columns={"observed_days": "era5_observed_days"})
    combined = combined.drop(columns=["grid_id"])
    combined = combined[OUTPUT_COLUMNS].sort_values(
        ["ibge_code", "month"]
    ).reset_index(drop=True)

    key_duplicates = int(combined.duplicated(["ibge_code", "month"]).sum())
    if key_duplicates:
        raise ValueError("Combined output contains duplicate municipality-month rows")
    report = {
        "expected_rows": int(len(mapping) * 12),
        "actual_rows": int(len(combined)),
        "municipalities": int(combined["ibge_code"].nunique()),
        "months": int(combined["month"].nunique()),
        "duplicate_keys": key_duplicates,
        "missing_nasa_rows": int(combined["nasa_observed_days"].isna().sum()),
        "missing_era5_rows": int(combined["era5_observed_days"].isna().sum()),
        "rows_missing_both_sources": int(
            (
                combined["nasa_observed_days"].isna()
                & combined["era5_observed_days"].isna()
            ).sum()
        ),
    }
    return combined, report


def compare_dataframes(
    actual: pd.DataFrame,
    pilot: pd.DataFrame,
    absolute_tolerance: float = 1e-12,
    relative_tolerance: float = 1e-12,
) -> dict[str, Any]:
    """Compare the output contract and every keyed value in two dataframes."""

    pilot = pilot.copy()
    pilot["ibge_code"] = _clean_ibge(pilot["ibge_code"], "Pilot")
    columns_match = pilot.columns.tolist() == OUTPUT_COLUMNS
    if not columns_match:
        return {
            "status": "failed",
            "columns_match": False,
            "expected_columns": OUTPUT_COLUMNS,
            "pilot_columns": pilot.columns.tolist(),
        }
    actual_sorted = actual.sort_values(["ibge_code", "month"]).reset_index(drop=True)
    pilot_sorted = pilot.sort_values(["ibge_code", "month"]).reset_index(drop=True)
    key_columns = ["ibge_code", "month"]
    actual_keys = set(map(tuple, actual_sorted[key_columns].itertuples(index=False, name=None)))
    pilot_keys = set(map(tuple, pilot_sorted[key_columns].itertuples(index=False, name=None)))
    missing_keys = sorted(pilot_keys - actual_keys)
    extra_keys = sorted(actual_keys - pilot_keys)
    merged = pilot_sorted.merge(
        actual_sorted,
        on=key_columns,
        how="inner",
        suffixes=("_pilot", "_actual"),
        validate="one_to_one",
    )
    text_columns = [
        "municipality",
        "nasa_weather_group_id",
        "era5_grid_id",
    ]
    text_differences = {
        column: int(
            merged[f"{column}_pilot"].astype("string").ne(
                merged[f"{column}_actual"].astype("string")
            ).sum()
        )
        for column in text_columns
    }
    numeric_columns = [column for column in OUTPUT_COLUMNS if column not in key_columns + text_columns]
    numeric_differences: dict[str, dict[str, Any]] = {}
    for column in numeric_columns:
        expected = pd.to_numeric(merged[f"{column}_pilot"], errors="coerce").to_numpy()
        observed = pd.to_numeric(merged[f"{column}_actual"], errors="coerce").to_numpy()
        close = np.isclose(
            expected,
            observed,
            atol=absolute_tolerance,
            rtol=relative_tolerance,
            equal_nan=True,
        )
        finite_pairs = np.isfinite(expected) & np.isfinite(observed)
        max_abs = (
            float(np.max(np.abs(expected[finite_pairs] - observed[finite_pairs])))
            if finite_pairs.any()
            else None
        )
        numeric_differences[column] = {
            "different_values": int((~close).sum()),
            "max_absolute_difference": max_abs,
        }
    difference_count = (
        len(missing_keys)
        + len(extra_keys)
        + sum(text_differences.values())
        + sum(item["different_values"] for item in numeric_differences.values())
    )
    return {
        "status": "passed" if difference_count == 0 else "failed",
        "columns_match": True,
        "pilot_rows": int(len(pilot_sorted)),
        "actual_rows": int(len(actual_sorted)),
        "matched_keys": int(len(merged)),
        "missing_keys": len(missing_keys),
        "extra_keys": len(extra_keys),
        "missing_key_examples": missing_keys[:10],
        "extra_key_examples": extra_keys[:10],
        "text_differences": text_differences,
        "numeric_differences": numeric_differences,
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
    }


def compare_to_pilot(
    actual: pd.DataFrame,
    pilot_path: Path,
    absolute_tolerance: float = 1e-12,
    relative_tolerance: float = 1e-12,
) -> dict[str, Any]:
    """Compare the output contract and every keyed value with an approved pilot."""

    if not pilot_path.is_file():
        raise FileNotFoundError(f"Pilot CSV not found: {pilot_path}")
    pilot = pd.read_csv(pilot_path, dtype={"ibge_code": "string"})
    return compare_dataframes(
        actual=actual,
        pilot=pilot,
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
    )


def run_year(
    year: int,
    mapping_path: Path,
    nasa_input_root: Path,
    era5_input_root: Path,
    output_path: Path,
    report_path: Path,
    pilot_path: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run one local calendar year and write CSV plus a coverage report."""

    mapping = load_mapping(mapping_path)
    nasa_files = discover_nasa_files(nasa_input_root, year)
    nasa_daily = load_nasa_daily(nasa_files, year)
    nasa_monthly, nasa_report = aggregate_nasa_monthly(nasa_daily, year)
    era_folder = era5_input_root / f"{year}-01-01_{year}-12-31" / "municipality" / "monthly"
    era5_monthly, era5_report = load_era5_monthly(era_folder, year)

    nasa_names = nasa_daily[["ibge_code", "municipality"]].drop_duplicates()
    if nasa_names["ibge_code"].duplicated().any():
        raise ValueError("NASA data has inconsistent municipality names for an IBGE code")
    name_check = mapping[["ibge_code", "municipality"]].merge(
        nasa_names,
        on="ibge_code",
        how="left",
        suffixes=("_mapping", "_nasa"),
        validate="one_to_one",
    )
    if name_check["municipality_nasa"].isna().any() or not name_check[
        "municipality_mapping"
    ].eq(name_check["municipality_nasa"]).all():
        raise ValueError("NASA municipality names or coverage differ from the mapping")

    combined, output_report = build_combined_monthly(
        mapping=mapping,
        nasa_monthly=nasa_monthly,
        era5_monthly=era5_monthly,
        year=year,
    )
    report: dict[str, Any] = {
        "year": year,
        "mapping": {
            "municipalities": int(len(mapping)),
            "nasa_weather_groups": int(mapping["nasa_weather_group_id"].nunique()),
            "era5_grids": int(mapping["era5_grid_id"].nunique()),
            "duplicate_ibge_codes": int(mapping["ibge_code"].duplicated().sum()),
        },
        "nasa": {
            "source_files": [str(path.resolve()) for path in nasa_files],
            **nasa_report,
        },
        "era5": era5_report,
        "output": output_report,
        "date_alignment_note": (
            "NASA Date labels are used as supplied. ERA5 monthly data was produced in "
            "Etc/GMT+3 by the existing processor. No date or timezone shifting is applied."
        ),
    }
    if pilot_path is not None:
        report["pilot_comparison"] = compare_to_pilot(combined, pilot_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return combined, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--mapping", type=Path, default=None)
    parser.add_argument("--nasa-input-root", type=Path, default=None)
    parser.add_argument("--era5-input-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--pilot", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    output_root = root / "data/processed/weather/combined/pilot"
    output = args.output or output_root / f"sp_municipality_monthly_weather_{args.year}.csv"
    report = args.report or output_root / f"sp_municipality_monthly_weather_{args.year}_validation.json"
    _, validation = run_year(
        year=args.year,
        mapping_path=args.mapping or root / "data/metadata/sp_era5_nasa_weather_source_city_mapping.xlsx",
        nasa_input_root=args.nasa_input_root or root / "data/raw/nasa_power/daily_weather/SP",
        era5_input_root=args.era5_input_root or root / "data/processed/advanced_weather/era5/sampling_0p5/SP",
        output_path=output,
        report_path=report,
        pilot_path=args.pilot,
    )
    print(f"Saved combined weather: {output}")
    print(f"Saved validation report: {report}")
    pilot = validation.get("pilot_comparison")
    if pilot is not None:
        print(f"Pilot comparison: {pilot['status']}")
        return 0 if pilot["status"] == "passed" else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
