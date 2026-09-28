"""EXP-01S analysis of observed-only normalized harvested-area shares.

Unavailable IBGE/PAM values (``...``) remain missing throughout.  Explicit
absolute zeros (``-``) enter the reported set with harvested area and weight
equal to zero.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.exp01s_harvested_area_weight_stability import (
    ANCHOR_YEARS,
    END_YEAR,
    START_YEAR,
    WEIGHT_TOLERANCE,
    load_raw_harvested_area,
    validate_processed_structure,
)


TOP_KS = (10, 25, 50)
ADMINISTRATIVELY_RESOLVED = {
    "3518859": (
        "1993-01-01",
        "https://www.ibge.gov.br/biblioteca/visualizacao/dtb/saopaulo/guatapara.pdf",
    ),
    "3553955": (
        "1993-01-01",
        "https://www.ibge.gov.br/biblioteca/visualizacao/dtb/saopaulo/taruma.pdf",
    ),
    "3532058": (
        "1993-01-01",
        "https://www.ibge.gov.br/biblioteca/visualizacao/dtb/saopaulo/motuca.pdf",
    ),
    "3548054": (
        "1993-01-01",
        "https://www.ibge.gov.br/biblioteca/visualizacao/dtb/saopaulo/santoantoniodoaracangua.pdf",
    ),
}


def build_observed_panel(
    processed: pd.DataFrame,
    symbol_data: pd.DataFrame,
) -> pd.DataFrame:
    """Return a symbol-aware panel with w_obs defined only on O_t."""

    panel = processed.merge(
        symbol_data,
        on=["ibge_code", "municipality", "year"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not panel["_merge"].eq("both").all():
        raise ValueError("Processed and raw municipality-year keys differ")
    panel = panel.drop(columns="_merge").rename(
        columns={
            "area_value_status": "source_status",
            "harvested_area_ha_symbol_aware": "reported_harvested_area_ha",
        }
    )
    panel["is_reported"] = panel["source_status"].isin(
        ["numeric_positive", "numeric_zero", "absolute_zero"]
    )
    if panel.loc[~panel["is_reported"], "reported_harvested_area_ha"].notna().any():
        raise ValueError("Unavailable source rows unexpectedly contain numeric area")
    denominator = panel.groupby("year")["reported_harvested_area_ha"].transform(
        lambda values: values.sum(min_count=1)
    )
    panel["observed_area_weight"] = (
        panel["reported_harvested_area_ha"] / denominator
    )
    sums = panel.groupby("year")["observed_area_weight"].sum(min_count=1)
    if not np.allclose(sums, 1.0, atol=WEIGHT_TOLERANCE, rtol=0):
        raise ValueError("Observed-only weights do not sum to one")
    comparable = panel["area_weight"].notna()
    differences = (
        panel.loc[comparable, "area_weight"]
        - panel.loc[comparable, "observed_area_weight"]
    ).abs()
    if differences.gt(WEIGHT_TOLERANCE).any():
        raise ValueError("Stored weights differ from reconstructed observed-only weights")
    return panel.sort_values(["year", "ibge_code"]).reset_index(drop=True)


def annual_top_sets(panel: pd.DataFrame) -> dict[tuple[int, int], set[str]]:
    """Return deterministic top-K sets among municipalities reported each year."""

    result: dict[tuple[int, int], set[str]] = {}
    for year, group in panel.loc[panel["is_reported"]].groupby("year"):
        ranked = group.sort_values(
            ["observed_area_weight", "ibge_code"], ascending=[False, True]
        )
        for k in TOP_KS:
            result[(int(year), k)] = set(ranked.head(k)["ibge_code"])
    return result


def build_missingness_materiality(
    panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Assess whether municipalities with any unavailable year are material."""

    affected_codes = set(
        panel.loc[panel["source_status"].eq("unavailable"), "ibge_code"]
    )
    top_sets = annual_top_sets(panel)
    rows = []
    for (code, municipality), group in panel.loc[
        panel["ibge_code"].isin(affected_codes)
    ].groupby(["ibge_code", "municipality"]):
        observed = group.loc[group["is_reported"]]
        unavailable_years = group.loc[
            group["source_status"].eq("unavailable"), "year"
        ].astype(int)
        row: dict[str, object] = {
            "ibge_code": code,
            "municipality": municipality,
            "unavailable_year_count": int(len(unavailable_years)),
            "unavailable_years": ";".join(map(str, unavailable_years.tolist())),
            "observed_year_count": int(len(observed)),
            "maximum_observed_area_weight": float(
                observed["observed_area_weight"].max()
            ),
            "mean_observed_area_weight": float(
                observed["observed_area_weight"].mean()
            ),
            "maximum_observed_harvested_area_ha": float(
                observed["reported_harvested_area_ha"].max()
            ),
        }
        installation = ADMINISTRATIVELY_RESOLVED.get(str(code))
        resolved = bool(installation) and set(unavailable_years) == {1990, 1991, 1992}
        row["administrative_availability_resolved"] = resolved
        row["official_installation_date"] = installation[0] if resolved else ""
        row["official_ibge_history_source"] = installation[1] if resolved else ""
        for k in TOP_KS:
            years = [
                year
                for year in range(START_YEAR, END_YEAR + 1)
                if code in top_sets[(year, k)]
            ]
            row[f"ever_top_{k}"] = bool(years)
            row[f"top_{k}_years"] = ";".join(map(str, years))
        rows.append(row)
    municipality = pd.DataFrame(rows).sort_values(
        ["maximum_observed_area_weight", "ibge_code"], ascending=[False, True]
    )

    annual_rows = []
    for year, group in panel.groupby("year"):
        affected = group["ibge_code"].isin(affected_codes)
        annual_rows.append(
            {
                "year": int(year),
                "affected_municipality_count": len(affected_codes),
                "affected_reported_count": int((affected & group["is_reported"]).sum()),
                "affected_unavailable_count": int(
                    (affected & group["source_status"].eq("unavailable")).sum()
                ),
                "combined_observed_share_of_affected_set": float(
                    group.loc[affected, "observed_area_weight"].sum(min_count=1)
                ),
            }
        )
    annual = pd.DataFrame(annual_rows)

    material = municipality["ever_top_50"]
    unresolved_material = material & ~municipality["administrative_availability_resolved"]
    gate = {
        "status": "blocked" if unresolved_material.any() else "passed",
        "criterion": (
            "affected municipality ever enters an annual Top-50 and its unavailable "
            "years are not explained by official municipality installation evidence"
        ),
        "material_municipality_count": int(material.sum()),
        "material_municipalities": "; ".join(
            municipality.loc[material, "municipality"].tolist()
        ),
        "administratively_resolved_material_count": int(
            (material & municipality["administrative_availability_resolved"]).sum()
        ),
        "unresolved_material_municipality_count": int(unresolved_material.sum()),
        "unresolved_material_municipalities": "; ".join(
            municipality.loc[unresolved_material, "municipality"].tolist()
        ),
        "maximum_affected_observed_weight": float(
            municipality["maximum_observed_area_weight"].max()
        ),
        "maximum_annual_combined_affected_share": float(
            annual["combined_observed_share_of_affected_set"].max()
        ),
    }
    return municipality, annual, gate


