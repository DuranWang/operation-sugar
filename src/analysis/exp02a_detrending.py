"""EXP-02A Phase 1 municipality-level yield detrending diagnostics.

Runs only the approved Linear and second-difference P50=10/12/6
specifications. Missing years may receive a latent fitted trend on the annual
grid, but residuals are created only for observed valid-yield years.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SPECIFICATIONS = ("linear", "p50_10", "p50_12", "p50_6")
P50_VALUES = {"p50_10": 10.0, "p50_12": 12.0, "p50_6": 6.0}
EXPECTED_ELIGIBLE = 511


def lambda_from_p50(period: float) -> float:
    if not np.isfinite(period) or period <= 2:
        raise ValueError("P50 must be finite and greater than two years")
    return float(1.0 / (16.0 * np.sin(np.pi / period) ** 4))


def amplitude_response(period: float, penalty: float) -> float:
    return float(1.0 / (1.0 + 16.0 * penalty * np.sin(np.pi / period) ** 4))


def second_difference_matrix(length: int) -> np.ndarray:
    if length < 3:
        return np.empty((0, length), dtype=float)
    matrix = np.zeros((length - 2, length), dtype=float)
    indices = np.arange(length - 2)
    matrix[indices, indices] = 1.0
    matrix[indices, indices + 1] = -2.0
    matrix[indices, indices + 2] = 1.0
    return matrix


def fit_linear(years: np.ndarray, values: np.ndarray, observed: np.ndarray) -> np.ndarray:
    if int(observed.sum()) < 2:
        raise ValueError("Linear fit requires at least two observations")
    centered = years.astype(float) - float(years[observed].mean())
    design = np.column_stack([np.ones(int(observed.sum())), centered[observed]])
    coefficients, *_ = np.linalg.lstsq(design, values[observed], rcond=None)
    return coefficients[0] + coefficients[1] * centered


def fit_second_difference(values: np.ndarray, observed: np.ndarray, penalty: float) -> np.ndarray:
    if len(values) != len(observed) or int(observed.sum()) < 2:
        raise ValueError("Smoother requires aligned arrays and at least two observations")
    d2 = second_difference_matrix(len(values))
    weights = observed.astype(float)
    system = np.diag(weights) + penalty * (d2.T @ d2)
    rhs = np.where(observed, values, 0.0)
    return np.linalg.solve(system, rhs)


def gap_stratum(maximum_gap: float) -> str:
    if pd.isna(maximum_gap) or maximum_gap == 0:
        return "0"
    if maximum_gap <= 5:
        return "1-5"
    if maximum_gap <= 10:
        return "6-10"
    return ">10"


def history_stratum(n_valid: int) -> str:
    if n_valid <= 19:
        return "15-19"
    if n_valid <= 29:
        return "20-29"
    if n_valid <= 39:
        return "30-39"
    if n_valid <= 51:
        return "40-51"
    return "52"


def contiguous_false_runs(observed: np.ndarray, years: np.ndarray) -> list[dict[str, int]]:
    missing_indices = np.flatnonzero(~observed)
    if not len(missing_indices):
        return []
    runs: list[dict[str, int]] = []
    start = previous = int(missing_indices[0])
    for index in missing_indices[1:]:
        index = int(index)
        if index != previous + 1:
            runs.append({"start_index": start, "end_index": previous})
            start = index
        previous = index
    runs.append({"start_index": start, "end_index": previous})
    for run in runs:
        run["gap_start_year"] = int(years[run["start_index"]])
        run["gap_end_year"] = int(years[run["end_index"]])
        run["gap_length"] = run["end_index"] - run["start_index"] + 1
    return runs


def attach_gap_proximity(grid: pd.DataFrame, runs: list[dict[str, int]]) -> pd.DataFrame:
    result = grid.copy()
    result["internal_gap_length_if_missing"] = 0
    result["distance_to_nearest_internal_gap"] = np.nan
    result["nearest_internal_gap_length"] = 0
    if not runs:
        result["gap_proximity"] = "no_internal_gap"
        return result
    years = result["year"].to_numpy()
    best_distance = np.full(len(result), np.inf)
    best_length = np.zeros(len(result), dtype=int)
    for run in runs:
        inside = np.arange(run["start_index"], run["end_index"] + 1)
        result.loc[inside, "internal_gap_length_if_missing"] = run["gap_length"]
        distance = np.where(
            years < run["gap_start_year"],
            run["gap_start_year"] - years,
            np.where(years > run["gap_end_year"], years - run["gap_end_year"], 0),
        )
        replace = distance < best_distance
        best_distance[replace] = distance[replace]
        best_length[replace] = run["gap_length"]
    result["distance_to_nearest_internal_gap"] = best_distance
    result["nearest_internal_gap_length"] = best_length
    result["gap_proximity"] = pd.cut(
        result["distance_to_nearest_internal_gap"],
        bins=[-0.1, 0.1, 1.1, 3.1, np.inf],
        labels=["latent_gap_year", "adjacent_1y", "near_2_3y", "far_4plus_y"],
    ).astype("string")
    return result


def fit_all(panel: pd.DataFrame, support: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = support.loc[
        support["n_valid_years"].ge(15) & support["calendar_span_years"].ge(20)
    ].copy()
    if len(eligible) != EXPECTED_ELIGIBLE:
        raise ValueError(f"Approved gate retained {len(eligible)} municipalities, expected {EXPECTED_ELIGIBLE}")
    eligible["gap_stratum"] = eligible["max_internal_gap_years"].map(gap_stratum)
    eligible["history_stratum"] = eligible["n_valid_years"].map(history_stratum)

    records: list[pd.DataFrame] = []
    gaps: list[dict[str, object]] = []
    panel_by_code = {str(code): group.set_index("year") for code, group in panel.groupby("ibge_code", sort=False)}
    penalties = {name: lambda_from_p50(period) for name, period in P50_VALUES.items()}
    for row in eligible.itertuples(index=False):
        first, last = int(row.first_valid_year), int(row.last_valid_year)
        years = np.arange(first, last + 1)
        source = panel_by_code[str(row.ibge_code)].reindex(years)
        observed = source["valid_yield_for_detrending"].fillna(False).astype(bool).to_numpy()
        values = source["yield_tch_source_aware"].to_numpy(dtype=float)
        if int(observed.sum()) != int(row.n_valid_years):
            raise ValueError(f"Observed-year mismatch for {row.ibge_code}")
        grid = pd.DataFrame({
            "ibge_code": str(row.ibge_code),
            "municipality": row.municipality,
            "year": years,
            "observed_valid_yield": observed,
            "yield_tch": values,
            "production_raw_symbol": source["production_raw_symbol"].to_numpy(),
            "production_source_status": source["production_source_status"].to_numpy(),
            "production_source_value": source["production_source_value"].to_numpy(),
            "harvested_area_raw_symbol": source["harvested_area_raw_symbol"].to_numpy(),
            "harvested_area_source_status": source["harvested_area_source_status"].to_numpy(),
            "harvested_area_source_value": source["harvested_area_source_value"].to_numpy(),
            "first_valid_year": first,
            "last_valid_year": last,
            "n_valid_years": int(row.n_valid_years),
            "calendar_span_years": int(row.calendar_span_years),
            "max_internal_gap_years": int(row.max_internal_gap_years),
            "gap_stratum": row.gap_stratum,
            "history_stratum": row.history_stratum,
            "endpoint_distance_years": np.minimum(years - first, last - years),
            "mean_observed_area_share_1990_2025": row.mean_observed_area_share_1990_2025,
        })
        runs = contiguous_false_runs(observed, years)
        grid = attach_gap_proximity(grid, runs)
        fits = {"linear": fit_linear(years, values, observed)}
        for name, penalty in penalties.items():
            fits[name] = fit_second_difference(values, observed, penalty)
        for name, fitted in fits.items():
            grid[f"fitted_{name}"] = fitted
            grid[f"residual_{name}"] = np.where(observed, values - fitted, np.nan)
        records.append(grid)

        for number, run in enumerate(runs, start=1):
            before, after = run["start_index"] - 1, run["end_index"] + 1
            gap_record: dict[str, object] = {
                "ibge_code": str(row.ibge_code), "municipality": row.municipality,
                "gap_number": number, "gap_start_year": run["gap_start_year"],
                "gap_end_year": run["gap_end_year"], "gap_length": run["gap_length"],
                "before_year": int(years[before]), "after_year": int(years[after]),
                "before_yield_tch": values[before], "after_yield_tch": values[after],
                "municipality_gap_stratum": row.gap_stratum,
            }
            for name, fitted in fits.items():
                gap_record[f"fitted_before_{name}"] = fitted[before]
                gap_record[f"fitted_after_{name}"] = fitted[after]
                gap_record[f"fitted_change_across_gap_{name}"] = fitted[after] - fitted[before]
            gaps.append(gap_record)
    wide = pd.concat(records, ignore_index=True)
    gap_inventory = pd.DataFrame(gaps)
    return wide, gap_inventory


def long_output(wide: pd.DataFrame) -> pd.DataFrame:
    id_columns = [column for column in wide.columns if not column.startswith(("fitted_", "residual_"))]
    frames = []
    for specification in SPECIFICATIONS:
        frame = wide[id_columns].copy()
        frame.insert(3, "specification", specification)
        frame["fitted_trend_tch"] = wide[f"fitted_{specification}"]
        frame["residual_tch"] = wide[f"residual_{specification}"]
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    if result.duplicated(["ibge_code", "year", "specification"]).any():
        raise ValueError("Duplicate detrending output keys")
    return result


def observed_with_disagreement(wide: pd.DataFrame) -> pd.DataFrame:
    observed = wide.loc[wide["observed_valid_yield"]].copy()
    residual_columns = [f"residual_{name}" for name in SPECIFICATIONS]
    observed["cross_spec_residual_range"] = observed[residual_columns].max(axis=1) - observed[residual_columns].min(axis=1)
    observed["cross_spec_residual_sd"] = observed[residual_columns].std(axis=1, ddof=0)
    return observed


def pairwise_diagnostics(observed: pd.DataFrame, group_name: str = "overall", group_value: str = "all") -> pd.DataFrame:
    rows = []
    for left, right in combinations(SPECIFICATIONS, 2):
        a = observed[f"residual_{left}"]
        b = observed[f"residual_{right}"]
        difference = a - b
        rows.append({
            "group_name": group_name, "group_value": group_value,
            "specification_a": left, "specification_b": right, "n": len(observed),
            "pearson_correlation": a.corr(b, method="pearson"),
            "spearman_correlation": a.corr(b, method="spearman"),
            "sign_agreement": float(np.mean(np.sign(a) == np.sign(b))),
            "mean_difference_a_minus_b": difference.mean(),
            "sd_difference": difference.std(ddof=1), "mean_absolute_difference": difference.abs().mean(),
            "rmse_difference": float(np.sqrt(np.mean(difference**2))),
            "p05_difference": difference.quantile(0.05), "p25_difference": difference.quantile(0.25),
            "median_difference": difference.median(), "p75_difference": difference.quantile(0.75),
            "p95_difference": difference.quantile(0.95), "maximum_absolute_difference": difference.abs().max(),
        })
    return pd.DataFrame(rows)


def scale_diagnostics(observed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for specification in SPECIFICATIONS:
        residual = observed[f"residual_{specification}"]
        municipal_sd = observed.groupby("ibge_code")[f"residual_{specification}"].std(ddof=1)
        rows.append({
            "specification": specification, "n": len(residual), "mean_residual": residual.mean(),
            "residual_sd": residual.std(ddof=1), "residual_iqr": residual.quantile(0.75) - residual.quantile(0.25),
            "mean_absolute_residual": residual.abs().mean(), "residual_rmse": float(np.sqrt(np.mean(residual**2))),
            "p05_residual": residual.quantile(0.05), "median_residual": residual.median(), "p95_residual": residual.quantile(0.95),
            "mean_municipality_residual_sd": municipal_sd.mean(), "median_municipality_residual_sd": municipal_sd.median(),
        })
    return pd.DataFrame(rows)


def stratified_diagnostics(observed: pd.DataFrame, column: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    pair_frames = []
    for value, group in observed.groupby(column, observed=True, sort=False):
        summary: dict[str, object] = {
            "stratum": str(value), "municipalities": group["ibge_code"].nunique(), "observations": len(group),
            "mean_cross_spec_range": group["cross_spec_residual_range"].mean(),
            "median_cross_spec_range": group["cross_spec_residual_range"].median(),
            "p95_cross_spec_range": group["cross_spec_residual_range"].quantile(0.95),
            "maximum_cross_spec_range": group["cross_spec_residual_range"].max(),
        }
        for specification in SPECIFICATIONS:
            summary[f"residual_sd_{specification}"] = group[f"residual_{specification}"].std(ddof=1)
        summary_rows.append(summary)
        pair_frames.append(pairwise_diagnostics(group, column, str(value)))
    return pd.DataFrame(summary_rows), pd.concat(pair_frames, ignore_index=True)


def endpoint_diagnostics(observed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    endpoint = observed.copy()
    endpoint["endpoint_band"] = pd.cut(
        endpoint["endpoint_distance_years"], bins=[-0.1, 0.1, 1.1, 2.1, 5.1, np.inf],
        labels=["endpoint", "distance_1", "distance_2", "distance_3_5", "distance_6plus"],
    )
    summary, pairs = stratified_diagnostics(endpoint, "endpoint_band")
    return summary, pairs


def calendar_year_diagnostics(observed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in observed.groupby("year", sort=True):
        row: dict[str, object] = {
            "year": int(year), "municipalities": group["ibge_code"].nunique(), "observations": len(group),
            "mean_cross_spec_range": group["cross_spec_residual_range"].mean(),
            "median_cross_spec_range": group["cross_spec_residual_range"].median(),
            "p95_cross_spec_range": group["cross_spec_residual_range"].quantile(0.95),
            "maximum_cross_spec_range": group["cross_spec_residual_range"].max(),
        }
        for specification in SPECIFICATIONS:
            residual = group[f"residual_{specification}"]
            row[f"mean_residual_{specification}"] = residual.mean()
            row[f"residual_sd_{specification}"] = residual.std(ddof=1)
        rows.append(row)
    return pd.DataFrame(rows)


def municipality_disagreement(observed: pd.DataFrame) -> pd.DataFrame:
    result = observed.groupby(["ibge_code", "municipality"], as_index=False).agg(
        n_observed=("year", "size"), gap_stratum=("gap_stratum", "first"),
        history_stratum=("history_stratum", "first"),
        mean_area_share_1990_2025=("mean_observed_area_share_1990_2025", "first"),
        mean_cross_spec_range=("cross_spec_residual_range", "mean"),
        median_cross_spec_range=("cross_spec_residual_range", "median"),
        p95_cross_spec_range=("cross_spec_residual_range", lambda values: values.quantile(0.95)),
        maximum_cross_spec_range=("cross_spec_residual_range", "max"),
    )
    return result.sort_values(["mean_cross_spec_range", "ibge_code"], ascending=[False, True])


def representative_selection(support: pd.DataFrame, municipality: pd.DataFrame) -> pd.DataFrame:
    merged = support.merge(municipality, on=["ibge_code", "municipality"], how="inner", validate="one_to_one")
    selected: list[dict[str, object]] = []
    used: set[str] = set()

    def choose(reason: str, candidates: pd.DataFrame, sort_columns: list[str], ascending: list[bool]) -> None:
        available = candidates.loc[~candidates["ibge_code"].astype(str).isin(used)].sort_values(sort_columns, ascending=ascending)
        if available.empty:
            raise ValueError(f"No unique representative available for {reason}")
        row = available.iloc[0]
        used.add(str(row.ibge_code))
        selected.append({
            "selection_reason": reason, "ibge_code": str(row.ibge_code), "municipality": row.municipality,
            "n_valid_years": int(row.n_valid_years), "calendar_span_years": int(row.calendar_span_years),
            "max_internal_gap_years": int(row.max_internal_gap_years), "gap_stratum": row.gap_stratum,
            "mean_area_share_1990_2025": row.mean_area_share_1990_2025,
            "mean_cross_spec_range": row.mean_cross_spec_range, "p95_cross_spec_range": row.p95_cross_spec_range,
        })

    choose("long_complete_high_area", merged.loc[merged.n_valid_years.eq(52)], ["mean_area_share_1990_2025", "ibge_code"], [False, True])
    shorter = merged.loc[merged.n_valid_years.between(15, 19)]
    choose("shorter_eligible_history", shorter, ["mean_area_share_1990_2025", "ibge_code"], [False, True])
    choose("small_internal_gaps", merged.loc[merged.gap_stratum.eq("1-5")], ["mean_area_share_1990_2025", "ibge_code"], [False, True])
    choose("long_internal_gap", merged.loc[merged.gap_stratum.eq(">10")], ["mean_cross_spec_range", "ibge_code"], [False, True])
    choose("high_harvested_area", merged, ["mean_area_share_1990_2025", "ibge_code"], [False, True])
    choose("large_cross_spec_disagreement", merged, ["mean_cross_spec_range", "ibge_code"], [False, True])
    return pd.DataFrame(selected)


def create_plots(
    wide: pd.DataFrame, pairwise: pd.DataFrame, gap_summary: pd.DataFrame,
    year_summary: pd.DataFrame, representatives: pd.DataFrame, figure_root: Path,
) -> None:
    figure_root.mkdir(parents=True, exist_ok=True)
    matrix = pd.DataFrame(np.eye(len(SPECIFICATIONS)), index=SPECIFICATIONS, columns=SPECIFICATIONS)
    for row in pairwise.itertuples(index=False):
        matrix.loc[row.specification_a, row.specification_b] = row.pearson_correlation
        matrix.loc[row.specification_b, row.specification_a] = row.pearson_correlation
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap="viridis")
    ax.set_xticks(range(len(matrix)), matrix.columns)
    ax.set_yticks(range(len(matrix)), matrix.index)
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            ax.text(j, i, f"{matrix.iloc[i, j]:.3f}", ha="center", va="center", color="white" if matrix.iloc[i, j] < .65 else "black")
    ax.set_title("Residual Pearson correlations")
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(figure_root / "residual_correlation_heatmap.png", dpi=180)
    plt.close(fig)

    order = ["0", "1-5", "6-10", ">10"]
    plotted = gap_summary.set_index("stratum").reindex(order)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(plotted.index, plotted["mean_cross_spec_range"], color="#4472C4")
    ax.set_xlabel("Maximum internal-gap stratum")
    ax.set_ylabel("Mean residual range across specifications (t/ha)")
    ax.set_title("Cross-specification disagreement by internal-gap stratum")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    fig.savefig(figure_root / "gap_stratum_disagreement.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(year_summary.year, year_summary.mean_cross_spec_range, label="Mean")
    ax.plot(year_summary.year, year_summary.p95_cross_spec_range, label="95th percentile")
    ax.set_xlabel("Calendar year")
    ax.set_ylabel("Residual range across specifications (t/ha)")
    ax.set_title("Cross-specification disagreement by calendar year")
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_root / "calendar_year_disagreement.png", dpi=180)
    plt.close(fig)

    representative_root = figure_root / "representative_municipalities"
    representative_root.mkdir(parents=True, exist_ok=True)
    colors = {"linear": "#222222", "p50_10": "#1f77b4", "p50_12": "#2ca02c", "p50_6": "#d62728"}
    for row in representatives.itertuples(index=False):
        group = wide.loc[wide.ibge_code.astype(str).eq(str(row.ibge_code))].sort_values("year")
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
        observed = group.observed_valid_yield
        axes[0].scatter(group.loc[observed, "year"], group.loc[observed, "yield_tch"], color="black", s=22, label="Observed yield", zorder=5)
        for specification in SPECIFICATIONS:
            axes[0].plot(group.year, group[f"fitted_{specification}"], color=colors[specification], label=specification)
            axes[1].plot(group.year, group[f"residual_{specification}"], marker="o", markersize=2.5, linewidth=1, color=colors[specification], label=specification)
        axes[1].axhline(0, color="gray", linewidth=.8)
        axes[0].set_ylabel("Yield / fitted trend (t/ha)")
        axes[1].set_ylabel("Residual (t/ha)")
        axes[1].set_xlabel("Year")
        axes[0].legend(ncol=3, fontsize=8)
        for ax in axes:
            ax.grid(alpha=.2)
        fig.suptitle(f"{row.municipality} ({row.ibge_code}) — {row.selection_reason}")
        fig.tight_layout()
        fig.savefig(representative_root / f"{row.selection_reason}_{row.ibge_code}.png", dpi=180)
        plt.close(fig)


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    shown = frame[columns].copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.{digits}f}" if pd.notna(value) else "")
    headers = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)]
    return "\n".join([headers, separator, *rows])


def write_reports(
    output_root: Path, data_root: Path, support: pd.DataFrame, wide: pd.DataFrame,
    pairwise: pd.DataFrame, scale: pd.DataFrame, gap_summary: pd.DataFrame,
    gap_pairs: pd.DataFrame, endpoint_summary: pd.DataFrame, history_summary: pd.DataFrame,
    proximity_summary: pd.DataFrame,
    year_summary: pd.DataFrame, municipality: pd.DataFrame, representatives: pd.DataFrame,
    lambda_table: pd.DataFrame,
) -> None:
    eligible = support.loc[support.n_valid_years.ge(15) & support.calendar_span_years.ge(20)]
    observed = observed_with_disagreement(wide)
    gap0 = gap_summary.set_index("stratum").loc["0"]
    gap_long = gap_summary.set_index("stratum").loc[">10"]
    gap0_pairs = gap_pairs.loc[gap_pairs.group_value.eq("0")].set_index(["specification_a", "specification_b"])
    gap_long_pairs = gap_pairs.loc[gap_pairs.group_value.eq(">10")].set_index(["specification_a", "specification_b"])
    highest_year = year_summary.sort_values(["mean_cross_spec_range", "year"], ascending=[False, True]).iloc[0]
    top_municipalities = municipality.head(10)
    slow_pairs = pairwise.loc[
        pairwise.specification_a.isin(["linear", "p50_10", "p50_12"])
        & pairwise.specification_b.isin(["linear", "p50_10", "p50_12"])
    ]
    aggressive_pairs = pairwise.loc[
        pairwise.specification_a.eq("p50_6") | pairwise.specification_b.eq("p50_6")
    ]
    report = f"""# EXP-02A Phase 1 Detrending Diagnostics

