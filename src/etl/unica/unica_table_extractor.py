"""
Extract structured cumulative crushing tables from UNICA PDF reports.
"""

from pathlib import Path
import re

import pdfplumber

from src.etl.unica.unica_pdf_utils import (
    find_page_containing_text,
)


TABLE_TITLE = (
    "Histórico da moagem quinzenal, "
    "ACUMULADA, da região Centro-Sul"
)

DATE_PATTERN = re.compile(
    r"^\d{2}/\d{2}$"
)

SEASON_PATTERN = re.compile(
    r"^\d{4}/\d{4}$"
)


def group_words_into_lines(
    words: list[dict],
    y_tolerance: float = 4.0,
) -> list[list[dict]]:
    """
    Group PDF words into visual text lines using their
    vertical coordinates.
    """

    sorted_words = sorted(
        words,
        key=lambda word: (
            float(word["top"]),
            float(word["x0"]),
        ),
    )

    lines: list[list[dict]] = []

    for word in sorted_words:
        word_top = float(word["top"])

        matching_line = None

        for line in lines:
            line_top = sum(
                float(existing_word["top"])
                for existing_word in line
            ) / len(line)

            if abs(word_top - line_top) <= y_tolerance:
                matching_line = line
                break

        if matching_line is None:
            lines.append(
                [word]
            )
        else:
            matching_line.append(
                word
            )

    for line in lines:
        line.sort(
            key=lambda word: float(word["x0"])
        )

    return lines


def combine_words(
    words: list[dict],
) -> str | None:
    """Combine ordered PDF words into one cell value."""

    if not words:
        return None

    return " ".join(
        str(word["text"]).strip()
        for word in words
        if str(word["text"]).strip()
    )


def find_header_word(
    words: list[dict],
    text: str,
) -> dict:
    """Find a table-header word using case-insensitive matching."""

    normalized_text = text.casefold()

    for word in words:
        if str(word["text"]).casefold() == normalized_text:
            return word

    raise ValueError(
        f"Could not locate table header word: {text!r}"
    )


def find_header_phrase_center(
    words: list[dict],
    phrase_words: list[str],
) -> float:
    """
    Find the approximate horizontal center of a table-header phrase.
    """

    matching_words = []

    normalized_phrase_words = {
        phrase_word.casefold()
        for phrase_word in phrase_words
    }

    for word in words:
        normalized_word = str(
            word["text"]
        ).strip().casefold()

        if normalized_word in normalized_phrase_words:
            matching_words.append(
                word
            )

    if not matching_words:
        raise ValueError(
            "Could not locate header phrase containing: "
            f"{phrase_words}"
        )

    left = min(
        float(word["x0"])
        for word in matching_words
    )

    right = max(
        float(word["x1"])
        for word in matching_words
    )

    return (
        left + right
    ) / 2


def determine_column_boundaries(
    words: list[dict],
) -> tuple[float, float, float]:
    """
    Determine boundaries separating the four logical columns:

    Quinzena | São Paulo | Centro-Sul | Demais Estados
    """

    date_header = find_header_word(
        words,
        "Quinzena",
    )

    date_center = (
        float(date_header["x0"])
        + float(date_header["x1"])
    ) / 2

    sao_paulo_center = find_header_phrase_center(
        words,
        [
            "São",
            "Paulo",
        ],
    )

    centro_sul_center = find_header_phrase_center(
        words,
        [
            "Centro-Sul",
        ],
    )

    demais_estados_center = find_header_phrase_center(
        words,
        [
            "Demais",
            "Estados",
        ],
    )

    first_boundary = (
        date_center + sao_paulo_center
    ) / 2

    second_boundary = (
        sao_paulo_center + centro_sul_center
    ) / 2

    third_boundary = (
        centro_sul_center + demais_estados_center
    ) / 2

    return (
        first_boundary,
        second_boundary,
        third_boundary,
    )


def split_line_into_columns(
    line: list[dict],
    boundaries: tuple[float, float, float],
) -> list[str | None]:
    """Split one visual PDF line into four logical table columns."""

    first_boundary, second_boundary, third_boundary = (
        boundaries
    )

    column_words: list[list[dict]] = [
        [],
        [],
        [],
        [],
    ]

    for word in line:
        word_center = (
            float(word["x0"])
            + float(word["x1"])
        ) / 2

        if word_center < first_boundary:
            column_index = 0
        elif word_center < second_boundary:
            column_index = 1
        elif word_center < third_boundary:
            column_index = 2
        else:
            column_index = 3

        column_words[column_index].append(
            word
        )

    return [
        combine_words(words_in_column)
        for words_in_column in column_words
    ]


