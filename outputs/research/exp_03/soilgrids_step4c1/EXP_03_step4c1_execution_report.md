# EXP-03 Step 4C-1 — SoilGrids acquisition execution report

## Scope

Built a bounded, depth-resolved SoilGrids 2.0 explanatory layer for all 76 usable EXP-03 ERA5 grids. No regime comparison, feature selection, regression, classification, or predictive modeling was performed.

## Acquisition

- Route: official ISRIC SoilGrids WCS bounded GetCoverage.
- Retrieval date: 2026-10-05.
- Bounding box (west, south, east, north): (-53.25, -24.75, -44.75, -19.75).
- Download grid: EPSG:4326 at 0.0025 degrees; source native product is 250 m Interrupted Goode Homolosine.
- Central estimate: mean prediction only. SoilGrids uncertainty quantiles were inspected as available service layers but not downloaded.
- Cached GeoTIFFs: 42.
- Licence: CC BY 4.0, attribution required.

## Output

- ERA5 grids: 76.
- Soil variables including derived AWC: 8.
- Native depth intervals: 6.
- Rows: 3648.
- Missing values: 0.
- Aggregation: spherical area-weighted mean of WCS pixels within each canonical 0.5-degree ERA5 cell.
- AWC terminology: modeled volumetric water-retention difference, `wv0033 - wv1500`, in volumetric percentage points.

## Validation

- Checks passed: 17/17.
- Failed checks: 0.
- Texture fractions were checked for approximate 100% closure after documented scaling.
- `theta33 >= theta1500` and nonnegative derived AWC were checked for every grid-depth row.
- No missing value was imputed and no unusual value was clipped.

## Boundary

The table is ready for review before EXP-03 Step 4C-2. It does not establish that soil properties explain or cause the response regimes.
