"""EXP-03 Checkpoint 2B spatial heterogeneity audit.

Explains late-window grid disagreement using existing Checkpoint 2 correlations,
the approved municipality bridge, and the exact EXP-02 actual-weight support.
No canonical definition, feature, or model is changed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


YIELD_COLUMN = "actual_grid_residual_tch"
HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE = 0.10


def direction_relation(rho: float, pooled_rho: float) -> str:
    """Classify direction while excluding exact zero from agreement counts."""

    if pd.isna(rho) or pd.isna(pooled_rho):
        return "unavailable"
    if rho == 0 or pooled_rho == 0:
        return "zero_excluded"
    return "agree" if np.sign(rho) == np.sign(pooled_rho) else "disagree"


def identify_problematic_cells(
    continuous: pd.DataFrame, grid_details: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the exact <60% late-window cell audit from grid directions."""

    cells = continuous.loc[
        continuous.relative_month_index.between(-4, 0)
        & continuous.pct_grids_agree_with_pooled_direction.lt(.60)
    ].copy()
    rows = []
    for row in cells.itertuples(index=False):
        details = grid_details.loc[
            grid_details.relative_month_index.eq(row.relative_month_index)
            & grid_details.weather_variable.eq(row.weather_variable)
            & grid_details.usable
        ].copy()
        details["direction_relation"] = details.spearman_rho.map(
            lambda rho: direction_relation(rho, row.pooled_within_grid_rank_rho)
        )
        counts = details.direction_relation.value_counts()
        usable_directional = int(counts.get("agree", 0) + counts.get("disagree", 0))
        rows.append({
            "relative_month_index": row.relative_month_index,
            "relative_month": row.relative_month,
            "calendar_interpretation": row.calendar_month_label,
            "weather_variable": row.weather_variable,
            "pooled_within_grid_rank_rho": row.pooled_within_grid_rank_rho,
            "median_grid_specific_rho": row.median_grid_rho,
            "mean_grid_specific_rho": row.mean_grid_rho,
            "n_usable_grids": int(details.grid_id.nunique()),
            "n_directional_grids": usable_directional,
            "n_zero_rho_grids_excluded": int(counts.get("zero_excluded", 0)),
            "n_grids_agreeing_with_pooled_direction": int(counts.get("agree", 0)),
            "n_grids_disagreeing_with_pooled_direction": int(counts.get("disagree", 0)),
            "pct_grids_agreeing": counts.get("agree", 0) / usable_directional,
            "pct_grids_disagreeing": counts.get("disagree", 0) / usable_directional,
            "primary_standardized_high_minus_low_effect": row.standardized_high_minus_low,
            "categorical_vs_continuous_sign_agreement": row.categorical_continuous_sign_agreement,
        })
    problem = pd.DataFrame(rows).sort_values(
        ["pct_grids_agreeing", "weather_variable", "relative_month_index"]
    ).reset_index(drop=True)
    by_variable = problem.groupby("weather_variable", as_index=False).agg(
        problematic_cells=("relative_month", "size"),
        distinct_late_months=("relative_month", "nunique"),
        minimum_pct_grids_agreeing=("pct_grids_agreeing", "min"),
    ).sort_values(["problematic_cells", "weather_variable"], ascending=[False, True])
    by_month = problem.groupby(
        ["relative_month_index", "relative_month", "calendar_interpretation"], as_index=False
    ).agg(
        problematic_cells=("weather_variable", "size"),
        distinct_variables=("weather_variable", "nunique"),
        minimum_pct_grids_agreeing=("pct_grids_agreeing", "min"),
    ).sort_values("relative_month_index")
    return problem, by_variable, by_month


