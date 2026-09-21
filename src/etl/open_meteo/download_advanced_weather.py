"""Download provider-supplied ERA5 VPD, soil water and solar radiation.

Research archive, not a reconstruction of historical publication vintages.
Run from the repository root: python -m src.etl.open_meteo.download_advanced_weather --help
"""

import argparse
import csv
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
LAYERS = ("0_to_7cm", "7_to_28cm", "28_to_100cm", "100_to_255cm")
HOURLY = ("vapour_pressure_deficit",) + tuple("soil_moisture_" + x for x in LAYERS)
MODEL = "era5"
TIMEZONE = "Etc/GMT+3"  # Fixed UTC-03; deliberately avoids DST-dependent days.

# Editable defaults; command-line arguments override these.
DEFAULT_STATE = "SP"
DEFAULT_YEAR = 2010
DEFAULT_SAMPLING_STEP = 0.5  # Point spacing; native ERA5 cells remain 0.25 degrees.
DEFAULT_METADATA = ROOT / "data/metadata/sp_municipalities.csv"
DEFAULT_OUTPUT_FOLDER = ROOT / "data/raw/open_meteo/era5"


def retry_after_seconds(value):
    """Parse Retry-After seconds or an HTTP date; ignore malformed headers."""
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            seconds = stamp.timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0, seconds) if math.isfinite(seconds) else None


def wait_for_server(cooldown_path, wait=True):
    """Honor persisted server cooldown even after restarting the downloader."""
    if not cooldown_path.exists():
        return
    state = json.loads(cooldown_path.read_text())
    while True:
        remaining = state['retry_at'] - time.time()
        if remaining <= 0:
            return
        if not wait:
            raise RuntimeError(f'Server cooldown active for {remaining:.0f}s; resume later')
        print(f'Server cooldown: {remaining:.0f}s remaining; cache retained.', flush=True)
        time.sleep(min(60, remaining))


def fetch_with_backoff(params, output_folder, ledger, ledger_path, cost, wait=True):
    """Sequential requests; three spaced 429 retries, then longer cooldowns.

    Server Retry-After always takes precedence if longer. Explicit hour/day
    limits skip short retries. Stop after three long cooldowns still fail.
    Other HTTP errors are handled by the caller, never retried as rate limits.
    """
    cooldown_path = output_folder / 'server_cooldown.json'
    short_retries, long_waits = 0, 0
    while True:
        wait_for_server(cooldown_path, wait)
        # Diagnostic estimate only: do not gate requests using guessed budgets.
        ledger.append({'at': time.time(), 'cost': cost})
        write_json(ledger_path, ledger)
        try:
            with urlopen(ENDPOINT + '?' + urlencode(params), timeout=90) as response:
                return response.read()
        except HTTPError as error:
            if error.code != 429:
                raise
            header_delay = retry_after_seconds(error.headers.get('Retry-After') if error.headers else None)
            try:
                raw_reason = error.read(8192).decode('utf-8', errors='replace')
                try:
                    payload = json.loads(raw_reason)
                    reason = str(payload.get('reason', raw_reason)) if isinstance(payload, dict) else raw_reason
                except ValueError:
                    reason = raw_reason
            finally:
                error.close()
            reason = ' '.join(reason.split())[:1000] or 'Too Many Requests'
            lower = reason.lower()
            explicit_delay = 86400 if 'day' in lower or 'daily' in lower else 3600 if 'hour' in lower else 0
            if explicit_delay or short_retries >= 3 or long_waits:
                delay = max(explicit_delay, 3600 * 2**min(long_waits, 2))
                long_waits += 1
                label = f'Long cooldown {long_waits}'
            else:
                delay = (60, 120, 240)[short_retries]
                short_retries += 1
                label = f'Retry {short_retries}/3'
            # With a valid server reset time, no need to guess a whole hour/day.
            if header_delay is not None:
                delay = max(1, header_delay) if explicit_delay else max(delay, header_delay)
            write_json(cooldown_path, dict(retry_at=time.time()+delay, reason=reason,
                                          status=429, wait_seconds=delay))
            print(f'HTTP 429: {reason}\n{label}: wait {delay:.0f}s.', flush=True)
            if not wait or long_waits > 3:
                raise RuntimeError(f'Rate limited (HTTP 429): {reason}. Cooldown and downloads saved; resume later.')


