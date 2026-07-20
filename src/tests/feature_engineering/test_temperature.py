import pandas as pd

from src.feature_engineering.temperature import (
    calculate_average_temperature,
)

# ======== Testing =============================================================================================
def test_calculate_average_temperature() -> None:
    test_cases = {
        "ordinary temperatures": (
            pd.Series([20.0, 22.0, 24.0]),
            22.0,
        ),
        "single observation": (
            pd.Series([25.0]),
            25.0,
        ),
        "decimal result": (
            pd.Series([20.0, 21.0]),
            20.5,
        ),
    }

    for name, (temperature, expected) in test_cases.items():
        actual = calculate_average_temperature(
            temperature=temperature,
        )

        assert actual == expected, (
            f"{name}: expected {expected}, got {actual}"
        )

    empty_result = calculate_average_temperature(
        temperature=pd.Series([], dtype=float),
    )

    assert pd.isna(empty_result)

    try:
        calculate_average_temperature(
            temperature=pd.Series([20.0, pd.NA, 24.0]),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "missing values: expected ValueError"
        )

    print("All temperature tests passed.")


if __name__ == "__main__":
    test_calculate_average_temperature()

# ======== Testing =============================================================================================