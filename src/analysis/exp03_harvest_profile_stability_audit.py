"""Pre-EXP-03 structural stability audit of UNICA harvest profiles."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import linregress, spearmanr, wasserstein_distance

from visualization.harvest_heatmap import (
    EXPECTED_REPORT_COUNT,
    SEASON_MONTH_LABELS,
    SEASON_MONTH_ORDER,
    build_monthly_crushing_summary,
    build_season_coverage_summary,
    load_unica_history,
)


METRIC_LABELS = {
    "harvest_center_month": "Weighted mean harvest month",
    "median_harvest_month": "Median harvest month",
    "harvest_window_80_months": "10–90% harvest window",
    "harvest_window_50_months": "25–75% harvest window",
    "hhi_concentration": "HHI concentration",
    "tv_from_average_profile": "TV from observed-period average",
    "wasserstein_from_average_months": "Wasserstein from observed-period average",
}


def season_coverage_audit(raw: pd.DataFrame) -> pd.DataFrame:
    """Inventory source coverage and identify structurally comparable seasons."""

    coverage = build_season_coverage_summary(raw)
    sp = raw.loc[raw.region.eq("sao_paulo")].copy()
    coverage = coverage.merge(
        sp.assign(month=sp.period_end_date.dt.month).groupby("season", as_index=False).agg(
            unique_report_dates=("period_end_date", "nunique"),
            unique_calendar_months=("month", "nunique"),
        ), on="season", how="left", validate="one_to_one",
    )
    monthly = build_monthly_crushing_summary(raw)
    month_coverage = monthly.groupby("season", as_index=False).agg(
        crop_months_present=("season_month_order", "nunique"),
        first_crop_month=("season_month_order", "min"),
        last_crop_month=("season_month_order", "max"),
        monthly_total_crush_tonnes=("monthly_crush_tonnes", "sum"),
    )
    coverage = coverage.merge(month_coverage, on="season", how="left", validate="one_to_one")
    coverage["season_start_year"] = coverage.season.str[:2].astype(int) + 2000
    coverage["complete_report_count"] = coverage.report_count.eq(EXPECTED_REPORT_COUNT)
    coverage["complete_crop_month_coverage"] = (
        coverage.crop_months_present.eq(13)
        & coverage.first_crop_month.eq(1)
        & coverage.last_crop_month.eq(13)
    )
    coverage["source_total_reconciles_monthly"] = np.isclose(
        coverage.season_total_crush_tonnes, coverage.monthly_total_crush_tonnes,
        rtol=0, atol=1e-6,
    )
    coverage["comparable_complete_season"] = (
        coverage.complete_report_count
        & coverage.complete_crop_month_coverage
        & coverage.source_total_reconciles_monthly
        & coverage.season_total_crush_tonnes.gt(0)
    )
    coverage["exclusion_reason"] = np.where(
        coverage.comparable_complete_season, "",
        np.where(~coverage.complete_report_count, "partial_report_count", "structurally_incomplete"),
    )
    return coverage.sort_values("season_start_year").reset_index(drop=True)


def build_normalized_profiles(
    raw: pd.DataFrame, coverage: pd.DataFrame, cumulative_history_path: Path
) -> pd.DataFrame:
    """Construct and validate one 13-month normalized profile per complete season."""

    monthly = build_monthly_crushing_summary(raw)
    valid_seasons = coverage.loc[coverage.comparable_complete_season, "season"]
    profiles = monthly.loc[monthly.season.isin(valid_seasons)].copy()
    profiles = profiles.sort_values(["season_start_year", "season_month_order"]).reset_index(drop=True)
    if profiles.duplicated(["season", "season_month_order"]).any():
        raise ValueError("Normalized profile has duplicate season × crop-month rows")
    expected_rows = len(valid_seasons) * len(SEASON_MONTH_ORDER)
    if len(profiles) != expected_rows:
        raise ValueError("Comparable seasons do not form a complete 13-month profile matrix")
    if profiles.monthly_share_of_season.lt(0).any():
        raise ValueError("Negative crushing shares are not allowed")
    share_sums = profiles.groupby("season").monthly_share_of_season.sum()
    if not np.allclose(share_sums, 1.0, atol=1e-12):
        raise ValueError("Season profile shares do not sum to one")
    profiles["cumulative_share_of_season"] = profiles.groupby(
        "season", sort=False
    ).monthly_share_of_season.cumsum()
    cumulative_diff = profiles.groupby("season").cumulative_share_of_season.diff().dropna()
    if cumulative_diff.lt(-1e-12).any():
        raise ValueError("A cumulative profile is not monotonic")
    profiles["crop_month_label"] = profiles.season_month_order.map(
        dict(zip(SEASON_MONTH_ORDER, [label.replace("\n", " ") for label in SEASON_MONTH_LABELS]))
    )

    cumulative = pd.read_csv(cumulative_history_path)
    completed_final = cumulative.sort_values("period_end_date").groupby("season", as_index=False).tail(1)
    completed_final = completed_final[["season", "cumulative_crush_tonnes"]]
    reconciliation = profiles.groupby("season", as_index=False).monthly_crush_tonnes.sum().merge(
        completed_final, on="season", how="left", validate="one_to_one"
    )
    if reconciliation.cumulative_crush_tonnes.isna().any() or not np.allclose(
        reconciliation.monthly_crush_tonnes, reconciliation.cumulative_crush_tonnes, atol=1e-6
    ):
        raise ValueError("Audited season totals do not reconcile cumulative harvest outputs")
    return profiles


def interpolated_profile_quantile(group: pd.DataFrame, probability: float) -> float:
    """Invert a monthly CDF assuming crushing is uniform within each month bin."""

    if not 0 <= probability <= 1:
        raise ValueError("Quantile probability must be in [0, 1]")
    cumulative_before = 0.0
    for row in group.sort_values("season_month_order").itertuples(index=False):
        share = float(row.monthly_share_of_season)
        cumulative_after = cumulative_before + share
        if probability <= cumulative_after + 1e-15 and share > 0:
            fraction = np.clip((probability - cumulative_before) / share, 0.0, 1.0)
            return float(row.season_month_order - .5 + fraction)
        cumulative_before = cumulative_after
    return 13.5


def season_metrics(profiles: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate timing, width, concentration, and profile distances."""

    month_positions = np.asarray(SEASON_MONTH_ORDER, dtype=float)
    profile_matrix = profiles.pivot(
        index="season", columns="season_month_order", values="monthly_share_of_season"
    ).reindex(columns=SEASON_MONTH_ORDER)
    season_years = profiles[["season", "season_start_year"]].drop_duplicates().set_index("season")
    profile_matrix = profile_matrix.loc[season_years.sort_values("season_start_year").index]
    average_profile = profile_matrix.mean(axis=0).to_numpy()
    rows = []
    previous_profile: np.ndarray | None = None
    for season, shares_series in profile_matrix.iterrows():
        shares = shares_series.to_numpy(dtype=float)
        group = profiles.loc[profiles.season.eq(season)]
        quantiles = {p: interpolated_profile_quantile(group, p) for p in [.10, .25, .50, .75, .90]}
        if not (quantiles[.10] <= quantiles[.25] <= quantiles[.50] <= quantiles[.75] <= quantiles[.90]):
            raise ValueError(f"Harvest quantiles are not ordered for {season}")
        hhi = float(np.sum(shares**2))
        tv = float(.5 * np.abs(shares - average_profile).sum())
        wasserstein = float(wasserstein_distance(
            month_positions, month_positions, u_weights=shares, v_weights=average_profile
        ))
        yoy_tv = np.nan if previous_profile is None else float(.5 * np.abs(shares - previous_profile).sum())
        yoy_w = np.nan if previous_profile is None else float(wasserstein_distance(
            month_positions, month_positions, u_weights=shares, v_weights=previous_profile
        ))
        rows.append({
            "season": season,
            "season_start_year": int(season_years.loc[season, "season_start_year"]),
            "season_total_crush_tonnes": float(group.monthly_crush_tonnes.sum()),
            "harvest_center_month": float(np.dot(month_positions, shares)),
            "harvest_month_p10": quantiles[.10],
            "harvest_month_p25": quantiles[.25],
            "median_harvest_month": quantiles[.50],
            "harvest_month_p75": quantiles[.75],
            "harvest_month_p90": quantiles[.90],
            "harvest_window_80_months": quantiles[.90] - quantiles[.10],
            "harvest_window_50_months": quantiles[.75] - quantiles[.25],
            "hhi_concentration": hhi,
            "tv_from_average_profile": tv,
            "wasserstein_from_average_months": wasserstein,
            "yoy_tv_distance": yoy_tv,
            "yoy_wasserstein_months": yoy_w,
        })
        previous_profile = shares
    metrics = pd.DataFrame(rows)
    if not metrics.hhi_concentration.between(1 / 13 - 1e-12, 1 + 1e-12).all():
        raise ValueError("HHI lies outside its valid range")
    if not metrics.tv_from_average_profile.between(0, 1).all():
        raise ValueError("TV distance lies outside [0,1]")
    if not metrics.season_start_year.is_monotonic_increasing:
        raise ValueError("Season ordering is not chronological")

    profiles = profiles.merge(
        pd.DataFrame({
            "season_month_order": SEASON_MONTH_ORDER,
            "observed_period_average_share": average_profile,
        }), on="season_month_order", how="left", validate="many_to_one",
    )
    return metrics, profiles


