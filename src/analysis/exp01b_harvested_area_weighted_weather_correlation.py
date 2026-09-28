"""EXP-01B harvested-area-weighted municipality weather correlations.

The municipality × year × calendar-month panel is preserved.  Contemporaneous
annual observed-only harvested-area shares are observation weights; the data
are never pre-aggregated into a statewide weather series.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.exp01a_municipality_weather_correlation import (
    CORE_PAIRS,
    CROSS_MONTH_VARIABLES,
    LAG_VARIABLES,
    WEATHER_VARIABLES,
    _heatmap,
    construct_lag1,
    load_and_validate,
)


EXPERIMENT = "exp_01b_harvested_area_weighted_weather_correlation"
AREA_COLUMNS = [
    "ibge_code",
    "municipality",
    "year",
    "raw_area_symbol",
    "harvested_area_ha_symbol_aware",
    "area_weight",
    "source_status",
]
VALID_STATUSES = {"numeric_positive", "numeric_zero", "absolute_zero", "unavailable"}


@dataclass(frozen=True)
class WeightedResult:
    value: float
    observed_n: int
    positive_weight_n: int
    zero_weight_n: int
    weight_sum: float
    effective_n: float
    status: str


@dataclass(frozen=True)
class PanelValidation:
    panel: pd.DataFrame
    annual: pd.DataFrame
    name_mismatches: pd.DataFrame


def kish_effective_n(weights: pd.Series | np.ndarray) -> float:
    values = np.asarray(weights, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if not len(values):
        return np.nan
    return float(values.sum() ** 2 / np.square(values).sum())


def weighted_pearson(
    frame: pd.DataFrame,
    x: str | int,
    y: str | int,
    weight: str | int = "analysis_weight",
) -> WeightedResult:
    """Pairwise-complete weighted Pearson with explicit support diagnostics."""

    pair = pd.concat(
        [frame[x].rename("_x"), frame[y].rename("_y"), frame[weight].rename("_w")],
        axis=1,
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if (pair["_w"] < 0).any():
        raise ValueError("Weights must be non-negative")
    observed_n = len(pair)
    positive = pair.loc[pair["_w"].gt(0)].copy()
    positive_n = len(positive)
    zero_n = observed_n - positive_n
    weight_sum = float(positive["_w"].sum())
    effective_n = kish_effective_n(positive["_w"])
    if positive_n < 2 or weight_sum <= 0:
        return WeightedResult(np.nan, observed_n, positive_n, zero_n, weight_sum, effective_n, "insufficient_positive_weight")
    w = positive["_w"].to_numpy(dtype=float)
    xv = positive["_x"].to_numpy(dtype=float)
    yv = positive["_y"].to_numpy(dtype=float)
    x_mean = float(np.average(xv, weights=w))
    y_mean = float(np.average(yv, weights=w))
    x_centered = xv - x_mean
    y_centered = yv - y_mean
    x_var = float(np.average(np.square(x_centered), weights=w))
    y_var = float(np.average(np.square(y_centered), weights=w))
    if x_var <= 0 or y_var <= 0:
        return WeightedResult(np.nan, observed_n, positive_n, zero_n, weight_sum, effective_n, "constant_variable")
    covariance = float(np.average(x_centered * y_centered, weights=w))
    value = float(np.clip(covariance / np.sqrt(x_var * y_var), -1.0, 1.0))
    return WeightedResult(value, observed_n, positive_n, zero_n, weight_sum, effective_n, "defined")


def weighted_spearman(
    frame: pd.DataFrame,
    x: str | int,
    y: str | int,
    weight: str | int = "analysis_weight",
) -> WeightedResult:
    """Weighted Pearson of average-tie ranks among positive-weight observations."""

    pair = pd.concat(
        [frame[x].rename("_x"), frame[y].rename("_y"), frame[weight].rename("_w")],
        axis=1,
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if (pair["_w"] < 0).any():
        raise ValueError("Weights must be non-negative")
    positive = pair.loc[pair["_w"].gt(0)].copy()
    ranked = pd.DataFrame({
        "rank_x": positive["_x"].rank(method="average"),
        "rank_y": positive["_y"].rank(method="average"),
        "analysis_weight": positive["_w"],
    })
    result = weighted_pearson(ranked, "rank_x", "rank_y")
    return WeightedResult(
        result.value,
        len(pair),
        len(positive),
        len(pair) - len(positive),
        result.weight_sum,
        result.effective_n,
        result.status,
    )


def load_area_weights(path: Path) -> pd.DataFrame:
    area = pd.read_csv(path, dtype={"ibge_code": "string"})
    missing = sorted(set(AREA_COLUMNS) - set(area.columns))
    if missing:
        raise ValueError(f"Harvested-area table missing columns: {missing}")
    area = area[AREA_COLUMNS].copy()
    area["ibge_code"] = area["ibge_code"].str.strip()
    area["year"] = pd.to_numeric(area["year"], errors="raise").astype(int)
    if area.duplicated(["ibge_code", "year"]).any():
        raise ValueError("Harvested-area table has duplicate municipality-year keys")
    statuses = set(area["source_status"].dropna())
    if statuses != VALID_STATUSES:
        raise ValueError(f"Unexpected harvested-area source statuses: {sorted(statuses)}")
    numeric_area = pd.to_numeric(area["harvested_area_ha_symbol_aware"], errors="coerce")
    observed = area["source_status"].ne("unavailable")
    if numeric_area[observed].isna().any() or numeric_area[observed].lt(0).any():
        raise ValueError("Observed harvested area must be finite and non-negative")
    if numeric_area[~observed].notna().any():
        raise ValueError("Unavailable harvested area must remain missing")
    zero_status = area["source_status"].isin(["absolute_zero", "numeric_zero"])
    if not numeric_area[zero_status].eq(0).all():
        raise ValueError("Explicit/numeric zero statuses must have zero symbol-aware area")
    denominators = numeric_area.where(observed).groupby(area["year"]).transform("sum")
    if denominators.isna().any() or denominators.le(0).any():
        raise ValueError("Every year must have positive observed harvested area")
    area["analysis_weight"] = numeric_area / denominators
    stored = pd.to_numeric(area["area_weight"], errors="coerce")
    positive = area["source_status"].eq("numeric_positive")
    if not np.allclose(area.loc[positive, "analysis_weight"], stored[positive], atol=1e-12, rtol=1e-12):
        raise ValueError("Reconstructed positive weights disagree with EXP-01S area_weight")
    if area.loc[zero_status, "analysis_weight"].ne(0).any():
        raise ValueError("Explicit zeros did not retain weight zero")
    if area.loc[~observed, "analysis_weight"].notna().any():
        raise ValueError("Unavailable harvested area received a fabricated weight")
    return area


def build_weighted_panel(weather: pd.DataFrame, area: pd.DataFrame) -> PanelValidation:
    weather_keys = weather[["ibge_code", "year"]].drop_duplicates()
    area_keys = area[["ibge_code", "year"]].drop_duplicates()
    key_check = weather_keys.merge(area_keys, on=["ibge_code", "year"], how="outer", indicator=True)
    if not key_check["_merge"].eq("both").all():
        raise ValueError("Weather and harvested-area municipality-year keys do not match")
    panel = weather.merge(
        area,
        on=["ibge_code", "year"],
        how="left",
        validate="many_to_one",
        suffixes=("_weather", "_area"),
    )
    if len(panel) != len(weather) or panel["source_status"].isna().any():
        raise ValueError("Weather-area merge did not preserve the complete weather panel")
    mismatches = panel.loc[
        panel["municipality_weather"].ne(panel["municipality_area"]),
        ["ibge_code", "municipality_weather", "municipality_area"],
    ].drop_duplicates().reset_index(drop=True)
    annual_rows = []
    for year, group in panel.groupby("year", sort=True):
        municipality = group.drop_duplicates(["ibge_code", "year"])
        month_sums = group.groupby("calendar_month")["analysis_weight"].sum(min_count=1)
        positive = municipality["analysis_weight"].gt(0)
        zeros = municipality["analysis_weight"].eq(0)
        unavailable = municipality["analysis_weight"].isna()
        annual_rows.append({
            "year": int(year),
            "panel_municipalities": municipality["ibge_code"].nunique(),
            "panel_rows": len(group),
            "positive_weight_municipalities": int(positive.sum()),
            "zero_weight_municipalities": int(zeros.sum()),
            "unavailable_weight_municipalities": int(unavailable.sum()),
            "observed_weight_municipalities": int((~unavailable).sum()),
            "annual_weight_sum": float(municipality["analysis_weight"].sum()),
            "minimum_month_weight_sum": float(month_sums.min()),
            "maximum_month_weight_sum": float(month_sums.max()),
            "maximum_municipality_weight": float(municipality["analysis_weight"].max()),
            "annual_kish_effective_n": kish_effective_n(municipality["analysis_weight"]),
        })
    annual = pd.DataFrame(annual_rows)
    if not np.allclose(annual["annual_weight_sum"], 1.0, atol=1e-12):
        raise ValueError("Annual observed-only weights do not sum to one")
    if not np.allclose(annual["minimum_month_weight_sum"], 1.0, atol=1e-12):
        raise ValueError("Month-slice weights do not sum to one in every year")
    if not np.allclose(annual["maximum_month_weight_sum"], 1.0, atol=1e-12):
        raise ValueError("Month-slice weights do not sum to one in every year")
    return PanelValidation(panel, annual, mismatches)


def _result_fields(prefix: str, result: WeightedResult) -> dict[str, object]:
    return {
        prefix: result.value,
        f"{prefix}_observed_n": result.observed_n,
        f"{prefix}_positive_weight_n": result.positive_weight_n,
        f"{prefix}_zero_weight_n": result.zero_weight_n,
        f"{prefix}_weight_sum": result.weight_sum,
        f"{prefix}_effective_n": result.effective_n,
        f"{prefix}_status": result.status,
    }


def weighted_matrices(frame: pd.DataFrame, variables: list[str]) -> dict[str, pd.DataFrame]:
    names = ["pearson", "spearman", "observed_n", "positive_weight_n", "zero_weight_n", "weight_sum", "effective_n"]
    matrices = {name: pd.DataFrame(np.nan, index=variables, columns=variables) for name in names}
    for x in variables:
        for y in variables:
            p = weighted_pearson(frame, x, y)
            s = weighted_spearman(frame, x, y)
            matrices["pearson"].loc[x, y] = p.value
            matrices["spearman"].loc[x, y] = s.value
            for name in ["observed_n", "positive_weight_n", "zero_weight_n", "weight_sum", "effective_n"]:
                matrices[name].loc[x, y] = getattr(p, name)
    return matrices


def weighted_monthly_correlations(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    rows = []
    for month in range(1, 13):
        subset = frame.loc[frame["calendar_month"].eq(month)]
        for x, y in combinations(variables, 2):
            p = weighted_pearson(subset, x, y)
            s = weighted_spearman(subset, x, y)
            rows.append({"month": month, "variable_x": x, "variable_y": y, **_result_fields("weighted_pearson_r", p), **_result_fields("weighted_spearman_rho", s)})
    return pd.DataFrame(rows)


def weighted_lag1(frame: pd.DataFrame, variables: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    lagged = construct_lag1(frame, variables)
    overall_rows, monthly_rows = [], []
    for variable in variables:
        lag = f"{variable}_lag1"
        p = weighted_pearson(lagged, variable, lag)
        s = weighted_spearman(lagged, variable, lag)
        overall_rows.append({"variable": variable, **_result_fields("weighted_pearson_r", p), **_result_fields("weighted_spearman_rho", s)})
        for month in range(1, 13):
            subset = lagged.loc[lagged["calendar_month"].eq(month)]
            p = weighted_pearson(subset, variable, lag)
            s = weighted_spearman(subset, variable, lag)
            monthly_rows.append({"destination_month": month, "variable": variable, **_result_fields("weighted_pearson_r", p), **_result_fields("weighted_spearman_rho", s)})
    return pd.DataFrame(overall_rows), pd.DataFrame(monthly_rows)


def weighted_cross_month(frame: pd.DataFrame, variable: str) -> dict[str, pd.DataFrame]:
    if frame.duplicated(["ibge_code", "year", "calendar_month"]).any():
        raise ValueError("Duplicate keys before cross-month reshape")
    values = frame.pivot(index=["ibge_code", "year"], columns="calendar_month", values=variable).reindex(columns=range(1, 13))
    weights = frame.drop_duplicates(["ibge_code", "year"]).set_index(["ibge_code", "year"])["analysis_weight"].reindex(values.index)
    wide = values.copy()
    wide["analysis_weight"] = weights
    labels = list(range(1, 13))
    names = ["pearson", "spearman", "observed_n", "positive_weight_n", "zero_weight_n", "weight_sum", "effective_n"]
    matrices = {name: pd.DataFrame(np.nan, index=labels, columns=labels) for name in names}
    for x in labels:
        for y in labels:
            p = weighted_pearson(wide, x, y)
            s = weighted_spearman(wide, x, y)
            matrices["pearson"].loc[x, y] = p.value
            matrices["spearman"].loc[x, y] = s.value
            for name in ["observed_n", "positive_weight_n", "zero_weight_n", "weight_sum", "effective_n"]:
                matrices[name].loc[x, y] = getattr(p, name)
    for matrix in matrices.values():
        matrix.index.name = "month"
        matrix.columns.name = "month"
    return matrices


def cross_month_summary(all_matrices: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    rows = []
    for variable, matrices in all_matrices.items():
        row: dict[str, object] = {"variable": variable}
        for method in ["pearson", "spearman"]:
            matrix = matrices[method]
            for distance, label in [(1, "adjacent"), (3, "three_month"), (6, "six_month")]:
                values = [matrix.loc[m, m + distance] for m in range(1, 13 - distance)]
                row[f"weighted_{method}_mean_{label}"] = float(np.mean(values))
                row[f"weighted_{method}_min_{label}"] = float(np.min(values))
                row[f"weighted_{method}_max_{label}"] = float(np.max(values))
        row["pairwise_observed_n"] = int(matrices["observed_n"].iloc[0, 1])
        row["positive_weight_n"] = int(matrices["positive_weight_n"].iloc[0, 1])
        row["weight_sum"] = float(matrices["weight_sum"].iloc[0, 1])
        row["effective_n"] = float(matrices["effective_n"].iloc[0, 1])
        rows.append(row)
    return pd.DataFrame(rows)


def strongest_pairs(matrices: dict[str, pd.DataFrame], monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, matrix in [("pearson", matrices["pearson"]), ("spearman", matrices["spearman"])]:
        for x, y in combinations(WEATHER_VARIABLES, 2):
            value = matrix.loc[x, y]
            rows.append({"scope": "pooled", "month": "", "method": method, "variable_x": x, "variable_y": y, "correlation": value, "absolute_correlation": abs(value)})
    for row in monthly.itertuples(index=False):
        for method, value in [("pearson", row.weighted_pearson_r), ("spearman", row.weighted_spearman_rho)]:
            rows.append({"scope": "calendar_month", "month": row.month, "method": method, "variable_x": row.variable_x, "variable_y": row.variable_y, "correlation": value, "absolute_correlation": abs(value)})
    return pd.DataFrame(rows).sort_values(["scope", "method", "absolute_correlation"], ascending=[True, True, False]).reset_index(drop=True)


def _core_matrix(core: pd.DataFrame, value: str) -> pd.DataFrame:
    labeled = core.assign(pair=core["variable_x"] + " ↔ " + core["variable_y"])
    return labeled.pivot(index="month", columns="pair", values=value).reindex(range(1, 13))


def _lag_bar(lag: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(lag))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(x - width / 2, lag["weighted_pearson_r"], width, label="Weighted Pearson")
    ax.bar(x + width / 2, lag["weighted_spearman_rho"], width, label="Weighted Spearman")
    ax.set_xticks(x, labels=lag["variable"], rotation=25, ha="right")
    ax.set_ylim(-1, 1)
    ax.set_ylabel("weighted lag-1 correlation")
    ax.set_title("EXP-01B weighted lag-1 persistence")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    validation: PanelValidation,
    area_path: Path,
    weather_path: Path,
    pooled: dict[str, pd.DataFrame],
    core: pd.DataFrame,
    lag: pd.DataFrame,
    cross: pd.DataFrame,
) -> None:
    annual = validation.annual
    core_lines = []
    for (x, y), group in core.groupby(["variable_x", "variable_y"], sort=False):
        core_lines.append(
            f"- `{x} ↔ {y}`: mean monthly weighted Pearson {group.weighted_pearson_r.mean():.3f} "
            f"(range {group.weighted_pearson_r.min():.3f} to {group.weighted_pearson_r.max():.3f}); "
            f"mean weighted Spearman {group.weighted_spearman_rho.mean():.3f}."
        )
    lag_lines = [
        f"- `{row.variable}`: weighted Pearson {row.weighted_pearson_r:.3f}; weighted Spearman {row.weighted_spearman_rho:.3f}; effective n {row.weighted_pearson_r_effective_n:.1f}."
        for row in lag.itertuples(index=False)
    ]
    cross_lines = [
        f"- `{row.variable}`: adjacent / 3-month / 6-month weighted Pearson = "
        f"{row.weighted_pearson_mean_adjacent:.3f} / {row.weighted_pearson_mean_three_month:.3f} / {row.weighted_pearson_mean_six_month:.3f}."
        for row in cross.itertuples(index=False)
    ]
    text = f"""# EXP-01B Execution Report

