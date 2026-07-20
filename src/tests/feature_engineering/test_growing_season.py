import pandas as pd

from src.feature_engineering.growing_season import (
    annotate_growing_season,
    select_growing_season,
)
# ================== Testing =======================================================================
def test_growing_season_assignment() -> None:
    test_weather = pd.DataFrame(
        {
            "year": [
                2019,
                2019,
                2019,
                2020,
                2020,
                2020,
            ],
            "month": [
                8,
                9,
                12,
                1,
                4,
                5,
            ],
        }
    )

    result = annotate_growing_season(test_weather)

    assert not result.loc[0, "is_growing_season"]
    assert pd.isna(result.loc[0, "harvest_year"])

    assert result.loc[1, "is_growing_season"]
    assert result.loc[1, "harvest_year"] == 2020

    assert result.loc[2, "harvest_year"] == 2020
    assert result.loc[3, "harvest_year"] == 2020
    assert result.loc[4, "harvest_year"] == 2020

    assert not result.loc[5, "is_growing_season"]
    assert pd.isna(result.loc[5, "harvest_year"])

    selected = select_growing_season(test_weather)

    assert len(selected) == 4
    assert selected["is_growing_season"].all()
    assert selected["harvest_year"].eq(2020).all()

    print("All growing-season tests passed.")


if __name__ == "__main__":
    test_growing_season_assignment()

# ================== Testing =======================================================================