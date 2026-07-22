"""Tests for the UNICA positioned-word table extractor."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.etl.unica.unica_table_extractor import (
    TABLE_TITLE,
    combine_words,
    determine_column_boundaries,
    extract_data_rows,
    extract_historical_crushing_tables,
    extract_table_from_words,
    extract_tables_from_page,
    find_header_phrase_center,
    find_header_word,
    find_season_header_row,
    group_words_into_lines,
    split_line_into_columns,
)


def make_word(
    text: str,
    x0: float,
    x1: float,
    top: float,
) -> dict:
    """Build one pdfplumber-style positioned word."""

    return {
        "text": text,
        "x0": x0,
        "x1": x1,
        "top": top,
    }


def build_header_words() -> list[dict]:
    """Build positioned words for the four logical table headers."""

    return [
        make_word("Quinzena", 10, 30, 10),
        make_word("São", 100, 115, 10),
        make_word("Paulo", 118, 140, 10),
        make_word("Centro-Sul", 220, 270, 10),
        make_word("Demais", 340, 370, 10),
        make_word("Estados", 374, 410, 10),
    ]


def build_full_page_words() -> list[dict]:
    """Build a minimal positioned-word representation of the target table."""

    return [
        *build_header_words(),
        make_word("2025/2026", 95, 145, 30),
        make_word("2025/2026", 215, 275, 30),
        make_word("2025/2026", 340, 410, 30),
        make_word("2026/2027", 95, 145, 31),
        make_word("2026/2027", 215, 275, 31),
        make_word("2026/2027", 340, 410, 31),
        make_word("16/04", 10, 35, 50),
        make_word("8.000.000", 100, 150, 50),
        make_word("11.000.000", 220, 280, 50),
        make_word("3.000.000", 345, 400, 50),
        make_word("01/05", 10, 35, 70),
        make_word("10.000.000", 100, 155, 70),
        make_word("13.000.000", 220, 280, 70),
        make_word("3.000.000", 345, 400, 70),
    ]


def test_table_title_matches_expected_heading() -> None:
    """Keep the official UNICA table title stable."""

    assert TABLE_TITLE == (
        "Histórico da moagem quinzenal, "
        "ACUMULADA, da região Centro-Sul"
    )


def test_group_words_into_lines_sorts_by_top_and_x_position() -> None:
    """Group nearby words and sort words within each visual line."""

    words = [
        make_word("B", 50, 60, 11),
        make_word("C", 10, 20, 30),
        make_word("A", 10, 20, 10),
    ]

    result = group_words_into_lines(
        words,
        y_tolerance=2,
    )

    assert [
        [word["text"] for word in line]
        for line in result
    ] == [
        ["A", "B"],
        ["C"],
    ]


def test_group_words_into_lines_respects_tolerance() -> None:
    """Place vertically distant words on separate lines."""

    words = [
        make_word("A", 10, 20, 10),
        make_word("B", 30, 40, 15),
    ]

    result = group_words_into_lines(
        words,
        y_tolerance=4,
    )

    assert len(result) == 2


def test_combine_words_returns_none_for_empty_input() -> None:
    """Return None when a logical cell has no words."""

    assert combine_words([]) is None


def test_combine_words_strips_and_joins_nonempty_text() -> None:
    """Join ordered words while removing blank text."""

    words = [
        make_word(" São ", 10, 20, 10),
        make_word("", 21, 22, 10),
        make_word("Paulo", 23, 40, 10),
    ]

    assert combine_words(words) == "São Paulo"


def test_find_header_word_is_case_insensitive() -> None:
    """Locate a header using case-insensitive exact matching."""

    words = build_header_words()

    result = find_header_word(
        words,
        "quinzena",
    )

    assert result["text"] == "Quinzena"


def test_find_header_word_rejects_missing_header() -> None:
    """Raise when a requested header word is absent."""

    with pytest.raises(
        ValueError,
        match="Could not locate table header word",
    ):
        find_header_word(
            build_header_words(),
            "Missing",
        )


def test_find_header_phrase_center_uses_outer_word_edges() -> None:
    """Calculate a phrase center from its leftmost and rightmost edges."""

    result = find_header_phrase_center(
        build_header_words(),
        [
            "São",
            "Paulo",
        ],
    )

    assert result == pytest.approx(
        (100 + 140) / 2
    )


def test_find_header_phrase_center_is_case_insensitive() -> None:
    """Match phrase words without case sensitivity."""

    result = find_header_phrase_center(
        build_header_words(),
        [
            "sÃO",
            "pAULO",
        ],
    )

    assert result == pytest.approx(120)


def test_find_header_phrase_center_rejects_missing_phrase() -> None:
    """Raise when none of the phrase words are present."""

    with pytest.raises(
        ValueError,
        match="Could not locate header phrase",
    ):
        find_header_phrase_center(
            build_header_words(),
            [
                "Unknown",
            ],
        )


def test_determine_column_boundaries_returns_midpoints() -> None:
    """Build boundaries halfway between logical header centers."""

    result = determine_column_boundaries(
        build_header_words()
    )

    date_center = 20
    sao_paulo_center = 120
    centro_sul_center = 245
    demais_estados_center = 375

    assert result == pytest.approx(
        (
            (date_center + sao_paulo_center) / 2,
            (sao_paulo_center + centro_sul_center) / 2,
            (centro_sul_center + demais_estados_center) / 2,
        )
    )


def test_split_line_into_columns_assigns_words_by_center() -> None:
    """Assign words to the four logical columns."""

    line = [
        make_word("16/04", 10, 30, 50),
        make_word("8.000.000", 100, 140, 50),
        make_word("11.000.000", 220, 280, 50),
        make_word("3.000.000", 345, 400, 50),
    ]

    result = split_line_into_columns(
        line,
        boundaries=(
            70,
            182.5,
            310,
        ),
    )

    assert result == [
        "16/04",
        "8.000.000",
        "11.000.000",
        "3.000.000",
    ]


def test_split_line_into_columns_returns_none_for_empty_column() -> None:
    """Represent a missing logical cell with None."""

    line = [
        make_word("16/04", 10, 30, 50),
        make_word("8.000.000", 100, 140, 50),
    ]

    result = split_line_into_columns(
        line,
        boundaries=(
            70,
            182.5,
            310,
        ),
    )

    assert result == [
        "16/04",
        "8.000.000",
        None,
        None,
    ]


def test_find_season_header_row_returns_split_row() -> None:
    """Locate a visual line containing at least two season labels."""

    lines = [
        [
            make_word("Header", 10, 30, 10),
        ],
        [
            make_word("2025/2026", 100, 150, 30),
            make_word("2026/2027", 220, 280, 30),
        ],
    ]

    result = find_season_header_row(
        lines,
        boundaries=(
            70,
            182.5,
            310,
        ),
    )

    assert result == [
        None,
        "2025/2026",
        "2026/2027",
        None,
    ]


def test_find_season_header_row_rejects_missing_row() -> None:
    """Raise when fewer than two season labels occur on every line."""

    lines = [
        [
            make_word("2025/2026", 100, 150, 30),
        ],
    ]

    with pytest.raises(
        ValueError,
        match="Could not locate the UNICA season-header row",
    ):
        find_season_header_row(
            lines,
            boundaries=(
                70,
                182.5,
                310,
            ),
        )


def test_extract_data_rows_keeps_only_dated_rows() -> None:
    """Extract only rows containing a DD/MM date token."""

    lines = [
        [
            make_word("Label", 10, 30, 10),
            make_word("Ignored", 100, 150, 10),
        ],
        [
            make_word("period", 5, 15, 30),
            make_word("16/04", 16, 35, 30),
            make_word("8.000.000", 100, 150, 30),
            make_word("11.000.000", 220, 280, 30),
            make_word("3.000.000", 345, 400, 30),
        ],
    ]

    result = extract_data_rows(
        lines,
        boundaries=(
            70,
            182.5,
            310,
        ),
    )

    assert result == [
        [
            "16/04",
            "8.000.000",
            "11.000.000",
            "3.000.000",
        ]
    ]


def test_extract_data_rows_rejects_page_without_dated_rows() -> None:
    """Raise when no DD/MM data rows can be reconstructed."""

    lines = [
        [
            make_word("Header", 10, 30, 10),
        ],
    ]

    with pytest.raises(
        ValueError,
        match="No dated crushing rows were extracted",
    ):
        extract_data_rows(
            lines,
            boundaries=(
                70,
                182.5,
                310,
            ),
        )


class FakePage:
    """Minimal pdfplumber page substitute."""

    def __init__(
        self,
        words: list[dict],
    ) -> None:
        self._words = words
        self.extract_words_kwargs = None

    def extract_words(
        self,
        **kwargs,
    ) -> list[dict]:
        self.extract_words_kwargs = kwargs
        return self._words


class FakePdf:
    """Minimal context-managed pdfplumber document substitute."""

    def __init__(
        self,
        pages: list[FakePage],
    ) -> None:
        self.pages = pages

    def __enter__(self) -> "FakePdf":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        return None


def test_extract_table_from_words_reconstructs_expected_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reconstruct the canonical table shape from positioned words."""

    page = FakePage(
        build_full_page_words()
    )

    monkeypatch.setattr(
        "src.etl.unica.unica_table_extractor.pdfplumber.open",
        lambda path: FakePdf([page]),
    )

    result = extract_table_from_words(
        pdf_path=tmp_path / "report.pdf",
        page_index=0,
    )

    assert result[0] == [
        "",
        "CANA-DE-AÇÚCAR (toneladas)",
        None,
        None,
    ]
    assert result[1] == [
        "Quinzena",
        "São Paulo",
        "Centro-Sul",
        "Demais Estados",
    ]
    assert result[-2:] == [
        [
            "16/04",
            "8.000.000",
            "11.000.000",
            "3.000.000",
        ],
        [
            "01/05",
            "10.000.000",
            "13.000.000",
            "3.000.000",
        ],
    ]

    assert page.extract_words_kwargs == {
        "x_tolerance": 2,
        "y_tolerance": 2,
        "keep_blank_chars": False,
        "use_text_flow": False,
    }


