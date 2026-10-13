"""EXP-05B final interval inventory, paired robustness and fixed figures."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from analysis import exp05_conditional_temperature_vpd as exp05
from analysis import exp05b_moisture_conditioning as base
from analysis import exp05b_fixed_grid_bootstrap as boot


CORE_ESTIMANDS = (
    "r2_P0", "r2_P1", "r2_P2", "delta_r2_P1_vs_P0", "delta_r2_P2_vs_P1",
    "beta_P2_3", "beta_P2_4", "dry_minus_wet_t_P2", "dry_minus_wet_v_P2",
)
PRIMARY_EXTRA = (
    "r2_Q1", "r2_Q2", "r2_Q1_prime", "r2_Q2_prime",
    "delta_r2_Q2_vs_Q1", "delta_r2_Q2_prime_vs_Q1_prime",
    "beta_Q2_3", "beta_Q2_4", "beta_Q2_prime_3", "beta_Q2_prime_4",
    "dry_minus_wet_t_Q2", "dry_minus_wet_v_Q2",
    "dry_minus_wet_t_Q2_prime", "dry_minus_wet_v_Q2_prime",
    "beta_spatial_ts", "beta_spatial_vs",
    "dry_minus_wet_t_spatial", "dry_minus_wet_v_spatial",
    "delta_r2_spatial_interactions",
)
PAIRED_ESTIMANDS = ("dry_minus_wet_t_P2", "dry_minus_wet_v_P2",
                    "delta_r2_P2_vs_P1", "beta_P2_3", "beta_P2_4")


def interval(values: pd.Series | np.ndarray) -> tuple[float,float]:
    array=np.asarray(values,dtype=float)
    array=array[np.isfinite(array)]
    if not len(array):
        return np.nan,np.nan
    return tuple(map(float,np.quantile(array,[.025,.975])))


def load_attempts(output: Path) -> pd.DataFrame:
    frames=[]
    for block in (1,3,5):
        path=output/f"bootstrap_final_block{block}_attempts.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        frame=pd.read_csv(path)
        if frame.groupby(["scenario","month_slot"]).size().nunique()!=1:
            raise ValueError("Incomplete final attempt roster")
        if frame.groupby(["scenario","month_slot"]).size().iloc[0]!=1000:
            raise ValueError("Final stage does not contain 1000 attempts per estimand")
        frames.append(frame)
    result=pd.concat(frames,ignore_index=True)
    if result.duplicated(["block_length_years","attempt","scenario","month_slot"]).any():
        raise ValueError("Duplicate bootstrap attempt key")
    return result


def summarize_attempts(attempts: pd.DataFrame, deterministic: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    diagnostics=[]; estimates=[]
    for (scenario,slot,block),part in attempts.groupby(["scenario","month_slot","block_length_years"]):
        original=deterministic.loc[deterministic.scenario.eq(scenario)&deterministic.month_slot.eq(slot)]
        if len(original)!=1:
            raise ValueError(f"Missing deterministic point estimate: {scenario} {slot}")
        original=original.iloc[0]
        for estimand in CORE_ESTIMANDS + (PRIMARY_EXTRA if scenario=="primary" else ()):
            if estimand not in part:
                raise ValueError(f"Missing bootstrap estimand {estimand}")
            spatial=estimand.endswith("_spatial") or estimand.startswith("beta_spatial_") or estimand=="delta_r2_spatial_interactions"
            valid=part[estimand].notna() & part.status.eq("estimable")
            if spatial:
                valid &= part.spatial_status.eq("estimable")
            n_valid=int(valid.sum())
            low,high=interval(part.loc[valid,estimand])
            if spatial:
                point_col={"beta_spatial_ts":"spatial_beta_grid_slope_ts",
                           "beta_spatial_vs":"spatial_beta_grid_slope_vs",
                           "dry_minus_wet_t_spatial":"spatial_dry_minus_wet_t_grid_slope",
                           "dry_minus_wet_v_spatial":"spatial_dry_minus_wet_v_grid_slope",
                           "delta_r2_spatial_interactions":"spatial_delta_r2_grid_slope_interaction"}[estimand]
            else:
                point_col=estimand
            point=float(original[point_col])
            reasons=part.loc[~valid,"failure_reason"].fillna("").tolist()
            if spatial:
                reasons += part.loc[~valid,"spatial_failure_reason"].fillna("").tolist()
            reasons=";".join(sorted({str(x) for x in reasons if str(x)}))
            diagnostics.append({"scenario":scenario,"month_slot":slot,"block_length_years":block,
                "estimand":estimand,"n_attempted":len(part),"n_valid":n_valid,
                "n_failed":len(part)-n_valid,"failure_rate":1-n_valid/len(part),
                "failure_reasons":reasons,"ci_low":low,"ci_high":high,
                "interval_method":"pointwise percentile of valid attempted synchronized calendar-year resamples; no retries",
                "conditional_on_success":n_valid<len(part)})
            estimates.append({"scenario":scenario,"month_slot":slot,
                "calendar_month_label":part.calendar_month_label.iloc[0],
                "block_length_years":block,"estimand":estimand,"point":point,
                "ci_low":low,"ci_high":high,"n_valid":n_valid,
                "n_attempted":len(part)})
    return pd.DataFrame(diagnostics),pd.DataFrame(estimates)


def paired_robustness(attempts: pd.DataFrame, deterministic: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (block,slot),month in attempts.groupby(["block_length_years","month_slot"]):
        primary=month.loc[month.scenario.eq("primary")].set_index("attempt")
        for scenario in sorted(set(month.scenario)-{"primary"}):
            alt=month.loc[month.scenario.eq(scenario)].set_index("attempt")
            if not primary.index.equals(alt.index):
                raise ValueError("Paired comparisons did not use identical draw indices")
            baseline_name="primary_matched_" + scenario.split("_",1)[1]
            point_primary=deterministic.loc[deterministic.scenario.eq(baseline_name)&deterministic.month_slot.eq(slot)]
            point_alt=deterministic.loc[deterministic.scenario.eq(scenario)&deterministic.month_slot.eq(slot)]
            if len(point_primary)!=1 or len(point_alt)!=1:
                raise ValueError(f"Missing matched deterministic pair: {scenario} {slot}")
            point_primary,point_alt=point_primary.iloc[0],point_alt.iloc[0]
            for estimand in PAIRED_ESTIMANDS:
                if abs(float(point_primary[estimand])-float(deterministic.loc[
                    deterministic.scenario.eq("primary")&deterministic.month_slot.eq(slot),estimand].iloc[0]))>1e-9:
                    raise ValueError("Matched-primary point differs; separate primary bootstrap cube required")
                valid=primary.status.eq("estimable") & alt.status.eq("estimable") & primary[estimand].notna() & alt[estimand].notna()
                delta=alt.loc[valid,estimand]-primary.loc[valid,estimand]
                low,high=interval(delta)
                rows.append({"scenario":scenario,"month_slot":slot,
                    "calendar_month_label":primary.calendar_month_label.iloc[0],
                    "block_length_years":block,"estimand":estimand,
                    "primary_matched_point":float(point_primary[estimand]),
                    "alternative_point":float(point_alt[estimand]),
                    "alternative_minus_primary_point":float(point_alt[estimand]-point_primary[estimand]),
                    "paired_delta_ci_low":low,"paired_delta_ci_high":high,
                    "n_attempted":len(primary),"n_joint_valid":int(valid.sum()),
                    "n_joint_failed":int((~valid).sum()),
                    "support_note":"current data have exact pairwise grid/year mask equality; verified before fit"})
    return pd.DataFrame(rows)


def leave_one_calendar_year_out(panel: pd.DataFrame, cubes: dict[tuple[str,int],boot.Cube],
                                deterministic: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for slot in range(-15,1):
        cube=cubes["primary",slot]
        point=deterministic.loc[deterministic.scenario.eq("primary")&deterministic.month_slot.eq(slot)].iloc[0]
        for year in boot.YEARS:
            counts=np.ones(len(boot.YEARS),dtype=np.int16)
            counts[year-boot.YEARS[0]]=0
            fit=boot.fit_cube(cube,counts,full_primary=True)
            rows.append({"month_slot":slot,"calendar_month_label":cube.label,
                "left_out_calendar_year":int(year),"status":fit["status"],
                "failure_reason":fit.get("failure_reason",""),
                "spatial_status":fit.get("spatial_status",""),
                "dry_minus_wet_v_point":point.dry_minus_wet_v_P2,
                "dry_minus_wet_v_loyo":fit.get("dry_minus_wet_v_P2",np.nan),
                "dry_minus_wet_t_point":point.dry_minus_wet_t_P2,
                "dry_minus_wet_t_loyo":fit.get("dry_minus_wet_t_P2",np.nan),
                "spatial_dry_minus_wet_v_loyo":fit.get("dry_minus_wet_v_spatial",np.nan)})
    return pd.DataFrame(rows)


def slope_profiles(panel: pd.DataFrame, deterministic: pd.DataFrame) -> pd.DataFrame:
    """Full Q derivatives at fixed within-grid T=V=0; flag support limits."""
    modifier="sm_28_100_prev3_mean"
    support=pd.read_csv(base.exp05.project_root()/"outputs/research/exp_05b/support_diagnostics.csv")
    rows=[]
    for slot,data in base.make_series(panel,modifier).items():
        fit=deterministic.loc[deterministic.scenario.eq("primary")&deterministic.month_slot.eq(slot)].iloc[0]
        for grid,frame in data.groupby("grid_id"):
            s=frame[modifier].to_numpy(float)
            s_mean=s.mean();s_sd=s.std(ddof=1)
            flag=support.loc[support.month_slot.eq(slot)&support.grid_id.eq(grid),
                             "joint_t_v_box_overlap_all_strata"].iloc[0]
            for quartile,physical in (("S25",np.quantile(s,.25)),("S50",np.quantile(s,.5)),
                                      ("S75",np.quantile(s,.75))):
                z=(physical-s_mean)/s_sd
                for model in ("P2","Q2","Q2_prime"):
                    # Q2: dY/dT=bT+2*cT*T+dT*S; dY/dV=bV+2*cV*V+dV*S.
                    # Q2_prime additionally includes eTV*V or eTV*T.
                    # Here T=V=0 on the original within-grid standardized scale.
                    t=float(fit[f"beta_{model}_0"]+fit[f"beta_{model}_3"]*z)
                    v=float(fit[f"beta_{model}_1"]+fit[f"beta_{model}_4"]*z)
                    rows.append({"month_slot":slot,"grid_id":grid,"model":model,
                        "reference":"T=0 and V=0 after within-grid-slot centering/scaling; hold same T/V at all S levels",
                        "soil_level":quartile,"soil_physical_m3_m3":physical,"soil_z":z,
                        "slope_t_tch_per_grid_sd":t,"slope_v_tch_per_grid_sd":v,
                        "joint_t_v_box_overlap_all_sm_terciles":bool(flag),
                        "support_caveat":"range-box overlap is necessary but does not establish dense joint T/V/S support"})
    return pd.DataFrame(rows)


def detailed_sample_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    base_valid=panel[[exp05.Y10,exp05.TEMP,exp05.VPD]].notna().all(axis=1)
    for (slot,grid),frame in panel.groupby(["month_slot","grid_id"],sort=True):
        index=frame.index
        for modifier in base.MODIFIERS:
            valid=base_valid.loc[index]&frame[modifier].notna()
            years=frame.loc[valid,"yield_year"].sort_values().to_numpy(int)
            rows.append({"month_slot":slot,"calendar_month_label":frame.calendar_month_label.iloc[0],
                "grid_id":grid,"modifier":modifier,"n_grid_year_rows":len(frame),
                "n_target_t_v_paired":int(base_valid.loc[index].sum()),
                "n_modifier_complete":int(frame[modifier].notna().sum()),
                "n_all_four_paired":int(valid.sum()),
                "n_missing_modifier_given_target_t_v":int((base_valid.loc[index]&frame[modifier].isna()).sum()),
                "n_missing_y":int(frame[exp05.Y10].isna().sum()),
                "n_missing_t_or_v_given_y":int((frame[exp05.Y10].notna()&frame[[exp05.TEMP,exp05.VPD]].isna().any(axis=1)).sum()),
                "original_n20_eligible":len(years)>=exp05.MIN_PRIMARY_N,
                "included_years":";".join(map(str,years)),
                "first_valid_year":years.min() if len(years) else np.nan,
                "last_valid_year":years.max() if len(years) else np.nan,
                "max_internal_calendar_gap":int(np.diff(years).max()-1) if len(years)>1 else np.nan,
                "mean_observed_mapped_area_ha_paired":frame.loc[valid,"actual_weight_denominator_ha"].mean()})
    return pd.DataFrame(rows)


def monthly_area_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    """EXP-05 mapped target-valid area-year denominator, not statewide area."""
    modifier="sm_28_100_prev3_mean"
    paired=base.analysis_mask(panel,modifier)
    eligible=paired.groupby([panel.month_slot,panel.grid_id]).transform("sum").ge(exp05.MIN_PRIMARY_N)
    rows=[]
    for slot,frame in panel.groupby("month_slot",sort=True):
        den_mask=frame[exp05.Y10].notna()&frame.weather_source_available
        num_mask=paired.loc[frame.index]&eligible.loc[frame.index]
        den=float(frame.loc[den_mask,"actual_weight_denominator_ha"].sum())
        num=float(frame.loc[num_mask,"actual_weight_denominator_ha"].sum())
        rows.append({"month_slot":slot,"calendar_month_label":frame.calendar_month_label.iloc[0],
            "denominator_mapped_target_valid_weather_year_area_ha_year_sum":den,
            "numerator_primary_paired_n20_area_ha_year_sum":num,
            "paired_area_fraction":num/den,
            "denominator_note":"mapped EXP-02B target-valid grid-year observed harvested area in verified weather years; not all statewide municipalities"})
    return pd.DataFrame(rows)


def make_figures(output: Path, panel: pd.DataFrame, estimates: pd.DataFrame) -> None:
    figures=output/"figures"
    figures.mkdir(parents=True,exist_ok=True)
    primary=estimates.loc[estimates.scenario.eq("primary")&estimates.block_length_years.eq(3)]
    fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True,layout="constrained")
    for ax,estimand,title in zip(axes,("dry_minus_wet_v_P2","dry_minus_wet_t_P2"),
                                ("VPD dry-minus-wet slope","Temperature dry-minus-wet slope")):
        part=primary.loc[primary.estimand.eq(estimand)].sort_values("month_slot")
        x=np.arange(len(part))
        ax.errorbar(x,part.point,yerr=[part.point-part.ci_low,part.ci_high-part.point],
                    marker="o",linestyle="-",capsize=3)
        ax.axhline(0,color="black",lw=.8)
        ax.axvspan(7.5,10.5,color="gold",alpha=.12)
        ax.set_ylabel("t/ha per within-grid predictor SD")
        ax.set_title(title+"; pointwise synchronized 3-year-block interval")
    axes[-1].set_xticks(np.arange(len(part)),part.calendar_month_label,rotation=65,ha="right")
    fig.savefig(figures/"all_slots_dry_wet_interaction_overview.png",dpi=170)
    plt.close(fig)
    detail=primary.loc[primary.month_slot.isin([-8,-7,-6,-5]) & primary.estimand.isin(
        ["dry_minus_wet_v_P2","dry_minus_wet_v_Q2","dry_minus_wet_v_Q2_prime","dry_minus_wet_v_spatial"])]
    fig,ax=plt.subplots(figsize=(10,5),layout="constrained")
    for i,(name,part) in enumerate(detail.groupby("estimand",sort=True)):
        part=part.sort_values("month_slot")
        x=np.arange(4)+(i-1.5)*.15
        ax.errorbar(x,part.point,yerr=[part.point-part.ci_low,part.ci_high-part.point],
                    fmt="o",capsize=2,label=name.replace("dry_minus_wet_v_",""))
    ax.axhline(0,color="black",lw=.8)
    ax.set_xticks(np.arange(4),["Aug_(t-1)","Sep_(t-1)","Oct_(t-1)","Nov_(t-1)"])
    ax.set_ylabel("VPD dry-minus-wet slope contrast, t/ha per grid SD")
    ax.set_title("Prespecified focal window; pointwise 3-year-block intervals")
    ax.legend(ncol=4,fontsize=8)
    fig.savefig(figures/"aug_nov_vpd_sensitivity_intervals.png",dpi=170)
    plt.close(fig)
    profiles=pd.read_csv(output/"conditional_slope_profiles.csv")
    profiles=profiles.loc[profiles.month_slot.isin([-8,-7,-6,-5])&profiles.model.eq("P2")]
    fig,axes=plt.subplots(2,2,figsize=(10,7),sharey=True,layout="constrained")
    for ax,(slot,part) in zip(axes.flat,profiles.groupby("month_slot",sort=True)):
        means=part.groupby("soil_level").slope_v_tch_per_grid_sd.mean()
        ax.plot([0,1,2],[means["S25"],means["S50"],means["S75"]],marker="o")
        ax.axhline(0,color="black",lw=.8)
        ax.set_xticks([0,1,2],["local S25","local S50","local S75"])
        ax.set_title({-8:"Aug_(t-1)",-7:"Sep_(t-1)",-6:"Oct_(t-1)",-5:"Nov_(t-1)"}[slot])
        ax.set_ylabel("mean VPD slope, t/ha per within-grid VPD SD")
        ax.text(.98,.95,f"T/V range-box overlap: {100*part.joint_t_v_box_overlap_all_sm_terciles.mean():.0f}% grids",
                transform=ax.transAxes,fontsize=8,ha="right",va="top",
                bbox={"facecolor":"white","edgecolor":"none","alpha":.85})
    fig.suptitle("P2 conditional VPD slopes at fixed within-grid mean T and V; support is descriptive")
    fig.savefig(figures/"aug_nov_conditional_vpd_slope_profiles.png",dpi=170)
    plt.close(fig)
    # Predetermined representative grid: median observed mapped area in Sep.
    modifier="sm_28_100_prev3_mean"
    data=base.make_series(panel,modifier)[-7]
    mean_area=data.groupby("grid_id").actual_weight_denominator_ha.mean().sort_values()
    grid=mean_area.index[len(mean_area)//2]
    sample=data.loc[data.grid_id.eq(grid)].sort_values("yield_year")
    s=sample[modifier].to_numpy(float)
    ranks=rankdata(s,method="average")
    labels=np.where((ranks-.5)/len(s)<1/3,"relatively_dry",
             np.where((ranks-.5)/len(s)>=2/3,"relatively_wet","middle"))
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout="constrained")
    for label,color in (("relatively_dry","tab:orange"),("middle","tab:gray"),
                        ("relatively_wet","tab:blue")):
        sub=sample.iloc[np.flatnonzero(labels==label)]
        axes[0].scatter(sub[exp05.TEMP],sub[exp05.VPD],label=f"{label} (n={len(sub)})",color=color)
        axes[1].scatter(sub[exp05.VPD],sub[exp05.Y10],color=color)
        axes[2].scatter(sub[exp05.TEMP],sub[exp05.Y10],color=color)
    axes[0].set(xlabel="T (°C)",ylabel="VPD (kPa)",title="Joint T/V support")
    axes[1].set(xlabel="VPD (kPa)",ylabel="Y residual (t/ha)",title="Marginal VPD–Y")
    axes[2].set(xlabel="T (°C)",ylabel="Y residual (t/ha)",title="Marginal T–Y")
    axes[0].legend(fontsize=7)
    fig.suptitle(f"Sep_(t-1), preselected median-area grid {grid}; descriptive strata")
    fig.savefig(figures/"september_representative_grid_moisture_strata.png",dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(4,3,figsize=(13,13),layout="constrained")
    for row,slot in enumerate((-8,-7,-6,-5)):
        month=base.make_series(panel,modifier)[slot]
        sample=month.loc[month.grid_id.eq(grid)].sort_values("yield_year")
        moisture=sample[modifier].to_numpy(float)
        ranks=rankdata(moisture,method="average")
        labels=np.where((ranks-.5)/len(sample)<1/3,"relatively_dry",
            np.where((ranks-.5)/len(sample)>=2/3,"relatively_wet","middle"))
        for label,color in (("relatively_dry","tab:orange"),("middle","tab:gray"),
                            ("relatively_wet","tab:blue")):
            sub=sample.iloc[np.flatnonzero(labels==label)]
            axes[row,0].scatter(sub[exp05.TEMP],sub[exp05.VPD],color=color,label=label,s=20)
            axes[row,1].scatter(sub[exp05.VPD],sub[exp05.Y10],color=color,s=20)
            axes[row,2].scatter(sub[exp05.TEMP],sub[exp05.Y10],color=color,s=20)
        axes[row,0].set_ylabel({-8:"Aug_(t-1)",-7:"Sep_(t-1)",-6:"Oct_(t-1)",-5:"Nov_(t-1)"}[slot]+"\nVPD (kPa)")
        axes[row,1].set_ylabel("Y residual (t/ha)")
        axes[row,2].set_ylabel("Y residual (t/ha)")
    for col,title in enumerate(("T vs V joint support","VPD vs Y marginal","T vs Y marginal")):
        axes[0,col].set_title(title)
    for row in range(4):
        axes[row,0].set_xlabel("T (°C)")
        axes[row,1].set_xlabel("VPD (kPa)")
        axes[row,2].set_xlabel("T (°C)")
    axes[0,0].legend(fontsize=7)
    fig.suptitle(f"Aug–Nov preselected median-area grid {grid}; within-slot relative-moisture thirds")
    fig.savefig(figures/"aug_nov_representative_grid_strata_support.png",dpi=170)
    plt.close(fig)


def main() -> None:
    root=base.exp05.project_root()
    output=root/"outputs/research/exp_05b"
    attempts=load_attempts(output)
    deterministic=pd.read_csv(output/"monthly_interaction_results.csv")
    diagnostics,estimates=summarize_attempts(attempts,deterministic)
    comparisons=paired_robustness(attempts,deterministic)
    diagnostics.to_csv(output/"bootstrap_diagnostics.csv",index=False)
    estimates.to_csv(output/"monthly_interaction_uncertainty.csv",index=False)
    comparisons.to_csv(output/"robustness_comparisons.csv",index=False)
    panel=pd.read_pickle(output/"panel.pkl")
    detailed_sample_coverage(panel).to_csv(output/"sample_coverage_grid_slot.csv",index=False)
    monthly_area_coverage(panel).to_csv(output/"monthly_area_coverage.csv",index=False)
    cubes=boot.prepare_cubes(panel)
    loyo=leave_one_calendar_year_out(panel,cubes,deterministic)
    loyo.to_csv(output/"interaction_leave_one_calendar_year_out.csv",index=False)
    slope_profiles(panel,deterministic).to_csv(output/"conditional_slope_profiles.csv",index=False)
    make_figures(output,panel,estimates)
    print(json.dumps({"n_attempt_rows":len(attempts),"n_diagnostic_rows":len(diagnostics),
                      "n_comparison_rows":len(comparisons),
                      "max_failure_rate":float(diagnostics.failure_rate.max()),
                      "n_any_invalid":int(diagnostics.n_failed.gt(0).sum())}))


if __name__=="__main__":
    main()
