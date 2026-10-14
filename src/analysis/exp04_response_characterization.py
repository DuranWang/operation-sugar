"""EXP-04: fixed-universe, one-weather-candidate-at-a-time response audit.

Reads frozen EXP-02B targets and canonical combined monthly weather. Writes
only EXP-04 outputs. Entry point: python -m src.analysis.exp04_response_characterization
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay, QhullError

from src.analysis import exp05_conditional_temperature_vpd as exp05

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/research/exp_04"
PROC = ROOT / "data/processed/analysis/exp_04"
UNIVERSE = ROOT / "outputs/research/exp_03/redundancy/exp04_candidate_universe.csv"
WEATHER = ROOT / "data/processed/combined_weather/annual"
VARS = ("nasa_total_rainfall_mm", "nasa_average_temperature_c",
        "nasa_average_relative_humidity_pct", "vpd_mean_kpa",
        "soil_moisture_0_to_7cm_m3_m3", "soil_moisture_28_to_100cm_m3_m3",
        "soil_moisture_100_to_255cm_m3_m3", "solar_radiation_mean_daily_mj_m2")
ERA5_VARS = VARS[3:]
TARGETS = (exp05.Y10, exp05.Y12, exp05.YFIX)
MIN_L, MIN_Q = 20, 30
COND_MAX = 1e8
FIXED_INCREMENT = {
    "rainfall_input": 100., "temperature": 1., "relative_humidity": 10.,
    "mean_vpd": .1, "upper_soil_moisture": .01,
    "deep_soil_moisture_28_100": .01, "deep_soil_moisture_100_255": .01,
    "solar_energy": 1.,
}


def fingerprint(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_universe() -> pd.DataFrame:
    c = pd.read_csv(UNIVERSE)
    if len(c) != 38 or not c.candidate_id.is_unique:
        raise ValueError("Frozen EXP-04 universe must have 38 unique candidates")
    if set(c.raw_source_variable) != set(VARS):
        raise ValueError("Frozen source variables differ from expected existing weather fields")
    for row in c.itertuples():
        if row.candidate_id.endswith("__dec_jan"):
            if row.source_relative_months != "-4;-3" or row.conceptual_variable not in (
                    "relative_humidity", "deep_soil_moisture_28_100"):
                raise ValueError(f"Unapproved aggregate: {row.candidate_id}")
        elif row.candidate_id != f"{row.conceptual_variable}__m_{int(row.source_relative_months)}":
            raise ValueError(f"Candidate month mismatch: {row.candidate_id}")
    c["analysis_formula"] = "X=calendar-month grid weather"
    c.loc[c.candidate_id.str.endswith("__dec_jan"), "analysis_formula"] = "X=(grid weather Dec(t-1)+grid weather Jan(t))/2, raw units"
    c["fixed_increment_raw_units"] = c.conceptual_variable.map(FIXED_INCREMENT)
    return c


def build_panel(candidates: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    targets, weights, mapping, lineage = exp05.load_frozen_targets(ROOT)
    if len(mapping) != 511 or mapping.grid_id.nunique() != 78:
        raise ValueError("Frozen eligible municipality support changed")
    slots = exp05.discover_slots(ROOT)
    slots = slots.loc[slots.month_slot.isin(range(-4, 1)), ["month_slot", "source_year_offset",
        "source_calendar_month", "calendar_month_label"]].copy()
    expected = {-4: (-1, 12), -3: (0, 1), -2: (0, 2), -1: (0, 3), 0: (0, 4)}
    for r in slots.itertuples():
        if (r.source_year_offset, r.source_calendar_month) != expected[r.month_slot]:
            raise ValueError("Relative-month alignment differs from frozen EXP-03")
    t = targets.loc[targets[exp05.Y10].notna()].copy()
    if t.duplicated(["grid_id", "yield_year"]).any():
        raise ValueError("Duplicate valid frozen target")
    aligned = t.merge(slots, how="cross")
    aligned["source_year"] = aligned.yield_year + aligned.source_year_offset
    w = weights[["grid_id", "year", "ibge_code", "actual_weight"]].rename(columns={"year": "yield_year"})
    expanded = aligned.merge(w, on=["grid_id", "yield_year"], how="left", validate="many_to_many")
    if expanded.ibge_code.isna().any():
        raise ValueError("Primary target lacks municipality support")
    needed_years = sorted(year for year in aligned.source_year.unique() if 1981 <= year <= 2025)
    weather = []
    fields = ["ibge_code", "era5_grid_id", "month", "nasa_observed_days", "era5_observed_days", *VARS]
    for year in needed_years:
        path = WEATHER / f"sp_municipality_monthly_weather_{year}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path, usecols=fields, dtype={"ibge_code": "string"})
        if not frame.month.str.startswith(f"{year}-").all():
            raise ValueError(f"Weather file year mismatch: {path}")
        frame["source_year"] = year
        frame["source_calendar_month"] = frame.month.str[-2:].astype(int)
        expected_days = np.array([calendar.monthrange(year, int(x))[1] for x in frame.source_calendar_month])
        for source, columns in (("nasa_observed_days", VARS[:3]), ("era5_observed_days", VARS[3:])):
            incomplete = frame[source].to_numpy() != expected_days
            if frame.loc[incomplete, list(columns)].notna().any().any():
                raise ValueError(f"Incomplete source month has nonmissing weather values: {path}")
        weather.append(frame.drop(columns="month"))
    weather = pd.concat(weather, ignore_index=True).rename(columns={"era5_grid_id": "grid_id"})
    if weather.duplicated(["ibge_code", "source_year", "source_calendar_month"]).any():
        raise ValueError("Duplicate canonical municipality-month weather")
    expanded = expanded.merge(weather, on=["grid_id", "ibge_code", "source_year", "source_calendar_month"],
                              how="left", validate="many_to_one")
    keys = ["grid_id", "yield_year", "month_slot"]
    # Each ERA5 series is shared by municipality within a grid, but we still
    # use the same frozen target-year support and verify no invented detail.
    for variable in ERA5_VARS:
        spread = expanded.groupby(keys)[variable].agg(lambda a: a.max()-a.min() if a.notna().any() else 0.)
        if spread.gt(1e-9).any():
            raise ValueError(f"Shared ERA5 grid variable varies within grid-month: {variable}")
    aggregated = expanded[keys].drop_duplicates().copy()
    partial_rows = []
    for variable in VARS:
        valid = np.isfinite(expanded[variable])
        weighted = expanded.actual_weight * expanded[variable].where(valid, 0.)
        covered = expanded.actual_weight.where(valid, 0.)
        part = expanded[keys].assign(weighted=weighted, covered=covered).groupby(keys, as_index=False).sum()
        part[variable] = part.weighted.where(np.isclose(part.covered, 1., atol=1e-10, rtol=0))
        partial = part.covered.between(1e-10, 1-1e-10)
        if partial.any():
            partial_rows.append(part.loc[partial, keys+['covered']].assign(variable=variable))
        aggregated = aggregated.merge(part[keys+[variable, "covered"]].rename(columns={"covered": f"{variable}__weight_coverage"}),
                                      on=keys, validate="one_to_one")
    if len(aggregated) != len(t)*5 or aggregated.duplicated(keys).any():
        raise ValueError("Grid monthly weather panel cardinality changed")
    base = aggregated.merge(t[["grid_id", "yield_year", *TARGETS,
        "actual_weight_denominator_ha", "grid_latitude", "grid_longitude"]],
        on=["grid_id", "yield_year"], validate="many_to_one")
    records = []
    source = base.set_index(keys)
    for r in candidates.itertuples():
        if r.candidate_id.endswith("__dec_jan"):
            dec = base.loc[base.month_slot.eq(-4), ["grid_id", "yield_year", r.raw_source_variable,
                f"{r.raw_source_variable}__weight_coverage"]].rename(columns={
                r.raw_source_variable: "dec", f"{r.raw_source_variable}__weight_coverage": "dec_coverage"})
            jan = base.loc[base.month_slot.eq(-3), ["grid_id", "yield_year", r.raw_source_variable,
                f"{r.raw_source_variable}__weight_coverage"]].rename(columns={
                r.raw_source_variable: "jan", f"{r.raw_source_variable}__weight_coverage": "jan_coverage"})
            part = dec.merge(jan, on=["grid_id", "yield_year"], validate="one_to_one")
            part["x"] = (part.dec+part.jan)/2
            part["weight_coverage"] = part[["dec_coverage", "jan_coverage"]].min(axis=1)
        else:
            slot = int(r.source_relative_months)
            part = base.loc[base.month_slot.eq(slot), ["grid_id", "yield_year", r.raw_source_variable,
                f"{r.raw_source_variable}__weight_coverage"]].rename(columns={
                r.raw_source_variable: "x", f"{r.raw_source_variable}__weight_coverage": "weight_coverage"})
        part = part.merge(t[["grid_id", "yield_year", *TARGETS,
            "actual_weight_denominator_ha", "grid_latitude", "grid_longitude"]],
            on=["grid_id", "yield_year"], validate="one_to_one")
        part["candidate_id"] = r.candidate_id
        records.append(part)
    panel = pd.concat(records, ignore_index=True)
    if panel.duplicated(["candidate_id", "grid_id", "yield_year"]).any():
        raise ValueError("Duplicate candidate grid-year")
    if partial_rows:
        pd.concat(partial_rows, ignore_index=True).to_csv(OUT/"partial_weather_support.csv", index=False)
    return panel, {"target_lineage": lineage, "weather_year_min": min(needed_years),
                   "weather_year_max": max(needed_years), "partial_weather_support_rows": sum(map(len,partial_rows))}


def design_fit(y, z, quadratic=False, extra=None, weights=None, fail_condition=COND_MAX):
    """Full-rank intercept fit; no pseudoinverse for unstable curves."""
    y, z = np.asarray(y, float), np.asarray(z, float)
    cols = [np.ones(len(y)), z]
    if quadratic:
        cols.append(z*z)
    if extra is not None:
        cols.append(np.asarray(extra, float))
    x = np.column_stack(cols)
    w = np.ones(len(y)) if weights is None else np.asarray(weights, float)
    if len(y) < x.shape[1] or np.any(w <= 0) or not np.isfinite(x).all() or not np.isfinite(y).all():
        return None, "invalid_data_or_support"
    d = x * np.sqrt(w[:,None])
    cond = np.linalg.cond(d)
    if not np.isfinite(cond) or cond > fail_condition or np.linalg.matrix_rank(d) < d.shape[1]:
        return None, "rank_or_condition_failure"
    beta = np.linalg.lstsq(d, y*np.sqrt(w), rcond=None)[0]
    resid = y-x@beta
    sse = float(np.sum(w*resid**2))
    sst = float(np.sum(w*(y-np.average(y, weights=w))**2))
    return {"beta":beta, "r2":1-sse/sst if sst>1e-12 else np.nan,
            "condition":cond, "residual":resid, "sse":sse, "sst":sst,
            "leverage":np.sum(d*(d@np.linalg.inv(d.T@d)), axis=1)}, ""


def estimate_grid(group, target, ref=None):
    valid = group.loc[np.isfinite(group.x) & np.isfinite(group[target]) &
                      np.isclose(group.weight_coverage, 1., atol=1e-10, rtol=0)].sort_values("yield_year")
    x, y = valid.x.to_numpy(float), valid[target].to_numpy(float)
    n = len(valid)
    result = {"candidate_id":group.candidate_id.iloc[0], "grid_id":group.grid_id.iloc[0],
              "target":target, "n":n, "years":";".join(map(str,valid.yield_year)),
              "first_year":valid.yield_year.min() if n else np.nan,
              "last_year":valid.yield_year.max() if n else np.nan,
              "missing_x":int(group.x.isna().sum()),
              "missing_y":int(group[target].isna().sum()),
              "partial_weather_rows":int((~np.isclose(group.weight_coverage,1.,atol=1e-10,rtol=0)).sum()),
              "mean_area_ha":valid.actual_weight_denominator_ha.mean() if n else np.nan,
              "grid_latitude":group.grid_latitude.iloc[0], "grid_longitude":group.grid_longitude.iloc[0],
              "linear_status":"insufficient_n", "quadratic_status":"insufficient_n"}
    if n:
        q = np.quantile(x,[.1,.25,.5,.75,.9])
        result.update(x_min=x.min(),x_max=x.max(),x_mean=x.mean(),x_sd=x.std(ddof=1) if n>1 else np.nan,
                      x_p10=q[0],x_p25=q[1],x_p50=q[2],x_p75=q[3],x_p90=q[4],unique_x=len(np.unique(x)))
    if n<MIN_L or n<2 or x.std(ddof=1)<=0:
        return result
    mu, sd = (x.mean(),x.std(ddof=1)) if ref is None else ref
    z=(x-mu)/sd
    l, reason=design_fit(y,z)
    if l is None:
        result["linear_status"]=reason
        return result
    b=l["beta"][1]
    result.update(linear_status="fit",x_ref_mean=mu,x_ref_sd=sd,
                  linear_beta_per_raw_unit=b/sd,linear_beta_per_x_sd=b,
                  linear_r2=l["r2"],linear_condition=l["condition"],
                  linear_iqr_contrast=b*(q[3]-q[1])/sd,
                  linear_p10_p90_contrast=b*(q[4]-q[0])/sd,
                  max_linear_leverage=l["leverage"].max())
    if n<MIN_Q or len(np.unique(x))<10:
        result["quadratic_status"]="n_or_unique_x_below_gate"
        return result
    fit,reason=design_fit(y,z,True)
    if fit is None:
        result["quadratic_status"]=reason
        return result
    b,c=fit["beta"][1:3]
    p=(q-mu)/sd
    f=lambda t: b*t+c*t*t
    low=f(p[2])-f(p[0]); high=f(p[4])-f(p[2])
    slope_low=low/(q[2]-q[0]) if q[2]>q[0] else np.nan
    slope_high=high/(q[4]-q[2]) if q[4]>q[2] else np.nan
    rz=z*z - np.column_stack([np.ones(n),z])@np.linalg.lstsq(np.column_stack([np.ones(n),z]),z*z,rcond=None)[0]
    terciles=np.quantile(x,[0,1/3,2/3,1])
    bins=np.searchsorted(terciles[1:-1],x,side="right")
    result.update(quadratic_status="fit",quadratic_b=b,quadratic_c=c,
                  quadratic_r2=fit["r2"],quadratic_delta_r2=fit["r2"]-l["r2"],
                  quadratic_condition=fit["condition"],z2_residual_variance=np.var(rz,ddof=1),
                  delta_low_tch=low,delta_high_tch=high,
                  segment_slope_low_raw=slope_low,segment_slope_high_raw=slope_high,
                  segment_slope_difference_raw=slope_high-slope_low,
                  local_slope_p10_raw=(b+2*c*p[0])/sd,
                  local_slope_p50_raw=(b+2*c*p[2])/sd,
                  local_slope_p90_raw=(b+2*c*p[4])/sd,
                  max_quadratic_leverage=fit["leverage"].max(),
                  p10_p90_fitted_change_tch=f(p[4])-f(p[0]),
                  turn_raw=mu-sd*b/(2*c) if abs(c)>1e-12 else np.nan,
                  turn_in_observed_range=bool(abs(c)>1e-12 and x.min()<=mu-sd*b/(2*c)<=x.max()),
                  turn_in_p10_p90=bool(abs(c)>1e-12 and q[0]<=mu-sd*b/(2*c)<=q[4]))
    for j in range(3):
        vals=x[bins==j]
        result[f"tercile_{j+1}_n"]=len(vals)
        result[f"tercile_{j+1}_unique_x"]=len(np.unique(vals))
        result[f"tercile_{j+1}_span"]=np.ptp(vals) if len(vals) else np.nan
    return result


def primary_grids(panel, candidates):
    rows=[]
    for (cid,gid),group in panel.groupby(["candidate_id","grid_id"],sort=True):
        rows.append(estimate_grid(group,exp05.Y10))
    result=pd.DataFrame(rows)
    for cid,frame in result.groupby("candidate_id"):
        if len(frame)!=78:
            raise ValueError(f"Candidate omitted frozen grid: {cid}")
    return result


def _fit_fe(parts, model, grid_weight="equal", target=exp05.Y10, heterogeneous=False):
    """FWL within-grid fit with fixed roster and grid-normalized row weights."""
    totals=[]
    residual_x=[]
    residual_y=[]
    weights=[]
    per_grid=[]
    for part in parts:
        z=part["z"]
        y=part[target]
        n=len(z)
        if n<3:
            return None,"grid_insufficient_resample_support"
        gw=part["pi"] if grid_weight=="area" else 1.
        w=np.full(n,gw/n)
        terms=np.column_stack([z,z*z]) if model in ("PQ","HQ") else z[:,None]
        xx=terms-np.average(terms,axis=0,weights=w)
        yy=y-np.average(y,weights=w)
        within_sst=float(np.sum(w*yy*yy))
        if heterogeneous:
            denom=float(np.sum(w*xx[:,0]**2))
            if denom<=1e-12:
                return None,"grid_local_z_rank_failure"
            local_slope=np.sum(w*xx[:,0]*yy)/denom
            local_z2_projection=(np.sum(w*xx[:,0]*xx[:,1])/denom) if model=="HQ" else np.nan
            if model=="HQ":
                x2=xx[:,1]-xx[:,0]*np.sum(w*xx[:,0]*xx[:,1])/denom
                yy=yy-xx[:,0]*np.sum(w*xx[:,0]*yy)/denom
                residual_x.append(x2)
                residual_y.append(yy)
                weights.append(w)
            per_grid.append((part["grid_id"],local_slope,local_z2_projection))
        else:
            residual_x.append(xx)
            residual_y.append(yy)
            weights.append(w)
        totals.append((within_sst,n))
    if heterogeneous and model=="HL":
        slopes={gid:slope for gid,slope,_ in per_grid}
        sse=0.
        for part in parts:
            z=part["z"];y=part[target];w=(part["pi"] if grid_weight=="area" else 1.)/len(z)
            sse+=float(w*np.sum(((y-y.mean())-slopes[part["grid_id"]]*(z-z.mean()))**2))
        sst=sum(v for v,_ in totals)
        return {"status":"fit","grid_slopes":slopes,"within_r2":1-sse/sst,
                "n_grids":len(parts),
                "n_observations":sum(n for _,n in totals)},""
    xx=np.concatenate(residual_x)
    yy=np.concatenate(residual_y)
    w=np.concatenate(weights)
    if xx.ndim==1:
        xx=xx[:,None]
    cross=(xx*w[:,None]).T@xx
    if np.linalg.matrix_rank(cross)<cross.shape[0] or np.linalg.cond(cross)>COND_MAX**2:
        return None,"pooled_rank_or_condition_failure"
    beta=np.linalg.solve(cross,(xx*w[:,None]).T@yy)
    sst=sum(v for v,_ in totals) if heterogeneous else np.sum(w*yy*yy)
    sse=np.sum(w*(yy-xx@beta)**2)
    return {"status":"fit","b":beta[0] if not heterogeneous else np.nan,
            "c":beta[-1] if model in ("PQ","HQ") else np.nan,
            "within_r2":1-sse/sst if sst>1e-12 else np.nan,
            "n_grids":len(parts),"n_observations":sum(n for _,n in totals),
            "grid_slopes":({gid:slope-beta[-1]*projection for gid,slope,projection in per_grid}
                            if heterogeneous else {})},""


def pooled_models(panel, grid_est, target=exp05.Y10, matched=False):
    rows=[]
    for cid,frame in panel.groupby("candidate_id",sort=True):
        reference=grid_est.loc[grid_est.candidate_id.eq(cid)].set_index("grid_id")
        roster=reference.index[reference.quadratic_status.eq("fit")]
        parts=[]
        for gid in roster:
            ref=reference.loc[gid]
            part=frame.loc[frame.grid_id.eq(gid) & np.isfinite(frame.x) & np.isfinite(frame[target])].copy()
            if matched:
                part=part.loc[np.isfinite(part[list(TARGETS)]).all(axis=1)]
            z=(part.x.to_numpy(float)-ref.x_ref_mean)/ref.x_ref_sd
            if len(part)==0:
                continue
            parts.append({"grid_id":gid,"z":z,target:part[target].to_numpy(float),
                          "pi":float(ref.mean_area_ha)})
        if not parts:
            continue
        area_sum=sum(x["pi"] for x in parts)
        for x in parts:
            x["pi"]/=area_sum
        fits={}
        for model,weight,het in (("PL","equal",False),("PQ","equal",False),
                                 ("HL","equal",True),("HQ","equal",True),
                                 ("PL","area",False),("PQ","area",False)):
            fit,reason=_fit_fe(parts,model,weight,target,het)
            fits[model,weight]=fit
            row={"candidate_id":cid,"target":target,"model":model,"grid_weighting":weight,
                 "status":"fit" if fit else reason,"fixed_grid_roster":";".join(x["grid_id"] for x in parts),
                 "n_fixed_grids":len(parts)}
            if fit:
                row.update({k:v for k,v in fit.items() if k!="grid_slopes"})
                contrasts=[]
                for part in parts:
                    ref=reference.loc[part["grid_id"]]
                    p=(np.array([ref.x_p10,ref.x_p50,ref.x_p90])-ref.x_ref_mean)/ref.x_ref_sd
                    slope=fit["grid_slopes"].get(part["grid_id"],fit.get("b",np.nan))
                    c=fit.get("c",np.nan)
                    c=0. if not np.isfinite(c) else c
                    f=lambda v:slope*v+c*v*v
                    contrasts.append((part["pi"] if weight=="area" else 1/len(parts),
                                      f(p[1])-f(p[0]),f(p[2])-f(p[1])))
                row["mean_delta_low_tch"]=sum(a*b for a,b,_ in contrasts)
                row["mean_delta_high_tch"]=sum(a*c for a,_,c in contrasts)
            rows.append(row)
        # The four core models use precisely the same original grid population.
        if any(fits.get((name,"equal")) is None for name in ("PL","PQ","HL","HQ")):
            continue
        for row in rows[-6:]:
            if row["candidate_id"]==cid and row["target"]==target:
                if row["model"]=="PQ":
                    base=fits["PL",row["grid_weighting"]]
                    row["delta_r2_vs_linear"]=row["within_r2"]-base["within_r2"]
                if row["model"]=="HQ":
                    base=fits["HL","equal"]
                    row["delta_r2_vs_linear"]=row["within_r2"]-base["within_r2"]
    return pd.DataFrame(rows)


def aggregate_diagnostics(panel, grid_est):
    results=[]
    for concept in ("relative_humidity","deep_soil_moisture_28_100"):
        aid=f"{concept}__dec_jan"
        agg=panel.loc[panel.candidate_id.eq(aid)].copy()
        agg["d"]=(agg.jan-agg.dec)/2
        for gid,g in agg.groupby("grid_id",sort=True):
            g=g.loc[np.isfinite(g[["x","d",exp05.Y10]]).all(axis=1)].sort_values("yield_year")
            n=len(g)
            rec={"candidate_id":aid,"grid_id":gid,"n":n,"years":";".join(map(str,g.yield_year)),
                 "linear_status":"insufficient_n","quadratic_status":"insufficient_n"}
            if n<MIN_L:
                results.append(rec);continue
            a=g.x.to_numpy(float);d=g.d.to_numpy(float);y=g[exp05.Y10].to_numpy(float)
            mu=a.mean();sd=a.std(ddof=1)
            if sd<=0:
                rec["linear_status"]="constant_A";results.append(rec);continue
            z=(a-mu)/sd
            ds=d.std(ddof=1)
            if ds<=0:
                rec["linear_status"]="constant_D";results.append(rec);continue
            zd=(d-d.mean())/ds
            ma,_=design_fit(y,z)
            mad,reason=design_fit(y,z,extra=zd)
            if ma is None or mad is None:
                rec["linear_status"]=reason or "MA_rank_failure";results.append(rec);continue
            b_a=mad["beta"][1]/sd;b_d=mad["beta"][2]/ds
            residual_d=zd-np.column_stack([np.ones(n),z])@np.linalg.lstsq(np.column_stack([np.ones(n),z]),zd,rcond=None)[0]
            rec.update(linear_status="fit",a_ref_mean=mu,a_ref_sd=sd,d_ref_mean=d.mean(),d_ref_sd=ds,
                       ma_r2=ma["r2"],mad_r2=mad["r2"],mad_delta_r2=mad["r2"]-ma["r2"],
                       mad_partial_r2=(ma["sse"]-mad["sse"])/ma["sse"] if ma["sse"]>0 else np.nan,
                       b_A_raw=b_a,b_D_raw=b_d,b_dec_raw=(b_a-b_d)/2,b_jan_raw=(b_a+b_d)/2,
                       residual_d_variance=float(np.var(residual_d,ddof=1)),
                       ad_correlation=float(np.corrcoef(a,d)[0,1]),
                       a_p50=np.quantile(a,.5),d_p25=np.quantile(d,.25),d_p75=np.quantile(d,.75))
            for label,values in (("dec",g.dec.to_numpy(float)),("jan",g.jan.to_numpy(float))):
                scale=values.std(ddof=1)
                if scale>0:
                    univ,_=design_fit(y,(values-values.mean())/scale)
                    rec[f"{label}_single_beta_raw"]=univ["beta"][1]/scale if univ else np.nan
                    rec[f"{label}_single_r2"]=univ["r2"] if univ else np.nan
            rec["a_single_beta_raw"]=ma["beta"][1]/sd
            rec["ad_convex_hull_support"]="unverified"
            try:
                hull=Delaunay(np.column_stack([a,d]))
                query=np.array([[rec["a_p50"],rec["d_p25"]],[rec["a_p50"],rec["d_p75"]]])
                supported=hull.find_simplex(query)>=0
                rec["ad_convex_hull_support"]="both_inside" if supported.all() else "outside"
                rec["mad_d_p25_p75_at_median_a_tch"]=(b_d*(rec["d_p75"]-rec["d_p25"])) if supported.all() else np.nan
            except QhullError:
                rec["ad_convex_hull_support"]="degenerate_joint_support"
            if n<MIN_Q or len(np.unique(a))<10:
                rec["quadratic_status"]="n_or_unique_A_below_gate";results.append(rec);continue
            qa,reason=design_fit(y,z,True)
            qad,reason2=design_fit(y,z,True,zd)
            if qa is None or qad is None:
                rec["quadratic_status"]=reason or reason2;results.append(rec);continue
            rec.update(quadratic_status="fit",qa_r2=qa["r2"],qad_r2=qad["r2"],
                       qad_delta_r2=qad["r2"]-qa["r2"],
                       qad_partial_r2=(qa["sse"]-qad["sse"])/qa["sse"] if qa["sse"]>0 else np.nan,
                       qad_b_D_raw=qad["beta"][-1]/ds)
            results.append(rec)
    return pd.DataFrame(results)


def fit_pooled_ad(parts, terms, heterogeneous_a=False):
    residual_x=[];residual_y=[];weights=[];sst=0.
    for part in parts:
        n=len(part["z"])
        if n<4:return None,"insufficient_grid_support"
        z=part["z"];d=part["d"];y=part["y"]
        variables={"z":z,"z2":z*z,"d":d}
        x=np.column_stack([variables[t] for t in terms])
        x=x-x.mean(axis=0)
        yy=y-y.mean()
        w=np.full(n,1/n)
        sst+=float(np.sum(w*yy*yy))
        if heterogeneous_a:
            za=z-z.mean()
            denom=float(np.sum(w*za*za))
            if denom<=1e-12:return None,"grid_A_slope_rank_failure"
            x=x-za[:,None]*(w@ (za[:,None]*x))[None,:]/denom
            yy=yy-za*np.sum(w*za*yy)/denom
        residual_x.append(x);residual_y.append(yy);weights.append(w)
    x=np.concatenate(residual_x);y=np.concatenate(residual_y);w=np.concatenate(weights)
    cross=(x*w[:,None]).T@x
    if np.linalg.matrix_rank(cross)<len(terms) or np.linalg.cond(cross)>COND_MAX**2:
        return None,"pooled_rank_or_condition_failure"
    beta=np.linalg.solve(cross,(x*w[:,None]).T@y)
    sse=float(np.sum(w*(y-x@beta)**2))
    return {"beta":beta,"within_r2":1-sse/sst,"n_grids":len(parts),
            "n_observations":sum(len(p["z"]) for p in parts)},""


def pooled_aggregate_diagnostics(panel, aggregation):
    rows=[]
    definitions=(("MA",("z",),False),("MAD",("z","d"),False),
                 ("QA",("z","z2"),False),("QAD",("z","z2","d"),False),
                 ("MAD_HA",("d",),True),("QAD_HA",("z2","d"),True))
    for cid in ("relative_humidity__dec_jan","deep_soil_moisture_28_100__dec_jan"):
        frame=panel.loc[panel.candidate_id.eq(cid)]
        ref=aggregation.loc[aggregation.candidate_id.eq(cid)].set_index("grid_id")
        for model,terms,heterogeneous in definitions:
            gate="quadratic_status" if model.startswith("Q") else "linear_status"
            roster=tuple(sorted(ref.index[ref[gate].eq("fit")]))
            parts=[]
            for gid in roster:
                r=ref.loc[gid]
                g=frame.loc[frame.grid_id.eq(gid)&np.isfinite(frame[["x","dec","jan",exp05.Y10]]).all(axis=1)]
                a=g.x.to_numpy(float);d=(g.jan.to_numpy(float)-g.dec.to_numpy(float))/2
                parts.append({"grid_id":gid,"z":(a-r.a_ref_mean)/r.a_ref_sd,
                    "d":(d-r.d_ref_mean)/r.d_ref_sd,"y":g[exp05.Y10].to_numpy(float),
                    "d_iqr_scaled":(r.d_p75-r.d_p25)/r.d_ref_sd})
            fit,reason=fit_pooled_ad(parts,terms,heterogeneous)
            row={"candidate_id":cid,"model":model,"status":"fit" if fit else reason,
                 "fixed_grid_roster":";".join(roster),"n_fixed_grids":len(roster)}
            if fit:
                row.update(within_r2=fit["within_r2"],n_observations=fit["n_observations"])
                row.update({f"coef_{term}":float(value) for term,value in zip(terms,fit["beta"])})
                if "d" in terms:
                    row["mean_d_iqr_contrast_tch"]=float(fit["beta"][terms.index("d")]*
                        np.mean([p["d_iqr_scaled"] for p in parts]))
            rows.append(row)
    result=pd.DataFrame(rows)
    for cid,grp in result.groupby("candidate_id"):
        for base,full in (("MA","MAD"),("QA","QAD")):
            b=grp.loc[grp.model.eq(base)].iloc[0];f=grp.loc[grp.model.eq(full)].iloc[0]
            if b.status=="fit" and f.status=="fit":
                result.loc[result.candidate_id.eq(cid)&result.model.eq(full),"incremental_r2_vs_base"]=(
                    f.within_r2-b.within_r2)
    return result


def leave_one_year_out(panel, grid_est, pooled):
    rows=[]
    grouped={key:part.loc[np.isfinite(part.x)&np.isfinite(part[exp05.Y10])].sort_values("yield_year")
             for key,part in panel.groupby(["candidate_id","grid_id"],sort=False)}
    for r in grid_est.loc[grid_est.quadratic_status.eq("fit")].itertuples():
        group=grouped[r.candidate_id,r.grid_id]
        years=group.yield_year.to_numpy(int)
        all_x=group.x.to_numpy(float)
        all_y=group[exp05.Y10].to_numpy(float)
        for year in years:
            mask=years!=year
            x=all_x[mask];y=all_y[mask]
            z=(x-r.x_ref_mean)/r.x_ref_sd
            q,reason=design_fit(y,z,True)
            row={"candidate_id":r.candidate_id,"grid_id":r.grid_id,"model":"Q",
                 "deleted_year":year,"status":"fit" if q else reason}
            if q:
                b,c=q["beta"][1:3]
                p=(np.array([r.x_p10,r.x_p50,r.x_p90])-r.x_ref_mean)/r.x_ref_sd
                f=lambda a:b*a+c*a*a
                row.update(c=c,delta_low_tch=f(p[1])-f(p[0]),
                           delta_high_tch=f(p[2])-f(p[1]))
            rows.append(row)
    # Pooled leave-one-year-out keeps original grid rosters and reference scales.
    primary=pooled.loc[pooled.target.eq(exp05.Y10)&pooled.grid_weighting.eq("equal")&
                       pooled.model.isin(("PQ","HQ"))]
    for p in primary.itertuples():
        if p.status!="fit":continue
        refs=grid_est.loc[grid_est.candidate_id.eq(p.candidate_id)].set_index("grid_id")
        roster=p.fixed_grid_roster.split(";")
        selected={gid:(grouped[p.candidate_id,gid].yield_year.to_numpy(int),
                       grouped[p.candidate_id,gid].x.to_numpy(float),
                       grouped[p.candidate_id,gid][exp05.Y10].to_numpy(float)) for gid in roster}
        years=sorted(set().union(*(set(part[0]) for part in selected.values())))
        for year in years:
            parts=[]
            for gid in roster:
                yr,x,y=selected[gid]
                mask=yr!=year
                ref=refs.loc[gid]
                parts.append({"grid_id":gid,"z":(x[mask]-ref.x_ref_mean)/ref.x_ref_sd,
                              exp05.Y10:y[mask],"pi":1.})
            f,reason=_fit_fe(parts,p.model,"equal",exp05.Y10,p.model=="HQ")
            row={"candidate_id":p.candidate_id,"grid_id":"__pooled__","model":p.model,
                 "deleted_year":year,"status":"fit" if f else reason,
                 "c":f.get("c") if f else np.nan}
            if f:
                contrasts=[]
                for gid in roster:
                    r=refs.loc[gid]
                    anchor=(np.array([r.x_p10,r.x_p50,r.x_p90])-r.x_ref_mean)/r.x_ref_sd
                    slope=f["grid_slopes"].get(gid,f.get("b",np.nan))
                    curve=lambda z:slope*z+f["c"]*z*z
                    contrasts.append((curve(anchor[1])-curve(anchor[0]),
                                      curve(anchor[2])-curve(anchor[1])))
                row["delta_low_tch"]=float(np.mean([x[0] for x in contrasts]))
                row["delta_high_tch"]=float(np.mean([x[1] for x in contrasts]))
            rows.append(row)
    return pd.DataFrame(rows)


def target_robustness(panel, primary):
    rows=[]
    for (cid,gid),group in panel.groupby(["candidate_id","grid_id"],sort=True):
        common=group.loc[np.isfinite(group[["x",*TARGETS]]).all(axis=1)].copy()
        reference=primary.loc[primary.candidate_id.eq(cid)&primary.grid_id.eq(gid)].iloc[0]
        if pd.isna(reference.get("x_ref_sd",np.nan)):
            continue
        for target in TARGETS:
            max_fit=estimate_grid(group,target,(reference.x_ref_mean,reference.x_ref_sd))
            matched_fit=estimate_grid(common,target,(reference.x_ref_mean,reference.x_ref_sd))
            rows.append({"candidate_id":cid,"grid_id":gid,"target":target,
                         "max_n":max_fit["n"],"common_n":matched_fit["n"],
                         "max_linear_beta_raw":max_fit.get("linear_beta_per_raw_unit"),
                         "common_linear_beta_raw":matched_fit.get("linear_beta_per_raw_unit"),
                         "max_quadratic_c":max_fit.get("quadratic_c"),
                         "common_quadratic_c":matched_fit.get("quadratic_c"),
                         "primary_ref_mean":reference.x_ref_mean,"primary_ref_sd":reference.x_ref_sd,
                         "common_years":matched_fit["years"]})
    result=pd.DataFrame(rows)
    base=result.loc[result.target.eq(exp05.Y10),["candidate_id","grid_id",
        "common_linear_beta_raw","common_quadratic_c"]].rename(columns={
        "common_linear_beta_raw":"primary_common_linear_beta_raw",
        "common_quadratic_c":"primary_common_quadratic_c"})
    result=result.merge(base,on=["candidate_id","grid_id"],validate="many_to_one")
    result["delta_linear_beta_raw_vs_primary"]=(result.common_linear_beta_raw-result.primary_common_linear_beta_raw)
    result["delta_quadratic_c_vs_primary"]=(result.common_quadratic_c-result.primary_common_quadratic_c)
    return result


def make_figures(panel, estimates, pooled, aggregate):
    figdir=OUT/"figures";figdir.mkdir(parents=True,exist_ok=True)
    for cid,frame in panel.groupby("candidate_id",sort=True):
        refs=estimates.loc[estimates.candidate_id.eq(cid)].set_index("grid_id")
        safe=cid.replace("/","_")
        with PdfPages(figdir/f"atlas_{safe}.pdf") as pdf:
            grids=sorted(frame.grid_id.unique())
            for offset in range(0,len(grids),12):
                fig,axes=plt.subplots(3,4,figsize=(16,11),constrained_layout=True)
                for ax,gid in zip(axes.flat,grids[offset:offset+12]):
                    part=frame.loc[frame.grid_id.eq(gid)&np.isfinite(frame.x)&np.isfinite(frame[exp05.Y10])]
                    ref=refs.loc[gid]
                    ax.scatter(part.x,part[exp05.Y10],s=12,c=part.yield_year,cmap="viridis",alpha=.75)
                    if ref.linear_status=="fit":
                        x=np.linspace(ref.x_p10,ref.x_p90,60)
                        y=part[exp05.Y10].mean()+ref.linear_beta_per_raw_unit*(x-part.x.mean())
                        ax.plot(x,y,color="#3e77b6",lw=1)
                    if ref.quadratic_status=="fit":
                        x=np.linspace(ref.x_p10,ref.x_p90,60)
                        z=(part.x-ref.x_ref_mean)/ref.x_ref_sd
                        zz=z.to_numpy()
                        intercept=part[exp05.Y10].mean()-ref.quadratic_b*zz.mean()-ref.quadratic_c*(zz**2).mean()
                        line=intercept+ref.quadratic_b*(x-ref.x_ref_mean)/ref.x_ref_sd+ref.quadratic_c*((x-ref.x_ref_mean)/ref.x_ref_sd)**2
                        ax.plot(x,line,color="#cf6947",lw=1)
                    lo,hi=ax.get_ylim()
                    ax.vlines(part.x,lo,lo+.025*(hi-lo),color="#3f3f3f",alpha=.35,lw=.5)
                    ax.set_title(f"{gid}\nn={len(part)}; {ref.quadratic_status}",fontsize=8)
                    ax.tick_params(labelsize=7)
                    ax.set_xlabel("weather, raw unit",fontsize=7);ax.set_ylabel("yield residual, t/ha",fontsize=7)
                for ax in list(axes.flat)[len(grids[offset:offset+12]):]:ax.axis("off")
                fig.suptitle(cid+" | all paired years; lines within P10–P90",fontsize=12)
                pdf.savefig(fig);plt.close(fig)
    # Compact all-candidate spatial slope and curvature atlases.
    for field,name in (("linear_beta_per_raw_unit","grid_linear_slopes.pdf"),
                       ("quadratic_c","grid_quadratic_curvature.pdf")):
        with PdfPages(figdir/name) as pdf:
            for cid,part in estimates.groupby("candidate_id",sort=True):
                fig,ax=plt.subplots(figsize=(7.5,5.4))
                s=part.loc[np.isfinite(part[field])]
                if len(s):
                    vmax=np.quantile(np.abs(s[field]),.95)
                    vmax=max(float(vmax),1e-12)
                    sc=ax.scatter(s.grid_longitude,s.grid_latitude,c=s[field],cmap="coolwarm",
                                  vmin=-vmax,vmax=vmax,s=34,edgecolors="black",linewidths=.25)
                    fig.colorbar(sc,ax=ax,label=field)
                ax.set(title=f"{cid} | {len(s)}/{len(part)} estimable grids",xlabel="Longitude",ylabel="Latitude")
                pdf.savefig(fig);plt.close(fig)
    for cid in ("relative_humidity__dec_jan","deep_soil_moisture_28_100__dec_jan"):
        part=panel.loc[panel.candidate_id.eq(cid)&np.isfinite(panel.x)&np.isfinite(panel.dec)&np.isfinite(panel.jan)]
        fig,ax=plt.subplots(figsize=(7,5))
        ax.scatter(part.x,(part.jan-part.dec)/2,s=7,alpha=.24)
        ax.set(xlabel="A=(Dec+Jan)/2",ylabel="D=(Jan-Dec)/2",title=f"Observed A/D joint support: {cid}")
        fig.tight_layout();fig.savefig(figdir/f"ad_support_{cid}.png",dpi=150);plt.close(fig)


def summarize(candidates, panel, estimates, pooled, aggregate, loyo, bootstrap=None):
    rows=[]
    for r in candidates.itertuples():
        e=estimates.loc[estimates.candidate_id.eq(r.candidate_id)]
        l=e.loc[e.linear_status.eq("fit")]
        q=e.loc[e.quadratic_status.eq("fit")]
        p=pooled.loc[pooled.candidate_id.eq(r.candidate_id)&pooled.target.eq(exp05.Y10)&
                     pooled.grid_weighting.eq("equal")]
        pq=p.loc[p.model.eq("PQ")]
        rows.append({"candidate_id":r.candidate_id,"conceptual_variable":r.conceptual_variable,
            "source_months":r.source_months,"raw_source_variable":r.raw_source_variable,
            "conditional_information_flag":r.conditional_information_flag,
            "n_frozen_grids":len(e),"n_linear_grids":len(l),"n_quadratic_grids":len(q),
            "linear_positive_grids":int(l.linear_beta_per_raw_unit.gt(0).sum()),
            "linear_negative_grids":int(l.linear_beta_per_raw_unit.lt(0).sum()),
            "linear_median_raw_beta":l.linear_beta_per_raw_unit.median(),
            "linear_q25_raw_beta":l.linear_beta_per_raw_unit.quantile(.25),
            "linear_q75_raw_beta":l.linear_beta_per_raw_unit.quantile(.75),
            "linear_median_iqr_contrast_tch":l.linear_iqr_contrast.median(),
            "curvature_positive_grids":int(q.quadratic_c.gt(0).sum()),
            "curvature_negative_grids":int(q.quadratic_c.lt(0).sum()),
            "curvature_median_c":q.quadratic_c.median(),
            "median_segment_slope_difference_raw":q.segment_slope_difference_raw.median(),
            "pooled_pq_c":pq.c.iloc[0] if len(pq) else np.nan,
            "pooled_pq_delta_r2":pq.delta_r2_vs_linear.iloc[0] if len(pq) else np.nan,
            "linear_direction_label":"predominantly_positive" if len(l) and l.linear_beta_per_raw_unit.gt(0).mean()>.7 else
                    "predominantly_negative" if len(l) and l.linear_beta_per_raw_unit.lt(0).mean()>.7 else "spatially_mixed",
            "curvature_label":"diagnostic_only; review block intervals, LOYO, target and tail support"})
    result=pd.DataFrame(rows)
    if len(result)!=38:
        raise ValueError("Summary lost a candidate")
    return result


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",choices=("deterministic","full"),default="full")
    args=parser.parse_args(argv)
    OUT.mkdir(parents=True,exist_ok=True);PROC.mkdir(parents=True,exist_ok=True)
    candidates=load_universe()
    panel,lineage=build_panel(candidates)
    candidates.to_csv(OUT/"candidate_manifest.csv",index=False)
    panel.to_csv(PROC/"candidate_grid_year_panel.csv",index=False)
    grid=primary_grids(panel,candidates)
    grid.to_csv(OUT/"grid_response_estimates.csv",index=False)
    support=grid[["candidate_id","grid_id","target","n","years","first_year","last_year",
                  "missing_x","missing_y","partial_weather_rows","linear_status","quadratic_status"]].copy()
    support.to_csv(OUT/"sample_support.csv",index=False)
    pooled=pooled_models(panel,grid)
    pooled.to_csv(OUT/"pooled_response_estimates.csv",index=False)
    aggregate=aggregate_diagnostics(panel,grid)
    aggregate.to_csv(OUT/"temporal_aggregation_diagnostics.csv",index=False)
    aggregate_pooled=pooled_aggregate_diagnostics(panel,aggregate)
    aggregate_pooled.to_csv(OUT/"pooled_temporal_aggregation_diagnostics.csv",index=False)
    robust=target_robustness(panel,grid)
    robust.to_csv(OUT/"target_robustness_comparisons.csv",index=False)
    pooled_targets=pd.concat([pooled_models(panel,grid,target=t,matched=True) for t in TARGETS],ignore_index=True)
    baseline=pooled_targets.loc[pooled_targets.target.eq(exp05.Y10),
        ["candidate_id","model","grid_weighting","within_r2","c"]].rename(columns={
        "within_r2":"primary_common_within_r2","c":"primary_common_c"})
    pooled_targets=pooled_targets.merge(baseline,on=["candidate_id","model","grid_weighting"],validate="many_to_one")
    pooled_targets["paired_delta_within_r2_vs_primary"]=pooled_targets.within_r2-pooled_targets.primary_common_within_r2
    pooled_targets["paired_delta_c_vs_primary"]=pooled_targets.c-pooled_targets.primary_common_c
    pooled_targets.to_csv(OUT/"target_pooled_comparisons.csv",index=False)
    loyo=leave_one_year_out(panel,grid,pooled)
    loyo.to_csv(OUT/"leave_one_year_out_diagnostics.csv",index=False)
    summary=summarize(candidates,panel,grid,pooled,aggregate,loyo)
    summary.to_csv(OUT/"candidate_response_summary.csv",index=False)
    conf={"commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
          "input_sha256":{"universe":fingerprint(UNIVERSE),
             "targets":fingerprint(exp05.source_paths(ROOT)["grid_targets"]),
             "weights":fingerprint(exp05.source_paths(ROOT)["municipality_weights"])},
          "primary_target":exp05.Y10,"robustness_targets":[exp05.Y12,exp05.YFIX],
          "linear_min_n":MIN_L,"quadratic_min_n":MIN_Q,"condition_max":COND_MAX,
          "candidate_count":len(candidates),"candidate_grid_year_rows":len(panel),
          "weather_alignment":{"-4":"Dec(t-1)","-3":"Jan(t)","-2":"Feb(t)","-1":"Mar(t)","0":"Apr(t)"},
          "weather_years":[lineage["weather_year_min"],lineage["weather_year_max"]],
          "lineage":lineage["target_lineage"],"partial_weather_support_rows":lineage["partial_weather_support_rows"]}
    (OUT/"config.json").write_text(json.dumps(conf,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_count":len(candidates),"grid_rows":len(grid),
        "linear_fits":int(grid.linear_status.eq("fit").sum()),
        "quadratic_fits":int(grid.quadratic_status.eq("fit").sum()),
        "partial_weather":lineage["partial_weather_support_rows"]},indent=2))
    if args.stage=="full":
        make_figures(panel,grid,pooled,aggregate)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
