"""Tests for safe UNICA historical database updates."""

from pathlib import Path

import pandas as pd
import pytest

from src.etl.unica.update_crushing_history import (
    HISTORY_COLUMNS,
    create_timestamped_backup,
    find_conflicting_observations,
    find_new_observations,
    prepare_crushing_dataframe,
    update_crushing_history,
    validate_existing_history_preserved,
    validate_final_dataframe,
    validate_no_duplicate_keys,
    validate_required_columns,
    write_dataframe_safely,
)


def build_history_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "season": ["25-26"] * 4,
            "period_end_date": [
                "2025-04-16",
                "2025-04-16",
                "2025-05-01",
                "2025-05-01",
            ],
            "region": [
                "other_states",
                "sao_paulo",
                "other_states",
                "sao_paulo",
            ],
            "crush_tonnes": [
                2_000_000,
                8_000_000,
                3_000_000,
                10_000_000,
            ],
        }
    )


def build_report_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "season": ["25-26"] * 6,
            "period_end_date": [
                "2025-05-01",
                "2025-05-01",
                "2025-05-01",
                "2025-05-16",
                "2025-05-16",
                "2025-05-16",
            ],
            "region": [
                "other_states",
                "sao_paulo",
                "centre_south",
                "other_states",
                "sao_paulo",
                "centre_south",
            ],
            "crush_tonnes": [
                3_000_000,
                10_000_000,
                13_000_000,
                4_000_000,
                12_000_000,
                16_000_000,
            ],
        }
    )


def write_csv(dataframe: pd.DataFrame, path: Path) -> None:
    dataframe.to_csv(path, index=False)


def test_validate_required_columns_accepts_valid_dataframe() -> None:
    validate_required_columns(
        build_history_dataframe(),
        HISTORY_COLUMNS,
        "history",
    )


@pytest.mark.parametrize("missing_column", HISTORY_COLUMNS)
def test_validate_required_columns_rejects_missing_column(
    missing_column: str,
) -> None:
    dataframe = build_history_dataframe().drop(columns=[missing_column])

    with pytest.raises(ValueError, match="missing required columns"):
        validate_required_columns(
            dataframe,
            HISTORY_COLUMNS,
            "history",
        )


def test_prepare_crushing_dataframe_normalizes_schema() -> None:
    dataframe = build_history_dataframe()
    dataframe["season"] = " 25-26 "
    dataframe["region"] = dataframe["region"].map(
        lambda value: f" {value} "
    )
    dataframe["extra"] = "ignored"

    result = prepare_crushing_dataframe(
        dataframe,
        "history",
    )

    assert result.columns.tolist() == HISTORY_COLUMNS
    assert set(result["season"]) == {"25-26"}
    assert set(result["region"]) == {
        "sao_paulo",
        "other_states",
    }
    assert pd.api.types.is_datetime64_any_dtype(
        result["period_end_date"]
    )


def test_prepare_crushing_dataframe_rejects_invalid_date() -> None:
    dataframe = build_history_dataframe()
    dataframe.loc[0, "period_end_date"] = "not-a-date"

    with pytest.raises(ValueError):
        prepare_crushing_dataframe(
            dataframe,
            "history",
        )


def test_validate_no_duplicate_keys_rejects_duplicate() -> None:
    dataframe = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )
    dataframe = pd.concat(
        [dataframe, dataframe.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate keys found"):
        validate_no_duplicate_keys(
            dataframe,
            "history",
        )


def test_find_conflicting_observations_returns_disagreement() -> None:
    history_df = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )
    report_df = history_df.iloc[[2, 3]].copy()
    report_df.loc[
        report_df["region"] == "sao_paulo",
        "crush_tonnes",
    ] = 999

    result = find_conflicting_observations(
        history_df,
        report_df,
    )

    assert len(result) == 1
    assert result.iloc[0]["region"] == "sao_paulo"
    assert result.iloc[0]["crush_tonnes_report"] == 999


def test_find_conflicting_observations_accepts_identical_overlap() -> None:
    history_df = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )
    report_df = history_df.iloc[[2, 3]].copy()

    result = find_conflicting_observations(
        history_df,
        report_df,
    )

    assert result.empty


