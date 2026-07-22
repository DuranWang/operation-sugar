"""
Parse UNICA bi-weekly harvest report PDFs.

This module reads report text and locates pages containing
specific table titles.
"""

from pathlib import Path

import pdfplumber


def extract_pdf_text(
    pdf_path: Path,
) -> list[str]:
    """
    Extract text from every page of a UNICA PDF report.

    Parameters
    ----------
    pdf_path:
        Path to the downloaded UNICA PDF.

    Returns
    -------
    list[str]
        Extracted text for each PDF page.
    """

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"UNICA report not found: {pdf_path}"
        )

    pages_text: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)

    return pages_text


def find_page_containing_text(
    pdf_path: Path,
    search_text: str,
) -> int:
    """
    Find the zero-based page index containing specified text.

    Parameters
    ----------
    pdf_path:
        Path to the downloaded UNICA PDF.

    search_text:
        Text used to identify the target page.

    Returns
    -------
    int
        Zero-based page index.

    Raises
    ------
    ValueError
        If the search text is not found.
    """

    pages_text = extract_pdf_text(pdf_path)

    normalized_search_text = search_text.casefold()

    for page_index, page_text in enumerate(pages_text):
        if normalized_search_text in page_text.casefold():
            return page_index

    raise ValueError(
        f"Could not find a PDF page containing: {search_text!r}"
    )


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[3]

    input_path = (
        project_root
        / "data"
        / "raw"
        / "unica"
        / "biweekly_reports"
        / "unica_report_2026-06-01.pdf"
    )

    target_title = (
        "Histórico da moagem quinzenal, "
        "ACUMULADA, da região Centro-Sul"
    )

    page_index = find_page_containing_text(
        pdf_path=input_path,
        search_text=target_title,
    )

    print(
        f"Target table found on PDF page {page_index + 1} "
        f"(zero-based index {page_index})."
    )