"""Build a bounded SoilGrids 2.0 layer for the EXP-03 ERA5 grid universe.

This module downloads only mean SoilGrids predictions for the São Paulo
bounding rectangle needed by the 76 usable EXP-03 grids.  Native SoilGrids
depth intervals are preserved.  No yield, regime, or predictive analysis is
performed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import requests
from PIL import Image


DEPTHS = (
    (0, 5, "0-5cm"),
    (5, 15, "5-15cm"),
    (15, 30, "15-30cm"),
    (30, 60, "30-60cm"),
    (60, 100, "60-100cm"),
    (100, 200, "100-200cm"),
)
PIXEL_SIZE_DEGREES = 0.0025
NODATA = -32768
WCS_VERSION = "1.0.0"
SOILGRIDS_PRODUCT = "SoilGrids 2.0"
SOILGRIDS_LICENSE = "CC BY 4.0"
SOURCE_NATIVE_CRS = "EPSG:152160 (Interrupted Goode Homolosine)"
DOWNLOAD_CRS = "EPSG:4326"
SOURCE_NATIVE_RESOLUTION = "250 m"


@dataclass(frozen=True)
class SoilVariable:
    service_name: str
    definition: str
    raw_unit: str
    unit: str
    scale_divisor: float
    plausible_min: float
    plausible_max: float


VARIABLES = {
    "clay": SoilVariable(
        "clay", "Clay content", "g kg-1", "percent_mass", 10.0, 0.0, 100.0,
    ),
    "sand": SoilVariable(
        "sand", "Sand content", "g kg-1", "percent_mass", 10.0, 0.0, 100.0,
    ),
    "silt": SoilVariable(
        "silt", "Silt content", "g kg-1", "percent_mass", 10.0, 0.0, 100.0,
    ),
    "bdod": SoilVariable(
        "bdod", "Bulk density of the fine earth fraction", "cg cm-3",
        "kg dm-3", 100.0, 0.0, 3.0,
    ),
    "cfvo": SoilVariable(
        "cfvo", "Volumetric fraction of coarse fragments", "cm3 dm-3",
        "percent_volume", 10.0, 0.0, 100.0,
    ),
    "wv0033": SoilVariable(
        "wv0033", "Volumetric water content at 33 kPa", "10^-3 cm3 cm-3",
        "percent_volume", 10.0, 0.0, 100.0,
    ),
    "wv1500": SoilVariable(
        "wv1500", "Volumetric water content at 1500 kPa", "10^-3 cm3 cm-3",
        "percent_volume", 10.0, 0.0, 100.0,
    ),
}
DERIVED_AWC = "awc_33_minus_1500"


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_exp03_grids(root: Path) -> pd.DataFrame:
    """Load the exact usable March grid universe and canonical coordinates."""

    correlations = pd.read_csv(
        root / "outputs/research/exp_03/yield_stratified_monthly_weather/"
        "checkpoint2/grid_specific_spearman_correlations.csv"
    )
    usable = correlations.loc[
        correlations.relative_month.eq("m_-1")
        & correlations.weather_variable.eq("soil_moisture_0_to_7cm_m3_m3")
        & correlations.usable.astype(bool),
        ["grid_id"],
    ].drop_duplicates()
    mapping = pd.read_csv(
        root / "outputs/research/exp_02/exp_02b/eligible_municipality_grid_mapping.csv"
    )
    coordinates = mapping.groupby("grid_id", as_index=False).agg(
        grid_lat=("grid_latitude", "first"),
        grid_lon=("grid_longitude", "first"),
    )
    grids = usable.merge(coordinates, on="grid_id", how="left", validate="one_to_one")
    if len(grids) != 76 or grids.grid_id.nunique() != 76:
        raise ValueError(f"Expected 76 usable EXP-03 grids, found {len(grids)}")
    if grids[["grid_lat", "grid_lon"]].isna().any().any():
        raise ValueError("Canonical grid coordinates are incomplete")
    return grids.sort_values("grid_id").reset_index(drop=True)


def bounding_box(grids: pd.DataFrame) -> tuple[float, float, float, float]:
    """Return west, south, east, north bounds for complete 0.5-degree cells."""

    return (
        float(grids.grid_lon.min() - 0.25),
        float(grids.grid_lat.min() - 0.25),
        float(grids.grid_lon.max() + 0.25),
        float(grids.grid_lat.max() + 0.25),
    )


def raster_shape(bounds: tuple[float, float, float, float]) -> tuple[int, int]:
    west, south, east, north = bounds
    width = int(round((east - west) / PIXEL_SIZE_DEGREES))
    height = int(round((north - south) / PIXEL_SIZE_DEGREES))
    if not math.isclose(width * PIXEL_SIZE_DEGREES, east - west):
        raise ValueError("Longitude bounds do not align to requested pixel size")
    if not math.isclose(height * PIXEL_SIZE_DEGREES, north - south):
        raise ValueError("Latitude bounds do not align to requested pixel size")
    return width, height


def coverage_id(variable: str, depth_label: str) -> str:
    return f"{VARIABLES[variable].service_name}_{depth_label}_mean"


def wcs_url(
    variable: str,
    depth_label: str,
    bounds: tuple[float, float, float, float],
) -> str:
    west, south, east, north = bounds
    width, height = raster_shape(bounds)
    params = {
        "map": f"/map/{VARIABLES[variable].service_name}.map",
        "SERVICE": "WCS",
        "VERSION": WCS_VERSION,
        "REQUEST": "GetCoverage",
        "COVERAGE": coverage_id(variable, depth_label),
        "CRS": DOWNLOAD_CRS,
        "BBOX": f"{west},{south},{east},{north}",
        "WIDTH": width,
        "HEIGHT": height,
        "FORMAT": "GEOTIFF_INT16",
    }
    return "https://maps.isric.org/mapserv?" + urlencode(params)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_tiff(content: bytes, expected_shape: tuple[int, int]) -> None:
    with Image.open(BytesIO(content)) as image:
        if image.size != expected_shape:
            raise ValueError(f"Unexpected raster size {image.size}; expected {expected_shape}")
        array = np.asarray(image)
        if array.ndim != 2:
            raise ValueError("Expected a single-band SoilGrids raster")
        geokeys = image.tag_v2.get(34735)
        if not geokeys or 4326 not in geokeys:
            raise ValueError("Downloaded raster is not tagged EPSG:4326")


def download_one(
    variable: str,
    depth_label: str,
    bounds: tuple[float, float, float, float],
    target: Path,
    refresh: bool = False,
    attempts: int = 3,
) -> dict[str, object]:
    """Download one bounded mean-prediction GeoTIFF, with cache validation."""

    url = wcs_url(variable, depth_label, bounds)
    expected_shape = raster_shape(bounds)
    if target.exists() and not refresh:
        content = target.read_bytes()
        validate_tiff(content, expected_shape)
        return {
            "soil_variable": variable,
            "source_depth_label": depth_label,
            "coverage_id": coverage_id(variable, depth_label),
            "url": url,
            "cache_path": str(target),
            "bytes": len(content),
            "sha256": sha256_bytes(content),
            "retrieved_at_utc": datetime.fromtimestamp(
                target.stat().st_mtime, timezone.utc
            ).isoformat(),
            "cache_reused": True,
        }
    headers = {"User-Agent": "Operation-Sugar-SoilGrids-Step4C1/1.0"}
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=300, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "tiff" not in content_type:
                preview = response.text[:300]
                raise ValueError(f"WCS returned {content_type}: {preview}")
            validate_tiff(response.content, expected_shape)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)
            return {
                "soil_variable": variable,
                "source_depth_label": depth_label,
                "coverage_id": coverage_id(variable, depth_label),
                "url": url,
                "cache_path": str(target),
                "bytes": len(response.content),
                "sha256": sha256_bytes(response.content),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "cache_reused": False,
            }
        except (requests.RequestException, OSError, ValueError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(3 * attempt)
    raise RuntimeError(f"Failed to download {variable} {depth_label}") from last_error


def download_all(
    raw_dir: Path,
    bounds: tuple[float, float, float, float],
    refresh: bool = False,
    max_workers: int = 2,
) -> list[dict[str, object]]:
    tasks = []
    for variable in VARIABLES:
        for _, _, depth_label in DEPTHS:
            target = raw_dir / variable / f"{coverage_id(variable, depth_label)}.tif"
            tasks.append((variable, depth_label, target))
    records: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(download_one, variable, depth, bounds, target, refresh):
            (variable, depth)
            for variable, depth, target in tasks
        }
        for future in as_completed(futures):
            records.append(future.result())
    return sorted(records, key=lambda row: (row["soil_variable"], row["source_depth_label"]))


def pixel_row_area_weights(n_rows: int, north: float) -> np.ndarray:
    """Spherical area weights for equal-longitude EPSG:4326 pixels."""

    top = north - np.arange(n_rows) * PIXEL_SIZE_DEGREES
    bottom = top - PIXEL_SIZE_DEGREES
    return np.sin(np.deg2rad(top)) - np.sin(np.deg2rad(bottom))


def aggregate_raster(
    array: np.ndarray,
    grids: pd.DataFrame,
    bounds: tuple[float, float, float, float],
) -> pd.DataFrame:
    """Area-weight raster samples inside each canonical 0.5-degree grid cell."""

    west, _, _, north = bounds
    rows = []
    row_weights = pixel_row_area_weights(array.shape[0], north)
    for grid in grids.itertuples(index=False):
        left = grid.grid_lon - 0.25
        right = grid.grid_lon + 0.25
        top = grid.grid_lat + 0.25
        bottom = grid.grid_lat - 0.25
        col0 = int(round((left - west) / PIXEL_SIZE_DEGREES))
        col1 = int(round((right - west) / PIXEL_SIZE_DEGREES))
        row0 = int(round((north - top) / PIXEL_SIZE_DEGREES))
        row1 = int(round((north - bottom) / PIXEL_SIZE_DEGREES))
        block = array[row0:row1, col0:col1].astype(float)
        valid = block != NODATA
        weights = np.repeat(row_weights[row0:row1, None], block.shape[1], axis=1)
        valid_weight = float(weights[valid].sum())
        total_weight = float(weights.sum())
        raw_mean = float(np.average(block[valid], weights=weights[valid])) if valid.any() else np.nan
        rows.append({
            "era5_grid_id": grid.grid_id,
            "grid_lat": grid.grid_lat,
            "grid_lon": grid.grid_lon,
            "raw_area_weighted_mean": raw_mean,
            "n_source_pixels": int(valid.sum()),
            "n_expected_pixels": int(block.size),
            "coverage_fraction": valid_weight / total_weight if total_weight else np.nan,
        })
    return pd.DataFrame(rows)


def aggregate_sources(
    grids: pd.DataFrame,
    raw_dir: Path,
    bounds: tuple[float, float, float, float],
) -> pd.DataFrame:
    rows = []
    for variable, metadata in VARIABLES.items():
        for depth_top, depth_bottom, depth_label in DEPTHS:
            path = raw_dir / variable / f"{coverage_id(variable, depth_label)}.tif"
            with Image.open(path) as image:
                array = np.asarray(image)
            aggregated = aggregate_raster(array, grids, bounds)
            aggregated["soil_variable"] = variable
            aggregated["depth_top_cm"] = depth_top
            aggregated["depth_bottom_cm"] = depth_bottom
            aggregated["source_depth_label"] = depth_label
            aggregated["value"] = scale_raw_values(
                variable, aggregated.raw_area_weighted_mean
            )
            aggregated["unit"] = metadata.unit
            aggregated["source_raw_unit"] = metadata.raw_unit
            aggregated["scale_divisor"] = metadata.scale_divisor
            aggregated["source"] = SOILGRIDS_PRODUCT
            aggregated["source_coverage_id"] = coverage_id(variable, depth_label)
            aggregated["aggregation_method"] = "spherical_area_weighted_mean_epsg4326"
            aggregated["is_derived"] = False
            aggregated["derived_from"] = ""
            rows.append(aggregated)
    return pd.concat(rows, ignore_index=True)


def scale_raw_values(variable: str, values: pd.Series | np.ndarray | float):
    """Apply the documented SoilGrids integer scale divisor."""

    return values / VARIABLES[variable].scale_divisor


def add_awc(source: pd.DataFrame) -> pd.DataFrame:
    """Add theta33 minus theta1500 in volumetric percentage points."""

    keys = [
        "era5_grid_id", "grid_lat", "grid_lon", "depth_top_cm", "depth_bottom_cm",
        "source_depth_label",
    ]
    water = source.loc[source.soil_variable.isin(["wv0033", "wv1500"])].pivot(
        index=keys, columns="soil_variable", values="value"
    ).reset_index()
    water["value"] = water.wv0033 - water.wv1500
    coverage = source.loc[source.soil_variable.isin(["wv0033", "wv1500"])].groupby(
        keys, as_index=False
    ).agg(
        n_source_pixels=("n_source_pixels", "min"),
        n_expected_pixels=("n_expected_pixels", "max"),
        coverage_fraction=("coverage_fraction", "min"),
    )
    awc = water.merge(coverage, on=keys, validate="one_to_one")
    awc["raw_area_weighted_mean"] = np.nan
    awc["soil_variable"] = DERIVED_AWC
    awc["unit"] = "percentage_points_volumetric"
    awc["source_raw_unit"] = "derived from scaled percent_volume"
    awc["scale_divisor"] = np.nan
    awc["source"] = SOILGRIDS_PRODUCT
    awc["source_coverage_id"] = "derived"
    awc["aggregation_method"] = "difference_of_area_weighted_means"
    awc["is_derived"] = True
    awc["derived_from"] = "wv0033;wv1500"
    return pd.concat([source, awc[source.columns]], ignore_index=True)


def validate_output(table: pd.DataFrame, grids: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run required coverage, range, texture, and water-retention checks."""

    expected_variables = set(VARIABLES) | {DERIVED_AWC}
    expected_depths = {label for _, _, label in DEPTHS}
    key = ["era5_grid_id", "soil_variable", "source_depth_label"]
    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    record("expected_grid_count", table.era5_grid_id.nunique() == len(grids),
           f"{table.era5_grid_id.nunique()} of {len(grids)}")
    record("expected_variable_set", set(table.soil_variable) == expected_variables,
           ";".join(sorted(set(table.soil_variable))))
    record("expected_depth_set", set(table.source_depth_label) == expected_depths,
           ";".join(sorted(set(table.source_depth_label))))
    duplicate_count = int(table.duplicated(key).sum())
    record("unique_grid_variable_depth", duplicate_count == 0, f"duplicates={duplicate_count}")
    invalid_grids = set(table.era5_grid_id) - set(grids.grid_id)
    record("canonical_grid_ids", not invalid_grids, f"invalid={sorted(invalid_grids)}")
    missing_values = int(table.value.isna().sum())
    record("no_missing_values", missing_values == 0, f"missing={missing_values}")

    for variable, metadata in VARIABLES.items():
        values = table.loc[table.soil_variable.eq(variable), "value"].dropna()
        valid = values.between(metadata.plausible_min, metadata.plausible_max).all()
        record(
            f"range_{variable}", bool(valid),
            f"min={values.min():.6f};max={values.max():.6f};expected="
            f"[{metadata.plausible_min},{metadata.plausible_max}]",
        )

    texture = table.loc[table.soil_variable.isin(["clay", "sand", "silt"])].pivot(
        index=["era5_grid_id", "source_depth_label"],
        columns="soil_variable", values="value",
    )
    texture_sum = texture[["clay", "sand", "silt"]].sum(axis=1)
    texture_error = (texture_sum - 100.0).abs()
    record(
        "texture_closure_within_0.2_percentage_points",
        bool(texture_error.le(0.2).all()),
        f"max_abs_error={texture_error.max():.6f};mean_abs_error={texture_error.mean():.6f}",
    )

    water = table.loc[table.soil_variable.isin(["wv0033", "wv1500"])].pivot(
        index=["era5_grid_id", "source_depth_label"],
        columns="soil_variable", values="value",
    )
    violations = int((water.wv0033 < water.wv1500).sum())
    record("theta33_ge_theta1500", violations == 0, f"violations={violations}")
    awc = table.loc[table.soil_variable.eq(DERIVED_AWC), "value"].dropna()
    negative_awc = int(awc.lt(0).sum())
    record(
        "nonnegative_awc", negative_awc == 0,
        f"negative={negative_awc};min={awc.min():.6f};max={awc.max():.6f}",
    )
    coverage = table.loc[~table.is_derived].coverage_fraction
    record(
        "positive_source_coverage", bool(coverage.gt(0).all()),
        f"min={coverage.min():.6f};median={coverage.median():.6f}",
    )

    missingness = table.groupby("soil_variable", as_index=False).agg(
        expected_combinations=("value", "size"),
        missing_combinations=("value", lambda values: int(values.isna().sum())),
        minimum_coverage_fraction=("coverage_fraction", "min"),
        mean_coverage_fraction=("coverage_fraction", "mean"),
        minimum_value=("value", "min"),
        maximum_value=("value", "max"),
    )
    missingness["percent_missing"] = (
        100 * missingness.missing_combinations / missingness.expected_combinations
    )
    return pd.DataFrame(checks), missingness


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def source_metadata(bounds: tuple[float, float, float, float]) -> dict[str, object]:
    width, height = raster_shape(bounds)
    return {
        "aggregation_run_date": date.today().isoformat(),
        "product": SOILGRIDS_PRODUCT,
        "prediction_statistic": "mean",
        "access_method": "Official ISRIC SoilGrids WCS bounded GetCoverage",
        "service_version": WCS_VERSION,
        "service_base": "https://maps.isric.org/mapserv",
        "license": SOILGRIDS_LICENSE,
        "license_url": "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html",
        "product_documentation": "https://docs.isric.org/globaldata/soilgrids/",
        "layer_documentation": "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html",
        "source_native_crs": SOURCE_NATIVE_CRS,
        "source_native_resolution": SOURCE_NATIVE_RESOLUTION,
        "download_crs": DOWNLOAD_CRS,
        "download_pixel_size_degrees": PIXEL_SIZE_DEGREES,
        "download_width": width,
        "download_height": height,
        "request_bbox_west_south_east_north": bounds,
        "nodata": NODATA,
        "depths": [
            {"top_cm": top, "bottom_cm": bottom, "label": label}
            for top, bottom, label in DEPTHS
        ],
        "variables": {
            name: {
                "official_service_name": item.service_name,
                "definition": item.definition,
                "source_raw_unit": item.raw_unit,
                "output_unit": item.unit,
                "scale_divisor": item.scale_divisor,
                "validation_range_output_units": [
                    item.plausible_min, item.plausible_max,
                ],
            }
            for name, item in VARIABLES.items()
        },
        "derived_variable": {
            "name": DERIVED_AWC,
            "formula": "scaled wv0033 - scaled wv1500",
            "unit": "percentage_points_volumetric",
            "interpretation": "difference in modeled volumetric water retention; not a measured agronomic capacity",
        },
        "aggregation": {
            "method": "spherical area-weighted mean of EPSG:4326 WCS pixels",
            "target_geometry": "existing ERA5 0.5-degree cells centered on canonical EXP-03 grid coordinates",
            "production_weights_used": False,
        },
        "limitations": [
            "SoilGrids values are modeled global predictions, not observations at every pixel.",
            "WCS reprojection to EPSG:4326 uses approximately 250 m samples over the São Paulo extent.",
            "SoilGrids ends at 200 cm; no values are fabricated for ERA5's 200-255 cm portion.",
            "Only central mean predictions were acquired; uncertainty quantiles remain available but were not downloaded.",
        ],
    }