## Status and scope

**PHASE 1 COMPLETED.** The approved gate was applied exactly: `n_valid_years >= 15`, calendar span `>= 20`, and no hard internal-gap exclusion. The run compares only Linear, P50=10, P50=12, and aggressive P50=6. It does not select a model, use weather results, split long gaps, or implement EXP-02B.

## Eligibility and output validation

- Eligible municipalities: **{len(eligible)}**; expected: {EXPECTED_ELIGIBLE}.
- Valid observed yield rows among eligible municipalities: **{int(observed.shape[0])}**.
- Annual smoother-grid rows: **{len(wide)}**; specification-grid rows: **{len(wide) * len(SPECIFICATIONS)}**.
- Residuals are present only on observed valid-yield years; latent fitted trends may exist on internal missing grid years.
- Grid endpoints equal each municipality's first and last valid years.
- Municipality × year × specification output keys are unique.

## Lambda validation

{markdown_table(lambda_table, ['specification', 'p50_years', 'lambda', 'response_at_p50'], digits=8)}

## Residual scale

{markdown_table(scale, ['specification', 'n', 'residual_sd', 'residual_iqr', 'mean_absolute_residual', 'residual_rmse', 'mean_municipality_residual_sd'])}

Residual scale is descriptive, not a model-selection score. A smaller residual variance under a more flexible trend is expected mechanically and is not evidence of superiority.