def describe_http_error(error):
    """Return a compact diagnostic for non-429 HTTP failures.

    Includes status, reason, Retry-After (when present), and up to 1000
    characters of the provider response body. The body is consumed here.
    """
    retry_after = error.headers.get('Retry-After') if error.headers else None
    try:
        raw_body = error.read(8192).decode('utf-8', errors='replace')
    except Exception as body_error:
        raw_body = f'<could not read response body: {type(body_error).__name__}: {body_error}>'
    finally:
        try:
            error.close()
        except Exception:
            pass
    body = ' '.join(raw_body.split())[:1000]
    parts = [f'HTTP {error.code}', f'reason={error.reason}']
    if retry_after:
        parts.append(f'Retry-After={retry_after}')
    if body:
        parts.append(f'body={body}')
    return '; '.join(parts)


def describe_exception(error):
    """Return an exception string that preserves the exception class."""
    if isinstance(error, URLError):
        return f'URLError: {error.reason!r}'
    return f'{type(error).__name__}: {error}'


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def write_json(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def write_csv(path, rows):
    if not rows:
        raise ValueError("Refusing to write an empty output")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def make_grid(metadata, state="SP"):
    """Map municipality points to nearest regular 0.25-degree ERA5 grid cells."""
    with metadata.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    state = state.strip().upper()
    seen, mapping, grids = set(), [], {}
    for row in rows:
        if row["state"].strip().upper() != state:
            continue
        code = row["ibge_code"]
        if code in seen:
            raise ValueError("Duplicate municipality: " + code)
        seen.add(code)
        lat, lon = float(row["latitude"]), float(row["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid coordinates")
        lat, lon = round(lat * 4) / 4, round(lon * 4) / 4
        grid_id = f"era5_{lat:.2f}_{lon:.2f}"
        grids[grid_id] = (lat, lon)
        mapping.append({**row, "grid_id": grid_id, "grid_latitude": lat, "grid_longitude": lon})
    if not mapping:
        raise ValueError(f"No municipalities for {state} in {metadata}")
    return mapping, dict(sorted(grids.items()))


def request_params(lat, lon, start, end):
    return dict(latitude=lat, longitude=lon, start_date=str(start), end_date=str(end),
                hourly=",".join(HOURLY), daily="shortwave_radiation_sum", models=MODEL,
                timezone=TIMEZONE, cell_selection="nearest", elevation="nan")


def parse_date(value):
    """Accept either ISO dates or the previous NASA downloader's YYYYMMDD."""
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y%m%d" if len(str(value)) == 8 else "%Y-%m-%d").date()


def read_cache(path, params):
    envelope = json.loads(gzip.decompress(path.read_bytes()))
    if envelope['request'] != params:
        raise ValueError('Cached request does not match parameters')
    response = envelope['response']
    if response.get('error'):
        raise ValueError(response.get('reason', 'Provider error'))
    if not all(key in response for key in ('hourly', 'daily', 'hourly_units', 'daily_units')):
        raise ValueError('Incomplete response envelope; inspect the cached file')
    return envelope


def sample_existing_grids(mapping, grids, step):
    """Fixed global lattice anchored at (0, 0); retain native cells only."""
    if step not in (0.25, 0.5):
        raise ValueError('Sampling step must be 0.25 or 0.5 degrees')
    selected = {key: coord for key, coord in grids.items()
                if all(abs(value / step - round(value / step)) < 1e-8 for value in coord)}
    if not selected:
        raise ValueError('No existing grids intersect the requested fixed lattice')
    return [r for r in mapping if r['grid_id'] in selected], selected


def download_weather_for_state_period(
    metadata_path, start, end, state=DEFAULT_STATE,
    output_folder=DEFAULT_OUTPUT_FOLDER, max_new_requests=None,
    offline=False, wait_for_quota=True, sampling_step=DEFAULT_SAMPLING_STEP,
):
    """Download fixed-lattice native cells for one state/year period.

    No aggregation is performed. A returned partial status must not be treated
    as complete coverage. Use the ETL stage for scientific data validation.
    """
    start, end = parse_date(start), parse_date(end)
    if start > end or start.year != end.year:
        raise ValueError('Each batch must be ordered and contained within one calendar year')
    if max_new_requests is not None and max_new_requests < 0:
        raise ValueError('max_new_requests must be nonnegative')
    state = state.strip().upper()
    if len(state) != 2 or not state.isascii() or not state.isalpha():
        raise ValueError('State must be a two-letter abbreviation, such as SP')
    metadata_path, output_folder = Path(metadata_path), Path(output_folder)
    mapping, grids = make_grid(metadata_path, state)
    full_mapping, full_grids = mapping, grids
    mapping, grids = sample_existing_grids(mapping, grids, sampling_step)
    period = f'{start}_{end}'
    archive_root = output_folder if sampling_step == 0.25 else output_folder / 'sampling_0p5'
    out = archive_root / state / period
    write_csv(out / 'municipality_grid_mapping.csv', mapping)
    ledger_path = output_folder / 'request_budget.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    cost = max(1, ((end-start).days+1)/14)
    done, errors, new_requests = [], [], 0
    stopped_reason = ''
    print(f'{state} {period}: {len(mapping)} municipalities, {len(grids)} grids; '
          f'estimated calls {len(grids)*cost:.0f}', flush=True)
    for position, (grid_id, (lat, lon)) in enumerate(grids.items(), 1):
        params = request_params(lat, lon, start, end)
        raw_path = out / 'raw' / (grid_id + '.json.gz')
        # Reuse compatible pre-state-directory caches without new requests.
        legacy_path = output_folder / period / 'raw' / raw_path.name
        full_path = output_folder / state / period / 'raw' / raw_path.name
        cached = next((p for p in (raw_path, full_path, legacy_path) if p.exists()), None)
        if cached is not None:
            try:
                read_cache(cached, params)
                if cached != raw_path:
                    atomic_bytes(raw_path, cached.read_bytes())
                done.append(grid_id)
            except (ValueError, KeyError, TypeError, OSError) as error:
                errors.append({'grid_id': grid_id, 'error': str(error)})
            continue
        if offline or stopped_reason:
            continue
        if max_new_requests is not None and new_requests >= max_new_requests:
            stopped_reason = 'Explicit request cap reached'
            continue
        new_requests += 1
        print(f'[{position}/{len(grids)}] {state} {grid_id}', flush=True)
        try:
            body = fetch_with_backoff(params, output_folder, ledger, ledger_path, cost, wait_for_quota)
            payload = json.loads(body)
            if payload.get('error'):
                raise ValueError(payload.get('reason', 'Provider error'))
            envelope = dict(request=params, endpoint=ENDPOINT,
                            retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                            response_sha256=hashlib.sha256(body).hexdigest(), response=payload)
            atomic_bytes(raw_path, gzip.compress(json.dumps(envelope).encode()))
            read_cache(raw_path, params)
            done.append(grid_id)
        except HTTPError as error:
            detail = describe_http_error(error)
            errors.append({
                'grid_id': grid_id, 'position': position,
                'latitude': lat, 'longitude': lon,
                'exception_type': type(error).__name__,
                'status_code': error.code, 'error': detail,
            })
            print(f'ERROR [{position}/{len(grids)}] {grid_id}: {detail}', flush=True)
            stopped_reason = 'Provider HTTP error; inspect diagnostic above before resuming'
        except Exception as error:
            detail = describe_exception(error)
            errors.append({
                'grid_id': grid_id, 'position': position,
                'latitude': lat, 'longitude': lon,
                'exception_type': type(error).__name__,
                'error': detail,
            })
            print(f'ERROR [{position}/{len(grids)}] {grid_id}: {detail}', flush=True)
            stopped_reason = 'Download error; resume from saved cache after inspection'
    done_set = set(done)
    missing = sorted(set(grids)-done_set)
    summary = dict(status='complete' if not missing else 'partial', state=state,
                   model=MODEL, timezone=TIMEZONE, start=str(start), end=str(end),
                   native_grid_step_degrees=0.25, sampling_step_degrees=sampling_step,
                   sampling_origin=[0.0, 0.0], aggregation='none_point_subsample',
                   full_mapping_grid_cells=len(full_grids), full_mapping_municipalities=len(full_mapping),
                   municipality_coverage_scope='municipalities_whose_native_cells_are_selected',
                   expected_grid_cells=len(grids), downloaded_grid_cells=len(done),
                   expected_municipalities=len(mapping),
                   covered_municipalities=sum(r['grid_id'] in done_set for r in mapping),
                   missing_grid_cells=missing, errors=errors, new_requests=new_requests,
                   stopped_reason=stopped_reason or ('Offline cache inventory' if offline and missing else ''),
                   processing_validated=False, historical_publication_vintages_verified=False)
    write_json(out / 'download_coverage.json', summary)
    print(f"{summary['status']}: {len(done)}/{len(grids)} grids; new requests={new_requests}", flush=True)
    if stopped_reason:
        print(stopped_reason, flush=True)
    if errors:
        last = errors[-1]
        print(f"Last recorded error: {last.get('grid_id')}: {last.get('error')}", flush=True)
    print(f'Output: {out}', flush=True)
    return summary


def download_weather_for_state_periods(metadata_path, periods, state=DEFAULT_STATE, **kwargs):
    """Run annual batches in caller-specified order; stop at first partial batch."""
    if not periods:
        raise ValueError('At least one period is required')
    # Reject bad schedules before making any network requests.
    normalized = [(parse_date(start), parse_date(end)) for start, end in periods]
    for start, end in normalized:
        if start > end or start.year != end.year:
            raise ValueError('Every period must fit within one calendar year')
    results = []
    for start, end in normalized:
        result = download_weather_for_state_period(metadata_path, start, end, state, **kwargs)
        results.append(result)
        if result['status'] != 'complete':
            break
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', default=DEFAULT_STATE)
    parser.add_argument('--year', type=int, default=None)
    parser.add_argument('--start', type=parse_date)
    parser.add_argument('--end', type=parse_date)
    parser.add_argument('--metadata', type=Path, default=DEFAULT_METADATA)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT_FOLDER)
    parser.add_argument('--max-new-requests', type=int, default=None,
                        help='Optional test cap; default attempts every target grid')
    parser.add_argument('--sampling-step', type=float, choices=[0.25, 0.5],
                        default=DEFAULT_SAMPLING_STEP, help='Sampling spacing, not native ERA5 resolution')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--no-wait', action='store_true', help='Save cooldown and stop on 429 rather than waiting')
    args = parser.parse_args()
    if args.year is not None and (args.start or args.end):
        parser.error('Choose --year OR --start/--end')
    if bool(args.start) != bool(args.end):
        parser.error('--start and --end must be supplied together')
    try:
        year = args.year if args.year is not None else DEFAULT_YEAR
        start, end = (args.start, args.end) if args.start else (date(year, 1, 1), date(year, 12, 31))
        result = download_weather_for_state_period(
            args.metadata, start, end, state=args.state, output_folder=args.output,
            max_new_requests=args.max_new_requests, offline=args.offline, wait_for_quota=not args.no_wait, sampling_step=args.sampling_step)
    except ValueError as error:
        parser.error(str(error))
    return 0 if result['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())

