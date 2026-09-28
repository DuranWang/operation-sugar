"""NASA POWER daily weather downloader: 4 workers, empirical group reuse, per-city resume.

Run from project root: python -m src.download_nasa_power
Set data/metadata/sp_nasa_power_weather_group_mapping.csv before running.
Checkpoint files live beside annual CSVs in SP/_checkpoints/YYYYMMDD_YYYYMMDD/.
"""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import numpy as np
import threading
import time

import pandas as pd
import requests

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
DEFAULT_OUTPUT_FOLDER = Path("data/raw/nasa_power/daily_weather")
MAX_WORKERS = 4
MAX_RETRIES = 7  # Total attempts per city request, including the first


class DownloadStopped(Exception):
    """The operator stopped the batch, or shared rate limiting exhausted retries."""


class RequestGate:
    """Allow normal concurrent requests; share cooldown only after HTTP 429."""

    def __init__(self):
        self.lock = threading.Lock()
        self.cooldown_until = 0.0
        self.rate_limit_streak = 0
        self.successes_since_429 = 0
        self.stop = threading.Event()

    def acquire(self) -> None:
        while True:
            if self.stop.is_set():
                raise DownloadStopped("Download stopped; saved checkpoints are retained.")
            with self.lock:
                now = time.monotonic()
                remaining = self.cooldown_until - now
                if remaining <= 0:
                    return
            self.stop.wait(min(remaining, 0.5))

    def rate_limited(self, response: requests.Response) -> None:
        with self.lock:
            self.rate_limit_streak += 1
            self.successes_since_429 = 0
            backoff = min(900.0, 60.0 * (2 ** min(self.rate_limit_streak - 1, 4)))
            header = response.headers.get("Retry-After")
            if header:
                try:
                    header_wait = max(0.0, float(header))
                except ValueError:
                    try:
                        target = parsedate_to_datetime(header)
                        if target.tzinfo is None:
                            target = target.replace(tzinfo=timezone.utc)
                        header_wait = max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
                    except (TypeError, ValueError, OverflowError):
                        header_wait = 0.0
                backoff = max(backoff, header_wait)
            self.cooldown_until = max(self.cooldown_until, time.monotonic() + backoff)
            print(f"HTTP 429: shared cooldown >= {backoff:.0f}s (streak {self.rate_limit_streak}).", flush=True)

    def success(self) -> None:
        # Clear the 429 streak only after sustained successful requests.
        with self.lock:
            self.successes_since_429 += 1
            if self.successes_since_429 >= 20:
                self.rate_limit_streak = 0


def get_power_response(
    params: dict,
    gate: RequestGate,
    max_retries: int = MAX_RETRIES,
) -> requests.Response:
    """Request POWER with shared 429 cooldown and interruptible retries."""
    for attempt in range(1, max_retries + 1):
        gate.acquire()
        try:
            response = requests.get(
                NASA_POWER_URL,
                params=params,
                timeout=(10, 30),
            )
            if response.status_code == 429:
                gate.rate_limited(response)
                if attempt == max_retries:
                    gate.stop.set()
                    raise DownloadStopped("Repeated HTTP 429; stop this run and resume later.")
                continue
            response.raise_for_status()
            gate.success()
            return response
        except requests.exceptions.RequestException as exc:
            if attempt == max_retries:
                raise RuntimeError(f"POWER request failed after {attempt} attempts: {exc}") from exc
            delay = min(120, 5 * (2 ** (attempt - 1)))
            print(f"Request error ({attempt}/{max_retries}): {exc}; retry in {delay}s", flush=True)
            if gate.stop.wait(delay):
                raise DownloadStopped("Stopped during retry wait.") from exc
    raise RuntimeError("Unexpected request loop exit.")


def download_power_data(
    parameters: list[str], latitude: float, longitude: float,
    start: str, end: str, gate: RequestGate,
) -> pd.DataFrame:
    if not parameters:
        raise ValueError("At least one NASA POWER parameter is required.")
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    data = get_power_response(params, gate).json()
    try:
        parameter_data = data["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Unexpected NASA POWER response structure.") from exc
    missing = set(parameters) - set(parameter_data)
    if missing:
        raise ValueError(f"NASA POWER response missing parameters: {sorted(missing)}")
    weather_df = pd.DataFrame({p: pd.Series(parameter_data[p]) for p in parameters})
    weather_df.index.name = "Date"
    weather_df = weather_df.reset_index()
    weather_df["Date"] = pd.to_datetime(weather_df["Date"], format="%Y%m%d", errors="raise")
    return weather_df