def write_gate_report(
    output_root: Path,
    municipality: pd.DataFrame,
    annual: pd.DataFrame,
    gate: dict[str, object],
) -> Path:
    leaders = municipality.head(10)
    leader_lines = "\n".join(
        f"- {row.municipality}: max observed share "
        f"{row.maximum_observed_area_weight:.4%}; max observed area "
        f"{row.maximum_observed_harvested_area_ha:,.0f} ha; "
        f"Top-50={row.ever_top_50}"
        for row in leaders.itertuples(index=False)
    )
    report = f"""# EXP-01S Missingness Materiality Gate

## Weight definition

The analysis weight is the observed-only normalized / reported harvested-area
share:

`w_obs(i,t) = A(i,t) / sum(A(j,t) for j in O_t)`

`O_t` contains source numeric values and explicit zero (`-`) observations.
Source `...` values remain unavailable (`NaN`) and are not imputed as zero.
This is not an estimate of the unobserved true São Paulo harvested-area
distribution.

## Gate result

- Status: **{gate['status']}**
- Conservative materiality criterion: {gate['criterion']}
- Affected municipalities: {len(municipality)}
- Affected municipalities meeting the criterion:
  {gate['material_municipality_count']}
- Material municipalities explained by official installation evidence:
  {gate['administratively_resolved_material_count']}
- Material municipalities with unresolved missingness:
  {gate['unresolved_material_municipality_count']}
- Maximum observed share among affected municipalities:
  {gate['maximum_affected_observed_weight']:.4%}
- Maximum annual combined observed share of the affected set:
  {gate['maximum_annual_combined_affected_share']:.4%}

Highest observed shares among affected municipalities:

{leader_lines}

## Decision

If the status is `blocked`, the main metrics are not computed or interpreted.
If it is `passed`, every historically Top-50 affected municipality has official
evidence that its only unavailable years predate municipal installation.
"""
    path = output_root / "EXP_01S_missingness_materiality_gate.md"
    path.write_text(report, encoding="utf-8")
    return path