def find_season_header_row(
    lines: list[list[dict]],
    boundaries: tuple[float, float, float],
) -> list[str | None]:
    """
    Find the line containing season labels such as
    2025/2026 and 2026/2027.
    """

    for line in lines:
        line_text = [
            str(word["text"]).strip()
            for word in line
        ]

        season_count = sum(
            bool(
                SEASON_PATTERN.fullmatch(text)
            )
            for text in line_text
        )

        if season_count >= 2:
            return split_line_into_columns(
                line,
                boundaries,
            )

    raise ValueError(
        "Could not locate the UNICA season-header row."
    )


def extract_data_rows(
    lines: list[list[dict]],
    boundaries: tuple[float, float, float],
) -> list[list[str | None]]:
    """
    Extract rows beginning with a bi-weekly date such as
    16/04 or 01/05.
    """

    data_rows = []

    for line in lines:
        cells = split_line_into_columns(
            line,
            boundaries,
        )

        date_cell = cells[0]

        if date_cell is None:
            continue

        date_tokens = date_cell.split()

        matching_dates = [
            token
            for token in date_tokens
            if DATE_PATTERN.fullmatch(token)
        ]

        if not matching_dates:
            continue

        cells[0] = matching_dates[0]

        data_rows.append(
            cells
        )

    if not data_rows:
        raise ValueError(
            "No dated crushing rows were extracted "
            "from the UNICA table."
        )

    return data_rows


def extract_table_from_words(
    pdf_path: Path,
    page_index: int,
) -> list[list[str | None]]:
    """
    Reconstruct the historical cumulative crushing table
    using positioned PDF words.
    """

    with pdfplumber.open(
        pdf_path
    ) as pdf:
        page = pdf.pages[
            page_index
        ]

        words = page.extract_words(
            x_tolerance=2,
            y_tolerance=2,
            keep_blank_chars=False,
            use_text_flow=False,
        )

    if not words:
        raise ValueError(
            "No words were extracted from the UNICA PDF page."
        )

    lines = group_words_into_lines(
        words,
        y_tolerance=4.0,
    )

    boundaries = determine_column_boundaries(
        words
    )

    season_header_row = find_season_header_row(
        lines,
        boundaries,
    )

    data_rows = extract_data_rows(
        lines,
        boundaries,
    )

    reconstructed_table = [
        [
            "",
            "CANA-DE-AÇÚCAR (toneladas)",
            None,
            None,
        ],
        [
            "Quinzena",
            "São Paulo",
            "Centro-Sul",
            "Demais Estados",
        ],
        season_header_row,
        *data_rows,
    ]

    return reconstructed_table


def extract_tables_from_page(
    pdf_path: Path,
    page_index: int,
) -> list[list[list[str | None]]]:
    """
    Extract the cumulative crushing table from a specified page.

    The return type remains a list of tables so downstream
    code stays compatible with the earlier extractor API.
    """

    reconstructed_table = extract_table_from_words(
        pdf_path=pdf_path,
        page_index=page_index,
    )

    return [
        reconstructed_table
    ]


def extract_historical_crushing_tables(
    pdf_path: Path,
) -> list[list[list[str | None]]]:
    """
    Locate and extract the historical cumulative
    crushing table.
    """

    page_index = find_page_containing_text(
        pdf_path=pdf_path,
        search_text=TABLE_TITLE,
    )

    return extract_tables_from_page(
        pdf_path=pdf_path,
        page_index=page_index,
    )


if __name__ == "__main__":
    project_root = Path(
        __file__
    ).resolve().parents[3]

    input_path = (
        project_root
        / "data"
        / "raw"
        / "unica"
        / "biweekly_reports"
        / "unica_report_2026-06-01.pdf"
    )

    tables = extract_historical_crushing_tables(
        input_path
    )

    print(
        f"Detected {len(tables)} table(s).\n"
    )

    for table_number, table in enumerate(
        tables,
        start=1,
    ):
        print("=" * 80)
        print(
            f"TABLE {table_number}"
        )
        print("=" * 80)

        for row_index, row in enumerate(
            table
        ):
            print(
                f"ROW {row_index}: {row}"
            )