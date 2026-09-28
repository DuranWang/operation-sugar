"""Build a compact EXP-01A research summary pack from completed outputs only."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


FRIENDLY = {
    "nasa_total_rainfall_mm": "Precipitation",
    "nasa_average_temperature_c": "Temperature",
    "nasa_average_relative_humidity_pct": "Relative humidity",
    "vpd_mean_kpa": "VPD",
    "vpd_mean_daily_max_kpa": "Daily-max VPD",
    "soil_moisture_0_to_7cm_m3_m3": "Surface soil moisture",
    "soil_moisture_7_to_28cm_m3_m3": "Soil moisture 7–28 cm",
    "soil_moisture_28_to_100cm_m3_m3": "Soil moisture 28–100 cm",
    "soil_moisture_100_to_255cm_m3_m3": "Soil moisture 100–255 cm",
    "solar_radiation_total_mj_m2": "Total solar radiation",
    "solar_radiation_mean_daily_mj_m2": "Mean-daily solar radiation",
}

PERSISTENCE_LABELS = {
    "nasa_total_rainfall_mm": "short-lived",
    "solar_radiation_mean_daily_mj_m2": "intermediate",
    "vpd_mean_kpa": "intermediate",
    "nasa_average_temperature_c": "persistent",
    "soil_moisture_0_to_7cm_m3_m3": "persistent",
}


def _pair_name(x: str, y: str) -> str:
    return f"{FRIENDLY.get(x, x)} ↔ {FRIENDLY.get(y, y)}"


def _sign_changes(values: pd.Series) -> bool:
    clean = values.dropna()
    return bool(clean.lt(0).any() and clean.gt(0).any())


def summarize_core_pairs(core: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (x, y), group in core.groupby(["variable_x", "variable_y"], sort=False):
        row: dict[str, object] = {
            "pair": _pair_name(x, y),
            "variable_x": x,
            "variable_y": y,
        }
        for method, column in [("pearson", "pearson_r"), ("spearman", "spearman_rho")]:
            minimum = group.loc[group[column].idxmin()]
            maximum = group.loc[group[column].idxmax()]
            row[f"mean_monthly_{method}"] = group[column].mean()
            row[f"minimum_monthly_{method}"] = minimum[column]
            row[f"month_of_minimum_{method}"] = int(minimum["month"])
            row[f"maximum_monthly_{method}"] = maximum[column]
            row[f"month_of_maximum_{method}"] = int(maximum["month"])
            row[f"monthly_range_{method}"] = maximum[column] - minimum[column]
            row[f"sign_changes_across_months_{method}"] = _sign_changes(group[column])
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_temporal_persistence(cross: pd.DataFrame, lag: pd.DataFrame) -> pd.DataFrame:
    lag_lookup = lag.set_index("variable")
    rows = []
    for row in cross.itertuples(index=False):
        lag_row = lag_lookup.loc[row.variable] if row.variable in lag_lookup.index else None
        rows.append({
            "variable": row.variable,
            "variable_label": FRIENDLY[row.variable],
            "descriptive_label": PERSISTENCE_LABELS[row.variable],
            "adjacent_month_pearson": row.pearson_mean_adjacent,
            "approximately_3_month_pearson": row.pearson_mean_three_month,
            "6_month_pearson": row.pearson_mean_six_month,
            "adjacent_month_spearman": row.spearman_mean_adjacent,
            "approximately_3_month_spearman": row.spearman_mean_three_month,
            "6_month_spearman": row.spearman_mean_six_month,
            "lag1_overall_pearson": np.nan if lag_row is None else lag_row["pearson_r"],
            "lag1_overall_spearman": np.nan if lag_row is None else lag_row["spearman_rho"],
            "pairwise_n": int(row.pairwise_n_min_off_diagonal),
            "label_note": "Descriptive shorthand only; not a formal statistical classification or feature-selection rule.",
        })
    order = [
        "nasa_total_rainfall_mm",
        "nasa_average_temperature_c",
        "vpd_mean_kpa",
        "soil_moisture_0_to_7cm_m3_m3",
        "solar_radiation_mean_daily_mj_m2",
    ]
    result = pd.DataFrame(rows).set_index("variable").reindex(order).reset_index()
    return result


def summarize_pooled_discrepancies(
    monthly: pd.DataFrame,
    pooled_pearson: pd.DataFrame,
    pooled_spearman: pd.DataFrame,
    top_per_method: int = 15,
) -> pd.DataFrame:
    rows = []
    for item in monthly.itertuples(index=False):
        for method, monthly_value, pooled_matrix in [
            ("pearson", item.pearson_r, pooled_pearson),
            ("spearman", item.spearman_rho, pooled_spearman),
        ]:
            pooled_value = float(pooled_matrix.loc[item.variable_x, item.variable_y])
            rows.append({
                "method": method,
                "pair": _pair_name(item.variable_x, item.variable_y),
                "variable_x": item.variable_x,
                "variable_y": item.variable_y,
                "month": int(item.month),
                "pooled_correlation": pooled_value,
                "month_specific_correlation": monthly_value,
                "absolute_discrepancy": abs(monthly_value - pooled_value),
                "sign_reversal": bool(
                    pd.notna(monthly_value)
                    and pooled_value != 0
                    and monthly_value != 0
                    and np.sign(pooled_value) != np.sign(monthly_value)
                ),
            })
    complete = pd.DataFrame(rows)
    selected = []
    for method, group in complete.groupby("method", sort=False):
        ranked = group.sort_values(
            ["absolute_discrepancy", "sign_reversal"], ascending=[False, False]
        ).head(top_per_method).copy()
        ranked.insert(0, "rank_within_method", range(1, len(ranked) + 1))
        selected.append(ranked)
    return pd.concat(selected, ignore_index=True).sort_values(
        ["method", "rank_within_method"]
    ).reset_index(drop=True)


def _core_heatmap(core: pd.DataFrame, value: str, title: str, path: Path) -> None:
    prepared = core.assign(pair=core.apply(lambda r: _pair_name(r.variable_x, r.variable_y), axis=1))
    matrix = prepared.pivot(index="month", columns="pair", values=value).reindex(range(1, 13))
    fig, ax = plt.subplots(figsize=(10, 6))
    image = ax.imshow(matrix.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(matrix.columns)), labels=matrix.columns, rotation=38, ha="right")
    ax.set_yticks(range(12), labels=range(1, 13))
    ax.set_xlabel("Core weather pair")
    ax.set_ylabel("Calendar month")
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label="correlation", shrink=0.85)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _lag_bar(lag: pd.DataFrame, path: Path) -> None:
    plot = lag.copy()
    plot["label"] = plot["variable"].map(FRIENDLY)
    x = np.arange(len(plot))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, plot["pearson_r"], width, label="Pearson")
    ax.bar(x + width / 2, plot["spearman_rho"], width, label="Spearman")
    ax.set_xticks(x, labels=plot["label"], rotation=25, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Lag-1 correlation")
    ax.set_title("EXP-01A overall lag-1 persistence")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _decay_plot(summary: pd.DataFrame, path: Path) -> None:
    x = np.array([1, 3, 6])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for _, row in summary.iterrows():
        y = [
            row["adjacent_month_pearson"],
            row["approximately_3_month_pearson"],
            row["6_month_pearson"],
        ]
        ax.plot(x, y, marker="o", linewidth=2, label=row["variable_label"])
    ax.set_xticks(x, labels=["Adjacent", "≈3 months", "6 months"])
    ax.set_ylabel("Mean Pearson correlation")
    ax.set_title("EXP-01A cross-month persistence decay")
    ax.set_ylim(-0.05, 1)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _f(value: float) -> str:
    return f"{value:.2f}"


def write_summary(
    path: Path,
    core_summary: pd.DataFrame,
    temporal: pd.DataFrame,
    discrepancies: pd.DataFrame,
) -> None:
    core_lookup = core_summary.set_index("pair")
    temp_vpd = core_lookup.loc["Temperature ↔ VPD"]
    rain_soil = core_lookup.loc["Precipitation ↔ Surface soil moisture"]
    solar_temp = core_lookup.loc["Temperature ↔ Mean-daily solar radiation"]
    top_reversals = discrepancies.loc[discrepancies["sign_reversal"]].sort_values(
        "absolute_discrepancy", ascending=False
    ).head(3)
    reversal_lines = "\n".join(
        f"- {row.pair}, month {int(row.month)} ({row.method}): pooled "
        f"{_f(row.pooled_correlation)} versus monthly {_f(row.month_specific_correlation)}."
        for row in top_reversals.itertuples(index=False)
    )
    temporal_lookup = temporal.set_index("variable_label")
    text = f"""# EXP-01A Research Summary