def execution_report(
    metadata: dict[str, object], table: pd.DataFrame, checks: pd.DataFrame,
    manifest: list[dict[str, object]],
) -> str:
    missing = int(table.value.isna().sum())
    failed = checks.loc[~checks.passed.astype(bool)]
    return f"""# EXP-03 Step 4C-1 — SoilGrids acquisition execution report

## Scope

Built a bounded, depth-resolved SoilGrids 2.0 explanatory layer for all 76 usable EXP-03 ERA5 grids. No regime comparison, feature selection, regression, classification, or predictive modeling was performed.

## Acquisition

- Route: official ISRIC SoilGrids WCS bounded GetCoverage.
- Retrieval date: {metadata['retrieval_date']}.
- Bounding box (west, south, east, north): {metadata['request_bbox_west_south_east_north']}.
- Download grid: EPSG:4326 at {PIXEL_SIZE_DEGREES} degrees; source native product is 250 m Interrupted Goode Homolosine.
- Central estimate: mean prediction only. SoilGrids uncertainty quantiles were inspected as available service layers but not downloaded.
- Cached GeoTIFFs: {len(manifest)}.
- Licence: {SOILGRIDS_LICENSE}, attribution required.

## Output

- ERA5 grids: {table.era5_grid_id.nunique()}.
- Soil variables including derived AWC: {table.soil_variable.nunique()}.
- Native depth intervals: {table.source_depth_label.nunique()}.
- Rows: {len(table)}.
- Missing values: {missing}.
- Aggregation: spherical area-weighted mean of WCS pixels within each canonical 0.5-degree ERA5 cell.
- AWC terminology: modeled volumetric water-retention difference, `wv0033 - wv1500`, in volumetric percentage points.

## Validation

- Checks passed: {int(checks.passed.astype(bool).sum())}/{len(checks)}.
- Failed checks: {len(failed)}.
- Texture fractions were checked for approximate 100% closure after documented scaling.
- `theta33 >= theta1500` and nonnegative derived AWC were checked for every grid-depth row.
- No missing value was imputed and no unusual value was clipped.

## Boundary

The table is ready for review before EXP-03 Step 4C-2. It does not establish that soil properties explain or cause the response regimes.
"""


