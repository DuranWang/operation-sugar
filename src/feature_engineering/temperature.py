"""
Temperature Features

This module implements reusable temperature-based feature
engineering methods used in Operation Sugar.

Features
--------
- Average Temperature

The same calculation can be applied to different biological
windows, including the growing season and maturation window.

References
----------
P01
P06
"""

import pandas as pd


def calculate_average_temperature(
    temperature: pd.Series,
) -> float:
    """
    Calculate the arithmetic mean of daily temperature observations.

    Parameters
    ----------
    temperature:
        Daily mean temperature observations in degrees Celsius.

    Returns
    -------
    float
        Average daily temperature.

        Returns NaN when the input Series is empty.

    Raises
    ------
    ValueError
        If the temperature Series contains missing values.
    """

    if temperature.empty:
        return float("nan")

    if temperature.isna().any():
        raise ValueError(
            "temperature contains missing values."
        )

    return float(temperature.mean())