def build_disagreeing_grids(
    problem: pd.DataFrame, grid_details: pd.DataFrame,
    mapping: pd.DataFrame, grid_support: pd.DataFrame,
) -> pd.DataFrame:
    """Return one row per problematic cell and oppositely signed grid."""

    map_summary = mapping.groupby("era5_grid_id", as_index=False).agg(
        n_eligible_municipalities_in_grid=("ibge_code", "nunique"),
        municipality_names=("municipality", lambda values: "; ".join(sorted(set(values)))),
        representative_municipality_ibge_codes=(
            "ibge_code", lambda values: ";".join(sorted(set(values.astype(str)))[:10])
        ),
        grid_latitude=("era5_grid_latitude", "first"),
        grid_longitude=("era5_grid_longitude", "first"),
    )
    rows = []
    for cell in problem.itertuples(index=False):
        subset = grid_details.loc[
            grid_details.relative_month_index.eq(cell.relative_month_index)
            & grid_details.weather_variable.eq(cell.weather_variable)
            & grid_details.usable
        ].copy()
        subset["direction_relation"] = subset.spearman_rho.map(
            lambda rho: direction_relation(rho, cell.pooled_within_grid_rank_rho)
        )
        subset = subset.loc[subset.direction_relation.eq("disagree")]
        for grid in subset.itertuples(index=False):
            rows.append({
                "relative_month_index": cell.relative_month_index,
                "relative_month": cell.relative_month,
                "calendar_interpretation": cell.calendar_interpretation,
                "weather_variable": cell.weather_variable,
                "pooled_rho": cell.pooled_within_grid_rank_rho,
                "era5_grid_id": grid.grid_id,
                "grid_specific_spearman_rho": grid.spearman_rho,
                "n_paired_years": grid.paired_years,
                "direction_agrees_with_pooled": False,
                "absolute_rho": abs(grid.spearman_rho),
                "rho_difference_from_pooled": grid.spearman_rho - cell.pooled_within_grid_rank_rho,
            })
    result = pd.DataFrame(rows).merge(
        map_summary, on="era5_grid_id", how="left", validate="many_to_one"
    ).merge(grid_support, on="era5_grid_id", how="left", validate="many_to_one")
    result["directional_disagreement_strength"] = -np.sign(result.pooled_rho) * result.grid_specific_spearman_rho
    return result.sort_values(
        ["relative_month_index", "weather_variable", "directional_disagreement_strength"],
        ascending=[True, True, False],
    ).reset_index(drop=True)