def validate_metadata(metadata_df: pd.DataFrame) -> None:
    required = {"municipality", "ibge_code", "state", "latitude", "longitude"}
    missing = required - set(metadata_df.columns)
    if missing:
        raise ValueError(f"Metadata missing columns: {sorted(missing)}")
    if metadata_df[list(required)].isna().any().any():
        raise ValueError("Metadata contains missing municipality information.")
    if metadata_df["ibge_code"].duplicated().any():
        raise ValueError("Metadata contains duplicate IBGE codes.")


def valid_city_frame(
    frame: pd.DataFrame, row, parameters: list[str], expected_dates: pd.DatetimeIndex,
) -> bool:
    required = {"Date", *parameters, "municipality", "ibge_code", "state", "latitude", "longitude"}
    if not required.issubset(frame.columns) or len(frame) != len(expected_dates):
        return False
    try:
        dates = pd.to_datetime(frame["Date"], errors="raise")
        codes = pd.to_numeric(frame["ibge_code"], errors="raise")
        coords_ok = (
            (pd.to_numeric(frame["latitude"], errors="raise") - float(row.latitude)).abs().le(1e-6).all()
            and (pd.to_numeric(frame["longitude"], errors="raise") - float(row.longitude)).abs().le(1e-6).all()
        )
        return bool(
            dates.is_unique
            and dates.sort_values().reset_index(drop=True).equals(pd.Series(expected_dates))
            and codes.eq(int(row.ibge_code)).all()
            and frame["municipality"].eq(row.municipality).all()
            and frame["state"].eq(row.state).all()
            and coords_ok
            and frame[parameters].notna().all().all()
        )
    except (ValueError, TypeError, KeyError):
        return False


