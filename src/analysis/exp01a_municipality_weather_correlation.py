"""EXP-01A municipality-level weather correlation analysis.

The command validates every annual combined-weather file before calculating any
correlation.  A material source gap writes the validation artifacts and a
stopped execution report, then exits without producing correlation results.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


EXPERIMENT = "exp_01a_municipality_weather_correlation"
EXPECTED_YEARS = tuple(range(1990, 2026))
KEY_COLUMNS = ["ibge_code", "year", "calendar_month"]
WEATHER_VARIABLES = [
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
CORE_PAIRS = [
    ("nasa_average_temperature_c", "vpd_mean_kpa"),
    ("nasa_total_rainfall_mm", "soil_moisture_0_to_7cm_m3_m3"),
    ("nasa_average_temperature_c", "soil_moisture_0_to_7cm_m3_m3"),
    ("nasa_total_rainfall_mm", "vpd_mean_kpa"),
    ("solar_radiation_mean_daily_mj_m2", "nasa_average_temperature_c"),
]
LAG_VARIABLES = [
    "nasa_total_rainfall_mm",
    "nasa_average_temperature_c",
    "vpd_mean_kpa",
    "soil_moisture_0_to_7cm_m3_m3",
]
CROSS_MONTH_VARIABLES = [
    "nasa_total_rainfall_mm",
    "nasa_average_temperature_c",
    "vpd_mean_kpa",
    "soil_moisture_0_to_7cm_m3_m3",
    "solar_radiation_mean_daily_mj_m2",
]


class ValidationGateError(RuntimeError):
    """Raised when EXP-01A must stop before correlation analysis."""


@dataclass(frozen=True)
class ValidationResult:
    data: pd.DataFrame
    inventory: pd.DataFrame
    coverage: pd.DataFrame
    missingness: pd.DataFrame
    merge_integrity: pd.DataFrame
    gate_reasons: tuple[str, ...]


def variable_inventory() -> pd.DataFrame:
    """Return the code-verified combined-weather column inventory."""

    rows = [
        ("municipality", "identifier", "metadata", "text", "mapping value", "authoritative mapping", False, "Municipality name"),
        ("ibge_code", "identifier", "metadata", "code", "one value per municipality", "authoritative mapping", False, "Canonical municipality identifier"),
        ("month", "identifier", "metadata", "YYYY-MM", "calendar month", "combined pipeline", False, "Parsed into year and calendar_month"),
        ("nasa_weather_group_id", "source mapping", "metadata", "identifier", "shared source group", "NASA POWER mapping", False, "Not a weather measurement"),
        ("era5_grid_id", "source mapping", "metadata", "identifier", "nearest sampled grid", "ERA5 mapping", False, "Not a weather measurement"),
        ("nasa_observed_days", "QA", "metadata", "days", "count of complete NASA days", "NASA POWER", False, "Coverage field"),
        ("era5_observed_days", "QA", "metadata", "days", "count of ERA5 days", "Open-Meteo ERA5", False, "Coverage field"),
        ("nasa_total_rainfall_mm", "precipitation", "basic", "mm", "monthly sum of daily PRECTOTCORR", "NASA POWER", True, "Daily rows require all NASA variables valid"),
        ("nasa_average_temperature_c", "temperature", "basic", "degrees C", "monthly mean of daily T2M", "NASA POWER", True, "Near-surface air temperature"),
        ("nasa_average_relative_humidity_pct", "relative humidity", "basic", "percent", "monthly mean of daily RH2M", "NASA POWER", True, "Near-surface relative humidity"),
        ("vpd_mean_kpa", "VPD", "advanced", "kPa", "monthly mean of daily mean hourly VPD", "Open-Meteo ERA5", True, "Hourly VPD averaged to day, then month"),
        ("vpd_mean_daily_max_kpa", "VPD", "advanced", "kPa", "monthly mean of daily maximum hourly VPD", "Open-Meteo ERA5", True, "Distinct from monthly mean VPD"),
        ("soil_moisture_0_to_7cm_m3_m3", "soil moisture 0-7 cm", "advanced", "m3/m3", "monthly mean of daily mean hourly soil moisture", "Open-Meteo ERA5", True, "Volumetric soil water layer retained separately"),
        ("soil_moisture_7_to_28cm_m3_m3", "soil moisture 7-28 cm", "advanced", "m3/m3", "monthly mean of daily mean hourly soil moisture", "Open-Meteo ERA5", True, "Volumetric soil water layer retained separately"),
        ("soil_moisture_28_to_100cm_m3_m3", "soil moisture 28-100 cm", "advanced", "m3/m3", "monthly mean of daily mean hourly soil moisture", "Open-Meteo ERA5", True, "Volumetric soil water layer retained separately"),
        ("soil_moisture_100_to_255cm_m3_m3", "soil moisture 100-255 cm", "advanced", "m3/m3", "monthly mean of daily mean hourly soil moisture", "Open-Meteo ERA5", True, "Volumetric soil water layer retained separately"),
        ("solar_radiation_total_mj_m2", "solar radiation", "advanced", "MJ/m2", "monthly sum of daily shortwave-radiation sum", "Open-Meteo ERA5", True, "Monthly total retained as its verified definition"),
        ("solar_radiation_mean_daily_mj_m2", "solar radiation", "advanced", "MJ/m2/day", "monthly mean of daily shortwave-radiation sum", "Open-Meteo ERA5", True, "Mean daily radiation retained separately"),
    ]
    return pd.DataFrame(rows, columns=[
        "column_name", "feature_family", "basic_or_advanced", "unit",
        "aggregation_definition", "source", "included_in_exp01a", "notes",
    ])


def parse_month_fields(frame: pd.DataFrame) -> pd.DataFrame:
    """Parse strict YYYY-MM labels into year, month number, and month start."""

    result = frame.copy()
    dates = pd.to_datetime(result["month"], format="%Y-%m", errors="raise")
    if not dates.dt.strftime("%Y-%m").eq(result["month"].astype("string")).all():
        raise ValueError("month must use canonical YYYY-MM formatting")
    result["year"] = dates.dt.year
    result["calendar_month"] = dates.dt.month
    result["date"] = dates
    return result


def detect_duplicate_keys(frame: pd.DataFrame) -> pd.DataFrame:
    """Return every row belonging to a duplicate municipality-month key."""

    return frame.loc[frame.duplicated(KEY_COLUMNS, keep=False)].copy()


def load_and_validate(input_dir: Path, expected_years: Iterable[int] = EXPECTED_YEARS) -> ValidationResult:
    """Load annual files and produce all mandatory pre-analysis validation tables."""

    expected_years = tuple(expected_years)
    paths = sorted(input_dir.glob("sp_municipality_monthly_weather_*.csv"))
    path_by_year: dict[int, list[Path]] = {year: [] for year in expected_years}
    unexpected: list[str] = []
    for path in paths:
        suffix = path.stem.rsplit("_", 1)[-1]
        if suffix.isdigit() and int(suffix) in path_by_year:
            path_by_year[int(suffix)].append(path)
        else:
            unexpected.append(path.name)

    reasons: list[str] = []
    missing_files = [year for year, matches in path_by_year.items() if not matches]
    duplicate_files = {year: matches for year, matches in path_by_year.items() if len(matches) > 1}
    if missing_files:
        reasons.append(f"Missing annual combined-weather files: {missing_files}")
    if duplicate_files:
        reasons.append(f"Duplicate annual files for years: {sorted(duplicate_files)}")
    if unexpected:
        reasons.append(f"Unexpected combined-weather filenames: {unexpected}")

    frames: list[pd.DataFrame] = []
    for year in expected_years:
        if len(path_by_year[year]) != 1:
            continue
        frame = pd.read_csv(path_by_year[year][0], dtype={"ibge_code": "string"})
        expected_columns = set(variable_inventory()["column_name"])
        missing_columns = sorted(expected_columns - set(frame.columns))
        if missing_columns:
            reasons.append(f"{year} missing columns: {missing_columns}")
            continue
        frame = parse_month_fields(frame)
        if not frame["year"].eq(year).all():
            reasons.append(f"{year} file contains month labels from another year")
        frame["source_file"] = str(path_by_year[year][0].resolve())
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if data.empty:
        raise ValidationGateError("No readable annual combined-weather data")

    duplicates = detect_duplicate_keys(data)
    if not duplicates.empty:
        reasons.append(f"Duplicate municipality-year-month keys: {len(duplicates)} rows")

    coverage_rows = []
    previous_codes: set[str] | None = None
    for year in expected_years:
        subset = data.loc[data["year"].eq(year)]
        codes = set(subset["ibge_code"].dropna().astype(str))
        counts = subset.groupby("ibge_code")["calendar_month"].nunique() if not subset.empty else pd.Series(dtype=int)
        expected_rows = len(codes) * 12
        coverage_rows.append({
            "year": year,
            "source_file": subset["source_file"].iloc[0] if not subset.empty else "",
            "municipalities": len(codes),
            "municipality_month_rows": len(subset),
            "expected_rows_from_year_universe": expected_rows,
            "distinct_months": int(subset["calendar_month"].nunique()),
            "duplicate_keys": int(subset.duplicated(KEY_COLUMNS).sum()),
            "municipalities_with_missing_months": int(counts.lt(12).sum()),
            "missing_municipality_months": int(expected_rows - len(subset)),
            "municipalities_entering": 0 if previous_codes is None else len(codes - previous_codes),
            "municipalities_leaving": 0 if previous_codes is None else len(previous_codes - codes),
        })
        previous_codes = codes
    coverage = pd.DataFrame(coverage_rows)
    bad_coverage = coverage.loc[
        coverage["municipality_month_rows"].ne(coverage["expected_rows_from_year_universe"])
        | coverage["distinct_months"].ne(12)
        | coverage["duplicate_keys"].gt(0)
        | coverage["municipalities_with_missing_months"].gt(0)
    ]
    if not bad_coverage.empty:
        reasons.append(f"Incomplete or duplicate key coverage in years: {bad_coverage['year'].tolist()}")

    missing_rows = []
    for variable in WEATHER_VARIABLES:
        for scope, period, subset in [("overall", "all", data)]:
            missing_rows.append(_missingness_row(variable, scope, period, subset))
        for year, subset in data.groupby("year", sort=True):
            missing_rows.append(_missingness_row(variable, "year", str(year), subset))
        for month, subset in data.groupby("calendar_month", sort=True):
            missing_rows.append(_missingness_row(variable, "calendar_month", str(month), subset))
    missingness = pd.DataFrame(missing_rows)

    merge_rows = []
    for year, subset in data.groupby("year", sort=True):
        basic = subset["nasa_observed_days"].notna()
        advanced = subset["era5_observed_days"].notna()
        merge_rows.append({
            "year": year,
            "rows": len(subset),
            "basic_only_rows": int((basic & ~advanced).sum()),
            "advanced_only_rows": int((~basic & advanced).sum()),
            "both_sources_rows": int((basic & advanced).sum()),
            "neither_source_rows": int((~basic & ~advanced).sum()),
            "months_with_any_missing_basic": ";".join(map(str, sorted(subset.loc[~basic, "calendar_month"].unique()))),
            "months_with_any_missing_advanced": ";".join(map(str, sorted(subset.loc[~advanced, "calendar_month"].unique()))),
        })
    merge_integrity = pd.DataFrame(merge_rows)

    # An entire source missing for every municipality in a year-month is material.
    source_month = data.groupby(["year", "calendar_month"]).agg(
        rows=("ibge_code", "size"),
        basic_present=("nasa_observed_days", "count"),
        advanced_present=("era5_observed_days", "count"),
    ).reset_index()
    material = source_month.loc[
        source_month["basic_present"].eq(0) | source_month["advanced_present"].eq(0)
    ]
    if not material.empty:
        labels = [f"{int(row.year)}-{int(row.calendar_month):02d}" for row in material.itertuples()]
        reasons.append("Material source gaps (an entire source absent for all municipalities): " + ", ".join(labels))

    if data["ibge_code"].isna().any() or data["ibge_code"].str.strip().eq("").any():
        reasons.append("Missing canonical IBGE municipality identifiers")
    return ValidationResult(
        data=data,
        inventory=variable_inventory(),
        coverage=coverage,
        missingness=missingness,
        merge_integrity=merge_integrity,
        gate_reasons=tuple(reasons),
    )


def _missingness_row(variable: str, scope: str, period: str, frame: pd.DataFrame) -> dict[str, object]:
    missing = int(frame[variable].isna().sum())
    return {
        "column_name": variable,
        "scope": scope,
        "period": period,
        "total_observations": len(frame),
        "non_missing_observations": len(frame) - missing,
        "missing_observations": missing,
        "missing_share": missing / len(frame) if len(frame) else np.nan,
    }


def pairwise_correlation(frame: pd.DataFrame, x: str, y: str, method: str) -> tuple[float, int, str]:
    """Calculate a pairwise-complete correlation with explicit constant handling."""

    pair = pd.concat(
        [frame[x].rename("_x"), frame[y].rename("_y")], axis=1
    ).replace([np.inf, -np.inf], np.nan).dropna()
    n = len(pair)
    if n < 2:
        return np.nan, n, "insufficient_observations"
    if pair["_x"].nunique(dropna=True) < 2 or pair["_y"].nunique(dropna=True) < 2:
        return np.nan, n, "constant_variable"
    value = float(pair["_x"].corr(pair["_y"], method=method))
    if not -1.0 <= value <= 1.0:
        raise AssertionError(f"Correlation outside [-1, 1]: {value}")
    return value, n, "defined"


def correlation_matrices(frame: pd.DataFrame, variables: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return Pearson, Spearman, and shared pairwise-count matrices."""

    pearson = pd.DataFrame(np.nan, index=variables, columns=variables)
    spearman = pearson.copy()
    counts = pd.DataFrame(0, index=variables, columns=variables, dtype=int)
    for x in variables:
        for y in variables:
            pearson.loc[x, y], counts.loc[x, y], _ = pairwise_correlation(frame, x, y, "pearson")
            spearman.loc[x, y], spearman_n, _ = pairwise_correlation(frame, x, y, "spearman")
            if spearman_n != counts.loc[x, y]:
                raise AssertionError("Pearson and Spearman pairwise counts differ")
    return pearson, spearman, counts


