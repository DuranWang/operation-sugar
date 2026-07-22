from pathlib import Path
import requests

"""
Download UNICA bi-weekly harvest reports.
"""

REPORT_URL = (
    "https://unicadata.com.br/"
    "download_media.php?idM=6758186"
)


def download_unica_report(
    url: str,
    output_path: Path,
    timeout: int = 30,
) -> Path:
    """Download a UNICA bi-weekly harvest report PDF."""

    response = requests.get(
        url,
        timeout=timeout,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if not response.content.startswith(b"%PDF"):
        raise ValueError(
            "Downloaded content does not appear to be a valid PDF. "
            f"Received Content-Type: {content_type}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(response.content)

    return output_path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[3]

    output_path = (
        project_root
        / "data"
        / "raw"
        / "unica"
        / "biweekly_reports"
        / "unica_report_2026-06-01.pdf"
    )

    saved_path = download_unica_report(
        url=REPORT_URL,
        output_path=output_path,
    )

    print(f"Saved UNICA report to: {saved_path}")