def atomic_csv(frame: pd.DataFrame, destination: Path) -> None:
    """Write each checkpoint atomically, so Ctrl+C never leaves half a city CSV."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".tmp")
    try:
        frame.to_csv(temp, index=False)
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)


MAPPING_PATH = Path("data/metadata/sp_nasa_power_weather_group_mapping.csv")


def validate_group_mapping(mapping_path: Path, state_metadata: pd.DataFrame) -> dict:
    """Validate an empirical weather-group map against the CURRENT municipality metadata.

    These are observed weather groups, not NASA-issued grid IDs. Never infer a
    group from rounded coordinates or silently accept changed metadata.
    """
    if not mapping_path.is_file():
        raise FileNotFoundError(f"Missing POWER weather-group mapping: {mapping_path}")
    mapping = pd.read_csv(
        mapping_path,
        dtype={"ibge_code": "string", "representative_ibge_code": "string"},
    )
    required = {
        "ibge_code", "municipality", "state", "latitude", "longitude",
        "weather_group_id", "representative_ibge_code",
        "representative_municipality", "representative_latitude",
        "representative_longitude", "group_member_count",
    }
    if mapping.empty or not required.issubset(mapping.columns):
        raise ValueError(f"Missing mapping columns: {sorted(required - set(mapping.columns))}")
    if mapping[list(required)].isna().any().any():
        raise ValueError("Weather-group mapping contains missing values.")
    if mapping["ibge_code"].duplicated().any():
        raise ValueError("Duplicate municipality IBGE codes in weather-group mapping.")
    by_code = {str(int(row.ibge_code)): row for row in state_metadata.itertuples(index=False)}
    mapping["ibge_code"] = mapping["ibge_code"].str.strip()
    mapping["representative_ibge_code"] = mapping["representative_ibge_code"].str.strip()
    if set(mapping["ibge_code"]) != set(by_code):
        missing = sorted(set(by_code) - set(mapping["ibge_code"]))
        extra = sorted(set(mapping["ibge_code"]) - set(by_code))
        raise ValueError(f"Mapping municipality coverage differs: missing={missing}, extra={extra}")

    for item in mapping.itertuples(index=False):
        row = by_code[str(item.ibge_code)]
        if (item.municipality != row.municipality or item.state != row.state
                or abs(float(item.latitude) - float(row.latitude)) > 1e-6
                or abs(float(item.longitude) - float(row.longitude)) > 1e-6):
            raise ValueError(f"Weather-group mapping no longer matches metadata: {item.ibge_code}")

    groups = {}
    for group_id, group in mapping.groupby("weather_group_id", sort=True):
        representative_codes = set(group["representative_ibge_code"])
        if len(representative_codes) != 1:
            raise ValueError(f"Multiple representative codes in group {group_id}")
        rep_code = representative_codes.pop()
        members = set(group["ibge_code"])
        if rep_code not in members:
            raise ValueError(f"Representative {rep_code} is not a member of {group_id}")
        rep_row = by_code[rep_code]
        for item in group.itertuples(index=False):
            if (item.representative_municipality != rep_row.municipality
                    or abs(float(item.representative_latitude) - float(rep_row.latitude)) > 1e-6
                    or abs(float(item.representative_longitude) - float(rep_row.longitude)) > 1e-6
                    or int(item.group_member_count) != len(group)):
                raise ValueError(f"Invalid representative/size metadata in group {group_id}")
        groups[group_id] = {
            "representative": rep_row,
            "members": [by_code[code] for code in sorted(members)],
        }
    print(f"Verified mapping: {len(mapping)} municipalities / {len(groups)} empirical groups.", flush=True)
    return groups


def weather_only(frame: pd.DataFrame, parameters: list[str],
                 expected_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Validate and normalize a complete weather series before using it for a group."""
    if not {"Date", *parameters}.issubset(frame.columns) or len(frame) != len(expected_dates):
        raise ValueError("Weather series has missing columns or incorrect day count.")
    dates = pd.to_datetime(frame["Date"], errors="raise")
    if (dates.duplicated().any()
            or not dates.sort_values().reset_index(drop=True).equals(pd.Series(expected_dates))):
        raise ValueError("Weather series has incomplete or duplicate dates.")
    result = frame[["Date", *parameters]].copy()
    result["Date"] = dates
    for parameter in parameters:
        result[parameter] = pd.to_numeric(result[parameter], errors="raise")
        if (not result[parameter].notna().all()
                or not np.isfinite(result[parameter].to_numpy(dtype="float64")).all()
                or result[parameter].eq(-999).any()):
            raise ValueError(f"Missing or invalid NASA POWER values for {parameter}.")
    return result.sort_values("Date").reset_index(drop=True)


def weather_equal(left: pd.DataFrame, right: pd.DataFrame,
                  parameters: list[str]) -> bool:
    """Compare parsed numeric data for already-downloaded group members."""
    return (left["Date"].equals(right["Date"])
            and np.array_equal(left[parameters].to_numpy(dtype="float64"),
                               right[parameters].to_numpy(dtype="float64")))


def expand_weather(weather: pd.DataFrame, row) -> pd.DataFrame:
    """Retain the recipient municipality's metadata; only weather is shared."""
    result = weather.copy()
    result["municipality"] = row.municipality
    result["ibge_code"] = int(row.ibge_code)
    result["state"] = row.state
    result["latitude"] = row.latitude
    result["longitude"] = row.longitude
    return result


