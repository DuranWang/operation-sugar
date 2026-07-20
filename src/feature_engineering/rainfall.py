"""
Rainfall Features

This module implements rainfall-based feature engineering
methods used in Operation Sugar.

Features

- Total Rainfall
- Rainy Days
- Dry Days
- Maximum Consecutive Dry Days (CDD)
- Maximum Daily Rainfall

References

P01
P02
P03
P04
"""

import pandas as pd


def calculate_max_consecutive_dry_days(
    rainfall: pd.Series,
    dates: pd.Series,
    dry_day_threshold: float = 1.0,
) -> int:
    """
    Calculate the maximum number of consecutive dry days.

    A dry spell continues only when:

    1. rainfall is below the dry-day threshold; and
    2. the current observation occurs exactly one calendar day after
       the previous observation.

    Parameters
    ----------
    rainfall:
        Daily rainfall values.

    dates:
        Corresponding observation dates.

    dry_day_threshold:
        Rainfall threshold below which a day is classified as dry.

    Returns
    -------
    int
        Maximum number of consecutive dry days.
    """

    if len(rainfall) != len(dates):
        raise ValueError(
            "rainfall and dates must contain the same number of observations."
        )

    if rainfall.empty:
        return 0

    if rainfall.isna().any():
        raise ValueError("rainfall contains missing values.")

    weather = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "rainfall": rainfall.to_numpy(),
        }
    )

    if weather["date"].isna().any():
        raise ValueError("dates contains missing or invalid values.")

    weather = (
        weather
        .sort_values("date")
        .reset_index(drop=True)
    )

    is_dry_day = weather["rainfall"].lt(dry_day_threshold)

    # True only when the current date immediately follows the previous date.
    is_next_calendar_day = weather["date"].diff().eq(
        pd.Timedelta(days=1)
    )

    current_dry_spell = 0
    maximum_dry_spell = 0

    for row_number in range(len(weather)):
        if not is_dry_day.iloc[row_number]:
            # Rainfall at or above the threshold ends the dry spell.
            current_dry_spell = 0

        elif row_number == 0:
            # The first dry observation starts a new dry spell.
            current_dry_spell = 1

        elif is_next_calendar_day.iloc[row_number]:
            # Dry day immediately following another observation.
            current_dry_spell += 1

        else:
            # The day is dry, but there is a gap in the dates.
            # Therefore, start a new dry spell.
            current_dry_spell = 1

        maximum_dry_spell = max(
            maximum_dry_spell,
            current_dry_spell,
        )

    return maximum_dry_spell

