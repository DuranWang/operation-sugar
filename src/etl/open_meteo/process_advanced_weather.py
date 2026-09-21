"""Validate cached advanced weather; build grid and municipality day/month tables."""
import argparse
import calendar
import csv
from datetime import date, timedelta
import gzip
import json
import math
from pathlib import Path
from src.etl.open_meteo.download_advanced_weather import (
    ROOT, HOURLY, LAYERS, MODEL, TIMEZONE, make_grid, request_params, write_csv, write_json,
)

def dates_between(start, end):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def validate_and_aggregate(data, grid_id, lat, lon, start, end):
    if data.get("error"):
        raise ValueError(data.get("reason", "Provider error"))
    if abs(data["latitude"] - lat) > 0.001 or abs(data["longitude"] - lon) > 0.001:
        raise ValueError("Returned grid does not match requested ERA5 cell")
    if data["utc_offset_seconds"] != -10800:
        raise ValueError("Unexpected timezone offset")
    days = dates_between(start, end)
    expected = [f"{day}T{hour:02d}:00" for day in days for hour in range(24)]
    hourly, daily = data["hourly"], data["daily"]
    if hourly["time"] != expected or daily["time"] != [str(day) for day in days]:
        raise ValueError("Missing, duplicate, unordered or unexpected timestamps")
    for name in HOURLY:
        unit = "kPa" if name == HOURLY[0] else "m³/m³"
        if data["hourly_units"][name] != unit:
            raise ValueError("Unexpected unit: " + name)
        values = hourly[name]
        if len(values) != len(expected):
            raise ValueError("Wrong array length: " + name)
        for value in values:
            if value is None or not math.isfinite(value) or value < 0:
                raise ValueError("Missing/nonfinite/negative value: " + name)
            if name != HOURLY[0] and value > 1:
                raise ValueError("Soil water outside [0, 1]")
    radiation = daily["shortwave_radiation_sum"]
    if data["daily_units"]["shortwave_radiation_sum"] != "MJ/m²" or len(radiation) != len(days):
        raise ValueError("Unexpected radiation units or length")
    if any(v is None or not math.isfinite(v) or v < 0 for v in radiation):
        raise ValueError("Missing/nonfinite/negative daily radiation")
    result = []
    for i, day in enumerate(days):
        row = {"grid_id": grid_id, "Date": str(day)}
        values = hourly[HOURLY[0]][24*i:24*(i+1)]
        row["vpd_mean_kpa"] = sum(values) / 24
        row["vpd_max_kpa"] = max(values)
        for layer in LAYERS:
            values = hourly["soil_moisture_" + layer][24*i:24*(i+1)]
            row["soil_moisture_" + layer + "_m3_m3"] = sum(values) / 24
        row["solar_radiation_mj_m2_day"] = radiation[i]
        result.append(row)
    return result


def monthly_rows(daily):
    groups = {}
    for row in daily:
        groups.setdefault(row["Date"][:7], []).append(row)
    result = []
    for month, group in sorted(groups.items()):
        year, number = map(int, month.split("-"))
        row = {"grid_id": group[0]["grid_id"], "month": month, "observed_days": len(group),
               "expected_days": calendar.monthrange(year, number)[1]}
        row["complete_month"] = row["observed_days"] == row["expected_days"]
        for key in group[0]:
            if key in ("Date", "grid_id"):
                continue
            values = [r[key] for r in group]
            if key == "solar_radiation_mj_m2_day":
                row["solar_radiation_total_mj_m2"] = sum(values)
                row["solar_radiation_mean_daily_mj_m2"] = sum(values) / len(values)
            elif key == "vpd_max_kpa":
                row["vpd_mean_daily_max_kpa"] = sum(values) / len(values)
            else:
                row[key] = sum(values) / len(values)
        result.append(row)
    return result


def municipality_rows(rows, municipalities):
    """Expand shared grid data by identifier, without inventing spatial detail."""
    return [{**municipality, **row} for municipality in municipalities for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/raw/open_meteo/era5/SP/2010-01-01_2010-12-31')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    with (args.input / 'municipality_grid_mapping.csv').open(newline='', encoding='utf-8') as stream:
        mapping = list(csv.DictReader(stream))
    states = {r['state'].strip().upper() for r in mapping}
    if len(states) != 1:
        raise ValueError('An ETL batch must contain one state')
    state = next(iter(states))
    processed_root = ROOT / 'data/processed/advanced_weather/era5'
    sampling = args.input.parent.parent.name
    if sampling == 'sampling_0p5':
        processed_root = processed_root / sampling
    out = args.output or processed_root / state / args.input.name
    codes = [r['ibge_code'] for r in mapping]
    if not codes or len(codes) != len(set(codes)):
        raise ValueError('Empty mapping or duplicate municipality codes')
    groups = {}
    for row in mapping:
        groups.setdefault(row['grid_id'], []).append(row)
    done, errors = [], []
    for grid_id, municipalities in sorted(groups.items()):
        path = args.input / 'raw' / (grid_id + '.json.gz')
        if not path.exists():
            continue
        try:
            envelope = json.loads(gzip.decompress(path.read_bytes()))
            request = envelope['request']
            start, end = date.fromisoformat(request['start_date']), date.fromisoformat(request['end_date'])
            lat, lon = float(municipalities[0]['grid_latitude']), float(municipalities[0]['grid_longitude'])
            if start > end or request != request_params(lat, lon, start, end):
                raise ValueError('Cached request does not match fixed source specification')
            if args.input.name != f'{start}_{end}':
                raise ValueError('Cached date range differs from archive directory')
            for municipality in municipalities:
                if (float(municipality['grid_latitude']), float(municipality['grid_longitude'])) != (lat, lon):
                    raise ValueError('Inconsistent grid mapping')
            daily = validate_and_aggregate(envelope['response'], grid_id, lat, lon, start, end)
            monthly = monthly_rows(daily)
            for frequency, rows in (('daily', daily), ('monthly', monthly)):
                write_csv(out / 'grid' / frequency / (grid_id + '.csv'), rows)
                write_csv(out / 'municipality' / frequency / (grid_id + '.csv'), municipality_rows(rows, municipalities))
            done.append(grid_id)
        except (ValueError, KeyError, TypeError, OSError) as error:
            errors.append({'grid_id': grid_id, 'error': str(error)})
    write_csv(out / 'municipality_grid_mapping.csv', mapping)
    summary = dict(status='complete' if len(done) == len(groups) else 'partial',
                   state=state, model=MODEL, timezone=TIMEZONE,
                   sampling_step_degrees=0.5 if sampling == 'sampling_0p5' else 0.25,
                   municipality_coverage_scope='only_municipalities_in_input_mapping', source_directory=str(args.input.resolve()),
                   expected_grid_cells=len(groups), completed_grid_cells=len(done),
                   completed_grid_ids=done, expected_municipalities=len(mapping),
                   covered_municipalities=sum(len(groups[key]) for key in done),
                   missing_grid_cells=sorted(set(groups)-set(done)), errors=errors,
                   historical_publication_vintages_verified=False)
    write_json(out / 'processing_coverage.json', summary)
    print(f"ETL: {len(done)}/{len(groups)} grids; status={summary['status']}")
    return 0 if summary['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())

