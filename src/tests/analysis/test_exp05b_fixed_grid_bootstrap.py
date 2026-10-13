"""Numerical and support invariants for the approved fixed-grid bootstrap."""

import numpy as np

from analysis import exp05b_fixed_grid_bootstrap as boot


def synthetic_cube(seed=4, n=45):
    rng=np.random.default_rng(seed)
    values=np.full((2,45,4),np.nan)
    quartiles=[]
    for i in range(2):
        t,v,s=rng.normal(size=(3,n))
        y=.7*t-.5*v+.6*v*s+.3*t*s+rng.normal(size=n)*.2
        values[i,:n]=np.column_stack([y,t,v,s])
        quartiles.append(np.quantile(s,[.25,.75]))
    q=np.array(quartiles)
    return boot.Cube("primary","s","y",-7,"Sep_(t-1)",("a","b"),
                     values,q[:,0],q[:,1])


def test_sub20_resample_allowed_if_identified():
    cube=synthetic_cube()
    counts=np.zeros(45,dtype=np.int16)
    counts[:12]=1
    result=boot.fit_cube(cube,counts,full_primary=True)
    assert result["status"]=="estimable"
    assert result["spatial_status"]=="estimable"
    assert result["n_below_original_n20"]==2
    assert result["n_fixed_grids"]==result["n_estimable_grids"]==2


def test_no_silent_grid_drop_for_unestimable_draw():
    cube=synthetic_cube()
    counts=np.zeros(45,dtype=np.int16)
    counts[0]=1;counts[1]=1;counts[2]=1
    result=boot.fit_cube(cube,counts,full_primary=True)
    assert result["status"]=="invalid"
    assert result["n_estimable_grids"]==0
    assert result["failure_reason"]=="grid_n_below_local_additive_rank_minimum"
    assert result["failed_grids"]=="a;b"


def test_draws_synchronized_and_separate_from_smoke():
    smoke=boot.draw_counts(50,3,20261015)
    final=boot.draw_counts(1000,3,20261016)
    assert smoke.shape==(50,45) and final.shape==(1000,45)
    assert np.all(smoke.sum(axis=1)==45)
    assert np.all(final.sum(axis=1)==45)
    assert not np.array_equal(smoke[0],final[0])


def test_extreme_predictor_collinearity_is_failure_not_drop():
    cube=synthetic_cube()
    values=cube.values.copy()
    values[:,:,2]=values[:,:,1]
    bad=boot.Cube(cube.scenario,cube.modifier,cube.target,cube.month_slot,cube.label,
                  cube.grids,values,cube.s25,cube.s75)
    result=boot.fit_cube(bad,np.ones(45,dtype=np.int16),full_primary=True)
    assert result["status"]=="invalid"
    assert result["n_estimable_grids"]==0
    assert result["failure_reason"] in ("singular_local_t_v_s_design",
                                        "ill_conditioned_local_t_v_s_design",
                                        "insufficient_residual_predictor_variation")
