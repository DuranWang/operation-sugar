import pandas as pd

from src.feature_engineering.rainfall import (
    calculate_max_consecutive_dry_days,
)
# ======= Test ===================================================================================================
def _test_calculate_max_consecutive_dry_days() -> None:
    test_cases = {
        "continuous dry spell": (
            pd.Series([0.0, 0.5, 0.8, 3.0]),
            pd.Series(
                pd.to_datetime(
                    [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                        "2020-01-04",
                    ]
                )
            ),
            3,
        ),
        "date gap breaks dry spell": (
            pd.Series([0.0, 0.5, 0.8, 0.2]),
            pd.Series(
                pd.to_datetime(
                    [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                        "2020-02-01",
                    ]
                )
            ),
            3,
        ),
        "threshold boundary": (
            pd.Series([0.0, 1.0, 0.0]),
            pd.Series(
                pd.to_datetime(
                    [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                    ]
                )
            ),
            1,
        ),
        "all wet": (
            pd.Series([2.0, 3.0, 5.0]),
            pd.Series(
                pd.to_datetime(
                    [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                    ]
                )
            ),
            0,
        ),
        "empty series": (
            pd.Series([], dtype=float),
            pd.Series([], dtype="datetime64[ns]"),
            0,
        ),
    }

    for name, (rainfall, dates, expected) in test_cases.items():
        actual = calculate_max_consecutive_dry_days(
            rainfall=rainfall,
            dates=dates,
        )

        assert actual == expected, (
            f"{name}: expected {expected}, got {actual}"
        )

    print("All rainfall CDD tests passed.")


if __name__ == "__main__":
    _test_calculate_max_consecutive_dry_days()

# ======= Test ===================================================================================================