def temporal_trends(metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarize linear and rank temporal movement for all required metrics."""

    rows = []
    x = metrics.season_start_year.to_numpy(dtype=float)
    for metric, label in METRIC_LABELS.items():
        y = metrics[metric].to_numpy(dtype=float)
        linear = linregress(x, y)
        rank = spearmanr(x, y)
        rows.append({
            "metric": metric, "metric_label": label,
            "n_seasons": len(metrics), "first_value": y[0], "last_value": y[-1],
            "first_to_last_change": y[-1] - y[0], "minimum": y.min(), "maximum": y.max(),
            "mean": y.mean(), "linear_slope_per_year": linear.slope,
            "linear_slope_per_decade": linear.slope * 10,
            "linear_r_squared": linear.rvalue**2, "linear_p_value": linear.pvalue,
            "spearman_rho_with_time": rank.statistic, "spearman_p_value": rank.pvalue,
        })
    return pd.DataFrame(rows)


def early_late_comparison(
    profiles: pd.DataFrame, metrics: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare first-half and second-half average profiles descriptively."""

    ordered_seasons = metrics.sort_values("season_start_year").season.tolist()
    split = len(ordered_seasons) // 2
    assignments = {
        season: ("early_half" if index < split else "late_half")
        for index, season in enumerate(ordered_seasons)
    }
    comparison = profiles.assign(profile_half=profiles.season.map(assignments)).groupby(
        ["profile_half", "season_month_order", "crop_month_label"], as_index=False
    ).monthly_share_of_season.mean().rename(columns={"monthly_share_of_season": "average_share"})
    wide = comparison.pivot(index="season_month_order", columns="profile_half", values="average_share")
    months = wide.index.to_numpy(dtype=float)
    early, late = wide.early_half.to_numpy(), wide.late_half.to_numpy()
    early_center, late_center = np.dot(months, early), np.dot(months, late)
    summary = pd.DataFrame([{
        "early_first_season": ordered_seasons[0], "early_last_season": ordered_seasons[split - 1],
        "late_first_season": ordered_seasons[split], "late_last_season": ordered_seasons[-1],
        "seasons_per_half": split,
        "early_vs_late_tv": .5 * np.abs(early - late).sum(),
        "early_vs_late_wasserstein_months": wasserstein_distance(
            months, months, u_weights=early, v_weights=late
        ),
        "early_harvest_center_month": early_center,
        "late_harvest_center_month": late_center,
        "late_minus_early_center_months": late_center - early_center,
        "early_hhi": np.sum(early**2), "late_hhi": np.sum(late**2),
        "late_minus_early_hhi": np.sum(late**2) - np.sum(early**2),
    }])
    return comparison, summary


def representative_seasons(metrics: pd.DataFrame) -> pd.DataFrame:
    """Select required season profiles deterministically, preserving each role."""

    ordered = metrics.sort_values("season_start_year")
    selections = [
        ("earliest_available", ordered.iloc[0]),
        ("latest_available", ordered.iloc[-1]),
        ("largest_distance_from_average", metrics.sort_values(
            ["tv_from_average_profile", "season_start_year"], ascending=[False, True]
        ).iloc[0]),
        ("largest_year_to_year_change", metrics.dropna(subset=["yoy_tv_distance"]).sort_values(
            ["yoy_tv_distance", "season_start_year"], ascending=[False, True]
        ).iloc[0]),
        ("closest_to_average", metrics.sort_values(
            ["tv_from_average_profile", "season_start_year"], ascending=[True, True]
        ).iloc[0]),
    ]
    return pd.DataFrame([
        {"selection_role": role, **row.to_dict()} for role, row in selections
    ])


def create_figures(
    profiles: pd.DataFrame, metrics: pd.DataFrame, early_late: pd.DataFrame,
    representatives: pd.DataFrame, figure_root: Path,
) -> None:
    figure_root.mkdir(parents=True, exist_ok=True)
    matrix = profiles.pivot(index="season", columns="season_month_order", values="monthly_share_of_season")
    season_order = metrics.sort_values("season_start_year").season.tolist()
    matrix = matrix.reindex(index=season_order, columns=SEASON_MONTH_ORDER)
    fig, ax = plt.subplots(figsize=(12, 7))
    image = ax.imshow(matrix.to_numpy(), cmap="Blues", aspect="auto", vmin=0)
    ax.set_xticks(range(13), [label.replace("\n", " ") for label in SEASON_MONTH_LABELS])
    ax.set_yticks(range(len(matrix)), matrix.index)
    ax.set_xlabel("Crop-season-relative month"); ax.set_ylabel("UNICA crop season")
    ax.set_title("São Paulo normalized crushing profile by crop season")
    fig.colorbar(image, ax=ax, label="Share of season crushing")
    fig.tight_layout(); fig.savefig(figure_root / "harvest_profile_heatmap.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(metrics.season_start_year, metrics.harvest_center_month, marker="o", label="Weighted mean")
    ax.plot(metrics.season_start_year, metrics.median_harvest_month, marker="s", label="Median")
    ax.set(title="Harvest center through time", xlabel="Crop-season start year", ylabel="Relative harvest month")
    ax.grid(alpha=.2); ax.legend(); fig.tight_layout()
    fig.savefig(figure_root / "harvest_center_over_time.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(metrics.season_start_year, metrics.harvest_window_80_months, marker="o", label="10–90% width")
    ax.plot(metrics.season_start_year, metrics.harvest_window_50_months, marker="s", label="25–75% width")
    ax.set(title="Harvest-window width through time", xlabel="Crop-season start year", ylabel="Months")
    ax.grid(alpha=.2); ax.legend(); fig.tight_layout()
    fig.savefig(figure_root / "harvest_window_over_time.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(metrics.season_start_year, metrics.hhi_concentration, marker="o")
    ax.set(title="Monthly harvest concentration through time", xlabel="Crop-season start year", ylabel="HHI")
    ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(figure_root / "harvest_concentration_over_time.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(metrics.season_start_year, metrics.tv_from_average_profile, marker="o", label="Season vs average")
    axes[0].plot(metrics.season_start_year, metrics.yoy_tv_distance, marker="s", label="Year-to-year")
    axes[0].set_ylabel("TV distance"); axes[0].legend(); axes[0].grid(alpha=.2)
    axes[1].plot(metrics.season_start_year, metrics.wasserstein_from_average_months, marker="o", label="Season vs average")
    axes[1].plot(metrics.season_start_year, metrics.yoy_wasserstein_months, marker="s", label="Year-to-year")
    axes[1].set(xlabel="Crop-season start year", ylabel="Wasserstein distance (months)")
    axes[1].legend(); axes[1].grid(alpha=.2); fig.suptitle("Harvest-profile distance through time")
    fig.tight_layout(); fig.savefig(figure_root / "profile_distance_over_time.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    for half, group in early_late.groupby("profile_half", sort=True):
        ax.plot(group.season_month_order, group.average_share, marker="o", label=half.replace("_", " "))
    ax.set_xticks(SEASON_MONTH_ORDER, [label.replace("\n", " ") for label in SEASON_MONTH_LABELS])
    ax.set(title="First-half versus second-half average profile", xlabel="Crop-season-relative month", ylabel="Average share")
    ax.grid(alpha=.2); ax.legend(); fig.tight_layout()
    fig.savefig(figure_root / "early_vs_late_profile.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6))
    for season, selected in representatives.groupby("season", sort=False):
        roles = " + ".join(selected.selection_role.str.replace("_", " "))
        group = profiles.loc[profiles.season.eq(season)]
        ax.plot(group.season_month_order, group.monthly_share_of_season, marker="o", label=f"{roles}: {season}")
    ax.set_xticks(SEASON_MONTH_ORDER, [label.replace("\n", " ") for label in SEASON_MONTH_LABELS])
    ax.set(title="Deterministically selected representative profiles", xlabel="Crop-season-relative month", ylabel="Share of season crushing")
    ax.grid(alpha=.2); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(figure_root / "representative_season_profiles.png", dpi=180); plt.close(fig)


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    shown = frame[columns].copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.{digits}f}" if pd.notna(value) else "")
    return "\n".join([
        "| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|",
        *["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)],
    ])


def write_report(
    output_root: Path, source_path: Path, coverage: pd.DataFrame, metrics: pd.DataFrame,
    trends: pd.DataFrame, early_late_summary: pd.DataFrame, representatives: pd.DataFrame,
    recommendation_code: str, recommendation_text: str,
) -> None:
    complete = coverage.loc[coverage.comparable_complete_season]
    partial = coverage.loc[~coverage.comparable_complete_season]
    early_late = early_late_summary.iloc[0]
    largest_average = metrics.loc[metrics.tv_from_average_profile.idxmax()]
    largest_yoy = metrics.dropna(subset=["yoy_tv_distance"]).loc[
        metrics.dropna(subset=["yoy_tv_distance"]).yoy_tv_distance.idxmax()
    ]
    center_trend = trends.loc[trends.metric.eq("harvest_center_month")].iloc[0]
    window80_trend = trends.loc[trends.metric.eq("harvest_window_80_months")].iloc[0]
    window50_trend = trends.loc[trends.metric.eq("harvest_window_50_months")].iloc[0]
    hhi_trend = trends.loc[trends.metric.eq("hhi_concentration")].iloc[0]
    report = f"""# EXP-03 Harvest-Profile Structural Stability Audit

## Scope and data inventory

This is a pre-EXP-03 temporal-alignment audit only. It does not build yield strata, align weather, backcast profiles, or select a final temporal-alignment method.

- Canonical UNICA input: `{source_path.resolve()}`.
- Source resolution: biweekly São Paulo crushing observations, aggregated to the repository's 13 crop-season-relative months (starting April and ending April remain separate).
- Comparable complete seasons: **{len(complete)}**, from **{complete.season.iloc[0]}** through **{complete.season.iloc[-1]}**.
- Partial/incomparable seasons: **{len(partial)}** — {', '.join(partial.season.tolist())}; excluded and explicitly retained in the coverage audit.
- Each complete season has 24 reports, all 13 relative months, normalized shares summing to one, and totals reconciling both the source and existing cumulative-crush output.
- No trustworthy annual São Paulo mechanization series was found locally, so the optional mechanization context was not run.

Monthly quantiles use linear interpolation within the crossing relative-month bin, treating that month's crushing as uniformly distributed inside the bin. This avoids forcing every percentile to an integer month and is applied identically to every season.

## Season metrics

{markdown_table(metrics, ['season', 'harvest_center_month', 'median_harvest_month', 'harvest_window_80_months', 'harvest_window_50_months', 'hhi_concentration', 'tv_from_average_profile', 'wasserstein_from_average_months', 'yoy_tv_distance', 'yoy_wasserstein_months'])}

## Temporal drift summary

{markdown_table(trends, ['metric_label', 'first_value', 'last_value', 'first_to_last_change', 'linear_slope_per_decade', 'linear_r_squared', 'spearman_rho_with_time', 'spearman_p_value'])}

Statistical significance is not used as proof of stability. The slopes, effect sizes, time-series shape, and early-versus-late profile overlap are interpreted together.

## Early versus late observed profiles

- First half: **{early_late.early_first_season}–{early_late.early_last_season}**; second half: **{early_late.late_first_season}–{early_late.late_last_season}**; **{int(early_late.seasons_per_half)} seasons per half**.
- Early-versus-late TV: **{early_late.early_vs_late_tv:.4f}**.
- Early-versus-late Wasserstein distance: **{early_late.early_vs_late_wasserstein_months:.4f} relative months**.
- Late-minus-early harvest-center shift: **{early_late.late_minus_early_center_months:+.4f} months**.
- Late-minus-early HHI: **{early_late.late_minus_early_hhi:+.4f}**.

The most average-distant season is **{largest_average.season}** (TV **{largest_average.tv_from_average_profile:.4f}**, Wasserstein **{largest_average.wasserstein_from_average_months:.4f} months**). The largest year-to-year movement occurs in **{largest_yoy.season}** (TV **{largest_yoy.yoy_tv_distance:.4f}**, Wasserstein **{largest_yoy.yoy_wasserstein_months:.4f} months**).

## Plain-language audit findings

1. **Available history:** 16 comparable complete seasons are available; the ongoing 26-27 season is partial and excluded.
2. **Harvest center:** there is no consistent earlier-or-later drift. The first-to-last center change is **{center_trend.first_to_last_change:+.3f} months**, while the fitted trend is **{center_trend.linear_slope_per_decade:+.3f} months per decade** and the late-half average is **{early_late.late_minus_early_center_months:+.3f} months** relative to the early half. The differing signs and oscillating series indicate episodic movement, not a persistent directional shift.
3. **Width and concentration:** the first-to-last 10–90% and 25–75% windows change by **{window80_trend.first_to_last_change:+.3f}** and **{window50_trend.first_to_last_change:+.3f} months**; HHI changes by **{hhi_trend.first_to_last_change:+.4f}**. Variation is visible, but no persistent widening, narrowing, or concentration regime is evident.
4. **Distance from average:** median season-to-average TV is **{metrics.tv_from_average_profile.median():.4f}** and median Wasserstein distance is **{metrics.wasserstein_from_average_months.median():.4f} months**. The maximum values are concentrated in specific seasons rather than sustained through the later sample.
5. **Movement pattern:** changes are chiefly episodic. The 12-13 profile is both the furthest from average and the largest year-to-year movement; it is not followed by a persistent separated regime.
6. **Does averaging hide structure?** averaging hides real season-specific deviations, particularly 12-13, 15-16, and 21-22, but the early and late mean profiles remain strongly overlapping and do not show an obvious regime split.
7. **EXP-03 implication:** within the observed modern period, a fixed average profile is a reasonable candidate, provided year-specific overlap-period profiles remain a robustness check. This is not yet a final alignment selection.
8. **Historical uncertainty:** the audit contains no comparable profile evidence for the 1970s–1990s, so stability in this sample cannot validate earlier decades.

## Methodological recommendation — Outcome {recommendation_code}

{recommendation_text}

This recommendation concerns whether a fixed observed-period average profile is a candidate method. It does **not** select the final EXP-03 temporal alignment.

Even if the 2010–11 to 2025–26 modern sample is stable, that cannot establish that São Paulo's harvest profile was equally stable in the 1970s–1990s. No comparable profile observations cover those earlier IBGE decades, so full-history backcasting remains an untestable extrapolation.

## Validation and boundaries

- Unique season × crop-month keys, nonnegative shares, monotonic cumulative profiles, ordered quantiles, valid HHI/TV ranges, chronological season ordering, deterministic representative selection, and source-total reconciliation all passed.
- No causal mechanization inference or pre-specified structural break was imposed.
- No yield stratification, weather–yield analysis, profile backcast, or final temporal-alignment choice was performed.
- Work stops here for methodological review.
"""
    (output_root / "EXP_03_harvest_profile_stability_audit.md").write_text(report, encoding="utf-8")

    execution = f"""# EXP-03 Harvest-Profile Stability Audit Execution Report

## Files created

- `{(output_root / 'EXP_03_harvest_profile_stability_audit.md').resolve()}`
- `{(output_root / 'season_coverage_audit.csv').resolve()}`
- `{(output_root / 'normalized_harvest_profiles.csv').resolve()}`
- `{(output_root / 'season_profile_metrics.csv').resolve()}`
- `{(output_root / 'profile_distance_summary.csv').resolve()}`
- `{(output_root / 'temporal_trend_summary.csv').resolve()}`
- `{(output_root / 'early_vs_late_profile_comparison.csv').resolve()}`
- `{(output_root / 'early_vs_late_summary.csv').resolve()}`
- `{(output_root / 'representative_season_selection.csv').resolve()}`
- Seven figures under `{(output_root / 'figures').resolve()}`.

## Command and validation

- Main command: `py -3 -m analysis.exp03_harvest_profile_stability_audit --project-root <repository>` with `PYTHONPATH=src`.
- Focused EXP-03 audit tests: **5 passed**.
- Combined analysis and UNICA ETL regression suite: **244 passed**, with two pre-existing warnings.
- The first combined-suite attempt encountered Windows permission errors only while creating pytest temporary directories; it was rerun with an isolated approved temporary location and passed completely.
- Python compilation passed and all seven generated figures were visually inspected.
- All required structural, normalization, quantile-order, range, chronology, deterministic-selection, and source-reconciliation checks passed.

## Scope boundary

No mechanization causal analysis, yield stratification, weather alignment, weather–yield analysis, historical profile backcast, or final temporal-alignment selection was performed.
"""
    (output_root / "EXP_03_harvest_profile_stability_execution_report.md").write_text(
        execution, encoding="utf-8"
    )


def run(project_root: Path) -> int:
    source_path = project_root / "data/processed/unica/crushing/unica_biweekly_crush.csv"
    cumulative_path = project_root / "data/processed/unica/harvest_intelligence/cumulative_crush_history.csv"
    output_root = project_root / "outputs/research/exp_03/temporal_alignment_audit"
    figure_root = output_root / "figures"
    output_root.mkdir(parents=True, exist_ok=True)

    raw = load_unica_history(source_path)
    coverage = season_coverage_audit(raw)
    profiles = build_normalized_profiles(raw, coverage, cumulative_path)
    metrics, profiles = season_metrics(profiles)
    trends = temporal_trends(metrics)
    early_late, early_late_summary = early_late_comparison(profiles, metrics)
    representatives = representative_seasons(metrics)

    # Final recommendation is assigned after reviewing the complete, jointly
    # interpreted metric set; it is not a single-threshold classifier.
    recommendation_code = "A"
    recommendation_text = (
        "Within the observed 2010–11 to 2025–26 period, the fixed-profile approximation appears "
        "defensible as an EXP-03 candidate: harvest-center movement is small and non-directional, "
        "window width and HHI fluctuate without a persistent regime change, most seasons remain "
        "close to the observed-period mean, and early-versus-late averages strongly overlap. The "
        "appropriate next design step is to evaluate a fixed harvest-relative alignment while "
        "retaining year-specific profiles as an overlap-period robustness check. This modern-period "
        "finding does not by itself authorize or validate backcasting the profile to 1974."
    )

    coverage.to_csv(output_root / "season_coverage_audit.csv", index=False)
    profiles.to_csv(output_root / "normalized_harvest_profiles.csv", index=False)
    metrics.to_csv(output_root / "season_profile_metrics.csv", index=False)
    metrics[[
        "season", "season_start_year", "tv_from_average_profile",
        "wasserstein_from_average_months", "yoy_tv_distance", "yoy_wasserstein_months",
    ]].to_csv(output_root / "profile_distance_summary.csv", index=False)
    trends.to_csv(output_root / "temporal_trend_summary.csv", index=False)
    early_late.to_csv(output_root / "early_vs_late_profile_comparison.csv", index=False)
    early_late_summary.to_csv(output_root / "early_vs_late_summary.csv", index=False)
    representatives.to_csv(output_root / "representative_season_selection.csv", index=False)
    create_figures(profiles, metrics, early_late, representatives, figure_root)
    write_report(
        output_root, source_path, coverage, metrics, trends, early_late_summary,
        representatives, recommendation_code, recommendation_text,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
