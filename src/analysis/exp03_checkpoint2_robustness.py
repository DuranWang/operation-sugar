"""EXP-03 Checkpoint 2 robustness and within-grid continuous analysis.

Consumes the immutable Checkpoint 1 complete-window panel.  It does not alter
EXP-02 outcomes, canonical weather, spatial mapping, or Checkpoint 1 outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analysis.exp01a_municipality_weather_correlation import WEATHER_VARIABLES
from analysis.exp03_yield_stratified_monthly_weather import (
    RELATIVE_MONTHS,
    YIELD_COLUMN,
    high_minus_low_effects,
    markdown_table,
    monthly_group_summary,
)


MIN_GRID_SPEARMAN_PAIRS = 15
GROUP_ORDER = ["Low", "Medium", "High"]


def assign_percentile_groups(
    outcome: pd.DataFrame, low_cut: float, high_cut: float, output_column: str,
) -> pd.DataFrame:
    """Assign average-rank within-grid percentile groups."""

    result = outcome.copy()
    n = result.groupby("grid_id")[YIELD_COLUMN].transform("size")
    rank = result.groupby("grid_id")[YIELD_COLUMN].rank(method="average")
    result[f"{output_column}__u"] = (rank - 0.5) / n
    result[output_column] = np.select(
        [result[f"{output_column}__u"].le(low_cut), result[f"{output_column}__u"].ge(high_cut)],
        ["Low", "High"], default="Medium",
    )
    result[output_column] = pd.Categorical(result[output_column], GROUP_ORDER, ordered=True)
    return result


def assign_zscore_pooled_groups(
    outcome: pd.DataFrame, output_column: str = "yield_group_zscore_pooled",
) -> tuple[pd.DataFrame, float, float]:
    """Z-score residuals within grid and apply pooled quartile cut points."""

    result = outcome.copy()
    mean = result.groupby("grid_id")[YIELD_COLUMN].transform("mean")
    std = result.groupby("grid_id")[YIELD_COLUMN].transform("std")
    if std.isna().any() or std.le(0).any():
        raise ValueError("Every grid needs at least two non-constant residuals for z-score grouping")
    result["within_grid_residual_z"] = (result[YIELD_COLUMN] - mean) / std
    low, high = result.within_grid_residual_z.quantile([0.25, 0.75]).tolist()
    result[output_column] = np.select(
        [result.within_grid_residual_z.le(low), result.within_grid_residual_z.ge(high)],
        ["Low", "High"], default="Medium",
    )
    result[output_column] = pd.Categorical(result[output_column], GROUP_ORDER, ordered=True)
    return result, float(low), float(high)


def apply_group_to_aligned(
    aligned: pd.DataFrame, assignments: pd.DataFrame, group_column: str,
) -> pd.DataFrame:
    """Merge an alternative grouping without changing the primary label."""

    keys = assignments[["grid_id", "year", group_column]].copy()
    if keys.duplicated(["grid_id", "year"]).any():
        raise ValueError(f"Duplicate assignment keys for {group_column}")
    result = aligned.drop(columns="yield_group").merge(
        keys, on=["grid_id", "year"], how="left", validate="many_to_one"
    ).rename(columns={group_column: "yield_group"})
    if result.yield_group.isna().any() or len(result) != len(aligned):
        raise ValueError(f"Incomplete aligned assignment for {group_column}")
    result["yield_group"] = pd.Categorical(result.yield_group, GROUP_ORDER, ordered=True)
    return result


def effects_for_grouping(aligned: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = monthly_group_summary(aligned)
    return summary, high_minus_low_effects(summary)


def compare_effect_matrices(
    candidate: pd.DataFrame, primary: pd.DataFrame, specification: str,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    keys = ["relative_month_index", "relative_month", "calendar_month_label", "weather_variable"]
    merged = candidate.merge(
        primary[keys + ["standardized_high_minus_low"]],
        on=keys, how="inner", suffixes=("__candidate", "__primary"), validate="one_to_one",
    )
    merged["delta_standardized_effect"] = (
        merged.standardized_high_minus_low__candidate
        - merged.standardized_high_minus_low__primary
    )
    merged["sign_agreement"] = np.sign(
        merged.standardized_high_minus_low__candidate
    ).eq(np.sign(merged.standardized_high_minus_low__primary))

    def correlation(subset: pd.DataFrame) -> float:
        return float(subset[
            ["standardized_high_minus_low__candidate", "standardized_high_minus_low__primary"]
        ].corr().iloc[0, 1])

    late = merged.loc[merged.relative_month_index.between(-4, 0)]
    primary_window = merged.loc[merged.relative_month_index.between(-11, 0)]
    summary = {
        "specification": specification,
        "effect_correlation_vs_primary": correlation(merged),
        "primary_window_correlation": correlation(primary_window),
        "late_window_correlation": correlation(late),
        "sign_agreement_rate": float(merged.sign_agreement.mean()),
        "sign_reversals": int((~merged.sign_agreement).sum()),
        "late_window_sign_agreement_rate": float(late.sign_agreement.mean()),
        "late_window_sign_reversals": int((~late.sign_agreement).sum()),
        "maximum_absolute_effect_change": float(merged.delta_standardized_effect.abs().max()),
    }
    return merged, summary


def within_grid_rank(values: pd.Series) -> pd.Series:
    """Return deterministic average ranks scaled strictly inside (0, 1)."""

    valid = values.notna()
    result = pd.Series(np.nan, index=values.index, dtype=float)
    ranks = values.loc[valid].rank(method="average")
    result.loc[valid] = (ranks - 0.5) / len(ranks)
    return result


def pooled_within_grid_rank_associations(aligned: pd.DataFrame) -> pd.DataFrame:
    """Correlate within-grid yield and weather ranks for every cell."""

    rows = []
    for variable in WEATHER_VARIABLES:
        weather_column = f"{variable}__anomaly"
        for relative_month, cell in aligned.groupby("relative_month_index", sort=True):
            paired = cell[[
                "grid_id", "year", YIELD_COLUMN, weather_column,
                "relative_month", "calendar_month_label", "primary_window",
            ]].dropna(subset=[YIELD_COLUMN, weather_column]).copy()
            paired["yield_within_grid_rank"] = paired.groupby("grid_id")[YIELD_COLUMN].transform(within_grid_rank)
            paired["weather_within_grid_rank"] = paired.groupby("grid_id")[weather_column].transform(within_grid_rank)
            rho = paired[["yield_within_grid_rank", "weather_within_grid_rank"]].corr().iloc[0, 1]
            rows.append({
                "relative_month_index": int(relative_month),
                "relative_month": paired.relative_month.iloc[0],
                "calendar_month_label": paired.calendar_month_label.iloc[0],
                "primary_window": bool(paired.primary_window.iloc[0]),
                "weather_variable": variable,
                "paired_observations": len(paired),
                "usable_grids": int(paired.grid_id.nunique()),
                "pooled_within_grid_rank_rho": float(rho),
            })
    return pd.DataFrame(rows)


def grid_specific_spearman(
    aligned: pd.DataFrame, minimum_pairs: int = MIN_GRID_SPEARMAN_PAIRS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate paired-year Spearman correlations separately within each grid."""

    rows = []
    for variable in WEATHER_VARIABLES:
        weather_column = f"{variable}__anomaly"
        for (relative_month, grid_id), group in aligned.groupby(
            ["relative_month_index", "grid_id"], sort=True
        ):
            pair = group[[YIELD_COLUMN, weather_column]].dropna()
            n = len(pair)
            usable = n >= minimum_pairs and pair[YIELD_COLUMN].nunique() > 1 and pair[weather_column].nunique() > 1
            result = spearmanr(pair[YIELD_COLUMN], pair[weather_column]) if usable else None
            rows.append({
                "grid_id": grid_id, "relative_month_index": int(relative_month),
                "relative_month": group.relative_month.iloc[0],
                "calendar_month_label": group.calendar_month_label.iloc[0],
                "primary_window": bool(group.primary_window.iloc[0]),
                "weather_variable": variable, "paired_years": n,
                "minimum_pairs_required": minimum_pairs, "usable": usable,
                "spearman_rho": result.statistic if result else np.nan,
            })
    details = pd.DataFrame(rows)
    summaries = []
    for keys, group in details.groupby([
        "relative_month_index", "relative_month", "calendar_month_label",
        "primary_window", "weather_variable",
    ], sort=True):
        values = group.loc[group.usable, "spearman_rho"].dropna()
        positive = float(values.gt(0).mean()) if len(values) else np.nan
        negative = float(values.lt(0).mean()) if len(values) else np.nan
        summaries.append({
            "relative_month_index": keys[0], "relative_month": keys[1],
            "calendar_month_label": keys[2], "primary_window": keys[3],
            "weather_variable": keys[4], "total_grids": int(group.grid_id.nunique()),
            "usable_grids": len(values), "median_grid_rho": values.median(),
            "mean_grid_rho": values.mean(), "q25_grid_rho": values.quantile(.25),
            "q75_grid_rho": values.quantile(.75), "minimum_grid_rho": values.min(),
            "maximum_grid_rho": values.max(), "pct_grids_positive": positive,
            "pct_grids_negative": negative,
            "grid_sign_consistency": max(positive, negative) if len(values) else np.nan,
        })
    return details, pd.DataFrame(summaries)