## Status

**COMPLETED.** EXP-01B retained the municipality × year × calendar-month panel and applied contemporaneous annual observed-only harvested-area shares as observation weights. No statewide weather series was constructed. EXP-01C was not run.

## Files created or modified

- `src/analysis/exp01b_harvested_area_weighted_weather_correlation.py`
- `src/tests/analysis/test_exp01b_harvested_area_weighted_weather_correlation.py`
- validation, cross-variable, cross-month, summary, and figure artifacts under `data/processed/analysis/{EXPERIMENT}/`
- this report under `outputs/experiments/{EXPERIMENT}/`

Existing unrelated working-tree changes were preserved. NASA/ERA5 downloaders and ETL source were not modified.

## Data and variables

- Weather source: `{weather_path.resolve()}`; 1990–2025, 642 municipalities, 277,344 municipality-month rows, no weather missingness.
- Weight source: `{area_path.resolve()}`; 23,112 municipality-year rows.
- Included weather variables: {', '.join(f'`{v}`' for v in WEATHER_VARIABLES)}.
- Canonical merge key: `ibge_code × year`; month remains part of the observation key after the merge.
- The same annual municipality weight is repeated across its 12 calendar months.

## Weighted Pearson and Spearman implementation

Weighted Pearson uses positive finite pairwise-complete observations, weighted means, weighted population covariance, and weighted population variances. Multiplying all weights by a constant leaves the coefficient unchanged.