def test_extract_table_from_words_rejects_empty_word_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise when pdfplumber extracts no positioned words."""

    monkeypatch.setattr(
        "src.etl.unica.unica_table_extractor.pdfplumber.open",
        lambda path: FakePdf(
            [
                FakePage([]),
            ]
        ),
    )

    with pytest.raises(
        ValueError,
        match="No words were extracted",
    ):
        extract_table_from_words(
            pdf_path=tmp_path / "report.pdf",
            page_index=0,
        )


def test_extract_tables_from_page_wraps_single_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Preserve the historical list-of-tables API."""

    expected_table = [
        [
            "Quinzena",
        ],
    ]

    monkeypatch.setattr(
        "src.etl.unica.unica_table_extractor.extract_table_from_words",
        lambda pdf_path, page_index: expected_table,
    )

    result = extract_tables_from_page(
        pdf_path=tmp_path / "report.pdf",
        page_index=3,
    )

    assert result == [
        expected_table
    ]


def test_extract_historical_crushing_tables_uses_found_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Locate the target page and extract from that exact index."""

    calls = SimpleNamespace(
        search_text=None,
        page_index=None,
    )

    def fake_find_page_containing_text(
        pdf_path: Path,
        search_text: str,
    ) -> int:
        calls.search_text = search_text
        return 4

    def fake_extract_tables_from_page(
        pdf_path: Path,
        page_index: int,
    ) -> list:
        calls.page_index = page_index
        return [
            [
                [
                    "table",
                ]
            ]
        ]

    monkeypatch.setattr(
        "src.etl.unica.unica_table_extractor.find_page_containing_text",
        fake_find_page_containing_text,
    )

    monkeypatch.setattr(
        "src.etl.unica.unica_table_extractor.extract_tables_from_page",
        fake_extract_tables_from_page,
    )

    result = extract_historical_crushing_tables(
        pdf_path=tmp_path / "report.pdf",
    )

    assert calls.search_text == TABLE_TITLE
    assert calls.page_index == 4
    assert result == [
        [
            [
                "table",
            ]
        ]
    ]