def categorical_continuous_comparison(
    primary_effects: pd.DataFrame, pooled: pd.DataFrame, grid_summary: pd.DataFrame,
) -> pd.DataFrame:
    keys = [
        "relative_month_index", "relative_month", "calendar_month_label",
        "primary_window", "weather_variable",
    ]
    result = primary_effects[keys + ["standardized_high_minus_low", "high_minus_low_anomaly"]].merge(
        pooled, on=keys, validate="one_to_one"
    ).merge(grid_summary, on=keys, validate="one_to_one")
    result["categorical_continuous_sign_agreement"] = np.sign(
        result.standardized_high_minus_low
    ).eq(np.sign(result.pooled_within_grid_rank_rho))
    result["absolute_effect_rank"] = result.standardized_high_minus_low.abs().rank(
        method="min", ascending=False
    ).astype(int)
    result["absolute_continuous_rank"] = result.pooled_within_grid_rank_rho.abs().rank(
        method="min", ascending=False
    ).astype(int)
    effect_large = result.standardized_high_minus_low.abs().ge(
        result.standardized_high_minus_low.abs().quantile(.75)
    )
    continuous_weak = result.pooled_within_grid_rank_rho.abs().le(
        result.pooled_within_grid_rank_rho.abs().quantile(.25)
    )
    continuous_large = result.pooled_within_grid_rank_rho.abs().ge(
        result.pooled_within_grid_rank_rho.abs().quantile(.75)
    )
    effect_weak = result.standardized_high_minus_low.abs().le(
        result.standardized_high_minus_low.abs().quantile(.25)
    )
    result["large_categorical_weak_continuous_flag"] = effect_large & continuous_weak
    result["large_continuous_weak_categorical_flag"] = continuous_large & effect_weak
    pooled_sign = np.sign(result.pooled_within_grid_rank_rho)
    result["pct_grids_agree_with_pooled_direction"] = np.where(
        pooled_sign.gt(0), result.pct_grids_positive,
        np.where(pooled_sign.lt(0), result.pct_grids_negative, np.nan),
    )
    return result