Weighted Spearman first filters to pairwise-complete positive-weight observations, assigns ordinary average ranks (`rank(method="average")`) within the same analysis slice, and then applies the identical weighted-Pearson calculation to those ranks. Zero-weight observations cannot affect ranks or coefficients. No imputation is used.

Cross-month matrices reshape to one row per `ibge_code × year` and use that same year's annual municipality weight. Lag-1 rows use the destination observation's annual weight; a December→January pair therefore uses the January/destination year weight. Lags never cross municipalities or bridge a missing calendar month.

Reported support fields distinguish raw observed rows, positive-weight rows, zero-weight rows, weight sum, and Kish effective sample size `(sum w)^2 / sum(w^2)`.

## Merge and weighting validation

- Weather-area municipality-year keys: exact match; no weather-only or area-only keys.
- Panel rows after merge: {len(validation.panel):,}; observation structure preserved.
- Positive-area municipality-years: {int(annual.positive_weight_municipalities.sum()):,}; explicit/numeric-zero municipality-years: {int(annual.zero_weight_municipalities.sum()):,}; unavailable municipality-years: {int(annual.unavailable_weight_municipalities.sum()):,}.
- `-` remains explicit zero with analysis weight 0; `...` remains unavailable with missing analysis weight.
- Annual weight sums: {annual.annual_weight_sum.min():.12f}–{annual.annual_weight_sum.max():.12f}; every month-year slice also sums to one.
- Positive stored EXP-01S weights agree with reconstructed weights within `1e-12`.
- Annual Kish effective sample size range: {annual.annual_kish_effective_n.min():.1f}–{annual.annual_kish_effective_n.max():.1f} municipalities.
- Every month-specific pair has 21,669 observed-weight rows, 16,570 positive-weight rows, 5,099 zero-weight rows, total weight 36, and Kish effective n 6,138.7; the 1,443 unavailable municipality-years are excluded.
- Every pooled same-month-variable pair has 260,028 observed-weight municipality-month rows, 198,840 positive-weight rows, 61,188 zero-weight rows, total weight 432, and Kish effective n 73,664.9.
- Three IBGE codes have municipality-name spelling/encoding differences across inputs; exact canonical codes match, so these are non-blocking metadata differences recorded in `municipality_name_mismatches.csv`.