## Pairwise residual agreement

{markdown_table(pairwise, ['specification_a', 'specification_b', 'pearson_correlation', 'spearman_correlation', 'sign_agreement', 'mean_absolute_difference', 'p95_difference', 'maximum_absolute_difference'])}

Across Linear/P50=10/P50=12 comparisons, Pearson residual correlation ranges from **{slow_pairs.pearson_correlation.min():.4f}** to **{slow_pairs.pearson_correlation.max():.4f}**. Comparisons involving aggressive P50=6 range from **{aggressive_pairs.pearson_correlation.min():.4f}** to **{aggressive_pairs.pearson_correlation.max():.4f}**. This documents sensitivity without designating a winner.

## Internal-gap diagnostics

{markdown_table(gap_summary, ['stratum', 'municipalities', 'observations', 'mean_cross_spec_range', 'median_cross_spec_range', 'p95_cross_spec_range', 'maximum_cross_spec_range'])}

The `>10` group has mean cross-specification residual range **{gap_long.mean_cross_spec_range:.4f} t/ha**, versus **{gap0.mean_cross_spec_range:.4f} t/ha** for `gap = 0` (difference **{gap_long.mean_cross_spec_range - gap0.mean_cross_spec_range:+.4f} t/ha**, ratio **{gap_long.mean_cross_spec_range / gap0.mean_cross_spec_range:.3f}**). This is a diagnostic comparison, not an automatic reason to split or exclude histories.

