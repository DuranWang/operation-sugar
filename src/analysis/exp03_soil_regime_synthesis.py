"""Reproduce the bounded EXP-03 SoilGrids regime synthesis.

Static soil properties remain explanatory context only.  This module creates
native-depth and transparent thickness-weighted descriptive summaries; it does
not construct predictive features or models.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analysis.exp03_march_soil_moisture_depth import (
    FROZEN_REGIME_COUNTS,
    markdown_table,
)


NATIVE_DEPTHS = [
    (0, 5, "0-5cm"),
    (5, 15, "5-15cm"),
    (15, 30, "15-30cm"),
    (30, 60, "30-60cm"),
    (60, 100, "60-100cm"),
    (100, 200, "100-200cm"),
]
SOIL_VARIABLES = [
    "clay", "sand", "silt", "bdod", "cfvo",
    "wv0033", "wv1500", "awc_33_minus_1500",
]
PRIMARY_REGIMES = ["depth_recovery", "persistent_negative"]
REFERENCE_REGIME = "positive_positive"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_soil_table(soil: pd.DataFrame) -> None:
    """Validate the bounded native-depth and AWC definitions."""

    required = {
        "era5_grid_id", "grid_lat", "soil_variable", "depth_top_cm",
        "depth_bottom_cm", "source_depth_label", "value", "coverage_fraction",
    }
    missing = required - set(soil.columns)
    if missing:
        raise ValueError(f"Missing SoilGrids columns: {sorted(missing)}")
    expected_depths = {label for _, _, label in NATIVE_DEPTHS}
    actual_depths = set(soil.source_depth_label)
    if actual_depths != expected_depths:
        raise ValueError(
            "Soil synthesis requires exactly the six native 0-200 cm depths; "
            f"found {sorted(actual_depths)}"
        )
    if soil.depth_bottom_cm.max() > 200 or soil.source_depth_label.astype(str).str.contains("255").any():
        raise ValueError("No 200-255 cm SoilGrids layer may be fabricated")
    if set(soil.soil_variable) != set(SOIL_VARIABLES):
        raise ValueError(f"Unexpected soil-variable set: {sorted(set(soil.soil_variable))}")
    if soil.duplicated(["era5_grid_id", "soil_variable", "source_depth_label"]).any():
        raise ValueError("Duplicate SoilGrids grid-variable-depth rows")
    if soil.value.isna().any():
        raise ValueError("Missing SoilGrids values are not imputed")

    keys = ["era5_grid_id", "source_depth_label"]
    water = soil.loc[soil.soil_variable.isin(["wv0033", "wv1500"])].pivot(
        index=keys, columns="soil_variable", values="value"
    )
    awc = soil.loc[soil.soil_variable.eq("awc_33_minus_1500")].set_index(keys).value
    expected_awc = water.wv0033 - water.wv1500
    if not np.allclose(awc.sort_index(), expected_awc.sort_index(), atol=1e-10):
        raise ValueError("AWC-like values do not equal theta33 minus theta1500")


def attach_regimes(soil: pd.DataFrame, regimes: pd.DataFrame) -> pd.DataFrame:
    required = {"grid_id", "regime"}
    missing = required - set(regimes.columns)
    if missing:
        raise ValueError(f"Missing regime columns: {sorted(missing)}")
    counts = regimes.drop_duplicates("grid_id").regime.value_counts().to_dict()
    if counts != FROZEN_REGIME_COUNTS:
        raise ValueError(f"Regime assignment disagrees with frozen state: {counts}")
    result = soil.merge(
        regimes.drop_duplicates("grid_id")[["grid_id", "regime"]],
        left_on="era5_grid_id", right_on="grid_id", validate="many_to_one",
    )
    if result.era5_grid_id.nunique() != 76:
        raise ValueError("Soil/regime merge must contain exactly 76 usable grids")
    return result.drop(columns="grid_id")


def thickness_weighted_profiles(soil_with_regime: pd.DataFrame) -> pd.DataFrame:
    """Build diagnostic 0-30 and 30-200 cm profiles from native intervals."""

    table = soil_with_regime.copy()
    table["thickness_cm"] = table.depth_bottom_cm - table.depth_top_cm
    expected = {
        label: bottom - top for top, bottom, label in NATIVE_DEPTHS
    }
    observed = table.groupby("source_depth_label").thickness_cm.unique().to_dict()
    if any(len(observed[label]) != 1 or observed[label][0] != thickness for label, thickness in expected.items()):
        raise ValueError("Native SoilGrids interval thickness is inconsistent")

    rows: list[dict[str, object]] = []
    for (grid_id, variable), group in table.groupby(["era5_grid_id", "soil_variable"]):
        upper = group.loc[group.depth_bottom_cm.le(30)]
        deep = group.loc[group.depth_top_cm.ge(30)]
        if set(upper.source_depth_label) != {"0-5cm", "5-15cm", "15-30cm"}:
            raise ValueError("Upper profile is not exactly 0-30 cm")
        if set(deep.source_depth_label) != {"30-60cm", "60-100cm", "100-200cm"}:
            raise ValueError("Deep profile is not exactly 30-200 cm")
        upper_value = float(np.average(upper.value, weights=upper.thickness_cm))
        deep_value = float(np.average(deep.value, weights=deep.thickness_cm))
        rows.append({
            "era5_grid_id": grid_id,
            "soil_variable": variable,
            "regime": group.regime.iloc[0],
            "grid_lat": float(group.grid_lat.iloc[0]),
            "coverage_fraction": float(group.coverage_fraction.min()),
            "upper_0_30": upper_value,
            "deep_30_200": deep_value,
            "deep_minus_upper": deep_value - upper_value,
        })
    return pd.DataFrame(rows)


def regime_profile_summary(profiles: pd.DataFrame) -> pd.DataFrame:
    long = profiles.melt(
        id_vars=["era5_grid_id", "soil_variable", "regime", "coverage_fraction"],
        value_vars=["upper_0_30", "deep_30_200", "deep_minus_upper"],
        var_name="profile_metric", value_name="value",
    )
    return long.groupby(["regime", "soil_variable", "profile_metric"], as_index=False).agg(
        n_grids=("era5_grid_id", "nunique"),
        mean=("value", "mean"),
        median=("value", "median"),
        q25=("value", lambda values: values.quantile(.25)),
        q75=("value", lambda values: values.quantile(.75)),
        minimum=("value", "min"),
        maximum=("value", "max"),
        median_coverage=("coverage_fraction", "median"),
        minimum_coverage=("coverage_fraction", "min"),
    )


def cliffs_delta(left: pd.Series, right: pd.Series) -> float:
    """Return Cliff's delta, positive when left tends to exceed right."""

    a = left.dropna().to_numpy(dtype=float)
    b = right.dropna().to_numpy(dtype=float)
    if not len(a) or not len(b):
        return np.nan
    return float(((a[:, None] > b).sum() - (a[:, None] < b).sum()) / (len(a) * len(b)))