def run_gate(processed_path: Path, raw_path: Path, output_root: Path) -> dict[str, object]:
    processed = pd.read_csv(processed_path, dtype={"ibge_code": "string"})
    processed = validate_processed_structure(processed)
    symbol_data, _ = load_raw_harvested_area(raw_path)
    panel = build_observed_panel(processed, symbol_data)
    municipality, annual, gate = build_missingness_materiality(panel)
    tables = output_root / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    municipality.to_csv(
        tables / "unavailable_municipality_materiality.csv", index=False
    )
    annual.to_csv(tables / "annual_affected_set_observed_share.csv", index=False)
    panel[[
        "ibge_code", "municipality", "year", "raw_area_symbol", "source_status",
        "reported_harvested_area_ha", "observed_area_weight",
    ]].to_csv(tables / "observed_only_weight_panel.csv", index=False)
    write_gate_report(output_root, municipality, annual, gate)
    print(f"EXP-01S materiality gate: {gate['status']}")
    print(f"Material affected municipalities: {gate['material_municipality_count']}")
    return gate


def _year_series(panel: pd.DataFrame, year: int) -> pd.Series:
    values = panel.loc[
        panel["year"].eq(year) & panel["is_reported"],
        ["ibge_code", "observed_area_weight"],
    ].set_index("ibge_code")["observed_area_weight"]
    if not np.isclose(values.sum(), 1.0, atol=WEIGHT_TOLERANCE, rtol=0):
        raise ValueError(f"Observed weights do not sum to one in {year}")
    return values


def reported_distribution_tv(first: pd.Series, second: pd.Series) -> float:
    """TV between reported-share distributions on their union of supports.

    Extending a probability distribution by zero outside its reported support
    is not an imputation of unavailable harvested area.
    """

    support = first.index.union(second.index)
    return float(
        0.5
        * (
            first.reindex(support, fill_value=0.0)
            - second.reindex(support, fill_value=0.0)
        ).abs().sum()
    )


def common_reported_spearman(first: pd.Series, second: pd.Series) -> tuple[float, int]:
    common = first.index.intersection(second.index)
    return float(first.loc[common].corr(second.loc[common], method="spearman")), len(common)


