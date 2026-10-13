import numpy as np
import pandas as pd

from analysis import exp05b_summarize as summary


def test_interval_uses_only_valid_finite_values():
    low,high=summary.interval(pd.Series([1.,2.,3.,np.nan]))
    assert np.isclose(low,1.05)
    assert np.isclose(high,2.95)


def test_empty_interval_is_explicitly_missing():
    low,high=summary.interval([np.nan])
    assert np.isnan(low) and np.isnan(high)


def test_core_roster_includes_joint_interaction_and_spatial_checks():
    assert "dry_minus_wet_v_P2" in summary.CORE_ESTIMANDS
    assert "dry_minus_wet_v_Q2_prime" in summary.PRIMARY_EXTRA
    assert "dry_minus_wet_v_spatial" in summary.PRIMARY_EXTRA
    assert "dry_minus_wet_v_P2" in summary.PAIRED_ESTIMANDS
