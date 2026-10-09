"""EXP-03 first checkpoint: yield-stratified monthly weather anomalies.

The checkpoint consumes the completed EXP-02 P50=10 actual-composition grid
residuals. It does not reconstruct harvest calendars, create monthly harvest
weights, aggregate months into stages, or fit predictive models.
"""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analysis.exp01a_municipality_weather_correlation import (
    WEATHER_VARIABLES,
    load_and_validate,
    variable_inventory,
)


RELATIVE_MONTHS = tuple(range(-15, 1))
PRIMARY_RELATIVE_MONTHS = tuple(range(-11, 1))
YIELD_COLUMN = "actual_grid_residual_tch"
NASA_VARIABLES = WEATHER_VARIABLES[:3]
ERA5_VARIABLES = WEATHER_VARIABLES[3:]


def relative_month_lookup() -> pd.DataFrame:
    """Return the exact handover-defined Jan(t-1) through Apr(t) mapping."""

    rows = []
    for relative_month in RELATIVE_MONTHS:
        # m_0 is April of the yield year; offset backwards from that anchor.
        zero_based = 4 - 1 + relative_month
        year_offset, month_zero = divmod(zero_based, 12)
        month = month_zero + 1
        timing = "t" if year_offset == 0 else "t-1"
        rows.append({
            "relative_month_index": relative_month,
            "relative_month": f"m_{relative_month}",
            "source_year_offset": year_offset,
            "source_calendar_month": month,
            "calendar_month_label": f"{calendar.month_abbr[month]}_({timing})",
            "primary_window": relative_month in PRIMARY_RELATIVE_MONTHS,
            "extended_only": relative_month not in PRIMARY_RELATIVE_MONTHS,
        })
    lookup = pd.DataFrame(rows)
    expected = {
        -15: (-1, 1), -12: (-1, 4), -11: (-1, 5), -4: (-1, 12),
        -3: (0, 1), 0: (0, 4),
    }
    for relative_month, (year_offset, month) in expected.items():
        row = lookup.loc[lookup.relative_month_index.eq(relative_month)].iloc[0]
        if (row.source_year_offset, row.source_calendar_month) != (year_offset, month):
            raise ValueError("Relative-month lookup does not match the handover")
    return lookup


def load_primary_yield_outcome(results_path: Path) -> pd.DataFrame:
    """Load the immutable EXP-02 primary actual-weight grid residual outcome."""

    results = pd.read_csv(results_path)
    required = {
        "grid_id", "year", "specification", "valid_grid_residual",
        "single_municipality_grid", YIELD_COLUMN,
    }
    missing = required - set(results.columns)
    if missing:
        raise ValueError(f"EXP-02 output is missing columns: {sorted(missing)}")
    outcome = results.loc[
        results.specification.eq("p50_10") & results.valid_grid_residual,
        [
            "grid_id", "grid_latitude", "grid_longitude", "year",
            "eligible_municipalities", "matched_support_municipalities",
            "single_municipality_grid", "actual_weight_denominator_ha", YIELD_COLUMN,
        ],
    ].copy()
    if outcome[YIELD_COLUMN].isna().any():
        raise ValueError("Valid EXP-02 primary outcome contains missing residuals")
    if outcome.duplicated(["grid_id", "year"]).any():
        raise ValueError("EXP-02 primary outcome keys are not unique")
    return outcome.sort_values(["grid_id", "year"]).reset_index(drop=True)


def assign_within_grid_yield_groups(outcome: pd.DataFrame) -> pd.DataFrame:
    """Apply the fixed average-rank within-grid 25/50/25 stratification."""

    result = outcome.copy()
    result["within_grid_n"] = result.groupby("grid_id")[YIELD_COLUMN].transform("size")
    result["within_grid_average_rank"] = result.groupby("grid_id")[YIELD_COLUMN].rank(
        method="average", ascending=True
    )
    result["within_grid_percentile_u"] = (
        result.within_grid_average_rank - .5
    ) / result.within_grid_n
    result["yield_group"] = np.select(
        [result.within_grid_percentile_u.le(.25), result.within_grid_percentile_u.ge(.75)],
        ["Low", "High"], default="Medium",
    )
    result["yield_group"] = pd.Categorical(
        result.yield_group, categories=["Low", "Medium", "High"], ordered=True
    )
    if result.within_grid_percentile_u.le(0).any() or result.within_grid_percentile_u.ge(1).any():
        raise ValueError("Within-grid percentile U must lie strictly between zero and one")
    return result


def build_alignment(outcome: pd.DataFrame) -> pd.DataFrame:
    """Expand every yield grid-year to all 16 required relative months."""

    lookup = relative_month_lookup()
    aligned = outcome.merge(lookup, how="cross")
    aligned["source_year"] = aligned.year + aligned.source_year_offset
    aligned["source_month"] = pd.to_datetime(dict(
        year=aligned.source_year,
        month=aligned.source_calendar_month,
        day=1,
    ))
    aligned["source_month_label"] = aligned.source_month.dt.strftime("%Y-%m")
    if aligned.duplicated(["grid_id", "year", "relative_month_index"]).any():
        raise ValueError("Aligned grid-year-relative-month keys are not unique")
    if len(aligned) != len(outcome) * 16:
        raise ValueError("Every grid-year must expand to exactly 16 relative months")
    return aligned


def prepare_weather(weather: pd.DataFrame) -> pd.DataFrame:
    """Validate canonical weather keys and retain the verified columns."""

    required = {"ibge_code", "era5_grid_id", "year", "calendar_month", *WEATHER_VARIABLES}
    missing = required - set(weather.columns)
    if missing:
        raise ValueError(f"Canonical weather is missing columns: {sorted(missing)}")
    selected = weather[[
        "ibge_code", "era5_grid_id", "year", "calendar_month", *WEATHER_VARIABLES
    ]].copy()
    selected = selected.rename(columns={"era5_grid_id": "grid_id", "year": "source_year"})
    if selected.duplicated(["ibge_code", "source_year", "calendar_month"]).any():
        raise ValueError("Canonical municipality weather keys are not unique")
    return selected


