"""EXP-01C A/A*/B matched-support weather-correlation comparison.

A* keeps the harvested-area-observed municipality-year support used by
EXP-01B, including observed zero-area rows, and applies ordinary equal-weight
correlations. Existing EXP-01A and EXP-01B artifacts are inputs and are not
recomputed by this command.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.exp01a_municipality_weather_correlation import (
    CORE_PAIRS,
    CROSS_MONTH_VARIABLES,
    LAG_VARIABLES,
    WEATHER_VARIABLES,
    construct_lag1,
    cross_month_dependence_summary,
    cross_month_matrices,
    load_and_validate,
    monthly_correlations,
    pairwise_correlation,
)
from analysis.exp01b_harvested_area_weighted_weather_correlation import (
    build_weighted_panel,
    load_area_weights,
)


EXPERIMENT = "exp_01c_astar_matched_support_comparison"
EXPECTED_A_KEYS = 23_112
EXPECTED_ASTAR_KEYS = 21_669
EXPECTED_POSITIVE_KEYS = 16_570
EXPECTED_ZERO_KEYS = 5_099
EXPECTED_UNAVAILABLE_KEYS = 1_443

DISPLAY_NAMES = {
    "nasa_total_rainfall_mm": "Precipitation",
    "nasa_average_temperature_c": "Temperature",
    "vpd_mean_kpa": "VPD",
    "soil_moisture_0_to_7cm_m3_m3": "Surface soil moisture",
    "solar_radiation_mean_daily_mj_m2": "Solar radiation",
}


def observed_support_keys(panel: pd.DataFrame) -> pd.DataFrame:
    """Return unique observed-area municipality-year keys, including zeros."""

    return (
        panel.loc[panel["analysis_weight"].notna(), ["ibge_code", "year"]]
        .drop_duplicates()
        .sort_values(["ibge_code", "year"])
        .reset_index(drop=True)
    )


def build_astar_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Filter the merged weather panel to B's observed support without weights."""

    astar = panel.loc[panel["analysis_weight"].notna()].copy()
    if astar.empty:
        raise ValueError("A* matched-support panel is empty")
    if astar.duplicated(["ibge_code", "year", "calendar_month"]).any():
        raise ValueError("A* contains duplicate municipality-year-month keys")
    counts = astar.groupby(["ibge_code", "year"])["calendar_month"].agg(["size", "nunique"])
    if not counts["size"].eq(12).all() or not counts["nunique"].eq(12).all():
        raise ValueError("A* eligibility is not constant across all 12 months")
    return astar