## Scope

EXP-01A describes overlap and temporal dependence among municipality-level monthly weather predictors for São Paulo, 1990–2025. It uses 277,344 municipality-month observations without yield data or harvested-area weighting. Correlations are descriptive: they do not establish causality, predictive redundancy, or feature keep/drop decisions.

## Main cross-variable findings

- Temperature and mean VPD are consistently positively associated, but the monthly Pearson relationship varies materially (mean {_f(temp_vpd.mean_monthly_pearson)}; range {_f(temp_vpd.minimum_monthly_pearson)} to {_f(temp_vpd.maximum_monthly_pearson)}). They overlap, but are not interchangeable.
- Precipitation and 0–7 cm soil moisture are positively associated in every month (mean Pearson {_f(rain_soil.mean_monthly_pearson)}; range {_f(rain_soil.minimum_monthly_pearson)} to {_f(rain_soil.maximum_monthly_pearson)}). Together with its cross-month persistence, this pattern is consistent with soil moisture carrying information beyond contemporaneous rainfall.
- Temperature and mean-daily solar radiation are positively related but distinctly month-dependent (mean Pearson {_f(solar_temp.mean_monthly_pearson)}; range {_f(solar_temp.minimum_monthly_pearson)} to {_f(solar_temp.maximum_monthly_pearson)}).
- Temperature–surface-soil-moisture and precipitation–VPD relationships remain negative in every calendar month. None of the five core-pair Pearson or Spearman relationships changes sign across months.