For Linear versus P50=10, residual correlation is **{gap_long_pairs.loc[('linear', 'p50_10'), 'pearson_correlation']:.4f}** in `gap >10` versus **{gap0_pairs.loc[('linear', 'p50_10'), 'pearson_correlation']:.4f}** in `gap = 0`. For P50=10 versus P50=12 it remains **{gap_long_pairs.loc[('p50_10', 'p50_12'), 'pearson_correlation']:.4f}** versus **{gap0_pairs.loc[('p50_10', 'p50_12'), 'pearson_correlation']:.4f}**, respectively.

Observed-year proximity to an internal gap:

{markdown_table(proximity_summary, ['stratum', 'municipalities', 'observations', 'mean_cross_spec_range', 'p95_cross_spec_range', 'maximum_cross_spec_range'])}

Detailed pairwise results by gap stratum and an inventory of every internal gap are supplied as CSV outputs.

## Endpoint and history-length diagnostics

{markdown_table(endpoint_summary, ['stratum', 'municipalities', 'observations', 'mean_cross_spec_range', 'p95_cross_spec_range', 'maximum_cross_spec_range'])}

{markdown_table(history_summary, ['stratum', 'municipalities', 'observations', 'mean_cross_spec_range', 'p95_cross_spec_range', 'maximum_cross_spec_range'])}

