"""Fixed-roster synchronized bootstrap for EXP-05B.

The original N>=20 gate selects grids once. Bootstrap repeats never reapply it.
An attempt is invalid for an estimand if the frozen grid roster cannot be fit
with adequate numerical identification. No grid is dropped within an attempt.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from analysis import exp05_conditional_temperature_vpd as exp05
from analysis import exp05b_moisture_conditioning as base


YEARS = np.arange(exp05.WEATHER_SOURCE_START, exp05.WEATHER_SOURCE_END + 1)
CONDITION_MAX = 1e8
RESIDUAL_VARIANCE_FRACTION_MIN = 1e-8
RAW_PREDICTOR_SD_MIN = 1e-10
MAX_COEFFICIENT_OVER_Y_SD = 1e4
LOCAL_ADDITIVE_MIN_ROWS = 4


@dataclass(frozen=True)
class Cube:
    scenario: str
    modifier: str
    target: str
    month_slot: int
    label: str
    grids: tuple[str, ...]
    values: np.ndarray  # grid x calendar year x (Y, T, V, S), NaN for absent
    s25: np.ndarray  # original physical S quartiles, never resampled
    s75: np.ndarray


def scenarios() -> list[tuple[str, str, str, str | None, str | None]]:
    primary = "sm_28_100_prev3_mean"
    result = [("primary", primary, exp05.Y10, None, None)]
    result += [(f"modifier_{m}", m, exp05.Y10, primary, None)
               for m in base.MODIFIERS if m != primary]
    result += [(f"target_{y}", primary, y, None, exp05.Y10)
               for y in (exp05.Y12, exp05.YFIX)]
    return result


def prepare_cubes(panel: pd.DataFrame) -> dict[tuple[str, int], Cube]:
    cubes = {}
    for scenario, modifier, target, matched_modifier, matched_target in scenarios():
        for slot, data in base.make_series(panel, modifier, target,
                                           matched_modifier, matched_target).items():
            grids = tuple(sorted(data.grid_id.unique()))
            if len(grids) != 76:
                raise ValueError(f"Original observed-grid roster changed: {scenario} {slot}: {len(grids)}")
            gidx = {grid: i for i, grid in enumerate(grids)}
            arr = np.full((len(grids), len(YEARS), 4), np.nan)
            s25 = np.empty(len(grids))
            s75 = np.empty(len(grids))
            for grid, part in data.groupby("grid_id", sort=True):
                i = gidx[grid]
                s25[i], s75[i] = np.quantile(part[modifier], [.25, .75])
                for row in part.itertuples(index=False):
                    year = int(row.yield_year)
                    if year not in YEARS:
                        raise ValueError("Paired yield year outside bootstrap calendar")
                    if np.isfinite(arr[i, year-YEARS[0], 0]):
                        raise ValueError("Duplicate grid/yield-year bootstrap key")
                    arr[i, year-YEARS[0]] = [getattr(row, target), getattr(row, exp05.TEMP),
                                              getattr(row, exp05.VPD), getattr(row, modifier)]
            cubes[scenario, slot] = Cube(scenario, modifier, target, slot,
                                         str(data.calendar_month_label.iloc[0]), grids, arr, s25, s75)
    # Pairwise comparisons must have precisely identical calendar masks and grids.
    primary = "sm_28_100_prev3_mean"
    for slot in range(-15, 1):
        for scenario, _, _, _, _ in scenarios()[1:]:
            alt = cubes[scenario, slot]
            primary_cube = cubes["primary", slot]
            if alt.grids != primary_cube.grids or not np.array_equal(
                np.isfinite(alt.values[:,:,0]), np.isfinite(primary_cube.values[:,:,0])):
                raise ValueError(f"Current matched comparator requires a separately refit primary cube: {scenario} {slot}")
            matched = base.analysis_mask(panel, primary, exp05.Y10,
                alt.modifier if scenario.startswith("modifier_") else None,
                alt.target if scenario.startswith("target_") else None)
            expected = panel.loc[matched & panel.month_slot.eq(slot)]
            expected = expected.loc[expected.grid_id.isin(alt.grids)]
            pair_keys = set(zip(expected.grid_id, expected.yield_year))
            actual = {(grid, int(YEARS[j])) for i, grid in enumerate(alt.grids)
                      for j in np.flatnonzero(np.isfinite(alt.values[i,:,0]))}
            if actual != pair_keys:
                raise ValueError(f"Paired comparison mask changed: {scenario} {slot}")
    return cubes


def draw_counts(attempts: int, block: int, seed: int) -> np.ndarray:
    draws = base.synchronized_draws(attempts, block, seed)
    return np.array([[draw[int(year)] for year in YEARS] for draw in draws], dtype=np.int16)


def _condition(xx: np.ndarray) -> float:
    singular = np.linalg.svd(xx, compute_uv=False)
    if singular[-1] <= 0:
        return np.inf
    return float(np.sqrt(singular[0]/singular[-1]))


def fit_cube(cube: Cube, counts: np.ndarray, *, full_primary: bool = False) -> dict[str, object]:
    """Equal-total-grid-weight FE fit from compact weighted cross-products."""
    if counts.shape != (len(YEARS),) or np.any(counts < 0):
        raise ValueError("Invalid synchronized calendar-year count vector")
    present = np.isfinite(cube.values).all(axis=2)
    w_raw = present * counts[None,:]
    n = w_raw.sum(axis=1)
    row: dict[str, object] = {"status":"estimable", "n_fixed_grids":len(cube.grids),
        "n_estimable_grids":len(cube.grids), "min_resampled_grid_n":int(n.min()),
        "n_below_original_n20":int(np.sum(n<exp05.MIN_PRIMARY_N)),
        "failure_reason":"", "failed_grids":""}
    if np.any(n < LOCAL_ADDITIVE_MIN_ROWS):
        bad=np.flatnonzero(n<LOCAL_ADDITIVE_MIN_ROWS)
        return {**row,"status":"invalid","failure_reason":"grid_n_below_local_additive_rank_minimum",
                "failed_grids":";".join(cube.grids[i] for i in bad),
                "n_estimable_grids":0}
    values=np.nan_to_num(cube.values,nan=0.0)
    means=np.einsum("gy,gyp->gp",w_raw,values,optimize=True)/n[:,None]
    centered=values-means[:,None,:]
    variance=np.einsum("gy,gyp->gp",w_raw,centered**2,optimize=True)/(n[:,None]-1)
    sd=np.sqrt(np.maximum(variance,0))
    if not np.isfinite(sd).all() or np.any(sd[:,1:] <= RAW_PREDICTOR_SD_MIN) or np.any(sd[:,0] <= 1e-10):
        bad=np.flatnonzero(np.any(sd[:,1:]<=RAW_PREDICTOR_SD_MIN,axis=1)|(sd[:,0]<=1e-10))
        return {**row,"status":"invalid","failure_reason":"near_constant_y_or_predictor",
                "failed_grids":";".join(cube.grids[i] for i in bad),
                "n_estimable_grids":0}
    w=w_raw/n[:,None]  # each original grid contributes total weight one
    z=centered[:,:,1:]/sd[:,None,1:]
    t,v,s=np.moveaxis(z,2,0)
    raw_design=np.stack([t,v,s,t*s,v*s,t*t,v*v,s*s,t*v],axis=2)
    mean_design=np.einsum("gy,gyp->gp",w,raw_design,optimize=True)
    x=raw_design-mean_design[:,None,:]
    y=centered[:,:,0]
    xx=np.einsum("gy,gyp,gyq->pq",w,x,x,optimize=True)
    xy=np.einsum("gy,gyp,gy->p",w,x,y,optimize=True)
    yy=float(np.einsum("gy,gy,gy->",w,y,y,optimize=True))
    if not np.isfinite(xx).all() or not np.isfinite(xy).all() or yy<=1e-18:
        return {**row,"status":"invalid","failure_reason":"nonfinite_or_constant_pooled_design",
                "n_estimable_grids":0}
    # Local T/V identifiability after conditioning on the other atmosphere
    # variable and S. This is stricter than pooled full rank alone.
    local=np.einsum("gy,gyp,gyq->gpq",w,z,z,optimize=True)
    local_cond=np.linalg.cond(local)
    if not np.isfinite(local_cond).all():
        return {**row,"status":"invalid","failure_reason":"singular_local_t_v_s_design",
                "n_estimable_grids":0}
    max_local_cond=float(np.sqrt(local_cond.max()))
    row["max_local_additive_condition"]=max_local_cond
    if max_local_cond>CONDITION_MAX:
        bad=np.flatnonzero(np.sqrt(local_cond)>CONDITION_MAX)
        return {**row,"status":"invalid","failure_reason":"ill_conditioned_local_t_v_s_design",
                "failed_grids":";".join(cube.grids[i] for i in bad),"n_estimable_grids":0}
    inv_local=np.linalg.inv(local)
    fractions=1/np.diagonal(inv_local,axis1=1,axis2=2)
    row["min_residual_t_variance_fraction"]=float(fractions[:,0].min())
    row["min_residual_v_variance_fraction"]=float(fractions[:,1].min())
    row["min_residual_s_variance_fraction"]=float(fractions[:,2].min())
    if np.any(fractions<=RESIDUAL_VARIANCE_FRACTION_MIN):
        bad=np.flatnonzero(np.any(fractions<=RESIDUAL_VARIANCE_FRACTION_MIN,axis=1))
        return {**row,"status":"invalid","failure_reason":"insufficient_residual_predictor_variation",
                "failed_grids":";".join(cube.grids[i] for i in bad),"n_estimable_grids":0}
    delta_s=(cube.s25-cube.s75)/sd[:,3]
    if not np.isfinite(delta_s).all():
        return {**row,"status":"invalid","failure_reason":"nonfinite_frozen_quartile_scale","n_estimable_grids":0}
    row["mean_frozen_dry_minus_wet_s_z"]=float(delta_s.mean())
    model_names=("P0","P1","P2","Q1","Q2","Q1_prime","Q2_prime") if full_primary else ("P0","P1","P2")
    y_sd=float(np.sqrt(yy/len(cube.grids)))
    for model in model_names:
        cols=base.MODELS[model]
        x_model=xx[np.ix_(cols,cols)]
        cond=_condition(x_model)
        row[f"condition_{model}"]=cond
        if not np.isfinite(cond) or cond>CONDITION_MAX:
            return {**row,"status":"invalid","failure_reason":f"ill_conditioned_{model}","n_estimable_grids":0}
        try:
            beta=np.linalg.solve(x_model,xy[cols])
        except np.linalg.LinAlgError:
            return {**row,"status":"invalid","failure_reason":f"rank_deficient_{model}","n_estimable_grids":0}
        if not np.isfinite(beta).all() or np.max(np.abs(beta))/y_sd>MAX_COEFFICIENT_OVER_Y_SD:
            return {**row,"status":"invalid","failure_reason":f"extreme_or_nonfinite_coefficient_{model}",
                    "n_estimable_grids":0}
        r2=float(beta@xy[cols]/yy)
        if not np.isfinite(r2) or r2 < -1e-8 or r2 > 1+1e-8:
            return {**row,"status":"invalid","failure_reason":f"invalid_r2_{model}","n_estimable_grids":0}
        row[f"r2_{model}"]=r2
        for j,b in zip(cols,beta):
            row[f"beta_{model}_{j}"]=float(b)
        if model in ("P2","Q2","Q2_prime"):
            row[f"dry_minus_wet_t_{model}"]=float(beta[cols.index(3)]*delta_s.mean())
            row[f"dry_minus_wet_v_{model}"]=float(beta[cols.index(4)]*delta_s.mean())
    for reduced,full in (("P0","P1"),("P1","P2"),("Q1","Q2"),("Q1_prime","Q2_prime")):
        if reduced in model_names and full in model_names:
            diff=row[f"r2_{full}"]-row[f"r2_{reduced}"]
            if diff < -1e-8:
                return {**row,"status":"invalid","failure_reason":f"nesting_violation_{full}","n_estimable_grids":0}
            row[f"delta_r2_{full}_vs_{reduced}"]=float(diff)
    if full_primary:
        # Frisch-Waugh-Lovell reduction: each grid has its own additive T/V/S
        # slopes; only the two moisture interactions are common across grids.
        a=local
        z_cross=np.einsum("gy,gyp,gyq->gpq",w,z,x[:,:,3:5],optimize=True)
        y_cross=np.einsum("gy,gyp,gy->gp",w,z,y,optimize=True)
        zz=np.einsum("gy,gyp,gyq->gpq",w,x[:,:,3:5],x[:,:,3:5],optimize=True)
        zy=np.einsum("gy,gyp,gy->gp",w,x[:,:,3:5],y,optimize=True)
        yyi=np.einsum("gy,gy,gy->g",w,y,y,optimize=True)
        a_inv_z=np.linalg.solve(a,z_cross)
        a_inv_y=np.linalg.solve(a,y_cross[:,:,None])[:,:,0]
        residual_zz=(zz-np.einsum("gpi,gpj->gij",z_cross,a_inv_z,optimize=True)).sum(axis=0)
        residual_zy=(zy-np.einsum("gpi,gp->gi",z_cross,a_inv_y,optimize=True)).sum(axis=0)
        reduced_sse=float((yyi-np.einsum("gp,gp->g",y_cross,a_inv_y,optimize=True)).sum())
        spatial_cond=_condition(residual_zz)
        row["condition_spatial_interactions"]=spatial_cond
        if not np.isfinite(spatial_cond) or spatial_cond>CONDITION_MAX or reduced_sse<=1e-18:
            row["spatial_status"]="invalid"
            row["spatial_failure_reason"]="ill_conditioned_or_zero_residual_spatial_interactions"
        else:
            spatial_beta=np.linalg.solve(residual_zz,residual_zy)
            if not np.isfinite(spatial_beta).all() or np.max(np.abs(spatial_beta))/y_sd>MAX_COEFFICIENT_OVER_Y_SD:
                row["spatial_status"]="invalid"
                row["spatial_failure_reason"]="extreme_or_nonfinite_spatial_coefficient"
            else:
                row["spatial_status"]="estimable"
                row["spatial_failure_reason"]=""
                row["beta_spatial_ts"]=float(spatial_beta[0])
                row["beta_spatial_vs"]=float(spatial_beta[1])
                row["dry_minus_wet_t_spatial"]=float(spatial_beta[0]*delta_s.mean())
                row["dry_minus_wet_v_spatial"]=float(spatial_beta[1]*delta_s.mean())
                row["delta_r2_spatial_interactions"]=float(spatial_beta@residual_zy/yy)
    return row


def validate_deterministic_equivalence(cubes: dict[tuple[str,int],Cube],
                                       deterministic: pd.DataFrame) -> pd.DataFrame:
    errors=[]
    ones=np.ones(len(YEARS),dtype=np.int16)
    for (scenario,slot),cube in cubes.items():
        fitted=fit_cube(cube,ones,full_primary=scenario=="primary")
        if fitted["status"]!="estimable" or (scenario=="primary" and fitted["spatial_status"]!="estimable"):
            raise ValueError(f"New bootstrap engine fails original point-estimate design: {scenario}, {slot}, {fitted}")
        old=deterministic.loc[deterministic.scenario.eq(scenario)&deterministic.month_slot.eq(slot)]
        if len(old)!=1:
            raise ValueError("Missing original frozen deterministic result")
        old=old.iloc[0]
        for key in ("r2_P0","r2_P1","r2_P2","dry_minus_wet_t_P2","dry_minus_wet_v_P2"):
            error=abs(float(fitted[key])-float(old[key]))
            errors.append({"scenario":scenario,"month_slot":slot,"estimand":key,"abs_error":error})
            if error>1e-9:
                raise ValueError(f"Bootstrap engine changes deterministic {scenario} {slot} {key}: {error}")
        if scenario=="primary":
            for key in ("r2_Q1","r2_Q2","r2_Q1_prime","r2_Q2_prime",
                        "dry_minus_wet_v_Q2","dry_minus_wet_v_Q2_prime"):
                error=abs(float(fitted[key])-float(old[key]))
                errors.append({"scenario":scenario,"month_slot":slot,"estimand":key,"abs_error":error})
                if error>1e-9:
                    raise ValueError(f"Bootstrap engine changes deterministic {scenario} {slot} {key}: {error}")
            for key,new in (("spatial_dry_minus_wet_v_grid_slope","dry_minus_wet_v_spatial"),
                            ("spatial_dry_minus_wet_t_grid_slope","dry_minus_wet_t_spatial")):
                error=abs(float(fitted[new])-float(old[key]))
                errors.append({"scenario":scenario,"month_slot":slot,"estimand":key,"abs_error":error})
                if error>1e-9:
                    raise ValueError(f"Bootstrap engine changes deterministic {scenario} {slot} {key}: {error}")
    return pd.DataFrame(errors)


def run_stage(cubes: dict[tuple[str,int],Cube], output: Path, *, attempts: int,
              stage: str, block: int, seed: int) -> pd.DataFrame:
    draws=draw_counts(attempts,block,seed)
    rows=[]
    for attempt,counts in enumerate(draws,1):
        for (scenario,slot),cube in cubes.items():
            result=fit_cube(cube,counts,full_primary=scenario=="primary")
            result.update({"stage":stage,"block_length_years":block,"seed":seed,
                           "attempt":attempt,"scenario":scenario,"month_slot":slot,
                           "calendar_month_label":cube.label})
            rows.append(result)
    result=pd.DataFrame(rows)
    name=f"bootstrap_{stage}_block{block}_attempts.csv"
    result.to_csv(output/name,index=False)
    return result


def preflight_summary(smoke: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (scenario,slot,block),part in smoke.groupby(["scenario","month_slot","block_length_years"]):
        failures=part.loc[part.status.ne("estimable")]
        spatial=part.spatial_status if scenario=="primary" else pd.Series([],dtype=object)
        rows.append({"scenario":scenario,"month_slot":slot,"block_length_years":block,
            "n_attempted":len(part),"n_pooled_valid":int(part.status.eq("estimable").sum()),
            "n_pooled_failed":len(failures),"pooled_failure_reasons":";".join(sorted(failures.failure_reason.dropna().unique())),
            "n_spatial_valid":int(spatial.eq("estimable").sum()) if scenario=="primary" else np.nan,
            "n_spatial_failed":int(spatial.ne("estimable").sum()) if scenario=="primary" else np.nan,
            "spatial_failure_reasons":";".join(sorted(part.spatial_failure_reason.dropna().unique())) if scenario=="primary" else "",
            "n_below_original_n20_max":int(part.n_below_original_n20.max()),
            "min_resampled_grid_n":int(part.min_resampled_grid_n.min()),
            "max_local_additive_condition":part.max_local_additive_condition.max(),
            "min_residual_t_variance_fraction":part.min_residual_t_variance_fraction.min(),
            "min_residual_v_variance_fraction":part.min_residual_v_variance_fraction.min(),
            "min_residual_s_variance_fraction":part.min_residual_s_variance_fraction.min(),
            "max_p2_condition":part.condition_P2.max()})
    return pd.DataFrame(rows)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",choices=["preflight","final"],required=True)
    parser.add_argument("--block",type=int,choices=[1,3,5],default=None)
    args=parser.parse_args()
    root=base.exp05.project_root()
    output=root/"outputs/research/exp_05b"
    panel=pd.read_pickle(output/"panel.pkl")
    deterministic=pd.read_csv(output/"monthly_interaction_results.csv")
    cubes=prepare_cubes(panel)
    validation=validate_deterministic_equivalence(cubes,deterministic)
    validation.to_csv(output/"bootstrap_engine_equivalence.csv",index=False)
    config=json.loads((output/"analysis_config.json").read_text(encoding="utf-8"))
    config["bootstrap"]["original_grid_n20_applies_only_at_selection"] = True
    config["bootstrap"]["numerical_guards"]={"condition_max":CONDITION_MAX,
        "min_residual_variance_fraction":RESIDUAL_VARIANCE_FRACTION_MIN,
        "min_raw_predictor_sd":RAW_PREDICTOR_SD_MIN,
        "max_abs_coefficient_over_pooled_within_grid_y_sd":MAX_COEFFICIENT_OVER_Y_SD,
        "min_resampled_rows_for_local_additive_rank":LOCAL_ADDITIVE_MIN_ROWS}
    config["grid_support"]="original observed N>=20 fixes 76-grid roster; resampled N<20 allowed if all required designs full-rank and numerically stable; any invalid attempt remains invalid"
    config["bootstrap"]["smoke_seed_by_block"]={str(b):20261012+b for b in (1,3,5)}
    config["bootstrap"]["final_seed_by_block"]={str(b):20261013+b for b in (1,3,5)}
    (output/"analysis_config.json").write_text(json.dumps(config,indent=2),encoding="utf-8")
    if args.stage=="preflight":
        frames=[run_stage(cubes,output,attempts=50,stage="smoke",block=block,seed=20261012+block)
                for block in (1,3,5)]
        summary=preflight_summary(pd.concat(frames,ignore_index=True))
        summary.to_csv(output/"bootstrap_smoke_model_preflight_summary.csv",index=False)
    else:
        if args.block is None:
            parser.error("--block is required for final stage")
        run_stage(cubes,output,attempts=1000,stage="final",block=args.block,
                  seed=20261013+args.block)


if __name__=="__main__":
    main()