The raw 642-municipality panel is retained. Unavailable weights are excluded from weighted coefficients rather than converted to zero; explicit zeros remain in validation counts but have no statistical contribution. Consequently, a later EXP-01C comparison must remember that the observed-only weighted view combines unequal weights with the approved exclusion of unavailable-area municipality-years.

## Main EXP-01B results

### Core month-specific relationships

{chr(10).join(core_lines)}

### Weighted lag-1 persistence

{chr(10).join(lag_lines)}

### Weighted cross-month persistence

{chr(10).join(cross_lines)}

Calendar-month-specific results remain primary. Pooled weighted matrices are secondary because seasonal mixing can still distort signs and magnitudes.

## Tests and commands

- Focused EXP-01B tests: **14 passed**.
- Combined EXP-01B, EXP-01A, and related weather tests: **37 passed**.
- Full repository test suite: **211 passed, 3 pre-existing warnings**.
- Main command: `py -3 -m analysis.exp01b_harvested_area_weighted_weather_correlation --project-root <repository>` with `PYTHONPATH=src`.

## Main output files

- `validation/weight_merge_validation.csv`
- `validation/municipality_name_mismatches.csv`
- `cross variable/weighted_pooled_pearson_correlation.csv`
- `cross variable/weighted_pooled_spearman_correlation.csv`
- `cross variable/weighted_monthly_pair_correlations.csv`
- `summary/weighted_core_pair_monthly_correlations.csv`
- `summary/weighted_pearson_spearman_divergence.csv`
- `summary/weighted_lag1_persistence_overall.csv`
- `summary/weighted_lag1_persistence_by_month.csv`
- `summary/weighted_cross_month_dependence_summary.csv`
- `cross month/` 12×12 matrices and support diagnostics for five variables
- `figures/` pooled, core-pair, lag-1, and cross-month heatmaps