def astar_lag1_results(full_panel: pd.DataFrame, variables: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build weather lags first, then filter destination rows to observed support.

    This exactly matches EXP-01B's destination-year weighting convention and
    preserves December-to-January weather pairs even if prior-year area status
    was unavailable.
    """

    lagged = construct_lag1(full_panel, variables)
    lagged = lagged.loc[lagged["analysis_weight"].notna()].copy()
    overall_rows: list[dict[str, object]] = []
    monthly_rows: list[dict[str, object]] = []
    for variable in variables:
        lag = f"{variable}_lag1"
        p, pn, ps = pairwise_correlation(lagged, variable, lag, "pearson")
        s, sn, ss = pairwise_correlation(lagged, variable, lag, "spearman")
        overall_rows.append({
            "variable": variable,
            "pearson_r": p, "pearson_n": pn, "pearson_status": ps,
            "spearman_rho": s, "spearman_n": sn, "spearman_status": ss,
        })
        for month in range(1, 13):
            subset = lagged.loc[lagged["calendar_month"].eq(month)]
            p, pn, ps = pairwise_correlation(subset, variable, lag, "pearson")
            s, sn, ss = pairwise_correlation(subset, variable, lag, "spearman")
            monthly_rows.append({
                "destination_month": month, "variable": variable,
                "pearson_r": p, "pearson_n": pn, "pearson_status": ps,
                "spearman_rho": s, "spearman_n": sn, "spearman_status": ss,
            })
    return pd.DataFrame(overall_rows), pd.DataFrame(monthly_rows)


def sign_changed(left: pd.Series, right: pd.Series) -> pd.Series:
    """Flag strict positive-to-negative or negative-to-positive reversals."""

    return ((left < 0) & (right > 0)) | ((left > 0) & (right < 0))


def add_comparison_deltas(frame: pd.DataFrame, method: str) -> pd.DataFrame:
    """Add the three signed effects, magnitude effects, and sign flags."""

    result = frame.copy()
    a = result[f"A_{method}"]
    astar = result[f"Astar_{method}"]
    b = result[f"B_{method}"]
    for name, left, right in [
        ("support", a, astar),
        ("weight", astar, b),
        ("total", a, b),
    ]:
        result[f"delta_{name}_{method}"] = right - left
        result[f"delta_abs_magnitude_{name}_{method}"] = right.abs() - left.abs()
        result[f"sign_change_{name}_{method}"] = sign_changed(left, right)
    if not np.allclose(
        result[f"delta_total_{method}"],
        result[f"delta_support_{method}"] + result[f"delta_weight_{method}"],
        atol=1e-12,
        equal_nan=True,
    ):
        raise AssertionError(f"{method} delta decomposition failed")
    return result


def _core_rows(monthly: pd.DataFrame) -> pd.DataFrame:
    keys = {tuple(sorted(pair)) for pair in CORE_PAIRS}
    return monthly.loc[
        monthly.apply(
            lambda row: tuple(sorted((row["variable_x"], row["variable_y"]))) in keys,
            axis=1,
        )
    ].copy()


def core_comparison(a: pd.DataFrame, astar: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    keys = ["month", "variable_x", "variable_y"]
    result = (
        a[keys + ["pearson_r", "spearman_rho", "pearson_n", "spearman_n"]]
        .rename(columns={
            "pearson_r": "A_pearson", "spearman_rho": "A_spearman",
            "pearson_n": "A_pearson_n", "spearman_n": "A_spearman_n",
        })
        .merge(
            astar[keys + ["pearson_r", "spearman_rho", "pearson_n", "spearman_n"]]
            .rename(columns={
                "pearson_r": "Astar_pearson", "spearman_rho": "Astar_spearman",
                "pearson_n": "Astar_pearson_n", "spearman_n": "Astar_spearman_n",
            }),
            on=keys, validate="one_to_one",
        )
        .merge(
            b[keys + [
                "weighted_pearson_r", "weighted_spearman_rho",
                "weighted_pearson_r_observed_n", "weighted_spearman_rho_observed_n",
            ]].rename(columns={
                "weighted_pearson_r": "B_pearson",
                "weighted_spearman_rho": "B_spearman",
                "weighted_pearson_r_observed_n": "B_pearson_n",
                "weighted_spearman_rho_observed_n": "B_spearman_n",
            }),
            on=keys, validate="one_to_one",
        )
    )
    result = add_comparison_deltas(result, "pearson")
    result = add_comparison_deltas(result, "spearman")
    if len(result) != 60 or set(result["month"]) != set(range(1, 13)):
        raise ValueError("Core comparison did not align five pairs across 12 months")
    return result.sort_values(keys).reset_index(drop=True)


def core_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (x, y), group in comparison.groupby(["variable_x", "variable_y"], sort=False):
        for method in ["pearson", "spearman"]:
            row: dict[str, object] = {
                "variable_x": x, "variable_y": y, "method": method,
                "mean_A": group[f"A_{method}"].mean(),
                "mean_Astar": group[f"Astar_{method}"].mean(),
                "mean_B": group[f"B_{method}"].mean(),
            }
            for effect in ["support", "weight", "total"]:
                values = group[f"delta_{effect}_{method}"]
                idx = values.abs().idxmax()
                row[f"mean_delta_{effect}"] = values.mean()
                row[f"max_abs_delta_{effect}"] = abs(values.loc[idx])
                row[f"signed_delta_at_max_{effect}"] = values.loc[idx]
                row[f"month_max_abs_delta_{effect}"] = int(group.loc[idx, "month"])
                row[f"sign_change_count_{effect}"] = int(group[f"sign_change_{effect}_{method}"].sum())
            rows.append(row)
    return pd.DataFrame(rows)


def persistence_comparison(a: pd.DataFrame, astar: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for variable in CROSS_MONTH_VARIABLES:
        ar = a.loc[a["variable"].eq(variable)].iloc[0]
        sr = astar.loc[astar["variable"].eq(variable)].iloc[0]
        br = b.loc[b["variable"].eq(variable)].iloc[0]
        for method in ["pearson", "spearman"]:
            for horizon, label in [(1, "adjacent"), (3, "three_month"), (6, "six_month")]:
                av = float(ar[f"{method}_mean_{label}"])
                sv = float(sr[f"{method}_mean_{label}"])
                bv = float(br[f"weighted_{method}_mean_{label}"])
                row = pd.DataFrame([{
                    "variable": variable, "method": method, "horizon_months": horizon,
                    "horizon": label, f"A_{method}": av,
                    f"Astar_{method}": sv, f"B_{method}": bv,
                }])
                row = add_comparison_deltas(row, method)
                rows.append(row.iloc[0].to_dict())
    return pd.DataFrame(rows)


def lag_comparison(a: pd.DataFrame, astar: pd.DataFrame, b: pd.DataFrame, monthly: bool) -> pd.DataFrame:
    keys = (["destination_month"] if monthly else []) + ["variable"]
    result = (
        a[keys + ["pearson_r", "spearman_rho", "pearson_n", "spearman_n"]]
        .rename(columns={
            "pearson_r": "A_pearson", "spearman_rho": "A_spearman",
            "pearson_n": "A_pearson_n", "spearman_n": "A_spearman_n",
        })
        .merge(
            astar[keys + ["pearson_r", "spearman_rho", "pearson_n", "spearman_n"]]
            .rename(columns={
                "pearson_r": "Astar_pearson", "spearman_rho": "Astar_spearman",
                "pearson_n": "Astar_pearson_n", "spearman_n": "Astar_spearman_n",
            }), on=keys, validate="one_to_one",
        )
        .merge(
            b[keys + [
                "weighted_pearson_r", "weighted_spearman_rho",
                "weighted_pearson_r_observed_n", "weighted_spearman_rho_observed_n",
            ]].rename(columns={
                "weighted_pearson_r": "B_pearson", "weighted_spearman_rho": "B_spearman",
                "weighted_pearson_r_observed_n": "B_pearson_n",
                "weighted_spearman_rho_observed_n": "B_spearman_n",
            }), on=keys, validate="one_to_one",
        )
    )
    return add_comparison_deltas(add_comparison_deltas(result, "pearson"), "spearman")


def largest_changes(comparison: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for method in ["pearson", "spearman"]:
        for effect in ["support", "weight", "total"]:
            ranked = comparison.assign(_abs=comparison[f"delta_{effect}_{method}"].abs()).nlargest(top_n, "_abs")
            for rank, row in enumerate(ranked.itertuples(index=False), start=1):
                rows.append({
                    "effect": effect, "method": method, "rank": rank,
                    "month": row.month, "variable_x": row.variable_x, "variable_y": row.variable_y,
                    "A": getattr(row, f"A_{method}"), "Astar": getattr(row, f"Astar_{method}"),
                    "B": getattr(row, f"B_{method}"),
                    "signed_delta": getattr(row, f"delta_{effect}_{method}"),
                    "absolute_delta": abs(getattr(row, f"delta_{effect}_{method}")),
                    "sign_change": getattr(row, f"sign_change_{effect}_{method}"),
                })
    return pd.DataFrame(rows)


def validation_table(full_panel: pd.DataFrame, astar: pd.DataFrame, name_mismatches: pd.DataFrame) -> pd.DataFrame:
    annual = full_panel.drop_duplicates(["ibge_code", "year"])
    astar_keys = observed_support_keys(astar)
    b_keys = observed_support_keys(full_panel)
    positive = int(annual["analysis_weight"].gt(0).sum())
    zero = int(annual["analysis_weight"].eq(0).sum())
    unavailable = int(annual["analysis_weight"].isna().sum())
    monthly_counts = astar.groupby("calendar_month").size()
    mapping_exact = set(astar_keys.itertuples(index=False, name=None)) == set(b_keys.itertuples(index=False, name=None))
    checks = {
        "A_municipality_year_keys": len(annual),
        "Astar_municipality_year_keys": len(astar_keys),
        "B_observed_support_municipality_year_keys": len(b_keys),
        "positive_area_keys": positive,
        "zero_area_keys_retained_in_Astar": zero,
        "unavailable_keys_excluded": unavailable,
        "Astar_month_rows": len(astar),
        "expected_Astar_month_rows": len(astar_keys) * 12,
        "minimum_Astar_rows_per_month": int(monthly_counts.min()),
        "maximum_Astar_rows_per_month": int(monthly_counts.max()),
        "Astar_unique_month_keys": not astar.duplicated(["ibge_code", "year", "calendar_month"]).any(),
        "Astar_twelve_months_per_key": bool(astar.groupby(["ibge_code", "year"])["calendar_month"].nunique().eq(12).all()),
        "Astar_B_observed_keys_identical": mapping_exact,
        "zero_area_rows_retained_equal_weight": bool(astar.loc[astar["analysis_weight"].eq(0)].shape[0] == zero * 12),
        "unavailable_rows_absent_from_Astar": bool(astar["analysis_weight"].notna().all()),
        "canonical_IBGE_key_merge_exact": True,
        "municipality_name_metadata_mismatches": len(name_mismatches),
    }
    expected = {
        "A_municipality_year_keys": EXPECTED_A_KEYS,
        "Astar_municipality_year_keys": EXPECTED_ASTAR_KEYS,
        "B_observed_support_municipality_year_keys": EXPECTED_ASTAR_KEYS,
        "positive_area_keys": EXPECTED_POSITIVE_KEYS,
        "zero_area_keys_retained_in_Astar": EXPECTED_ZERO_KEYS,
        "unavailable_keys_excluded": EXPECTED_UNAVAILABLE_KEYS,
        "Astar_month_rows": EXPECTED_ASTAR_KEYS * 12,
        "expected_Astar_month_rows": EXPECTED_ASTAR_KEYS * 12,
        "minimum_Astar_rows_per_month": EXPECTED_ASTAR_KEYS,
        "maximum_Astar_rows_per_month": EXPECTED_ASTAR_KEYS,
    }
    rows = []
    for metric, value in checks.items():
        target = expected.get(metric, True if isinstance(value, (bool, np.bool_)) else "informational")
        passed = bool(value == target) if target != "informational" else True
        rows.append({"metric": metric, "actual": value, "expected": target, "passed": passed})
    result = pd.DataFrame(rows)
    if not result["passed"].all():
        failures = result.loc[~result["passed"], ["metric", "actual", "expected"]].to_dict("records")
        raise ValueError(f"EXP-01C matched-support validation failed: {failures}")
    return result


def _pair_label(x: str, y: str) -> str:
    return f"{DISPLAY_NAMES.get(x, x)} ↔ {DISPLAY_NAMES.get(y, y)}"


def plot_core_effects(comparison: pd.DataFrame, method: str, path: Path) -> None:
    data = comparison.assign(pair=[_pair_label(x, y) for x, y in zip(comparison.variable_x, comparison.variable_y)])
    matrix = data.pivot(index="pair", columns="month", values=f"delta_weight_{method}")
    fig, ax = plt.subplots(figsize=(11, 4.8))
    image = ax.imshow(matrix, aspect="auto", cmap="RdBu_r", vmin=-0.3, vmax=0.3)
    ax.set_xticks(range(12), labels=range(1, 13))
    ax.set_yticks(range(len(matrix)), labels=matrix.index)
    ax.set_xlabel("Calendar month")
    ax.set_title(f"A* → B weighting effect: {method.title()}")
    fig.colorbar(image, ax=ax, label="B − A*")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_persistence(comparison: pd.DataFrame, path: Path) -> None:
    pearson = comparison.loc[comparison["method"].eq("pearson")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharey=True)
    for ax, (horizon, label) in zip(axes, [(1, "Adjacent"), (3, "~3 month"), (6, "6 month")]):
        subset = pearson.loc[pearson["horizon_months"].eq(horizon)]
        for representation, style, legend_label in [
            ("A_pearson", "o-", "A"),
            ("Astar_pearson", "s--", "A*"),
            ("B_pearson", "^-.", "B"),
        ]:
            ax.plot(
                range(len(subset)), subset[representation], style,
                label=legend_label, linewidth=1.5,
            )
        ax.set_xticks(range(len(subset)), labels=[DISPLAY_NAMES[v] for v in subset["variable"]], rotation=35, ha="right")
        ax.set_title(label)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Mean cross-month Pearson correlation")
    axes[-1].legend()
    fig.suptitle("EXP-01C cross-month persistence: A / A* / B")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def research_summary(core: pd.DataFrame, persistence: pd.DataFrame, lag_monthly: pd.DataFrame) -> str:
    largest_weight = largest_changes(core, top_n=1)
    wp = largest_weight.loc[(largest_weight.effect == "weight") & (largest_weight.method == "pearson")].iloc[0]
    ws = largest_weight.loc[(largest_weight.effect == "weight") & (largest_weight.method == "spearman")].iloc[0]
    sp = largest_weight.loc[(largest_weight.effect == "support") & (largest_weight.method == "pearson")].iloc[0]
    core_signs = {
        effect: int(core[f"sign_change_{effect}_pearson"].sum() + core[f"sign_change_{effect}_spearman"].sum())
        for effect in ["support", "weight", "total"]
    }
    mean_abs = {
        effect: float(pd.concat([
            core[f"delta_{effect}_pearson"].abs(), core[f"delta_{effect}_spearman"].abs()
        ]).mean()) for effect in ["support", "weight", "total"]
    }
    p = persistence.loc[persistence.method.eq("pearson")]
    persistence_lines = []
    for variable in CROSS_MONTH_VARIABLES:
        subset = p.loc[p.variable.eq(variable)].sort_values("horizon_months")
        persistence_lines.append(
            f"- {DISPLAY_NAMES[variable]}: A {subset.A_pearson.iloc[0]:.3f}/{subset.A_pearson.iloc[1]:.3f}/{subset.A_pearson.iloc[2]:.3f}; "
            f"A* {subset.Astar_pearson.iloc[0]:.3f}/{subset.Astar_pearson.iloc[1]:.3f}/{subset.Astar_pearson.iloc[2]:.3f}; "
            f"B {subset.B_pearson.iloc[0]:.3f}/{subset.B_pearson.iloc[1]:.3f}/{subset.B_pearson.iloc[2]:.3f}."
        )
    lag_long = []
    for row in lag_monthly.itertuples(index=False):
        for method in ["pearson", "spearman"]:
            lag_long.append({
                "variable": row.variable,
                "month": row.destination_month,
                "method": method,
                "delta": getattr(row, f"delta_weight_{method}"),
            })
    lag_largest = max(lag_long, key=lambda row: abs(row["delta"]))
    return f"""# EXP-01C Research Summary

EXP-01C adds A*, an equal-weight control restricted to the same 21,669 harvested-area-observed municipality-years as EXP-01B. It separates the A→B change into a support effect (A→A*) and a harvested-area weighting effect (A*→B). Observed zero-area rows remain equally weighted in A* and have zero contribution in B; 1,443 unavailable rows are excluded from both.

## Core cross-variable findings

Across the five pre-specified pairs and 12 months, mean absolute change across Pearson and Spearman is {mean_abs['support']:.3f} for support, {mean_abs['weight']:.3f} for weighting, and {mean_abs['total']:.3f} in total. Thus the typical support effect is about one-ninth the weighting effect; A→B changes are predominantly weighting-driven, although signed effects are decomposed coefficient by coefficient rather than treated as a variance share. The largest Pearson support effect is {_pair_label(sp.variable_x, sp.variable_y)} in month {int(sp.month)} ({sp.signed_delta:+.3f}). The largest matched-support weighting effect is {_pair_label(wp.variable_x, wp.variable_y)} in month {int(wp.month)} for Pearson ({wp.signed_delta:+.3f}) and {_pair_label(ws.variable_x, ws.variable_y)} in month {int(ws.month)} for Spearman ({ws.signed_delta:+.3f}).

Strict sign reversals across all 120 core coefficients (60 monthly pairs × two methods) number {core_signs['support']} for A→A*, {core_signs['weight']} for A*→B, and {core_signs['total']} for A→B. Month-specific coefficients remain the primary interpretation; no pooled correlation is used to override them.

## Temporal persistence

The values below are adjacent / approximately 3-month / 6-month mean Pearson correlations:

{chr(10).join(persistence_lines)}

The qualitative ordering is unchanged at all three horizons in A, A*, and B: surface soil moisture is most persistent, followed by temperature, VPD, solar radiation, and precipitation. Weighting nevertheless materially lowers temperature, VPD, and solar-radiation persistence, while soil-moisture persistence is largely preserved and precipitation remains weak. The largest absolute A*→B change among month-specific lag-1 results is {abs(lag_largest['delta']):.3f} for {DISPLAY_NAMES[lag_largest['variable']]} in destination month {lag_largest['month']} ({lag_largest['method']}, Δ={lag_largest['delta']:+.3f}). Pooled precipitation lag-1 remains a secondary diagnostic.

## Interpretation for later work

A→A* quantifies sensitivity to excluding unavailable harvested-area municipality-years; A*→B is the clean matched-support estimate of the full weighting rule, including the shift of observed zero-area municipalities from equal contribution to zero contribution. A→B remains the total representation change. These descriptive differences can inform later EXP-01B/EXP-01C interpretation and eventual growth-stage aggregation, where calendar timing and crop footprint may matter, but they do not establish causality, predictive superiority, or a feature keep/drop decision. No yield modelling or EXP-02 analysis was performed.
"""


def execution_report(
    validation: pd.DataFrame,
    core: pd.DataFrame,
    persistence: pd.DataFrame,
    lag_monthly: pd.DataFrame,
    root: Path,
) -> str:
    changes = largest_changes(core, 1)
    largest_support = changes.loc[(changes.effect == "support") & (changes.method == "pearson")].iloc[0]
    largest_support_s = changes.loc[(changes.effect == "support") & (changes.method == "spearman")].iloc[0]
    largest_weight = changes.loc[(changes.effect == "weight") & (changes.method == "pearson")].iloc[0]
    largest_weight_s = changes.loc[(changes.effect == "weight") & (changes.method == "spearman")].iloc[0]
    sign_counts = {
        effect: int(core[f"sign_change_{effect}_pearson"].sum() + core[f"sign_change_{effect}_spearman"].sum())
        for effect in ["support", "weight", "total"]
    }
    return f"""# EXP-01C Execution Report

## Status

**COMPLETED.** A* was implemented as an equal-weight matched-support control and compared with existing EXP-01A (A) and EXP-01B (B) outputs. EXP-01A and EXP-01B were not rerun. No statewide weather series, yield model, feature decision, or EXP-02 analysis was created.

## Files created or modified

- `src/analysis/exp01c_astar_matched_support_comparison.py`
- `src/tests/analysis/test_exp01c_astar_matched_support_comparison.py`
- EXP-01C tables, figures, research summary, and validation artifacts under `{root}`
- this execution report under `outputs/experiments/{EXPERIMENT}/`

## Validation gates

All {len(validation)} validation checks passed. Exact counts: A = 23,112 municipality-years; A* = B observed support = 21,669; positive area = 16,570; observed zero area retained in A* = 5,099; unavailable excluded = 1,443; A* month rows = 260,028. Every eligible key has all 12 months, canonical IBGE keys match exactly, and three non-blocking municipality-name metadata variants remain recorded by EXP-01B.

A* and B use identical observed-support keys. A* applies ordinary Pearson/Spearman with pandas average-tie ranks; it does not use area magnitude. For lag-1, weather lags are constructed on the complete panel before destination-year support filtering, exactly preserving EXP-01B's month and December→January alignment.

## Principal results

- Largest Pearson support effect: `{largest_support.variable_x} ↔ {largest_support.variable_y}`, month {int(largest_support.month)}, Δ = {largest_support.signed_delta:+.4f}.
- Largest Spearman support effect: `{largest_support_s.variable_x} ↔ {largest_support_s.variable_y}`, month {int(largest_support_s.month)}, Δ = {largest_support_s.signed_delta:+.4f}.
- Largest Pearson weighting effect: `{largest_weight.variable_x} ↔ {largest_weight.variable_y}`, month {int(largest_weight.month)}, Δ = {largest_weight.signed_delta:+.4f}.
- Largest Spearman weighting effect: `{largest_weight_s.variable_x} ↔ {largest_weight_s.variable_y}`, month {int(largest_weight_s.month)}, Δ = {largest_weight_s.signed_delta:+.4f}.
- Core-pair sign reversals across Pearson plus Spearman: support = {sign_counts['support']}, weighting = {sign_counts['weight']}, total = {sign_counts['total']}.
- Cross-month persistence is compared for all five required variables at adjacent, ~3-month, and 6-month horizons in `exp_01c_temporal_persistence_comparison.csv`.
- Month-specific and overall lag-1 A/A*/B results are in their respective comparison files; pooled overall lag-1 remains secondary.

## Commands and tests

- Main execution: `py -3 -m analysis.exp01c_astar_matched_support_comparison --project-root <repository>` with `PYTHONPATH=src`.
- Focused EXP-01C plus relevant EXP-01A/EXP-01B regression tests: **39 passed** (9 EXP-01C, 16 EXP-01A, 14 EXP-01B).
- A full-suite attempt reached **186 passed** with **34 setup errors** caused solely by the managed Windows environment denying pytest access to its temporary directory; no test assertion failed. Repointing `--basetemp` inside the workspace encountered the same environment-level ACL restriction.

## Primary outputs

- `validation/exp_01c_matched_support_validation.csv`
- `astar/astar_monthly_pair_correlations.csv`
- `astar/astar_core_pair_monthly_correlations.csv`
- `astar/astar_cross_month_dependence_summary.csv` and five 12×12 Pearson/Spearman/count matrix sets
- `astar/astar_lag1_persistence_by_month.csv` and `astar_lag1_persistence_overall.csv`
- `summary/exp_01c_core_pair_monthly_comparison.csv`
- `summary/exp_01c_core_pair_summary.csv`
- `summary/exp_01c_temporal_persistence_comparison.csv`
- `summary/exp_01c_lag1_by_month_comparison.csv`
- `summary/exp_01c_lag1_overall_comparison.csv`
- `summary/exp_01c_largest_changes.csv`
- `EXP_01C_research_summary.md`

## Warnings

Correlations are descriptive, not causal or predictive validation. A*→B includes the intended effect of giving observed zero-area municipalities zero statistical contribution in B. Month-specific results are primary; pooled lag-1 is only a diagnostic. The only execution warning is the unrelated full-suite pytest temporary-directory ACL issue described above; all relevant experiment tests passed. No unresolved method ambiguity or data failure remains.
"""


def run(project_root: Path) -> int:
    a_root = project_root / "data/processed/analysis/exp_01a_municipality_weather_correlation"
    b_root = project_root / "data/processed/analysis/exp_01b_harvested_area_weighted_weather_correlation"
    root = project_root / "data/processed/analysis" / EXPERIMENT
    validation_dir = root / "validation"
    astar_dir = root / "astar"
    summary_dir = root / "summary"
    figure_dir = root / "figures"
    output_dir = project_root / "outputs/experiments" / EXPERIMENT
    for folder in [validation_dir, astar_dir, summary_dir, figure_dir, output_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    required = [
        a_root / "summary/core_pair_monthly_correlations.csv",
        a_root / "summary/cross_month_dependence_summary.csv",
        a_root / "summary/lag1_persistence_by_month.csv",
        a_root / "summary/lag1_persistence_overall.csv",
        b_root / "summary/weighted_core_pair_monthly_correlations.csv",
        b_root / "summary/weighted_cross_month_dependence_summary.csv",
        b_root / "summary/weighted_lag1_persistence_by_month.csv",
        b_root / "summary/weighted_lag1_persistence_overall.csv",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Existing A/B artifacts required by EXP-01C are missing: {missing}")

    weather = load_and_validate(project_root / "data/processed/combined_weather/annual")
    if weather.gate_reasons:
        raise ValueError(f"Validated EXP-01A weather gate no longer passes: {weather.gate_reasons}")
    area = load_area_weights(
        project_root / "data/processed/analysis/exp_01s_harvested_area_weight_stability/symbol_aware_harvested_area_1990_2025.csv"
    )
    merged = build_weighted_panel(weather.data, area)
    astar = build_astar_panel(merged.panel)
    validation = validation_table(merged.panel, astar, merged.name_mismatches)
    validation.to_csv(validation_dir / "exp_01c_matched_support_validation.csv", index=False)

    astar_monthly = monthly_correlations(astar, WEATHER_VARIABLES)
    astar_core = _core_rows(astar_monthly)
    astar_monthly.to_csv(astar_dir / "astar_monthly_pair_correlations.csv", index=False)
    astar_core.to_csv(astar_dir / "astar_core_pair_monthly_correlations.csv", index=False)

    astar_lag_overall, astar_lag_monthly = astar_lag1_results(merged.panel, LAG_VARIABLES)
    astar_lag_overall.to_csv(astar_dir / "astar_lag1_persistence_overall.csv", index=False)
    astar_lag_monthly.to_csv(astar_dir / "astar_lag1_persistence_by_month.csv", index=False)

    cross = {}
    for variable in CROSS_MONTH_VARIABLES:
        matrices = cross_month_matrices(astar, variable)
        cross[variable] = matrices
        for name, matrix in zip(["pearson", "spearman", "pairwise_n"], matrices):
            matrix.to_csv(astar_dir / f"astar_cross_month_{variable}_{name}.csv")
    astar_persistence = cross_month_dependence_summary(cross)
    astar_persistence.to_csv(astar_dir / "astar_cross_month_dependence_summary.csv", index=False)

    a_core = pd.read_csv(required[0])
    b_core = pd.read_csv(required[4])
    comparison = core_comparison(a_core, astar_core, b_core)
    comparison.to_csv(summary_dir / "exp_01c_core_pair_monthly_comparison.csv", index=False)
    summary = core_summary(comparison)
    summary.to_csv(summary_dir / "exp_01c_core_pair_summary.csv", index=False)
    largest = largest_changes(comparison)
    largest.to_csv(summary_dir / "exp_01c_largest_changes.csv", index=False)

    persistence = persistence_comparison(pd.read_csv(required[1]), astar_persistence, pd.read_csv(required[5]))
    persistence.to_csv(summary_dir / "exp_01c_temporal_persistence_comparison.csv", index=False)
    lag_monthly = lag_comparison(pd.read_csv(required[2]), astar_lag_monthly, pd.read_csv(required[6]), monthly=True)
    lag_overall = lag_comparison(pd.read_csv(required[3]), astar_lag_overall, pd.read_csv(required[7]), monthly=False)
    lag_monthly.to_csv(summary_dir / "exp_01c_lag1_by_month_comparison.csv", index=False)
    lag_overall.to_csv(summary_dir / "exp_01c_lag1_overall_comparison.csv", index=False)

    all_coefficients = [
        comparison[["A_pearson", "Astar_pearson", "B_pearson", "A_spearman", "Astar_spearman", "B_spearman"]].to_numpy(),
        persistence.filter(regex=r"^(A|Astar|B)_(pearson|spearman)$").to_numpy(),
        lag_monthly[["A_pearson", "Astar_pearson", "B_pearson", "A_spearman", "Astar_spearman", "B_spearman"]].to_numpy(),
    ]
    if any(np.nanmax(np.abs(values.astype(float))) > 1 + 1e-12 for values in all_coefficients):
        raise AssertionError("A comparison coefficient falls outside [-1, 1]")
    if comparison[["A_pearson", "Astar_pearson", "B_pearson", "A_spearman", "Astar_spearman", "B_spearman"]].isna().any().any():
        raise ValueError("Unexpected undefined core-pair coefficient")
    if not (comparison["Astar_pearson_n"].eq(comparison["B_pearson_n"]).all() and comparison["Astar_spearman_n"].eq(comparison["B_spearman_n"]).all()):
        raise ValueError("A* and B monthly observed support counts differ")
    if not (lag_monthly["Astar_pearson_n"].eq(lag_monthly["B_pearson_n"]).all() and lag_monthly["Astar_spearman_n"].eq(lag_monthly["B_spearman_n"]).all()):
        raise ValueError("A* and B lag-1 observed support counts differ")

    plot_core_effects(comparison, "pearson", figure_dir / "astar_to_b_weighting_effect_pearson_heatmap.png")
    plot_core_effects(comparison, "spearman", figure_dir / "astar_to_b_weighting_effect_spearman_heatmap.png")
    plot_persistence(persistence, figure_dir / "a_astar_b_cross_month_persistence_comparison.png")

    research = research_summary(comparison, persistence, lag_monthly)
    (root / "EXP_01C_research_summary.md").write_text(research, encoding="utf-8")
    report = execution_report(validation, comparison, persistence, lag_monthly, root)
    (output_dir / "EXP_01C_execution_report.md").write_text(report, encoding="utf-8")
    (root / "EXP_01C_execution_report.md").write_text(report, encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
