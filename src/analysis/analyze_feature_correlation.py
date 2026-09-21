"""Analyze monthly weather correlations across shared historical seasons.

Run from the project root:
    python -m src.analysis.analyze_feature_correlation

Reuse the baseline loaders and restrict weather to seasons present in the
complete harvest sample. Each season contributes exactly one observation.
These are descriptive correlations, not supervised feature selection.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.modeling.aggregate_baseline_data import (
    HARVEST_INPUT_PATH,
    WEATHER_INPUT_PATH,
    build_base_harvest_periods,
)
from src.modeling.month_level_baseline_data import (
    MONTH_LEVEL_FEATURES,
    load_month_level_weather_predictors,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analysis"
    / "feature_correlation"
)


def build_season_feature_table(
    weather_df: pd.DataFrame,
    base_period_df: pd.DataFrame,
) -> pd.DataFrame:
    """Select one weather row per season shared with the harvest sample.

    Inputs should come from the existing baseline loaders. No harvest-block
    rows, aggregate controls, or target values enter the correlation table.
    """

    columns = ["season", *MONTH_LEVEL_FEATURES]
    missing_columns = set(columns) - set(weather_df.columns)
    if missing_columns:
        raise ValueError(
            f"Weather data is missing columns: {sorted(missing_columns)}"
        )
    if "season" not in base_period_df.columns:
        raise ValueError("Harvest data is missing the season column.")
    if weather_df["season"].isna().any():
        raise ValueError("Weather data contains missing season identifiers.")
    if base_period_df["season"].isna().any():
        raise ValueError("Harvest data contains missing season identifiers.")
    if weather_df["season"].duplicated().any():
        raise ValueError("Weather data must contain only one row per season.")

    feature_df = weather_df.loc[
        weather_df["season"].isin(base_period_df["season"]),
        columns,
    ].copy()

    if feature_df.empty:
        raise ValueError("No overlapping weather and harvest seasons.")

    return feature_df.sort_values("season").reset_index(drop=True)


def calculate_correlation_matrices(
    feature_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Compute Pearson and Spearman matrices using the same complete rows.

    Spearman is Pearson correlation of average ranks (including ties).
    Reject missing, infinite, and constant features instead of silently
    using different samples for different pairs or emitting undefined cells.
    """

    required_columns = {"season", *MONTH_LEVEL_FEATURES}
    missing_columns = required_columns - set(feature_df.columns)
    if missing_columns:
        raise ValueError(
            f"Feature table is missing columns: {sorted(missing_columns)}"
        )
    if feature_df["season"].isna().any():
        raise ValueError("Feature table contains missing season identifiers.")
    if feature_df["season"].duplicated().any():
        raise ValueError("Correlation input must contain one row per season.")
    if len(feature_df) < 3:
        raise ValueError("At least three shared seasons are required.")

    values = feature_df[list(MONTH_LEVEL_FEATURES)].apply(
        pd.to_numeric,
        errors="raise",
    )
    finite_columns = np.isfinite(values.to_numpy(dtype=float)).all(axis=0)
    if not finite_columns.all():
        invalid_columns = values.columns[~finite_columns].tolist()
        raise ValueError(
            "Weather features contain missing or infinite values: "
            f"{invalid_columns}"
        )
    constant_columns = values.columns[values.nunique().le(1)].tolist()
    if constant_columns:
        raise ValueError(
            f"Correlation is undefined for constant features: {constant_columns}"
        )

    matrices = {
        "pearson": values.corr(method="pearson"),
        "spearman": values.rank(method="average").corr(method="pearson"),
    }
    for method, matrix in matrices.items():
        if not np.isfinite(matrix.to_numpy()).all():
            raise ValueError(f"The {method} matrix contains undefined values.")
        matrix.index.name = "feature"
        matrix.columns.name = "feature"

    return matrices


def main() -> None:
    """Build and save the season-level sample and both correlation matrices."""

    weather_df = load_month_level_weather_predictors(WEATHER_INPUT_PATH)
    base_period_df = build_base_harvest_periods(HARVEST_INPUT_PATH)
    feature_df = build_season_feature_table(weather_df, base_period_df)
    matrices = calculate_correlation_matrices(feature_df)

    # Validate and calculate everything before writing any output.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    feature_df.to_csv(OUTPUT_DIR / "season_weather_features.csv", index=False)
    feature_df[["season"]].to_csv(
        OUTPUT_DIR / "included_seasons.csv",
        index=False,
    )
    for method, matrix in matrices.items():
        matrix.to_csv(OUTPUT_DIR / f"{method}_correlation.csv")

    weather_seasons = set(weather_df["season"])
    harvest_seasons = set(base_period_df["season"])
    weather_only = sorted(weather_seasons - harvest_seasons)
    harvest_only = sorted(harvest_seasons - weather_seasons)

    print("=" * 72)
    print("Month-Level Weather Feature Correlation")
    print("=" * 72)
    print(f"Complete weather seasons: {len(weather_seasons)}")
    print(f"Complete harvest seasons: {len(harvest_seasons)}")
    print(f"Shared seasons used: {len(feature_df)}")
    print(f"Weather-only seasons excluded: {weather_only}")
    print(f"Harvest-only seasons excluded: {harvest_only}")
    print("Included seasons: " + ", ".join(feature_df["season"].astype(str)))
    print(
        f"[OK] Feature table: {len(feature_df)} seasons x "
        f"{len(MONTH_LEVEL_FEATURES)} weather features"
    )
    for method, matrix in matrices.items():
        print(f"[OK] {method.capitalize()} matrix: {matrix.shape[0]} x {matrix.shape[1]}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()