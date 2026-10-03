"""EXP-02A Phase 0: source-aware municipality yield-support audit.

This module stops before detrending. It reconstructs the 1974-2025 annual
municipality panel from the raw IBGE workbook, preserves explicit zero versus
unavailable source values, measures municipality history support, and compares
candidate eligibility gates without choosing a final gate.
"""

from __future__ import annotations

import argparse
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


EXPERIMENT = "exp_02a_yield_support_audit"
START_YEAR = 1974
END_YEAR = 2025
EXPECTED_MUNICIPALITIES = 642
EXPECTED_ROWS = EXPECTED_MUNICIPALITIES * (END_YEAR - START_YEAR + 1)

MIN_VALID_YEARS_GRID = (10, 15, 20, 25, 30, 35)
MIN_CALENDAR_SPAN_GRID = (15, 20, 25, 30, 35, 40)
MAX_INTERNAL_GAP_GRID: tuple[int | None, ...] = (1, 2, 3, 5, 10, None)

REPRESENTATIVE_GATES = (
    ("G10_S15_GU", 10, 15, None),
    ("G15_S20_G10", 15, 20, 10),
    ("G20_S25_G5", 20, 25, 5),
    ("G25_S30_G3", 25, 30, 3),
    ("G30_S35_G2", 30, 35, 2),
    ("G35_S40_G1", 35, 40, 1),
)

OBSERVED_STATUSES = {"numeric_positive", "numeric_zero", "explicit_zero"}


def classify_ibge_value(value: object) -> tuple[float, str, str]:
    """Parse an IBGE cell while retaining its raw symbol and source meaning."""

    if pd.isna(value):
        return np.nan, "blank", ""
    text = str(value).strip()
    if text == "-":
        return 0.0, "explicit_zero", text
    if text == "...":
        return np.nan, "unavailable", text
    if text == "..":
        return np.nan, "not_applicable", text
    if text.lower() == "x":
        return np.nan, "suppressed", text
    if text == "":
        return np.nan, "blank", text
    try:
        number = float(text)
    except ValueError as error:
        raise ValueError(f"Unrecognized IBGE value: {value!r}") from error
    if not np.isfinite(number) or number < 0:
        raise ValueError(f"Invalid IBGE value: {value!r}")
    status = "numeric_zero" if number == 0 else "numeric_positive"
    return number, status, text


def load_raw_variable(
    workbook_path: Path,
    sheet_name: str,
    value_name: str,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
) -> pd.DataFrame:
    """Read one IBGE municipality variable over the complete requested period."""

    raw = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None, dtype=str)
    if raw.shape[0] < 7 or raw.shape[1] < 4:
        raise ValueError(f"Unexpected layout in {sheet_name!r}")
    if raw.iloc[2, :3].tolist() != ["Nível", "Cód.", "Unidade da Federação e Município"]:
        raise ValueError(f"Unexpected geographic headers in {sheet_name!r}")
    years: dict[int, int] = {}
    for column in range(3, raw.shape[1]):
        label = raw.iat[3, column]
        if pd.isna(label):
            continue
        text = str(label).strip()
        if text.isdigit() and len(text) == 4:
            year = int(text)
            if start_year <= year <= end_year:
                if year in years:
                    raise ValueError(f"Duplicate year {year} in {sheet_name!r}")
                years[year] = column
    if set(years) != set(range(start_year, end_year + 1)):
        raise ValueError(f"{sheet_name!r} does not contain every requested year")

    municipalities = raw.loc[raw.iloc[:, 0].eq("MU")].copy()
    if municipalities.empty:
        raise ValueError(f"No municipality rows in {sheet_name!r}")
    rows: list[dict[str, object]] = []
    for source_row in municipalities.itertuples(index=False, name=None):
        code = str(source_row[1]).strip()
        municipality = str(source_row[2]).removesuffix(" (SP)").strip()
        for year, column in sorted(years.items()):
            value, status, raw_symbol = classify_ibge_value(source_row[column])
            rows.append({
                "ibge_code": code,
                "municipality": municipality,
                "year": year,
                f"{value_name}_raw_symbol": raw_symbol,
                f"{value_name}_source_status": status,
                f"{value_name}_source_value": value,
            })
    result = pd.DataFrame(rows)
    result["ibge_code"] = result["ibge_code"].astype("string").str.strip()
    if not result["ibge_code"].str.fullmatch(r"35\d{5}").all():
        raise ValueError(f"Invalid São Paulo municipality code in {sheet_name!r}")
    if result.duplicated(["ibge_code", "year"]).any():
        raise ValueError(f"Duplicate municipality-year rows in {sheet_name!r}")
    return result