## Month dependence and pooled-correlation pitfalls

Month-specific results are primary because pooled estimates can be dominated by the shared annual cycle. The strongest discrepancies include outright sign reversals:

{reversal_lines}

For example, pooled precipitation–mean-daily-radiation Pearson correlation is positive even though the strongest monthly discrepancy is negative. This makes the pooled matrix useful as an overview, but unsafe as the sole description of predictor overlap.

## Temporal persistence

- Surface soil moisture is the most persistent variable: mean Pearson dependence is {_f(temporal_lookup.loc['Surface soil moisture', 'adjacent_month_pearson'])} for adjacent months and {_f(temporal_lookup.loc['Surface soil moisture', '6_month_pearson'])} six months apart.
- Temperature is also persistent ({_f(temporal_lookup.loc['Temperature', 'adjacent_month_pearson'])} adjacent; {_f(temporal_lookup.loc['Temperature', '6_month_pearson'])} at six months).
- VPD is intermediate ({_f(temporal_lookup.loc['VPD', 'adjacent_month_pearson'])} adjacent; {_f(temporal_lookup.loc['VPD', '6_month_pearson'])} at six months).
- Mean-daily solar radiation is weaker but still structured across months ({_f(temporal_lookup.loc['Mean-daily solar radiation', 'adjacent_month_pearson'])} adjacent; {_f(temporal_lookup.loc['Mean-daily solar radiation', '6_month_pearson'])} at six months).
- Precipitation is short-lived ({_f(temporal_lookup.loc['Precipitation', 'adjacent_month_pearson'])} adjacent; {_f(temporal_lookup.loc['Precipitation', '6_month_pearson'])} at six months). These labels are descriptive shorthand, not formal classifications.

## Implications for later experiments

EXP-01B should retain the same verified variables and definitions so harvested-area-weighted correlations remain directly comparable with EXP-01A. EXP-01C should compare the weighted and unweighted patterns, especially where seasonality or long persistence may change apparent overlap.

For later growth-stage aggregation, rainfall's short memory suggests that timing and episodic totals may matter more than broad multi-month averaging. Soil moisture and temperature carry substantial dependence across adjacent and distant months, so heavily overlapping stage windows could encode repeated information. VPD and radiation sit between these extremes. These observations motivate careful, pre-specified stage windows and multicollinearity checks; they do not by themselves justify selecting variables or stages.
"""
    path.write_text(text, encoding="utf-8")


def build(input_dir: Path, output_dir: Path) -> None:
    required = {
        "core": input_dir / "summary/core_pair_monthly_correlations.csv",
        "monthly": input_dir / "cross variable/monthly_pair_correlations.csv",
        "pearson": input_dir / "cross variable/pooled_pearson_correlation.csv",
        "spearman": input_dir / "cross variable/pooled_spearman_correlation.csv",
        "lag": input_dir / "summary/lag1_persistence_overall.csv",
        "cross": input_dir / "summary/cross_month_dependence_summary.csv",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Completed EXP-01A outputs are missing: {missing}")

    core = pd.read_csv(required["core"])
    monthly = pd.read_csv(required["monthly"])
    pooled_pearson = pd.read_csv(required["pearson"], index_col=0)
    pooled_spearman = pd.read_csv(required["spearman"], index_col=0)
    lag = pd.read_csv(required["lag"])
    cross = pd.read_csv(required["cross"])

    output_dir.mkdir(parents=True, exist_ok=True)
    figures = output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    core_summary = summarize_core_pairs(core)
    temporal = summarize_temporal_persistence(cross, lag)
    discrepancies = summarize_pooled_discrepancies(monthly, pooled_pearson, pooled_spearman)
    core_summary.to_csv(output_dir / "core_weather_relationship_summary.csv", index=False)
    temporal.to_csv(output_dir / "temporal_persistence_summary.csv", index=False)
    discrepancies.to_csv(output_dir / "pooled_vs_monthly_discrepancy_summary.csv", index=False)

    _core_heatmap(core, "pearson_r", "Core-pair monthly Pearson correlation", figures / "core_pair_monthly_pearson_heatmap.png")
    _core_heatmap(core, "spearman_rho", "Core-pair monthly Spearman correlation", figures / "core_pair_monthly_spearman_heatmap.png")
    _lag_bar(lag, figures / "lag1_persistence_overall_bar_chart.png")
    _decay_plot(temporal, figures / "cross_month_persistence_decay.png")
    write_summary(output_dir / "EXP_01A_research_summary.md", core_summary, temporal, discrepancies)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.project_root.resolve()
    build(
        root / "data/processed/analysis/exp_01a_municipality_weather_correlation",
        root / "outputs/experiments/exp_01a_municipality_weather_correlation/research_summary_pack",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