## Warnings and interpretation limits

- These are historical descriptive weights; finalized contemporaneous target-year area weights are not automatically forecast-safe.
- The 1,443 unavailable municipality-years remain unavailable, not zero.
- Zero-weight municipalities do not influence weighted coefficients or weighted ranks.
- Weighted correlations do not prove causality, predictive redundancy, or that weighting improves yield prediction.
- No feature keep/drop decision was made, and EXP-01C was not executed.
"""
    path.write_text(text, encoding="utf-8")


def run(project_root: Path) -> int:
    weather_root = project_root / "data/processed/combined_weather/annual"
    area_path = project_root / "data/processed/analysis/exp_01s_harvested_area_weight_stability/symbol_aware_harvested_area_1990_2025.csv"
    table_root = project_root / "data/processed/analysis" / EXPERIMENT
    output_root = project_root / "outputs/experiments" / EXPERIMENT
    validation_dir = table_root / "validation"
    cross_variable_dir = table_root / "cross variable"
    cross_month_dir = table_root / "cross month"
    summary_dir = table_root / "summary"
    figure_dir = table_root / "figures"
    for folder in [validation_dir, cross_variable_dir, cross_month_dir, summary_dir, figure_dir, output_root]:
        folder.mkdir(parents=True, exist_ok=True)

    weather_validation = load_and_validate(weather_root)
    if weather_validation.gate_reasons:
        raise ValueError(f"EXP-01A weather gate no longer passes: {weather_validation.gate_reasons}")
    area = load_area_weights(area_path)
    validation = build_weighted_panel(weather_validation.data, area)
    panel = validation.panel
    validation.annual.to_csv(validation_dir / "weight_merge_validation.csv", index=False)
    validation.name_mismatches.to_csv(validation_dir / "municipality_name_mismatches.csv", index=False)

    pooled = weighted_matrices(panel, WEATHER_VARIABLES)
    filenames = {
        "pearson": "weighted_pooled_pearson_correlation.csv",
        "spearman": "weighted_pooled_spearman_correlation.csv",
        "observed_n": "weighted_pooled_pairwise_observed_n.csv",
        "positive_weight_n": "weighted_pooled_positive_weight_n.csv",
        "zero_weight_n": "weighted_pooled_zero_weight_n.csv",
        "weight_sum": "weighted_pooled_weight_sum.csv",
        "effective_n": "weighted_pooled_effective_n.csv",
    }
    for name, filename in filenames.items():
        pooled[name].to_csv(cross_variable_dir / filename)
    monthly = weighted_monthly_correlations(panel, WEATHER_VARIABLES)
    monthly.to_csv(cross_variable_dir / "weighted_monthly_pair_correlations.csv", index=False)
    core_keys = {tuple(sorted(pair)) for pair in CORE_PAIRS}
    core = monthly.loc[monthly.apply(lambda row: tuple(sorted((row.variable_x, row.variable_y))) in core_keys, axis=1)].copy()
    core.to_csv(summary_dir / "weighted_core_pair_monthly_correlations.csv", index=False)
    divergence = monthly.assign(weighted_absolute_pearson_spearman_difference=(monthly.weighted_spearman_rho - monthly.weighted_pearson_r).abs()).sort_values("weighted_absolute_pearson_spearman_difference", ascending=False)
    divergence.to_csv(summary_dir / "weighted_pearson_spearman_divergence.csv", index=False)
    lag_overall, lag_monthly = weighted_lag1(panel, LAG_VARIABLES)
    lag_overall.to_csv(summary_dir / "weighted_lag1_persistence_overall.csv", index=False)
    lag_monthly.to_csv(summary_dir / "weighted_lag1_persistence_by_month.csv", index=False)
    strongest_pairs(pooled, monthly).to_csv(summary_dir / "weighted_strongest_correlation_pairs.csv", index=False)

    all_cross: dict[str, dict[str, pd.DataFrame]] = {}
    for variable in CROSS_MONTH_VARIABLES:
        matrices = weighted_cross_month(panel, variable)
        all_cross[variable] = matrices
        for name, matrix in matrices.items():
            matrix.to_csv(cross_month_dir / f"weighted_cross_month_{variable}_{name}.csv")
        _heatmap(matrices["pearson"], f"EXP-01B weighted cross-month Pearson: {variable}", figure_dir / f"weighted_cross_month_{variable}_pearson_heatmap.png")
        _heatmap(matrices["spearman"], f"EXP-01B weighted cross-month Spearman: {variable}", figure_dir / f"weighted_cross_month_{variable}_spearman_heatmap.png")
    cross_summary = cross_month_summary(all_cross)
    cross_summary.to_csv(summary_dir / "weighted_cross_month_dependence_summary.csv", index=False)

    _heatmap(pooled["pearson"], "EXP-01B pooled weighted Pearson", figure_dir / "weighted_pooled_pearson_heatmap.png")
    _heatmap(pooled["spearman"], "EXP-01B pooled weighted Spearman", figure_dir / "weighted_pooled_spearman_heatmap.png")
    _heatmap(_core_matrix(core, "weighted_pearson_r"), "EXP-01B core pairs by month: weighted Pearson", figure_dir / "weighted_core_pairs_monthly_pearson_heatmap.png")
    _heatmap(_core_matrix(core, "weighted_spearman_rho"), "EXP-01B core pairs by month: weighted Spearman", figure_dir / "weighted_core_pairs_monthly_spearman_heatmap.png")
    _lag_bar(lag_overall, figure_dir / "weighted_lag1_persistence_overall_bar.png")
    write_report(output_root / "EXP_01B_execution_report.md", validation, area_path, weather_root, pooled, core, lag_overall, cross_summary)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
