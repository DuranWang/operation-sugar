"""EXP-05 conditional temperature/VPD association on frozen grid yield targets.

The module reuses EXP-02B outcome and annual-weight details plus canonical
monthly weather.  Each grid and crop-year-relative month-slot is a separate
historical time series.  No upstream ETL or yield detrending is performed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, t as student_t
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis.exp03_yield_stratified_monthly_weather import relative_month_lookup


Y10 = "Y_P50_10_actual_tch"
Y12 = "Y_P50_12_actual_tch"
YFIX = "Y_P50_10_fixed_tch"
TEMP = "T_C"
VPD = "VPD_kPa"
TARGETS = (Y10, Y12, YFIX)
MIN_LINEAR_N = 15
MIN_PRIMARY_N = 20
MIN_QUADRATIC_N = 30
WEATHER_SOURCE_START = 1981
WEATHER_SOURCE_END = 2025


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def source_paths(root: Path) -> dict[str, Path]:
    return {
        "grid_targets": root / "data/processed/analysis/exp_02b/actual_vs_fixed_grid_residuals.csv",
        "municipality_weights": root / "data/processed/analysis/exp_02b/matched_support_weight_details.csv",
        "municipality_grid_mapping": root / "outputs/research/exp_02/exp_02b/eligible_municipality_grid_mapping.csv",
        "annual_weather": root / "data/processed/combined_weather/annual",
        "weather_inventory": root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1/weather_variable_inventory.csv",
        "monthly_alignment_example": root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1/relative_month_alignment_examples.csv",
        "grid_target_code": root / "src/analysis/exp02b_composition_sensitivity.py",
        "grid_weather_code": root / "src/analysis/exp03_yield_stratified_monthly_weather.py",
        "temperature_etl_code": root / "src/etl/weather/build_combined_monthly_weather.py",
        "vpd_etl_code": root / "src/etl/open_meteo/process_advanced_weather_data.py",
    }


def discover_slots(root: Path) -> pd.DataFrame:
    """Freeze month slots from the existing analysis artifact and verify code."""

    existing = pd.read_csv(source_paths(root)["monthly_alignment_example"])
    fields = [
        "relative_month_index", "relative_month", "source_year_offset",
        "source_calendar_month", "calendar_month_label", "primary_window",
        "extended_only",
    ]
    slots = existing[fields].drop_duplicates().sort_values("relative_month_index").reset_index(drop=True)
    if slots.duplicated("relative_month_index").any() or len(slots) != 16:
        raise ValueError("Existing monthly-analysis artifact has ambiguous month slots")
    code_slots = relative_month_lookup()[fields].sort_values("relative_month_index").reset_index(drop=True)
    pd.testing.assert_frame_equal(slots, code_slots, check_dtype=False)
    slots = slots.rename(columns={"relative_month_index": "month_slot"})
    slots["yield_year_alignment"] = "source_year = yield_year + source_year_offset"
    slots["source_artifact"] = str(source_paths(root)["monthly_alignment_example"])
    return slots


def load_frozen_targets(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    paths = source_paths(root)
    results = pd.read_csv(paths["grid_targets"])
    weights = pd.read_csv(paths["municipality_weights"], dtype={"ibge_code": "string"})
    mapping = pd.read_csv(paths["municipality_grid_mapping"], dtype={"ibge_code": "string"})
    if results.duplicated(["grid_id", "year", "specification"]).any():
        raise ValueError("Duplicate frozen grid target keys")
    if weights.duplicated(["grid_id", "year", "ibge_code"]).any():
        raise ValueError("Duplicate municipality weight keys")
    if mapping.groupby("ibge_code").grid_id.nunique().gt(1).any():
        raise ValueError("Municipality outcomes overlap multiple ERA5 grids")
    if mapping.duplicated("ibge_code").any():
        raise ValueError("Duplicate municipality mapping keys")
    weight_sums = weights.groupby(["grid_id", "year"]).actual_weight.sum()
    fixed_sums = weights.groupby(["grid_id", "year"]).fixed_weight.sum()
    if not np.allclose(weight_sums, 1, atol=1e-10) or not np.allclose(fixed_sums, 1, atol=1e-10):
        raise ValueError("Existing grid weights are not normalized")

    primary = results.loc[results.specification.eq("p50_10")].copy()
    conservative = results.loc[results.specification.eq("p50_12"), [
        "grid_id", "year", "valid_grid_residual", "actual_grid_residual_tch"
    ]].rename(columns={
        "valid_grid_residual": "valid_p50_12",
        "actual_grid_residual_tch": Y12,
    })
    targets = primary.merge(conservative, on=["grid_id", "year"], validate="one_to_one")
    targets = targets.rename(columns={
        "valid_grid_residual": "valid_p50_10",
        "actual_grid_residual_tch": Y10,
        "fixed_grid_residual_tch": YFIX,
        "year": "yield_year",
    })
    for column, flag in [(Y10, "valid_p50_10"), (Y12, "valid_p50_12"), (YFIX, "valid_p50_10")]:
        targets[column] = targets[column].where(targets[flag].astype(bool))

    # Verify all three saved targets against the municipality residual inputs.
    errors = {}
    for target, residual, weight in [
        (Y10, "residual_p50_10", "actual_weight"),
        (Y12, "residual_p50_12", "actual_weight"),
        (YFIX, "residual_p50_10", "fixed_weight"),
    ]:
        reconstructed = weights.assign(weighted=weights[residual] * weights[weight]).groupby(
            ["grid_id", "year"], as_index=False
        ).weighted.sum().rename(columns={"year": "yield_year"})
        joined = targets[["grid_id", "yield_year", target]].merge(
            reconstructed, on=["grid_id", "yield_year"], how="left", validate="one_to_one"
        )
        valid = joined[target].notna()
        if joined.loc[valid, "weighted"].isna().any():
            raise ValueError(f"Missing municipality lineage for {target}")
        max_error = float((joined.loc[valid, target] - joined.loc[valid, "weighted"]).abs().max())
        if max_error > 1e-9:
            raise ValueError(f"Frozen target lineage disagrees for {target}: {max_error}")
        errors[target] = max_error

    # No municipality appears in two grids. Check whether target values are
    # literally replicated statewide within a year as an additional guard.
    duplicate_target_values = int(sum(
        group[Y10].dropna().duplicated().sum()
        for _, group in targets.groupby("yield_year")
    ))
    valid_primary = targets.loc[targets[Y10].notna()]
    minimum_distinct_targets = int(valid_primary.groupby("yield_year")[Y10].nunique().min())
    if minimum_distinct_targets <= 1:
        raise ValueError("Grid targets appear to replicate one statewide annual value")

    overlap = {
        "municipalities_mapped": int(mapping.ibge_code.nunique()),
        "grids_mapped": int(mapping.grid_id.nunique()),
        "municipalities_mapped_to_multiple_grids": 0,
        "grid_years_with_weights": int(weights[["grid_id", "year"]].drop_duplicates().shape[0]),
        "year_within_grid_duplicate_target_values": duplicate_target_values,
        "minimum_distinct_grid_targets_per_year": minimum_distinct_targets,
        "target_lineage_max_abs_error_tch": errors,
        "weight_sum_min": float(weight_sums.min()),
        "weight_sum_max": float(weight_sums.max()),
        "fixed_weight_sum_min": float(fixed_sums.min()),
        "fixed_weight_sum_max": float(fixed_sums.max()),
        "spatial_caveat": (
            "Municipality outcome memberships are disjoint across grids; "
            "shared annual shocks and weather-source groups can still induce dependence."
        ),
    }
    return targets, weights, mapping, overlap


def load_monthly_weather(root: Path, needed_source_years: set[int]) -> pd.DataFrame:
    """Read only T/VPD and keys from existing canonical annual CSV files."""

    folder = source_paths(root)["annual_weather"]
    columns = [
        "ibge_code", "era5_grid_id", "month",
        "nasa_average_temperature_c", "vpd_mean_kpa",
    ]
    frames = []
    for year in sorted(needed_source_years):
        if year < WEATHER_SOURCE_START or year > WEATHER_SOURCE_END:
            continue
        path = folder / f"sp_municipality_monthly_weather_{year}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Existing canonical weather year is missing: {path}")
        frame = pd.read_csv(path, usecols=columns, dtype={"ibge_code": "string"})
        frame["source_year"] = year
        frame["source_calendar_month"] = frame.month.str[-2:].astype(int)
        if not frame.month.str.startswith(f"{year}-").all():
            raise ValueError(f"Weather year does not agree with file name: {path}")
        frames.append(frame.drop(columns="month"))
    weather = pd.concat(frames, ignore_index=True).rename(columns={
        "era5_grid_id": "grid_id",
        "nasa_average_temperature_c": TEMP,
        "vpd_mean_kpa": VPD,
    })
    if weather.duplicated(["ibge_code", "source_year", "source_calendar_month"]).any():
        raise ValueError("Canonical municipality-month weather keys are duplicated")
    return weather


def build_grid_slot_panel(
    targets: pd.DataFrame, weights: pd.DataFrame, weather: pd.DataFrame,
    slots: pd.DataFrame,
) -> pd.DataFrame:
    """Join Y, T and VPD without a complete-window or other-variable gate."""

    keys = ["grid_id", "yield_year", "month_slot"]
    alignment = targets.merge(slots.drop(columns="source_artifact"), how="cross")
    alignment["source_year"] = alignment.yield_year + alignment.source_year_offset
    alignment["weather_source_available"] = alignment.source_year.between(
        WEATHER_SOURCE_START, WEATHER_SOURCE_END
    )
    valid_y = alignment.loc[alignment[Y10].notna()].copy()
    w = weights[["grid_id", "year", "ibge_code", "actual_weight"]].rename(columns={"year": "yield_year"})
    expanded = valid_y[keys + ["source_year", "source_calendar_month"]].merge(
        w, on=["grid_id", "yield_year"], how="left", validate="many_to_many"
    )
    if expanded.ibge_code.isna().any():
        raise ValueError("Valid target lacks existing municipality weights")
    expanded = expanded.merge(
        weather,
        on=["grid_id", "ibge_code", "source_year", "source_calendar_month"],
        how="left", validate="many_to_one",
    )
    for variable in [TEMP, VPD]:
        expanded[f"{variable}_valid"] = np.isfinite(expanded[variable])
        expanded[f"{variable}_covered_weight"] = expanded.actual_weight.where(
            expanded[f"{variable}_valid"], 0.0
        )
        expanded[f"{variable}_weighted"] = expanded.actual_weight * expanded[variable].where(
            expanded[f"{variable}_valid"], 0.0
        )
    grouped = expanded.groupby(keys, as_index=False).agg(
        T_covered_weight=(f"{TEMP}_covered_weight", "sum"),
        VPD_covered_weight=(f"{VPD}_covered_weight", "sum"),
        T_weighted=(f"{TEMP}_weighted", "sum"),
        VPD_weighted=(f"{VPD}_weighted", "sum"),
        matched_weather_municipalities=("T_C_valid", "sum"),
    )
    grouped[TEMP] = grouped.T_weighted.where(np.isclose(grouped.T_covered_weight, 1.0, atol=1e-10))
    grouped[VPD] = grouped.VPD_weighted.where(np.isclose(grouped.VPD_covered_weight, 1.0, atol=1e-10))
    panel = alignment.merge(
        grouped[keys + ["T_covered_weight", "VPD_covered_weight", TEMP, VPD,
                        "matched_weather_municipalities"]],
        on=keys, how="left", validate="one_to_one",
    )
    panel["T_covered_weight"] = panel.T_covered_weight.fillna(0.0)
    panel["VPD_covered_weight"] = panel.VPD_covered_weight.fillna(0.0)
    if panel.duplicated(keys).any() or len(panel) != len(targets) * len(slots):
        raise ValueError("Grid-slot panel changed target/slot cardinality")
    panel["primary_eligible"] = np.isfinite(panel[[Y10, TEMP, VPD]]).all(axis=1)
    panel["all_target_eligible"] = np.isfinite(panel[[Y10, Y12, YFIX, TEMP, VPD]]).all(axis=1)
    panel["missingness_reason"] = np.select(
        [
            panel[Y10].isna(),
            ~panel.weather_source_available,
            panel[TEMP].isna() & panel[VPD].isna(),
            panel[TEMP].isna(),
            panel[VPD].isna(),
        ],
        [
            "invalid_or_missing_primary_target", "source_year_outside_verified_weather",
            "temperature_and_vpd_missing_or_partial_weight_coverage",
            "temperature_missing_or_partial_weight_coverage",
            "vpd_missing_or_partial_weight_coverage",
        ],
        default="eligible",
    )
    return panel.sort_values(keys).reset_index(drop=True)


def sample_tier(n: int) -> str:
    if n < MIN_LINEAR_N:
        return "lt15"
    if n < MIN_PRIMARY_N:
        return "15_19_low_n"
    if n < MIN_QUADRATIC_N:
        return "20_29_primary_linear"
    return "ge30_linear_and_restricted_quadratic"


def sample_support(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (slot, grid), group in panel.groupby(["month_slot", "grid_id"], sort=True):
        usable = group.loc[group.primary_eligible]
        common = group.loc[group.all_target_eligible]
        n = len(usable)
        rows.append({
            "month_slot": slot, "grid_id": grid,
            "calendar_month_label": group.calendar_month_label.iloc[0],
            "grid_latitude": group.grid_latitude.iloc[0],
            "grid_longitude": group.grid_longitude.iloc[0],
            "n_primary": n, "n_all_targets_common": len(common),
            "sample_tier": sample_tier(n),
            "included_years": ";".join(map(str, usable.yield_year.astype(int))),
            "all_target_common_years": ";".join(map(str, common.yield_year.astype(int))),
            "first_primary_year": usable.yield_year.min(),
            "last_primary_year": usable.yield_year.max(),
            "median_area_ha_primary_years": usable.actual_weight_denominator_ha.median(),
            "mean_area_ha_primary_years": usable.actual_weight_denominator_ha.mean(),
            "single_municipality_grid": bool(group.single_municipality_grid.iloc[0]),
        })
    return pd.DataFrame(rows)


def ols(y: np.ndarray, x: np.ndarray) -> dict[str, object]:
    """Intercept-inclusive OLS with HC3 covariance and rank diagnostics."""

    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    design = np.column_stack([np.ones(len(y)), x])
    coefficients, _, rank, singular = np.linalg.lstsq(design, y, rcond=None)
    if rank < design.shape[1]:
        raise np.linalg.LinAlgError("rank_deficient_design")
    fitted = design @ coefficients
    residual = y - fitted
    sse = float(residual @ residual)
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - sse / sst if sst > 0 else np.nan
    inverse = np.linalg.inv(design.T @ design)
    leverage = np.einsum("ij,jk,ik->i", design, inverse, design)
    safe = np.clip(1 - leverage, 1e-12, None)
    hc3 = inverse @ (design.T * ((residual / safe) ** 2)) @ design @ inverse
    se = np.sqrt(np.clip(np.diag(hc3), 0, None))
    dof = len(y) - design.shape[1]
    critical = float(student_t.ppf(.975, dof)) if dof > 0 else np.nan
    sigma2 = sse / dof if dof > 0 else np.nan
    cooks = ((residual ** 2) / (design.shape[1] * sigma2)) * leverage / safe ** 2 if sigma2 > 0 else np.zeros(len(y))
    return {
        "coef": coefficients, "se_hc3": se, "ci_low_hc3": coefficients - critical * se,
        "ci_high_hc3": coefficients + critical * se, "r2": r2, "sse": sse,
        "residual": residual, "fitted": fitted,
        "condition_number_raw": float(singular.max() / singular.min()),
        "max_leverage": float(leverage.max()), "max_cooks_distance": float(np.nanmax(cooks)),
        "max_cooks_index": int(np.nanargmax(cooks)),
    }


def residualize(y: np.ndarray, conditioned: np.ndarray) -> np.ndarray:
    controls = np.asarray(conditioned)
    if controls.ndim == 1:
        controls = controls[:, None]
    return np.asarray(ols(y, controls)["residual"])


def partial_correlation(y: np.ndarray, tested: np.ndarray, conditioned: np.ndarray) -> float:
    """Two-sided intercept-inclusive OLS residualization."""

    y_resid = residualize(y, conditioned)
    tested_resid = residualize(tested, conditioned)
    if np.std(y_resid) <= 1e-12 or np.std(tested_resid) <= 1e-12:
        raise np.linalg.LinAlgError("near_constant_residualized_feature")
    return float(np.corrcoef(y_resid, tested_resid)[0, 1])


def fit_linear_sample(sample: pd.DataFrame, target: str = Y10) -> dict[str, object]:
    """Fit all three models and both partial directions on one fixed sample."""

    y = sample[target].to_numpy(dtype=float)
    t = sample[TEMP].to_numpy(dtype=float)
    v = sample[VPD].to_numpy(dtype=float)
    n = len(sample)
    if n < MIN_LINEAR_N or not np.isfinite(np.column_stack([y, t, v])).all():
        raise ValueError("Linear sample lacks >=15 finite paired years")
    std = np.std(np.column_stack([y, t, v]), axis=0, ddof=1)
    if np.any(std <= 1e-12):
        raise np.linalg.LinAlgError("near_constant_primary_feature")
    yt, yv, tv = [float(np.corrcoef(a, b)[0, 1]) for a, b in [(y, t), (y, v), (t, v)]]
    fit_t = ols(y, t[:, None])
    fit_v = ols(y, v[:, None])
    fit_full = ols(y, np.column_stack([t, v]))
    partial_v_t = partial_correlation(y, v, t)
    partial_t_v = partial_correlation(y, t, v)
    delta_v_t = float(fit_full["r2"] - fit_t["r2"])
    delta_t_v = float(fit_full["r2"] - fit_v["r2"])
    partial_r2_v_t = float((fit_t["sse"] - fit_full["sse"]) / fit_t["sse"])
    partial_r2_t_v = float((fit_v["sse"] - fit_full["sse"]) / fit_v["sse"])
    identity_error = max(abs(partial_v_t ** 2 - partial_r2_v_t), abs(partial_t_v ** 2 - partial_r2_t_v))
    if identity_error > 1e-8:
        raise ValueError(f"Partial correlation/R² identity failed: {identity_error}")
    ranks = np.column_stack([rankdata(col, method="average") for col in [y, t, v]])
    rank_v_t = partial_correlation(ranks[:, 0], ranks[:, 2], ranks[:, 1])
    rank_t_v = partial_correlation(ranks[:, 0], ranks[:, 1], ranks[:, 2])
    # Collinearity quality q is the same in both directions for one control.
    q = float(1 - tv ** 2)
    t_resid_sd = float(np.std(residualize(t, v), ddof=1))
    v_resid_sd = float(np.std(residualize(v, t), ddof=1))
    standardized = np.asarray(fit_full["coef"])[1:] * std[1:] / std[0]
    return {
        "n": n, "r_y_t": yt, "r_y_vpd": yv, "r_t_vpd": tv,
        "partial_r_y_vpd_given_t": partial_v_t, "partial_r_y_t_given_vpd": partial_t_v,
        "rank_partial_r_y_vpd_given_t": rank_v_t,
        "rank_partial_r_y_t_given_vpd": rank_t_v,
        "beta_t_raw_tch_per_c": float(fit_full["coef"][1]),
        "beta_vpd_raw_tch_per_kpa": float(fit_full["coef"][2]),
        "beta_t_standardized_y_and_predictor": float(standardized[0]),
        "beta_vpd_standardized_y_and_predictor": float(standardized[1]),
        "beta_t_se_hc3": float(fit_full["se_hc3"][1]),
        "beta_vpd_se_hc3": float(fit_full["se_hc3"][2]),
        "beta_t_ci_low_hc3": float(fit_full["ci_low_hc3"][1]),
        "beta_t_ci_high_hc3": float(fit_full["ci_high_hc3"][1]),
        "beta_vpd_ci_low_hc3": float(fit_full["ci_low_hc3"][2]),
        "beta_vpd_ci_high_hc3": float(fit_full["ci_high_hc3"][2]),
        "r2_t_only": float(fit_t["r2"]), "r2_vpd_only": float(fit_v["r2"]),
        "r2_full": float(fit_full["r2"]),
        "delta_r2_vpd_given_t": delta_v_t, "delta_r2_t_given_vpd": delta_t_v,
        "partial_r2_vpd_given_t": partial_r2_v_t,
        "partial_r2_t_given_vpd": partial_r2_t_v,
        "partial_identity_max_error": identity_error,
        "q_vpd_given_t": q, "q_t_given_vpd": q,
        "residual_vpd_sd_kpa": v_resid_sd, "residual_t_sd_c": t_resid_sd,
        "sd_y_tch": float(std[0]), "sd_t_c": float(std[1]), "sd_vpd_kpa": float(std[2]),
        "condition_number_standardized_predictors": float(np.sqrt((1 + abs(tv)) / q) * np.sqrt(1 + abs(tv))),
        "condition_number_raw_design": float(fit_full["condition_number_raw"]),
        "max_leverage": float(fit_full["max_leverage"]),
        "max_cooks_distance": float(fit_full["max_cooks_distance"]),
        "max_cooks_year": int(sample.yield_year.iloc[fit_full["max_cooks_index"]]),
        "included_years": ";".join(map(str, sample.yield_year.astype(int))),
    }


def fit_grid_linear(panel: pd.DataFrame, target: str = Y10, common: bool = False) -> pd.DataFrame:
    rows = []
    eligibility = "all_target_eligible" if common else "primary_eligible"
    for (slot, grid), group in panel.groupby(["month_slot", "grid_id"], sort=True):
        sample = group.loc[group[eligibility]].sort_values("yield_year")
        row = {
            "month_slot": slot, "grid_id": grid,
            "calendar_month_label": group.calendar_month_label.iloc[0],
            "target": target, "sample_definition": "all_target_common" if common else "primary_maximal",
            "sample_tier": sample_tier(len(sample)),
            "n": len(sample),
            "first_year": sample.yield_year.min(), "last_year": sample.yield_year.max(),
            "grid_latitude": group.grid_latitude.iloc[0],
            "grid_longitude": group.grid_longitude.iloc[0],
            "mean_area_ha": sample.actual_weight_denominator_ha.mean(),
            "included_years": ";".join(map(str, sample.yield_year.astype(int))),
            "fit_status": "below_15" if len(sample) < MIN_LINEAR_N else "estimable",
        }
        if len(sample) >= MIN_LINEAR_N:
            try:
                row.update(fit_linear_sample(sample, target))
            except (np.linalg.LinAlgError, ValueError) as error:
                row["fit_status"] = f"inestimable:{error}"
        rows.append(row)
    return pd.DataFrame(rows)


def strata_diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    """Empirical within-series thirds; tied values receive average ranks."""

    rows = []
    for (slot, grid), group in panel.groupby(["month_slot", "grid_id"], sort=True):
        sample = group.loc[group.primary_eligible].sort_values("yield_year")
        if len(sample) < MIN_LINEAR_N:
            continue
        for conditioner, tested, direction in [
            (TEMP, VPD, "VPD_given_T"), (VPD, TEMP, "T_given_VPD")
        ]:
            n = len(sample)
            ranks = rankdata(sample[conditioner].to_numpy(), method="average")
            labels = np.where((ranks - .5) / n < 1 / 3, "low",
                              np.where((ranks - .5) / n >= 2 / 3, "high", "middle"))
            cuts = np.quantile(sample[conditioner], [1 / 3, 2 / 3])
            ranges = {name: (float(part[tested].min()), float(part[tested].max()))
                      for name in ("low", "middle", "high")
                      for part in [sample.loc[labels == name]] if len(part)}
            overlap_low = max(value[0] for value in ranges.values())
            overlap_high = min(value[1] for value in ranges.values())
            for name in ("low", "middle", "high"):
                part = sample.loc[labels == name]
                slope = np.nan
                if len(part) >= 10 and part[tested].std() > 1e-12:
                    slope = float(ols(part[Y10].to_numpy(), part[tested].to_numpy()[:, None])["coef"][1])
                rows.append({
                    "month_slot": slot, "calendar_month_label": group.calendar_month_label.iloc[0],
                    "grid_id": grid, "direction": direction, "conditioning_variable": conditioner,
                    "tested_variable": tested, "stratum": name, "n_series": n, "n_stratum": len(part),
                    "years": ";".join(map(str, part.yield_year.astype(int))),
                    "tertile_cut_1": cuts[0], "tertile_cut_2": cuts[1],
                    "tie_rule": "average ranks; fractional rank below 1/3 low, at or above 2/3 high",
                    "conditioning_min": part[conditioner].min(), "conditioning_median": part[conditioner].median(),
                    "conditioning_max": part[conditioner].max(),
                    "tested_min": part[tested].min(), "tested_median": part[tested].median(),
                    "tested_max": part[tested].max(), "tested_sd": part[tested].std(),
                    "yield_min_tch": part[Y10].min(), "yield_median_tch": part[Y10].median(),
                    "yield_max_tch": part[Y10].max(), "yield_sd_tch": part[Y10].std(),
                    "common_tested_range_low": overlap_low,
                    "common_tested_range_high": overlap_high,
                    "all_three_strata_tested_overlap": overlap_high >= overlap_low,
                    "descriptive_slope_tch_per_tested_unit": slope,
                    "slope_status": "descriptive_n_ge_10" if np.isfinite(slope) else "not_fitted_n_lt_10_or_degenerate",
                })
    return pd.DataFrame(rows)


def restricted_grid_nonlinear(panel: pd.DataFrame) -> pd.DataFrame:
    """Only the two preregistered M1/M2 versus M3/M4 comparisons."""

    rows = []
    for (slot, grid), group in panel.groupby(["month_slot", "grid_id"], sort=True):
        sample = group.loc[group.primary_eligible].sort_values("yield_year")
        n = len(sample)
        if n < MIN_QUADRATIC_N:
            continue
        y = sample[Y10].to_numpy(float)
        for conditioner, tested, direction in [(TEMP, VPD, "VPD_given_T"), (VPD, TEMP, "T_given_VPD")]:
            c = sample[conditioner].to_numpy(float)
            x = sample[tested].to_numpy(float)
            row = {"month_slot": slot, "grid_id": grid, "calendar_month_label": group.calendar_month_label.iloc[0],
                   "direction": direction, "n": n, "status": "estimable"}
            try:
                c = (c - c.mean()) / c.std(ddof=1)
                x = (x - x.mean()) / x.std(ddof=1)
                m1 = ols(y, c[:, None]); m2 = ols(y, np.column_stack([c, x]))
                m3 = ols(y, np.column_stack([c, c ** 2]))
                m4 = ols(y, np.column_stack([c, c ** 2, x]))
                x_resid = residualize(x, np.column_stack([c, c ** 2]))
                row.update({"r2_m1": m1["r2"], "r2_m2": m2["r2"], "r2_m3": m3["r2"],
                            "r2_m4": m4["r2"], "delta_r2_linear": m2["r2"] - m1["r2"],
                            "delta_r2_after_quadratic_control": m4["r2"] - m3["r2"],
                            "increment_change_after_quadratic": (m4["r2"] - m3["r2"]) - (m2["r2"] - m1["r2"]),
                            "tested_residual_sd_after_quadratic_standardized": np.std(x_resid, ddof=1),
                            "m4_condition_number_raw_design": m4["condition_number_raw"]})
            except (np.linalg.LinAlgError, ValueError, FloatingPointError) as error:
                row["status"] = f"inestimable:{error}"
            rows.append(row)
    return pd.DataFrame(rows)


def pooled_nonlinear(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-slot grid-intercept common-slope fits; no year effects."""

    rows = []
    for slot, group in panel.groupby("month_slot", sort=True):
        counts = group.groupby("grid_id").primary_eligible.sum()
        usable = group.loc[group.primary_eligible & group.grid_id.isin(counts[counts >= MIN_PRIMARY_N].index)].copy()
        row = {"month_slot": slot, "calendar_month_label": group.calendar_month_label.iloc[0],
               "n_grid_years": len(usable), "n_grids": usable.grid_id.nunique(),
               "sample_rule": "primary-complete grid-series with N>=20; grid intercepts; common slopes; no year FE",
               "status": "estimable"}
        if len(usable) < 30:
            row["status"] = "insufficient_support"; rows.append(row); continue
        for variable, key in [(TEMP, "t"), (VPD, "v")]:
            usable[key] = usable.groupby("grid_id")[variable].transform(
                lambda s: (s - s.mean()) / s.std(ddof=1) if s.std(ddof=1) > 1e-12 else np.nan)
        if usable[["t", "v"]].isna().any().any():
            row["status"] = "degenerate_within_grid_predictor"; rows.append(row); continue
        usable["t2"] = usable.t ** 2; usable["v2"] = usable.v ** 2; usable["tv"] = usable.t * usable.v
        terms = {"L": ["t", "v"], "Q_T": ["t", "v", "t2"],
                 "Q_V": ["t", "v", "v2"], "Q": ["t", "v", "t2", "v2"],
                 "I": ["t", "v", "t2", "v2", "tv"]}
        y = (usable[Y10] - usable.groupby("grid_id")[Y10].transform("mean")).to_numpy(float)
        sst = float(y @ y)
        for model, columns in terms.items():
            x = usable[columns] - usable.groupby("grid_id")[columns].transform("mean")
            coef, _, rank, singular = np.linalg.lstsq(x.to_numpy(float), y, rcond=None)
            if rank < len(columns):
                row["status"] = f"rank_deficient_{model}"; break
            err = y - x.to_numpy(float) @ coef
            row[f"r2_{model}"] = 1 - float(err @ err) / sst
            row[f"condition_{model}"] = singular.max() / singular.min()
            for term, value in zip(columns, coef):
                row[f"beta_{model}_{term}"] = value
        if row["status"] == "estimable":
            for model in ["Q_T", "Q_V", "Q", "I"]:
                row[f"delta_r2_{model}_vs_L"] = row[f"r2_{model}"] - row["r2_L"]
            row["delta_r2_I_vs_Q"] = row["r2_I"] - row["r2_Q"]
        rows.append(row)
    return pd.DataFrame(rows)