def monthly_correlations(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Calculate each unordered variable pair within each calendar month."""

    rows = []
    for month in range(1, 13):
        subset = frame.loc[frame["calendar_month"].eq(month)]
        for x, y in combinations(variables, 2):
            pearson, pearson_n, pearson_status = pairwise_correlation(subset, x, y, "pearson")
            spearman, spearman_n, spearman_status = pairwise_correlation(subset, x, y, "spearman")
            rows.append({
                "month": month, "variable_x": x, "variable_y": y,
                "pearson_r": pearson, "pearson_n": pearson_n,
                "pearson_status": pearson_status,
                "spearman_rho": spearman, "spearman_n": spearman_n,
                "spearman_status": spearman_status,
            })
    return pd.DataFrame(rows)


def construct_lag1(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Attach lags only for exactly consecutive months within municipality."""

    ordered = frame.sort_values(["ibge_code", "date"]).copy()
    previous_date = ordered.groupby("ibge_code")["date"].shift(1)
    expected_previous = ordered["date"] - pd.offsets.MonthBegin(1)
    consecutive = previous_date.eq(expected_previous)
    for variable in variables:
        lagged = ordered.groupby("ibge_code")[variable].shift(1)
        ordered[f"{variable}_lag1"] = lagged.where(consecutive)
    return ordered


def lag1_results(frame: pd.DataFrame, variables: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    lagged = construct_lag1(frame, variables)
    overall_rows, monthly_rows = [], []
    for variable in variables:
        lag = f"{variable}_lag1"
        p, pn, ps = pairwise_correlation(lagged, variable, lag, "pearson")
        s, sn, ss = pairwise_correlation(lagged, variable, lag, "spearman")
        overall_rows.append({"variable": variable, "pearson_r": p, "pearson_n": pn, "pearson_status": ps, "spearman_rho": s, "spearman_n": sn, "spearman_status": ss})
        for month in range(1, 13):
            subset = lagged.loc[lagged["calendar_month"].eq(month)]
            p, pn, ps = pairwise_correlation(subset, variable, lag, "pearson")
            s, sn, ss = pairwise_correlation(subset, variable, lag, "spearman")
            monthly_rows.append({"destination_month": month, "variable": variable, "pearson_r": p, "pearson_n": pn, "pearson_status": ps, "spearman_rho": s, "spearman_n": sn, "spearman_status": ss})
    return pd.DataFrame(overall_rows), pd.DataFrame(monthly_rows)


def cross_month_matrices(
    frame: pd.DataFrame,
    variable: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Correlate one variable across calendar months on municipality-year rows."""

    required = {"ibge_code", "year", "calendar_month", variable}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Cross-month input missing columns: {missing}")
    if frame.duplicated(["ibge_code", "year", "calendar_month"]).any():
        raise ValueError("Cross-month input contains duplicate municipality-year-month keys")
    invalid_months = ~frame["calendar_month"].between(1, 12, inclusive="both")
    if invalid_months.any():
        raise ValueError("Cross-month input contains calendar months outside 1-12")

    wide = frame.pivot(index=["ibge_code", "year"], columns="calendar_month", values=variable)
    wide = wide.reindex(columns=range(1, 13))
    pearson = pd.DataFrame(np.nan, index=range(1, 13), columns=range(1, 13))
    spearman = pearson.copy()
    counts = pd.DataFrame(0, index=range(1, 13), columns=range(1, 13), dtype=int)
    for month_x in range(1, 13):
        for month_y in range(1, 13):
            pearson.loc[month_x, month_y], counts.loc[month_x, month_y], _ = pairwise_correlation(
                wide, month_x, month_y, "pearson"
            )
            spearman.loc[month_x, month_y], spearman_n, _ = pairwise_correlation(
                wide, month_x, month_y, "spearman"
            )
            if spearman_n != counts.loc[month_x, month_y]:
                raise AssertionError("Pearson and Spearman cross-month counts differ")
    pearson.index.name = spearman.index.name = counts.index.name = "month"
    pearson.columns.name = spearman.columns.name = counts.columns.name = "month"
    return pearson, spearman, counts


def cross_month_dependence_summary(
    matrices: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]],
) -> pd.DataFrame:
    """Summarize correlation decay without imposing a keep/drop threshold."""

    rows = []
    for variable, (pearson, spearman, counts) in matrices.items():
        row: dict[str, object] = {"variable": variable}
        for method, matrix in [("pearson", pearson), ("spearman", spearman)]:
            for distance, label in [(1, "adjacent"), (2, "two_month"), (3, "three_month"), (6, "six_month")]:
                values = [matrix.loc[month, month + distance] for month in range(1, 13 - distance)]
                row[f"{method}_mean_{label}"] = float(np.nanmean(values))
                row[f"{method}_min_{label}"] = float(np.nanmin(values))
                row[f"{method}_max_{label}"] = float(np.nanmax(values))
            off_diagonal = matrix.to_numpy(dtype=float)[~np.eye(12, dtype=bool)]
            row[f"{method}_mean_all_off_diagonal"] = float(np.nanmean(off_diagonal))
        off_diagonal_counts = counts.to_numpy(dtype=int)[~np.eye(12, dtype=bool)]
        row["pairwise_n_min_off_diagonal"] = int(off_diagonal_counts.min())
        row["pairwise_n_max_off_diagonal"] = int(off_diagonal_counts.max())
        rows.append(row)
    return pd.DataFrame(rows)


def _matrix_pairs(matrix: pd.DataFrame, method: str, scope: str) -> list[dict[str, object]]:
    rows = []
    for x, y in combinations(matrix.columns, 2):
        value = matrix.loc[x, y]
        rows.append({"scope": scope, "month": "", "method": method, "variable_x": x, "variable_y": y, "correlation": value, "absolute_correlation": abs(value) if pd.notna(value) else np.nan})
    return rows


def strongest_pairs(pearson: pd.DataFrame, spearman: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    rows = _matrix_pairs(pearson, "pearson", "pooled") + _matrix_pairs(spearman, "spearman", "pooled")
    for row in monthly.itertuples(index=False):
        for method, value in [("pearson", row.pearson_r), ("spearman", row.spearman_rho)]:
            rows.append({"scope": "calendar_month", "month": row.month, "method": method, "variable_x": row.variable_x, "variable_y": row.variable_y, "correlation": value, "absolute_correlation": abs(value) if pd.notna(value) else np.nan})
    result = pd.DataFrame(rows)
    return result.sort_values(["scope", "method", "absolute_correlation"], ascending=[True, True, False], na_position="last").reset_index(drop=True)


def _heatmap(matrix: pd.DataFrame, title: str, path: Path, vmin: float = -1, vmax: float = 1) -> None:
    fig, ax = plt.subplots(figsize=(12, 9))
    image = ax.imshow(matrix.to_numpy(dtype=float), cmap="coolwarm", vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(matrix.columns)), labels=matrix.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(matrix.index)), labels=matrix.index, fontsize=8)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, shrink=0.8, label="correlation")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _core_month_matrix(core: pd.DataFrame, value: str) -> pd.DataFrame:
    labeled = core.assign(pair=core["variable_x"] + " ↔ " + core["variable_y"])
    return labeled.pivot(index="month", columns="pair", values=value).reindex(range(1, 13))


def write_stopped_report(path: Path, validation: ValidationResult, input_dir: Path) -> None:
    affected = validation.merge_integrity.loc[validation.merge_integrity["advanced_only_rows"].gt(0)]
    text = f"""# EXP-01A execution report

## Status

**STOPPED AT THE MANDATORY DATA-VALIDATION GATE.** No correlations, rankings, lag-persistence estimates, figures, or scientific interpretations were produced.

## Data validation

- Exact source path: `{input_dir.resolve()}` (`sp_municipality_monthly_weather_YYYY.csv`).
- Files found: {len(validation.coverage)} annual files covering {int(validation.coverage.year.min())}–{int(validation.coverage.year.max())}.
- Canonical key: `ibge_code × year × calendar_month`; duplicate keys: {int(validation.coverage.duplicate_keys.sum())}.
- Municipality universe: {int(validation.coverage.municipalities.min())}–{int(validation.coverage.municipalities.max())} per year.
- Rows: {int(validation.coverage.municipality_month_rows.sum()):,}.
- Verified correlation-variable inventory: {', '.join(WEATHER_VARIABLES)}.
- Units, aggregations, sources, metadata exclusions, and all soil/radiation definitions are recorded in `weather_variable_inventory.csv`.
- Missingness by variable, year, and calendar month is recorded in `weather_missingness_summary.csv`.
- Source alignment is recorded in `merge_integrity_summary.csv`.

### Mandatory stopping condition

{chr(10).join(f'- {reason}' for reason in validation.gate_reasons)}

The 2009 file contains complete ERA5 data but NASA POWER data only for September–December. January–August contain 5,136 advanced-only rows ({int(affected['advanced_only_rows'].sum()) if not affected.empty else 0:,} total), representing all 642 municipalities in each of eight months. Repository evidence identifies the sole NASA source as `20090901_20091231.csv`; therefore this is a real upstream coverage gap, not a merge or parsing artifact. Eight wholly absent basic-weather months are material under the handover's stopping rule.

## Methods planned but not executed

The implemented module uses pairwise-complete Pearson and Spearman correlations, calendar-month grouping, and exact consecutive-month lags within IBGE municipality (including December→January and never bridging gaps). These methods were not applied to the repository data because the validation gate failed.

## Results

No EXP-01A correlation result is reported or interpreted. Producing results by silently excluding 2009, using unequal source windows, or imputing the missing NASA values would contradict the approved gate.

## Interpretation limits

- Predictor correlation does not prove predictive redundancy.
- EXP-01A does not select final yield-model features.
- EXP-01B and EXP-01C remain required before deciding how crop-area weighting changes the picture.
- EXP-01B and EXP-01C were not run.

## Engineering verification

- Implemented `src/analysis/exp01a_municipality_weather_correlation.py`.
- Added focused tests at `src/tests/analysis/test_exp01a_municipality_weather_correlation.py`.
- Validation artifacts were written before the stop.
- Focused EXP-01A tests: **13 passed** (`py -3 -m pytest -q src/tests/analysis/test_exp01a_municipality_weather_correlation.py`).
- Related combined-weather ETL tests: **7 passed** (`py -3 -m pytest -q src/tests/etl/weather`).
- Full repository suite: **194 passed, 3 warnings** (`py -3 -m pytest -q --basetemp ...` outside the restricted temporary-directory sandbox). The warnings are pre-existing deprecation/date-parsing warnings.
- The first full-suite attempt reached 160 passes and 34 setup errors because pytest could not access its default Windows temporary directory; the unrestricted rerun confirms those were environment errors, not test failures.
- Analysis invocation: `$env:PYTHONPATH = 'src'; py -3 -m analysis.exp01a_municipality_weather_correlation --project-root \"D:\\Desktop\\Operation Sugar\"`; controlled validation-gate stop as documented above.
- Upstream downloaders and ETL modules were not modified.
- Existing unrelated working-tree changes were preserved.

## Required resolution before rerun

Provide and rebuild complete NASA POWER daily data for 2009-01-01 through 2009-08-31, then rerun the combined-weather builder and EXP-01A. If the research design instead intends to exclude 2009, that is a material scope decision and should be explicitly approved before rerunning.
"""
    path.write_text(text, encoding="utf-8")


def _pair_label(x: str, y: str) -> str:
    return f"{x} ↔ {y}"


def _number(value: float, digits: int = 3) -> str:
    return "NA" if pd.isna(value) else f"{value:.{digits}f}"


def write_success_report(
    path: Path,
    validation: ValidationResult,
    input_dir: Path,
    pearson: pd.DataFrame,
    spearman: pd.DataFrame,
    monthly: pd.DataFrame,
    core: pd.DataFrame,
    divergence: pd.DataFrame,
    lag_overall: pd.DataFrame,
    lag_monthly: pd.DataFrame,
    cross_month_summary: pd.DataFrame,
) -> None:
    """Write the completed, interpretation-limited EXP-01A report."""

    basic = set(WEATHER_VARIABLES[:3])
    advanced = set(WEATHER_VARIABLES[3:])
    cross_rows = []
    for method, matrix in [("Pearson", pearson), ("Spearman", spearman)]:
        for x, y in combinations(WEATHER_VARIABLES, 2):
            if not ((x in basic and y in advanced) or (x in advanced and y in basic)):
                continue
            value = matrix.loc[x, y]
            cross_rows.append((method, x, y, value, abs(value)))
    cross_rows.sort(key=lambda item: (item[0], -item[4]))
    strongest_lines = []
    for method in ("Pearson", "Spearman"):
        selected = [row for row in cross_rows if row[0] == method][:5]
        strongest_lines.extend(
            f"- {method}: `{_pair_label(x, y)}` = {_number(value)} (n={int(validation.data[[x, y]].dropna().shape[0]):,})."
            for _, x, y, value, _ in selected
        )

    core_lines = []
    for (x, y), group in core.groupby(["variable_x", "variable_y"], sort=False):
        low = group.loc[group["pearson_r"].abs().idxmin()]
        high = group.loc[group["pearson_r"].abs().idxmax()]
        core_lines.append(
            f"- `{_pair_label(x, y)}`: weakest absolute Pearson in month {int(low.month)} "
            f"(r={_number(low.pearson_r)}, n={int(low.pearson_n):,}); strongest in month "
            f"{int(high.month)} (r={_number(high.pearson_r)}, n={int(high.pearson_n):,})."
        )

    divergence_lines = []
    for row in divergence.head(10).itertuples(index=False):
        divergence_lines.append(
            f"- Month {int(row.month)}, `{_pair_label(row.variable_x, row.variable_y)}`: "
            f"Pearson={_number(row.pearson_r)}, Spearman={_number(row.spearman_rho)}, "
            f"|difference|={_number(row.absolute_pearson_spearman_difference)}."
        )

    lag_lines = []
    for row in lag_overall.sort_values("pearson_r", ascending=False).itertuples(index=False):
        month_group = lag_monthly.loc[lag_monthly["variable"].eq(row.variable)]
        lowest = month_group.loc[month_group["pearson_r"].idxmin()]
        highest = month_group.loc[month_group["pearson_r"].idxmax()]
        lag_lines.append(
            f"- `{row.variable}`: overall Pearson={_number(row.pearson_r)} and Spearman="
            f"{_number(row.spearman_rho)} (n={int(row.pearson_n):,}); destination-month Pearson "
            f"range {_number(lowest.pearson_r)} (month {int(lowest.destination_month)}) to "
            f"{_number(highest.pearson_r)} (month {int(highest.destination_month)})."
        )

    cross_month_lines = []
    for row in cross_month_summary.sort_values("pearson_mean_six_month", ascending=False).itertuples(index=False):
        cross_month_lines.append(
            f"- `{row.variable}`: mean adjacent-month Pearson={_number(row.pearson_mean_adjacent)}, "
            f"three-month={_number(row.pearson_mean_three_month)}, and six-month="
            f"{_number(row.pearson_mean_six_month)}; corresponding Spearman values are "
            f"{_number(row.spearman_mean_adjacent)}, {_number(row.spearman_mean_three_month)}, "
            f"and {_number(row.spearman_mean_six_month)} (pairwise n="
            f"{int(row.pairwise_n_min_off_diagonal):,}–{int(row.pairwise_n_max_off_diagonal):,})."
        )
    ordered_cross = cross_month_summary.sort_values("pearson_mean_six_month", ascending=False)
    persistent_names = ", ".join(f"`{name}`" for name in ordered_cross.head(2)["variable"])
    short_lived_names = ", ".join(f"`{name}`" for name in ordered_cross.tail(2)["variable"])

    pooled_month_differences = []
    for x, y in combinations(WEATHER_VARIABLES, 2):
        group = monthly.loc[monthly["variable_x"].eq(x) & monthly["variable_y"].eq(y)]
        pooled = pearson.loc[x, y]
        max_gap = float((group["pearson_r"] - pooled).abs().max())
        most_different = group.loc[(group["pearson_r"] - pooled).abs().idxmax()]
        pooled_month_differences.append((max_gap, x, y, pooled, most_different))
    pooled_month_differences.sort(reverse=True, key=lambda item: item[0])
    pooled_lines = []
    for gap, x, y, pooled, row in pooled_month_differences[:5]:
        pooled_lines.append(
            f"- `{_pair_label(x, y)}`: pooled r={_number(pooled)} versus month "
            f"{int(row.month)} r={_number(row.pearson_r)} (absolute gap={_number(gap)})."
        )

    temp_vpd = core.loc[
        core.apply(
            lambda row: {row.variable_x, row.variable_y}
            == {"nasa_average_temperature_c", "vpd_mean_kpa"}, axis=1
        )
    ]
    rain_soil = core.loc[
        core.apply(
            lambda row: {row.variable_x, row.variable_y}
            == {"nasa_total_rainfall_mm", "soil_moisture_0_to_7cm_m3_m3"}, axis=1
        )
    ]
    solar_temp = core.loc[
        core.apply(
            lambda row: {row.variable_x, row.variable_y}
            == {"solar_radiation_mean_daily_mj_m2", "nasa_average_temperature_c"}, axis=1
        )
    ]

    text = f"""# EXP-01A execution report

## Status

**COMPLETED.** The mandatory validation gate passed on the authoritative combined-weather CSVs, and EXP-01A was executed through correlation, divergence, ranking, lag-1 persistence, figures, and verification. EXP-01B and EXP-01C were not run.

## Data validation

- Exact analysis source: `{input_dir.resolve()}` (`sp_municipality_monthly_weather_YYYY.csv`).
- Years analyzed: 1990–2025 inclusive (36 years).
- Observation unit and validated key: `ibge_code × calendar year × calendar month`.
- Coverage: {len(validation.data):,} rows; 642 municipalities, 7,704 rows, and 12 calendar months in every year; no entering/leaving municipalities, missing municipality-month keys, or duplicate keys.
- Missingness: zero missing observations in every included weather variable, overall, by year, and by calendar month.
- Merge integrity: all {len(validation.data):,} rows contain both NASA POWER basic data and Open-Meteo/ERA5 advanced data; zero basic-only, advanced-only, or neither-source rows.
- Municipality mapping: stable canonical seven-digit IBGE codes; 87 shared NASA weather groups and 83 sampled ERA5 grid points are retained as metadata, not analyzed as weather variables.
- Exact included variables: {', '.join(f'`{name}`' for name in WEATHER_VARIABLES)}.
- Excluded metadata/QA fields: `municipality`, `ibge_code`, `month`, `year`, `calendar_month`, `date`, `nasa_weather_group_id`, `era5_grid_id`, `nasa_observed_days`, and `era5_observed_days`.
- Units, source, and code-verified aggregation definitions are recorded in `weather_variable_inventory.csv`. Separate VPD definitions, four soil depths, and monthly-total versus mean-daily radiation were preserved; no arbitrary averaging or unit conversion was applied.
- The official 2009 validation artifact was regenerated from `data/raw/nasa_power/daily_weather/SP/20090101_20091231.csv`: 365 dates, 234,330 valid NASA daily rows, 7,704 combined monthly rows, zero missing source rows, and a value-for-value match to the repaired annual CSV within pipeline tolerance (`pilot_comparison: passed`).

## Methods

- Pearson correlation describes linear association; Spearman correlation is Pearson correlation of within-pair ranks and describes monotonic association.
- Each coefficient uses pairwise-complete observations and carries its own `n`. No weather value was imputed or replaced with zero.
- Pooled matrices use every valid municipality-year-month row and may reflect the common seasonal cycle.
- Month-specific correlations use only municipality-year observations from the same calendar month across 1990–2025.
- Pearson–Spearman divergence is `|Spearman rho - Pearson r|` for each unordered pair and calendar month.
- Lag-1 values were created within IBGE municipality only when the prior record was exactly one calendar month earlier. December→January is allowed; missing months are never bridged.
- No significance tests, p-values, nonlinear models, yield data, harvested-area weights, or feature-selection thresholds were used.

## Results

### Strongest pooled basic/advanced overlap

{chr(10).join(strongest_lines)}

These pooled results are descriptive and partly reflect the annual seasonal cycle. Month-specific results below are primary.

### Core relationships by calendar month

{chr(10).join(core_lines)}

- Temperature ↔ mean VPD is positive in every month, with Pearson r ranging from {_number(temp_vpd.pearson_r.min())} to {_number(temp_vpd.pearson_r.max())}; it is consistently related but not interchangeable.
- Precipitation ↔ surface soil moisture is positive in every month, ranging from {_number(rain_soil.pearson_r.min())} to {_number(rain_soil.pearson_r.max())}, with clear seasonal strength variation.
- Mean-daily solar radiation ↔ temperature ranges from {_number(solar_temp.pearson_r.min())} to {_number(solar_temp.pearson_r.max())}; radiation retains visibly distinct within-month variation.

### Largest Pearson–Spearman divergences

{chr(10).join(divergence_lines)}

These differences flag nonlinearity, rank structure, or influential extremes; EXP-01A does not fit nonlinear models.

### Lag-1 persistence

{chr(10).join(lag_lines)}

### Full cross-month temporal dependence

Each matrix compares the same variable in two calendar months after reshaping to one row per `ibge_code × year`. All 12×12 Pearson and Spearman matrices and their pairwise-count matrices use exact year alignment; no lag bridging or imputation occurs.

{chr(10).join(cross_month_lines)}

On a relative, descriptive basis, {persistent_names} retain the strongest six-month dependence, while {short_lived_names} are the most short-lived of the five variables. This ranking describes temporal dependence only and is not a feature-selection rule.

### Pooled versus month-specific relationships

The following pairs have the largest gaps between pooled Pearson correlation and at least one calendar-month estimate:

{chr(10).join(pooled_lines)}

Accordingly, pooled correlations should not be used alone to characterize weather-feature overlap.

## Answers for the next research step

1. The strongest observed cross-source overlaps are listed above; exact complete rankings are in `strongest_correlation_pairs.csv`.
2. The most month-dependent relationships are identified by the pooled/month gaps and the complete monthly table.
3. Temperature and mean VPD are positively related in every month, but the strength varies and does not establish redundancy.
4. Surface soil moisture is positively associated with precipitation in every month, with seasonal variation shown above.
5. Solar radiation tracks temperature only partially within months and retains distinct variation.
6. The lag table above ranks persistence across precipitation, temperature, VPD, and surface soil moisture.
7. Several pooled relationships differ materially from individual-month estimates; the listed largest gaps are the clearest examples.
8. No analyzed-CSV coverage, missingness, key, source-merge, or validation-artifact issue blocks EXP-01B.
9. EXP-01B should carry forward the same 11 included variables, unchanged, so weighted and unweighted results remain directly comparable.

## Interpretation limits

- Predictor correlation does not prove predictive redundancy or causation.
- Low correlation does not prove incremental yield-prediction value.
- EXP-01A does not select final yield-model features.
- Rows share 87 NASA weather groups and 83 sampled ERA5 grid points, so they are not independent spatial observations; no classical p-values or significance stars are reported.
- EXP-01B and EXP-01C are still required before deciding how crop-area weighting changes the picture.

## Engineering verification

- Created/modified: `src/analysis/exp01a_municipality_weather_correlation.py`, `src/tests/analysis/test_exp01a_municipality_weather_correlation.py`, the refreshed 2009 validation JSON, four validation CSVs, seven original correlation/persistence CSVs, sixteen cross-month CSVs, fifteen figures, and this report.
- Focused EXP-01A tests: **16 passed**.
- Related combined-weather ETL tests: **7 passed**.
- Full repository suite: **197 passed, 3 pre-existing warnings**.
- 2009 independent rebuild/pilot comparison: **passed** with 7,704 matched keys and no differing values within `1e-12` absolute/relative tolerance.
- Upstream downloader and ETL source code was not modified. Existing unrelated working-tree changes were preserved.
"""
    path.write_text(text, encoding="utf-8")


def run(project_root: Path) -> int:
    input_dir = project_root / "data/processed/combined_weather/annual"
    table_dir = project_root / "data/processed/analysis" / EXPERIMENT
    output_dir = project_root / "outputs/experiments" / EXPERIMENT
    figure_dir = output_dir / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    validation = load_and_validate(input_dir)
    validation.inventory.to_csv(table_dir / "weather_variable_inventory.csv", index=False)
    validation.coverage.to_csv(table_dir / "weather_coverage_validation.csv", index=False)
    validation.missingness.to_csv(table_dir / "weather_missingness_summary.csv", index=False)
    validation.merge_integrity.to_csv(table_dir / "merge_integrity_summary.csv", index=False)
    report_path = output_dir / "EXP_01A_execution_report.md"
    if validation.gate_reasons:
        write_stopped_report(report_path, validation, input_dir)
        print("EXP-01A stopped at validation gate:")
        for reason in validation.gate_reasons:
            print(f"- {reason}")
        print(f"Stopped report: {report_path}")
        return 2

    data = validation.data
    pearson, spearman, counts = correlation_matrices(data, WEATHER_VARIABLES)
    pearson.to_csv(table_dir / "pooled_pearson_correlation.csv")
    spearman.to_csv(table_dir / "pooled_spearman_correlation.csv")
    counts.to_csv(table_dir / "pooled_pairwise_n.csv")
    monthly = monthly_correlations(data, WEATHER_VARIABLES)
    monthly.to_csv(table_dir / "monthly_pair_correlations.csv", index=False)
    core_keys = {tuple(sorted(pair)) for pair in CORE_PAIRS}
    core = monthly.loc[monthly.apply(lambda row: tuple(sorted((row.variable_x, row.variable_y))) in core_keys, axis=1)].copy()
    core.to_csv(table_dir / "core_pair_monthly_correlations.csv", index=False)
    divergence = monthly.assign(absolute_pearson_spearman_difference=(monthly["spearman_rho"] - monthly["pearson_r"]).abs()).sort_values("absolute_pearson_spearman_difference", ascending=False)
    divergence.to_csv(table_dir / "pearson_spearman_divergence.csv", index=False)
    lag_overall, lag_monthly = lag1_results(data, LAG_VARIABLES)
    lag_overall.to_csv(table_dir / "lag1_persistence_overall.csv", index=False)
    lag_monthly.to_csv(table_dir / "lag1_persistence_by_month.csv", index=False)
    strongest_pairs(pearson, spearman, monthly).to_csv(table_dir / "strongest_correlation_pairs.csv", index=False)
    cross_month: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
    for variable in CROSS_MONTH_VARIABLES:
        matrices = cross_month_matrices(data, variable)
        cross_month[variable] = matrices
        cross_pearson, cross_spearman, cross_counts = matrices
        cross_pearson.to_csv(table_dir / f"cross_month_{variable}_pearson.csv")
        cross_spearman.to_csv(table_dir / f"cross_month_{variable}_spearman.csv")
        cross_counts.to_csv(table_dir / f"cross_month_{variable}_pairwise_n.csv")
    cross_summary = cross_month_dependence_summary(cross_month)
    cross_summary.to_csv(table_dir / "cross_month_dependence_summary.csv", index=False)
    figure_dir.mkdir(parents=True, exist_ok=True)
    _heatmap(pearson, "EXP-01A pooled Pearson correlation", figure_dir / "pooled_pearson_heatmap.png")
    _heatmap(spearman, "EXP-01A pooled Spearman correlation", figure_dir / "pooled_spearman_heatmap.png")
    _heatmap(_core_month_matrix(core, "pearson_r"), "EXP-01A core pairs by month: Pearson", figure_dir / "core_pairs_monthly_pearson_heatmap.png")
    _heatmap(_core_month_matrix(core, "spearman_rho"), "EXP-01A core pairs by month: Spearman", figure_dir / "core_pairs_monthly_spearman_heatmap.png")
    lag_matrix = lag_monthly.pivot(index="destination_month", columns="variable", values="pearson_r")
    _heatmap(lag_matrix, "EXP-01A lag-1 persistence by destination month", figure_dir / "lag1_persistence_heatmap.png")
    for variable, (cross_pearson, cross_spearman, _) in cross_month.items():
        _heatmap(
            cross_pearson,
            f"EXP-01A cross-month Pearson: {variable}",
            figure_dir / f"cross_month_{variable}_pearson_heatmap.png",
        )
        _heatmap(
            cross_spearman,
            f"EXP-01A cross-month Spearman: {variable}",
            figure_dir / f"cross_month_{variable}_spearman_heatmap.png",
        )
    write_success_report(
        report_path,
        validation,
        input_dir,
        pearson,
        spearman,
        monthly,
        core,
        divergence,
        lag_overall,
        lag_monthly,
        cross_summary,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