def calculate_annual_metrics(
    panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[int, int], set[str]]]:
    weights = {year: _year_series(panel, year) for year in range(START_YEAR, END_YEAR + 1)}
    top_sets = annual_top_sets(panel)
    adjacent = []
    for year in range(START_YEAR + 1, END_YEAR + 1):
        first, second = weights[year - 1], weights[year]
        spearman, common_count = common_reported_spearman(first, second)
        row = {
            "year_from": year - 1,
            "year_to": year,
            "total_variation_reported_share": reported_distribution_tv(first, second),
            "spearman_common_reported": spearman,
            "common_reported_municipalities": common_count,
        }
        for k in TOP_KS:
            row[f"top_{k}_membership_overlap"] = len(
                top_sets[(year - 1, k)] & top_sets[(year, k)]
            ) / k
        adjacent.append(row)

    concentration = []
    for year, values in weights.items():
        ordered = values.sort_values(ascending=False, kind="mergesort")
        row = {
            "year": year,
            "reported_municipality_count": int(len(values)),
            "reported_share_hhi": float((values ** 2).sum()),
        }
        for k in TOP_KS:
            row[f"top_{k}_reported_share"] = float(ordered.head(k).sum())
        concentration.append(row)
    return pd.DataFrame(adjacent), pd.DataFrame(concentration), top_sets


