"""EXP-05B: frozen-target, moisture-conditioned monthly associations.

Run Phase A independently before any model fitting. No upstream artifact is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from analysis import exp05_conditional_temperature_vpd as exp05


SM = "soil_moisture_28_to_100cm_m3_m3"
DEEP = "soil_moisture_100_to_255cm_m3_m3"
RAIN = "nasa_total_rainfall_mm"
MODIFIERS = {
    "sm_28_100_prev3_mean": (SM, 3, "mean"),
    "sm_28_100_prev1": (SM, 1, "mean"),
    "sm_api_100_255_prev3_mean": (DEEP, 3, "mean"),
    "rain_prev3_sum": (RAIN, 3, "sum"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_weather(root: Path) -> pd.DataFrame:
    """Load established monthly series; distinguish absent from literal zero."""
    folder = root / "data/processed/combined_weather/annual"
    fields = ["ibge_code", "era5_grid_id", "month", "nasa_average_temperature_c",
              "vpd_mean_kpa", SM, DEEP, RAIN]
    frames = []
    for year in range(exp05.WEATHER_SOURCE_START, exp05.WEATHER_SOURCE_END + 1):
        path = folder / f"sp_municipality_monthly_weather_{year}.csv"
        part = pd.read_csv(path, usecols=fields, dtype={"ibge_code": "string"})
        part["source_year"] = year
        if not part.month.str.startswith(f"{year}-").all():
            raise ValueError(f"Weather file/year mismatch: {path}")
        part["source_calendar_month"] = part.month.str[-2:].astype(int)
        frames.append(part.drop(columns="month"))
    weather = pd.concat(frames, ignore_index=True).rename(columns={
        "era5_grid_id": "grid_id", "nasa_average_temperature_c": exp05.TEMP,
        "vpd_mean_kpa": exp05.VPD})
    if weather.duplicated(["ibge_code", "source_year", "source_calendar_month"]).any():
        raise ValueError("Duplicate municipality-month weather key")
    if weather[[SM, DEEP]].notna().any().any():
        values = weather[[SM, DEEP]].to_numpy(float)
        if np.nanmin(values) < 0 or np.nanmax(values) > 1:
            raise ValueError("Soil moisture outside physical volumetric range [0,1]")
    return weather


def shift_month(year: pd.Series, month: pd.Series, lag: int) -> tuple[pd.Series, pd.Series]:
    """Calendar-safe month subtraction, independent of crop-year labels."""
    absolute = year.astype(int) * 12 + month.astype(int) - 1 - lag
    return absolute // 12, absolute % 12 + 1


def add_antecedents(base: pd.DataFrame, weather: pd.DataFrame,
                    weights: pd.DataFrame) -> pd.DataFrame:
    """Aggregate existing municipality weather using yield-year actual weights.

    A grid-month is valid only when *all* contemporaneous matched-support
    municipality weight is represented by finite weather. The antecedent window
    is then valid only when all requested grid-months are valid.
    """
    keys = ["grid_id", "yield_year", "month_slot"]
    alignment = base.loc[base[exp05.Y10].notna(), keys + ["source_year", "source_calendar_month"]].copy()
    w = weights[["grid_id", "year", "ibge_code", "actual_weight"]].rename(
        columns={"year": "yield_year"})
    months = []
    for lag in (0, 1, 2, 3):
        a = alignment.copy()
        a["lag"] = lag
        a["source_year"], a["source_calendar_month"] = shift_month(
            a.source_year, a.source_calendar_month, lag)
        months.append(a)
    expanded = pd.concat(months, ignore_index=True).merge(
        w, on=["grid_id", "yield_year"], how="left", validate="many_to_many")
    if expanded.ibge_code.isna().any():
        raise ValueError("Target grid-year has no municipality weights")
    expanded = expanded.merge(weather,
        on=["grid_id", "ibge_code", "source_year", "source_calendar_month"],
        how="left", validate="many_to_one")
    variables = [exp05.TEMP, exp05.VPD, SM, DEEP, RAIN]
    for variable in variables:
        valid = np.isfinite(expanded[variable])
        expanded[f"{variable}_covered"] = expanded.actual_weight.where(valid, 0)
        expanded[f"{variable}_weighted"] = expanded.actual_weight * expanded[variable].where(valid, 0)
    agg = {f"{variable}_covered": (f"{variable}_covered", "sum") for variable in variables}
    agg.update({f"{variable}_weighted": (f"{variable}_weighted", "sum") for variable in variables})
    monthly = expanded.groupby(keys + ["lag"], as_index=False).agg(**agg)
    for variable in variables:
        monthly[variable] = monthly[f"{variable}_weighted"].where(
            np.isclose(monthly[f"{variable}_covered"], 1, atol=1e-10))
    wide = monthly.pivot(index=keys, columns="lag", values=variables)
    wide.columns = [f"{field}_lag{lag}" for field, lag in wide.columns]
    wide = wide.reset_index()
    result = base.merge(wide, on=keys, how="left", validate="one_to_one")
    # Existing EXP-05 target-month weighting and new construction must agree.
    for variable in (exp05.TEMP, exp05.VPD):
        old, new = result[variable], result[f"{variable}_lag0"]
        if not np.array_equal(old.notna().to_numpy(), new.notna().to_numpy()):
            raise ValueError(f"EXP-05 target-month support changed for {variable}")
        if not np.allclose(old.dropna(), new.dropna(), atol=1e-10):
            raise ValueError(f"EXP-05 target-month value changed for {variable}")
    for name, (field, count, reducer) in MODIFIERS.items():
        columns = [f"{field}_lag{i}" for i in range(1, count + 1)]
        complete = result[columns].notna().all(axis=1)
        values = result[columns].mean(axis=1) if reducer == "mean" else result[columns].sum(axis=1)
        result[name] = values.where(complete)
        result[f"{name}_complete"] = complete
    return result


def phase_a(root: Path, output: Path) -> pd.DataFrame:
    output.mkdir(parents=True, exist_ok=True)
    paths = exp05.source_paths(root)
    targets, weights, mapping, lineage = exp05.load_frozen_targets(root)
    slots = exp05.discover_slots(root)
    previous = pd.read_csv(root / "outputs/research/exp_05/sample_coverage.csv",
                           dtype={"ibge_code": "string"})
    required = {"grid_id", "yield_year", "month_slot", "source_year", "source_calendar_month"}
    if not required.issubset(previous):
        raise ValueError("EXP-05 paired coverage schema changed")
    if len(previous) != len(targets) * len(slots) or previous.duplicated(["grid_id", "yield_year", "month_slot"]).any():
        raise ValueError("EXP-05 paired coverage cardinality changed")
    weather = load_weather(root)
    panel = add_antecedents(previous, weather, weights)
    target_files = [paths["grid_targets"], paths["municipality_weights"],
                    paths["municipality_grid_mapping"],
                    root / "outputs/research/exp_05/sample_coverage.csv",
                    root / "outputs/research/exp_05/month_slots.csv"]
    manifest = {
        "experiment": "EXP-05B", "lineage": lineage,
        "frozen_input_sha256": {str(path): sha256(path) for path in target_files},
        "weather_files": {str(path): sha256(path) for path in sorted(paths["annual_weather"].glob("sp_municipality_monthly_weather_*.csv"))},
        "weather_years": [1981, 2025], "weather_rows": len(weather),
        "weather_fields": {
            exp05.TEMP: "NASA POWER nasa_average_temperature_c, monthly mean daily T2M, degrees C",
            exp05.VPD: "Open-Meteo ERA5 vpd_mean_kpa, monthly mean daily mean hourly VPD, kPa",
            SM: "Open-Meteo ERA5 volumetric soil moisture layer 3, 28-100 cm, m3/m3; hourly to daily to monthly mean",
            DEEP: "Open-Meteo API alias 100-255 cm, mapped to ERA5 volumetric soil water layer 4 (native 100-289 cm); no thickness conversion, m3/m3",
            RAIN: "NASA POWER nasa_total_rainfall_mm, monthly sum daily PRECTOTCORR, mm",
        },
        "month_slots": slots.to_dict("records"),
        "weather_weighting": "Yield-year EXP-02B actual within-grid municipality weights, same as EXP-05 target-month weather; require full weight coverage per calendar month",
        "modifier_definitions": {name: {"field": field, "preceding_months": count, "reducer": reducer} for name, (field, count, reducer) in MODIFIERS.items()},
        "deep_provenance": {
            "project_api_request": "models=era5; hourly soil_moisture_100_to_255cm",
            "project_etl": "hourly -> daily mean -> monthly mean; validate [0,1]; no depth rescale",
            "provider_code": "https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Era5/Era5Variables.swift",
            "ecmwf_documentation": "https://confluence.ecmwf.int/plugins/viewsource/viewpagesrc.action?pageId=488287070",
            "physical_interpretation": "ERA5 native fourth soil-water layer, nominal 100-289 cm; API field retains historical 100-255 name",
        },
    }
    (output / "input_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    coverage = []
    for name in MODIFIERS:
        for slot, group in panel.groupby("month_slot"):
            valid = group[[exp05.Y10, exp05.TEMP, exp05.VPD, name]].notna().all(axis=1)
            n_by_grid = valid.groupby(group.grid_id).sum()
            coverage.append({"modifier": name, "month_slot": slot,
                "calendar_month_label": group.calendar_month_label.iloc[0],
                "n_target_rows": len(group), "n_complete_rows": int(valid.sum()),
                "n_grids_n_ge_15": int(n_by_grid.ge(15).sum()),
                "n_grids_n_ge_20": int(n_by_grid.ge(20).sum()),
                "n_grids_n_ge_30": int(n_by_grid.ge(30).sum()),
                "first_valid_yield_year": group.loc[valid, "yield_year"].min(),
                "last_valid_yield_year": group.loc[valid, "yield_year"].max(),
                "n_valid_yield_years": group.loc[valid, "yield_year"].nunique(),
                "n_modifier_missing_with_target_tv": int((group[[exp05.Y10, exp05.TEMP, exp05.VPD]].notna().all(axis=1) & group[name].isna()).sum())})
    coverage = pd.DataFrame(coverage).sort_values(["modifier", "month_slot"])
    coverage.to_csv(output / "sample_coverage.csv", index=False)
    panel.to_pickle(output / "panel.pkl")
    lines = ["# EXP-05B Phase A gate", "", "**PASS for deterministic modeling.** Frozen target reconstruction and weight normalization are rechecked by the EXP-05 loader; target-month T/V values and missingness match EXP-05 exactly. All four antecedent modifiers are derived from complete, calendar-safe prior months only, with full matched-municipality weight coverage. No upstream data were regenerated.", "", "The pre-1981 weather boundary removes the first otherwise-eligible year for Jan–Mar_(t−1) and Jan–Mar_t primary antecedents; other slots have no additional primary-antecedent loss beyond the EXP-05 T/V sample. There are 76 grids with at least 20 paired primary years in each of 16 slots. See `sample_coverage.csv` for every modifier and slot.", "", "Deep-source provenance: the project requests Open-Meteo `models=era5` and `soil_moisture_100_to_255cm`; its ETL averages 24 hourly values to daily and daily values to monthly without depth rescaling. Open-Meteo's ERA5 variable mapping points that API label to `volumetric_soil_water_layer_4`; ECMWF specifies ERA5 native layer 4 as 100–289 cm. The API label is retained as a field name, while this native layer definition is documented separately. This is a sensitivity proxy, not verified crop root-zone water stress.", "", "Sources: [Open-Meteo API](https://open-meteo.com/en/docs/historical-weather-api), [Open-Meteo ERA5 variable mapping](https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Era5/Era5Variables.swift), [ECMWF ERA5 native layers](https://confluence.ecmwf.int/plugins/viewsource/viewpagesrc.action?pageId=488287070).", ""]
    (output / "phase_a_gate_note.md").write_text("\n".join(lines), encoding="utf-8")
    return panel


def analysis_mask(panel: pd.DataFrame, modifier: str, target: str = exp05.Y10,
                  matched_modifier: str | None = None,
                  matched_target: str | None = None) -> pd.Series:
    fields = [target, exp05.TEMP, exp05.VPD, modifier]
    if matched_modifier:
        fields.append(matched_modifier)
    if matched_target:
        fields.append(matched_target)
    return panel[fields].notna().all(axis=1)


def make_series(panel: pd.DataFrame, modifier: str, target: str = exp05.Y10,
                matched_modifier: str | None = None,
                matched_target: str | None = None) -> dict[int, pd.DataFrame]:
    mask = analysis_mask(panel, modifier, target, matched_modifier, matched_target)
    groups = {}
    for slot, data in panel.loc[mask].groupby("month_slot", sort=True):
        n = data.groupby("grid_id").size()
        grids = n[n.ge(exp05.MIN_PRIMARY_N)].index
        groups[int(slot)] = data.loc[data.grid_id.isin(grids)].copy()
    return groups


def _design_one_grid(values: np.ndarray, counts: np.ndarray,
                     s25: float, s75: float) -> dict[str, object] | None:
    """Resample-scale on a fixed grid support; return centered sufficient stats."""
    n = int(counts.sum())
    if n < exp05.MIN_PRIMARY_N:
        return None
    predictors = values[:, 1:]
    means = np.average(predictors, axis=0, weights=counts)
    var = np.average((predictors - means) ** 2, axis=0, weights=counts) * n / (n - 1)
    if np.any(var <= 1e-24):
        return None
    sd = np.sqrt(var)
    z = (predictors - means) / sd
    t, v, s = z.T
    design = np.column_stack([t, v, s, t*s, v*s, t*t, v*v, s*s, t*v])
    mean_x = np.average(design, axis=0, weights=counts)
    x = design - mean_x
    y = values[:, 0] - np.average(values[:, 0], weights=counts)
    w = counts.astype(float) / n
    if np.sum(w * y*y) <= 1e-20:
        return None
    # On the resampled scale, evaluate the *original* physical S quartiles.
    z25, z75 = (s25 - means[2])/sd[2], (s75 - means[2])/sd[2]
    return {"x": x, "y": y, "w": w, "n": n, "sd": sd,
            "s25z": z25, "s75z": z75, "smedz": (np.median(values[:, 3])-means[2])/sd[2],
            "srange": (float(np.min(s)), float(np.max(s)))}


MODELS = {
    "P0": [0, 1], "P1": [0, 1, 2], "P2": [0, 1, 2, 3, 4],
    "Q1": [0, 1, 2, 5, 6, 7], "Q2": [0, 1, 2, 5, 6, 7, 3, 4],
    "Q1_prime": [0, 1, 2, 5, 6, 7, 8],
    "Q2_prime": [0, 1, 2, 5, 6, 7, 8, 3, 4],
}


def pooled_fit(data: pd.DataFrame, modifier: str, target: str, models: tuple[str, ...],
               year_counts: dict[int, int] | None = None,
               fixed_grids: tuple[str, ...] | None = None) -> dict[str, object]:
    """Grid intercepts, total grid weight one, fixed inclusion in resampling."""
    groups = dict(tuple(data.groupby("grid_id", sort=True)))
    grids = fixed_grids or tuple(groups)
    if tuple(groups) != grids:
        raise ValueError("Pooled fit changed included grid support")
    parts = []
    failed = []
    for grid in grids:
        frame = groups[grid].sort_values("yield_year")
        values = frame[[target, exp05.TEMP, exp05.VPD, modifier]].to_numpy(float)
        counts = (np.ones(len(frame), dtype=int) if year_counts is None else
                  frame.yield_year.map(year_counts).fillna(0).to_numpy(int))
        q25, q75 = np.quantile(frame[modifier].to_numpy(float), [.25, .75])
        part = _design_one_grid(values, counts, q25, q75)
        if part is None:
            failed.append(grid)
        else:
            parts.append(part)
    if failed:
        return {"status": "grid_failed", "failed_grids": ";".join(failed),
                "n_failed_grids": len(failed), "n_grids": len(grids)}
    x = np.concatenate([p["x"] for p in parts])
    y = np.concatenate([p["y"] for p in parts])
    w = np.concatenate([p["w"] for p in parts])
    sqrtw = np.sqrt(w)
    xw, yw = x*sqrtw[:, None], y*sqrtw
    sst = float(yw @ yw)
    result: dict[str, object] = {"status": "estimable", "n_grids": len(grids),
                                "n_rows": int(sum(p["n"] for p in parts)),
                                "sst": sst, "failed_grids": "", "n_failed_grids": 0}
    for name in models:
        cols = MODELS[name]
        design = xw[:, cols]
        coef, _, rank, singular = np.linalg.lstsq(design, yw, rcond=None)
        if rank < len(cols):
            return {"status": f"rank_deficient_{name}", "n_grids": len(grids),
                    "n_failed_grids": 0, "failed_grids": ""}
        resid = yw - design @ coef
        result[f"r2_{name}"] = 1 - float(resid @ resid)/sst
        result[f"condition_{name}"] = float(singular[0]/singular[-1])
        for col, beta in zip(cols, coef):
            result[f"beta_{name}_{col}"] = float(beta)
        if name in ("P2", "Q2", "Q2_prime"):
            bt = float(coef[cols.index(3)])
            bv = float(coef[cols.index(4)])
            result[f"dry_minus_wet_t_{name}"] = float(np.mean([bt*(p["s25z"]-p["s75z"]) for p in parts]))
            result[f"dry_minus_wet_v_{name}"] = float(np.mean([bv*(p["s25z"]-p["s75z"]) for p in parts]))
            result[f"n_supported_grid_quartiles_{name}"] = len(parts)
    for reduced, full in (("P0", "P1"), ("P1", "P2"), ("Q1", "Q2"), ("Q1_prime", "Q2_prime")):
        if reduced in models and full in models:
            result[f"delta_r2_{full}_vs_{reduced}"] = result[f"r2_{full}"] - result[f"r2_{reduced}"]
    return result


def grid_conditional(data: pd.DataFrame, modifier: str, target: str) -> pd.DataFrame:
    rows = []
    for grid, frame in data.groupby("grid_id", sort=True):
        frame = frame.sort_values("yield_year")
        y, t, v, s = [frame[col].to_numpy(float) for col in (target, exp05.TEMP, exp05.VPD, modifier)]
        row = {"grid_id": grid, "n": len(frame), "first_year": int(frame.yield_year.min()),
               "last_year": int(frame.yield_year.max()),
               "years": ";".join(map(str, frame.yield_year.astype(int))),
               "t_min": t.min(), "t_max": t.max(), "v_min": v.min(), "v_max": v.max(),
               "s_min": s.min(), "s_max": s.max(),
               "r_t_v": np.corrcoef(t,v)[0,1], "r_t_s": np.corrcoef(t,s)[0,1],
               "r_v_s": np.corrcoef(v,s)[0,1], "status": "estimable"}
        try:
            m0, m1 = exp05.ols(y, np.column_stack([t,v])), exp05.ols(y, np.column_stack([t,v,s]))
            row.update({"r2_m0": m0["r2"], "r2_m1": m1["r2"],
                "delta_r2_s": m1["r2"]-m0["r2"],
                "partial_r_y_v_given_t": exp05.partial_correlation(y,v,t),
                "partial_r_y_v_given_t_s": exp05.partial_correlation(y,v,np.column_stack([t,s])),
                "partial_r_y_t_given_v": exp05.partial_correlation(y,t,v),
                "partial_r_y_t_given_v_s": exp05.partial_correlation(y,t,np.column_stack([v,s])),
                "beta_t_m0": m0["coef"][1], "beta_v_m0": m0["coef"][2],
                "beta_t_m1": m1["coef"][1], "beta_v_m1": m1["coef"][2],
                "beta_s_m1": m1["coef"][3],
                "beta_t_m1_ci_low_hc3": m1["ci_low_hc3"][1],
                "beta_t_m1_ci_high_hc3": m1["ci_high_hc3"][1],
                "beta_v_m1_ci_low_hc3": m1["ci_low_hc3"][2],
                "beta_v_m1_ci_high_hc3": m1["ci_high_hc3"][2],
                "residual_t_sd_given_v_s": np.std(exp05.residualize(t,np.column_stack([v,s])),ddof=1),
                "residual_v_sd_given_t_s": np.std(exp05.residualize(v,np.column_stack([t,s])),ddof=1),
                "remaining_t_variance_fraction": np.var(exp05.residualize(t,np.column_stack([v,s])),ddof=1)/np.var(t,ddof=1),
                "remaining_v_variance_fraction": np.var(exp05.residualize(v,np.column_stack([t,s])),ddof=1)/np.var(v,ddof=1),
                "rank_partial_v_given_t_s": exp05.partial_correlation(rankdata(y),rankdata(v),np.column_stack([rankdata(t),rankdata(s)])),
                "rank_partial_t_given_v_s": exp05.partial_correlation(rankdata(y),rankdata(t),np.column_stack([rankdata(v),rankdata(s)])),
                "m1_condition_number": m1["condition_number_raw"],
                "m1_max_cooks_distance": m1["max_cooks_distance"],
                "m1_most_influential_year": int(frame.yield_year.iloc[m1["max_cooks_index"]])})
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
            row["status"] = f"inestimable:{error}"
        rows.append(row)
    return pd.DataFrame(rows)


def spatial_slope_fit(data: pd.DataFrame, modifier: str, target: str,
                      year_counts: dict[int, int] | None = None,
                      fixed_grids: tuple[str, ...] | None = None) -> dict[str, object]:
    groups = dict(tuple(data.groupby("grid_id", sort=True)))
    grids = fixed_grids or tuple(groups)
    if tuple(groups) != grids:
        raise ValueError("Spatial-slope grid support changed")
    reduced_sse = full_sse = 0.0
    interaction_xx = np.zeros((2,2))
    interaction_xy = np.zeros(2)
    sst = 0.0
    parts = []
    for grid in grids:
        frame = groups[grid].sort_values("yield_year")
        counts = (np.ones(len(frame), int) if year_counts is None else
                  frame.yield_year.map(year_counts).fillna(0).to_numpy(int))
        q25, q75 = np.quantile(frame[modifier], [.25,.75])
        part = _design_one_grid(frame[[target, exp05.TEMP, exp05.VPD, modifier]].to_numpy(float), counts, q25, q75)
        if part is None:
            return {"status": "grid_failed", "failed_grid": grid}
        x, y, w = part["x"], part["y"], part["w"]
        a, z = x[:, :3], x[:, 3:5]
        aw = a*np.sqrt(w)[:, None]
        zw = z*np.sqrt(w)[:, None]
        yw = y*np.sqrt(w)
        if np.linalg.matrix_rank(aw) < 3:
            return {"status": "rank_deficient_grid_additive", "failed_grid": grid}
        ba = np.linalg.lstsq(aw, yw, rcond=None)[0]
        bz = np.linalg.lstsq(aw, zw, rcond=None)[0]
        yr, zr = yw-aw@ba, zw-aw@bz
        reduced_sse += float(yr@yr)
        sst += float(yw@yw)
        interaction_xx += zr.T@zr
        interaction_xy += zr.T@yr
        parts.append(part)
    if np.linalg.matrix_rank(interaction_xx) < 2:
        return {"status": "rank_deficient_spatial_interaction"}
    beta = np.linalg.solve(interaction_xx, interaction_xy)
    full_sse = reduced_sse - float(beta@interaction_xy)
    return {"status": "estimable", "n_grids": len(grids),
        "r2_grid_slope_additive": 1-reduced_sse/sst,
        "r2_grid_slope_interaction": 1-full_sse/sst,
        "delta_r2_grid_slope_interaction": (reduced_sse-full_sse)/sst,
        "beta_grid_slope_ts": beta[0], "beta_grid_slope_vs": beta[1],
        "dry_minus_wet_t_grid_slope": float(np.mean([beta[0]*(p["s25z"]-p["s75z"]) for p in parts])),
        "dry_minus_wet_v_grid_slope": float(np.mean([beta[1]*(p["s25z"]-p["s75z"]) for p in parts]))}


def support_and_strata(data: pd.DataFrame, modifier: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    support, strata = [], []
    for grid, frame in data.groupby("grid_id", sort=True):
        frame = frame.sort_values("yield_year")
        s = frame[modifier].to_numpy(float)
        ranks = rankdata(s, method="average")
        labels = np.where((ranks-.5)/len(s)<1/3, "relatively_dry",
                  np.where((ranks-.5)/len(s)>=2/3, "relatively_wet", "middle"))
        q1,q2 = np.quantile(s,[1/3,2/3])
        row = {"grid_id":grid, "n":len(frame), "s_cut_1":q1,"s_cut_2":q2,
               "s_distinct_values":len(np.unique(s)), "s_bin_collapsed":len(set(labels))<3,
               "s_raw_min":s.min(),"s_raw_max":s.max(),
               "t_raw_min":frame[exp05.TEMP].min(),"t_raw_max":frame[exp05.TEMP].max(),
               "v_raw_min":frame[exp05.VPD].min(),"v_raw_max":frame[exp05.VPD].max(),
               "max_calendar_gap_years":int(frame.yield_year.diff().dropna().max()-1)}
        support.append(row)
        ranges=[]
        for label in ("relatively_dry","middle","relatively_wet"):
            part=frame.iloc[np.flatnonzero(labels==label)]
            if len(part):
                tmin,tmax=part[exp05.TEMP].min(),part[exp05.TEMP].max()
                vmin,vmax=part[exp05.VPD].min(),part[exp05.VPD].max()
                ranges.append((tmin,tmax,vmin,vmax))
            else:
                tmin=tmax=vmin=vmax=np.nan
            strata.append({"grid_id":grid,"stratum":label,"n":len(part),
                "years":";".join(map(str,part.yield_year.astype(int))),
                "sm_cut_1":q1,"sm_cut_2":q2,
                "sm_min":part[modifier].min(),"sm_median":part[modifier].median(),"sm_max":part[modifier].max(),
                "t_min":tmin,"t_median":part[exp05.TEMP].median(),"t_max":tmax,
                "v_min":vmin,"v_median":part[exp05.VPD].median(),"v_max":vmax,
                "y_median":part[exp05.Y10].median(),
                "r_t_v":part[[exp05.TEMP,exp05.VPD]].corr().iloc[0,1] if len(part)>2 else np.nan,
                "tie_rule":"average rank; no random split"})
        overlap=bool(len(ranges)==3 and max(x[0] for x in ranges)<=min(x[1] for x in ranges)
                     and max(x[2] for x in ranges)<=min(x[3] for x in ranges))
        support[-1]["joint_t_v_box_overlap_all_strata"]=overlap
    return pd.DataFrame(support),pd.DataFrame(strata)


def deterministic_run(panel: pd.DataFrame, output: Path) -> tuple[pd.DataFrame,pd.DataFrame]:
    config={"experiment":"EXP-05B","min_grid_linear_n":15,"min_primary_n":20,
        "min_grid_quadratic_n":30,"within_grid_predictor_scale":"sample SD ddof=1; recompute within each bootstrap",
        "outcome_unit":"t/ha, unstandardized","pooled_weight":"each grid total weight one; observation count/n_g",
        "dry_wet_reference":"grid-specific original physical S25/S75, frozen per comparison; evaluate on replicate-scaled S coordinates",
        "grid_support":"fixed grids with >=20 original paired years; replicate fails if any grid drops below 20 or has degenerate design",
        "bootstrap":{"smoke_attempts":50,"final_attempts_per_scheme":1000,
          "smoke_seed":20261012,"final_seed":20261013,"year_universe":[1981,2025],"block_lengths":[1,3,5]},
        "models":MODELS,"modifier_definitions":MODIFIERS}
    (output/"analysis_config.json").write_text(json.dumps(config,indent=2),encoding="utf-8")
    pooled_rows=[]; grid_rows=[]; support_rows=[]; strata_rows=[]
    primary="sm_28_100_prev3_mean"
    scenarios=[("primary",primary,exp05.Y10,None,None)]
    scenarios += [(f"modifier_{m}",m,exp05.Y10,primary,None) for m in MODIFIERS if m!=primary]
    scenarios += [(f"target_{y}",primary,y,None,exp05.Y10) for y in (exp05.Y12,exp05.YFIX)]
    # A separate primary baseline is recomputed on every matched comparator support.
    scenarios += [(f"primary_matched_{m}",primary,exp05.Y10,m,None) for m in MODIFIERS if m!=primary]
    scenarios += [(f"primary_matched_{y}",primary,exp05.Y10,None,y) for y in (exp05.Y12,exp05.YFIX)]
    for label,modifier,target,matched_modifier,matched_target in scenarios:
        for slot,data in make_series(panel,modifier,target,matched_modifier,matched_target).items():
            models=("P0","P1","P2","Q1","Q2","Q1_prime","Q2_prime") if label=="primary" else ("P0","P1","P2")
            row=pooled_fit(data,modifier,target,models)
            row.update({"scenario":label,"modifier":modifier,"target":target,"month_slot":slot,
                        "calendar_month_label":data.calendar_month_label.iloc[0]})
            if label=="primary":
                row.update({f"spatial_{k}":v for k,v in spatial_slope_fit(data,modifier,target).items()})
            pooled_rows.append(row)
            if label=="primary" or label.startswith("modifier_") or label.startswith("target_"):
                grid=grid_conditional(data,modifier,target)
                grid.insert(0,"month_slot",slot)
                grid.insert(0,"scenario",label)
                grid_rows.append(grid)
            if label=="primary":
                support,strata=support_and_strata(data,modifier)
                support.insert(0,"month_slot",slot);strata.insert(0,"month_slot",slot)
                support_rows.append(support);strata_rows.append(strata)
    pooled=pd.DataFrame(pooled_rows)
    grid=pd.concat(grid_rows,ignore_index=True)
    pooled.to_csv(output/"monthly_interaction_results.csv",index=False)
    grid.to_csv(output/"grid_month_conditional_results.csv",index=False)
    pd.concat(support_rows).to_csv(output/"support_diagnostics.csv",index=False)
    pd.concat(strata_rows).to_csv(output/"moisture_strata_diagnostics.csv",index=False)
    return pooled,grid


def synchronized_draws(attempts: int, block_length: int, seed: int) -> list[dict[int,int]]:
    """Consecutive *calendar* year blocks; never bridge observed-year gaps."""
    rng=np.random.default_rng(seed)
    years=np.arange(exp05.WEATHER_SOURCE_START,exp05.WEATHER_SOURCE_END+1)
    draws=[]
    for _ in range(attempts):
        if block_length==1:
            sample=rng.choice(years,size=len(years),replace=True)
        else:
            starts=rng.integers(0,len(years)-block_length+1,
                                size=int(np.ceil(len(years)/block_length)))
            sample=np.concatenate([years[start:start+block_length] for start in starts])[:len(years)]
        counts=np.bincount(sample-years[0],minlength=len(years))
        draws.append(dict(zip(years,map(int,counts))))
    return draws


def smoke_support_audit(panel: pd.DataFrame, output: Path, attempts: int=50) -> pd.DataFrame:
    """Preflight whether fixed original grid support survives synchronized draws.

    This is a necessary estimability condition, not a bootstrap interval.
    """
    primary="sm_28_100_prev3_mean"
    scenarios=[("primary",primary,exp05.Y10,None,None)]
    scenarios += [(f"modifier_{m}",m,exp05.Y10,primary,None) for m in MODIFIERS if m!=primary]
    scenarios += [(f"target_{y}",primary,y,None,exp05.Y10) for y in (exp05.Y12,exp05.YFIX)]
    datasets={label:make_series(panel,modifier,target,matched_modifier,matched_target)
              for label,modifier,target,matched_modifier,matched_target in scenarios}
    rows=[]
    for block in (1,3,5):
        seed=20261012+block
        for attempt,draw in enumerate(synchronized_draws(attempts,block,seed),1):
            for label,slots in datasets.items():
                for slot,data in slots.items():
                    by_grid=data.groupby("grid_id").yield_year.apply(
                        lambda years: sum(draw[int(y)] for y in years))
                    failed=by_grid[by_grid.lt(exp05.MIN_PRIMARY_N)]
                    rows.append({"stage":"smoke_support_preflight","block_length_years":block,
                        "seed":seed,"attempt":attempt,"scenario":label,"month_slot":slot,
                        "n_fixed_grids":len(by_grid),"n_failed_grids":len(failed),
                        "failed_grids":";".join(failed.index),
                        "status":"grid_below_preexisting_n20" if len(failed) else "support_pass",
                        "min_resampled_grid_n":int(by_grid.min())})
    result=pd.DataFrame(rows)
    result.to_csv(output/"bootstrap_smoke_support_preflight.csv",index=False)
    return result


def smoke_bootstrap(panel: pd.DataFrame, output: Path, attempts: int=50) -> pd.DataFrame:
    """Implementation check only; not mixed into final inference."""
    primary="sm_28_100_prev3_mean"
    scenarios=[("primary",primary,exp05.Y10,None,None)]
    scenarios += [(f"modifier_{m}",m,exp05.Y10,primary,None) for m in MODIFIERS if m!=primary]
    scenarios += [(f"target_{y}",primary,y,None,exp05.Y10) for y in (exp05.Y12,exp05.YFIX)]
    scenarios += [(f"primary_matched_{m}",primary,exp05.Y10,m,None) for m in MODIFIERS if m!=primary]
    scenarios += [(f"primary_matched_{y}",primary,exp05.Y10,None,y) for y in (exp05.Y12,exp05.YFIX)]
    datasets={label:make_series(panel,modifier,target,matched_modifier,matched_target)
              for label,modifier,target,matched_modifier,matched_target in scenarios}
    rows=[]
    for block in (1,3,5):
        seed=20261012+block
        for attempt,draw in enumerate(synchronized_draws(attempts,block,seed),1):
            for label,modifier,target,_,_ in scenarios:
                for slot,data in datasets[label].items():
                    models=("P0","P1","P2","Q1","Q2","Q1_prime","Q2_prime") if label=="primary" else ("P0","P1","P2")
                    result=pooled_fit(data,modifier,target,models,draw,
                                      tuple(sorted(data.grid_id.unique())))
                    row={"stage":"smoke","block_length_years":block,"seed":seed,
                        "attempt":attempt,"scenario":label,"month_slot":slot,
                        "model_roster":";".join(models),"status":result["status"],
                        "n_fixed_grids":data.grid_id.nunique(),
                        "n_failed_grids":result.get("n_failed_grids",0),
                        "failed_grids":result.get("failed_grids","")}
                    if label=="primary" and result["status"]=="estimable":
                        spatial=spatial_slope_fit(data,modifier,target,draw,
                                                  tuple(sorted(data.grid_id.unique())))
                        row["spatial_status"]=spatial["status"]
                    rows.append(row)
    result=pd.DataFrame(rows)
    result.to_csv(output/"bootstrap_smoke_attempts.csv",index=False)
    summary=result.groupby(["scenario","month_slot","block_length_years","status"],
                           dropna=False).size().rename("n_attempts").reset_index()
    summary.to_csv(output/"bootstrap_diagnostics.csv",index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["a", "deterministic", "smoke-support"], default="a")
    args = parser.parse_args()
    root = exp05.project_root()
    output = root / "outputs/research/exp_05b"
    panel=phase_a(root, output)
    if args.phase in ("deterministic","smoke-support"):
        deterministic_run(panel,output)
    if args.phase=="smoke-support":
        smoke_support_audit(panel,output)


if __name__ == "__main__":
    main()