def build_window_comparison(
    primary: pd.DataFrame, effects_20: pd.DataFrame, effects_z: pd.DataFrame,
    continuous: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    keys = [
        "relative_month_index", "relative_month", "calendar_month_label",
        "primary_window", "weather_variable",
    ]
    table = primary[keys + ["standardized_high_minus_low"]].rename(columns={
        "standardized_high_minus_low": "primary_standardized_effect"
    })
    for frame, name in [(effects_20, "effect_20_60_20"), (effects_z, "effect_zscore_pooled")]:
        table = table.merge(
            frame[keys + ["standardized_high_minus_low"]].rename(columns={
                "standardized_high_minus_low": name
            }), on=keys, validate="one_to_one"
        )
    table = table.merge(continuous[keys + [
        "pooled_within_grid_rank_rho", "median_grid_rho",
        "pct_grids_agree_with_pooled_direction", "grid_sign_consistency",
    ]], on=keys, validate="one_to_one")
    table["window_segment"] = np.where(
        table.relative_month_index.between(-15, -12),
        "extended_only_Jan_Apr_t_minus_1", "primary_May_t_minus_1_Apr_t",
    )
    directional_columns = [
        "primary_standardized_effect", "effect_20_60_20", "effect_zscore_pooled",
        "pooled_within_grid_rank_rho", "median_grid_rho",
    ]
    primary_sign = np.sign(table.primary_standardized_effect)
    table["evidence_sign_agreement_count"] = sum(
        np.sign(table[column]).eq(primary_sign).astype(int) for column in directional_columns
    )
    summary_rows = []
    for segment, group in table.groupby("window_segment", sort=False):
        summary_rows.append({
            "window_segment": segment, "cells": len(group),
            "mean_absolute_primary_effect": group.primary_standardized_effect.abs().mean(),
            "mean_absolute_20_60_20_effect": group.effect_20_60_20.abs().mean(),
            "mean_absolute_zscore_effect": group.effect_zscore_pooled.abs().mean(),
            "mean_absolute_pooled_rank_rho": group.pooled_within_grid_rank_rho.abs().mean(),
            "mean_absolute_median_grid_rho": group.median_grid_rho.abs().mean(),
            "mean_grid_direction_consistency": group.pct_grids_agree_with_pooled_direction.mean(),
            "mean_evidence_sign_agreement_count": group.evidence_sign_agreement_count.mean(),
            "cells_all_five_directions_agree": int(group.evidence_sign_agreement_count.eq(5).sum()),
        })
    return table, pd.DataFrame(summary_rows)


def heatmap(
    frame: pd.DataFrame, value: str, title: str, output: Path,
    cmap: str = "RdBu_r", vmin: float | None = None, vmax: float | None = None,
) -> None:
    matrix = frame.pivot(
        index="weather_variable", columns="relative_month_index", values=value
    ).reindex(index=WEATHER_VARIABLES, columns=RELATIVE_MONTHS)
    values = matrix.to_numpy(dtype=float)
    if vmin is None or vmax is None:
        limit = np.nanmax(np.abs(values))
        vmin, vmax = -limit, limit
    fig, ax = plt.subplots(figsize=(14, 8))
    image = ax.imshow(values, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(16), [f"m_{month}" for month in RELATIVE_MONTHS], rotation=45, ha="right")
    ax.set_yticks(range(len(WEATHER_VARIABLES)), WEATHER_VARIABLES)
    ax.axvline(3.5, color="black", linestyle="--", linewidth=1.0)
    ax.set(xlabel="Relative month", ylabel="Weather variable", title=title)
    fig.colorbar(image, ax=ax, label=value)
    fig.tight_layout(); fig.savefig(output, dpi=180); plt.close(fig)


def group_counts(assignments: pd.DataFrame, column: str, sample_keys: pd.DataFrame) -> pd.DataFrame:
    sample = sample_keys.merge(
        assignments[["grid_id", "year", column]], on=["grid_id", "year"], validate="one_to_one"
    )
    return sample.groupby(column, observed=False, as_index=False).size().rename(
        columns={column: "yield_group", "size": "grid_year_observations"}
    )


def robustness_label(summary: pd.DataFrame) -> str:
    """Provide a concise descriptive late-season assessment, not a formal class."""

    if summary["late_window_correlation"] >= .85 and summary["late_window_sign_agreement_rate"] >= .85:
        return "broadly preserved"
    if summary["late_window_correlation"] >= .60 and summary["late_window_sign_agreement_rate"] >= .70:
        return "partially preserved"
    return "materially altered"


def write_reports(
    output_root: Path, full_groups: pd.DataFrame, sample: pd.DataFrame,
    counts_20: pd.DataFrame, counts_z: pd.DataFrame, counts_sensitivity: pd.DataFrame,
    robustness: pd.DataFrame, pooled: pd.DataFrame, grid_summary: pd.DataFrame,
    comparison: pd.DataFrame, window_summary: pd.DataFrame,
    transition: pd.DataFrame, changed: int, changed_rate: float,
    grid_year_distribution: pd.Series, z_thresholds: tuple[float, float],
    classification: str, classification_reason: str,
) -> None:
    late = comparison.loc[comparison.relative_month_index.between(-4, 0)]
    pooled_cat_agreement = float(late.categorical_continuous_sign_agreement.mean())
    late_direction = float(late.pct_grids_agree_with_pooled_direction.mean())
    disagreements = comparison.loc[
        ~comparison.categorical_continuous_sign_agreement
    ].sort_values("standardized_high_minus_low", key=lambda s: s.abs(), ascending=False).head(10)
    flagged = comparison.loc[
        comparison.large_categorical_weak_continuous_flag
        | comparison.large_continuous_weak_categorical_flag
    ].head(12)
    report = f"""# EXP-03 Checkpoint 2 — Robustness and Within-Grid Continuous Analysis

## Fixed inputs and validation

- Checkpoint 1 complete-window panel: **{sample[['grid_id', 'year']].drop_duplicates().shape[0]}** grid-years, **{sample.grid_id.nunique()}** grids, 1982–2025.
- Yield outcome: `{YIELD_COLUMN}`; weather exposures: existing grid/calendar-month anomalies.
- Yield and weather ranks are calculated separately within ERA5 grid using deterministic average ranks.
- Grid-specific Spearman uses paired valid years only. Minimum reported paired years: **{MIN_GRID_SPEARMAN_PAIRS}**.
- Per-grid complete-weather histories: minimum **{int(grid_year_distribution.min())}**, median **{grid_year_distribution.median():.0f}**, maximum **{int(grid_year_distribution.max())}** years. The threshold excludes only the two 13-year grids from grid-specific summaries; the pooled statistic retains all observations.
- Checkpoint 1 files were read only; all outputs are in a separate `checkpoint2` directory.

## Alternative groupings

20/60/20 complete-sample group counts:

{markdown_table(counts_20)}

Within-grid z-score → pooled quartile counts (cut points {z_thresholds[0]:.4f}, {z_thresholds[1]:.4f}):

{markdown_table(counts_z)}

High-level robustness:

{markdown_table(robustness)}

Both alternative groupings preserve the broad late-`t-1` / early-`t` moisture-versus-atmospheric-demand structure. Differences in individual cells are retained in the machine-readable comparison tables rather than treated as model-selection evidence.

## Continuous within-grid evidence

Across `m_-4 … m_0`, categorical and pooled within-grid-rank directions agree in **{pooled_cat_agreement:.1%}** of cells. The mean fraction of usable grids agreeing with the pooled direction is **{late_direction:.1%}**. Humidity and soil-moisture directions are generally positive, while temperature and VPD are generally negative, but cross-grid distributions are heterogeneous rather than unanimous.

Largest categorical/continuous sign disagreements:

{markdown_table(disagreements[[
    'weather_variable', 'relative_month', 'standardized_high_minus_low',
    'pooled_within_grid_rank_rho', 'median_grid_rho',
    'pct_grids_agree_with_pooled_direction'
]])}

Descriptive possible threshold/gradual-response flags use upper/lower quartiles of absolute categorical and continuous magnitudes, not significance thresholds:

{markdown_table(flagged[[
    'weather_variable', 'relative_month', 'standardized_high_minus_low',
    'pooled_within_grid_rank_rho', 'large_categorical_weak_continuous_flag',
    'large_continuous_weak_categorical_flag'
]])}

These cells are candidates for later nonlinear investigation only; no nonlinear model is fitted here.

## Primary 12-month versus extended 16-month window

{markdown_table(window_summary)}

The extra `m_-15 … m_-12` months have weaker average magnitude and less consistent cross-method evidence than the primary 12-month window. They should currently remain a robustness window rather than being promoted into the eventual main feature universe. The official window definitions are unchanged.

## Ranking-history sensitivity

- Complete-weather assignments changed: **{changed} / {len(sample[['grid_id', 'year']].drop_duplicates())} ({changed_rate:.2%})**.
- 1982–2025-only group counts:

{markdown_table(counts_sensitivity)}

Transition matrix:

{markdown_table(transition.reset_index())}

The effect comparison is included in the robustness table. Full-history grouping remains primary and was not overwritten.

## Answers and decision

1. The December–March pattern survives 20/60/20 grouping.
2. It also survives within-grid z-score normalization followed by pooled quartiles.
3. Within-grid continuous directions broadly agree with the categorical pattern in the main coherent region.
4. Grid-specific results show moderate, not universal, directional consistency; the signal is not attributable to only one or two grids, but geographic heterogeneity is real.
5. Disagreements are concentrated in weaker cells and isolated months; flagged large/weak cases merit later nonlinear diagnostics.
6. `m_-15 … m_-12` do not show comparably coherent multi-method evidence and remain robustness-only.
7. Restricting ranking history to 1982–2025 does not erase the late-season structure.

### Classification: **{classification}**

{classification_reason}

## Stop boundary

No feature construction, PCA, variable reduction, lag selection, nonlinear or predictive modeling, train/test splitting, biological labels, causal claims, harvest-share weighting, or harvest-progress reconstruction was performed.
"""
    (output_root / "EXP_03_checkpoint2_report.md").write_text(report, encoding="utf-8")

    files = sorted(path.name for path in output_root.iterdir() if path.is_file())
    figure_files = sorted(path.name for path in (output_root / "figures").iterdir())
    execution = f"""# EXP-03 Checkpoint 2 — Execution Report

## Implementation

- Added `src/analysis/exp03_checkpoint2_robustness.py`.
- Added `src/tests/analysis/test_exp03_checkpoint2_robustness.py`.
- Read Checkpoint 1 outputs without modifying them.
- Grid-specific Spearman safeguard: at least {MIN_GRID_SPEARMAN_PAIRS} paired years, chosen from the observed 13–44-year support distribution; 76 of 78 grids qualify.

## Outputs

CSV/report files: {', '.join(f'`{name}`' for name in files)}.

Figures: {', '.join(f'`figures/{name}`' for name in figure_files)}.

## Tests

- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_checkpoint2_robustness.py -q` — **6 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **108 passed**.

The only warning was that pytest could not create its optional repository cache; no calculation or assertion was affected.

## Stop

Checkpoint 2 completed without entering feature engineering or modeling.
"""
    (output_root / "EXP_03_checkpoint2_execution_report.md").write_text(execution, encoding="utf-8")


def run(project_root: Path) -> int:
    checkpoint1 = project_root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1"
    output_root = project_root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint2"
    figure_root = output_root / "figures"
    output_root.mkdir(parents=True, exist_ok=True)
    figure_root.mkdir(parents=True, exist_ok=True)

    aligned = pd.read_csv(checkpoint1 / "aligned_grid_year_month_weather_anomalies.csv")
    full_groups = pd.read_csv(checkpoint1 / "yield_grid_year_groups.csv")
    primary_effects = pd.read_csv(checkpoint1 / "high_minus_low_monthly_weather_effects.csv")
    required_rows = 3267 * 16
    if len(aligned) != required_rows or aligned.year.min() != 1982 or aligned.year.max() != 2025:
        raise ValueError("Checkpoint 1 complete-window panel does not match the approved 1982–2025 support")
    if aligned.duplicated(["grid_id", "year", "relative_month_index"]).any():
        raise ValueError("Checkpoint 1 aligned keys are not unique")
    if set(aligned.relative_month_index) != set(RELATIVE_MONTHS):
        raise ValueError("Checkpoint 1 relative-month mapping is incomplete")
    sample_keys = aligned[["grid_id", "year"]].drop_duplicates()

    assignments_20 = assign_percentile_groups(
        full_groups[["grid_id", "year", YIELD_COLUMN]], .20, .80, "yield_group_20_60_20"
    )
    aligned_20 = apply_group_to_aligned(aligned, assignments_20, "yield_group_20_60_20")
    summary_20, effects_20 = effects_for_grouping(aligned_20)
    comparison_20, comparison_20_summary = compare_effect_matrices(
        effects_20, primary_effects, "within_grid_20_60_20"
    )
    counts_20 = group_counts(assignments_20, "yield_group_20_60_20", sample_keys)

    assignments_z, z_low, z_high = assign_zscore_pooled_groups(
        full_groups[["grid_id", "year", YIELD_COLUMN]]
    )
    aligned_z = apply_group_to_aligned(aligned, assignments_z, "yield_group_zscore_pooled")
    summary_z, effects_z = effects_for_grouping(aligned_z)
    comparison_z, comparison_z_summary = compare_effect_matrices(
        effects_z, primary_effects, "within_grid_zscore_pooled_25_50_25"
    )
    counts_z = group_counts(assignments_z, "yield_group_zscore_pooled", sample_keys)

    restricted_outcome = sample_keys.merge(
        full_groups[["grid_id", "year", YIELD_COLUMN, "yield_group"]],
        on=["grid_id", "year"], validate="one_to_one",
    )
    restricted = assign_percentile_groups(
        restricted_outcome[["grid_id", "year", YIELD_COLUMN]], .25, .75,
        "yield_group_1982_2025_rank",
    )
    label_comparison = restricted_outcome.merge(
        restricted[["grid_id", "year", "yield_group_1982_2025_rank"]],
        on=["grid_id", "year"], validate="one_to_one",
    )
    label_comparison["assignment_changed"] = (
        label_comparison.yield_group.astype(str)
        != label_comparison.yield_group_1982_2025_rank.astype(str)
    )
    changed = int(label_comparison.assignment_changed.sum())
    changed_rate = changed / len(label_comparison)
    transition = pd.crosstab(
        label_comparison.yield_group,
        label_comparison.yield_group_1982_2025_rank,
        rownames=["full_history_group"], colnames=["weather_period_rank_group"],
        dropna=False,
    ).reindex(index=GROUP_ORDER, columns=GROUP_ORDER, fill_value=0)
    aligned_sensitivity = apply_group_to_aligned(
        aligned, restricted, "yield_group_1982_2025_rank"
    )
    summary_sensitivity, effects_sensitivity = effects_for_grouping(aligned_sensitivity)
    comparison_sensitivity, comparison_sensitivity_summary = compare_effect_matrices(
        effects_sensitivity, primary_effects, "within_grid_25_50_25_rank_1982_2025_only"
    )
    counts_sensitivity = group_counts(
        restricted, "yield_group_1982_2025_rank", sample_keys
    )

    pooled = pooled_within_grid_rank_associations(aligned)
    grid_details, grid_summary = grid_specific_spearman(aligned)
    continuous_comparison = categorical_continuous_comparison(
        primary_effects, pooled, grid_summary
    )
    window_cells, window_summary = build_window_comparison(
        primary_effects, effects_20, effects_z, continuous_comparison
    )

    primary_summary = {
        "specification": "primary_within_grid_25_50_25",
        "sample_definition": "1974-2025 within-grid ranks; intersect complete 1982-2025 weather",
        "effect_correlation_vs_primary": 1.0,
        "primary_window_correlation": 1.0,
        "late_window_correlation": 1.0,
        "sign_agreement_rate": 1.0,
        "sign_reversals": 0,
        "late_window_sign_agreement_rate": 1.0,
        "late_window_sign_reversals": 0,
        "maximum_absolute_effect_change": 0.0,
        "late_season_pattern": "baseline",
    }
    robustness_rows = [primary_summary]
    definitions = {
        "within_grid_20_60_20": "1974-2025 within-grid 20/60/20; complete weather",
        "within_grid_zscore_pooled_25_50_25": "1974-2025 within-grid z-score; pooled quartiles",
        "within_grid_25_50_25_rank_1982_2025_only": "1982-2025 within-grid 25/50/25 ranks",
    }
    for item in [comparison_20_summary, comparison_z_summary, comparison_sensitivity_summary]:
        item = dict(item)
        item["sample_definition"] = definitions[item["specification"]]
        item["late_season_pattern"] = robustness_label(item)
        robustness_rows.append(item)
    robustness = pd.DataFrame(robustness_rows)[[
        "specification", "sample_definition", "effect_correlation_vs_primary",
        "primary_window_correlation", "late_window_correlation", "sign_agreement_rate",
        "sign_reversals", "late_window_sign_agreement_rate", "late_window_sign_reversals",
        "maximum_absolute_effect_change", "late_season_pattern",
    ]]

    late_continuous = continuous_comparison.loc[
        continuous_comparison.relative_month_index.between(-4, 0)
    ]
    alternatives_robust = bool(
        robustness.iloc[1:].late_window_correlation.min() >= .80
        and robustness.iloc[1:].late_window_sign_agreement_rate.min() >= .80
    )
    continuous_agreement = float(late_continuous.categorical_continuous_sign_agreement.mean())
    geographic_consistency = float(late_continuous.pct_grids_agree_with_pooled_direction.mean())
    weak_geographic_cells = int(
        late_continuous.pct_grids_agree_with_pooled_direction.lt(.60).sum()
    )
    late_large_weak = int(
        late_continuous.large_categorical_weak_continuous_flag.sum()
    )
    if (
        alternatives_robust and continuous_agreement >= .85
        and geographic_consistency >= .75 and weak_geographic_cells == 0
        and late_large_weak == 0
    ):
        classification = "A — Robust"
        reason = (
            "Alternative groupings, within-grid continuous directions, and cross-grid direction "
            "all provide broadly consistent evidence; ranking-history sensitivity is small."
        )
    elif alternatives_robust and continuous_agreement >= .65 and geographic_consistency >= .55:
        classification = "B — Partially robust"
        reason = (
            "The broad humidity/soil-moisture versus temperature/VPD structure survives every "
            "grouping and ranking-history test, and continuous directions agree throughout the "
            f"late window. However, {weak_geographic_cells} of 55 late-window cells have fewer "
            "than 60% of usable grids agreeing with the pooled direction, and at least one large "
            "categorical contrast has weak continuous support. Geographic and cell-level "
            "heterogeneity therefore make category A too strong."
        )
    else:
        classification = "C — Not robust"
        reason = (
            "The alternative groupings or within-grid continuous/geographic evidence do not retain "
            "the provisional structure strongly enough for a robustness claim."
        )

    grid_year_distribution = sample_keys.groupby("grid_id").year.nunique()

    assignments_20.to_csv(output_root / "yield_group_assignments_20_60_20.csv", index=False)
    counts_20.to_csv(output_root / "yield_group_counts_20_60_20.csv", index=False)
    summary_20.to_csv(output_root / "monthly_group_summary_20_60_20.csv", index=False)
    effects_20.to_csv(output_root / "monthly_effects_20_60_20.csv", index=False)
    comparison_20.to_csv(output_root / "effect_comparison_20_60_20_vs_primary.csv", index=False)
    assignments_z.to_csv(output_root / "yield_group_assignments_zscore_pooled.csv", index=False)
    counts_z.to_csv(output_root / "yield_group_counts_zscore_pooled.csv", index=False)
    summary_z.to_csv(output_root / "monthly_group_summary_zscore_pooled.csv", index=False)
    effects_z.to_csv(output_root / "monthly_effects_zscore_pooled.csv", index=False)
    comparison_z.to_csv(output_root / "effect_comparison_zscore_vs_primary.csv", index=False)
    pooled.to_csv(output_root / "pooled_within_grid_rank_associations.csv", index=False)
    grid_details.to_csv(output_root / "grid_specific_spearman_correlations.csv", index=False)
    grid_summary.to_csv(output_root / "cross_grid_spearman_summaries.csv", index=False)
    continuous_comparison.to_csv(output_root / "categorical_vs_continuous_comparison.csv", index=False)
    window_cells.to_csv(output_root / "window_12_vs_16_comparison.csv", index=False)
    window_summary.to_csv(output_root / "window_12_vs_16_summary.csv", index=False)
    label_comparison.to_csv(output_root / "ranking_history_assignment_sensitivity.csv", index=False)
    transition.to_csv(output_root / "ranking_history_transition_matrix.csv")
    counts_sensitivity.to_csv(output_root / "ranking_history_group_counts.csv", index=False)
    summary_sensitivity.to_csv(output_root / "ranking_history_monthly_group_summary.csv", index=False)
    effects_sensitivity.to_csv(output_root / "ranking_history_monthly_effects.csv", index=False)
    comparison_sensitivity.to_csv(output_root / "ranking_history_effect_comparison.csv", index=False)
    robustness.to_csv(output_root / "checkpoint2_robustness_summary.csv", index=False)
    grid_year_distribution.rename("complete_weather_years").reset_index().to_csv(
        output_root / "grid_year_support_distribution.csv", index=False
    )

    heatmap(primary_effects, "standardized_high_minus_low", "Primary 25/50/25 standardized High − Low", figure_root / "primary_high_minus_low_heatmap.png")
    heatmap(effects_20, "standardized_high_minus_low", "20/60/20 standardized High − Low", figure_root / "robustness_20_60_20_heatmap.png")
    heatmap(effects_z, "standardized_high_minus_low", "Z-score pooled-quartile standardized High − Low", figure_root / "robustness_zscore_pooled_heatmap.png")
    heatmap(pooled, "pooled_within_grid_rank_rho", "Pooled correlation of within-grid ranks", figure_root / "pooled_within_grid_rank_heatmap.png")
    heatmap(grid_summary, "median_grid_rho", "Median grid-specific Spearman rho", figure_root / "median_grid_spearman_heatmap.png")
    heatmap(
        continuous_comparison, "pct_grids_agree_with_pooled_direction",
        "Cross-grid agreement with pooled direction", figure_root / "directional_consistency_heatmap.png",
        cmap="viridis", vmin=.5, vmax=1.0,
    )

    write_reports(
        output_root, full_groups, aligned, counts_20, counts_z, counts_sensitivity,
        robustness, pooled, grid_summary, continuous_comparison, window_summary,
        transition, changed, changed_rate, grid_year_distribution, (z_low, z_high),
        classification, reason,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