def _contrast_rows(
    long: pd.DataFrame, scope: str, sample: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    keys = ["soil_variable", "depth_or_profile"]
    for (variable, depth), group in long.groupby(keys, sort=True):
        dr = group.loc[group.regime.eq("depth_recovery"), "value"]
        pn = group.loc[group.regime.eq("persistent_negative"), "value"]
        pp = group.loc[group.regime.eq(REFERENCE_REGIME), "value"]
        rows.append({
            "scope": scope,
            "sample": sample,
            "soil_variable": variable,
            "depth_or_profile": depth,
            "n_depth_recovery": len(dr),
            "n_persistent_negative": len(pn),
            "n_positive_positive": len(pp),
            "median_depth_recovery": dr.median(),
            "median_persistent_negative": pn.median(),
            "median_positive_positive": pp.median(),
            "median_difference_dr_minus_pn": dr.median() - pn.median(),
            "cliffs_delta_dr_vs_pn": cliffs_delta(dr, pn),
        })
    return rows


def soil_contrasts(
    soil_with_regime: pd.DataFrame, profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize native depths and profile contrasts for all and >=90% coverage."""

    native = soil_with_regime.rename(columns={
        "source_depth_label": "depth_or_profile",
    })[["era5_grid_id", "regime", "soil_variable", "depth_or_profile", "value", "coverage_fraction"]]
    profile_long = profiles.melt(
        id_vars=["era5_grid_id", "regime", "soil_variable", "coverage_fraction"],
        value_vars=["upper_0_30", "deep_30_200", "deep_minus_upper"],
        var_name="depth_or_profile", value_name="value",
    )
    rows = _contrast_rows(native, "native_depth", "all_valid")
    rows += _contrast_rows(profile_long, "profile", "all_valid")
    rows += _contrast_rows(
        profile_long.loc[profile_long.coverage_fraction.ge(.90)],
        "profile", "coverage_ge_0_90",
    )
    return pd.DataFrame(rows)


def latitude_associations(profiles: pd.DataFrame) -> pd.DataFrame:
    """Quantify simple soil-latitude association within the primary 32 grids."""

    primary = profiles.loc[profiles.regime.isin(PRIMARY_REGIMES)]
    rows = []
    for variable, group in primary.groupby("soil_variable", sort=True):
        for metric in ["upper_0_30", "deep_30_200", "deep_minus_upper"]:
            pair = group[[metric, "grid_lat"]].dropna()
            rho = spearmanr(pair[metric], pair.grid_lat).statistic
            rows.append({
                "soil_variable": variable,
                "profile_metric": metric,
                "n_grids": len(pair),
                "spearman_rho_with_latitude": float(rho),
            })
    return pd.DataFrame(rows)


def report_text(
    profile_summary: pd.DataFrame, contrasts: pd.DataFrame,
    latitude: pd.DataFrame, production_summary: pd.DataFrame | None,
) -> str:
    primary_profiles = contrasts.loc[
        contrasts.scope.eq("profile") & contrasts["sample"].eq("all_valid")
    ]
    key = primary_profiles.loc[primary_profiles.soil_variable.isin([
        "wv0033", "wv1500", "awc_33_minus_1500", "clay", "sand", "bdod", "cfvo",
    ])]
    production_section = (
        markdown_table(production_summary)
        if production_summary is not None else
        "_(Module A production-support summary was not available at report time.)_"
    )
    return f"""# EXP-03 bounded SoilGrids regime synthesis

## Scope

This report reproduces Step 4C-2 using the six native SoilGrids intervals through 200 cm. No 200-255 cm layer is created, and no static soil variable is added to a predictive model.

Primary comparison: 19 depth-recovery grids versus 13 persistent-negative grids. The 42 positive-positive grids provide reference context.

## Key profile contrasts

{markdown_table(key)}

## Latitude association

{markdown_table(latitude)}

## Existing production-support context

{production_section}

## Reproduced interpretation

- Depth-recovery grids tend to be sandier and less clay-rich, especially at depth.
- Their modeled absolute theta33 and theta1500 values are generally lower.
- Upper-profile `awc_33_minus_1500` levels are similar, while the deep-minus-upper decline is less negative in depth-recovery grids.
- Bulk-density and coarse-fragment contrasts are strong descriptively but co-occur with the broader geographic soil pattern.
- The strongest soil summaries materially track latitude, while production-support structure also differs by regime.

**Classification: suggestive / partial explanatory evidence.** These static modeled soil properties provide context but do not establish an independent or causal explanation.
"""


def build(root: Path, output_dir: Path | None = None) -> dict[str, Path]:
    root = root.resolve()
    soil_path = root / "data/processed/soil/soilgrids_era5_grid_properties.csv"
    regime_root = root / "outputs/research/exp_03/march_soil_moisture_depth"
    regime_path = regime_root / "grid_depth_regimes.csv"
    production_path = regime_root / "regime_production_support_summary.csv"
    for path in [soil_path, regime_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required upstream artifact not found: {path}")

    soil = pd.read_csv(soil_path)
    regimes = pd.read_csv(regime_path)
    validate_soil_table(soil)
    merged = attach_regimes(soil, regimes)
    profiles = thickness_weighted_profiles(merged)
    profile_summary = regime_profile_summary(profiles)
    contrasts = soil_contrasts(merged, profiles)
    latitude = latitude_associations(profiles)
    production = pd.read_csv(production_path) if production_path.exists() else None

    output = output_dir or root / "outputs/research/exp_03/soil_regime_synthesis"
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "profile_summary": output / "regime_soil_profile_summary.csv",
        "contrasts": output / "regime_soil_contrasts.csv",
        "latitude": output / "soil_latitude_association.csv",
        "report": output / "EXP_03_soil_regime_synthesis_report.md",
    }
    profile_summary.to_csv(paths["profile_summary"], index=False)
    contrasts.to_csv(paths["contrasts"], index=False)
    latitude.to_csv(paths["latitude"], index=False)
    paths["report"].write_text(
        report_text(profile_summary, contrasts, latitude, production), encoding="utf-8"
    )
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=project_root())
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(args.project_root, args.output_dir)


if __name__ == "__main__":
    main()
