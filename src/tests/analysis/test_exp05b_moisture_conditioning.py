"""Focused downstream EXP-05B tests; no upstream pipeline execution."""

import numpy as np
import pandas as pd

from analysis import exp05_conditional_temperature_vpd as exp05
from analysis import exp05b_moisture_conditioning as work


def test_calendar_safe_antecedents_cross_year():
    years=pd.Series([1982,1982,1982])
    months=pd.Series([1,2,9])
    old_year,old_month=work.shift_month(years,months,3)
    assert list(zip(old_year,old_month))==[(1981,10),(1981,11),(1982,6)]


def test_modifier_completeness_and_no_target_month():
    key={"grid_id":"g","yield_year":1982,"month_slot":-7,
         "source_year":1981,"source_calendar_month":9}
    base=pd.DataFrame([{**key,exp05.Y10:1.,exp05.TEMP:26.,exp05.VPD:1.}])
    weights=pd.DataFrame({"grid_id":["g"],"year":[1982],"ibge_code":["1"],"actual_weight":[1.]})
    rows=[]
    for month in range(6,10):
        rows.append({"grid_id":"g","ibge_code":"1","source_year":1981,
            "source_calendar_month":month,exp05.TEMP:26.,exp05.VPD:1.,
            work.SM:month/100,work.DEEP:month/100,work.RAIN:float(month)})
    weather=pd.DataFrame(rows)
    result=work.add_antecedents(base,weather,weights)
    assert np.isclose(result.loc[0,"sm_28_100_prev3_mean"],.07)
    assert result.loc[0,"rain_prev3_sum"]==21
    weather.loc[weather.source_calendar_month.eq(7),work.SM]=np.nan
    missing=work.add_antecedents(base,weather,weights)
    assert pd.isna(missing.loc[0,"sm_28_100_prev3_mean"])
    assert np.isclose(missing.loc[0,"sm_28_100_prev1"],.08)


def test_two_sided_partial_and_nested_same_sample():
    rng=np.random.default_rng(9)
    n=45
    t=rng.normal(size=n)
    v=rng.normal(size=n)
    s=rng.normal(size=n)
    y=2*t-v+.5*s+rng.normal(size=n)*.02
    assert exp05.partial_correlation(y,v,np.column_stack([t,s])) < -.9
    assert exp05.partial_correlation(y,t,np.column_stack([v,s])) > .9
    frame=pd.DataFrame({"grid_id":"g","yield_year":np.arange(1981,1981+n),
                        exp05.Y10:y,exp05.TEMP:t,exp05.VPD:v,
                        "sm_28_100_prev3_mean":s})
    fit=work.pooled_fit(frame,"sm_28_100_prev3_mean",exp05.Y10,
                        ("P0","P1","P2"))
    assert fit["status"]=="estimable"
    assert fit["r2_P1"]>=fit["r2_P0"]-1e-10
    assert fit["r2_P2"]>=fit["r2_P1"]-1e-10


def test_synthetic_moisture_interaction_and_q_prime_nesting():
    rng=np.random.default_rng(19)
    frames=[]
    for grid in ("a","b"):
        n=45;t=rng.normal(size=n);v=rng.normal(size=n);s=rng.normal(size=n)
        y=.6*t-.4*v+1.2*v*s+.3*t*s+.4*t*v+rng.normal(size=n)*.02
        frames.append(pd.DataFrame({"grid_id":grid,"yield_year":np.arange(1981,1981+n),
                        exp05.Y10:y,exp05.TEMP:t,exp05.VPD:v,
                        "sm_28_100_prev3_mean":s}))
    frame=pd.concat(frames,ignore_index=True)
    fit=work.pooled_fit(frame,"sm_28_100_prev3_mean",exp05.Y10,
                       tuple(work.MODELS))
    assert fit["status"]=="estimable"
    assert fit["dry_minus_wet_v_P2"]<0
    assert fit["r2_Q2_prime"]>=fit["r2_Q1_prime"]-1e-10
    assert fit["r2_Q2_prime"]>=fit["r2_Q2"]-1e-10
    assert fit["r2_Q1_prime"]>=fit["r2_Q1"]-1e-10


def test_synchronized_calendar_block_draws_and_failure():
    draws=work.synchronized_draws(50,3,42)
    assert len(draws)==50
    assert all(sum(draw.values())==45 for draw in draws)
    assert all(set(draw)==set(range(1981,2026)) for draw in draws)
    assert any(draw[1981]==0 for draw in draws)
    rng=np.random.default_rng(6)
    frame=pd.DataFrame({"grid_id":"g","yield_year":np.arange(1981,2003),
                        exp05.Y10:rng.normal(size=22),exp05.TEMP:rng.normal(size=22),
                        exp05.VPD:rng.normal(size=22),"sm_28_100_prev3_mean":rng.normal(size=22)})
    empty={year:0 for year in range(1981,2026)}
    fit=work.pooled_fit(frame,"sm_28_100_prev3_mean",exp05.Y10,("P0","P1","P2"),empty)
    assert fit["status"]=="grid_failed"
    assert fit["n_failed_grids"]==1
