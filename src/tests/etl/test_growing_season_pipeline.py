import pandas as pd

from src.feature_engineering.pipeline import (
    calculate_growing_season_features,
)


def test_growing_season_pipeline() -> None:
    test_weather = pd.DataFrame(
        {
            "ibge_code": [3500105] * 10,
            "municipality": ["Adamantina"] * 10,
            "state": ["SP"] * 10,
            "date": [
                "2019-09-01",
                "2019-09-02",
                "2019-09-03",
                "2019-09-04",
                "2019-09-05",
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-04",
                "2020-01-05",
            ],
            "year": [
                2019,
                2019,
                2019,
                2019,
                2019,
                2020,
                2020,
                2020,
                2020,
                2020,
            ],
            "month": [
                9,
                9,
                9,
                9,
                9,
                1,
                1,
                1,
                1,
                1,
            ],
            "PRECTOTCORR": [
                0.0,
                0.2,
                0.5,
                3.0,
                0.0,
                0.0,
                0.4,
                0.8,
                2.0,
                0.0,
            ],
            "T2M": [
                20.0,
                21.0,
                22.0,
                23.0,
                24.0,
                25.0,
                26.0,
                27.0,
                28.0,
                29.0,
            ],
        }
    )

    result = calculate_growing_season_features(test_weather)

    assert len(result) == 1
    assert result.loc[0, "harvest_year"] == 2020
    assert result.loc[0, "growing_season_total_rainfall"] == 6.9
    assert result.loc[0, "growing_season_average_temperature"] == 24.5
    assert (
        result.loc[
            0,
            "growing_season_max_consecutive_dry_days",
        ]
        == 3
    )


if __name__ == "__main__":
    test_growing_season_pipeline()
    print("Growing-season pipeline test passed.")