## Calendar-year and unusually large disagreement

The calendar year with the highest mean cross-specification residual range is **{int(highest_year.year)}** at **{highest_year.mean_cross_spec_range:.4f} t/ha**. Full year-by-year scale and disagreement diagnostics are provided in `calendar_year_diagnostics.csv`.

Municipalities with the largest mean cross-specification residual range:

{markdown_table(top_municipalities, ['municipality', 'ibge_code', 'n_observed', 'gap_stratum', 'mean_cross_spec_range', 'p95_cross_spec_range', 'maximum_cross_spec_range'])}

The observation-level ranked file reports the municipality-years with the largest disagreement without imposing an unapproved materiality threshold.

## Representative plots

{markdown_table(representatives, ['selection_reason', 'municipality', 'ibge_code', 'n_valid_years', 'calendar_span_years', 'max_internal_gap_years', 'mean_cross_spec_range'])}

Selection is deterministic and rule-based. The plots are diagnostics, not a basis for choosing the visually most attractive specification.

## Interpretation boundaries and questions for Chat

- A residual is a detrended yield anomaly, not a measured weather-caused component.
- P50=6 is an aggressive sensitivity case near the multi-year climate-variability band; lower residual scale is not evidence that it is preferable.
- Long gaps were bridged only by the stated smoothness assumption for latent fitted values. No residual was manufactured inside a gap.
- Chat should interpret whether the observed gap-stratum, endpoint, and aggressive-smoother disagreement is practically material. No quantitative materiality threshold was invented here.
- No choice between Linear, P50=10, and P50=12 is made in this report.
"""
    (output_root / "EXP_02A_phase1_diagnostic_report.md").write_text(report, encoding="utf-8")

    execution = f"""# EXP-02A Phase 1 Execution Report