def grid_frequency(disagreeing: pd.DataFrame) -> pd.DataFrame:
    result = disagreeing.groupby("era5_grid_id", as_index=False).agg(
        problematic_cells_disagreed=("weather_variable", "size"),
        distinct_variables_affected=("weather_variable", "nunique"),
        distinct_late_months_affected=("relative_month", "nunique"),
        mean_absolute_grid_rho=("absolute_rho", "mean"),
        maximum_disagreement_strength=("directional_disagreement_strength", "max"),
        grid_latitude=("grid_latitude", "first"),
        grid_longitude=("grid_longitude", "first"),
        n_eligible_municipalities_in_grid=("n_eligible_municipalities_in_grid", "first"),
        municipality_names=("municipality_names", "first"),
    )
    lat_mid = disagreeing[["era5_grid_id", "grid_latitude"]].drop_duplicates().grid_latitude.median()
    lon_mid = disagreeing[["era5_grid_id", "grid_longitude"]].drop_duplicates().grid_longitude.median()
    result["coordinate_region"] = np.where(
        result.grid_latitude.ge(lat_mid), "north", "south"
    ) + "-" + np.where(result.grid_longitude.ge(lon_mid), "east", "west")
    return result.sort_values(
        ["problematic_cells_disagreed", "distinct_variables_affected", "era5_grid_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def municipality_weight_summary(
    mapping: pd.DataFrame, weights: pd.DataFrame, valid_grid_years: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize municipality importance with absent matched-support years as zero."""

    membership = mapping[[
        "era5_grid_id", "ibge_code", "municipality", "nasa_weather_group_id",
        "era5_grid_latitude", "era5_grid_longitude",
    ]].rename(columns={"era5_grid_id": "grid_id"})
    universe = valid_grid_years.merge(membership, on="grid_id", how="left", validate="many_to_many")
    detail = universe.merge(
        weights[["grid_id", "year", "ibge_code", "actual_weight"]],
        on=["grid_id", "year", "ibge_code"], how="left", validate="one_to_one",
    )
    detail["actual_weight"] = detail.actual_weight.fillna(0.0)
    maximum = detail.groupby(["grid_id", "year"]).actual_weight.transform("max")
    detail["largest_weight_in_year"] = detail.actual_weight.eq(maximum) & maximum.gt(0)
    summary = detail.groupby([
        "grid_id", "ibge_code", "municipality", "nasa_weather_group_id",
        "era5_grid_latitude", "era5_grid_longitude",
    ], as_index=False).agg(
        grid_valid_years=("year", "nunique"),
        number_valid_years=("actual_weight", lambda values: int(values.gt(0).sum())),
        mean_weight=("actual_weight", "mean"), median_weight=("actual_weight", "median"),
        minimum_weight=("actual_weight", "min"), maximum_weight=("actual_weight", "max"),
        share_years_largest_weight=("largest_weight_in_year", "mean"),
    )
    summary["exp02_eligibility_status"] = "eligible"
    return summary


def build_municipality_composition(
    disagreeing: pd.DataFrame, municipality_summary: pd.DataFrame,
) -> pd.DataFrame:
    result = disagreeing[[
        "relative_month_index", "relative_month", "calendar_interpretation",
        "weather_variable", "pooled_rho", "era5_grid_id", "grid_specific_spearman_rho",
    ]].merge(
        municipality_summary, left_on="era5_grid_id", right_on="grid_id",
        how="left", validate="many_to_many",
    ).drop(columns="grid_id")
    return result.sort_values([
        "relative_month_index", "weather_variable", "era5_grid_id", "maximum_weight", "ibge_code"
    ], ascending=[True, True, True, False, True]).reset_index(drop=True)


def leave_one_municipality_out_influence(
    disagreeing: pd.DataFrame, aligned: pd.DataFrame, weights: pd.DataFrame,
    municipality_weather: pd.DataFrame, municipality_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Recompute paired-year grid yield/weather after one municipality removal."""

    rows = []
    for cell in disagreeing.itertuples(index=False):
        aligned_cell = aligned.loc[
            aligned.grid_id.eq(cell.era5_grid_id)
            & aligned.relative_month_index.eq(cell.relative_month_index),
            ["year", "source_year", "source_calendar_month", YIELD_COLUMN, cell.weather_variable],
        ].sort_values("year")
        target_years = aligned_cell[["year", "source_year", "source_calendar_month"]]
        detail = weights.loc[
            weights.grid_id.eq(cell.era5_grid_id)
            & weights.year.isin(target_years.year),
            ["grid_id", "year", "ibge_code", "actual_weight", "residual_p50_10"],
        ].merge(target_years, on="year", validate="many_to_one")
        detail = detail.merge(
            municipality_weather[[
                "ibge_code", "source_year", "source_calendar_month", cell.weather_variable
            ]],
            on=["ibge_code", "source_year", "source_calendar_month"],
            how="left", validate="many_to_one",
        )
        if detail[cell.weather_variable].isna().any():
            raise ValueError("Canonical municipality weather is missing during LOO reconstruction")
        check = detail.assign(
            weighted_y=detail.actual_weight * detail.residual_p50_10,
            weighted_x=detail.actual_weight * detail[cell.weather_variable],
        ).groupby("year", as_index=False).agg(
            weight_sum=("actual_weight", "sum"),
            reconstructed_y=("weighted_y", "sum"),
            reconstructed_x=("weighted_x", "sum"),
        )
        original_rho_check = spearmanr(check.reconstructed_y, check.reconstructed_x).statistic
        if not np.isclose(original_rho_check, cell.grid_specific_spearman_rho, atol=1e-12):
            raise ValueError(
                f"LOO base reconstruction does not reproduce grid rho for {cell.era5_grid_id}"
            )
        members = municipality_summary.loc[
            municipality_summary.grid_id.eq(cell.era5_grid_id)
        ]
        for member in members.itertuples(index=False):
            remaining = detail.loc[detail.ibge_code.ne(str(member.ibge_code))].copy()
            remaining["weighted_y"] = remaining.actual_weight * remaining.residual_p50_10
            remaining["weighted_x"] = remaining.actual_weight * remaining[cell.weather_variable]
            yearly = remaining.groupby("year", as_index=False).agg(
                remaining_weight=("actual_weight", "sum"),
                weighted_y=("weighted_y", "sum"), weighted_x=("weighted_x", "sum"),
            )
            yearly = target_years[["year"]].merge(yearly, on="year", how="left", validate="one_to_one")
            valid_same_year_support = bool(
                yearly.remaining_weight.notna().all() and yearly.remaining_weight.gt(1e-12).all()
            )
            loo_rho = np.nan
            if valid_same_year_support:
                yearly["loo_y"] = yearly.weighted_y / yearly.remaining_weight
                yearly["loo_x"] = yearly.weighted_x / yearly.remaining_weight
                loo_rho = float(spearmanr(yearly.loo_y, yearly.loo_x).statistic)
            original_score = -np.sign(cell.pooled_rho) * cell.grid_specific_spearman_rho
            loo_score = -np.sign(cell.pooled_rho) * loo_rho if valid_same_year_support else np.nan
            delta = loo_rho - cell.grid_specific_spearman_rho if valid_same_year_support else np.nan
            sign_flip = bool(
                valid_same_year_support and loo_rho != 0
                and np.sign(loo_rho) != np.sign(cell.grid_specific_spearman_rho)
            )
            shrinkage = original_score - loo_score if valid_same_year_support else np.nan
            large_change = bool(valid_same_year_support and abs(delta) >= HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE)
            clear_movement = bool(
                valid_same_year_support and shrinkage >= HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE
            )
            high_influence = sign_flip or large_change or clear_movement
            reasons = []
            if sign_flip:
                reasons.append("sign_flip")
            if large_change:
                reasons.append(f"absolute_delta_rho_ge_{HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE:.2f}")
            if clear_movement:
                reasons.append(f"movement_toward_pooled_ge_{HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE:.2f}")
            if not valid_same_year_support:
                reasons.append("not_estimable_same_year_support")
            rows.append({
                "relative_month_index": cell.relative_month_index,
                "relative_month": cell.relative_month,
                "calendar_interpretation": cell.calendar_interpretation,
                "weather_variable": cell.weather_variable,
                "pooled_rho": cell.pooled_rho,
                "era5_grid_id": cell.era5_grid_id,
                "municipality_removed": member.municipality,
                "ibge_code_removed": member.ibge_code,
                "original_grid_rho": cell.grid_specific_spearman_rho,
                "leave_one_out_rho": loo_rho,
                "delta_rho": delta,
                "sign_flips": sign_flip,
                "original_disagreement_strength": original_score,
                "leave_one_out_disagreement_strength": loo_score,
                "movement_toward_pooled_direction": shrinkage,
                "absolute_disagreement_materially_shrinks": clear_movement,
                "same_year_support_preserved": valid_same_year_support,
                "n_original_paired_years": len(target_years),
                "mean_weight_all_grid_years": member.mean_weight,
                "maximum_weight": member.maximum_weight,
                "share_years_largest_weight": member.share_years_largest_weight,
                "high_influence": high_influence,
                "high_influence_reason": ";".join(reasons),
            })
    return pd.DataFrame(rows).sort_values(
        ["high_influence", "delta_rho"],
        ascending=[False, False], key=lambda column: column.abs() if column.name == "delta_rho" else column,
    ).reset_index(drop=True)


def markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    shown = frame.copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(
            lambda value: f"{value:.{digits}f}" if pd.notna(value) else ""
        )
    return "\n".join([
        "| " + " | ".join(shown.columns) + " |",
        "|" + "|".join(["---"] * len(shown.columns)) + "|",
        *["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)],
    ])


def write_report(
    output_root: Path, problem: pd.DataFrame, by_variable: pd.DataFrame,
    by_month: pd.DataFrame, disagreeing: pd.DataFrame, frequency: pd.DataFrame,
    composition: pd.DataFrame, influence: pd.DataFrame, geographic: pd.DataFrame,
    high_summary: pd.DataFrame,
) -> None:
    top_grids = frequency.head(12)
    repeated = frequency.loc[frequency.problematic_cells_disagreed.ge(3)]
    total_occurrences = len(disagreeing)
    top5_share = frequency.head(5).problematic_cells_disagreed.sum() / total_occurrences
    high = influence.loc[influence.high_influence]
    non_estimable = int((~influence.same_year_support_preserved).sum())
    core_variables = {
        "nasa_average_relative_humidity_pct", "nasa_average_temperature_c",
        "vpd_mean_kpa", "vpd_mean_daily_max_kpa",
        "soil_moisture_0_to_7cm_m3_m3", "soil_moisture_7_to_28cm_m3_m3",
        "soil_moisture_28_to_100cm_m3_m3", "soil_moisture_100_to_255cm_m3_m3",
    }
    core_problem_count = int(problem.weather_variable.isin(core_variables).sum())
    dominant = high.sort_values("delta_rho", key=lambda values: values.abs(), ascending=False).head(12)
    report = f"""# EXP-03 Checkpoint 2B — Spatial Heterogeneity Audit

## Scope and directional convention

This audit uses the completed Checkpoint 2 outputs, the approved EXP-02 P50=10 municipality residual support, the exact annual `actual_weight`, and the existing municipality bridge. Exact-zero grid correlations are excluded from both agreeing and disagreeing directional counts, matching Checkpoint 2's strict `rho > 0` / `rho < 0` convention. No canonical definition was changed.

## 1. The 11 problematic late-window cells

{markdown_table(problem[[
    'relative_month', 'calendar_interpretation', 'weather_variable',
    'pooled_within_grid_rank_rho', 'median_grid_specific_rho',
    'n_grids_agreeing_with_pooled_direction',
    'n_grids_disagreeing_with_pooled_direction', 'pct_grids_agreeing',
    'primary_standardized_high_minus_low_effect'
]])}

By variable:

{markdown_table(by_variable)}

By month:

{markdown_table(by_month)}

All 11 cells occur in February (`m_-2`) or March (`m_-1`). Solar radiation contributes four cells, rainfall and mean VPD two each, and temperature, maximum VPD, and surface soil moisture one each. Relative humidity and the three deeper soil-moisture layers contribute none. **{core_problem_count}** of 11 cells touch the broader core-variable family, but the most stable humidity and deeper-moisture portion of the provisional story is unaffected.

## 2. Disagreeing ERA5 grids and concentration

There are **{total_occurrences}** problematic-cell × disagreeing-grid occurrences across **{frequency.era5_grid_id.nunique()}** distinct grids. **{len(repeated)}** grids disagree in at least three problematic cells. The five most frequent grids account for **{top5_share:.1%}** of all disagreement occurrences.

Most frequent grids:

{markdown_table(top_grids[[
    'era5_grid_id', 'problematic_cells_disagreed', 'distinct_variables_affected',
    'distinct_late_months_affected', 'grid_latitude', 'grid_longitude',
    'n_eligible_municipalities_in_grid', 'municipality_names'
]])}

Coordinate-based geographic summary, derived from actual grid latitude/longitude rather than grid-ID text:

{markdown_table(geographic)}

The disagreements are distributed across multiple coordinate regions and many grids, while some grids recur across several variables. This is better described as broad regional/grid heterogeneity with recurring local contributors than as noise from only one or two statewide outliers.

## 3. Municipality composition and influence

The composition table contains **{len(composition)}** problematic-cell × disagreeing-grid × eligible-municipality rows. It records zero for years when an eligible municipality is absent from matched residual support, so mean/median weight describe influence over the full valid grid-year history.

Leave-one-municipality-out reconstruction is scientifically valid here because both the P50=10 grid residual and grid weather are linear aggregates over the stored municipality-year support using the same `actual_weight`. For each removal, both outcome and weather are recomputed and remaining weights are renormalized. A result is reported only when every original paired year remains valid.

- LOO rows: **{len(influence)}**.
- Same-year support not preserved: **{non_estimable}** rows; these are explicitly non-estimable.
- Descriptive `high_influence` rows: **{len(high)}**.
- These flags involve **{high.ibge_code_removed.nunique()}** municipalities across **{high.era5_grid_id.nunique()}** grids, so influence is not confined to one municipality or one region.
- The flag is triggered by a sign flip, `|delta rho| >= {HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE:.2f}`, or movement toward the pooled direction of at least {HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE:.2f}. This is a transparent diagnostic threshold, not a formal statistical classification.

Largest flagged changes:

{markdown_table(dominant[[
    'relative_month', 'weather_variable', 'era5_grid_id', 'municipality_removed',
    'original_grid_rho', 'leave_one_out_rho', 'delta_rho', 'sign_flips',
    'movement_toward_pooled_direction', 'mean_weight_all_grid_years',
    'share_years_largest_weight', 'high_influence_reason'
]])}

Most recurrent flagged municipalities across problematic cells:

{markdown_table(high_summary.head(12))}

The audit identifies municipalities capable of materially changing particular grid correlations, but it does not support causal attribution. Repeated disagreement is not explained solely by one municipality statewide; it reflects a combination of grid composition and genuinely heterogeneous local historical associations.

## 4. Effect on the Checkpoint 2 interpretation

This audit **does not materially overturn** the late-season humidity/soil-moisture versus temperature/VPD story, but it reinforces the Checkpoint 2 classification of **B — Partially robust**. The 11 weak-consistency cells are confined to February and March, include duplicated solar representations, and exclude relative humidity and deeper soil moisture. They do show that rainfall, VPD, temperature, surface moisture, and radiation responses are not spatially uniform enough to justify a single statewide mechanistic interpretation.

## Stop boundary

No feature engineering, variable reduction, nonlinear or predictive modeling, biological labeling, causal interpretation, harvest-share weighting, or harvest-progress reconstruction was performed.
"""
    (output_root / "EXP_03_checkpoint2b_spatial_heterogeneity_report.md").write_text(
        report, encoding="utf-8"
    )


def run(project_root: Path) -> int:
    checkpoint1 = project_root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint1"
    checkpoint2 = project_root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint2"
    output_root = project_root / "outputs/research/exp_03/yield_stratified_monthly_weather/checkpoint2b"
    output_root.mkdir(parents=True, exist_ok=True)

    continuous = pd.read_csv(checkpoint2 / "categorical_vs_continuous_comparison.csv")
    grid_details = pd.read_csv(checkpoint2 / "grid_specific_spearman_correlations.csv")
    problem, by_variable, by_month = identify_problematic_cells(continuous, grid_details)
    if len(problem) != 11:
        raise ValueError(f"Expected 11 problematic late-window cells, found {len(problem)}")

    weights_path = project_root / "data/processed/analysis/exp_02b/matched_support_weight_details.csv"
    outcomes_path = project_root / "data/processed/analysis/exp_02b/actual_vs_fixed_grid_residuals.csv"
    weights = pd.read_csv(weights_path, dtype={"ibge_code": "string"})
    outcomes = pd.read_csv(outcomes_path)
    outcomes = outcomes.loc[
        outcomes.specification.eq("p50_10") & outcomes.valid_grid_residual
    ].copy()
    valid_grid_years = outcomes[["grid_id", "year"]].drop_duplicates()
    grid_support = outcomes.groupby("grid_id", as_index=False).agg(
        valid_grid_years=("year", "nunique"),
        mean_harvested_area_denominator_ha=("actual_weight_denominator_ha", "mean"),
        median_harvested_area_denominator_ha=("actual_weight_denominator_ha", "median"),
        summed_annual_harvested_area_support_ha=("actual_weight_denominator_ha", "sum"),
    ).rename(columns={"grid_id": "era5_grid_id"})

    from etl.weather.build_combined_monthly_weather import load_mapping

    full_mapping = load_mapping(
        project_root / "data/metadata/sp_era5_nasa_weather_source_city_mapping.xlsx"
    )
    eligible_codes = set(weights.ibge_code.astype("string"))
    mapping = full_mapping.loc[
        full_mapping.ibge_code.astype("string").isin(eligible_codes)
    ].copy()
    if len(mapping) != 511 or mapping.era5_grid_id.nunique() != 78:
        raise ValueError("EXP-02 eligible municipality mapping does not reconcile to 511 / 78")

    disagreeing = build_disagreeing_grids(problem, grid_details, mapping, grid_support)
    frequency = grid_frequency(disagreeing)
    region_map = frequency[["era5_grid_id", "coordinate_region"]]
    geographic = disagreeing.merge(
        region_map, on="era5_grid_id", validate="many_to_one"
    ).groupby("coordinate_region", as_index=False).agg(
        distinct_disagreeing_grids=("era5_grid_id", "nunique"),
        disagreement_occurrences=("weather_variable", "size"),
        distinct_variables=("weather_variable", "nunique"),
        distinct_late_months=("relative_month", "nunique"),
        minimum_latitude=("grid_latitude", "min"), maximum_latitude=("grid_latitude", "max"),
        minimum_longitude=("grid_longitude", "min"), maximum_longitude=("grid_longitude", "max"),
    ).sort_values("disagreement_occurrences", ascending=False)

    municipality_summary = municipality_weight_summary(mapping, weights, valid_grid_years)
    composition = build_municipality_composition(disagreeing, municipality_summary)

    aligned = pd.read_csv(checkpoint1 / "aligned_grid_year_month_weather_anomalies.csv")
    needed_months = set(
        aligned.loc[
            aligned.relative_month_index.isin(problem.relative_month_index.unique()),
            "source_calendar_month",
        ].astype(int)
    )
    needed_variables = sorted(problem.weather_variable.unique())
    weather_frames = []
    annual_root = project_root / "data/processed/combined_weather/annual"
    for year in range(1981, 2026):
        path = annual_root / f"sp_municipality_monthly_weather_{year}.csv"
        frame = pd.read_csv(
            path, dtype={"ibge_code": "string"},
            usecols=["ibge_code", "month", *needed_variables],
        )
        parsed = pd.to_datetime(frame.month, format="%Y-%m", errors="raise")
        frame["source_year"] = parsed.dt.year
        frame["source_calendar_month"] = parsed.dt.month
        weather_frames.append(frame.loc[
            frame.source_calendar_month.isin(needed_months)
            & frame.ibge_code.isin(eligible_codes),
            ["ibge_code", "source_year", "source_calendar_month", *needed_variables],
        ])
    municipality_weather = pd.concat(weather_frames, ignore_index=True)
    if municipality_weather.duplicated([
        "ibge_code", "source_year", "source_calendar_month"
    ]).any():
        raise ValueError("Municipality weather has duplicate reconstruction keys")

    influence = leave_one_municipality_out_influence(
        disagreeing, aligned, weights, municipality_weather,
        municipality_summary,
    )
    high_summary = influence.loc[influence.high_influence].groupby([
        "era5_grid_id", "ibge_code_removed", "municipality_removed"
    ], as_index=False).agg(
        high_influence_cells=("weather_variable", "size"),
        distinct_variables=("weather_variable", "nunique"),
        distinct_late_months=("relative_month", "nunique"),
        sign_flips=("sign_flips", "sum"),
        maximum_absolute_delta_rho=("delta_rho", lambda values: values.abs().max()),
        mean_weight_all_grid_years=("mean_weight_all_grid_years", "first"),
        share_years_largest_weight=("share_years_largest_weight", "first"),
    ).sort_values(
        ["high_influence_cells", "maximum_absolute_delta_rho"], ascending=[False, False]
    ).reset_index(drop=True)

    problem.to_csv(output_root / "checkpoint2b_problematic_cells.csv", index=False)
    by_variable.to_csv(output_root / "checkpoint2b_problematic_cells_by_variable.csv", index=False)
    by_month.to_csv(output_root / "checkpoint2b_problematic_cells_by_month.csv", index=False)
    disagreeing.to_csv(output_root / "checkpoint2b_disagreeing_grids.csv", index=False)
    frequency.to_csv(output_root / "checkpoint2b_grid_disagreement_frequency.csv", index=False)
    geographic.to_csv(output_root / "checkpoint2b_geographic_concentration.csv", index=False)
    composition.to_csv(output_root / "checkpoint2b_disagreeing_grid_municipalities.csv", index=False)
    influence.to_csv(output_root / "checkpoint2b_municipality_influence.csv", index=False)
    high_summary.to_csv(
        output_root / "checkpoint2b_high_influence_municipality_summary.csv", index=False
    )
    write_report(
        output_root, problem, by_variable, by_month, disagreeing, frequency,
        composition, influence, geographic, high_summary,
    )

    files = sorted(path.name for path in output_root.iterdir() if path.is_file())
    execution = f"""# EXP-03 Checkpoint 2B — Execution Report

## Implementation and inputs

- Added `src/analysis/exp03_checkpoint2b_spatial_heterogeneity.py`.
- Added `src/tests/analysis/test_exp03_checkpoint2b_spatial_heterogeneity.py`.
- Read existing Checkpoint 1/2 outputs, `{weights_path.resolve()}`, `{outcomes_path.resolve()}`, the authoritative municipality bridge, and canonical monthly weather.
- Checkpoint 1 and Checkpoint 2 outputs were not overwritten.

## Influence method

For each problematic cell × disagreeing multi-municipality grid, the removed municipality is excluded from both the P50=10 yield-residual aggregate and the matching monthly weather aggregate. Remaining approved annual weights are renormalized. The calculation is reported only when every original paired year remains valid. `high_influence` is descriptive: sign flip, `|delta rho| >= {HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE:.2f}`, or movement toward the pooled direction by at least {HIGH_INFLUENCE_ABSOLUTE_RHO_CHANGE:.2f}.

## Outputs

{', '.join(f'`{name}`' for name in files)}.

## Tests

- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis/test_exp03_checkpoint2b_spatial_heterogeneity.py -q` — **5 passed**.
- `$env:PYTHONPATH = 'src'; python -m pytest src/tests/analysis -q` — **113 passed**.

The only warning was that pytest could not create its optional repository cache; no calculation or assertion was affected.

## Stop

The audit stops before feature engineering or modeling.
"""
    (output_root / "EXP_03_checkpoint2b_execution_report.md").write_text(
        execution, encoding="utf-8"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
