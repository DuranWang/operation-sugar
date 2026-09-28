"""Build and validate an empirical NASA POWER municipality weather-group map.

No network requests. Groups are based on identical *complete daily* PRECTOTCORR,
T2M and RH2M series in one reference period and validated on separate periods.
A weather-group identifier is NOT an official NASA POWER grid identifier.

Example, from the repository root (adjust paths to where the existing CSVs live):
    python build_nasa_power_weather_group_mapping.py \
        --metadata data/metadata/sp_municipalities.csv \
        --reference data/raw/nasa_power/daily_weather/SP/19830101_19831231.csv \
        --validation data/raw/nasa_power/daily_weather/SP/20250101_20251231.csv \
        --output data/metadata/sp_nasa_power_weather_group_mapping.csv \
        --report data/metadata/sp_nasa_power_weather_group_validation.json
"""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

WEATHER = ("PRECTOTCORR", "T2M", "RH2M")
REQUIRED = {"Date", *WEATHER, "ibge_code", "municipality", "state", "latitude", "longitude"}
PERIOD_NAME = re.compile(r"^(\d{8})_(\d{8})\.csv$")


def read_metadata(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ibge_code": "string"})
    required = {"ibge_code", "municipality", "state", "latitude", "longitude"}
    if not required.issubset(df.columns) or df.empty:
        raise ValueError(f"Missing metadata columns or empty metadata: {path}")
    df["ibge_code"] = df["ibge_code"].str.strip()
    if df["ibge_code"].isna().any() or df["ibge_code"].duplicated().any():
        raise ValueError("Metadata IBGE codes must be unique and nonmissing")
    if df[list(required)].isna().any().any() or not df["state"].eq("SP").all():
        raise ValueError("Metadata must contain valid São Paulo municipality records")
    return df.sort_values("ibge_code").reset_index(drop=True)


def load_signatures(path: Path, metadata: pd.DataFrame) -> tuple[dict[str, str], dict]:
    match = PERIOD_NAME.fullmatch(path.name)
    if not match:
        raise ValueError(f"Period filename must be YYYYMMDD_YYYYMMDD.csv: {path.name}")
    first, last = (pd.to_datetime(v, format="%Y%m%d") for v in match.groups())
    dates = pd.date_range(first, last, freq="D")
    df = pd.read_csv(path, dtype={"ibge_code": "string"})
    if not REQUIRED.issubset(df.columns):
        raise ValueError(f"Missing expected columns in {path}")
    df["ibge_code"] = df["ibge_code"].str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="raise")
    codes = set(metadata["ibge_code"])
    if set(df["ibge_code"]) != codes:
        raise ValueError(f"Municipality IBGE code coverage differs from metadata: {path.name}")
    if len(df) != len(codes) * len(dates) or df.duplicated(["ibge_code", "Date"]).any():
        raise ValueError(f"Missing or duplicated municipality-date rows: {path.name}")
    if df["Date"].min() != first or df["Date"].max() != last:
        raise ValueError(f"Unexpected date boundaries in {path.name}")
    if df["Date"].nunique() != len(dates):
        raise ValueError(f"Date coverage incomplete in {path.name}")
    if not df["state"].eq("SP").all():
        raise ValueError(f"Non-SP rows in {path.name}")
    for col in WEATHER:
        df[col] = pd.to_numeric(df[col], errors="raise")
    values = df[list(WEATHER)].to_numpy(dtype="float64")
    if not np.isfinite(values).all() or (values == -999).any() or (values == -999.0).any():
        raise ValueError(f"Missing/nonfinite or -999 weather values: {path.name}")
    metadata_check = df.drop_duplicates("ibge_code").merge(
        metadata[["ibge_code", "municipality", "latitude", "longitude"]],
        on="ibge_code", how="left", validate="one_to_one", suffixes=("", "_meta"),
    )
    if not metadata_check["municipality"].eq(metadata_check["municipality_meta"]).all():
        raise ValueError(f"Municipality names differ from metadata: {path.name}")
    for col in ("latitude", "longitude"):
        if not np.isclose(metadata_check[col], metadata_check[f"{col}_meta"], atol=1e-6, rtol=0).all():
            raise ValueError(f"Coordinates differ from metadata: {path.name}")
    signatures = {}
    for code, chunk in df.groupby("ibge_code", sort=False):
        chunk = chunk.sort_values("Date")
        if not chunk["Date"].reset_index(drop=True).equals(pd.Series(dates)):
            raise ValueError(f"Incomplete/out-of-order city date coverage in {path.name}: {code}")
        series = chunk[list(WEATHER)].to_numpy(dtype="<f8", copy=True)
        signatures[str(code)] = hashlib.sha256(series.tobytes()).hexdigest()
    unique = len(set(signatures.values()))
    return signatures, {
        "filename": path.name,
        "start": first.strftime("%Y-%m-%d"), "end": last.strftime("%Y-%m-%d"),
        "days": len(dates), "municipalities": len(codes),
        "observed_distinct_complete_weather_series": unique,
    }