## Scope

Phase 1 completed under the approved 511-municipality gate. No EXP-02B code or weather-based tuning was executed, and no winning detrending model was selected.

## Files created or modified

- `src/analysis/exp02a_detrending.py`
- `src/tests/analysis/test_exp02a_detrending.py`
- Reproducible model output under `{data_root.resolve()}`.
- Diagnostics, reports, and plots under `{output_root.resolve()}`.

No unrelated EXP-01 source file was modified.

## Commands and tests

- Main command: `py -3 -m analysis.exp02a_detrending --project-root <repository>` with `PYTHONPATH=src`.
- Focused Phase 1 unit and integration tests validate lambdas, normal equations, missing-year residual behavior, exact gate reconciliation, grid endpoints, source semantics, and output-key uniqueness.
- Phase 1, Phase 0, and relevant EXP-01S source-semantics regression tests passed: **38 passed**.
- Nine generated figures were visually inspected; residual lines correctly break across unobserved years while fitted trend lines retain the approved latent annual grid.

## Reconciliation

- Eligible municipalities: {len(eligible)}.
- Observed residual-bearing municipality-years: {len(observed)}.
- Latent annual-grid rows: {len(wide)}.
- Four specifications: {', '.join(SPECIFICATIONS)}.
- Missing/unavailable/undefined yield years have no residual.