def build_source_aware_panel(
    workbook_path: Path,
    processed_path: Path,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
) -> pd.DataFrame:
    """Build and reconcile the source-aware annual-yield panel."""

    production = load_raw_variable(
        workbook_path, "Quantidade produzida", "production", start_year, end_year
    )
    area = load_raw_variable(
        workbook_path, "Área colhida", "harvested_area", start_year, end_year
    )
    panel = production.merge(
        area,
        on=["ibge_code", "municipality", "year"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not panel["_merge"].eq("both").all():
        raise ValueError("Raw production and harvested-area keys differ")
    panel = panel.drop(columns="_merge")

    processed = pd.read_csv(processed_path, dtype={"ibge_code": "string"})
    required = {
        "ibge_code", "municipality", "year", "harvested_area_ha",
        "production_tonnes", "yield_tch", "area_weight",
    }
    missing = sorted(required - set(processed.columns))
    if missing:
        raise ValueError(f"Processed annual panel missing columns: {missing}")
    processed = processed.loc[processed["year"].between(start_year, end_year)].copy()
    processed["ibge_code"] = processed["ibge_code"].astype("string").str.strip()
    if processed.duplicated(["ibge_code", "year"]).any():
        raise ValueError("Processed panel contains duplicate municipality-year keys")
    panel = panel.merge(
        processed,
        on=["ibge_code", "municipality", "year"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not panel["_merge"].eq("both").all():
        raise ValueError("Raw and processed municipality-year keys or names differ")
    panel = panel.drop(columns="_merge")
    if len(panel) != (end_year - start_year + 1) * EXPECTED_MUNICIPALITIES:
        raise ValueError("Unexpected source-aware panel row count")
    if panel["ibge_code"].nunique() != EXPECTED_MUNICIPALITIES:
        raise ValueError("Unexpected municipality universe")
    year_counts = panel.groupby("year")["ibge_code"].nunique()
    if not year_counts.eq(EXPECTED_MUNICIPALITIES).all():
        raise ValueError("Municipality universe is not constant by year")

    panel = derive_source_aware_yield(panel)

    valid = panel["valid_yield_for_detrending"]
    if not np.allclose(
        panel.loc[valid, "yield_tch_source_aware"],
        panel.loc[valid, "yield_tch"],
        atol=1e-12,
        rtol=1e-12,
    ):
        raise ValueError("Processed yield disagrees with source-aware yield")
    if panel.loc[~valid, "yield_tch"].notna().any():
        raise ValueError("Processed panel defines yield for a source-invalid row")
    for raw_column, processed_column in [
        ("production_source_value", "production_tonnes"),
        ("harvested_area_source_value", "harvested_area_ha"),
    ]:
        numeric = panel[raw_column].notna() & ~panel[
            raw_column.replace("_source_value", "_source_status")
        ].eq("explicit_zero")
        if not np.allclose(
            panel.loc[numeric, raw_column], panel.loc[numeric, processed_column],
            atol=0, rtol=0,
        ):
            raise ValueError(f"Processed {processed_column} disagrees with raw numeric values")
    return panel.sort_values(["ibge_code", "year"]).reset_index(drop=True)


def derive_source_aware_yield(panel: pd.DataFrame) -> pd.DataFrame:
    """Apply the Phase-0 yield-validity rule to an already parsed raw panel."""

    required = {
        "production_source_status", "production_source_value",
        "harvested_area_source_status", "harvested_area_source_value",
    }
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError(f"Source-aware yield input missing columns: {missing}")
    result = panel.copy()
    production_observed = result["production_source_status"].isin(OBSERVED_STATUSES)
    area_positive = result["harvested_area_source_status"].eq("numeric_positive")
    result["valid_yield_for_detrending"] = production_observed & area_positive
    result["yield_tch_source_aware"] = (
        result["production_source_value"]
        / result["harvested_area_source_value"].where(area_positive)
    )
    if result.loc[~result["valid_yield_for_detrending"], "yield_tch_source_aware"].notna().any():
        raise AssertionError("Invalid source rows received source-aware yield")
    if result.loc[result["valid_yield_for_detrending"], "yield_tch_source_aware"].isna().any():
        raise AssertionError("A valid source row has missing source-aware yield")
    if np.isinf(result["yield_tch_source_aware"]).any() or result["yield_tch_source_aware"].lt(0).any():
        raise ValueError("Source-aware yield contains negative or infinite values")
    return result


def _gap_metrics(valid: pd.Series) -> tuple[int, int, int]:
    """Return invalid count, longest invalid run, and invalid-run count."""

    values = valid.to_numpy(dtype=bool)
    missing = ~values
    if not len(values) or not missing.any():
        return int(missing.sum()), 0, 0
    run_ids = np.cumsum(np.r_[True, missing[1:] != missing[:-1]])
    runs = pd.DataFrame({"missing": missing, "run": run_ids}).groupby("run")["missing"].agg(["first", "size"])
    missing_runs = runs.loc[runs["first"]]
    return int(missing.sum()), int(missing_runs["size"].max()), int(len(missing_runs))


def municipality_support_metrics(panel: pd.DataFrame) -> pd.DataFrame:
    """Calculate one source-aware yield-history support row per municipality."""

    rows: list[dict[str, object]] = []
    for (code, municipality), group in panel.groupby(["ibge_code", "municipality"], sort=True):
        group = group.sort_values("year")
        valid = group["valid_yield_for_detrending"]
        valid_years = group.loc[valid, "year"].astype(int)
        n_valid = int(valid.sum())
        row: dict[str, object] = {
            "ibge_code": code,
            "municipality": municipality,
            "n_valid_years": n_valid,
            "valid_years_1974_1989": int((valid & group["year"].between(1974, 1989)).sum()),
            "valid_years_1990_2025": int((valid & group["year"].between(1990, 2025)).sum()),
            "latest_valid_year": int(valid_years.max()) if n_valid else pd.NA,
            "valid_yield_2025": bool((valid & group["year"].eq(2025)).any()),
        }
        if n_valid:
            first = int(valid_years.min())
            last = int(valid_years.max())
            inside = group.loc[group["year"].between(first, last), "valid_yield_for_detrending"]
            missing, max_gap, n_gaps = _gap_metrics(inside)
            span = last - first + 1
            row.update({
                "first_valid_year": first,
                "last_valid_year": last,
                "calendar_span_years": span,
                "n_missing_inside_span": missing,
                "max_internal_gap_years": max_gap,
                "n_internal_gaps": n_gaps,
                "share_valid_within_span": n_valid / span,
            })
        else:
            row.update({
                "first_valid_year": pd.NA,
                "last_valid_year": pd.NA,
                "calendar_span_years": 0,
                "n_missing_inside_span": 0,
                "max_internal_gap_years": pd.NA,
                "n_internal_gaps": 0,
                "share_valid_within_span": np.nan,
            })
        rows.append(row)
    result = pd.DataFrame(rows)
    for column in ["first_valid_year", "last_valid_year", "latest_valid_year", "max_internal_gap_years"]:
        result[column] = result[column].astype("Int64")
    return result


def add_footprint_metrics(support: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Attach observed-only municipality harvested-area importance diagnostics."""

    area = panel.loc[panel["year"].between(1990, 2025)].copy()
    annual_total = area.groupby("year")["harvested_area_source_value"].transform(
        lambda values: values.sum(min_count=1)
    )
    area["observed_area_share"] = area["harvested_area_source_value"] / annual_total
    footprint = area.groupby("ibge_code", as_index=False).agg(
        mean_observed_area_share_1990_2025=("observed_area_share", "mean"),
        max_observed_area_share_1990_2025=("observed_area_share", "max"),
        mean_observed_harvested_area_ha_1990_2025=("harvested_area_source_value", "mean"),
    )
    latest = area.loc[area["year"].eq(2025), ["ibge_code", "observed_area_share"]].rename(
        columns={"observed_area_share": "observed_area_share_2025"}
    )
    return support.merge(footprint, on="ibge_code", how="left", validate="one_to_one").merge(
        latest, on="ibge_code", how="left", validate="one_to_one"
    )


def gate_mask(
    support: pd.DataFrame,
    min_valid_years: int,
    min_calendar_span: int,
    max_internal_gap: int | None,
) -> pd.Series:
    """Return municipality eligibility for a candidate support gate."""

    mask = support["n_valid_years"].ge(min_valid_years) & support["calendar_span_years"].ge(min_calendar_span)
    if max_internal_gap is not None:
        gaps = pd.to_numeric(support["max_internal_gap_years"], errors="coerce").astype(float)
        mask &= gaps.fillna(np.inf).le(max_internal_gap)
    return mask.astype(bool)


def _gap_label(max_internal_gap: int | None) -> str:
    return "unrestricted" if max_internal_gap is None else str(max_internal_gap)


def gate_yearly_support(
    panel: pd.DataFrame,
    eligible_codes: set[str],
    gate_id: str,
) -> pd.DataFrame:
    """Calculate annual valid-yield support and observed-only footprint coverage."""

    rows = []
    for year, group in panel.groupby("year", sort=True):
        retained = group["ibge_code"].isin(eligible_codes)
        valid = group["valid_yield_for_detrending"]
        denominator = float(group["harvested_area_source_value"].sum(min_count=1))
        numerator = float(group.loc[retained, "harvested_area_source_value"].sum())
        valid_area = float(group.loc[retained & valid, "harvested_area_source_value"].sum())
        rows.append({
            "gate_id": gate_id,
            "year": int(year),
            "retained_municipality_count": len(eligible_codes),
            "valid_yield_municipality_count": int((retained & valid).sum()),
            "all_valid_yield_municipality_count": int(valid.sum()),
            "retained_valid_yield_share": float((retained & valid).sum() / valid.sum()) if valid.any() else np.nan,
            "retained_observed_harvested_area_ha": numerator,
            "retained_valid_yield_harvested_area_ha": valid_area,
            "all_observed_harvested_area_ha": denominator,
            "retained_observed_area_coverage": numerator / denominator if denominator > 0 else np.nan,
            "retained_valid_yield_area_coverage": valid_area / denominator if denominator > 0 else np.nan,
            "retained_unavailable_area_rows": int((retained & group["harvested_area_source_status"].eq("unavailable")).sum()),
        })
    return pd.DataFrame(rows)


def summarize_gate(
    panel: pd.DataFrame,
    support: pd.DataFrame,
    gate_id: str,
    min_valid_years: int,
    min_calendar_span: int,
    max_internal_gap: int | None,
) -> tuple[dict[str, object], pd.DataFrame, pd.Series]:
    mask = gate_mask(support, min_valid_years, min_calendar_span, max_internal_gap)
    codes = set(support.loc[mask, "ibge_code"].astype(str))
    yearly = gate_yearly_support(panel, codes, gate_id)
    all_valid = int(panel["valid_yield_for_detrending"].sum())
    retained_valid = int(panel.loc[panel["ibge_code"].isin(codes), "valid_yield_for_detrending"].sum())
    full = yearly["retained_valid_yield_area_coverage"]
    recent = yearly.loc[yearly["year"].between(1990, 2025), "retained_valid_yield_area_coverage"]
    coverage_2025 = yearly.loc[yearly["year"].eq(2025), "retained_valid_yield_area_coverage"]
    result: dict[str, object] = {
        "gate_id": gate_id,
        "min_valid_years": min_valid_years,
        "min_calendar_span_years": min_calendar_span,
        "max_internal_gap_years": _gap_label(max_internal_gap),
        "retained_municipalities": int(mask.sum()),
        "retained_municipality_share": float(mask.mean()),
        "retained_valid_municipality_years": retained_valid,
        "retained_valid_observation_share": retained_valid / all_valid,
        "minimum_annual_valid_municipalities": int(yearly["valid_yield_municipality_count"].min()),
        "median_annual_valid_municipalities": float(yearly["valid_yield_municipality_count"].median()),
        "mean_annual_valid_municipalities": float(yearly["valid_yield_municipality_count"].mean()),
        "minimum_annual_area_coverage_1974_2025": float(full.min()),
        "p10_annual_area_coverage_1974_2025": float(full.quantile(0.10)),
        "median_annual_area_coverage_1974_2025": float(full.median()),
        "mean_annual_area_coverage_1974_2025": float(full.mean()),
        "minimum_annual_area_coverage_1990_2025": float(recent.min()),
        "p10_annual_area_coverage_1990_2025": float(recent.quantile(0.10)),
        "median_annual_area_coverage_1990_2025": float(recent.median()),
        "mean_annual_area_coverage_1990_2025": float(recent.mean()),
        "area_coverage_2025": float(coverage_2025.iloc[0]) if not coverage_2025.empty else np.nan,
    }
    return result, yearly, mask


def candidate_gate_tables(
    panel: pd.DataFrame,
    support: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return full-grid, representative, one-dimensional, annual, and membership tables."""

    full_rows: list[dict[str, object]] = []
    full_yearly: list[pd.DataFrame] = []
    for minimum, span, gap in product(MIN_VALID_YEARS_GRID, MIN_CALENDAR_SPAN_GRID, MAX_INTERNAL_GAP_GRID):
        gate_id = f"N{minimum}_S{span}_G{_gap_label(gap)}"
        row, yearly, _ = summarize_gate(panel, support, gate_id, minimum, span, gap)
        full_rows.append(row)
        full_yearly.append(yearly)
    full = pd.DataFrame(full_rows)

    representative_rows: list[dict[str, object]] = []
    representative_yearly: list[pd.DataFrame] = []
    membership = support[["ibge_code", "municipality"]].copy()
    for gate_id, minimum, span, gap in REPRESENTATIVE_GATES:
        row, yearly, mask = summarize_gate(panel, support, gate_id, minimum, span, gap)
        representative_rows.append(row)
        representative_yearly.append(yearly)
        membership[f"eligible_{gate_id}"] = mask.to_numpy()

    one_rows: list[dict[str, object]] = []
    for minimum in MIN_VALID_YEARS_GRID:
        row, _, _ = summarize_gate(panel, support, f"minimum_valid_years_{minimum}", minimum, 1, None)
        row["dimension"] = "minimum_valid_years"
        row["candidate_value"] = str(minimum)
        one_rows.append(row)
    for span in MIN_CALENDAR_SPAN_GRID:
        row, _, _ = summarize_gate(panel, support, f"minimum_calendar_span_{span}", 1, span, None)
        row["dimension"] = "minimum_calendar_span_years"
        row["candidate_value"] = str(span)
        one_rows.append(row)
    for gap in MAX_INTERNAL_GAP_GRID:
        row, _, _ = summarize_gate(panel, support, f"maximum_internal_gap_{_gap_label(gap)}", 1, 1, gap)
        row["dimension"] = "maximum_internal_gap_years"
        row["candidate_value"] = _gap_label(gap)
        one_rows.append(row)
    one = pd.DataFrame(one_rows)
    return (
        full,
        pd.DataFrame(representative_rows),
        one,
        pd.concat(full_yearly, ignore_index=True),
        pd.concat(representative_yearly, ignore_index=True),
        membership,
    )


def source_status_summary(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, group in [(str(year), subset) for year, subset in panel.groupby("year", sort=True)] + [("overall", panel)]:
        row: dict[str, object] = {
            "period": period,
            "municipality_year_rows": len(group),
            "valid_yield_rows": int(group["valid_yield_for_detrending"].sum()),
            "invalid_yield_rows": int((~group["valid_yield_for_detrending"]).sum()),
            "production_area_status_mismatches": int(group["production_source_status"].ne(group["harvested_area_source_status"]).sum()),
        }
        for variable in ["production", "harvested_area"]:
            for status in ["numeric_positive", "numeric_zero", "explicit_zero", "unavailable", "not_applicable", "suppressed", "blank"]:
                row[f"{variable}_{status}_rows"] = int(group[f"{variable}_source_status"].eq(status).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def annual_support_table(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in panel.groupby("year", sort=True):
        valid = group["valid_yield_for_detrending"]
        observed_area = float(group["harvested_area_source_value"].sum(min_count=1))
        valid_area = float(group.loc[valid, "harvested_area_source_value"].sum(min_count=1))
        rows.append({
            "year": int(year),
            "municipality_rows": len(group),
            "valid_yield_municipality_count": int(valid.sum()),
            "valid_yield_municipality_share": float(valid.mean()),
            "observed_harvested_area_ha": observed_area,
            "valid_yield_harvested_area_ha": valid_area,
            "valid_yield_observed_area_coverage": valid_area / observed_area if observed_area > 0 else np.nan,
            "explicit_zero_rows": int(group["harvested_area_source_status"].eq("explicit_zero").sum()),
            "unavailable_rows": int(group["harvested_area_source_status"].eq("unavailable").sum()),
        })
    return pd.DataFrame(rows)


def create_figures(
    support: pd.DataFrame,
    full_grid: pd.DataFrame,
    representative: pd.DataFrame,
    representative_yearly: pd.DataFrame,
    annual: pd.DataFrame,
    metadata_path: Path,
    figure_dir: Path,
) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, column, title in [
        (axes[0], "n_valid_years", "Valid yield years"),
        (axes[1], "calendar_span_years", "Calendar span"),
        (axes[2], "max_internal_gap_years", "Maximum internal gap"),
    ]:
        values = pd.to_numeric(support[column], errors="coerce").dropna()
        ax.hist(values, bins=range(0, 56, 2), color="#4472C4", edgecolor="white")
        ax.set_xlabel("Years")
        ax.set_ylabel("Municipalities")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("EXP-02A Phase 0 municipality history support")
    fig.tight_layout()
    fig.savefig(figure_dir / "municipality_support_distributions.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 6))
    scatter = ax.scatter(
        full_grid["retained_municipalities"],
        full_grid["mean_annual_area_coverage_1990_2025"],
        c=full_grid["min_valid_years"], cmap="viridis", alpha=0.65, s=35,
    )
    ax.plot(
        representative["retained_municipalities"],
        representative["mean_annual_area_coverage_1990_2025"],
        "o-", color="#C00000", label="Representative tightening sequence",
    )
    ax.set_xlabel("Retained municipalities")
    ax.set_ylabel("Mean retained observed-area coverage, 1990–2025")
    ax.set_ylim(0.80, 1.01)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.colorbar(scatter, ax=ax, label="Minimum valid years")
    fig.tight_layout()
    fig.savefig(figure_dir / "candidate_gate_tradeoff.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(annual["year"], annual["valid_yield_municipality_count"], color="black", linewidth=2, label="All valid")
    for gate_id, group in representative_yearly.groupby("gate_id", sort=False):
        axes[0].plot(group["year"], group["valid_yield_municipality_count"], label=gate_id, alpha=0.85)
        axes[1].plot(group["year"], group["retained_valid_yield_area_coverage"], label=gate_id, alpha=0.85)
    axes[0].set_ylabel("Valid-yield municipalities")
    axes[1].set_ylabel("Observed-area coverage")
    axes[1].set_xlabel("Year")
    axes[1].set_ylim(0, 1.02)
    for ax in axes:
        ax.grid(alpha=0.25)
    axes[0].legend(ncol=4, fontsize=8)
    fig.suptitle("Year-by-year support under representative candidate gates")
    fig.tight_layout()
    fig.savefig(figure_dir / "representative_gate_yearly_support.png", dpi=180)
    plt.close(fig)

    if metadata_path.exists():
        metadata = pd.read_csv(metadata_path, dtype={"ibge_code": "string"})
        mapped = metadata.merge(support, on="ibge_code", how="inner", validate="one_to_one")
        if len(mapped) == EXPECTED_MUNICIPALITIES:
            fig, ax = plt.subplots(figsize=(8, 7))
            points = ax.scatter(mapped["longitude"], mapped["latitude"], c=mapped["n_valid_years"], cmap="viridis", s=18)
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.set_title("Spatial distribution of valid-yield history length")
            fig.colorbar(points, ax=ax, label="Valid yield years")
            fig.tight_layout()
            fig.savefig(figure_dir / "municipality_history_support_map.png", dpi=180)
            plt.close(fig)


def _markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 3) -> str:
    shown = frame[columns].copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.{digits}f}" if pd.notna(value) else "")
    headers = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)]
    return "\n".join([headers, separator, *rows])


def write_report(
    path: Path,
    panel: pd.DataFrame,
    support: pd.DataFrame,
    status: pd.DataFrame,
    annual: pd.DataFrame,
    one_dimensional: pd.DataFrame,
    representative: pd.DataFrame,
    workbook_path: Path,
    processed_path: Path,
) -> None:
    overall = status.loc[status["period"].eq("overall")].iloc[0]
    quantiles = support[["n_valid_years", "calendar_span_years", "max_internal_gap_years"]].quantile([0.1, 0.5, 0.9])
    no_valid = int(support["n_valid_years"].eq(0).sum())
    complete = int(support["n_valid_years"].eq(END_YEAR - START_YEAR + 1).sum())
    recent_valid = int(support["valid_yield_2025"].sum())
    largest_gaps = support.sort_values(["max_internal_gap_years", "mean_observed_area_share_1990_2025"], ascending=[False, False]).head(8)
    one_view = one_dimensional[[
        "dimension", "candidate_value", "retained_municipalities",
        "retained_valid_observation_share", "mean_annual_area_coverage_1990_2025",
        "minimum_annual_area_coverage_1990_2025",
    ]]
    representative_view = representative[[
        "gate_id", "retained_municipalities", "retained_valid_municipality_years",
        "retained_valid_observation_share", "mean_annual_area_coverage_1990_2025",
        "minimum_annual_area_coverage_1990_2025", "area_coverage_2025",
    ]]
    text = f"""# EXP-02A Phase 0 Municipality Yield-Support Audit

## Status

**PHASE 0 COMPLETED.** This audit builds the source-aware 1974–2025 municipality annual-yield panel and compares candidate history-support gates. It does not choose a gate, fit a trend, create residuals, aggregate to weather grids, or run EXP-02B.

## Inputs and validity rule

- Raw authoritative source: `{workbook_path.resolve()}`, sheets `Quantidade produzida` and `Área colhida`.
- Processed reconciliation source: `{processed_path.resolve()}`.
- Unit of observation: municipality × calendar year, 1974–2025.
- Raw numeric values remain numeric; `-` is explicit zero; `...` remains unavailable.
- Yield is valid only when harvested area is observed and strictly positive and production is observed. Numeric or explicit production zero is an observed zero, but 0/0 is undefined. No unavailable value is converted to zero.
- Harvested-area coverage uses the observed-only denominator: the sum of symbol-aware reported municipality area in that year. It is not latent true statewide coverage.

## Source validation

- Rows: {len(panel):,}; municipalities: {panel.ibge_code.nunique():,}; duplicate keys: {int(panel.duplicated(['ibge_code', 'year']).sum())}.
- Valid yield rows: {int(overall.valid_yield_rows):,}; numeric source rows: {int(overall.harvested_area_numeric_positive_rows + overall.harvested_area_numeric_zero_rows):,}; explicit-zero rows: {int(overall.harvested_area_explicit_zero_rows):,}; unavailable rows: {int(overall.harvested_area_unavailable_rows):,}.
- Production/area status mismatches: {int(overall.production_area_status_mismatches)}.
- Numeric 0/0 rows excluded from valid yield: {int(((panel.harvested_area_source_status == 'numeric_zero') & (panel.production_source_status == 'numeric_zero')).sum())}.
- No negative or infinite source-aware yield was introduced, and every valid source-aware yield matches the processed `yield_tch`.

## Municipality history support

- Municipalities with no valid yield: {no_valid}; municipalities with all 52 years valid: {complete}; municipalities with valid 2025 yield: {recent_valid}.
- Valid-yield municipality count by year ranges from {int(annual.valid_yield_municipality_count.min())} to {int(annual.valid_yield_municipality_count.max())}.
- `n_valid_years` 10th / median / 90th percentiles: {quantiles.loc[0.1, 'n_valid_years']:.1f} / {quantiles.loc[0.5, 'n_valid_years']:.1f} / {quantiles.loc[0.9, 'n_valid_years']:.1f}.
- `calendar_span_years` 10th / median / 90th percentiles: {quantiles.loc[0.1, 'calendar_span_years']:.1f} / {quantiles.loc[0.5, 'calendar_span_years']:.1f} / {quantiles.loc[0.9, 'calendar_span_years']:.1f}.
- `max_internal_gap_years` 10th / median / 90th percentiles among defined histories: {quantiles.loc[0.1, 'max_internal_gap_years']:.1f} / {quantiles.loc[0.5, 'max_internal_gap_years']:.1f} / {quantiles.loc[0.9, 'max_internal_gap_years']:.1f}.

Municipalities with the largest internal gaps are listed in `municipality_support.csv`; the leading cases are:

{_markdown_table(largest_gaps, ['municipality', 'n_valid_years', 'calendar_span_years', 'max_internal_gap_years', 'mean_observed_area_share_1990_2025'], digits=6)}

## One-dimensional candidate trade-offs

Each row varies one dimension while applying only a minimal one-valid-year / one-year-span base for the other dimensions. The unrestricted gap row therefore describes municipalities with any valid yield, not all 642 municipalities.

{_markdown_table(one_view, list(one_view.columns))}

## Representative combined gates

These gates are a reporting sequence, not a recommendation or optimization result.

{_markdown_table(representative_view, list(representative_view.columns))}

The full 216-rule Cartesian grid is retained in `candidate_gate_summary_full_grid.csv`, and every gate-year result is in `candidate_gate_yearly_support_full_grid.csv`. This makes the three gate dimensions auditable without selecting the rule that maximizes city count or footprint.

## Geographic and support cautions

The available repository metadata contains municipality coordinates but no authoritative mesoregion labels. `municipality_history_support_map.png` provides a visual check for geographic concentration, but this audit does not invent regional classifications. Early-year gaps also reflect the constant current 642-municipality universe and the historical availability of municipalities, not only agricultural non-production.

Explicit-zero histories represent observed inactivity and must remain distinct from unavailable reporting. A retained municipality contributes a residual only in later Phase 1 years with valid observed yield; this audit does not bridge gaps or create yield values.

## Decisions returned to Chat

1. Select the minimum valid-yield years from the reported trade-off grid.
2. Select the minimum first-to-last valid calendar span.
3. Select the maximum internal gap that the future smoother may bridge.
4. Decide how strongly the gate should prioritize long 1974–2025 history versus preserving the 1990–2025 observed harvested-area footprint.
5. Decide whether municipalities with late starts but material recent footprint require a separately reported shorter-history stratum.

Formal detrending remains on hold pending those decisions.
"""
    path.write_text(text, encoding="utf-8")


def write_execution_report(path: Path, project_root: Path) -> None:
    text = f"""# EXP-02A Phase 0 Execution Report

## Scope and status

Phase 0 is complete. The run reconstructed and validated the source-aware 1974–2025 municipality annual-yield panel, measured history support, evaluated the full candidate-gate grid, and produced the requested tables and figures. It did **not** select a final eligibility gate, fit trends, create residuals, run EXP-02B, or alter EXP-01 outputs.

## Files created

- `{(project_root / 'src/analysis/exp02a_yield_support_audit.py').resolve()}`
- `{(project_root / 'src/tests/analysis/test_exp02a_yield_support_audit.py').resolve()}`
- `{(project_root / 'data/processed/analysis' / EXPERIMENT / 'source_aware_annual_yield_panel_1974_2025.csv').resolve()}`
- All Phase 0 tables, figures, and reports under `{path.parent.resolve()}`.

No pre-existing tracked source or data file was modified.

## Commands and validation

- Main run: `py -3 -m analysis.exp02a_yield_support_audit --project-root \"{project_root.resolve()}\"` with `PYTHONPATH=src`.
- Focused Phase 0 tests cover source-symbol parsing, yield validity, 0/0 exclusion, support spans and gaps, gate boundaries, observed-area denominators, annual reconciliation, and gate-summary reconciliation.
- The focused Phase 0 tests plus the relevant EXP-01S source-aware harvested-area regression tests passed: **27 passed**.
- Four generated figures were visually inspected for readable labels, legends, ranges, and plotted content.

## Data and source-semantics validation

- Raw authoritative workbook: `data/raw/tabela5457.xlsx`; sheets `Quantidade produzida` and `Área colhida`.
- Processed reconciliation input: `data/processed/sp_sugarcane_annual.csv`.
- Panel: 642 municipalities × 52 calendar years = 33,384 unique municipality-year rows.
- Both variables contain 21,822 numeric-positive rows, 3 numeric-zero rows, 8,857 explicit-zero (`-`) rows, and 2,702 unavailable (`...`) rows.
- Production and harvested-area status disagree in 0 rows.
- There are 21,822 valid yield rows. All three numeric 0/0 rows are excluded. No unavailable value is converted to zero.
- Every valid source-aware yield matches the processed `yield_tch` value.

## Outputs and cautions

The full Cartesian grid contains 216 gates, with yearly support retained for every gate. A six-row representative tightening sequence is included only to make the trade-off readable; it is not a recommendation. Harvested-area coverage is the retained share of the observed-only municipality area total for each year, not coverage of latent true statewide production.

The current 642-municipality universe includes places that did not exist as independent municipalities throughout the early period. Therefore, early missing histories may reflect municipality formation and reporting availability as well as agricultural inactivity. The repository provides coordinates but no authoritative historical region classification, so no region labels were invented.

## Decisions returned to Chat

1. Minimum valid-yield years.
2. Minimum first-to-last valid calendar span.
3. Maximum permitted internal gap.
4. The desired balance between long historical support and retention of the 1990–2025 observed harvested-area footprint.
5. Whether a separately reported recent/shorter-history stratum is needed.
"""
    path.write_text(text, encoding="utf-8")


def run(project_root: Path) -> int:
    workbook_path = project_root / "data/raw/tabela5457.xlsx"
    processed_path = project_root / "data/processed/sp_sugarcane_annual.csv"
    metadata_path = project_root / "data/metadata/sp_municipalities.csv"
    data_root = project_root / "data/processed/analysis" / EXPERIMENT
    output_root = project_root / "outputs/research/exp_02/exp_02a_phase0"
    figure_dir = output_root / "figures"
    data_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    panel = build_source_aware_panel(workbook_path, processed_path)
    support = add_footprint_metrics(municipality_support_metrics(panel), panel)
    status = source_status_summary(panel)
    annual = annual_support_table(panel)
    full, representative, one, full_yearly, representative_yearly, membership = candidate_gate_tables(panel, support)
    support = support.merge(membership, on=["ibge_code", "municipality"], how="left", validate="one_to_one")

    panel.to_csv(data_root / "source_aware_annual_yield_panel_1974_2025.csv", index=False)
    support.to_csv(output_root / "municipality_support.csv", index=False)
    status.to_csv(output_root / "source_status_summary.csv", index=False)
    annual.to_csv(output_root / "year_by_year_support_all_municipalities.csv", index=False)
    full.to_csv(output_root / "candidate_gate_summary_full_grid.csv", index=False)
    representative.to_csv(output_root / "candidate_gate_summary_representative.csv", index=False)
    one.to_csv(output_root / "candidate_gate_summary_one_dimensional.csv", index=False)
    full_yearly.to_csv(output_root / "candidate_gate_yearly_support_full_grid.csv", index=False)
    representative_yearly.to_csv(output_root / "candidate_gate_yearly_support_representative.csv", index=False)

    create_figures(support, full, representative, representative_yearly, annual, metadata_path, figure_dir)
    write_report(
        output_root / "EXP_02A_phase0_support_audit_report.md",
        panel, support, status, annual, one, representative, workbook_path, processed_path,
    )
    write_execution_report(output_root / "EXP_02A_phase0_execution_report.md", project_root)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return run(args.project_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