def download_weather_for_state_period(
    metadata_df: pd.DataFrame,
    parameters: list[str],
    start: str,
    end: str,
    state: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    max_workers: int = MAX_WORKERS,
    gate: RequestGate | None = None,
    mapping_path: Path = MAPPING_PATH,
) -> pd.DataFrame:
    """Download only missing REPRESENTATIVE points, then expand to all cities.

    Reuse existing complete annual CSVs and legacy per-city checkpoints. Check
    all observed member series for disagreement before any group reconstruction.
    """
    first, last = pd.to_datetime(start, format="%Y%m%d"), pd.to_datetime(end, format="%Y%m%d")
    if first > last or first.year != last.year:
        raise ValueError("Download period must stay within one calendar year.")
    if not 1 <= max_workers <= 4:
        raise ValueError("max_workers must be between 1 and 4.")
    if not parameters or len(parameters) != len(set(parameters)):
        raise ValueError("Parameters must be nonempty and unique.")
    validate_metadata(metadata_df)
    state_metadata = metadata_df.loc[metadata_df["state"] == state].copy()
    if state_metadata.empty:
        raise ValueError(f"No municipality metadata for {state}.")
    groups = validate_group_mapping(Path(mapping_path), state_metadata)
    rows = {int(row.ibge_code): row for row in state_metadata.itertuples(index=False)}
    dates = pd.date_range(first, last, freq="D")
    output_dir = Path(output_folder) / state
    output_file = output_dir / f"{start}_{end}.csv"
    checkpoint_dir = output_dir / "_checkpoints" / f"{start}_{end}"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    gate = gate or RequestGate()

    existing_complete = False
    # Existing municipal records may come from an older non-grouped downloader.
    # Preserve them and cross-check observed members within every weather group.
    saved_cities: dict[int, pd.DataFrame] = {}
    if output_file.exists():
        try:
            annual = pd.read_csv(output_file, dtype={"ibge_code": "string"})
            if "ibge_code" in annual.columns:
                for code, frame in annual.groupby("ibge_code", sort=False):
                    if str(code).isdigit() and int(code) in rows:
                        city = rows[int(code)]
                        if valid_city_frame(frame, city, parameters, dates):
                            saved_cities[int(code)] = frame.copy()
                existing_complete = (
                    len(saved_cities) == len(rows)
                    and len(annual) == len(rows) * len(dates)
                )
        except (ValueError, OSError, pd.errors.ParserError) as exc:
            print(f"Unable to reuse existing annual CSV: {exc}", flush=True)

    # Legacy city checkpoints are included even when the representative itself
    # has no checkpoint; any saved member can avoid a duplicate group request.
    for code, row in rows.items():
        city_file = checkpoint_dir / f"{code}.csv"
        if not city_file.is_file():
            continue
        try:
            frame = pd.read_csv(city_file, dtype={"ibge_code": "string"})
            if not valid_city_frame(frame, row, parameters, dates):
                print(f"Ignoring invalid city checkpoint: {code}", flush=True)
                continue
            if code in saved_cities:
                old_weather = weather_only(saved_cities[code], parameters, dates)
                new_weather = weather_only(frame, parameters, dates)
                if not weather_equal(old_weather, new_weather, parameters):
                    raise ValueError(f"Annual CSV and checkpoint disagree for municipality {code}")
            else:
                saved_cities[code] = frame
        except (OSError, pd.errors.ParserError) as exc:
            print(f"Ignoring unreadable city checkpoint {code}: {exc}", flush=True)

    group_weather: dict[str, pd.DataFrame] = {}
    for group_id, group in groups.items():
        source_code = None
        for row in group["members"]:
            code = int(row.ibge_code)
            if code not in saved_cities:
                continue
            series = weather_only(saved_cities[code], parameters, dates)
            if group_id not in group_weather:
                group_weather[group_id] = series
                source_code = code
            elif not weather_equal(group_weather[group_id], series, parameters):
                raise ValueError(
                    f"Observed weather conflicts inside {group_id}: "
                    f"municipality {source_code} differs from {code}. "
                    "This empirical mapping may not apply to this year; "
                    "the existing files were not overwritten."
                )

    # If an entire annual file is already valid, verified against the mapping
    # and its legacy checkpoints, preserve its exact bytes and avoid rewriting.
    if existing_complete:
        print(f"Skipping complete annual CSV: {output_file}", flush=True)
        return annual

    missing_groups = [group_id for group_id in groups if group_id not in group_weather]
    print(
        f"\n{state} {start}–{end}: {len(saved_cities)}/{len(rows)} city records saved; "
        f"{len(group_weather)}/{len(groups)} groups already covered; "
        f"{len(missing_groups)} representative requests remaining; {max_workers} workers.",
        flush=True,
    )

    def work(group_id: str):
        representative = groups[group_id]["representative"]
        weather = weather_only(
            download_power_data(parameters, representative.latitude, representative.longitude,
                                start, end, gate),
            parameters, dates,
        )
        rep_frame = expand_weather(weather, representative)
        # Immediately preserve the downloaded representative in the EXISTING
        # per-city checkpoint format; no group-wide work must complete first.
        atomic_csv(rep_frame, checkpoint_dir / f"{int(representative.ibge_code)}.csv")
        return group_id, weather

    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = {}
    pending_iter = iter(missing_groups)

    def submit_next():
        if gate.stop.is_set():
            return
        try:
            group_id = next(pending_iter)
        except StopIteration:
            return
        futures[executor.submit(work, group_id)] = group_id

    try:
        for _ in range(min(max_workers, len(missing_groups))):
            submit_next()
        while futures:
            completed, _ = wait(tuple(futures), timeout=0.5, return_when=FIRST_COMPLETED)
            if gate.stop.is_set():
                raise DownloadStopped("Shared rate-limit stop requested.")
            for future in completed:
                group_id = futures.pop(future)
                try:
                    received_id, weather = future.result()
                    group_weather[received_id] = weather
                    print(f"[{len(group_weather)}/{len(groups)}] OK: {received_id} (saved)", flush=True)
                except DownloadStopped:
                    raise
                except Exception as exc:
                    print(f"FAILED group {group_id}: {exc}", flush=True)
                    gate.stop.set()
                    raise DownloadStopped("A group failed; saved checkpoints retained.") from exc
                submit_next()
    except KeyboardInterrupt:
        gate.stop.set()
        print("\nCtrl+C received: stopping new requests; saved checkpoints retained.", flush=True)
        raise
    finally:
        if len(group_weather) != len(groups):
            gate.stop.set()
        executor.shutdown(wait=True, cancel_futures=True)

    if len(group_weather) != len(groups):
        raise RuntimeError(f"Incomplete period: {len(group_weather)}/{len(groups)} groups.")

    # Build the ORIGINAL city-level annual CSV. Never write new city metadata
    # using the representative city's name, IBGE code, or coordinates.
    assembled = []
    city_to_group = {int(member.ibge_code): group_id
                     for group_id, group in groups.items()
                     for member in group["members"]}
    for row in sorted(rows.values(), key=lambda item: int(item.ibge_code)):
        weather = group_weather[city_to_group[int(row.ibge_code)]]
        # An existing municipal series was checked against its group's weather
        # above; all expanded rows use the recipient's ORIGINAL metadata.
        assembled.append(expand_weather(weather, row))
    final_df = pd.concat(assembled, ignore_index=True)
    final_df = final_df[["Date", *parameters, "municipality", "ibge_code", "state", "latitude", "longitude"]]
    final_df = final_df.sort_values(["ibge_code", "Date"]).reset_index(drop=True)
    if len(final_df) != len(rows) * len(dates):
        raise ValueError("Unexpected final municipality-date coverage; annual CSV not overwritten.")
    atomic_csv(final_df, output_file)
    print(f"Saved complete annual CSV: {output_file}", flush=True)
    return final_df


