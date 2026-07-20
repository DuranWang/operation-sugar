from pathlib import Path
import time

import pandas as pd
import requests


NASA_POWER_URL = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
)

DEFAULT_OUTPUT_FOLDER = Path(
    "data/raw/nasa_power/daily_weather"
)


def get_power_response(
    params: dict,
    max_retries: int = 5,
    timeout: int = 60,
) -> requests.Response:
    """Send a NASA POWER request with exponential-backoff retries."""

    for attempt in range(max_retries):
        try:
            response = requests.get(
                NASA_POWER_URL,
                params=params,
                timeout=timeout,
            )

            if response.status_code == 429:
                wait_seconds = 10 * (2**attempt)

                print(
                    f"Rate limited. Waiting {wait_seconds} seconds "
                    f"before retry {attempt + 1}/{max_retries}..."
                )

                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as error:
            if attempt == max_retries - 1:
                break

            wait_seconds = 10 * (2**attempt)

            print(
                f"Request failed: {error}. "
                f"Waiting {wait_seconds} seconds before retry "
                f"{attempt + 1}/{max_retries}..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError(
        f"NASA POWER request failed after {max_retries} attempts."
    )


def download_power_data(
    parameters: list[str],
    latitude: float,
    longitude: float,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Download daily NASA POWER variables for one geographic point."""

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

    response = get_power_response(params)
    data = response.json()

    try:
        parameter_data = data["properties"]["parameter"]
    except KeyError as error:
        raise ValueError(
            "Unexpected NASA POWER response structure."
        ) from error

    missing_parameters = (
        set(parameters) - set(parameter_data.keys())
    )

    if missing_parameters:
        raise ValueError(
            "NASA POWER response is missing parameters: "
            f"{sorted(missing_parameters)}"
        )

    weather_df = pd.DataFrame(
        {
            parameter: pd.Series(parameter_data[parameter])
            for parameter in parameters
        }
    )

    weather_df.index.name = "Date"
    weather_df = weather_df.reset_index()

    weather_df["Date"] = pd.to_datetime(
        weather_df["Date"],
        format="%Y%m%d",
        errors="raise",
    )

    return weather_df


def validate_metadata(metadata_df: pd.DataFrame) -> None:
    """Validate municipality metadata required for weather downloads."""

    required_columns = {
        "municipality",
        "ibge_code",
        "state",
        "latitude",
        "longitude",
    }

    missing_columns = required_columns - set(metadata_df.columns)

    if missing_columns:
        raise ValueError(
            "Metadata is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if metadata_df[list(required_columns)].isna().any().any():
        raise ValueError(
            "Metadata contains missing municipality information."
        )

    if metadata_df["ibge_code"].duplicated().any():
        raise ValueError("Metadata contains duplicate IBGE codes.")


def download_weather_for_state_year(
    metadata_df: pd.DataFrame,
    parameters: list[str],
    start: str,
    end: str,
    state: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
) -> pd.DataFrame:
    """Download and save daily weather for one state and year."""

    start_year = start[:4]
    end_year = end[:4]

    if start_year != end_year:
        raise ValueError(
            "download_weather_for_state_year requires start and end "
            "dates from the same calendar year."
        )
    
    year = start_year

    validate_metadata(metadata_df)

    state_metadata = metadata_df.loc[
        metadata_df["state"] == state
    ].copy()

    if state_metadata.empty:
        raise ValueError(
            f"No municipality metadata found for state {state}."
        )

    output_path = Path(output_folder) / state
    output_path.mkdir(parents=True, exist_ok=True)

    all_weather = []
    failed_downloads = []
    total = len(state_metadata)

    for position, row in enumerate(
        state_metadata.itertuples(index=False),
        start=1,
    ):
        print(
            f"[{position}/{total}] Downloading weather for "
            f"{row.municipality}..."
        )

        try:
            weather_df = download_power_data(
                parameters=parameters,
                latitude=row.latitude,
                longitude=row.longitude,
                start=start,
                end=end,
            )

            weather_df["municipality"] = row.municipality
            weather_df["ibge_code"] = int(row.ibge_code)
            weather_df["state"] = row.state
            weather_df["latitude"] = row.latitude
            weather_df["longitude"] = row.longitude

            all_weather.append(weather_df)

        # Continue the state-level batch even if one municipality fails.
        except Exception as error:
            print(f"Failed for {row.municipality}: {error}")

            failed_downloads.append(
                {
                    "municipality": row.municipality,
                    "ibge_code": row.ibge_code,
                    "error": str(error),
                }
            )
    
    if not all_weather:
        raise RuntimeError(
            f"All municipality downloads failed for {state} {year}."
        )

    final_df = pd.concat(
        all_weather,
        ignore_index=True,
    )

    output_file = output_path / f"{year}.csv"
    final_df.to_csv(output_file, index=False)

    print(f"Weather data saved to {output_file}")
    print(f"Successful municipalities: {len(all_weather)}")
    print(f"Failed municipalities: {len(failed_downloads)}")

    if failed_downloads:
        failed_file = output_path / f"{year}_failed_downloads.csv"

        pd.DataFrame(failed_downloads).to_csv(
            failed_file,
            index=False,
        )

        print(f"Failed download list saved to {failed_file}")

    return final_df


def main() -> None:
    """Run the São Paulo weather download pipeline."""

    start_time = time.time()

    metadata_df = pd.read_csv(
        "data/metadata/sp_municipalities.csv"
    )

    download_weather_for_state_year(
        metadata_df=metadata_df,
        parameters=["PRECTOTCORR", "T2M", "RH2M"],
        start="20210101",
        end="20211231",
        state="SP",
    )

    elapsed = time.time() - start_time
    print(f"Finished in {elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()