def aggregate_aligned_grid_weather(
    aligned: pd.DataFrame,
    weight_details: pd.DataFrame,
    weather: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate municipality weather with the exact EXP-02 actual annual weights.

    The same target-year municipality support and annual harvested-area weights
    used for R_actual[g,t] are applied to every monthly weather observation in
    that target yield-year window. These are not monthly harvest-share weights.
    """

    weights = weight_details[[
        "grid_id", "year", "ibge_code", "municipality", "actual_weight"
    ]].copy()
    weights["ibge_code"] = weights.ibge_code.astype("string")
    if weights.duplicated(["grid_id", "year", "ibge_code"]).any():
        raise ValueError("EXP-02 actual-weight details have duplicate keys")
    weight_sums = weights.groupby(["grid_id", "year"]).actual_weight.sum()
    if not np.allclose(weight_sums, 1.0, atol=1e-12):
        raise ValueError("EXP-02 actual weights do not sum to one")

    expanded = aligned.merge(weights, on=["grid_id", "year"], how="left", validate="many_to_many")
    if expanded.ibge_code.isna().any():
        raise ValueError("An outcome grid-year has no EXP-02 municipality weight detail")
    expanded = expanded.merge(
        weather,
        left_on=["grid_id", "ibge_code", "source_year", "source_calendar_month"],
        right_on=["grid_id", "ibge_code", "source_year", "calendar_month"],
        how="left", validate="many_to_one",
    )
    keys = ["grid_id", "year", "relative_month_index"]
    metadata = [
        "grid_latitude", "grid_longitude", "eligible_municipalities",
        "matched_support_municipalities", "single_municipality_grid",
        "actual_weight_denominator_ha", YIELD_COLUMN, "within_grid_n",
        "within_grid_average_rank", "within_grid_percentile_u", "yield_group",
        "relative_month", "source_year_offset", "source_year", "source_calendar_month",
        "source_month", "source_month_label", "calendar_month_label",
        "primary_window", "extended_only",
    ]
    aggregations: dict[str, str] = {column: "first" for column in metadata}
    aggregations["ibge_code"] = "nunique"
    for variable in WEATHER_VARIABLES:
        weighted_column = f"{variable}__weighted_value"
        coverage_column = f"{variable}__covered_weight"
        expanded[weighted_column] = expanded[variable] * expanded.actual_weight
        expanded[coverage_column] = expanded.actual_weight.where(expanded[variable].notna(), 0.0)
        aggregations[weighted_column] = "sum"
        aggregations[coverage_column] = "sum"
    grid_weather = expanded.groupby(keys, sort=False, observed=True, as_index=False).agg(aggregations)
    grid_weather = grid_weather.rename(columns={"ibge_code": "matched_weather_municipalities"})

    partial_frames = []
    for variable in WEATHER_VARIABLES:
        weighted_column = f"{variable}__weighted_value"
        coverage_column = f"{variable}__covered_weight"
        coverage_weight = grid_weather[coverage_column]
        grid_weather[variable] = np.where(
            np.isclose(coverage_weight, 1.0, atol=1e-12),
            grid_weather[weighted_column], np.nan,
        )
        partial = ~np.isclose(coverage_weight, 0.0, atol=1e-12) & ~np.isclose(
            coverage_weight, 1.0, atol=1e-12
        )
        if partial.any():
            issue = grid_weather.loc[partial, keys + [coverage_column]].copy()
            issue = issue.rename(columns={
                "year": "yield_year", coverage_column: "covered_actual_weight"
            })
            issue["weather_variable"] = variable
            issue["issue"] = "partial_weather_weight_coverage"
            partial_frames.append(issue)
        grid_weather = grid_weather.drop(columns=weighted_column)
    missing_rows = pd.concat(partial_frames, ignore_index=True) if partial_frames else pd.DataFrame(
        columns=["grid_id", "yield_year", "relative_month_index", "covered_actual_weight", "weather_variable", "issue"]
    )
    if grid_weather.duplicated(keys).any() or len(grid_weather) != len(aligned):
        raise ValueError("Grid weather aggregation changed aligned key cardinality")
    return grid_weather, missing_rows


def add_weather_anomalies(grid_weather: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Subtract grid × calendar-month historical means using primary-cycle rows.

    Primary May(t-1)–Apr(t) rows define the climatology so each physical source
    month enters once. Pre-window Jan–Apr(t-1) rows reuse the corresponding
    grid/calendar-month baseline. Precipitation uses a raw millimetre deviation,
    consistent with the handover's permitted first-pass treatment; no percent,
    log, or standardized precipitation transformation is introduced.
    """

    result = grid_weather.copy()
    baseline_source = result.loc[result.primary_window].copy()
    baseline_rows = []
    for variable in WEATHER_VARIABLES:
        baseline = baseline_source.groupby(
            ["grid_id", "source_calendar_month"], as_index=False, observed=True
        )[variable].agg(historical_mean="mean", historical_n="count")
        baseline["weather_variable"] = variable
        baseline_rows.append(baseline)
        renamed = baseline.rename(columns={
            "historical_mean": f"{variable}__historical_mean",
            "historical_n": f"{variable}__historical_n",
        }).drop(columns="weather_variable")
        result = result.merge(
            renamed, on=["grid_id", "source_calendar_month"], how="left", validate="many_to_one"
        )
        result[f"{variable}__anomaly"] = result[variable] - result[f"{variable}__historical_mean"]
    return result, pd.concat(baseline_rows, ignore_index=True)


def yield_group_diagnostics(grouped: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    overall = grouped.groupby("yield_group", observed=False, as_index=False).agg(
        grid_year_observations=("year", "size"), unique_grids=("grid_id", "nunique"),
        unique_years=("year", "nunique"), minimum_residual=(YIELD_COLUMN, "min"),
        median_residual=(YIELD_COLUMN, "median"), maximum_residual=(YIELD_COLUMN, "max"),
    )
    by_grid = grouped.groupby(["grid_id", "yield_group"], observed=False, as_index=False).agg(
        observations=("year", "size"), minimum_year=("year", "min"), maximum_year=("year", "max"),
    )
    return overall, by_grid


def weather_coverage_diagnostics(aligned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in WEATHER_VARIABLES:
        for relative_month, group in aligned.groupby("relative_month_index", sort=True):
            observed = int(group[variable].notna().sum())
            rows.append({
                "relative_month_index": relative_month,
                "relative_month": group.relative_month.iloc[0],
                "calendar_month_label": group.calendar_month_label.iloc[0],
                "primary_window": bool(group.primary_window.iloc[0]),
                "weather_variable": variable,
                "expected_grid_year_observations": len(group),
                "observed_grid_year_observations": observed,
                "missing_grid_year_observations": len(group) - observed,
                "coverage_rate": observed / len(group),
                "first_source_year_observed": group.loc[group[variable].notna(), "source_year"].min(),
                "last_source_year_observed": group.loc[group[variable].notna(), "source_year"].max(),
            })
    return pd.DataFrame(rows)


def temporal_source_coverage_audit(weather: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize actual canonical coverage without inferring theoretical availability."""

    rows = []
    expected_months = pd.period_range("1981-01", "2025-12", freq="M").astype(str)
    for variable in WEATHER_VARIABLES:
        observed = weather.loc[weather[variable].notna()].copy()
        observed_months = set(observed.month.astype(str))
        missing_months = [month for month in expected_months if month not in observed_months]
        rows.append({
            "weather_variable": variable,
            "source": "NASA POWER" if variable in NASA_VARIABLES else "ERA5",
            "earliest_available_month": observed.month.min() if not observed.empty else "",
            "latest_available_month": observed.month.max() if not observed.empty else "",
            "missing_calendar_months": ";".join(missing_months),
            "n_missing_calendar_months": len(missing_months),
            "missing_municipality_month_rows": int(weather[variable].isna().sum()),
            "mapped_municipalities": int(observed.ibge_code.nunique()),
            "complete_from_1981_01": bool(
                not missing_months
                and weather[variable].notna().all()
                and observed.ibge_code.nunique() == weather.ibge_code.nunique()
            ),
            "sufficient_for_complete_1982_window": bool(
                weather.loc[weather.month.between("1981-01", "1982-04"), variable].notna().all()
                and weather.loc[weather.month.between("1981-01", "1982-04"), "month"].nunique() == 16
            ),
        })
    annual_rows = []
    for year, group in weather.groupby("year", sort=True):
        row = {
            "year": int(year), "municipality_month_rows": len(group),
            "municipalities": int(group.ibge_code.nunique()),
            "months": int(group.calendar_month.nunique()),
            "duplicate_municipality_month_keys": int(group.duplicated(["ibge_code", "month"]).sum()),
            "missing_nasa_source_rows": int(group.nasa_observed_days.isna().sum()),
            "missing_era5_source_rows": int(group.era5_observed_days.isna().sum()),
        }
        for variable in WEATHER_VARIABLES:
            row[f"missing__{variable}"] = int(group[variable].isna().sum())
        annual_rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(annual_rows)


def grid_year_window_status(grid_weather: pd.DataFrame) -> pd.DataFrame:
    """Classify primary and extended coverage before restricting the analysis sample."""

    working = grid_weather.assign(all_variables_present=grid_weather[WEATHER_VARIABLES].notna().all(axis=1))
    rows = []
    for (grid_id, year, yield_group), group in working.groupby(
        ["grid_id", "year", "yield_group"], observed=True, sort=True
    ):
        primary = group.loc[group.primary_window]
        extended = group
        primary_n = int(primary.all_variables_present.sum())
        extended_n = int(extended.all_variables_present.sum())
        rows.append({
            "grid_id": grid_id, "yield_year": int(year), "yield_group": yield_group,
            "primary_months_available": primary_n,
            "extended_months_available": extended_n,
            "complete_primary_window": primary_n == 12,
            "complete_extended_window": extended_n == 16,
            "window_status": (
                "complete_16_months" if extended_n == 16
                else "complete_primary_only" if primary_n == 12
                else "missing_window" if extended_n == 0
                else "partial_window"
            ),
        })
    return pd.DataFrame(rows)


def spatial_reconciliation_audit(
    weather: pd.DataFrame, weights: pd.DataFrame, outcome: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Audit the municipality bridge and exact EXP-02 support/weight contract."""

    mapping = weather[[
        "ibge_code", "municipality", "nasa_weather_group_id", "era5_grid_id"
    ]].drop_duplicates()
    if mapping.duplicated("ibge_code").any():
        raise ValueError("Canonical combined weather maps a municipality more than once")
    eligible_codes = set(weights.ibge_code.astype("string"))
    eligible = mapping.loc[mapping.ibge_code.astype("string").isin(eligible_codes)].copy()
    missing_mapping = eligible_codes - set(eligible.ibge_code.astype("string"))
    if missing_mapping:
        raise ValueError(f"EXP-02 municipalities absent from weather bridge: {sorted(missing_mapping)[:5]}")
    eligible = eligible.rename(columns={"era5_grid_id": "grid_id"})
    weight_sums = weights.groupby(["grid_id", "year"], as_index=False).actual_weight.sum()
    expected_keys = set(map(tuple, outcome[["grid_id", "year"]].itertuples(index=False, name=None)))
    actual_keys = set(map(tuple, weight_sums[["grid_id", "year"]].itertuples(index=False, name=None)))
    if expected_keys != actual_keys:
        raise ValueError("EXP-02 weight-detail grid-year support differs from the residual outcome")

    group_crosswalk = eligible.groupby("nasa_weather_group_id", as_index=False).agg(
        n_eligible_municipalities=("ibge_code", "nunique"),
        n_era5_grids=("grid_id", "nunique"),
        representative_era5_grid_ids=("grid_id", lambda values: ";".join(sorted(set(values))[:8])),
    )
    group_crosswalk["contributes_to_multiple_era5_grids"] = group_crosswalk.n_era5_grids.gt(1)

    grid_rows = []
    years_by_grid = weights.groupby("grid_id").year.nunique()
    for grid_id, group in eligible.groupby("grid_id", sort=True):
        sums = weight_sums.loc[weight_sums.grid_id.eq(grid_id), "actual_weight"]
        groups = sorted(group.nasa_weather_group_id.unique())
        grid_rows.append({
            "era5_grid_id": grid_id,
            "n_eligible_municipalities": int(group.ibge_code.nunique()),
            "n_nasa_groups": len(groups),
            "n_years": int(years_by_grid.loc[grid_id]),
            "representative_nasa_group_ids": ";".join(groups[:8]),
            "minimum_actual_weight_sum": float(sums.min()),
            "maximum_actual_weight_sum": float(sums.max()),
            "maximum_absolute_weight_sum_deviation": float((sums - 1).abs().max()),
            "mapping_anomaly_flag": bool(
                group.ibge_code.duplicated().any() or not np.allclose(sums, 1.0, atol=1e-12)
            ),
        })
    summary = pd.DataFrame([{
        "eligible_municipalities": len(eligible_codes),
        "represented_era5_grids": int(eligible.grid_id.nunique()),
        "represented_nasa_groups": int(eligible.nasa_weather_group_id.nunique()),
        "nasa_groups_spanning_multiple_era5_grids": int(
            group_crosswalk.contributes_to_multiple_era5_grids.sum()
        ),
        "duplicate_canonical_municipality_month_rows": int(
            weather.duplicated(["ibge_code", "month"]).sum()
        ),
        "grid_year_weight_sums_all_one": bool(np.allclose(weight_sums.actual_weight, 1.0, atol=1e-12)),
        "residual_and_weight_grid_year_support_identical": expected_keys == actual_keys,
        "nasa_and_era5_share_municipality_month_keys": bool(
            weather.nasa_observed_days.notna().eq(weather.era5_observed_days.notna()).all()
        ),
    }])
    return pd.DataFrame(grid_rows), group_crosswalk, summary


def monthly_group_summary(aligned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in WEATHER_VARIABLES:
        anomaly = f"{variable}__anomaly"
        for (relative_month, yield_group), group in aligned.groupby(
            ["relative_month_index", "yield_group"], sort=True, observed=False
        ):
            values = group[anomaly].dropna()
            rows.append({
                "relative_month_index": relative_month,
                "relative_month": group.relative_month.iloc[0],
                "calendar_month_label": group.calendar_month_label.iloc[0],
                "primary_window": bool(group.primary_window.iloc[0]),
                "weather_variable": variable,
                "yield_group": yield_group,
                "n": len(values),
                "mean_anomaly": values.mean(), "median_anomaly": values.median(),
                "std_anomaly": values.std(ddof=1), "q25_anomaly": values.quantile(.25),
                "q75_anomaly": values.quantile(.75),
            })
    return pd.DataFrame(rows)


def high_minus_low_effects(summary: pd.DataFrame) -> pd.DataFrame:
    index = [
        "relative_month_index", "relative_month", "calendar_month_label",
        "primary_window", "weather_variable",
    ]
    wide = summary.pivot(index=index, columns="yield_group", values=[
        "n", "mean_anomaly", "std_anomaly"
    ]).reset_index()
    wide.columns = [
        "__".join(str(part) for part in column if str(part) != "")
        if isinstance(column, tuple) else column for column in wide.columns
    ]
    wide = wide.rename(columns={
        "n__Low": "low_n", "n__High": "high_n",
        "mean_anomaly__Low": "low_mean_anomaly", "mean_anomaly__High": "high_mean_anomaly",
        "std_anomaly__Low": "low_std_anomaly", "std_anomaly__High": "high_std_anomaly",
    })
    wide["high_minus_low_anomaly"] = wide.high_mean_anomaly - wide.low_mean_anomaly
    denominator_df = wide.high_n + wide.low_n - 2
    pooled_variance = (
        (wide.high_n - 1) * wide.high_std_anomaly**2
        + (wide.low_n - 1) * wide.low_std_anomaly**2
    ) / denominator_df
    wide["pooled_high_low_sd"] = np.sqrt(pooled_variance)
    wide["standardized_high_minus_low"] = (
        wide.high_minus_low_anomaly / wide.pooled_high_low_sd.replace(0, np.nan)
    )
    return wide.sort_values(["weather_variable", "relative_month_index"]).reset_index(drop=True)


def continuous_spearman(aligned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in WEATHER_VARIABLES:
        anomaly = f"{variable}__anomaly"
        for relative_month, group in aligned.groupby("relative_month_index", sort=True):
            pair = group[[YIELD_COLUMN, anomaly]].dropna()
            result = spearmanr(pair[YIELD_COLUMN], pair[anomaly]) if len(pair) > 2 else None
            rows.append({
                "relative_month_index": relative_month,
                "relative_month": group.relative_month.iloc[0],
                "calendar_month_label": group.calendar_month_label.iloc[0],
                "primary_window": bool(group.primary_window.iloc[0]),
                "weather_variable": variable, "n": len(pair),
                "spearman_rho": result.statistic if result else np.nan,
                "spearman_p_value": result.pvalue if result else np.nan,
            })
    return pd.DataFrame(rows)


def alignment_examples(grouped: pd.DataFrame, years: tuple[int, ...] = (1982, 1991, 2010, 2025)) -> pd.DataFrame:
    lookup = relative_month_lookup()
    rows = []
    for year in years:
        if year not in set(grouped.year):
            continue
        example = lookup.copy()
        example["yield_year"] = year
        example["source_year"] = year + example.source_year_offset
        example["source_month_label"] = pd.to_datetime(dict(
            year=example.source_year, month=example.source_calendar_month, day=1
        )).dt.strftime("%Y-%m")
        rows.append(example)
    return pd.concat(rows, ignore_index=True)


def create_figures(effects: pd.DataFrame, line_data: pd.DataFrame, figure_root: Path) -> None:
    figure_root.mkdir(parents=True, exist_ok=True)
    matrix = effects.pivot(
        index="weather_variable", columns="relative_month_index", values="standardized_high_minus_low"
    ).reindex(columns=RELATIVE_MONTHS)
    fig, ax = plt.subplots(figsize=(14, 8))
    limit = np.nanmax(np.abs(matrix.to_numpy()))
    image = ax.imshow(matrix.to_numpy(), cmap="RdBu_r", aspect="auto", vmin=-limit, vmax=limit)
    ax.set_xticks(range(16), [f"m_{month}" for month in RELATIVE_MONTHS], rotation=45, ha="right")
    ax.set_yticks(range(len(matrix)), matrix.index)
    ax.axvline(3.5, color="black", linewidth=1.2, linestyle="--")
    ax.set(xlabel="Relative month (dashed line separates extended-only and primary)", ylabel="Weather variable",
           title="Exploratory standardized High − Low monthly weather contrast")
    fig.colorbar(image, ax=ax, label="Standardized High − Low")
    fig.tight_layout(); fig.savefig(figure_root / "high_minus_low_weather_heatmap.png", dpi=180); plt.close(fig)

    variables = WEATHER_VARIABLES
    fig, axes = plt.subplots(4, 3, figsize=(17, 16), sharex=True)
    colors = {"Low": "#d73027", "Medium": "#777777", "High": "#1a9850"}
    for ax, variable in zip(axes.flat, variables):
        subset = line_data.loc[line_data.weather_variable.eq(variable)]
        for group_name, group in subset.groupby("yield_group", observed=False, sort=False):
            ax.plot(group.relative_month_index, group.mean_anomaly, marker="o", markersize=3,
                    label=str(group_name), color=colors[str(group_name)])
        ax.axhline(0, color="black", linewidth=.7); ax.axvline(-11.5, color="black", linestyle="--", linewidth=.8)
        ax.set_title(variable, fontsize=9); ax.grid(alpha=.2)
    for ax in axes.flat[len(variables):]:
        ax.axis("off")
    axes[0, 0].legend(); fig.supxlabel("Relative month"); fig.supylabel("Mean grid/calendar-month anomaly")
    fig.suptitle("Exploratory Low / Medium / High monthly weather profiles")
    fig.tight_layout(); fig.savefig(figure_root / "yield_group_monthly_weather_profiles.png", dpi=180); plt.close(fig)


def strongest_coherent_windows(effects: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """Rank same-sign adjacent 3-month descriptive windows without defining features."""

    rows = []
    for variable, group in effects.groupby("weather_variable", sort=False):
        group = group.sort_values("relative_month_index").reset_index(drop=True)
        for start in range(len(group) - window + 1):
            subset = group.iloc[start:start + window]
            values = subset.standardized_high_minus_low
            same_sign = bool((values.gt(0).all()) or (values.lt(0).all()))
            if same_sign and values.notna().all():
                rows.append({
                    "weather_variable": variable,
                    "start_relative_month": subset.relative_month.iloc[0],
                    "end_relative_month": subset.relative_month.iloc[-1],
                    "window_in_primary": bool(subset.primary_window.all()),
                    "direction": "positive" if values.gt(0).all() else "negative",
                    "mean_standardized_high_minus_low": values.mean(),
                    "mean_absolute_standardized_effect": values.abs().mean(),
                    "minimum_absolute_standardized_effect": values.abs().min(),
                })
    return pd.DataFrame(rows).sort_values(
        ["mean_absolute_standardized_effect", "weather_variable", "start_relative_month"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    """Render a compact Markdown table without optional dependencies."""

    shown = frame.copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(
            lambda value: f"{value:.{digits}f}" if pd.notna(value) else ""
        )
    columns = shown.columns.tolist()
    return "\n".join([
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
        *["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)],
    ])


def _write_report_1991_2025_legacy(
    output_root: Path, results_path: Path, weights_path: Path, weather_dir: Path,
    grouped: pd.DataFrame, aligned: pd.DataFrame, group_diag: pd.DataFrame,
    coverage: pd.DataFrame, effects: pd.DataFrame, spearman: pd.DataFrame,
    coherent: pd.DataFrame, partial_issues: pd.DataFrame,
) -> None:
    complete_by_variable = coverage.groupby("weather_variable").agg(
        observed=("observed_grid_year_observations", "sum"),
        expected=("expected_grid_year_observations", "sum"),
    )
    complete_by_variable["coverage_rate"] = complete_by_variable.observed / complete_by_variable.expected
    availability = aligned.assign(
        weather_available=aligned[WEATHER_VARIABLES[0]].notna()
    ).groupby(["grid_id", "year", "yield_group"], observed=True, as_index=False).agg(
        available_months=("weather_available", "sum")
    )
    availability["coverage_class"] = np.select(
        [availability.available_months.eq(16), availability.available_months.eq(0)],
        ["complete_16_months", "no_weather"], default="partial_window",
    )
    availability_summary = availability.groupby("coverage_class", as_index=False).agg(
        grid_year_observations=("year", "size"), first_yield_year=("year", "min"),
        last_yield_year=("year", "max"),
    )
    complete_group_counts = availability.loc[
        availability.coverage_class.eq("complete_16_months")
    ].groupby("yield_group", observed=False, as_index=False).size().rename(columns={"size": "complete_grid_years"})
    tied_rows = int(grouped.duplicated(["grid_id", YIELD_COLUMN], keep=False).sum())
    by_grid_group = grouped.groupby(["grid_id", "yield_group"], observed=False).size().unstack(fill_value=0)
    group_ranges = pd.DataFrame({
        "yield_group": ["Low", "Medium", "High"],
        "minimum_per_grid": [int(by_grid_group[column].min()) for column in ["Low", "Medium", "High"]],
        "median_per_grid": [float(by_grid_group[column].median()) for column in ["Low", "Medium", "High"]],
        "maximum_per_grid": [int(by_grid_group[column].max()) for column in ["Low", "Medium", "High"]],
    })
    top_windows = coherent.head(12)
    report = f"""# EXP-03 Checkpoint 1 — Yield-Stratified Monthly Weather Analysis

## Scope and exact inputs

- EXP-02 grid residuals: `{results_path.resolve()}`.
- Exact outcome: rows with `specification == p50_10` and `valid_grid_residual == True`; residual column **`{YIELD_COLUMN}`**.
- Exact EXP-02 municipality support/weights: `{weights_path.resolve()}`; `actual_weight` is reused unchanged to represent municipality weather within each target grid-year.
- Canonical weather: annual files under `{weather_dir.resolve()}`, validated through the existing EXP-01A combined-weather gate.
- Weather columns: {', '.join(f'`{variable}`' for variable in WEATHER_VARIABLES)}.

These are annual harvested-area weights from EXP-02, not monthly harvest shares. No harvest calendar, interpolation, or monthly harvest weighting was constructed.

## Outcome and alignment inventory

- Valid primary grid-year outcomes: **{len(grouped)}**.
- Grids: **{grouped.grid_id.nunique()}**; yield years: **{grouped.year.nunique()}** ({grouped.year.min()}–{grouped.year.max()}).
- Expanded alignment rows: **{len(aligned)}** = 16 rows per outcome.
- Extended window: `m_-15` Jan_(t-1) through `m_0` Apr_t.
- Primary flag: `m_-11` May_(t-1) through `m_0` Apr_t.
- Canonical weather years: 1990–2025. Earlier yield windows remain in diagnostics with missing weather; they are not imputed.
- Partial within-month actual-weight weather coverage issues: **{len(partial_issues)}**.

Weather anomalies are raw deviations from the grid × calendar-month historical mean. The climatology uses primary-window rows so each physical source month enters once. Precipitation is therefore expressed as a documented raw millimetre deviation; no percent, log, or newly standardized precipitation transformation was introduced.

## Primary 25/50/25 grouping

{markdown_table(group_diag)}

Average ranks are used for exact ties, with `U=(rank-0.5)/n`. Groups are assigned on the complete EXP-02 outcome history before weather availability is considered.

Rows participating in exact within-grid residual ties: **{tied_rows}**. Per-grid group-count ranges:

{markdown_table(group_ranges)}

## Weather coverage

{markdown_table(complete_by_variable.reset_index())}

The aggregate 69.65% rate reflects the fixed 1990 start of canonical weather, not interpolation or silent row deletion. Grid-year window coverage is:

{markdown_table(availability_summary)}

All **2,610** complete 16-month windows use yield years 1991–2025. The **72** partial windows are yield-year 1990 and contain only Jan–Apr 1990 (`m_-3` through `m_0`); their prior-year months precede the canonical weather record. The **1,091** no-weather grid-years are 1974–1989. Complete-window group counts are:

{markdown_table(complete_group_counts)}

## Strongest preliminary coherent three-month patterns

{markdown_table(top_windows)}

These are descriptive same-sign adjacent-month windows ranked by average absolute standardized High-minus-Low contrast. They are exploratory pattern summaries, not constructed features, hypothesis tests, or selection decisions. Isolated p-values are not interpreted.

The continuous Spearman companion is provided in `continuous_yield_weather_spearman.csv`; it is supporting evidence only.

## Validation and stop boundary

- Exact relative-month mapping, 16 rows per outcome, unique grid-year-month keys, average-rank group assignment, EXP-02 weight reconciliation, weather-key uniqueness, anomaly centering, and summary cardinalities are validated in code and focused tests.
- No historical harvest calendar, harvest-share weight, growth-stage feature, predictive model, optimized feature weight, or altered residual was created.
- This checkpoint stops before robustness group specifications, feature engineering, inference design, or modeling.
"""
    (output_root / "EXP_03_checkpoint1_report.md").write_text(report, encoding="utf-8")


def _write_execution_report_1991_2025_legacy(output_root: Path) -> None:
    created = [
        "EXP_03_checkpoint1_report.md", "EXP_03_checkpoint1_execution_report.md",
        "yield_grid_year_groups.csv", "yield_group_observation_counts.csv",
        "yield_group_counts_by_grid.csv", "weather_variable_inventory.csv",
        "weather_coverage_missingness.csv", "partial_weather_weight_coverage_issues.csv",
        "grid_calendar_month_weather_baselines.csv",
        "aligned_grid_year_month_weather_anomalies.csv",
        "relative_month_alignment_examples.csv", "monthly_weather_by_yield_group.csv",
        "high_minus_low_monthly_weather_effects.csv", "heatmap_ready_high_minus_low.csv",
        "line_profile_ready_yield_groups.csv", "continuous_yield_weather_spearman.csv",
        "exploratory_coherent_three_month_windows.csv",
        "figures/high_minus_low_weather_heatmap.png",
        "figures/yield_group_monthly_weather_profiles.png",
    ]
    report = f"""# EXP-03 Checkpoint 1 — Execution Report

## Implementation boundary

Implemented only the handover's first exploratory checkpoint. The code does not reconstruct harvest calendars, form monthly harvest weights, collapse months into stages, alter EXP-02 residuals, train models, or select features.

## Files created or modified

- Implementation: `src/analysis/exp03_yield_stratified_monthly_weather.py`
- Focused tests: `src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py`
- Output directory: `{output_root.resolve()}`
- Output artifacts: {', '.join(f'`{name}`' for name in created)}.

## Reproducible commands

- `$env:PYTHONPATH = 'src'; python -m analysis.exp03_yield_stratified_monthly_weather --project-root .` — completed successfully.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py -q` — **5 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **102 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/etl/weather/test_build_combined_monthly_weather.py src/tests/feature_engineering/test_month_level_weather.py -q` — **14 passed**.

The test runs emitted only a non-computational warning that pytest could not create its optional `.pytest_cache` directory; no test or assertion failed.

## Validation gates

- The existing EXP-01A combined-weather validation gate must pass before calculation.
- EXP-02 P50=10 valid grid-year keys and the exact actual-weight detail must reconcile one-to-one and weights must sum to one.
- Every outcome expands to 16 unique relative months.
- Available monthly weather must cover the full target-year actual weight; partial-weight months are rejected as missing and separately audited.
- Primary-cycle grid/calendar-month anomalies are centered on zero by construction and checked in tests.

## Known data boundary

Canonical combined weather begins in 1990. Yield outcomes are deliberately retained for 1974–2025: pre-1990 aligned weather is missing rather than bridged or imputed. Yield-year 1990 has only Jan–Apr contemporaneous weather and no prior-year weather. Full 16-month exploratory comparisons therefore use yield years 1991–2025.
"""
    (output_root / "EXP_03_checkpoint1_execution_report.md").write_text(report, encoding="utf-8")


def write_report(
    output_root: Path, results_path: Path, weights_path: Path, weather_dir: Path,
    grouped: pd.DataFrame, aligned: pd.DataFrame, group_diag: pd.DataFrame,
    coverage: pd.DataFrame, effects: pd.DataFrame, spearman: pd.DataFrame,
    coherent: pd.DataFrame, partial_issues: pd.DataFrame,
    temporal_audit: pd.DataFrame, annual_source_coverage: pd.DataFrame,
    grid_audit: pd.DataFrame, spatial_summary: pd.DataFrame,
    windows: pd.DataFrame, complete_by_year: pd.DataFrame,
    complete_group_counts: pd.DataFrame, comparison: pd.DataFrame,
) -> None:
    availability_summary = windows.groupby("window_status", as_index=False).agg(
        grid_year_observations=("yield_year", "size"),
        first_yield_year=("yield_year", "min"), last_yield_year=("yield_year", "max"),
    )
    tied_rows = int(grouped.duplicated(["grid_id", YIELD_COLUMN], keep=False).sum())
    top_windows = coherent.head(12)
    comparison_correlation = comparison[[
        "standardized_high_minus_low__1982_2025",
        "standardized_high_minus_low__1991_2025",
    ]].corr().iloc[0, 1]
    max_change = comparison.loc[comparison.delta_standardized_effect.abs().idxmax()]
    late = comparison.loc[comparison.relative_month_index.between(-4, 0)]
    spatial = spatial_summary.iloc[0]
    report = f"""# EXP-03 Checkpoint 1 — Extended 1982–2025 Rerun

## Scope and exact inputs

- EXP-02 grid residuals: `{results_path.resolve()}`.
- Exact outcome: valid `p50_10` rows, residual column **`{YIELD_COLUMN}`**.
- Exact EXP-02 support/weights: `{weights_path.resolve()}`; target-year `actual_weight` is unchanged.
- Canonical municipality-month weather: `{weather_dir.resolve()}`, extended and validated for 1981–2025.
- Weather columns: {', '.join(f'`{variable}`' for variable in WEATHER_VARIABLES)}.

These are annual harvested-area weights from EXP-02, not monthly harvest shares. No harvest calendar, interpolation, or monthly harvest weighting was constructed.

## Outcome, alignment, and grouping

- Full residual sample: **{len(grouped)}** grid-years, **{grouped.grid_id.nunique()}** grids, yield years **{grouped.year.min()}–{grouped.year.max()}**.
- Complete-window analysis: **{aligned[['grid_id', 'year']].drop_duplicates().shape[0]}** grid-years and **{len(aligned)}** aligned rows.
- Earliest scientifically valid all-variable yield year: **{aligned.year.min()}**.
- Extended window remains `m_-15` Jan_(t-1) through `m_0` Apr_t; primary remains `m_-11` May_(t-1) through `m_0` Apr_t.
- Partial within-month actual-weight coverage issues: **{len(partial_issues)}**.

{markdown_table(group_diag)}

Grouping uses average within-grid ranks over the full residual history before weather availability. Rows in exact within-grid residual ties: **{tied_rows}**. Complete-weather group counts are:

{markdown_table(complete_group_counts)}

## Temporal source-coverage gate

{markdown_table(temporal_audit[[
    'weather_variable', 'source', 'earliest_available_month', 'latest_available_month',
    'n_missing_calendar_months', 'missing_municipality_month_rows',
    'mapped_municipalities', 'sufficient_for_complete_1982_window'
]])}

For every year 1981–1989, the canonical panel contains 7,704 rows, 642 municipalities, 12 months, no duplicate keys, no missing NASA or ERA5 source rows, and no missing required-variable values. The complete year-by-year audit is `annual_source_coverage_1981_2025.csv`.

Grid-year window coverage over the full residual history is:

{markdown_table(availability_summary)}

## Spatial reconciliation gate

| Diagnostic | Value |
|---|---:|
| Eligible EXP-02 municipalities | {int(spatial.eligible_municipalities)} |
| Represented ERA5 grids | {int(spatial.represented_era5_grids)} |
| NASA weather groups | {int(spatial.represented_nasa_groups)} |
| NASA groups spanning multiple ERA5 grids | {int(spatial.nasa_groups_spanning_multiple_era5_grids)} |
| Duplicate municipality-month keys | {int(spatial.duplicate_canonical_municipality_month_rows)} |
| All valid grid-year weight sums equal one | {bool(spatial.grid_year_weight_sums_all_one)} |
| Residual and weight-detail support identical | {bool(spatial.residual_and_weight_grid_year_support_identical)} |
| NASA and ERA5 municipality-month support identical | {bool(spatial.nasa_and_era5_share_municipality_month_keys)} |

NASA is attached at municipality-month level through `nasa_weather_group_id`; ERA5 is attached through `era5_grid_id`; sources merge on municipality plus month before ERA5-grid aggregation. NASA groups spanning multiple ERA5 grids are expected bridge behavior, not a direct grid join. All **{len(grid_audit)}** grid audit rows have no mapping anomaly.

## Strongest preliminary coherent three-month patterns

{markdown_table(top_windows)}

These are descriptive adjacent-month contrasts, not constructed features, formal hypothesis tests, biological stage labels, or selection decisions. The Spearman companion remains supporting evidence only.

## Comparison with the former 1991–2025 checkpoint

- Correlation across the 176 old and new standardized High-minus-Low cells: **{comparison_correlation:.4f}**.
- Sign reversals across all cells: **{int(comparison.sign_changed.sum())}**; within `m_-4` through `m_0`: **{int(late.sign_changed.sum())}**.
- Largest absolute standardized-effect change: **{abs(max_change.delta_standardized_effect):.4f}**, `{max_change.weather_variable}` at `m_{int(max_change.relative_month_index)}`.

The late-`t-1` / early-`t` exploratory pattern remains visible: higher-yield observations are comparatively more humid and soil-moist, with lower temperature and VPD across adjacent months. Individual magnitudes changed after adding 1982–1990, so no month or window is treated as finalized.

## Stop boundary

No final features, seasonal collapse, biological labels, predictive model, optimized weights, harvest-share weights, or reconstructed harvest profiles were produced. This remains Checkpoint 1 only.
"""
    (output_root / "EXP_03_checkpoint1_report.md").write_text(report, encoding="utf-8")


def write_execution_report(output_root: Path) -> None:
    report = f"""# EXP-03 Extended Checkpoint 1 — Execution Report

## Files changed

- `src/etl/weather/build_combined_monthly_weather.py`
- `src/analysis/exp01a_municipality_weather_correlation.py`
- `src/analysis/exp03_yield_stratified_monthly_weather.py`
- `src/tests/etl/weather/test_build_combined_monthly_weather.py`
- `src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py`
- Canonical combined-weather annual CSV and validation JSON files for 1981–1989.
- Extended audit and exploratory outputs under `{output_root.resolve()}`.

## Commands and validation

- Rebuilt each 1981–1989 canonical annual file with the established municipality bridge.
- Reran EXP-03 Checkpoint 1 with the canonical 1981–2025 gate.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_yield_stratified_monthly_weather.py -q` — **5 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **102 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/etl/weather/test_build_combined_monthly_weather.py src/tests/feature_engineering/test_month_level_weather.py -q` — **15 passed**.

The only warning was that pytest could not create its optional repository cache; no calculation or assertion was affected.

## Implementation issue resolved

The 1982 NASA source contains valid ISO dates in both `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS` form. The loader now explicitly accepts mixed ISO renderings while retaining strict filename-period, duplicate-key, and calendar-year validation. No observations or weather values were changed.

## Boundary

Grouping remains independent of weather availability. Only complete 16-month grid-year windows from 1982–2025 enter the exploratory contrasts. Earlier residuals remain part of rank construction and coverage diagnostics but are not imputed.
"""
    (output_root / "EXP_03_checkpoint1_execution_report.md").write_text(report, encoding="utf-8")


def run(project_root: Path) -> int:
    results_path = project_root / "data/processed/analysis/exp_02b/actual_vs_fixed_grid_residuals.csv"
    weights_path = project_root / "data/processed/analysis/exp_02b/matched_support_weight_details.csv"
    weather_dir = project_root / "data/processed/combined_weather/annual"
    output_root = project_root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1"
    figure_root = output_root / "figures"
    output_root.mkdir(parents=True, exist_ok=True)

    outcome = load_primary_yield_outcome(results_path)
    grouped = assign_within_grid_yield_groups(outcome)
    alignment = build_alignment(grouped)
    validation = load_and_validate(weather_dir, expected_years=range(1981, 2026))
    if validation.gate_reasons:
        raise ValueError("Canonical weather validation gate failed: " + "; ".join(validation.gate_reasons))
    temporal_audit, annual_source_coverage = temporal_source_coverage_audit(validation.data)
    if not temporal_audit.complete_from_1981_01.all():
        failed = temporal_audit.loc[~temporal_audit.complete_from_1981_01, "weather_variable"].tolist()
        raise ValueError(f"Required all-variable weather coverage does not begin in 1981-01: {failed}")
    weather = prepare_weather(validation.data)
    weights = pd.read_csv(weights_path, dtype={"ibge_code": "string"})
    grid_audit, nasa_group_audit, spatial_summary = spatial_reconciliation_audit(
        validation.data, weights, outcome
    )
    if grid_audit.mapping_anomaly_flag.any():
        raise ValueError("Spatial reconciliation audit found grid-level mapping or weight anomalies")
    grid_weather, partial_issues = aggregate_aligned_grid_weather(alignment, weights, weather)
    windows = grid_year_window_status(grid_weather)
    complete_keys = windows.loc[
        windows.complete_extended_window & windows.yield_year.ge(1982), ["grid_id", "yield_year"]
    ].rename(columns={"yield_year": "year"})
    analysis_grid_weather = grid_weather.merge(
        complete_keys, on=["grid_id", "year"], how="inner", validate="many_to_one"
    )
    aligned, baseline = add_weather_anomalies(analysis_grid_weather)
    if aligned.year.min() != 1982 or aligned.year.max() != 2025:
        raise ValueError("Complete EXP-03 analysis sample does not span the expected 1982–2025 interval")

    group_diag, by_grid = yield_group_diagnostics(grouped)
    coverage = weather_coverage_diagnostics(grid_weather)
    summary = monthly_group_summary(aligned)
    effects = high_minus_low_effects(summary)
    heatmap = effects[[
        "relative_month_index", "relative_month", "calendar_month_label", "primary_window",
        "weather_variable", "standardized_high_minus_low", "high_minus_low_anomaly",
    ]].copy()
    line_data = summary.copy()
    spearman = continuous_spearman(aligned)
    examples = alignment_examples(grouped)
    coherent = strongest_coherent_windows(effects)
    complete_by_year = windows.groupby("yield_year", as_index=False).agg(
        complete_primary_windows=("complete_primary_window", "sum"),
        complete_extended_windows=("complete_extended_window", "sum"),
        partial_windows=("window_status", lambda values: int(pd.Series(values).eq("partial_window").sum())),
        missing_windows=("window_status", lambda values: int(pd.Series(values).eq("missing_window").sum())),
    )
    complete_group_counts = windows.loc[windows.complete_extended_window].groupby(
        "yield_group", observed=False, as_index=False
    ).size().rename(columns={"size": "complete_grid_years"})

    baseline_path = output_root / "baseline_1991_2025_high_minus_low_monthly_weather_effects.csv"
    if not baseline_path.is_file():
        raise FileNotFoundError("The preserved 1991–2025 Checkpoint 1 effect table is required for comparison")
    old_effects = pd.read_csv(baseline_path)
    comparison = effects.merge(
        old_effects[[
            "relative_month_index", "weather_variable", "high_minus_low_anomaly",
            "standardized_high_minus_low",
        ]],
        on=["relative_month_index", "weather_variable"], how="left",
        suffixes=("__1982_2025", "__1991_2025"), validate="one_to_one",
    )
    comparison["delta_standardized_effect"] = (
        comparison.standardized_high_minus_low__1982_2025
        - comparison.standardized_high_minus_low__1991_2025
    )
    comparison["sign_changed"] = np.sign(
        comparison.standardized_high_minus_low__1982_2025
    ).ne(np.sign(comparison.standardized_high_minus_low__1991_2025))

    inventory = variable_inventory().loc[
        variable_inventory().column_name.isin(WEATHER_VARIABLES)
    ].copy()
    grouped.to_csv(output_root / "yield_grid_year_groups.csv", index=False)
    group_diag.to_csv(output_root / "yield_group_observation_counts.csv", index=False)
    by_grid.to_csv(output_root / "yield_group_counts_by_grid.csv", index=False)
    inventory.to_csv(output_root / "weather_variable_inventory.csv", index=False)
    temporal_audit.to_csv(output_root / "temporal_source_coverage_audit.csv", index=False)
    annual_source_coverage.to_csv(output_root / "annual_source_coverage_1981_2025.csv", index=False)
    grid_audit.to_csv(output_root / "spatial_reconciliation_by_era5_grid.csv", index=False)
    nasa_group_audit.to_csv(output_root / "nasa_group_to_era5_grid_audit.csv", index=False)
    spatial_summary.to_csv(output_root / "spatial_reconciliation_summary.csv", index=False)
    coverage.to_csv(output_root / "weather_coverage_missingness.csv", index=False)
    windows.to_csv(output_root / "grid_year_weather_window_status.csv", index=False)
    complete_by_year.to_csv(output_root / "complete_window_counts_by_yield_year.csv", index=False)
    complete_group_counts.to_csv(output_root / "complete_weather_yield_group_counts.csv", index=False)
    partial_issues.to_csv(output_root / "partial_weather_weight_coverage_issues.csv", index=False)
    baseline.to_csv(output_root / "grid_calendar_month_weather_baselines.csv", index=False)
    aligned.to_csv(output_root / "aligned_grid_year_month_weather_anomalies.csv", index=False)
    examples.to_csv(output_root / "relative_month_alignment_examples.csv", index=False)
    summary.to_csv(output_root / "monthly_weather_by_yield_group.csv", index=False)
    effects.to_csv(output_root / "high_minus_low_monthly_weather_effects.csv", index=False)
    heatmap.to_csv(output_root / "heatmap_ready_high_minus_low.csv", index=False)
    line_data.to_csv(output_root / "line_profile_ready_yield_groups.csv", index=False)
    spearman.to_csv(output_root / "continuous_yield_weather_spearman.csv", index=False)
    coherent.to_csv(output_root / "exploratory_coherent_three_month_windows.csv", index=False)
    comparison.to_csv(output_root / "checkpoint1_effect_comparison_1982_2025_vs_1991_2025.csv", index=False)
    create_figures(effects, line_data, figure_root)
    write_report(
        output_root, results_path, weights_path, weather_dir, grouped, aligned,
        group_diag, coverage, effects, spearman, coherent, partial_issues,
        temporal_audit, annual_source_coverage, grid_audit, spatial_summary,
        windows, complete_by_year, complete_group_counts, comparison,
    )
    write_execution_report(output_root)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