def test_find_new_observations_returns_only_new_keys() -> None:
    history_df = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )
    report_df = build_report_dataframe()
    report_df = report_df.loc[
        report_df["region"] != "centre_south"
    ]
    report_df = prepare_crushing_dataframe(
        report_df,
        "report",
    )

    result = find_new_observations(
        history_df,
        report_df,
    )

    assert len(result) == 2
    assert set(result["period_end_date"]) == {
        pd.Timestamp("2025-05-16")
    }


def test_validate_existing_history_preserved_accepts_append() -> None:
    history_df = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )
    new_row = pd.DataFrame(
        {
            "season": ["25-26"],
            "period_end_date": pd.to_datetime(["2025-05-16"]),
            "region": ["sao_paulo"],
            "crush_tonnes": [12_000_000],
        }
    )
    combined_df = pd.concat(
        [history_df, new_row],
        ignore_index=True,
    )

    validate_existing_history_preserved(
        history_df,
        combined_df,
    )


def test_validate_existing_history_preserved_rejects_changed_value() -> None:
    history_df = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )
    combined_df = history_df.copy()
    combined_df.loc[0, "crush_tonnes"] = 1

    with pytest.raises(
        ValueError,
        match="historical crush values changed",
    ):
        validate_existing_history_preserved(
            history_df,
            combined_df,
        )


def test_validate_final_dataframe_rejects_wrong_row_count() -> None:
    dataframe = prepare_crushing_dataframe(
        build_history_dataframe(),
        "history",
    )

    with pytest.raises(ValueError, match="Unexpected final row count"):
        validate_final_dataframe(
            dataframe,
            expected_row_count=len(dataframe) + 1,
        )