def groups_from_signatures(signatures: dict[str, str]) -> list[tuple[str, ...]]:
    groups = defaultdict(list)
    for code, sig in signatures.items():
        groups[sig].append(code)
    return sorted((tuple(sorted(group)) for group in groups.values()), key=lambda g: g[0])


def create_mapping(metadata: pd.DataFrame, groups: list[tuple[str, ...]]) -> pd.DataFrame:
    by_code = metadata.set_index("ibge_code")
    rows = []
    for group_num, members in enumerate(groups, start=1):
        rep = members[0]  # Stable, deterministic representative IBGE code.
        for code in members:
            member = by_code.loc[code]
            representative = by_code.loc[rep]
            rows.append({
                "ibge_code": code,
                "municipality": member["municipality"],
                "state": member["state"],
                "latitude": float(member["latitude"]),
                "longitude": float(member["longitude"]),
                "weather_group_id": f"POWER_WG_{group_num:03d}",
                "representative_ibge_code": rep,
                "representative_municipality": representative["municipality"],
                "representative_latitude": float(representative["latitude"]),
                "representative_longitude": float(representative["longitude"]),
                "group_member_count": len(members),
            })
    df = pd.DataFrame(rows).sort_values("ibge_code").reset_index(drop=True)
    if len(df) != len(metadata) or df["ibge_code"].duplicated().any():
        raise ValueError("Mapping did not preserve one row per metadata municipality")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--validation", type=Path, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.reference in args.validation:
        parser.error("Reference file must not be reused as validation")
    meta = read_metadata(args.metadata)
    reference_sigs, reference_report = load_signatures(args.reference, meta)
    base_groups = groups_from_signatures(reference_sigs)
    base_partition = set(base_groups)
    if not args.validation:
        raise ValueError("At least one independent validation period is required")
    validations = []
    for path in args.validation:
        sigs, details = load_signatures(path, meta)
        groups = groups_from_signatures(sigs)
        group_match = set(groups) == base_partition
        # Strongest practical offline check: every member has the exact three-variable
        # daily time series of its group's representative throughout this period.
        within_group_matches = all(
            len({sigs[code] for code in members}) == 1 for members in base_groups
        )
        details.update({
            "same_municipality_partition_as_reference": group_match,
            "each_city_series_identical_to_its_representative": within_group_matches,
        })
        validations.append(details)
        print(
            f"{path.name}: {details['observed_distinct_complete_weather_series']} series; "
            f"same partition={group_match}; representative reconstruction={within_group_matches}",
            flush=True,
        )
        if not (group_match and within_group_matches):
            raise ValueError(f"Mapping validation failed for {path.name}; no outputs written")
    mapping = create_mapping(meta, base_groups)
    if args.output.exists():
        existing = pd.read_csv(args.output, dtype={"ibge_code": "string", "representative_ibge_code": "string"})
        if not existing.equals(mapping):
            raise FileExistsError(f"Existing mapping differs; refusing to overwrite: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(args.output, index=False)
    report = {
        "mapping_type": "empirical_complete_weather_series_group; NOT_official_NASA_POWER_grid",
        "weather_variables": list(WEATHER),
        "reference": reference_report,
        "validation_periods": validations,
        "mapping_municipalities": len(mapping),
        "mapping_groups": len(base_groups),
        "min_group_size": min(map(len, base_groups)),
        "max_group_size": max(map(len, base_groups)),
        "caveat": (
            "Groups are inferred from equality of already-downloaded municipal weather "
            "series, not from provider grid IDs. Validation is limited to supplied periods. "
            "Before changing downloader requests, verify representative-only requests "
            "on an independent period and retain a fallback for boundary/sampling changes."
        ),
    }
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(mapping)} municipalities / {len(base_groups)} empirical groups: {args.output}")
    print(f"Saved validation report: {args.report}")


if __name__ == "__main__":
    main()
