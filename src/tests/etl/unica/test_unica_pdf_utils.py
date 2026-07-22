"""Tests for UNICA PDF helper utilities."""

from pathlib import Path

import pytest

from src.etl.unica.unica_pdf_utils import (
    extract_pdf_text,
    find_page_containing_text,
)


# ------------------------------------------------------------------
# Fake pdfplumber objects
# ------------------------------------------------------------------

class FakePage:
    """Minimal pdfplumber page."""

    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakePdf:
    """Minimal context-managed PDF."""

    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


# ------------------------------------------------------------------
# extract_pdf_text()
# ------------------------------------------------------------------

def test_extract_pdf_text_rejects_missing_file(tmp_path):
    """Require the PDF to exist."""

    with pytest.raises(
        FileNotFoundError,
        match="UNICA report not found",
    ):
        extract_pdf_text(
            tmp_path / "missing.pdf"
        )


def test_extract_pdf_text_extracts_all_pages(
    monkeypatch,
    tmp_path,
):
    """Extract text from every page."""

    pdf_path = tmp_path / "report.pdf"
    pdf_path.touch()

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.pdfplumber.open",
        lambda path: FakePdf(
            [
                FakePage("page 1"),
                FakePage("page 2"),
                FakePage("page 3"),
            ]
        ),
    )

    result = extract_pdf_text(
        pdf_path
    )

    assert result == [
        "page 1",
        "page 2",
        "page 3",
    ]


def test_extract_pdf_text_converts_none_to_empty_string(
    monkeypatch,
    tmp_path,
):
    """Replace None page text with an empty string."""

    pdf_path = tmp_path / "report.pdf"
    pdf_path.touch()

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.pdfplumber.open",
        lambda path: FakePdf(
            [
                FakePage(None),
                FakePage("abc"),
            ]
        ),
    )

    result = extract_pdf_text(
        pdf_path
    )

    assert result == [
        "",
        "abc",
    ]


def test_extract_pdf_text_handles_empty_pdf(
    monkeypatch,
    tmp_path,
):
    """Allow PDFs containing zero pages."""

    pdf_path = tmp_path / "report.pdf"
    pdf_path.touch()

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.pdfplumber.open",
        lambda path: FakePdf([]),
    )

    result = extract_pdf_text(
        pdf_path
    )

    assert result == []


# ------------------------------------------------------------------
# find_page_containing_text()
# ------------------------------------------------------------------

def test_find_page_containing_text_returns_first_match(
    monkeypatch,
    tmp_path,
):
    """Return the first matching page."""

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.extract_pdf_text",
        lambda path: [
            "abc",
            "target",
            "target again",
        ],
    )

    result = find_page_containing_text(
        tmp_path / "dummy.pdf",
        "target",
    )

    assert result == 1


def test_find_page_containing_text_is_case_insensitive(
    monkeypatch,
    tmp_path,
):
    """Ignore case when searching."""

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.extract_pdf_text",
        lambda path: [
            "Historical Crushing",
        ],
    )

    result = find_page_containing_text(
        tmp_path / "dummy.pdf",
        "historical crushing",
    )

    assert result == 0


def test_find_page_containing_text_matches_substring(
    monkeypatch,
    tmp_path,
):
    """Allow substring matches."""

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.extract_pdf_text",
        lambda path: [
            "This page contains the UNICA table.",
        ],
    )

    result = find_page_containing_text(
        tmp_path / "dummy.pdf",
        "UNICA table",
    )

    assert result == 0


def test_find_page_containing_text_rejects_missing_text(
    monkeypatch,
    tmp_path,
):
    """Raise if the text is absent."""

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.extract_pdf_text",
        lambda path: [
            "abc",
            "def",
        ],
    )

    with pytest.raises(
        ValueError,
        match="Could not find a PDF page containing",
    ):
        find_page_containing_text(
            tmp_path / "dummy.pdf",
            "target",
        )


def test_find_page_containing_text_handles_empty_pages(
    monkeypatch,
    tmp_path,
):
    """Ignore empty pages."""

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.extract_pdf_text",
        lambda path: [
            "",
            "",
            "hello",
        ],
    )

    result = find_page_containing_text(
        tmp_path / "dummy.pdf",
        "hello",
    )

    assert result == 2


def test_find_page_containing_text_returns_zero_for_first_page(
    monkeypatch,
    tmp_path,
):
    """Use zero-based indexing."""

    monkeypatch.setattr(
        "src.etl.unica.unica_pdf_utils.extract_pdf_text",
        lambda path: [
            "target",
            "another page",
        ],
    )

    result = find_page_containing_text(
        tmp_path / "dummy.pdf",
        "target",
    )

    assert result == 0