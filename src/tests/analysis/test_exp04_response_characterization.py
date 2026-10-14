"""Focused EXP-04 tests for alignment, model equivalence and bootstrap support."""

import numpy as np
import pandas as pd

from analysis import exp04_bootstrap as boot
from analysis import exp04_response_characterization as core


def test_frozen_month_alignment_and_candidate_universe():
    c=core.load_universe()
    slots=core.exp05.discover_slots(core.ROOT).set_index("month_slot")
    assert len(c)==38 and c.candidate_id.is_unique
    assert [(int(slots.loc[k,"source_year_offset"]),int(slots.loc[k,"source_calendar_month"]))
            for k in range(-4,1)]==[(-1,12),(0,1),(0,2),(0,3),(0,4)]


def test_synthetic_quadratic_contrasts_and_raw_slope():
    x=np.linspace(-2,2,40)
    y=3+2*x+.5*x*x
    group=pd.DataFrame({"candidate_id":"synthetic","grid_id":"g","yield_year":np.arange(1981,2021),
        "x":x,"weight_coverage":1.,core.exp05.Y10:y,
        "actual_weight_denominator_ha":100.,"grid_latitude":-20.,"grid_longitude":-50.})
    result=core.estimate_grid(group,core.exp05.Y10)
    assert result["linear_status"]=="fit" and result["quadratic_status"]=="fit"
    assert np.isclose(result["local_slope_p50_raw"],2)
    q=np.quantile(x,[.1,.5,.9])
    assert np.isclose(result["delta_low_tch"],2*(q[1]-q[0])+.5*(q[1]**2-q[0]**2))
    assert np.isclose(result["segment_slope_difference_raw"],.5*(q[2]-q[0]))


def test_ad_representation_matches_separate_months():
    dec=np.array([2.,4.,1.,5.,8.,3.,7.,6.])
    jan=np.array([5.,1.,6.,2.,7.,8.,4.,3.])
    a=(dec+jan)/2;d=(jan-dec)/2
    y=1+2*dec+3*jan
    fit=core.design_fit(y,a,extra=d)[0]
    b_a,b_d=fit["beta"][1:]
    assert np.isclose((b_a-b_d)/2,2.)
    assert np.isclose((b_a+b_d)/2,3.)
    direct=core.design_fit(y,dec,extra=jan)[0]
    assert np.isclose(fit["sse"],direct["sse"])


def test_moving_blocks_use_consecutive_calendar_years_without_wrap():
    axis=np.arange(1990,2001)
    idx=boot.draw_calendar_indices(axis,50,3,21)
    assert idx.shape==(50,len(axis))
    assert np.all((idx>=0)&(idx<len(axis)))
    assert np.all(np.diff(idx[:,:9].reshape(50,3,3),axis=2)==1)
    counts=boot.draw_calendar_counts(axis,50,3,21)
    assert np.all(counts.sum(axis=1)==len(axis))


def test_fixed_grid_moments_reproduce_direct_pooled_models():
    years=np.arange(2000,2008)
    z=np.stack([np.linspace(-1,1,8),np.linspace(-1.2,.8,8)])
    y=np.stack([1+.3*z[0]+.4*z[0]**2,3-.2*z[1]+.4*z[1]**2])
    cube={"z":z,"y":np.stack([y,y,y],axis=2),"mask":np.ones_like(z,dtype=bool),
          "qidx":np.array([0,1]),"pi":np.array([.4,.6]),
          "anchors":np.array([[[-.8,0,.8]],[[-.8,0,.8]]]).reshape(2,3)}
    xx,xy,y2=boot.moments(cube,np.ones((1,len(years)),int))
    status=np.zeros((1,2),np.int8)
    for model in ("PL","PQ","HL","HQ"):
        direct,_=core._fit_fe([{"grid_id":f"g{i}","z":z[i],core.exp05.Y10:y[i],"pi":cube["pi"][i]}
                               for i in range(2)],model,"equal",core.exp05.Y10,model in ("HL","HQ"))
        batched,reason=boot.pooled_from_moments(cube,xx,xy,y2,status,model,"equal")
        assert reason[0]=="valid"
        assert np.isclose(batched["within_r2"][0],direct["within_r2"],atol=1e-10)
        if model in ("PQ","HQ"):
            assert np.isclose(batched["c"][0],direct["c"],atol=1e-10)


def test_ad_pooled_moments_reproduce_direct_ladder():
    z=np.stack([np.linspace(-1.2,1.1,9),np.linspace(-.9,1.3,9)])
    d=np.stack([np.array([.4,-.8,.2,1.,-.3,.7,-1.,.6,-.5]),
                np.array([-.6,.2,.9,-.8,.5,-.2,1.,-.4,.3])])
    y=np.stack([1+.7*z[0]+.15*z[0]**2+.4*d[0],
                3-.2*z[1]+.15*z[1]**2+.4*d[1]])
    x=np.stack([np.ones_like(z),z,z*z,d],axis=2)
    cube={"x":x,"y":y,"mask":np.ones_like(z,dtype=bool),"qidx":np.array([0,1]),
          "grids":("g0","g1"),"d_iqr_scaled":np.ones(2)}
    xx,xy,y2=boot.ad_moments(cube,np.ones((1,9),int))
    parts=[{"grid_id":f"g{i}","z":z[i],"d":d[i],"y":y[i]} for i in range(2)]
    definitions={"MA":(("z",),False),"MAD":(("z","d"),False),
                 "QA":(("z","z2"),False),"QAD":(("z","z2","d"),False),
                 "MAD_HA":(("d",),True),"QAD_HA":(("z2","d"),True)}
    for model,(terms,heterogeneous) in definitions.items():
        direct,reason=core.fit_pooled_ad(parts,terms,heterogeneous)
        assert reason==""
        batched,status=boot.pooled_ad_from_moments(cube,xx,xy,y2,np.zeros((1,2),np.int8),model)
        assert status[0]=="valid"
        assert np.isclose(batched["within_r2"][0],direct["within_r2"],atol=1e-10)
        if "d" in terms:
            assert np.isclose(batched["coef_d"][0],direct["beta"][terms.index("d")],atol=1e-10)