def build(root: Path, refresh: bool = False, max_workers: int = 2) -> None:
    grids = load_exp03_grids(root)
    bounds = bounding_box(grids)
    raw_dir = root / "data/raw/soil/soilgrids_2_0/sp_exp03_era5_extent"
    processed_dir = root / "data/processed/soil"
    validation_dir = root / "outputs/research/exp_03/soilgrids_step4c1"

    manifest = download_all(raw_dir, bounds, refresh=refresh, max_workers=max_workers)
    metadata = source_metadata(bounds)
    retrieved = [
        datetime.fromisoformat(str(item["retrieved_at_utc"])).date().isoformat()
        for item in manifest if item.get("retrieved_at_utc")
    ]
    metadata["retrieval_date"] = min(retrieved) if retrieved else date.today().isoformat()
    metadata["downloads"] = manifest
    write_json(raw_dir / "manifest.json", metadata)

    source = aggregate_sources(grids, raw_dir, bounds)
    table = add_awc(source).sort_values(
        ["era5_grid_id", "soil_variable", "depth_top_cm"]
    ).reset_index(drop=True)
    checks, missingness = validate_output(table, grids)
    failed = checks.loc[~checks.passed.astype(bool)]
    if not failed.empty:
        raise ValueError("SoilGrids validation failed:\n" + failed.to_string(index=False))

    processed_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(processed_dir / "soilgrids_era5_grid_properties.csv", index=False)
    checks.to_csv(validation_dir / "soilgrids_validation_summary.csv", index=False)
    missingness.to_csv(validation_dir / "soilgrids_missingness.csv", index=False)
    write_json(validation_dir / "soilgrids_source_metadata.json", metadata)
    (validation_dir / "EXP_03_step4c1_execution_report.md").write_text(
        execution_report(metadata, table, checks, manifest), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=project_root())
    parser.add_argument("--refresh", action="store_true", help="Replace validated cached GeoTIFFs")
    parser.add_argument("--max-workers", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(args.project_root.resolve(), refresh=args.refresh, max_workers=args.max_workers)


if __name__ == "__main__":
    main()