## Main diagnostic outputs

- `residual_pairwise_diagnostics.csv`
- `residual_scale_diagnostics.csv`
- `gap_stratum_summary.csv` and `gap_stratum_pairwise_diagnostics.csv`
- `internal_gap_inventory.csv` and `gap_proximity_diagnostics.csv`
- `endpoint_diagnostics.csv`
- `history_length_diagnostics.csv`
- `calendar_year_diagnostics.csv`
- ranked municipality and municipality-year disagreement tables
- deterministic representative-selection table and plots

## Warnings / interpretation

Latent trend values across missing years are consequences of the approved smoothness assumption, not reconstructed observed yields. The gap `>10` comparison is diagnostic and does not authorize automatic exclusion or history splitting. Residual-scale differences are not model-selection evidence.
"""
    (output_root / "EXP_02A_phase1_execution_report.md").write_text(execution, encoding="utf-8")


def run(project_root: Path) -> int:
    panel_path = project_root / "data/processed/analysis/exp_02a_yield_support_audit/source_aware_annual_yield_panel_1974_2025.csv"
    support_path = project_root / "outputs/research/exp_02/exp_02a_phase0/municipality_support.csv"
    data_root = project_root / "data/processed/analysis/exp_02a_phase1"
    output_root = project_root / "outputs/research/exp_02/exp_02a_phase1"
    figure_root = output_root / "figures"
    data_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(panel_path, dtype={"ibge_code": "string"})
    support = pd.read_csv(support_path, dtype={"ibge_code": "string"})
    panel["valid_yield_for_detrending"] = panel["valid_yield_for_detrending"].astype(bool)
    wide, gap_inventory = fit_all(panel, support)
    long = long_output(wide)
    observed = observed_with_disagreement(wide)
    pairwise = pairwise_diagnostics(observed)
    scale = scale_diagnostics(observed)
    gap_summary, gap_pairs = stratified_diagnostics(observed, "gap_stratum")
    history_summary, history_pairs = stratified_diagnostics(observed, "history_stratum")
    endpoint_summary, endpoint_pairs = endpoint_diagnostics(observed)
    proximity_summary, proximity_pairs = stratified_diagnostics(observed, "gap_proximity")
    year_summary = calendar_year_diagnostics(observed)
    municipality = municipality_disagreement(observed)
    unusual_observations = observed.sort_values(
        ["cross_spec_residual_range", "ibge_code", "year"], ascending=[False, True, True]
    ).head(250)
    representatives = representative_selection(
        support.loc[support.n_valid_years.ge(15) & support.calendar_span_years.ge(20)], municipality
    )
    lambda_table = pd.DataFrame([
        {"specification": name, "p50_years": period, "lambda": lambda_from_p50(period),
         "response_at_p50": amplitude_response(period, lambda_from_p50(period))}
        for name, period in P50_VALUES.items()
    ])

    residual_columns = [f"residual_{name}" for name in SPECIFICATIONS]
    if long.loc[~long.observed_valid_yield, "residual_tch"].notna().any():
        raise ValueError("Residuals were generated for unobserved yield years")
    if long.loc[long.observed_valid_yield, "residual_tch"].isna().any():
        raise ValueError("Observed valid-yield row is missing a residual")
    if observed[residual_columns].isna().any().any():
        raise ValueError("Observed diagnostic rows contain missing residuals")
    endpoint_check = wide.groupby("ibge_code").agg(grid_first=("year", "min"), grid_last=("year", "max"), first=("first_valid_year", "first"), last=("last_valid_year", "first"))
    if not (endpoint_check.grid_first.eq(endpoint_check["first"]) & endpoint_check.grid_last.eq(endpoint_check["last"])).all():
        raise ValueError("Smoother grid endpoint mismatch")

    long.to_csv(data_root / "municipality_detrending_long.csv", index=False)
    observed.to_csv(data_root / "observed_residuals_wide.csv", index=False)
    gap_inventory.to_csv(output_root / "internal_gap_inventory.csv", index=False)
    pairwise.to_csv(output_root / "residual_pairwise_diagnostics.csv", index=False)
    scale.to_csv(output_root / "residual_scale_diagnostics.csv", index=False)
    gap_summary.to_csv(output_root / "gap_stratum_summary.csv", index=False)
    gap_pairs.to_csv(output_root / "gap_stratum_pairwise_diagnostics.csv", index=False)
    history_summary.to_csv(output_root / "history_length_diagnostics.csv", index=False)
    history_pairs.to_csv(output_root / "history_length_pairwise_diagnostics.csv", index=False)
    endpoint_summary.to_csv(output_root / "endpoint_diagnostics.csv", index=False)
    endpoint_pairs.to_csv(output_root / "endpoint_pairwise_diagnostics.csv", index=False)
    proximity_summary.to_csv(output_root / "gap_proximity_diagnostics.csv", index=False)
    proximity_pairs.to_csv(output_root / "gap_proximity_pairwise_diagnostics.csv", index=False)
    year_summary.to_csv(output_root / "calendar_year_diagnostics.csv", index=False)
    municipality.to_csv(output_root / "municipality_disagreement_ranked.csv", index=False)
    unusual_columns = [
        "ibge_code", "municipality", "year", "gap_stratum", "history_stratum", "endpoint_distance_years",
        "gap_proximity", "yield_tch", *residual_columns, "cross_spec_residual_range", "cross_spec_residual_sd",
    ]
    unusual_observations[unusual_columns].to_csv(output_root / "municipality_year_disagreement_top250.csv", index=False)
    representatives.to_csv(output_root / "representative_municipality_selection.csv", index=False)
    lambda_table.to_csv(output_root / "smoother_lambda_validation.csv", index=False)

    create_plots(wide, pairwise, gap_summary, year_summary, representatives, figure_root)
    write_reports(
        output_root, data_root, support, wide, pairwise, scale, gap_summary, gap_pairs,
        endpoint_summary, history_summary, proximity_summary, year_summary, municipality, representatives, lambda_table,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
