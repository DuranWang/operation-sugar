"""Fixed-roster synchronized calendar-year inference for EXP-04.

Run smoke first, then full. The original grid eligibility roster, scaling and
weather anchors are fixed before drawing years; no failed grid is dropped.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis import exp04_response_characterization as core

OUT=core.OUT
PROC=core.PROC
Y=core.exp05.Y10
TARGETS=core.TARGETS
SCHEMES={"iid":1,"block3":3,"block5":5}
SEEDS={"smoke":143010,"full":143100}
FAIL={0:"valid",1:"insufficient_resampled_rows",2:"rank_or_condition_failure",
      3:"extreme_or_nonfinite_coefficient",4:"constant_resampled_target"}


def draw_calendar_indices(axis, n_attempts, block, seed):
    """Noncircular overlapping moving blocks on the full calendar axis."""
    rng=np.random.default_rng(seed)
    length=len(axis)
    if block==1:
        idx=rng.integers(0,length,size=(n_attempts,length))
    else:
        starts=rng.integers(0,length-block+1,size=(n_attempts,(length+block-1)//block))
        idx=(starts[:,:,None]+np.arange(block)[None,None,:]).reshape(n_attempts,-1)[:,:length]
    return idx


def draw_calendar_counts(axis, n_attempts, block, seed):
    idx=draw_calendar_indices(axis,n_attempts,block,seed)
    length=len(axis)
    count=np.zeros((n_attempts,length),dtype=np.int16)
    np.add.at(count,(np.arange(n_attempts)[:,None],idx),1)
    assert np.all(count.sum(axis=1)==length)
    return count


def make_cube(frame, estimates, candidate_id):
    source=frame.loc[frame.candidate_id.eq(candidate_id)]
    ref=estimates.loc[estimates.candidate_id.eq(candidate_id)].set_index("grid_id")
    grids=tuple(sorted(ref.loc[ref.linear_status.eq("fit")].index))
    qgrids=tuple(sorted(ref.loc[ref.quadratic_status.eq("fit")].index))
    if not qgrids or not set(qgrids).issubset(grids):
        raise ValueError(f"No valid nested quadratic roster: {candidate_id}")
    observed=source.loc[np.isfinite(source.x)&np.isfinite(source[Y])]
    axis=np.arange(int(observed.yield_year.min()),int(observed.yield_year.max())+1)
    gidx={g:i for i,g in enumerate(grids)}
    years={year:i for i,year in enumerate(axis)}
    z=np.zeros((len(grids),len(axis)),float)
    yy=np.zeros((len(grids),len(axis),len(TARGETS)),float)
    mask=np.zeros((len(grids),len(axis)),bool)
    for row in source.loc[source.grid_id.isin(grids)].itertuples():
        if row.yield_year not in years or not np.isfinite(row.x):
            continue
        if not all(np.isfinite(getattr(row,t)) for t in TARGETS):
            continue
        i,j=gidx[row.grid_id],years[row.yield_year]
        r=ref.loc[row.grid_id]
        if mask[i,j]:raise ValueError("Duplicate cube grid-year")
        z[i,j]=(row.x-r.x_ref_mean)/r.x_ref_sd
        yy[i,j]=[getattr(row,t) for t in TARGETS]
        mask[i,j]=True
    original=mask.sum(axis=1)
    if not np.array_equal(original,np.array([ref.loc[g,"n"] for g in grids])):
        raise ValueError("Bootstrap cube support differs from original paired sample")
    qidx=np.array([gidx[g] for g in qgrids],int)
    pi=np.array([ref.loc[g,"mean_area_ha"] for g in qgrids],float)
    pi=pi/pi.sum()
    anchors=np.array([[(ref.loc[g,f"x_p{k}"]-ref.loc[g,"x_ref_mean"])/ref.loc[g,"x_ref_sd"]
                       for k in (10,50,90)] for g in grids],float)
    return {"candidate_id":candidate_id,"axis":axis,"grids":grids,"qgrids":qgrids,"qidx":qidx,
            "z":z,"y":yy,"mask":mask,"pi":pi,"anchors":anchors,
            "sd":np.array([ref.loc[g,"x_ref_sd"] for g in grids],float)}


def moments(cube, counts, target_index=0):
    z=cube["z"];mask=cube["mask"]
    x=np.stack([mask.astype(float),z*mask,z*z*mask],axis=2)
    yy=cube["y"][:,:,target_index]*mask
    xx=np.einsum("ry,gyp,gyq->rgpq",counts,x,x,optimize=True)
    xy=np.einsum("ry,gyp,gy->rgp",counts,x,yy,optimize=True)
    y2=np.einsum("ry,gy->rg",counts,yy*yy,optimize=True)
    return xx,xy,y2


def solve_grid(xx,xy,y2,p,original_y_sd):
    a=xx[:,:,:p,:p]
    b=xy[:,:,:p]
    n=xx[:,:,0,0]
    centered_y2=y2-xy[:,:,0]**2/np.maximum(n,1)
    eigen=np.linalg.eigvalsh(a)
    smallest=eigen[:,:,0];largest=eigen[:,:,-1]
    cond=np.sqrt(np.maximum(largest,0)/np.maximum(smallest,1e-300))
    status=np.zeros(n.shape,np.int8)
    status[n<p]=1
    status[(status==0)&((smallest<=1e-12)|(cond>core.COND_MAX)|~np.isfinite(cond))]=2
    status[(status==0)&(centered_y2<=1e-12)]=4
    beta=np.full((*n.shape,p),np.nan)
    ok=status==0
    if np.any(ok):
        beta[ok]=np.linalg.solve(a[ok],b[ok][...,None])[...,0]
    extreme=np.any(np.abs(beta)>1e4*original_y_sd[None,:,None],axis=2)|~np.isfinite(beta).all(axis=2)
    status[ok&extreme]=3
    beta[status!=0]=np.nan
    explained=np.einsum("rgp,rgp->rg",np.nan_to_num(beta),b)-xy[:,:,0]**2/np.maximum(n,1)
    r2=explained/centered_y2
    r2[status!=0]=np.nan
    return beta,r2,status,n,cond


def pooled_from_moments(cube,xx,xy,y2,qstatus,model,weight="equal"):
    q=cube["qidx"]
    a=xx[:,q];b=xy[:,q];v=y2[:,q]
    n=a[:,:,0,0]
    bad=np.any(qstatus[:,q]!=0,axis=1)|np.any(n<3,axis=1)
    n_safe=np.maximum(n,1)
    mu_z=a[:,:,0,1]/n_safe;mu_z2=a[:,:,0,2]/n_safe
    mu_y=b[:,:,0]/n_safe
    uzz=a[:,:,1,1]/n_safe-mu_z**2
    uzq=a[:,:,1,2]/n_safe-mu_z*mu_z2
    uqq=a[:,:,2,2]/n_safe-mu_z2**2
    uzy=b[:,:,1]/n_safe-mu_z*mu_y
    uqy=b[:,:,2]/n_safe-mu_z2*mu_y
    uyy=v/n_safe-mu_y**2
    bad|=np.any((uzz<=1e-12)|(uyy<=1e-12),axis=1)
    w=(cube["pi"] if weight=="area" else np.ones(len(q)))[None,:]
    S=lambda term:np.sum(w*term,axis=1)
    total=S(uyy)
    beta=np.full((len(n),2),np.nan)
    grid_b=np.full_like(uzz,np.nan)
    if model=="PL":
        denominator=S(uzz)
        good=(~bad)&(denominator>1e-12)
        beta[good,0]=S(uzy)[good]/denominator[good]
        gain=2*beta[:,0]*S(uzy)-beta[:,0]**2*S(uzz)
    elif model=="PQ":
        aa=np.stack([np.stack([S(uzz),S(uzq)],axis=1),
                     np.stack([S(uzq),S(uqq)],axis=1)],axis=1)
        bb=np.stack([S(uzy),S(uqy)],axis=1)
        eig=np.linalg.eigvalsh(aa)
        good=(~bad)&(eig[:,0]>1e-12)&(np.sqrt(eig[:,1]/np.maximum(eig[:,0],1e-300))<=core.COND_MAX)
        beta[good]=np.linalg.solve(aa[good],bb[good][...,None])[...,0]
        gain=beta[:,0]*S(uzy)+beta[:,1]*S(uqy)
    elif model=="HL":
        good=~bad
        grid_b[good]=uzy[good]/uzz[good]
        gain=S(uzy*uzy/np.maximum(uzz,1e-300))
    elif model=="HQ":
        resid_qq=uqq-uzq**2/np.maximum(uzz,1e-300)
        resid_qy=uqy-uzq*uzy/np.maximum(uzz,1e-300)
        denom=S(resid_qq)
        good=(~bad)&(denom>1e-12)
        beta[good,1]=S(resid_qy)[good]/denom[good]
        grid_b[good]=(uzy[good]-beta[good,1,None]*uzq[good])/uzz[good]
        gain=S(uzy*uzy/np.maximum(uzz,1e-300))+beta[:,1]*S(resid_qy)
    else:raise ValueError(model)
    good &= np.isfinite(gain)&(total>1e-12)
    b_local=grid_b if model in ("HL","HQ") else np.broadcast_to(beta[:,0,None],uzz.shape)
    c=np.zeros(len(n)) if model in ("HL","PL") else beta[:,1]
    p=cube["anchors"][q]
    low=b_local*(p[None,:,1]-p[None,:,0])+c[:,None]*(p[None,:,1]**2-p[None,:,0]**2)
    high=b_local*(p[None,:,2]-p[None,:,1])+c[:,None]*(p[None,:,2]**2-p[None,:,1]**2)
    divisor=np.sum(w)
    mean_low=np.sum(w*low,axis=1)/divisor
    mean_high=np.sum(w*high,axis=1)/divisor
    result={"b":beta[:,0],"c":c,"within_r2":gain/total,
            "mean_delta_low_tch":mean_low,"mean_delta_high_tch":mean_high}
    for value in result.values():
        value[~good]=np.nan
    reason=np.where(good,"valid",np.where(bad,"fixed_roster_grid_failure","pooled_rank_or_variance_failure"))
    return result,reason


def summarize_draws(values,valid,reference,stage,scheme,subject,model,candidate,grid="__pooled__",target=Y):
    n=int(np.sum(valid & np.isfinite(values)))
    attempted=len(values)
    a=values[valid & np.isfinite(values)]
    return {"stage":stage,"scheme":scheme,"candidate_id":candidate,"grid_id":grid,
            "target":target,"model":model,"metric":subject,"original":reference,
            "ci_lower":float(np.quantile(a,.025)) if n else np.nan,
            "ci_upper":float(np.quantile(a,.975)) if n else np.nan,
            "n_attempted":attempted,"n_valid":n,
            "interval_status":"usable" if n>=.8*attempted else "provisional_low_validity"}


def make_ad_cube(panel, estimates, candidate_id):
    source=panel.loc[panel.candidate_id.eq(candidate_id)]
    reference=estimates.loc[estimates.candidate_id.eq(candidate_id)].set_index("grid_id")
    grids=tuple(sorted(reference.index[reference.linear_status.eq("fit")]))
    qgrids=tuple(sorted(reference.index[reference.quadratic_status.eq("fit")]))
    axis=np.arange(1982,2026)
    index={g:i for i,g in enumerate(grids)}
    x=np.zeros((len(grids),len(axis),4));yy=np.zeros((len(grids),len(axis)))
    mask=np.zeros((len(grids),len(axis)),bool)
    for row in source.loc[source.grid_id.isin(grids)].itertuples():
        if not (1982<=row.yield_year<=2025) or not np.isfinite([row.x,row.dec,row.jan,getattr(row,Y)]).all():
            continue
        i=index[row.grid_id];j=row.yield_year-1982;r=reference.loc[row.grid_id]
        d=(row.jan-row.dec)/2
        a=(row.x-r.a_ref_mean)/r.a_ref_sd
        dd=(d-r.d_ref_mean)/r.d_ref_sd
        x[i,j]=[1.,a,a*a,dd]
        yy[i,j]=getattr(row,Y);mask[i,j]=True
    if not np.array_equal(mask.sum(axis=1),np.array([reference.loc[g,"n"] for g in grids])):
        raise ValueError(f"Aggregation cube differs from original sample: {candidate_id}")
    return {"candidate_id":candidate_id,"axis":axis,"grids":grids,"qgrids":qgrids,
        "qidx":np.array([index[g] for g in qgrids]),"x":x,"y":yy,"mask":mask,
        "d_sd":np.array([reference.loc[g,"d_ref_sd"] for g in grids]),
        "d_iqr_scaled":np.array([(reference.loc[g,"d_p75"]-reference.loc[g,"d_p25"])/reference.loc[g,"d_ref_sd"]
                                  for g in grids])}


def ad_moments(cube,counts):
    x=cube["x"];y=cube["y"]
    return (np.einsum("ry,gyp,gyq->rgpq",counts,x,x,optimize=True),
            np.einsum("ry,gyp,gy->rgp",counts,x,y,optimize=True),
            np.einsum("ry,gy->rg",counts,y*y,optimize=True))


def solve_selected(xx,xy,y2,columns,ysd):
    aa=xx[:,:,:,:][:,:,columns,:][:,:,:,columns]
    bb=xy[:,:,columns]
    n=xx[:,:,0,0]
    dof=len(columns)
    centered_y2=y2-xy[:,:,0]**2/np.maximum(n,1)
    eig=np.linalg.eigvalsh(aa)
    cond=np.sqrt(np.maximum(eig[:,:,-1],0)/np.maximum(eig[:,:,0],1e-300))
    status=np.zeros(n.shape,np.int8)
    status[n<dof]=1
    status[(status==0)&((eig[:,:,0]<=1e-12)|(cond>core.COND_MAX)|~np.isfinite(cond))]=2
    status[(status==0)&(centered_y2<=1e-12)]=4
    beta=np.full((*n.shape,dof),np.nan)
    valid=status==0
    if valid.any():beta[valid]=np.linalg.solve(aa[valid],bb[valid][...,None])[...,0]
    extreme=np.any(np.abs(beta)>1e4*ysd[None,:,None],axis=2)|~np.isfinite(beta).all(axis=2)
    status[valid&extreme]=3;beta[status!=0]=np.nan
    explained=np.einsum("rgp,rgp->rg",np.nan_to_num(beta),bb)-xy[:,:,0]**2/np.maximum(n,1)
    r2=explained/centered_y2;r2[status!=0]=np.nan
    return beta,r2,status,n


def pooled_ad_from_moments(cube,xx,xy,y2,status,model):
    quadratic=model.startswith("Q")
    heterogeneous=model.endswith("_HA")
    q=cube["qidx"] if quadratic else np.arange(len(cube["grids"]))
    n=xx[:,q,0,0]
    bad=np.any(status[:,q]!=0,axis=1)|np.any(n<4,axis=1)
    nn=np.maximum(n,1)
    m=xx[:,q,0,:]/nn[:,:,None]
    my=xy[:,q,0]/nn
    u=xx[:,q,1:,1:]/nn[:,:,None,None]-m[:,:,1:,None]*m[:,:,None,1:]
    uy=xy[:,q,1:]/nn[:,:,None]-m[:,:,1:]*my[:,:,None]
    yv=y2[:,q]/nn-my*my
    bad|=np.any((u[:,:,0,0]<=1e-12)|(yv<=1e-12),axis=1)
    terms={"MA":(0,),"MAD":(0,2),"QA":(0,1),"QAD":(0,1,2),
           "MAD_HA":(2,),"QAD_HA":(1,2)}[model]
    if heterogeneous:
        projection=u[:,:,0,list(terms)]/np.maximum(u[:,:,0,0,None],1e-300)
        base=u[:,:,list(terms),:][:,:,:,list(terms)]
        cov=base-projection[:,:,:,None]*u[:,:,0,list(terms)][:,:,None,:]
        target=uy[:,:,list(terms)]-projection*uy[:,:,0,None]
        y_base=yv-uy[:,:,0]**2/np.maximum(u[:,:,0,0],1e-300)
    else:
        cov=u[:,:,list(terms),:][:,:,:,list(terms)]
        target=uy[:,:,list(terms)]
        y_base=yv
    aa=np.sum(cov,axis=1);bb=np.sum(target,axis=1)
    eig=np.linalg.eigvalsh(aa)
    good=(~bad)&(eig[:,0]>1e-12)&(np.sqrt(eig[:,-1]/np.maximum(eig[:,0],1e-300))<=core.COND_MAX)
    beta=np.full((len(n),len(terms)),np.nan)
    if good.any():beta[good]=np.linalg.solve(aa[good],bb[good][...,None])[...,0]
    gain=np.einsum("rp,rp->r",np.nan_to_num(beta),bb)
    r2=(np.sum(yv,axis=1)-np.sum(y_base,axis=1)+gain)/np.sum(yv,axis=1)
    dcoef=beta[:,list(terms).index(2)] if 2 in terms else np.full(len(n),np.nan)
    result={"coef_d":dcoef,"within_r2":r2,
            "mean_d_iqr_contrast_tch":dcoef*np.mean(cube["d_iqr_scaled"][q])}
    for value in result.values():value[~good]=np.nan
    reason=np.where(good,"valid",np.where(bad,"fixed_roster_grid_failure","pooled_rank_or_variance_failure"))
    return result,reason


def run(stage):
    attempts=50 if stage=="smoke" else 1000
    panel=pd.read_csv(PROC/"candidate_grid_year_panel.csv")
    estimates=pd.read_csv(OUT/"grid_response_estimates.csv")
    pooled=pd.read_csv(OUT/"pooled_response_estimates.csv")
    robust=pd.read_csv(OUT/"target_robustness_comparisons.csv")
    pooled_targets=pd.read_csv(OUT/"target_pooled_comparisons.csv")
    aggregate=pd.read_csv(OUT/"temporal_aggregation_diagnostics.csv")
    aggregate_pooled=pd.read_csv(OUT/"pooled_temporal_aggregation_diagnostics.csv")
    candidates=tuple(pd.read_csv(OUT/"candidate_manifest.csv").candidate_id)
    draw_cache={}
    diag=[];intervals=[];calendar=[]
    for cid in candidates:
        cube=make_cube(panel,estimates,cid)
        refs=estimates.loc[estimates.candidate_id.eq(cid)].set_index("grid_id")
        rp=pooled.loc[pooled.candidate_id.eq(cid)&pooled.target.eq(Y)]
        rb=robust.loc[robust.candidate_id.eq(cid)].set_index(["grid_id","target"])
        original_ysd=np.array([panel.loc[panel.candidate_id.eq(cid)&panel.grid_id.eq(g),Y].std()
                               for g in cube["grids"]])
        for scheme,block in SCHEMES.items():
            key=(tuple(cube["axis"]),scheme)
            if key not in draw_cache:
                seed=SEEDS[stage]+100*block+int(cube["axis"][0])
                counts=draw_calendar_counts(cube["axis"],attempts,block,seed)
                draw_cache[key]=counts
                calendar.extend(dict(stage=stage,scheme=scheme,year=int(y),
                    mean_resampled_count=float(counts[:,j].mean()),
                    minimum_resampled_count=int(counts[:,j].min()),
                    maximum_resampled_count=int(counts[:,j].max()),seed=seed)
                    for j,y in enumerate(cube["axis"]))
            counts=draw_cache[key]
            xx,xy,y2=moments(cube,counts)
            l,lr2,ls,ln,lcond=solve_grid(xx,xy,y2,2,original_ysd)
            q,qr2,qs,qn,qcond=solve_grid(xx,xy,y2,3,original_ysd)
            p=cube["anchors"]
            for i,gid in enumerate(cube["grids"]):
                ref=refs.loc[gid]
                for model,status in (("L",ls[:,i]),("Q",qs[:,i])):
                    counts_by_reason={str(name):int(np.sum(status==code)) for code,name in FAIL.items()}
                    diagnostic={"stage":stage,"scheme":scheme,"candidate_id":cid,
                        "grid_id":gid,"model":model,"n_attempted":attempts,
                        "n_valid":counts_by_reason.pop("valid"),"failure_reasons":json.dumps(counts_by_reason),
                        "min_resampled_rows":int((ln if model=="L" else qn)[:,i].min()),
                        "maximum_design_condition":float(np.nanmax((lcond if model=="L" else qcond)[:,i]))}
                    if model=="Q" and ref.quadratic_status=="fit":
                        with np.errstate(divide="ignore",invalid="ignore"):
                            turn=ref.x_ref_mean-cube["sd"][i]*q[:,i,1]/(2*q[:,i,2])
                        valid_turn=(status==0)&np.isfinite(turn)
                        diagnostic["turn_inside_observed_fraction_all_valid"]=(
                            float(np.mean((turn[valid_turn]>=ref.x_min)&(turn[valid_turn]<=ref.x_max)))
                            if valid_turn.any() else np.nan)
                        diagnostic["turn_finite_n"]=int(valid_turn.sum())
                    diag.append(diagnostic)
                intervals.append(summarize_draws(l[:,i,1]/cube["sd"][i],ls[:,i]==0,
                    ref.linear_beta_per_raw_unit,stage,scheme,"beta_per_raw_unit","L",cid,gid))
                if ref.quadratic_status=="fit":
                    intervals.append(summarize_draws(q[:,i,2],qs[:,i]==0,ref.quadratic_c,
                        stage,scheme,"c_z2","Q",cid,gid))
                    lo=q[:,i,1]*(p[i,1]-p[i,0])+q[:,i,2]*(p[i,1]**2-p[i,0]**2)
                    hi=q[:,i,1]*(p[i,2]-p[i,1])+q[:,i,2]*(p[i,2]**2-p[i,1]**2)
                    for values,metric,reference in ((lo,"delta_low_tch",ref.delta_low_tch),
                                                    (hi,"delta_high_tch",ref.delta_high_tch)):
                        intervals.append(summarize_draws(values,qs[:,i]==0,reference,stage,scheme,metric,"Q",cid,gid))
                    slope_diff=(hi/(cube["sd"][i]*(p[i,2]-p[i,1]))-
                                lo/(cube["sd"][i]*(p[i,1]-p[i,0])))
                    intervals.append(summarize_draws(slope_diff,qs[:,i]==0,
                        ref.segment_slope_difference_raw,stage,scheme,
                        "segment_slope_difference_raw","Q",cid,gid))
                    with np.errstate(divide="ignore",invalid="ignore"):
                        turn=ref.x_ref_mean-cube["sd"][i]*q[:,i,1]/(2*q[:,i,2])
                    intervals.append(summarize_draws(turn,qs[:,i]==0,ref.turn_raw,
                        stage,scheme,"turn_raw_all_finite","Q",cid,gid))
            for model,weight in (("PL","equal"),("PQ","equal"),("HL","equal"),
                                 ("HQ","equal"),("PL","area"),("PQ","area")):
                status_for_model=ls if model in ("PL","HL") else qs
                values,reasons=pooled_from_moments(cube,xx,xy,y2,status_for_model,model,weight)
                original=rp.loc[rp.model.eq(model)&rp.grid_weighting.eq(weight)].iloc[0]
                diag.append({"stage":stage,"scheme":scheme,"candidate_id":cid,
                    "grid_id":"__pooled__","model":model+"_"+weight,"n_attempted":attempts,
                    "n_valid":int(np.sum(reasons=="valid")),
                    "failure_reasons":json.dumps(pd.Series(reasons).value_counts().drop("valid",errors="ignore").to_dict())})
                for metric in ("b","c","within_r2","mean_delta_low_tch","mean_delta_high_tch"):
                    if metric=="b" and model in ("HL","HQ"):continue
                    if metric=="c" and model in ("PL","HL"):continue
                    intervals.append(summarize_draws(values[metric],reasons=="valid",
                        original.get(metric,np.nan),stage,scheme,metric,model+"_"+weight,cid))
            for reduced,full,weight in (("PL","PQ","equal"),("HL","HQ","equal"),
                                         ("PL","PQ","area")):
                base,base_reason=pooled_from_moments(cube,xx,xy,y2,ls,reduced,weight)
                alt,alt_reason=pooled_from_moments(cube,xx,xy,y2,qs,full,weight)
                good=(base_reason=="valid")&(alt_reason=="valid")
                reference=rp.loc[rp.model.eq(full)&rp.grid_weighting.eq(weight)].iloc[0]
                intervals.append(summarize_draws(alt["within_r2"]-base["within_r2"],good,
                    reference.delta_r2_vs_linear,stage,scheme,
                    "paired_delta_r2_vs_"+reduced,full+"_"+weight,cid))
            # The three targets use the same X, original scales and resampled years.
            primary_pooled={}
            for model in ("PL","PQ","HL","HQ"):
                primary_pooled[model]=pooled_from_moments(cube,xx,xy,y2,
                    ls if model in ("PL","HL") else qs,model,"equal")
            for j,target in enumerate(TARGETS[1:],1):
                _,alt_xy,alt_y2=moments(cube,counts,j)
                alt_l,_,alt_ls,_,_=solve_grid(xx,alt_xy,alt_y2,2,original_ysd)
                alt_q,_,alt_qs,_,_=solve_grid(xx,alt_xy,alt_y2,3,original_ysd)
                for i,gid in enumerate(cube["grids"]):
                    reference=rb.loc[gid,target]
                    valid=(ls[:,i]==0)&(alt_ls[:,i]==0)
                    difference=(alt_l[:,i,1]-l[:,i,1])/cube["sd"][i]
                    intervals.append(summarize_draws(difference,valid,
                        reference.delta_linear_beta_raw_vs_primary,stage,scheme,
                        "paired_delta_beta_raw_vs_primary","L",cid,gid,target))
                    if gid in cube["qgrids"]:
                        valid=(qs[:,i]==0)&(alt_qs[:,i]==0)
                        intervals.append(summarize_draws(alt_q[:,i,2]-q[:,i,2],valid,
                            reference.delta_quadratic_c_vs_primary,stage,scheme,
                            "paired_delta_c_vs_primary","Q",cid,gid,target))
                for model in ("PL","PQ","HL","HQ"):
                    base,base_reason=primary_pooled[model]
                    alt,alt_reason=pooled_from_moments(cube,xx,alt_xy,alt_y2,
                        alt_ls if model in ("PL","HL") else alt_qs,model,"equal")
                    paired=(base_reason=="valid")&(alt_reason=="valid")
                    reference=pooled_targets.loc[pooled_targets.candidate_id.eq(cid)&
                        pooled_targets.target.eq(target)&pooled_targets.model.eq(model)&
                        pooled_targets.grid_weighting.eq("equal")].iloc[0]
                    primary_b=pooled_targets.loc[pooled_targets.candidate_id.eq(cid)&
                        pooled_targets.target.eq(Y)&pooled_targets.model.eq(model)&
                        pooled_targets.grid_weighting.eq("equal"),"b"].iloc[0]
                    for metric,point in (("b",reference.b-primary_b),
                                         ("within_r2",reference.paired_delta_within_r2_vs_primary),
                                         ("c",reference.paired_delta_c_vs_primary)):
                        if metric=="b" and model in ("HL","HQ"):continue
                        if metric=="c" and model in ("PL","HL"):continue
                        intervals.append(summarize_draws(alt[metric]-base[metric],paired,point,
                            stage,scheme,"paired_delta_"+metric+"_vs_primary",model+"_equal",cid,
                            target=target))
            print(f"{stage} {cid} {scheme}: {attempts} attempts",flush=True)
    for cid in ("relative_humidity__dec_jan","deep_soil_moisture_28_100__dec_jan"):
        cube=make_ad_cube(panel,aggregate,cid)
        refs=aggregate.loc[aggregate.candidate_id.eq(cid)].set_index("grid_id")
        pool_ref=aggregate_pooled.loc[aggregate_pooled.candidate_id.eq(cid)].set_index("model")
        ysd=np.array([panel.loc[panel.candidate_id.eq(cid)&panel.grid_id.eq(g),Y].std()
                      for g in cube["grids"]])
        for scheme,block in SCHEMES.items():
            key=(tuple(cube["axis"]),scheme)
            counts=draw_cache[key]
            xx,xy,y2=ad_moments(cube,counts)
            definitions={"MA":(0,1),"MAD":(0,1,3),"QA":(0,1,2),"QAD":(0,1,2,3)}
            fitted={name:solve_selected(xx,xy,y2,list(cols),ysd) for name,cols in definitions.items()}
            for i,gid in enumerate(cube["grids"]):
                ref=refs.loc[gid]
                for name,(_,r2,status,n) in fitted.items():
                    if name.startswith("Q") and gid not in cube["qgrids"]:continue
                    state=status[:,i]
                    diag.append({"stage":stage,"scheme":scheme,"candidate_id":cid,
                        "grid_id":gid,"model":name,"n_attempted":attempts,
                        "n_valid":int(np.sum(state==0)),
                        "failure_reasons":json.dumps({FAIL[k]:int(np.sum(state==k)) for k in (1,2,3,4)})})
                for full,base,metric,ref_beta,ref_delta in (("MAD","MA","b_D_raw","b_D_raw","mad_delta_r2"),
                                                              ("QAD","QA","qad_b_D_raw","qad_b_D_raw","qad_delta_r2")):
                    if full=="QAD" and gid not in cube["qgrids"]:continue
                    fb,fr,fs,_=fitted[full];_,br,bs,_=fitted[base]
                    valid=(fs[:,i]==0)&(bs[:,i]==0)
                    intervals.append(summarize_draws(fb[:,i,-1]/cube["d_sd"][i],valid,
                        ref[ref_beta],stage,scheme,metric,full,cid,gid))
                    intervals.append(summarize_draws(fr[:,i]-br[:,i],valid,
                        ref[ref_delta],stage,scheme,"incremental_r2_vs_"+base,full,cid,gid))
            pooled_fit={}
            for model in ("MA","MAD","QA","QAD","MAD_HA","QAD_HA"):
                base_model="MAD" if model=="MAD_HA" else "QAD" if model=="QAD_HA" else model
                values,reasons=pooled_ad_from_moments(cube,xx,xy,y2,fitted[base_model][2],model)
                pooled_fit[model]=(values,reasons)
                diag.append({"stage":stage,"scheme":scheme,"candidate_id":cid,"grid_id":"__pooled__",
                    "model":model,"n_attempted":attempts,"n_valid":int(np.sum(reasons=="valid")),
                    "failure_reasons":json.dumps(pd.Series(reasons).value_counts().drop("valid",errors="ignore").to_dict())})
                ref=pool_ref.loc[model]
                if model in ("MAD","QAD","MAD_HA","QAD_HA"):
                    for metric in ("coef_d","mean_d_iqr_contrast_tch"):
                        intervals.append(summarize_draws(values[metric],reasons=="valid",ref.get(metric,np.nan),
                            stage,scheme,metric,model,cid))
            for base,full in (("MA","MAD"),("QA","QAD")):
                bv,br=pooled_fit[base];fv,fr=pooled_fit[full]
                valid=(br=="valid")&(fr=="valid")
                intervals.append(summarize_draws(fv["within_r2"]-bv["within_r2"],valid,
                    pool_ref.loc[full,"incremental_r2_vs_base"],stage,scheme,
                    "incremental_r2_vs_"+base,full,cid))
            print(f"{stage} {cid} aggregation {scheme}: {attempts} attempts",flush=True)
    pd.DataFrame(diag).to_csv(OUT/f"bootstrap_diagnostics_{stage}.csv",index=False)
    pd.DataFrame(intervals).to_csv(OUT/f"bootstrap_intervals_{stage}.csv",index=False)
    pd.DataFrame(calendar).drop_duplicates(["scheme","year"]).to_csv(OUT/f"bootstrap_calendar_weights_{stage}.csv",index=False)
    np.savez_compressed(OUT/f"bootstrap_draw_counts_{stage}.npz",
        **{f"{scheme}_{axis[0]}_{axis[-1]}":matrix
           for (axis,scheme),matrix in draw_cache.items()})
    d=pd.DataFrame(diag)
    pooled_diag=d.loc[d.grid_id.eq("__pooled__")]
    validity=pooled_diag.n_valid.min()/attempts
    result={"stage":stage,"attempts_per_scheme":attempts,"min_pooled_validity":validity,
        "all_pooled_at_least_80pct":bool(validity>=.8),
        "diagnostics_rows":len(diag),"interval_rows":len(intervals)}
    (OUT/f"bootstrap_{stage}_summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if result["all_pooled_at_least_80pct"] else 2


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",choices=("smoke","full"),required=True)
    args=parser.parse_args(argv)
    return run(args.stage)


if __name__=="__main__":
    raise SystemExit(main())