def test_create_timestamped_backup_copies_file(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    history_path.write_text("original", encoding="utf-8")

    backup_path = create_timestamped_backup(
        history_path
    )

    assert backup_path.exists()
    assert ".backup.csv" in backup_path.name
    assert backup_path.read_text(
        encoding="utf-8"
    ) == "original"


def test_write_dataframe_safely_writes_and_removes_temp(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "history.csv"
    dataframe = build_history_dataframe()

    write_dataframe_safely(
        dataframe,
        output_path,
    )

    assert output_path.exists()
    assert not (
        tmp_path / "history.tmp.csv"
    ).exists()
    assert len(pd.read_csv(output_path)) == len(dataframe)


def test_update_crushing_history_appends_new_rows(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    write_csv(build_history_dataframe(), history_path)
    write_csv(build_report_dataframe(), report_path)

    result = update_crushing_history(
        history_path,
        report_path,
    )

    assert len(result) == 6
    assert set(result["region"]) == {
        "sao_paulo",
        "other_states",
    }
    assert not (
        result["region"] == "centre_south"
    ).any()
    assert len(
        list(tmp_path.glob("history_*.backup.csv"))
    ) == 1


def test_update_crushing_history_does_not_duplicate_overlap(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"
    history_df = build_history_dataframe()
    report_df = history_df.loc[
        history_df["period_end_date"] == "2025-05-01"
    ]

    write_csv(history_df, history_path)
    write_csv(report_df, report_path)

    result = update_crushing_history(
        history_path,
        report_path,
    )

    assert len(result) == len(history_df)


def test_update_crushing_history_rejects_conflict_without_writing(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"
    history_df = build_history_dataframe()
    report_df = history_df.iloc[[0]].copy()
    report_df.loc[
        report_df.index[0],
        "crush_tonnes",
    ] = 999

    write_csv(history_df, history_path)
    original_bytes = history_path.read_bytes()
    write_csv(report_df, report_path)

    with pytest.raises(
        ValueError,
        match="Conflicting UNICA observations detected",
    ):
        update_crushing_history(
            history_path,
            report_path,
        )

    assert history_path.read_bytes() == original_bytes
    assert not list(
        tmp_path.glob("history_*.backup.csv")
    )


def test_update_crushing_history_excludes_centre_south(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    report_df = pd.DataFrame(
        {
            "season": ["25-26", "25-26"],
            "period_end_date": [
                "2025-05-16",
                "2025-05-16",
            ],
            "region": [
                "sao_paulo",
                "centre_south",
            ],
            "crush_tonnes": [
                12_000_000,
                16_000_000,
            ],
        }
    )

    write_csv(build_history_dataframe(), history_path)
    write_csv(report_df, report_path)

    result = update_crushing_history(
        history_path,
        report_path,
    )

    assert len(result) == 5
    assert "centre_south" not in set(result["region"])


def test_update_crushing_history_rejects_unknown_report_region(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    report_df = pd.DataFrame(
        {
            "season": ["25-26"],
            "period_end_date": ["2025-05-16"],
            "region": ["unknown_region"],
            "crush_tonnes": [1],
        }
    )

    write_csv(build_history_dataframe(), history_path)
    write_csv(report_df, report_path)

    with pytest.raises(
        ValueError,
        match="report contains unsupported regions",
    ):
        update_crushing_history(
            history_path,
            report_path,
        )


def test_update_crushing_history_rejects_only_centre_south(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    report_df = pd.DataFrame(
        {
            "season": ["25-26"],
            "period_end_date": ["2025-05-16"],
            "region": ["centre_south"],
            "crush_tonnes": [16_000_000],
        }
    )

    write_csv(build_history_dataframe(), history_path)
    write_csv(report_df, report_path)

    with pytest.raises(
        ValueError,
        match="contains no rows for the historical database regions",
    ):
        update_crushing_history(
            history_path,
            report_path,
        )


@pytest.mark.parametrize(
    ("missing_file", "message"),
    [
        (
            "history",
            "Historical database does not exist",
        ),
        (
            "report",
            "Normalized report does not exist",
        ),
    ],
)
def test_update_crushing_history_rejects_missing_file(
    tmp_path: Path,
    missing_file: str,
    message: str,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    if missing_file != "history":
        write_csv(build_history_dataframe(), history_path)

    if missing_file != "report":
        write_csv(build_report_dataframe(), report_path)

    with pytest.raises(FileNotFoundError, match=message):
        update_crushing_history(
            history_path,
            report_path,
        )


def test_update_crushing_history_restores_backup_after_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    write_csv(build_history_dataframe(), history_path)
    original_bytes = history_path.read_bytes()
    write_csv(build_report_dataframe(), report_path)

    def fail_write(
        dataframe: pd.DataFrame,
        output_path: Path,
    ) -> None:
        output_path.write_text(
            "corrupted",
            encoding="utf-8",
        )
        raise OSError("simulated failure")

    monkeypatch.setattr(
        "src.etl.unica.update_crushing_history.write_dataframe_safely",
        fail_write,
    )

    with pytest.raises(OSError, match="simulated failure"):
        update_crushing_history(
            history_path,
            report_path,
        )

    assert history_path.read_bytes() == original_bytes


def test_update_crushing_history_sorts_output(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.csv"
    report_path = tmp_path / "report.csv"

    write_csv(
        build_history_dataframe().sample(
            frac=1,
            random_state=1,
        ),
        history_path,
    )
    write_csv(
        build_report_dataframe().sample(
            frac=1,
            random_state=2,
        ),
        report_path,
    )

    result = update_crushing_history(
        history_path,
        report_path,
    )

    expected = (
        result
        .sort_values(
            [
                "season",
                "period_end_date",
                "region",
            ]
        )
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        result,
        expected,
    )