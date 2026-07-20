from pathlib import Path
from typing import Mapping

import pandas as pd
import requests


UNICA_URL = "https://unicadata.com.br/xlsHPM.php"

RAW_OUTPUT_PATH = Path(
    "data/raw/unica/"
    "unica_state_sugarcane_2019_2020_to_2020_2021.xlsx"
)

PROCESSED_OUTPUT_PATH = Path(
    "data/processed/"
    "unica_state_sugarcane_production_2019_2020_to_2020_2021.csv"
)

SHEET_NAME = "Hist. de Prd. e Moag. - Produto"
HEADER_ROW = 9

UNICA_PARAMS = {
    "idioma": 1,
    "tipoHistorico": 2,
    "idTabela": 2494,
    "produto": "cana",
    "safra": "",
    "safraIni": "2019/2020",
    "safraFim": "2020/2021",
    "estado": "SP",
}

BRAZILIAN_STATES = {
    "Acre",
    "Alagoas",
    "Amapá",
    "Amazonas",
    "Bahia",
    "Ceará",
    "Distrito Federal",
    "Espírito Santo",
    "Goiás",
    "Maranhão",
    "Mato Grosso",
    "Mato Grosso do Sul",
    "Minas Gerais",
    "Pará",
    "Paraíba",
    "Paraná",
    "Pernambuco",
    "Piauí",
    "Rio de Janeiro",
    "Rio Grande do Norte",
    "Rio Grande do Sul",
    "Rondônia",
    "Roraima",
    "Santa Catarina",
    "São Paulo",
    "Sergipe",
    "Tocantins",
}


def download_unica_workbook(
    output_path: Path = RAW_OUTPUT_PATH,
    params: Mapping[str, str | int] | None = None,
    timeout: int = 30,
) -> Path:
    """Download a UNICA sugarcane production workbook."""

    request_params = UNICA_PARAMS if params is None else params

    response = requests.get(
        UNICA_URL,
        params=request_params,
        timeout=timeout,
    )
    response.raise_for_status()

    if not response.content:
        raise ValueError("UNICA returned an empty response.")

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if "text/html" in content_type:
        raise ValueError(
            "UNICA returned an HTML page instead of an Excel workbook."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)

    print(f"Downloaded workbook to: {output_path}")
    print(f"File size: {len(response.content):,} bytes")
    print(f"Content type: {content_type or 'unknown'}")

    return output_path


def process_unica_workbook(
    input_path: Path = RAW_OUTPUT_PATH,
    output_path: Path = PROCESSED_OUTPUT_PATH,
) -> pd.DataFrame:
    """Transform a UNICA state-level production workbook into long format."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"UNICA workbook not found: {input_path}"
        )

    workbook = pd.ExcelFile(input_path)

    if SHEET_NAME not in workbook.sheet_names:
        raise ValueError(
            f"Expected sheet '{SHEET_NAME}' was not found. "
            f"Available sheets: {workbook.sheet_names}"
        )

    production_df = pd.read_excel(
        workbook,
        sheet_name=SHEET_NAME,
        header=HEADER_ROW,
    )

    required_columns = {"Estado/Safra"}
    missing_columns = required_columns - set(production_df.columns)

    if missing_columns:
        raise ValueError(
            "UNICA worksheet is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    production_df = (
        production_df
        .rename(columns={"Estado/Safra": "state"})
        .dropna(how="all")
        .dropna(subset=["state"])
    )

    production_df = production_df.loc[
        production_df["state"].isin(BRAZILIAN_STATES)
    ].copy()

    if production_df.empty:
        raise ValueError(
            "No recognized Brazilian state rows were found "
            "in the UNICA worksheet."
        )

    long_df = production_df.melt(
        id_vars="state",
        var_name="harvest_year",
        value_name="production_thousand_tonnes",
    )

    long_df = long_df.dropna(
        subset=["production_thousand_tonnes"]
    )

    if long_df.empty:
        raise ValueError(
            "No production observations remained after processing."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    long_df.to_csv(output_path, index=False)

    print(f"Processed file saved to: {output_path}")
    print(f"Processed rows: {len(long_df)}")

    return long_df


def main() -> None:
    """Download and process UNICA state-level sugarcane production data."""

    workbook_path = download_unica_workbook()

    process_unica_workbook(
        input_path=workbook_path,
    )


if __name__ == "__main__":
    main()