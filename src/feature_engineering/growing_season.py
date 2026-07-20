"""
Growing Season

Definition
----------
The growing season refers to the period from crop
establishment (plant cane) or ratoon regrowth after
harvest through tillering and stalk growth,
ending before the maturation phase begins.

Biological Purpose
------------------
This period represents the primary phase of
vegetative development and biomass accumulation.

Operation Sugar Assumption
--------------------------
For the purpose of Operation Sugar v1.0,
the growing season in São Paulo is approximated
as September through April.

References
----------
P05
P06
"""

import pandas as pd
from pathlib import Path

SAO_PAULO_GROWING_SEASON_START_MONTH = 9
SAO_PAULO_GROWING_SEASON_END_MONTH = 4



def annotate_growing_season(
    weather_df: pd.DataFrame,
    start_month: int = SAO_PAULO_GROWING_SEASON_START_MONTH,
    end_month: int = SAO_PAULO_GROWING_SEASON_END_MONTH,
) -> pd.DataFrame:
    
    """
    Identify growing-season observations and assign a harvest year.

    The São Paulo growing season crosses the calendar-year boundary,
    beginning in September and ending in April of the following year.

    Parameters
    ----------
    weather_df:
        Daily weather observations containing `year` and `month`
        columns.

    start_month:
        First month of the growing season.

    end_month:
        Final month of the growing season.

    Returns
    -------
    pd.DataFrame
        Copy of the input DataFrame with two additional columns:

        - `is_growing_season`
        - `harvest_year`

        Observations outside the growing season receive a missing
        value for `harvest_year`.
    """

    required_columns = {"year", "month"}
    missing_columns = required_columns - set(weather_df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if not 1 <= start_month <= 12:
        raise ValueError("start_month must be between 1 and 12.")

    if not 1 <= end_month <= 12:
        raise ValueError("end_month must be between 1 and 12.")
    
    if start_month <= end_month:
        raise ValueError(
            "Growing season must cross the calendar-year boundary "
            "(start_month > end_month)."
        )

    result = weather_df.copy()

    # The São Paulo window crosses the calendar-year boundary:
    # September through December, followed by January through April.
    result["is_growing_season"] = (
        result["month"].ge(start_month)
        | result["month"].le(end_month)
    )

    # September–December belong to the following harvest year.
    # January–April belong to the current calendar year.
    result["harvest_year"] = pd.NA

    # September–December belong to the following harvest year.
    start_year_mask = (
        result["is_growing_season"]
        & result["month"].ge(start_month)
    )

    # January–April belong to the current harvest year.
    end_year_mask = (
        result["is_growing_season"]
        & result["month"].le(end_month)
    )

    result.loc[start_year_mask, "harvest_year"] = (
        result.loc[start_year_mask, "year"] + 1
    )

    result.loc[end_year_mask, "harvest_year"] = (
        result.loc[end_year_mask, "year"]
    )

    result["harvest_year"] = result["harvest_year"].astype("Int64")

    return result


def select_growing_season(
    weather_df: pd.DataFrame,
    start_month: int = SAO_PAULO_GROWING_SEASON_START_MONTH,
    end_month: int = SAO_PAULO_GROWING_SEASON_END_MONTH,
) -> pd.DataFrame:
    
    """
    Return only observations that fall within the growing season.

    Parameters
    ----------
    weather_df:
        Daily weather observations containing `year` and `month`
        columns.

    start_month:
        First month of the growing season.

    end_month:
        Final month of the growing season.

    Returns
    -------
    pd.DataFrame
        Growing-season observations with an annotateed `harvest_year`.
    """

    result = annotate_growing_season(
        weather_df=weather_df,
        start_month=start_month,
        end_month=end_month,
    )

    return (
        result.loc[result["is_growing_season"]]
        .copy()
        .reset_index(drop=True)
    )


