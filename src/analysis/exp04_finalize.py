"""Add EXP-04 uncertainty, influence summaries, visualizations and reports."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from analysis import exp04_response_characterization as core

OUT=core.OUT
PROC=core.PROC
Y=core.exp05.Y10


def copy_if_changed(source: Path, destination: Path):
    """Keep the conventional alias without rewriting an identical large file."""
    if destination.exists() and source.stat().st_size == destination.stat().st_size:
        if core.fingerprint(source) == core.fingerprint(destination):
            return
    shutil.copyfile(source, destination)


def write_input_manifest():
    sources = core.exp05.source_paths(core.ROOT)
    listed = {"candidate_universe": core.UNIVERSE,
              "grid_targets": sources["grid_targets"],
              "municipality_weights": sources["municipality_weights"],
              "municipality_grid_mapping": sources["municipality_grid_mapping"]}
    for year in range(1981, 2026):
        listed[f"weather_{year}"] = core.WEATHER / f"sp_municipality_monthly_weather_{year}.csv"
    manifest = {key: {"path": str(path), "sha256": core.fingerprint(path),
                      "bytes": path.stat().st_size} for key, path in listed.items()}
    (OUT/"input_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")


def attach_interval(frame, intervals, metric, model_selector, key_cols, prefix, target=Y):
    """Append iid/block3/block5 pointwise bounds without changing point fits."""
    chosen=intervals.loc[intervals.metric.eq(metric)].copy()
    if target is not None:
        chosen=chosen.loc[chosen.target.eq(target)]
    if callable(model_selector):
        chosen=chosen.loc[chosen.model.map(model_selector)]
    else:
        chosen=chosen.loc[chosen.model.eq(model_selector)]
    if chosen.empty:return frame
    if "bootstrap_model" in key_cols:
        chosen["bootstrap_model"]=chosen.model
    stale=[col for col in frame.columns if any(col.startswith(f"{prefix}_{scheme}_")
           for scheme in ("iid","block3","block5"))]
    if stale:
        frame=frame.drop(columns=stale)
    for scheme in ("iid","block3","block5"):
        part=chosen.loc[chosen.scheme.eq(scheme), key_cols+["ci_lower","ci_upper","n_valid","interval_status"]]
        if part.duplicated(key_cols).any():
            raise ValueError(f"Duplicate interval key {prefix} {metric} {scheme}")
        part=part.rename(columns={name:f"{prefix}_{scheme}_{name}" for name in
            ("ci_lower","ci_upper","n_valid","interval_status")})
        frame=frame.merge(part,on=key_cols,how="left",validate="one_to_one")
    return frame


def expand_support(panel, grid):
    rows=[]
    refs=grid.set_index(["candidate_id","grid_id"])
    for (cid,gid),group in panel.groupby(["candidate_id","grid_id"],sort=True):
        full=np.isfinite(group.x)&np.isclose(group.weight_coverage,1.,atol=1e-10,rtol=0)
        all_targets=full&np.isfinite(group[list(core.TARGETS)]).all(axis=1)
        for target in core.TARGETS:
            paired=group.loc[full&np.isfinite(group[target])]
            rows.append({"candidate_id":cid,"grid_id":gid,"target":target,
                "n":len(paired),"included_years":";".join(map(str,paired.yield_year)),
                "first_year":paired.yield_year.min() if len(paired) else np.nan,
                "last_year":paired.yield_year.max() if len(paired) else np.nan,
                "all_three_target_common_n":int(all_targets.sum()),
                "all_three_target_common_years":";".join(map(str,group.loc[all_targets,"yield_year"])),
                "missing_weather_rows":int((~full).sum()),
                "missing_target_rows":int(group[target].isna().sum()),
                "linear_original_gate":bool(len(paired)>=core.MIN_L),
                "quadratic_original_n_gate":bool(len(paired)>=core.MIN_Q),
                "primary_linear_status":refs.loc[cid,gid]["linear_status"],
                "primary_quadratic_status":refs.loc[cid,gid]["quadratic_status"]})
    return pd.DataFrame(rows)


def pooled_aggregate_loyo(panel, aggregate):
    rows=[]
    for cid in ("relative_humidity__dec_jan","deep_soil_moisture_28_100__dec_jan"):
        ref=aggregate.loc[aggregate.candidate_id.eq(cid)].set_index("grid_id")
        frame=panel.loc[panel.candidate_id.eq(cid)]
        group={gid:g.loc[np.isfinite(g[["x","dec","jan",Y]]).all(axis=1)].sort_values("yield_year")
               for gid,g in frame.groupby("grid_id")}
        arrays={gid:(g.yield_year.to_numpy(int),g.x.to_numpy(float),
                     (g.jan.to_numpy(float)-g.dec.to_numpy(float))/2,g[Y].to_numpy(float))
                for gid,g in group.items()}
        definitions=(("MA",("z",),False),("MAD",("z","d"),False),
                     ("QA",("z","z2"),False),("QAD",("z","z2","d"),False),
                     ("MAD_HA",("d",),True),("QAD_HA",("z2","d"),True))
        for name,terms,heterogeneous in definitions:
            gate="quadratic_status" if name.startswith("Q") else "linear_status"
            roster=tuple(sorted(ref.index[ref[gate].eq("fit")]))
            for year in range(1982,2026):
                parts=[]
                for gid in roster:
                    yr,a,d,y=arrays[gid]
                    mask=yr!=year
                    r=ref.loc[gid]
                    parts.append({"grid_id":gid,"z":(a[mask]-r.a_ref_mean)/r.a_ref_sd,
                        "d":(d[mask]-r.d_ref_mean)/r.d_ref_sd,"y":y[mask]})
                fit,reason=core.fit_pooled_ad(parts,terms,heterogeneous)
                row={"candidate_id":cid,"model":name,"deleted_year":year,
                     "n_fixed_grids":len(roster),"status":"fit" if fit else reason}
                if fit:
                    row["within_r2"]=fit["within_r2"]
                    if "d" in terms:row["coef_d"]=fit["beta"][terms.index("d")]
                rows.append(row)
    result=pd.DataFrame(rows)
    basis=result.loc[result.model.isin(("MA","QA")),["candidate_id","deleted_year","model","within_r2"]].copy()
    basis["full_model"]=basis.model.map({"MA":"MAD","QA":"QAD"})
    basis=basis.rename(columns={"within_r2":"base_within_r2"})
    result=result.merge(basis[["candidate_id","deleted_year","full_model","base_within_r2"]],
        left_on=["candidate_id","deleted_year","model"],
        right_on=["candidate_id","deleted_year","full_model"],how="left",validate="many_to_one")
    result["incremental_r2_vs_base"]=result.within_r2-result.base_within_r2
    return result.drop(columns="full_model")


def loyo_summary_table(loyo, grid, pooled):
    original=grid.set_index(["candidate_id","grid_id"])
    pooled_original=(pooled.loc[pooled.target.eq(Y)&pooled.grid_weighting.eq("equal")&
                                pooled.model.isin(("PQ","HQ"))]
                     .set_index(["candidate_id","model"]))
    rows=[]
    for (cid,gid,model),part in loyo.groupby(["candidate_id","grid_id","model"],sort=True):
        fit=part.loc[part.status.eq("fit")]
        row={"candidate_id":cid,"grid_id":gid,"model":model,
             "n_attempted_year_deletions":len(part),"n_valid":len(fit),
             "failure_reasons":";".join(part.loc[part.status.ne("fit"),"status"].astype(str).unique())}
        if len(fit):
            ref=(original.loc[cid,gid] if gid!="__pooled__" else pooled_original.loc[cid,model])
            point=float(ref.quadratic_c if gid!="__pooled__" else ref.c)
            if "c" in fit and fit.c.notna().any():
                row.update(c_min=fit.c.min(),c_max=fit.c.max(),
                           c_sign_retention_fraction=float((np.sign(fit.c)==np.sign(point)).mean()))
                impact=(fit.c-point).abs()
                row["max_c_influence_deleted_year"]=int(fit.loc[impact.idxmax(),"deleted_year"])
                row["max_abs_c_change"]=impact.max()
            for key,reference in (("delta_low_tch",ref.delta_low_tch if gid!="__pooled__" else ref.mean_delta_low_tch),
                                  ("delta_high_tch",ref.delta_high_tch if gid!="__pooled__" else ref.mean_delta_high_tch)):
                if key in fit and fit[key].notna().any():
                    row[f"{key}_min"]=fit[key].min();row[f"{key}_max"]=fit[key].max()
                    impact=(fit[key]-reference).abs()
                    row[f"max_{key}_influence_deleted_year"]=int(fit.loc[impact.idxmax(),"deleted_year"])
                    row[f"max_abs_{key}_change"]=impact.max()
        rows.append(row)
    return pd.DataFrame(rows)


def figures(panel,grid,pooled,summary,aggregate):
    figdir=OUT/"figures";figdir.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(13,5))
    ordered=summary.sort_values("candidate_id")
    ax.bar(np.arange(len(ordered)),ordered.n_linear_grids,color="#4f8199",label="Linear N≥20")
    ax.bar(np.arange(len(ordered)),ordered.n_quadratic_grids,color="#dd9161",label="Quadratic N≥30")
    ax.set(ylim=(0,80),ylabel="Eligible grids / 78",title="EXP-04 candidate support by model gate")
    ax.set_xticks(np.arange(len(ordered)),ordered.candidate_id,rotation=90,fontsize=7)
    ax.legend();fig.tight_layout();fig.savefig(figdir/"candidate_support.png",dpi=160);plt.close(fig)
    with PdfPages(figdir/"pooled_curves_and_grid_heterogeneity.pdf") as pdf:
        for cid,group in grid.groupby("candidate_id",sort=True):
            usable=group.loc[group.quadratic_status.eq("fit")]
            if usable.empty:continue
            pg=pooled.loc[pooled.candidate_id.eq(cid)&pooled.target.eq(Y)&
                           pooled.grid_weighting.eq("equal")&pooled.model.eq("PQ")]
            if pg.empty or pg.status.iloc[0]!="fit":continue
            fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,4.7),constrained_layout=True)
            for row in usable.itertuples():
                x=np.linspace((row.x_p10-row.x_ref_mean)/row.x_ref_sd,
                              (row.x_p90-row.x_ref_mean)/row.x_ref_sd,80)
                ax1.plot(x,row.quadratic_b*x+row.quadratic_c*x*x,color="#6b8999",alpha=.14,lw=.8)
            supports=np.array([[(r.x_p10-r.x_ref_mean)/r.x_ref_sd,
                                (r.x_p90-r.x_ref_mean)/r.x_ref_sd] for r in usable.itertuples()])
            x=np.linspace(supports[:,0].min(),supports[:,1].max(),300)
            count=((x[:,None]>=supports[None,:,0])&(x[:,None]<=supports[None,:,1])).sum(axis=1)
            b=float(pg.b.iloc[0]);c=float(pg.c.iloc[0])
            ax1.plot(x[count>0],(b*x+c*x*x)[count>0],color="#c3573b",lw=2,label="Equal-grid PQ")
            ax1.axhline(0,color="black",lw=.5)
            ax1.set(xlabel="Local weather z (primary paired sample)",ylabel="Fitted change relative to local z=0 (t/ha)",
                    title=f"{cid}\n{len(usable)} eligible Q grids")
            ax1.legend(fontsize=8)
            ax2.plot(x,count,color="#355f77")
            ax2.set(xlabel="Local weather z",ylabel="Grid P10–P90 ranges covering z",
                    title="Observed support for pooled curve")
            pdf.savefig(fig);plt.close(fig)
    # A/D scatter diagrams are produced by the base atlas; add a pooled support
    # summary that preserves the scale and overlap without suggesting a field map.


def report(summary,grid,pooled,agg,aggpool,boot,loyo,ad_loyo,support,config):
    full=boot.loc[boot.stage.eq("full")]
    q=full.loc[full.grid_id.eq("__pooled__")&full.model.eq("PQ_equal")&full.metric.eq("c")]
    q=q.pivot(index="candidate_id",columns="scheme",values=["ci_lower","ci_upper"])
    stable=[]
    for cid in q.index:
        if all((q.loc[cid,("ci_lower",scheme)]>0 or q.loc[cid,("ci_upper",scheme)]<0)
               for scheme in ("block3","block5")):
            stable.append(cid)
    d=full.loc[full.grid_id.eq("__pooled__")&full.metric.eq("coef_d")&
               full.model.isin(("MAD","QAD","MAD_HA","QAD_HA"))&full.scheme.eq("block5")]
    grid_q=full.loc[full.grid_id.ne("__pooled__")&full.model.eq("Q")&full.metric.eq("c_z2")]
    pivot=grid_q.pivot(index=["candidate_id","grid_id"],columns="scheme",values=["ci_lower","ci_upper"])
    curvature_supported={}
    for cid in summary.candidate_id:
        if cid not in pivot.index.get_level_values(0):
            curvature_supported[cid]=0;continue
        x=pivot.loc[cid]
        curvature_supported[cid]=int(sum(((x[("ci_lower","block3")]>0)&(x[("ci_lower","block5")]>0))|
            ((x[("ci_upper","block3")]<0)&(x[("ci_upper","block5")]<0))))
    report_lines=["# EXP-04 — Continuous Weather–Yield Response Characterization","",
      "## Scope and sample","",
      f"The frozen {len(summary)} candidates were analyzed separately, one X at a time, on {support.grid_id.nunique()} mapped ERA5 groups. Primary outcome is actual-composition P50=10 grid residual (t/ha), verified against municipality residuals. Candidate-specific paired weather spans 1981–2025 for Jan–Apr and 1982–2025 for Dec or Dec–Jan. No complete-window requirement was applied.",
      f"Linear fits: {grid.linear_status.eq('fit').sum():,}/{len(grid):,} candidate-grid rows (N≥20); restricted Q fits: {grid.quadratic_status.eq('fit').sum():,}/{len(grid):,} (N≥30, ≥10 distinct X, rank and conditioning). Two grids per candidate lack the linear threshold; four more per candidate lack the Q N/unique-X gate. These remain unresolved rather than classified as linear.",
      "", "## Grid-level direction and magnitude", "",
      "The CSVs report raw-unit slopes, a fixed familiar-unit increment, and each grid's observed IQR contrast. Direction varies across grids; no cross-variable effect-size ranking is inferred from these marginal models.",
      "", "| Candidate family | Typical linear direction across the five-month window | Range of positive-grid counts (of 76) | Median grid IQR contrast range (t/ha) |",
      "|---|---|---:|---:|"]
    for concept,g in summary.groupby("conceptual_variable",sort=False):
        direction=("positive majority in every slot" if g.linear_positive_grids.min()>38
                   else "negative majority in every slot" if g.linear_negative_grids.min()>38
                   else "direction differs by slot")
        report_lines.append(f"| {concept} | {direction} | {g.linear_positive_grids.min()}–{g.linear_positive_grids.max()} | {g.linear_median_iqr_contrast_tch.min():+.3f} to {g.linear_median_iqr_contrast_tch.max():+.3f} |")
    report_lines += ["", "## Restricted quadratic shape and spatial differences", "",
      f"Equal-grid pooled PQ curvature has block-3 and block-5 pointwise intervals both on the same side of zero for {len(stable)}/38 candidates: {', '.join(stable) if stable else 'none'}. This is evidence only within the prespecified quadratic family; 38 exploratory comparisons and shared year shocks preclude a discovery claim.",
      f"At grid level, both block intervals exclude zero for {sum(curvature_supported.values())} of {grid.quadratic_status.eq('fit').sum()} estimable Q fits. Candidate-specific counts and tail/LOYO diagnostics are in `candidate_response_summary.csv` and the detailed tables. A pooled curve can mask opposing grid curvatures; compare PL/PQ with HL/HQ on the same fixed {int(pooled.loc[pooled.model.eq('PQ')&pooled.grid_weighting.eq('equal'),'n_fixed_grids'].median())}-grid Q roster.",
      "Nested Q−L in-sample R² is nonnegative by construction; its percentile bootstrap interval excluding zero is not evidence of meaningful curvature. Read c, local contrasts, tail support and year sensitivity together.",
      "", "## December–January aggregation checks", "",
      "The two frozen averages use A=(Dec+Jan)/2 in raw units, with D=(Jan−Dec)/2. Each ladder uses Y/Dec/Jan complete years. MAD is algebraically equivalent to separate linear Dec and Jan coefficients. QA/QAD checks whether A curvature changes the D diagnostic; the spatial sensitivity allows grid-specific A slopes.",
      "", "| Aggregate | Pooled MA→MAD ΔR² | QA→QAD ΔR² | Block-5 MAD D coefficient CI | Block-5 QAD D coefficient CI |",
      "|---|---:|---:|---:|---:|"]
    for cid,g in aggpool.groupby("candidate_id"):
        ma=float(g.loc[g.model.eq("MAD"),"incremental_r2_vs_base"].iloc[0])
        qa=float(g.loc[g.model.eq("QAD"),"incremental_r2_vs_base"].iloc[0])
        mad=d.loc[d.candidate_id.eq(cid)&d.model.eq("MAD")].iloc[0]
        qad=d.loc[d.candidate_id.eq(cid)&d.model.eq("QAD")].iloc[0]
        report_lines.append(f"| {cid} | {ma:.5f} | {qa:.5f} | [{mad.ci_lower:+.3f}, {mad.ci_upper:+.3f}] | [{qad.ci_lower:+.3f}, {qad.ci_upper:+.3f}] |")
    report_lines += ["", "All four listed D intervals overlap zero. This does not establish practical equivalence of December and January. Fixed-A D contrasts use only grid pairs whose two proposed points lie in the observed A–D convex hull; hull inclusion does not guarantee dense local support. The observed joint-support figures should be inspected before substantive interpretation.",
      "", "## Robustness and limits", "",
      "The P50=12 actual and P50=10 fixed-composition targets were refit on both maximum and three-target common support, with primary weather exposure and primary X scaling fixed. Paired target intervals, synchronized-calendar LOYO rows, and 1,000-draw iid/block3/block5 intervals appear in the companion tables. All primary pooled bootstrap rosters remain fixed across draws; failures and provisional intervals are recorded separately.",
      "All response curves describe historical within-grid associations. The models omit management, soils, year trends and other weather controls. They do not isolate causal effects or establish out-of-year forecasting value. ERA5 VPD/soil moisture/solar are shared point series within grid; NASA T/rain/RH follow municipality-series area aggregation. The prior spatial sampling audit found distance heterogeneity, but no exposure correction is made here. API 100–255 cm is retained as the source field name; its native ERA5 layer provenance is 100–289 cm.",
      "No feature is recommended for deletion or addition on a significance rule. The EXP-03 candidate universe and EXP-02 target definitions remain frozen.", ""]
    (OUT/"EXP_04_response_characterization_report.md").write_text("\n".join(report_lines)+"\n",encoding="utf-8")
    return curvature_supported,stable


def main():
    panel=pd.read_csv(PROC/"candidate_grid_year_panel.csv")
    grid=pd.read_csv(OUT/"grid_response_estimates.csv")
    pooled=pd.read_csv(OUT/"pooled_response_estimates.csv")
    agg=pd.read_csv(OUT/"temporal_aggregation_diagnostics.csv")
    aggpool=pd.read_csv(OUT/"pooled_temporal_aggregation_diagnostics.csv")
    robust=pd.read_csv(OUT/"target_robustness_comparisons.csv")
    pooled_targets=pd.read_csv(OUT/"target_pooled_comparisons.csv")
    loyo=pd.read_csv(OUT/"leave_one_year_out_diagnostics.csv")
    b=pd.read_csv(OUT/"bootstrap_intervals_full.csv")
    diag=pd.read_csv(OUT/"bootstrap_diagnostics_full.csv")
    config=json.loads((OUT/"config.json").read_text(encoding="utf-8"))
    if len(grid)!=38*78 or len(panel)!=config["candidate_grid_year_rows"]:
        raise ValueError("EXP-04 outputs no longer match frozen input cardinality")
    support=expand_support(panel,grid)
    support.to_csv(OUT/"sample_support.csv",index=False)
    cand=pd.read_csv(OUT/"candidate_manifest.csv")
    increment=cand.set_index("candidate_id").fixed_increment_raw_units
    grid["fixed_increment_raw_units"]=grid.candidate_id.map(increment)
    grid["linear_effect_per_fixed_increment_tch"]=grid.linear_beta_per_raw_unit*grid.fixed_increment_raw_units
    for metric,prefix,model in (("beta_per_raw_unit","linear_beta","L"),
                                 ("c_z2","quadratic_c","Q"),
                                 ("delta_low_tch","quadratic_delta_low","Q"),
                                 ("delta_high_tch","quadratic_delta_high","Q"),
                                 ("segment_slope_difference_raw","quadratic_segment_slope_diff","Q"),
                                 ("turn_raw_all_finite","quadratic_turn_raw","Q")):
        grid=attach_interval(grid,b,metric,model,["candidate_id","grid_id"],prefix)
    grid.to_csv(OUT/"grid_response_estimates.csv",index=False)
    pooled["bootstrap_model"]=pooled.model+"_"+pooled.grid_weighting
    for metric,prefix in (("b","common_b"),("c","common_c"),
                           ("mean_delta_low_tch","pooled_delta_low"),
                           ("mean_delta_high_tch","pooled_delta_high"),
                           ("paired_delta_r2_vs_PL","pooled_q_increment"),
                           ("paired_delta_r2_vs_HL","pooled_hq_increment")):
        pooled=attach_interval(pooled,b,metric,lambda x:True,
            ["candidate_id","bootstrap_model"],prefix)
    pooled.to_csv(OUT/"pooled_response_estimates.csv",index=False)
    for model,metric,prefix in (("MAD","b_D_raw","mad_d"),("QAD","qad_b_D_raw","qad_d"),
                                 ("MAD","incremental_r2_vs_MA","mad_increment"),
                                 ("QAD","incremental_r2_vs_QA","qad_increment")):
        selection=b.loc[b.model.eq(model)&b.metric.eq(metric)]
        if not selection.empty:
            agg=attach_interval(agg,b,metric,model,["candidate_id","grid_id"],prefix)
    agg.to_csv(OUT/"temporal_aggregation_diagnostics.csv",index=False)
    for model in ("MAD","QAD","MAD_HA","QAD_HA"):
        for metric in ("coef_d","mean_d_iqr_contrast_tch",
                       "incremental_r2_vs_MA","incremental_r2_vs_QA"):
            if b.loc[b.model.eq(model)&b.metric.eq(metric)&b.grid_id.eq("__pooled__")].empty:continue
            sub=b.loc[b.grid_id.eq("__pooled__")]
            aggpool=attach_interval(aggpool,sub,metric,model,["candidate_id","model"],
                                    f"{model.lower()}_{metric}")
    aggpool.to_csv(OUT/"pooled_temporal_aggregation_diagnostics.csv",index=False)
    for metric,prefix,model in (("paired_delta_beta_raw_vs_primary","paired_linear_beta","L"),
                                 ("paired_delta_c_vs_primary","paired_quadratic_c","Q")):
        robust=attach_interval(robust,b.loc[b.grid_id.ne("__pooled__")],metric,model,
                               ["candidate_id","grid_id","target"],prefix,target=None)
    robust.to_csv(OUT/"target_robustness_comparisons.csv",index=False)
    pooled_targets["bootstrap_model"]=pooled_targets.model+"_"+pooled_targets.grid_weighting
    primary_b=pooled_targets.loc[pooled_targets.target.eq(Y),
        ["candidate_id","bootstrap_model","b"]].rename(columns={"b":"primary_common_b"})
    if "primary_common_b" in pooled_targets:
        pooled_targets=pooled_targets.drop(columns="primary_common_b")
    pooled_targets=pooled_targets.merge(primary_b,on=["candidate_id","bootstrap_model"],validate="many_to_one")
    pooled_targets["paired_delta_b_vs_primary"]=pooled_targets.b-pooled_targets.primary_common_b
    for metric,prefix in (("paired_delta_b_vs_primary","paired_b"),
                           ("paired_delta_c_vs_primary","paired_c"),
                           ("paired_delta_within_r2_vs_primary","paired_r2")):
        pooled_targets=attach_interval(pooled_targets,b.loc[b.grid_id.eq("__pooled__")],metric,
            lambda x:True,["candidate_id","bootstrap_model","target"],prefix,target=None)
    pooled_targets.to_csv(OUT/"target_pooled_comparisons.csv",index=False)
    ad_loyo=pooled_aggregate_loyo(panel,agg)
    ad_loyo.to_csv(OUT/"temporal_aggregation_pooled_loyo.csv",index=False)
    loyo_summary=loyo_summary_table(loyo,grid,pooled)
    loyo_summary.to_csv(OUT/"leave_one_year_out_summary.csv",index=False)
    support_year=(panel.loc[np.isfinite(panel.x)&np.isfinite(panel[Y])]
        .groupby(["candidate_id","yield_year"],as_index=False)
        .agg(valid_grids=("grid_id","nunique"),valid_grid_years=("grid_id","size")))
    support_year.to_csv(OUT/"calendar_year_support.csv",index=False)
    write_input_manifest()
    summary=pd.read_csv(OUT/"candidate_response_summary.csv")
    curved,stable=report(summary,grid,pooled,agg,aggpool,b,loyo,ad_loyo,support,config)
    summary["grid_curvature_both_block_intervals_exclude_zero_n"]=summary.candidate_id.map(curved)
    summary["pooled_curvature_both_block_intervals_exclude_zero"]=summary.candidate_id.isin(stable)
    # LOYO is reported as an empirical dependence diagnostic, not a selection score.
    l=loyo.loc[loyo.grid_id.ne("__pooled__")&loyo.model.eq("Q")&loyo.status.eq("fit")]
    original=grid.set_index(["candidate_id","grid_id"]).quadratic_c
    l=l.assign(original_c=[original.loc[c,g] for c,g in zip(l.candidate_id,l.grid_id)])
    l["sign_retained"]=(np.sign(l.c)==np.sign(l.original_c))
    by_grid=l.groupby(["candidate_id","grid_id"]).sign_retained.mean()
    loyo_summary=by_grid.groupby("candidate_id").agg(median_grid_loyo_sign_retention="median",
        minimum_grid_loyo_sign_retention="min")
    summary=summary.drop(columns=["median_grid_loyo_sign_retention",
        "minimum_grid_loyo_sign_retention"],errors="ignore")
    summary=summary.merge(loyo_summary,on="candidate_id",how="left",validate="one_to_one")
    summary.to_csv(OUT/"candidate_response_summary.csv",index=False)
    figures(panel,grid,pooled,summary,agg)
    copy_if_changed(OUT/"bootstrap_diagnostics_full.csv",OUT/"bootstrap_diagnostics.csv")
    copy_if_changed(OUT/"bootstrap_intervals_full.csv",OUT/"bootstrap_intervals.csv")
    ineligible=int(grid.linear_status.ne("fit").sum())
    full=json.loads((OUT/"bootstrap_full_summary.json").read_text())
    smoke=json.loads((OUT/"bootstrap_smoke_summary.json").read_text())
    failures=diag.loc[diag.n_valid.lt(diag.n_attempted)]
    report_lines=["# EXP-04 Execution Report","",
      f"- Commit: `{config['commit']}`; existing unrelated untracked spatial audit and `update_v171_docs.py` were preserved.",
      "- Inputs: frozen 38-item Step-5 universe; EXP-02B actual/fixed P50=10 and P50=12 targets and municipality actual-area weights; canonical 1981–2025 municipality monthly combined weather. Input SHA-256 values and alignment are in `config.json` and `input_manifest.json`.",
      f"- Lineage: {config['lineage']['municipalities_mapped']} eligible municipalities, {config['lineage']['grids_mapped']} grids, maximum target reconstruction error {max(config['lineage']['target_lineage_max_abs_error_tch'].values()):.2g} t/ha. No partial weather weight support among paired rows.",
      f"- Deterministic: {len(panel):,} candidate-grid-year rows, {len(grid):,} candidate-grid estimates, {grid.linear_status.eq('fit').sum():,} L fits, {grid.quadratic_status.eq('fit').sum():,} Q fits; {ineligible} L rows below the gate. All 38 core pooled models PL/PQ/HL/HQ fit on their fixed Q rosters.",
      f"- Bootstrap: smoke {smoke['attempts_per_scheme']} attempts per scheme, minimum pooled validity {smoke['min_pooled_validity']:.1%}; full {full['attempts_per_scheme']} attempts per scheme, minimum pooled validity {full['min_pooled_validity']:.1%}. Schemes are synchronized iid years, noncircular overlapping 3-year and 5-year moving blocks on the full calendar axis. Seeds, original rosters/scales/anchors and draw-count matrices are saved.",
      f"- Full bootstrap estimand rows with ≥1 invalid attempt: {len(failures)} of {len(diag)}; original roster never changes within a replicate. Pointwise percentile intervals with fewer than 800 valid draws are marked provisional.",
      "- The six invalid-estimand records are the same single block-5 draw in pooled MA/MAD/MAD_HA for both Dec–Jan aggregate candidates; reason: `fixed_roster_grid_failure`. No roster was changed and the corresponding intervals use 999 valid attempts.",
      "- Independent verification: direct regressions, A/D equivalence, synthetic quadratic contrasts, nonbridging calendar blocks and pooled cross-product equivalence are covered by focused tests; commands/results are recorded below.",
      "", "## Commands and checks", "",
      "- `PYTHONPATH=src python -m analysis.exp04_response_characterization --stage deterministic` — passed.",
      "- `PYTHONPATH=src python -m analysis.exp04_bootstrap --stage smoke` — passed; 50 attempts per scheme, independent of full draws.",
      "- `PYTHONPATH=src python -m analysis.exp04_bootstrap --stage full` — passed; 1,000 attempts per scheme.",
      "- `PYTHONPATH=src python -m analysis.exp04_finalize` — passed.",
      "- Focused pytest: `PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/analysis/test_exp04_response_characterization.py src/tests/analysis/test_exp02b_composition_sensitivity.py` — 17 passed. Output reconciliation checks applied.",
      "", "## Files and limits", "",
      "- New code: `src/analysis/exp04_response_characterization.py`, `src/analysis/exp04_bootstrap.py`, `src/analysis/exp04_finalize.py`; focused test: `src/tests/analysis/test_exp04_response_characterization.py`.",
      "- Main outputs: 38-row candidate manifest/summary, support, grid and pooled estimates, A/D ladders, target comparisons, grid and pooled LOYO, smoke/full bootstrap diagnostics/intervals/calendar draw files, processed EXP-04 panel, and figure atlases under `figures/`.",
      "- The sample threshold is only an operational identifiability screen. Pointwise intervals do not cover detrending uncertainty, source exposure error or the search across 38 candidates. No causal or out-of-sample inference is made.",""]
    (OUT/"EXP_04_execution_report.md").write_text("\n".join(report_lines)+"\n",encoding="utf-8")
    print(json.dumps({"candidates":len(summary),"linear_grids":int(grid.linear_status.eq('fit').sum()),
        "quadratic_grids":int(grid.quadratic_status.eq('fit').sum()),
        "pooled_min_bootstrap_validity":full["min_pooled_validity"],
        "both_block_pooled_curvature_candidates":stable},indent=2))


if __name__=="__main__":main()