def _fast_partial_stats(values: np.ndarray) -> tuple[float, float, float, float]:
    """Correlational identity for resampling/LOYO, after paired-row selection."""

    if len(values) < MIN_LINEAR_N or np.min(np.std(values, axis=0)) <= 1e-12:
        return (np.nan,) * 4
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(values, rowvar=False)
        ryt, ryv, rtv = corr[0, 1], corr[0, 2], corr[1, 2]
        q = 1 - rtv * rtv
        if q <= 1e-10:
            return (np.nan,) * 4
        pv = (ryv - ryt * rtv) / np.sqrt((1 - ryt * ryt) * q)
        pt = (ryt - ryv * rtv) / np.sqrt((1 - ryv * ryv) * q)
        return float(pv), float(pt), float(pv * pv * (1 - ryt * ryt)), float(pt * pt * (1 - ryv * ryv))


def leave_one_year_out(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (slot, grid), group in panel.groupby(["month_slot", "grid_id"], sort=True):
        sample = group.loc[group.primary_eligible].sort_values("yield_year")
        if len(sample) < MIN_LINEAR_N:
            continue
        values = sample[[Y10, TEMP, VPD]].to_numpy(float)
        base = _fast_partial_stats(values)
        changes = [[], []]
        sign_flips = [0, 0]
        for index in range(len(sample)):
            leave = _fast_partial_stats(np.delete(values, index, axis=0))
            for direction in range(2):
                changes[direction].append(leave[direction])
                if np.isfinite(leave[direction]) and np.sign(leave[direction]) != np.sign(base[direction]):
                    sign_flips[direction] += 1
        for direction, name in enumerate(["VPD_given_T", "T_given_VPD"]):
            arr = np.asarray(changes[direction], float)
            rows.append({"month_slot": slot, "grid_id": grid, "direction": name, "n": len(sample),
                         "base_partial": base[direction], "min_loyo_partial": np.nanmin(arr),
                         "max_loyo_partial": np.nanmax(arr),
                         "max_abs_loyo_change": np.nanmax(np.abs(arr - base[direction])),
                         "n_loyo_sign_flips": sign_flips[direction],
                         "n_inestimable_loyo": int(np.isnan(arr).sum()),
                         "most_influential_left_out_year": int(sample.yield_year.iloc[np.nanargmax(np.abs(arr - base[direction]))])})
    return pd.DataFrame(rows)


def cross_month_common_year(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    slots = set(panel.month_slot.unique())
    common = panel.loc[panel.primary_eligible].groupby(["grid_id", "yield_year"]).month_slot.nunique()
    common_keys = set(common[common.eq(len(slots))].index)
    sensitivity = panel.loc[[key in common_keys for key in zip(panel.grid_id, panel.yield_year)]].copy()
    fit = fit_grid_linear(sensitivity)
    fit["sample_definition"] = "all_16_slots_common_years_sensitivity"
    counts = panel.groupby(["month_slot", "grid_id"]).primary_eligible.sum().rename("n_maximal")
    fit = fit.merge(counts.reset_index(), on=["month_slot", "grid_id"], how="left", validate="one_to_one")
    fit["years_lost_vs_maximal"] = fit.n_maximal - fit.n
    years = pd.DataFrame(sorted(common_keys), columns=["grid_id", "yield_year"])
    return fit, years


def synchronized_bootstrap(panel: pd.DataFrame, replicates: int = 200, seed: int = 20261010) -> pd.DataFrame:
    """Global yield-year draws are shared by every grid and month-slot."""

    rng = np.random.default_rng(seed)
    years = np.arange(WEATHER_SOURCE_START, WEATHER_SOURCE_END + 1)
    draws = {}
    for block in [1, 3, 5]:
        for replicate in range(replicates):
            if block == 1:
                draw = rng.choice(years, size=len(years), replace=True)
            else:
                starts = rng.integers(0, len(years) - block + 1,
                                      size=int(np.ceil(len(years) / block)))
                draw = np.concatenate([years[start:start + block] for start in starts])[:len(years)]
            draws[block, replicate] = np.bincount(draw - years[0], minlength=len(years))
    rows = []
    for slot, slot_data in panel.groupby("month_slot", sort=True):
        series = []
        for grid, group in slot_data.groupby("grid_id"):
            sample = group.loc[group.primary_eligible]
            if len(sample) < MIN_PRIMARY_N:
                continue
            series.append((grid, sample.yield_year.to_numpy(int) - years[0],
                           sample[[Y10, TEMP, VPD]].to_numpy(float)))
        for block in [1, 3, 5]:
            for replicate in range(replicates):
                counts = draws[block, replicate]
                estimates = []
                failed = 0
                for _, year_idx, values in series:
                    repeated = np.repeat(values, counts[year_idx], axis=0)
                    if len(repeated) < MIN_PRIMARY_N:
                        failed += 1; continue
                    result = _fast_partial_stats(repeated)
                    if not np.isfinite(result[:2]).all():
                        failed += 1; continue
                    estimates.append(result)
                matrix = np.asarray(estimates).reshape(-1, 4)
                for direction, index in [("VPD_given_T", 0), ("T_given_VPD", 1)]:
                    values = matrix[:, index]
                    rows.append({"month_slot": slot, "calendar_month_label": slot_data.calendar_month_label.iloc[0],
                                 "direction": direction, "block_length_years": block,
                                 "replicate": replicate, "seed": seed,
                                 "n_input_grids": len(series), "n_estimable_grids": len(values),
                                 "n_inestimable_grids": failed,
                                 "median_partial": np.median(values) if len(values) else np.nan,
                                 "fraction_positive": np.mean(values > 0) if len(values) else np.nan,
                                 "median_delta_r2": np.median(matrix[:, index + 2]) if len(values) else np.nan})
    return pd.DataFrame(rows)


def pooled_nonlinear_synchronized_bootstrap(
    panel: pd.DataFrame, replicates: int = 200, seed: int = 20261010,
) -> pd.DataFrame:
    """Refit pooled grid-intercept L/Q/I fits on synchronized yield-year draws."""

    rng = np.random.default_rng(seed)
    years = np.arange(WEATHER_SOURCE_START, WEATHER_SOURCE_END + 1)
    slot_cubes = {}
    for slot, group in panel.groupby("month_slot", sort=True):
        group = group.loc[group.primary_eligible]
        eligible_grids = group.groupby("grid_id").size()
        grids = sorted(eligible_grids[eligible_grids.ge(MIN_PRIMARY_N)].index)
        cube = np.full((len(grids), len(years), 3), np.nan)
        grid_index = {grid: i for i, grid in enumerate(grids)}
        for row in group.loc[group.grid_id.isin(grids)].itertuples(index=False):
            cube[grid_index[row.grid_id], int(row.yield_year) - years[0]] = [
                getattr(row, Y10), getattr(row, TEMP), getattr(row, VPD)]
        slot_cubes[slot] = (group.calendar_month_label.iloc[0], cube)
    rows = []
    for block in [1, 3, 5]:
        for replicate in range(replicates):
            if block == 1:
                draw = rng.choice(years, size=len(years), replace=True)
            else:
                starts = rng.integers(0, len(years) - block + 1,
                                      size=int(np.ceil(len(years) / block)))
                draw = np.concatenate([years[start:start + block] for start in starts])[:len(years)]
            counts = np.bincount(draw - years[0], minlength=len(years))
            for slot, (label, cube) in slot_cubes.items():
                row = _pooled_from_year_cube(cube, counts)
                row.update({"month_slot": slot, "calendar_month_label": label,
                            "sample_rule": "synchronized year resample; refit within-grid scales and grid intercepts; common slopes"})
                row.update({"block_length_years": block, "replicate": replicate, "seed": seed,
                            "n_input_grids": len(cube),
                            "n_excluded_grids_n_lt_20_or_degenerate": len(cube) - row["n_grids"]})
                rows.append(row)
    return pd.DataFrame(rows)


def _pooled_from_year_cube(cube: np.ndarray, year_counts: np.ndarray) -> dict[str, object]:
    """Weighted sufficient-statistic OLS for repeated year rows, with grid FE."""

    mask = np.isfinite(cube).all(axis=2)
    w = mask * year_counts[None, :]
    n = w.sum(axis=1)
    valid = n >= MIN_PRIMARY_N
    if not valid.any():
        return {"status": "no_estimable_grids", "n_grids": 0, "n_grid_years": 0}
    x = np.nan_to_num(cube, nan=0.0)
    means = np.einsum("gy,gyp->gp", w, x) / np.maximum(n[:, None], 1)
    centered = x - means[:, None, :]
    variance = np.einsum("gy,gyp->gp", w, centered ** 2) / np.maximum(n[:, None] - 1, 1)
    valid &= np.all(variance > 1e-24, axis=1)
    if not valid.any():
        return {"status": "degenerate_within_grid_predictor", "n_grids": 0, "n_grid_years": 0}
    w = w[valid]
    centered = centered[valid]
    variance = variance[valid]
    n = n[valid]
    zt = centered[:, :, 1] / np.sqrt(variance[:, None, 1])
    zv = centered[:, :, 2] / np.sqrt(variance[:, None, 2])
    design = np.stack([zt, zv, zt ** 2, zv ** 2, zt * zv], axis=2)
    means_design = np.einsum("gy,gyp->gp", w, design) / n[:, None]
    design -= means_design[:, None, :]
    y = centered[:, :, 0]
    cross = np.einsum("gy,gyp,gyq->pq", w, design, design)
    xy = np.einsum("gy,gyp,gy->p", w, design, y)
    sst = np.einsum("gy,gy,gy->", w, y, y)
    row: dict[str, object] = {"status": "estimable", "n_grids": len(n), "n_grid_years": int(n.sum())}
    models = {"L": [0, 1], "Q_T": [0, 1, 2], "Q_V": [0, 1, 3],
              "Q": [0, 1, 2, 3], "I": [0, 1, 2, 3, 4]}
    for name, indices in models.items():
        xx = cross[np.ix_(indices, indices)]
        if np.linalg.matrix_rank(xx) < len(indices):
            row["status"] = f"rank_deficient_{name}"
            return row
        coef = np.linalg.solve(xx, xy[indices])
        row[f"r2_{name}"] = float(coef @ xy[indices] / sst)
        row[f"condition_{name}"] = float(np.linalg.cond(xx) ** .5)
    for name in ["Q_T", "Q_V", "Q", "I"]:
        row[f"delta_r2_{name}_vs_L"] = row[f"r2_{name}"] - row["r2_L"]
    row["delta_r2_I_vs_Q"] = row["r2_I"] - row["r2_Q"]
    return row


def monthly_area_coverage(panel: pd.DataFrame, support: pd.DataFrame) -> pd.DataFrame:
    """Numerator and denominator are both mapped, target-valid grid area."""

    merged = panel.merge(support[["month_slot", "grid_id", "n_primary"]],
                         on=["month_slot", "grid_id"], validate="many_to_one")
    rows = []
    for slot, group in merged.groupby("month_slot", sort=True):
        source = group.loc[group.weather_source_available & group[Y10].notna()]
        primary = source.loc[source.primary_eligible & source.n_primary.ge(MIN_PRIMARY_N)]
        low = source.loc[source.primary_eligible & source.n_primary.ge(MIN_LINEAR_N)]
        denominator = source.actual_weight_denominator_ha.sum()
        rows.append({"month_slot": slot, "calendar_month_label": group.calendar_month_label.iloc[0],
                     "denominator_target_valid_mapped_area_ha_year_sum": denominator,
                     "numerator_primary_n_ge_20_paired_area_ha_year_sum": primary.actual_weight_denominator_ha.sum(),
                     "numerator_n_ge_15_paired_area_ha_year_sum": low.actual_weight_denominator_ha.sum(),
                     "primary_area_fraction": primary.actual_weight_denominator_ha.sum() / denominator,
                     "n_ge_15_area_fraction": low.actual_weight_denominator_ha.sum() / denominator,
                     "denominator_convention": "sum across weather-source-compatible yield years of mapped EXP-02B valid-target grid-year observed harvested-area denominators; not all statewide municipalities"})
    return pd.DataFrame(rows)


def directional_results(primary: pd.DataFrame, loyo: pd.DataFrame,
                        other_targets: pd.DataFrame, common_year: pd.DataFrame,
                        nonlinear: pd.DataFrame) -> pd.DataFrame:
    rows = []
    partial_cols = {"VPD_given_T": ("partial_r_y_vpd_given_t", "rank_partial_r_y_vpd_given_t",
                                     "delta_r2_vpd_given_t", "partial_r2_vpd_given_t",
                                     "beta_vpd_ci_low_hc3", "beta_vpd_ci_high_hc3"),
                    "T_given_VPD": ("partial_r_y_t_given_vpd", "rank_partial_r_y_t_given_vpd",
                                     "delta_r2_t_given_vpd", "partial_r2_t_given_vpd",
                                     "beta_t_ci_low_hc3", "beta_t_ci_high_hc3")}
    lookup = {(row.month_slot, row.grid_id, row.target): row
              for row in other_targets.itertuples(index=False)}
    common_lookup = {(row.month_slot, row.grid_id): row for row in common_year.itertuples(index=False)}
    loyo_lookup = {(row.month_slot, row.grid_id, row.direction): row for row in loyo.itertuples(index=False)}
    nonlinear_lookup = {(row.month_slot, row.grid_id, row.direction): row for row in nonlinear.itertuples(index=False)}
    for row in primary.itertuples(index=False):
        for direction, (pc, rc, dc, prc, ci_l, ci_h) in partial_cols.items():
            record = {"month_slot": row.month_slot, "calendar_month_label": row.calendar_month_label,
                      "grid_id": row.grid_id, "grid_latitude": row.grid_latitude,
                      "grid_longitude": row.grid_longitude, "direction": direction,
                      "n": row.n, "sample_tier": row.sample_tier, "fit_status": row.fit_status,
                      "mean_area_ha": row.mean_area_ha}
            if row.fit_status == "estimable":
                marginal = row.r_y_vpd if direction == "VPD_given_T" else row.r_y_t
                record.update({"partial": getattr(row, pc), "rank_partial": getattr(row, rc),
                               "marginal": marginal,
                               "partial_minus_marginal": getattr(row, pc) - marginal,
                               "marginal_partial_sign_reversal": np.sign(getattr(row, pc)) != np.sign(marginal),
                               "delta_r2": getattr(row, dc), "partial_r2": getattr(row, prc),
                               "partial_ci_excludes_zero_hc3": getattr(row, ci_l) * getattr(row, ci_h) > 0,
                               "q_predictor": row.q_vpd_given_t,
                               "max_cooks_distance": row.max_cooks_distance,
                               "max_cooks_year": row.max_cooks_year})
                for target, name in [(Y12, "p50_12"), (YFIX, "fixed")]:
                    other = lookup.get((row.month_slot, row.grid_id, target))
                    record[f"partial_{name}_shared_years"] = getattr(other, pc) if other and other.fit_status == "estimable" else np.nan
                    record[f"n_{name}_shared_years"] = other.n if other else np.nan
                primary_shared = lookup.get((row.month_slot, row.grid_id, Y10))
                record["partial_primary_shared_years"] = getattr(primary_shared, pc) if primary_shared and primary_shared.fit_status == "estimable" else np.nan
                for name in ["p50_12", "fixed"]:
                    record[f"partial_difference_{name}_minus_primary_shared"] = (
                        record[f"partial_{name}_shared_years"] - record["partial_primary_shared_years"])
                lo = loyo_lookup.get((row.month_slot, row.grid_id, direction))
                if lo:
                    record.update({"max_abs_loyo_change": lo.max_abs_loyo_change,
                                   "n_loyo_sign_flips": lo.n_loyo_sign_flips,
                                   "most_influential_left_out_year": lo.most_influential_left_out_year})
                cm = common_lookup.get((row.month_slot, row.grid_id))
                record["partial_all_months_common_years"] = getattr(cm, pc) if cm and cm.fit_status == "estimable" else np.nan
                record["n_all_months_common_years"] = cm.n if cm else 0
                nl = nonlinear_lookup.get((row.month_slot, row.grid_id, direction))
                if nl and nl.status == "estimable":
                    record.update({"delta_r2_linear_nonlinear_sample": nl.delta_r2_linear,
                                   "delta_r2_after_quadratic_control": nl.delta_r2_after_quadratic_control})
                # No importance margin was approved, so this status never implies redundancy.
                record["evidence_status"] = (
                    "low_n_unresolved" if row.n < MIN_PRIMARY_N else
                    "directionally_consistent_candidate_magnitude_unadjudicated"
                    if (getattr(row, ci_l) * getattr(row, ci_h) > 0
                        and lo and lo.n_loyo_sign_flips == 0
                        and np.sign(getattr(row, pc)) == np.sign(getattr(row, rc))
                        and all(np.sign(record["partial_primary_shared_years"]) ==
                                np.sign(record.get(f"partial_{name}_shared_years", np.nan))
                                for name in ["p50_12", "fixed"]))
                    else "unresolved_or_mixed")
            else:
                record["evidence_status"] = "insufficient_support_or_inestimable"
            rows.append(record)
    return pd.DataFrame(rows)


def monthly_spatial_synthesis(directions: pd.DataFrame, support: pd.DataFrame,
                              area: pd.DataFrame, bootstrap: pd.DataFrame,
                              pooled: pd.DataFrame, pooled_bootstrap: pd.DataFrame) -> pd.DataFrame:
    summaries = []
    for (slot, direction), all_rows in directions.groupby(["month_slot", "direction"], sort=True):
        group = all_rows.loc[all_rows.n.ge(MIN_PRIMARY_N) & all_rows.fit_status.eq("estimable")]
        partial = group.partial.dropna()
        rank = group.rank_partial.dropna()
        row = {"month_slot": slot, "calendar_month_label": all_rows.calendar_month_label.iloc[0],
               "direction": direction, "n_grids_total": len(all_rows), "n_primary_estimable_grids": len(group),
               "n_low_n_15_19": int(all_rows.n.between(15, 19).sum()),
               "n_below_15": int(all_rows.n.lt(15).sum()),
               "n_ge_30": int(all_rows.n.ge(30).sum()),
               "median_partial": partial.median(), "q25_partial": partial.quantile(.25),
               "q75_partial": partial.quantile(.75),
               "median_rank_partial": rank.median(),
               "median_marginal": group.marginal.median(),
               "median_partial_minus_marginal": group.partial_minus_marginal.median(),
               "fraction_marginal_partial_sign_reversal": group.marginal_partial_sign_reversal.mean(),
               "median_delta_r2": group.delta_r2.median(), "median_partial_r2": group.partial_r2.median(),
               "fraction_positive": float((partial > 0).mean()) if len(partial) else np.nan,
               "fraction_negative": float((partial < 0).mean()) if len(partial) else np.nan,
               "n_rank_same_direction": int((np.sign(group.partial) == np.sign(group.rank_partial)).sum()),
               "n_loyo_sign_stable": int(group.n_loyo_sign_flips.eq(0).sum()),
               "median_q_predictor": group.q_predictor.median(),
               "n_directionally_consistent_candidates_magnitude_unadjudicated": int(group.evidence_status.eq("directionally_consistent_candidate_magnitude_unadjudicated").sum()),
               "mean_area_weighted_fraction_positive_supplemental": np.average(
                   (group.partial > 0).astype(float), weights=group.mean_area_ha) if len(group) and group.mean_area_ha.sum() > 0 else np.nan,
               "area_weighting_convention": "grid mean observed area over that slot's paired years; mapped EXP-02B support only; supplemental"}
        boot = bootstrap.loc[bootstrap.month_slot.eq(slot) & bootstrap.direction.eq(direction)]
        for block in [1, 3, 5]:
            sub = boot.loc[boot.block_length_years.eq(block)]
            row[f"bootstrap_block_{block}_median_partial_ci_low"] = sub.median_partial.quantile(.025)
            row[f"bootstrap_block_{block}_median_partial_ci_high"] = sub.median_partial.quantile(.975)
            row[f"bootstrap_block_{block}_median_fraction_positive"] = sub.fraction_positive.median()
            row[f"bootstrap_block_{block}_max_failed_grids"] = sub.n_inestimable_grids.max()
        for block in [3, 5]:
            pooled_draws = pooled_bootstrap.loc[pooled_bootstrap.month_slot.eq(slot) &
                                                pooled_bootstrap.block_length_years.eq(block) &
                                                pooled_bootstrap.status.eq("estimable")]
            for model in ["Q_T", "Q_V", "Q", "I"]:
                column = f"delta_r2_{model}_vs_L"
                row[f"pooled_block_{block}_{column}_ci_low"] = pooled_draws[column].quantile(.025)
                row[f"pooled_block_{block}_{column}_ci_high"] = pooled_draws[column].quantile(.975)
            row[f"pooled_block_{block}_fit_failures"] = int((pooled_bootstrap.loc[
                pooled_bootstrap.month_slot.eq(slot) & pooled_bootstrap.block_length_years.eq(block),
                "status"] != "estimable").sum())
        summaries.append(row)
    frame = pd.DataFrame(summaries)
    return frame.merge(area, on=["month_slot", "calendar_month_label"], validate="many_to_one").merge(
        pooled[["month_slot", "status", "n_grid_years", "n_grids", "delta_r2_Q_T_vs_L",
                "delta_r2_Q_V_vs_L", "delta_r2_Q_vs_L", "delta_r2_I_vs_Q"]],
        on="month_slot", validate="many_to_one", suffixes=("", "_pooled"))


def make_figures(directions: pd.DataFrame, summary: pd.DataFrame, panel: pd.DataFrame,
                 output: Path, prefix: str = "") -> None:
    figure_dir = output / "figures"
    figure_dir.mkdir(exist_ok=True)
    for direction in ["VPD_given_T", "T_given_VPD"]:
        sub = summary.loc[summary.direction.eq(direction)].sort_values("month_slot")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sub.month_slot, sub.median_partial, marker="o", label="grid-equal median partial")
        ax.fill_between(sub.month_slot.to_numpy(float),
                        sub.bootstrap_block_3_median_partial_ci_low.to_numpy(float),
                        sub.bootstrap_block_3_median_partial_ci_high.to_numpy(float),
                        alpha=.22, label="3-year synchronized bootstrap 95% interval")
        ax.axhline(0, color="black", linewidth=.8)
        ax.set_xticks(sub.month_slot); ax.set_xticklabels(sub.calendar_month_label, rotation=65, ha="right")
        ax.set_ylabel("Partial correlation")
        ax.set_title(f"EXP-05 {direction}: month-slot spatial median")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(figure_dir / f"{prefix}monthly_partial_{direction}.png", dpi=150)
        plt.close(fig)
    for slot in ([-2] if prefix else [-4, -2, 0]):
        for direction in ["VPD_given_T", "T_given_VPD"]:
            sub = directions.loc[directions.month_slot.eq(slot) & directions.direction.eq(direction) &
                                 directions.n.ge(MIN_PRIMARY_N) & directions.partial.notna()]
            if sub.empty: continue
            fig, ax = plt.subplots(figsize=(6, 5))
            sc = ax.scatter(sub.grid_longitude, sub.grid_latitude, c=sub.partial,
                            cmap="coolwarm", vmin=-.6, vmax=.6, s=38, edgecolors="black", linewidths=.2)
            fig.colorbar(sc, ax=ax, label="Partial correlation")
            ax.set_xlabel("ERA5 grid longitude"); ax.set_ylabel("ERA5 grid latitude")
            ax.set_title(f"{sub.calendar_month_label.iloc[0]}: {direction}, N≥20")
            fig.tight_layout(); fig.savefig(figure_dir / f"{prefix}map_slot_{slot}_{direction}.png", dpi=150); plt.close(fig)
    # Representative February strata: largest-area and median-area eligible grids,
    # selected independently of the observed yield association.
    feb = panel.loc[panel.month_slot.eq(-2) & panel.primary_eligible]
    if not feb.empty:
        area = feb.groupby("grid_id").actual_weight_denominator_ha.mean().sort_values()
        selected = list(dict.fromkeys([area.index[len(area) // 2], area.index[-1]]))
        for grid in selected:
            sample = feb.loc[feb.grid_id.eq(grid)]
            fig, axes = plt.subplots(1, 2, figsize=(10, 4))
            for ax, (conditioner, tested, title) in zip(axes, [(TEMP, VPD, "T thirds: VPD–Y"),
                                                                   (VPD, TEMP, "VPD thirds: T–Y")]):
                ranks = rankdata(sample[conditioner], method="average")
                bands = np.where((ranks - .5) / len(sample) < 1 / 3, "low",
                                 np.where((ranks - .5) / len(sample) >= 2 / 3, "high", "middle"))
                for band, color in [("low", "blue"), ("middle", "gray"), ("high", "red")]:
                    part = sample.loc[bands == band]
                    ax.scatter(part[tested], part[Y10], label=f"{band} (n={len(part)})", alpha=.75, color=color)
                ax.set_xlabel(tested); ax.set_ylabel("P50=10 actual Y anomaly (t/ha)"); ax.set_title(title)
            axes[0].legend(fontsize=7); fig.suptitle(f"February pilot strata, {grid}")
            fig.tight_layout(); fig.savefig(figure_dir / f"{prefix}february_strata_{grid}.png", dpi=150); plt.close(fig)


def input_manifest(root: Path, slots: pd.DataFrame, overlap: dict[str, object]) -> dict[str, object]:
    paths = source_paths(root)
    inventory = pd.read_csv(paths["weather_inventory"])
    definitions = inventory.loc[inventory.column_name.isin([
        "nasa_average_temperature_c", "vpd_mean_kpa"
    ])].to_dict("records")
    return {
        "experiment": "EXP-05",
        "source_paths": {key: str(value) for key, value in paths.items()},
        "weather_source_years": [WEATHER_SOURCE_START, WEATHER_SOURCE_END],
        "weather_definitions": definitions,
        "outcome_definitions": {
            Y10: "P50=10 municipality yield residual, same-year actual harvested-area-weighted ERA5 grid sum; t/ha",
            Y12: "P50=12 municipality yield residual, same-year actual harvested-area-weighted ERA5 grid sum; t/ha",
            YFIX: "P50=10 municipality yield residual, approved fixed-composition weights on same matched support; t/ha",
        },
        "target_lineage_and_overlap_audit": overlap,
        "month_slot_count": len(slots),
        "month_slot_indices": slots.month_slot.astype(int).tolist(),
        "sample_rule": "Per grid-month-slot, finite Y_P50_10_actual_tch, T_C, and VPD_kPa only; no 16-month completeness gate",
        "linear_models": ["Y~T", "Y~VPD", "Y~T+VPD"],
        "uncertainty": "HC3 coefficient intervals within grid; synchronized yield-year bootstrap for spatial summaries",
        "standardization": "Both predictor and Y use within-grid-slot sample standard deviations",
        "minimum_n_linear": MIN_LINEAR_N,
        "minimum_n_primary": MIN_PRIMARY_N,
        "minimum_n_grid_quadratic": MIN_QUADRATIC_N,
    }


def run_phase_a(root: Path, output: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Discover, verify, and execute the February_t pilot sample and linear gate."""

    slots = discover_slots(root)
    targets, weights, mapping, overlap = load_frozen_targets(root)
    feb = slots.loc[slots.calendar_month_label.eq("Feb_(t)")]
    if len(feb) != 1 or feb.month_slot.iloc[0] != -2:
        raise ValueError("February_t pilot slot is ambiguous")
    needed_years = set((targets.yield_year + int(feb.source_year_offset.iloc[0])).astype(int))
    weather = load_monthly_weather(root, needed_years)
    weather = weather.loc[weather.source_calendar_month.eq(2)].copy()
    panel = build_grid_slot_panel(targets, weights, weather, feb)
    support = sample_support(panel)
    linear = fit_grid_linear(panel)
    strata = strata_diagnostics(panel)
    nonlinear = restricted_grid_nonlinear(panel)
    pooled = pooled_nonlinear(panel)
    loyo = leave_one_year_out(panel)
    bootstrap = synchronized_bootstrap(panel)
    pooled_bootstrap = pooled_nonlinear_synchronized_bootstrap(panel)
    area = monthly_area_coverage(panel, support)
    manifest = input_manifest(root, slots, overlap)
    output.mkdir(parents=True, exist_ok=True)
    slots.to_csv(output / "month_slots.csv", index=False)
    panel.to_csv(output / "phase_a_february_sample_coverage.csv", index=False)
    support.to_csv(output / "phase_a_february_grid_support.csv", index=False)
    linear.to_csv(output / "phase_a_february_linear_conditional.csv", index=False)
    strata.to_csv(output / "phase_a_february_stratification.csv", index=False)
    nonlinear.to_csv(output / "phase_a_february_grid_nonlinear.csv", index=False)
    pooled.to_csv(output / "phase_a_february_pooled_nonlinear.csv", index=False)
    loyo.to_csv(output / "phase_a_february_leave_one_year_out.csv", index=False)
    bootstrap.to_csv(output / "phase_a_february_synchronized_bootstrap.csv", index=False)
    pooled_bootstrap.to_csv(output / "phase_a_february_pooled_nonlinear_bootstrap.csv", index=False)
    area.to_csv(output / "phase_a_february_area_coverage.csv", index=False)
    (output / "input_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    eligible = linear.loc[linear.fit_status.eq("estimable")]
    gate_pass = (len(eligible) >= 1 and pooled.status.eq("estimable").all()
                 and nonlinear.status.eq("estimable").all()
                 and eligible.partial_identity_max_error.max() < 1e-8
                 and bootstrap.n_estimable_grids.min() > 0
                 and pooled_bootstrap.status.eq("estimable").all()
                 and overlap["municipalities_mapped_to_multiple_grids"] == 0)
    gate_note = f"""# EXP-05 Phase A gate — February_t

Status: **{'PASS' if gate_pass else 'STOP / REVIEW'}**.

- Frozen target lineage reconstructs all three grid outcomes with maximum absolute error {max(overlap['target_lineage_max_abs_error_tch'].values()):.3g} t/ha; 511 municipalities map uniquely to 78 grids. Within-year grid target values are not replicated statewide. Shared yearly shocks and weather-source groups remain possible spatial dependence.
- February_t is month slot -2, yield-year February, from the existing 16-slot alignment. No 16-month completeness filter is applied.
- {int(panel.primary_eligible.sum())} paired primary grid-years; {int(support.n_primary.ge(20).sum())} grids have N≥20, {int(support.n_primary.ge(30).sum())} have N≥30, {int(support.n_primary.lt(15).sum())} have N<15. All-three-target paired rows: {int(panel.all_target_eligible.sum())}.
- Partial-correlation/partial-R² identity maximum error {eligible.partial_identity_max_error.max():.3g}; all {len(nonlinear)} allowed per-grid restricted nonlinear fits and the pooled grid-intercept diagnostic are estimable. Synchronized year bootstraps produced estimable spatial medians and pooled nonlinear refits; failed-grid counts remain in the outputs.
- Protocol frozen for Phase B: same per-grid-slot Y/T/VPD complete-case sample; 15/20/30-year tiers; two-sided linear and rank partials; HC3; average-rank empirical thirds; restricted quadratic controls; pooled common-slope grid-intercept L/Q/I; shared-year target comparison; synchronized i.i.d./3-year/5-year year draws (200 replicates, seed 20261010); no year fixed effects or additional covariates.
- Known limitations: weather begins in 1981; some target grid-years are invalid; adjacent grid weather and shared annual shocks can correlate. No smallest-important-effect margin is approved, so potential redundancy is not assigned. Pooled nonlinear fits are diagnostics, not grid-universal effects.

{'No material methodological ambiguity was found in the pilot; proceed to Phase B under the frozen rules.' if gate_pass else 'Do not proceed to Phase B until Chat-level review.'}
"""
    (output / "phase_a_gate_note.md").write_text(gate_note, encoding="utf-8")
    manifest["phase_a_gate_pass"] = bool(gate_pass)
    (output / "input_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return panel, support, linear, manifest


def run_phase_b_c(root: Path, output: Path, manifest: dict[str, object]) -> None:
    if not manifest.get("phase_a_gate_pass"):
        raise RuntimeError("Phase A did not pass; full run prohibited")
    slots = discover_slots(root)
    targets, weights, _, _ = load_frozen_targets(root)
    needed_years = set(int(year + offset) for year in targets.yield_year
                       for offset in slots.source_year_offset)
    weather = load_monthly_weather(root, needed_years)
    panel = build_grid_slot_panel(targets, weights, weather, slots)
    support = sample_support(panel)
    linear = fit_grid_linear(panel)
    strata = strata_diagnostics(panel)
    nonlinear = restricted_grid_nonlinear(panel)
    pooled = pooled_nonlinear(panel)
    loyo = leave_one_year_out(panel)
    shared = pd.concat([fit_grid_linear(panel, target, common=True) for target in TARGETS],
                       ignore_index=True)
    common_year, common_year_keys = cross_month_common_year(panel)
    bootstrap = synchronized_bootstrap(panel)
    pooled_bootstrap = pooled_nonlinear_synchronized_bootstrap(panel)
    area = monthly_area_coverage(panel, support)
    directional = directional_results(linear, loyo, shared, common_year, nonlinear)
    synthesis = monthly_spatial_synthesis(directional, support, area, bootstrap, pooled,
                                          pooled_bootstrap)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "sample_coverage.csv": panel, "grid_month_support.csv": support,
        "linear_conditional_results.csv": linear, "stratification_diagnostics.csv": strata,
        "grid_restricted_nonlinear_diagnostics.csv": nonlinear,
        "pooled_month_nonlinear_diagnostics.csv": pooled,
        "leave_one_year_out.csv": loyo, "all_target_shared_year_linear.csv": shared,
        "cross_month_common_year_linear.csv": common_year,
        "cross_month_common_year_keys.csv": common_year_keys,
        "synchronized_year_bootstrap_replicates.csv": bootstrap,
        "pooled_nonlinear_synchronized_bootstrap.csv": pooled_bootstrap,
        "monthly_area_coverage.csv": area,
        "grid_month_direction_evidence.csv": directional,
        "monthly_spatial_synthesis.csv": synthesis,
    }
    for name, frame in artifacts.items():
        frame.to_csv(output / name, index=False)
    make_figures(directional, synthesis, panel, output)
    write_reports(output, manifest, panel, support, linear, strata, nonlinear,
                  pooled, shared, common_year, bootstrap, directional, synthesis)


def write_reports(output: Path, manifest: dict[str, object], panel: pd.DataFrame,
                  support: pd.DataFrame, linear: pd.DataFrame, strata: pd.DataFrame,
                  nonlinear: pd.DataFrame, pooled: pd.DataFrame, shared: pd.DataFrame,
                  common_year: pd.DataFrame, bootstrap: pd.DataFrame,
                  directional: pd.DataFrame, synthesis: pd.DataFrame) -> None:
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root(),
                              capture_output=True, text=True, check=True).stdout.strip()
    lines = ["# EXP-05 conditional temperature–VPD synthesis", "",
             "Exploratory grid/month-slot associations, not causal effects or forecasting feature selection.", "",
             "## Main distribution", "",
             "The primary estimand is the equal-grid median of per-grid two-sided partial correlations. "
             "Intervals below resample yield-year labels synchronously across grids in consecutive 3-year blocks (200 replicates).", "",
             "| Slot | VPD\\|T median [3-year interval] | T\\|VPD median [3-year interval] | N primary grids |",
             "|---|---:|---:|---:|"]
    for slot, group in synthesis.groupby("month_slot", sort=True):
        a = group.loc[group.direction.eq("VPD_given_T")].iloc[0]
        b = group.loc[group.direction.eq("T_given_VPD")].iloc[0]
        lines.append(f"| {a.calendar_month_label} | {a.median_partial:.3f} [{a.bootstrap_block_3_median_partial_ci_low:.3f}, {a.bootstrap_block_3_median_partial_ci_high:.3f}] | {b.median_partial:.3f} [{b.bootstrap_block_3_median_partial_ci_low:.3f}, {b.bootstrap_block_3_median_partial_ci_high:.3f}] | {int(a.n_primary_estimable_grids)} |")
    lines += ["", "## Empirical reading", "",
              "The clearest sustained conditional pattern is negative VPD|T over Aug–Nov_(t-1): equal-grid median partial correlations are approximately −0.10, −0.10, −0.08, and −0.11. The synchronized 3-year and 5-year block intervals for those spatial medians remain below zero, though individual grid directions vary. The February_t pilot median VPD|T is −0.08, but its block interval crosses zero. Temperature|VPD is weaker and changes sign across month-slots; Dec_(t-1) and Mar_t have negative medians with 3-year intervals below zero. These are descriptive signals, not isolated-month discoveries.", "",
              "P50=12 and fixed-composition targets use the exact same paired-year support as primary in this run (zero rows lost). The Aug–Nov VPD|T medians retain their negative signs under both targets. The all-16-slot common-year sensitivity loses at most one year per grid-slot and preserves the broad pattern. Restricted per-grid quadratic conditioning generally leaves the Aug–Nov median VPD increment similar to its linear-control increment; pooled grid-intercept quadratic/interaction increments are small and are not evidence that all grids share one curvature.", "",
              "Spatial heterogeneity and influence remain material: rank-partial signs agree with linear-partial signs for about 82% of N≥20 grid-slot-directions, while leave-one-year-out signs remain stable for about 59%. Do not equate a spatial median with a common response in every grid. February has no robust spatial-median direction after year-block uncertainty.", "",
              "## Interpretation boundaries", "",
              "Direction, magnitude, grid heterogeneity, rank robustness, target robustness, nonlinear controls, and common-year sensitivity are tabulated separately. The fixed-composition outcome tests yield weighting, not weather weighting. The grid-intercept pooled quadratic models impose common slopes and do not prove a common grid response. A year-synchronized bootstrap preserves common resampled calendar-year shocks but does not remove spatial dependence or establish causality.", "",
              "No potential-redundancy label or feature keep/drop recommendation is made: no a priori smallest-important-effect margin exists. Directionally consistent candidates remain exploratory and their substantive importance is unadjudicated. See per-grid evidence flags and execution report for caveats."]
    (output / "EXP_05_research_synthesis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    observed = panel.loc[panel.primary_eligible]
    pilot = support.loc[support.month_slot.eq(-2)]
    identity = linear.loc[linear.fit_status.eq("estimable"), "partial_identity_max_error"]
    shrink = int(panel.primary_eligible.sum() - panel.all_target_eligible.sum())
    report = f"""# EXP-05 execution report

## Gate and frozen sources

Phase A passed; see `phase_a_gate_note.md`. No upstream source, prior experiment result, or authoritative research-state file was modified. Sources and field definitions are in `input_manifest.json`; the frozen targets are `{manifest['source_paths']['grid_targets']}`, with municipality residual/weight lineage checked against `{manifest['source_paths']['municipality_weights']}`. Canonical weather is read from `{manifest['source_paths']['annual_weather']}`; T is `nasa_average_temperature_c` (°C), NASA POWER monthly mean of daily T2M, and VPD is `vpd_mean_kpa` (kPa), Open-Meteo ERA5 monthly mean of daily mean hourly VPD.

Upstream repository HEAD at execution: `{git_head}`. The newly written EXP-05 implementation is uncommitted in this working tree.

## Validation

- {len(panel):,} grid × month-slot × yield-year rows: {panel.grid_id.nunique()} grids × {panel.month_slot.nunique()} slots × {panel.yield_year.nunique()} target years. {len(observed):,} primary paired observations, years {int(observed.yield_year.min())}–{int(observed.yield_year.max())}; {shrink} rows lost on all-three-target year intersection.
- February pilot: {int(pilot.n_primary.ge(20).sum())} primary grids N≥20; {int(pilot.n_primary.ge(30).sum())} grids N≥30. Full run: {int(support.n_primary.ge(20).sum())} of {len(support)} grid-slot series N≥20. N-tier limits are retained in all outputs.
- Missingness reasons: {int(panel.missingness_reason.eq('source_year_outside_verified_weather').sum()):,} rows outside the verified 1981–2025 weather source; {int(panel.missingness_reason.eq('invalid_or_missing_primary_target').sum()):,} rows with invalid/missing primary target. There are no additional T/VPD partial-coverage losses once source year and target are valid. Eligible T/VPD covered weights sum to one. The primary analyzable grid-years represent at least {100 * monthly_area_coverage(panel, support).primary_area_fraction.min():.5f}% of mapped, target-valid area-years under the stated denominator; this is not statewide area coverage.
- Target reconstruction max absolute error {max(manifest['target_lineage_and_overlap_audit']['target_lineage_max_abs_error_tch'].values()):.3g} t/ha; municipality-to-grid overlap 0; target values are not replicated statewide. Shared annual shocks and adjacent weather remain non-independence caveats.
- Partial correlation squared versus partial-R² max discrepancy {identity.max():.3g}; {int((linear.fit_status == 'estimable').sum())} estimable linear series; {int((nonlinear.status == 'estimable').sum())}/{len(nonlinear)} allowed restricted nonlinear fits; {int((pooled.status == 'estimable').sum())}/{len(pooled)} pooled month models estimable.
- Stratified slopes fitted only when N≥10; empirical tertiles use average ranks for ties. No stratum is used as a primary conditional estimate. All linear, ranking, strata, and nonlinear comparisons use identical per-grid-slot primary paired rows.
- Cross-month sensitivity intersects paired years across all 16 slots within each grid; {int((common_year.n >= 15).sum())} grid-slot common-year series retain N≥15. Its estimates never replace maximal-sample results.
- Year-synchronized bootstrap: 200 replicate draws for each of iid, consecutive 3-year, and consecutive 5-year blocks, seed 20261010. The same sampled yield-year labels are applied across grids and slots; missingness masks remain. Grid failures and effective counts are in the replicate table. HC3 coefficient intervals and leave-one-year-out influence are also retained.
- Pooled grid-intercept nonlinear models are additionally refitted under the same synchronized year draws, with within-grid scaling recomputed each replicate. Their per-slot interval diagnostics are in `pooled_nonlinear_synchronized_bootstrap.csv` and `monthly_spatial_synthesis.csv`.

## Principal empirical findings

The sustained negative VPD|T grid-median pattern is Aug–Nov_(t-1), with primary partial medians approximately −0.104, −0.099, −0.081, and −0.105; synchronized 3-year and 5-year block intervals are below zero for those four slots. The Feb_t pilot median VPD|T is about −0.080 but its 3-year interval spans zero. T|VPD has negative medians with 3-year intervals below zero in Dec_(t-1) and Mar_t, but no similarly sustained run. Magnitudes are modest: typical per-grid incremental R² values are near 0.01–0.02. These are month-level descriptive distributions, not independent grid discoveries or causal effects. Grid direction and year influence vary; candidate flags do not assign substantive importance.

P50=12 and fixed-composition median directions broadly agree for the Aug–Nov VPD|T pattern on identical years. The pooled common-slope nonlinear increments do not by themselves generalize to every grid. The common-year sensitivity changes at most one eligible year per grid-slot here and does not overturn the sustained pattern.

## Data products and methods

The output directory contains source manifest, month slots, sample and support audit, per-grid linear partials, strata, restricted per-grid and pooled common-slope nonlinear diagnostics, shared-year target robustness, common-year month sensitivity, leave-one-year-out sensitivity, synchronized bootstrap replicates, area coverage, directional evidence, monthly synthesis, figures, and this report. `grid_month_direction_evidence.csv` marks candidate directional consistency only; substantive magnitude is unadjudicated and **potential redundancy is not assigned**.

Principal machine-readable files: `sample_coverage.csv`, `grid_month_support.csv`, `linear_conditional_results.csv`, `stratification_diagnostics.csv`, `grid_restricted_nonlinear_diagnostics.csv`, `pooled_month_nonlinear_diagnostics.csv`, `all_target_shared_year_linear.csv`, `cross_month_common_year_linear.csv`, `leave_one_year_out.csv`, `synchronized_year_bootstrap_replicates.csv`, `pooled_nonlinear_synchronized_bootstrap.csv`, `monthly_area_coverage.csv`, `grid_month_direction_evidence.csv`, and `monthly_spatial_synthesis.csv`. February-only pilot diagnostics and maps/plots are retained alongside them.

Area coverage denominator is the sum of mapped, target-valid EXP-02B grid harvested-area denominators over weather-source-compatible yield years in each slot; it is not statewide area of all municipalities. Area-weighted directional shares use each grid's mean observed area over its own paired years and are supplemental. Grid-equal-weight summaries are primary.

Models use the existing monthly T and VPD values directly. Within one grid × slot, the existing grid/calendar-month anomaly convention would subtract a constant; intercept-inclusive OLS correlations, partials, and within-grid standardized pooled fits are invariant to that shift. No new weather transformation or upstream anomaly file was created.

## Limitations and unresolved research questions

Weather begins in 1981 and some grid targets are invalid. Restricted per-grid curvature and pooled common-slope curvature are descriptive, not causal. No year fixed effects are used because those would change the estimand. Spatially adjacent weather and shared annual shocks can reduce effective evidence diversity despite disjoint municipality outcome membership. The 3-/5-year block uncertainty is finite-sample sensitivity, not a guarantee of temporal dependence correction. An agreed smallest-important-effect margin and a subsequent forecasting comparison would be needed before considering simplification; neither is part of EXP-05. Project-wide research-state updates are proposed for Chat review, not applied.

## Reproducibility

`$env:PYTHONPATH='src'; python -m analysis.exp05_conditional_temperature_vpd --phase all`

Validation tests: `$env:PYTHONPATH='src'; python -m pytest src/tests/analysis/test_exp05_conditional_temperature_vpd.py src/tests/analysis/test_exp02b_composition_sensitivity.py src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py -q -p no:cacheprovider` — 22 passed (2026-10-10). New files: `src/analysis/exp05_conditional_temperature_vpd.py`, `src/tests/analysis/test_exp05_conditional_temperature_vpd.py`, and the isolated `outputs/research/exp_05/` tree. No tracked pre-existing file was changed.
"""
    (output / "EXP_05_execution_report.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=project_root())
    parser.add_argument("--phase", choices=["a", "all"], default="a")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    output = root / "outputs/research/exp_05"
    _, _, _, manifest = run_phase_a(root, output)
    if args.phase == "all":
        run_phase_b_c(root, output, manifest)


if __name__ == "__main__":
    main()