def calculate_municipality_stability(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_years = END_YEAR - START_YEAR + 1
    for (code, municipality), group in panel.groupby(["ibge_code", "municipality"]):
        group = group.sort_values("year")
        weights = group.set_index("year")["observed_area_weight"]
        observed = weights.dropna()
        consecutive = weights.diff().abs().where(weights.notna() & weights.shift().notna()).dropna()
        positive = weights.gt(0) & weights.notna()
        positive_years = weights.index[positive]
        rows.append(
            {
                "ibge_code": code,
                "municipality": municipality,
                "reported_year_count": int(weights.notna().sum()),
                "unavailable_year_count": int(weights.isna().sum()),
                "mean_annual_observed_weight": float(observed.mean()) if len(observed) else np.nan,
                "median_annual_observed_weight": float(observed.median()) if len(observed) else np.nan,
                "std_annual_observed_weight": float(observed.std(ddof=1)) if len(observed) > 1 else np.nan,
                "minimum_annual_observed_weight": float(observed.min()) if len(observed) else np.nan,
                "maximum_annual_observed_weight": float(observed.max()) if len(observed) else np.nan,
                "full_sample_observed_weight_range": float(observed.max() - observed.min()) if len(observed) else np.nan,
                "adjacent_reported_pair_count": int(len(consecutive)),
                "mean_annual_absolute_change": float(consecutive.mean()) if len(consecutive) else np.nan,
                "median_annual_absolute_change": float(consecutive.median()) if len(consecutive) else np.nan,
                "maximum_annual_absolute_change": float(consecutive.max()) if len(consecutive) else np.nan,
                "first_positive_weight_year": int(positive_years.min()) if len(positive_years) else np.nan,
                "last_positive_weight_year": int(positive_years.max()) if len(positive_years) else np.nan,
                "positive_weight_year_count": int(positive.sum()),
                "positive_weight_year_share": float(positive.sum() / total_years),
            }
        )
    return pd.DataFrame(rows)


def calculate_anchor_tables(
    panel: pd.DataFrame,
    top_sets: dict[tuple[int, int], set[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    weights = {year: _year_series(panel, year) for year in ANCHOR_YEARS}
    pairs = [(1990, 2000), (2000, 2010), (2010, 2020), (2020, 2025), (1990, 2025)]
    comparisons = []
    for first_year, second_year in pairs:
        first, second = weights[first_year], weights[second_year]
        spearman, common_count = common_reported_spearman(first, second)
        row = {
            "year_from": first_year,
            "year_to": second_year,
            "total_variation_reported_share": reported_distribution_tv(first, second),
            "spearman_common_reported": spearman,
            "common_reported_municipalities": common_count,
        }
        for k in TOP_KS:
            row[f"top_{k}_membership_overlap"] = len(
                top_sets[(first_year, k)] & top_sets[(second_year, k)]
            ) / k
        comparisons.append(row)

    tops = []
    for year in ANCHOR_YEARS:
        group = panel.loc[panel["year"].eq(year) & panel["is_reported"]].sort_values(
            ["observed_area_weight", "ibge_code"], ascending=[False, True]
        ).head(50)
        for rank, row in enumerate(group.itertuples(index=False), start=1):
            tops.append(
                {
                    "year": year,
                    "rank": rank,
                    "ibge_code": row.ibge_code,
                    "municipality": row.municipality,
                    "reported_harvested_area_ha": row.reported_harvested_area_ha,
                    "observed_area_weight": row.observed_area_weight,
                }
            )
    return pd.DataFrame(comparisons), pd.DataFrame(tops)


def calculate_sensitivity(adjacent: pd.DataFrame) -> pd.DataFrame:
    flagged = {1998, 2006}
    primary = adjacent
    excluded = adjacent.loc[
        ~adjacent["year_from"].isin(flagged) & ~adjacent["year_to"].isin(flagged)
    ]
    rows = []
    metrics = [
        "total_variation_reported_share",
        "spearman_common_reported",
        "top_10_membership_overlap",
        "top_25_membership_overlap",
        "top_50_membership_overlap",
    ]
    for metric in metrics:
        for statistic in ("mean", "median", "min", "max"):
            primary_value = float(getattr(primary[metric], statistic)())
            excluded_value = float(getattr(excluded[metric], statistic)())
            rows.append(
                {
                    "metric": metric,
                    "statistic": statistic,
                    "primary_1990_2025": primary_value,
                    "excluding_pairs_touching_1998_or_2006": excluded_value,
                    "difference_excluding_minus_primary": excluded_value - primary_value,
                    "primary_pair_count": len(primary),
                    "sensitivity_pair_count": len(excluded),
                }
            )
    return pd.DataFrame(rows)


def create_figures(
    panel: pd.DataFrame,
    adjacent: pd.DataFrame,
    concentration: pd.DataFrame,
    municipality: pd.DataFrame,
    figure_root: Path,
) -> None:
    figure_root.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(adjacent["year_to"], adjacent["total_variation_reported_share"], marker="o", ms=3)
    ax.set(title="Annual total variation in reported municipality shares", xlabel="Year", ylabel="Total variation")
    fig.tight_layout()
    fig.savefig(figure_root / "annual_total_variation.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(adjacent["year_to"], adjacent["spearman_common_reported"], marker="o", ms=3)
    ax.set(title="Adjacent-year rank stability among commonly reported municipalities", xlabel="Year", ylabel="Spearman correlation")
    fig.tight_layout()
    fig.savefig(figure_root / "annual_rank_stability.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for k in TOP_KS:
        ax.plot(concentration["year"], concentration[f"top_{k}_reported_share"], label=f"Top {k}")
    ax.set(title="Concentration of reported municipality harvested-area shares", xlabel="Year", ylabel="Combined reported share")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_root / "top_k_concentration.png", dpi=180)
    plt.close(fig)

    top_codes = municipality.nlargest(25, "mean_annual_observed_weight")["ibge_code"]
    names = municipality.set_index("ibge_code")["municipality"]
    heat = panel.loc[panel["ibge_code"].isin(top_codes)].pivot(
        index="ibge_code", columns="year", values="observed_area_weight"
    ).loc[top_codes]
    fig, ax = plt.subplots(figsize=(12, 8))
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad("#d9d9d9")
    image = ax.imshow(np.ma.masked_invalid(heat.to_numpy()), aspect="auto", cmap=cmap)
    ax.set_yticks(range(len(heat)), labels=[names[code] for code in heat.index])
    ax.set_xticks(range(0, len(heat.columns), 5), labels=heat.columns[::5])
    ax.set(title="Observed harvested-area shares for leading municipalities", xlabel="Year")
    fig.colorbar(image, ax=ax, label="Observed share")
    fig.tight_layout()
    fig.savefig(figure_root / "municipality_weight_heatmap.png", dpi=180)
    plt.close(fig)


def _summary_values(frame: pd.DataFrame, column: str) -> str:
    values = frame[column]
    return (
        f"mean {values.mean():.4f}, median {values.median():.4f}, "
        f"SD {values.std(ddof=1):.4f}, min {values.min():.4f}, max {values.max():.4f}"
    )


def write_execution_report(
    output_root: Path,
    gate: dict[str, object],
    adjacent: pd.DataFrame,
    concentration: pd.DataFrame,
    anchors: pd.DataFrame,
    municipality: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> Path:
    high_tv = adjacent.nlargest(5, "total_variation_reported_share")
    low_rank = adjacent.nsmallest(5, "spearman_common_reported")
    high_tv_lines = "\n".join(
        f"- {r.year_from}–{r.year_to}: {r.total_variation_reported_share:.4f}"
        for r in high_tv.itertuples(index=False)
    )
    low_rank_lines = "\n".join(
        f"- {r.year_from}–{r.year_to}: {r.spearman_common_reported:.4f}"
        for r in low_rank.itertuples(index=False)
    )
    anchor_lines = "\n".join(
        f"- {r.year_from}–{r.year_to}: TV {r.total_variation_reported_share:.4f}; "
        f"Spearman {r.spearman_common_reported:.4f}; Top-10/25/50 overlap "
        f"{r.top_10_membership_overlap:.2f}/{r.top_25_membership_overlap:.2f}/"
        f"{r.top_50_membership_overlap:.2f}"
        for r in anchors.itertuples(index=False)
    )
    sensitivity_means = sensitivity.loc[sensitivity["statistic"].eq("mean")]
    sensitivity_lines = "\n".join(
        f"- {r.metric}: {r.primary_1990_2025:.4f} primary; "
        f"{r.excluding_pairs_touching_1998_or_2006:.4f} excluding affected pairs; "
        f"difference {r.difference_excluding_minus_primary:+.4f}"
        for r in sensitivity_means.itertuples(index=False)
    )
    top_average = municipality.nlargest(10, "mean_annual_observed_weight")
    top_average_lines = "\n".join(
        f"- {r.municipality}: {r.mean_annual_observed_weight:.4%}"
        for r in top_average.itertuples(index=False)
    )
    top_instability = municipality.nlargest(5, "maximum_annual_absolute_change")
    top_instability_lines = "\n".join(
        f"- {r.municipality}: maximum adjacent observed-share change "
        f"{r.maximum_annual_absolute_change:.4f}; mean adjacent change "
        f"{r.mean_annual_absolute_change:.4f}"
        for r in top_instability.itertuples(index=False)
    )
    report = f"""# EXP-01S Execution Report

## Definition and scope

EXP-01S analyzes the observed-only normalized / reported harvested-area share:

`w_obs(i,t) = A(i,t) / sum(A(j,t) for j in O_t)`

`O_t` includes reported numeric harvested area and explicit zero (`-`). Source
`...` remains unavailable (`NaN`) and is never imputed as zero. The results do
not estimate the unobserved true São Paulo harvested-area distribution.

TV and related metrics describe changes in the **reported municipality
harvested-area share distribution**, not literal physical redistribution of
hectares.

For TV only, each annual reported-share distribution is embedded on the union
of the two years' reported supports with probability mass zero outside its own
support. This is a mathematical representation of `w_obs`, not an assignment
of zero harvested area to a source `...` cell. Spearman uses only
municipalities reported in both compared years.

## Missingness materiality gate

- Gate: **{gate['status']}**
- 127 municipalities contain at least one `...`.
- Four ever enter an annual Top-50: Guatapará, Tarumã, Motuca, and Santo Antônio
  do Aracanguá.
- All four contain `...` only in 1990–1992, and official IBGE histories record
  installation on 1993-01-01. Their high-share missingness is therefore
  explained by administrative availability.
- No municipality with unresolved `...` ever enters an annual Top-50.
- No affected municipality ever enters the annual Top-10; only Guatapará enters
  the annual Top-25.

## Validation

- 642 municipality rows in every year, 1990–2025.
- `(ibge_code, year)` duplicates: 0.
- Reconstructed `w_obs` sums to one within `1e-12` every year.
- Stored numeric `area_weight` matches reconstructed `w_obs` within `1e-12`.
- 1998 and 2006 remain in the primary analysis. The separately queried IBGE
  state total differs from the municipality sum by -200 ha (-0.0078%) and
  -2,372 ha (-0.0679%), respectively.

## Adjacent-year reported-share stability

- Total variation: {_summary_values(adjacent, 'total_variation_reported_share')}.
- Spearman among municipalities reported in both adjacent years:
  {_summary_values(adjacent, 'spearman_common_reported')}.

Largest TV changes:

{high_tv_lines}

The largest value, 1992–1993, coincides with the installation of multiple new
municipalities on 1993-01-01. It therefore includes a change in reported
municipality support and must not be interpreted as literal physical movement
of harvested hectares. Anchor comparisons involving 1990 carry the same
administrative-boundary caveat.

Lowest adjacent-year rank correlations:

{low_rank_lines}

## Concentration and membership stability

- Mean Top-10 reported share: {concentration['top_10_reported_share'].mean():.4%}.
- Mean Top-25 reported share: {concentration['top_25_reported_share'].mean():.4%}.
- Mean Top-50 reported share: {concentration['top_50_reported_share'].mean():.4%}.
- Mean adjacent Top-10 overlap: {adjacent['top_10_membership_overlap'].mean():.2%}.
- Mean adjacent Top-25 overlap: {adjacent['top_25_membership_overlap'].mean():.2%}.
- Mean adjacent Top-50 overlap: {adjacent['top_50_membership_overlap'].mean():.2%}.

Municipalities with the largest mean reported shares:

{top_average_lines}

Largest municipality-level adjacent observed-share changes:

{top_instability_lines}

## Anchor-year comparison

{anchor_lines}

## 1998/2006 sensitivity

The sensitivity excludes adjacent pairs touching 1998 or 2006, leaving 31 of
35 adjacent comparisons. Mean results are:

{sensitivity_lines}

The exclusion does not reverse the descriptive finding: rank correlations and
Top-K overlaps remain high relative to the size of exact-share changes. The
full numerical sensitivity table is retained for review rather than imposing a
stable/unstable cutoff.

## Answers returned to Chat

1. Missing values have mixed semantics: `-` is explicit zero; `...` is
   unavailable. `w_obs` is normalized only over `O_t`.
2. Typical one-year change is summarized by the TV mean and median above.
3. The five largest-TV year pairs are listed above.
4. Rank stability is generally higher than exact-share stability, but zero
   ties and changing reported support remain limitations.
5. Top-producer concentration and membership are reported in the annual table.
6. Anchor comparisons show how cumulative differences exceed many adjacent
   changes; 1990–2025 results are in the anchor table.
7. The evidence supports testing fixed, lagged, and rolling weights later; it
   does not select one for EXP-01B.
8. Data-quality warnings remain: unavailable values, administrative availability,
   and small 1998/2006 state-versus-municipality reconciliation differences.

## Files and commands

Tables and figures are under this output directory. The analysis was run from
the repository's `data/processed/sp_sugarcane_annual.csv` and
`data/raw/tabela5457.xlsx`. No source downloader or existing ETL was changed.

Created or refreshed:

- `EXP_01S_execution_report.md`
- `EXP_01S_missingness_materiality_gate.md`
- 13 analysis and validation CSV tables under `tables/`
- `figures/annual_total_variation.png`
- `figures/annual_rank_stability.png`
- `figures/top_k_concentration.png`
- `figures/municipality_weight_heatmap.png`

Commands run:

- `python -m pytest -q -p no:cacheprovider work/exp01s_impl/src/tests/analysis`
- `python -m src.analysis.exp01s_observed_weight_stability --project-root <repo> --output <output>`
- Existing repository ETL validator test module.

Test results:

- EXP-01S analysis tests: 16 passed.
- Existing repository ETL validator tests: 9 passed.
"""
    path = output_root / "EXP_01S_execution_report.md"
    path.write_text(report, encoding="utf-8")
    return path


def run_full_analysis(
    processed_path: Path, raw_path: Path, output_root: Path
) -> dict[str, object]:
    processed = pd.read_csv(processed_path, dtype={"ibge_code": "string"})
    processed = validate_processed_structure(processed)
    symbol_data, state_totals = load_raw_harvested_area(raw_path)
    panel = build_observed_panel(processed, symbol_data)
    materiality, affected_annual, gate = build_missingness_materiality(panel)
    tables = output_root / "tables"
    figures = output_root / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    materiality.to_csv(tables / "unavailable_municipality_materiality.csv", index=False)
    affected_annual.to_csv(tables / "annual_affected_set_observed_share.csv", index=False)
    panel[[
        "ibge_code", "municipality", "year", "raw_area_symbol", "source_status",
        "reported_harvested_area_ha", "observed_area_weight",
    ]].to_csv(tables / "observed_only_weight_panel.csv", index=False)
    write_gate_report(output_root, materiality, affected_annual, gate)
    if gate["status"] == "blocked":
        return gate

    coverage = (
        panel.groupby("year", as_index=False)
        .agg(
            municipality_rows=("ibge_code", "size"),
            reported_observations=("is_reported", "sum"),
            explicit_zero_observations=("source_status", lambda s: int(s.eq("absolute_zero").sum())),
            numeric_zero_observations=("source_status", lambda s: int(s.eq("numeric_zero").sum())),
            unavailable_observations=("source_status", lambda s: int(s.eq("unavailable").sum())),
            total_reported_harvested_area_ha=("reported_harvested_area_ha", "sum"),
            positive_weight_municipalities=("observed_area_weight", lambda s: int(s.gt(0).sum())),
            observed_weight_sum=("observed_area_weight", "sum"),
        )
        .merge(state_totals, on="year", how="left", validate="one_to_one")
    )
    coverage["municipality_sum_minus_state_total_ha"] = (
        coverage["total_reported_harvested_area_ha"]
        - coverage["ibge_state_total_area_ha"]
    )
    coverage["municipality_sum_minus_state_total_share"] = (
        coverage["municipality_sum_minus_state_total_ha"]
        / coverage["ibge_state_total_area_ha"]
    )
    coverage.to_csv(tables / "annual_data_coverage.csv", index=False)

    adjacent, concentration, top_sets = calculate_annual_metrics(panel)
    municipality = calculate_municipality_stability(panel)
    anchors, anchor_top = calculate_anchor_tables(panel, top_sets)
    sensitivity = calculate_sensitivity(adjacent)

    municipality.to_csv(tables / "municipality_weight_stability.csv", index=False)
    municipality.nlargest(50, "mean_annual_observed_weight").to_csv(
        tables / "municipalities_largest_average_reported_share.csv", index=False
    )
    municipality.nlargest(50, "maximum_annual_absolute_change").to_csv(
        tables / "municipalities_largest_year_to_year_instability.csv", index=False
    )
    adjacent[[
        "year_from", "year_to", "total_variation_reported_share"
    ]].to_csv(tables / "annual_weight_redistribution.csv", index=False)
    adjacent[[
        "year_from", "year_to", "spearman_common_reported",
        "common_reported_municipalities",
    ]].to_csv(tables / "annual_rank_stability.csv", index=False)
    annual_combined = concentration.merge(adjacent, left_on="year", right_on="year_to", how="left")
    annual_combined.to_csv(tables / "annual_concentration_and_stability.csv", index=False)
    anchors.to_csv(tables / "anchor_year_comparison.csv", index=False)
    anchor_top.to_csv(tables / "anchor_year_top_municipalities.csv", index=False)
    sensitivity.to_csv(tables / "state_total_discrepancy_sensitivity.csv", index=False)
    create_figures(panel, adjacent, concentration, municipality, figures)
    write_execution_report(
        output_root, gate, adjacent, concentration, anchors, municipality, sensitivity
    )
    print("EXP-01S observed-only stability analysis completed")
    return gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    run_full_analysis(
        root / "data/processed/sp_sugarcane_annual.csv",
        root / "data/raw/tabela5457.xlsx",
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