def download_weather_for_state_periods(
    metadata_df: pd.DataFrame,
    parameters: list[str],
    periods: list[tuple[str, str]],
    state: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    mapping_path: Path = MAPPING_PATH,
) -> None:
    """Resume each year using the same 4-worker shared 429 cooldown gate."""
    if not periods:
        raise ValueError("At least one download period is required.")
    gate = RequestGate()
    for start, end in periods:
        download_weather_for_state_period(
            metadata_df=metadata_df,
            parameters=parameters,
            start=start,
            end=end,
            state=state,
            output_folder=output_folder,
            max_workers=MAX_WORKERS,
            gate=gate,
            mapping_path=mapping_path,
        )


def main() -> None:
    start_time = time.time()
    metadata_df = pd.read_csv("data/metadata/sp_municipalities.csv")
    periods = [(f"{year}0101", f"{year}1231") for year in range(2009, 2010)]
    try:
        download_weather_for_state_periods(
            metadata_df=metadata_df,
            parameters=["PRECTOTCORR", "T2M", "RH2M"],
            periods=periods,
            state="SP",
        )
    except (KeyboardInterrupt, DownloadStopped) as exc:
        print(f"\nStopped. Saved checkpoints will be reused. {exc}", flush=True)
        return
    print(f"\nAll requested periods finished in {time.time() - start_time:.1f}s.", flush=True)


if __name__ == "__main__":
    main()
