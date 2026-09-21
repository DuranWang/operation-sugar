"""Measure monthly weather correlation sensitivity to leaving out one season.

Run from the project root after analyze_feature_correlation:
    python -m src.analysis.analyze_correlation_stability

Each fold removes one complete season and recalculates both correlations.
Spearman ranks are recomputed within each retained sample by the shared
correlation function. There is no prediction, feature selection, or tuning.
Leave-one-out minima and maxima are sensitivity ranges, not confidence
intervals or evidence of future predictive performance.
"""

from itertools import combinations
import numpy as np
import pandas as pd

from src.analysis.analyze_feature_correlation import (
    OUTPUT_DIR as CORRELATION_OUTPUT_DIR,
    calculate_correlation_matrices,
)
from src.modeling.month_level_baseline_data import MONTH_LEVEL_FEATURES


INPUT_PATH = CORRELATION_OUTPUT_DIR / "season_weather_features.csv"
OUTPUT_DIR = CORRELATION_OUTPUT_DIR / "loso_stability"
METHODS = ("pearson", "spearman")

# Coefficients within this numerical tolerance of zero count as zero.
# This is not a statistical significance or feature-selection threshold.
SIGN_TOLERANCE = 1e-12


def _correlation_sign(value: float) -> int:
    """Return -1, 0, or 1, allowing for floating-point noise around zero."""

    if value > SIGN_TOLERANCE:
        return 1
    if value < -SIGN_TOLERANCE:
        return -1
    return 0


def _pair_group(feature_a: str, feature_b: str) -> str:
    """Label rainfall, temperature, and cross-variable feature pairs."""

    family_a = feature_a.split("_", maxsplit=1)[0]
    family_b = feature_b.split("_", maxsplit=1)[0]
    if family_a == family_b:
        return f"{family_a}_within"
    return "rainfall_temperature"


def analyze_correlation_stability(
    feature_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return fold-level results and one summary row per unique feature pair.

    Both methods appear in the long fold table and in separate prefixed
    columns of the wide summary. Only the upper triangle is used: neither
    self-correlations nor mirrored pairs are counted.

    At least four seasons are needed so each retained sample contains at
    least three. Invalid full samples or undefined fold correlations raise
    an error; failed folds are never silently dropped or filled with zero.

    Summary definitions (for each method):
    - full_correlation: recomputed from the complete input sample.
    - loo_min / loo_max / loo_range: observed leave-one-out range.
    - max_abs_change: largest absolute departure from full_correlation.
    - most_influential_seasons: excluded seasons achieving that departure,
      including ties within SIGN_TOLERANCE, separated by semicolons.
    - positive / negative / zero_fold_count: retained-sample sign counts.
    - sign_flip_count: strictly opposite signs relative to the full sample;
      zero counts as neither sign and never constitutes a sign flip.

    Use sign counts alongside coefficient magnitudes. A tiny correlation
    crossing zero does not have the same meaning as a large change.
    """

    # Reuse the existing one-row-per-season, finite-value and variance checks.
    full_matrices = calculate_correlation_matrices(feature_df)
    if len(feature_df) < 4:
        raise ValueError(
            "At least four seasons are required for leave-one-season-out "
            "correlation analysis."
        )

    sample = feature_df.sort_values("season").reset_index(drop=True)
    pairs = list(combinations(MONTH_LEVEL_FEATURES, 2))
    n_seasons = len(sample)
    records = []

    for row_index, excluded_season in enumerate(sample["season"]):
        retained = sample.drop(index=row_index)
        try:
            fold_matrices = calculate_correlation_matrices(retained)
        except ValueError as error:
            raise ValueError(
                f"Correlation fold excluding season {excluded_season!r} "
                f"is invalid: {error}"
            ) from error

        for method in METHODS:
            for feature_a, feature_b in pairs:
                full_r = float(full_matrices[method].loc[feature_a, feature_b])
                fold_r = float(fold_matrices[method].loc[feature_a, feature_b])
                full_sign = _correlation_sign(full_r)
                fold_sign = _correlation_sign(fold_r)
                records.append(
                    {
                        "method": method,
                        "feature_a": feature_a,
                        "feature_b": feature_b,
                        "pair_group": _pair_group(feature_a, feature_b),
                        "excluded_season": excluded_season,
                        "retained_season_count": n_seasons - 1,
                        "full_correlation": full_r,
                        "loo_correlation": fold_r,
                        "change_from_full": fold_r - full_r,
                        "abs_change_from_full": abs(fold_r - full_r),
                        "loo_sign": fold_sign,
                        "sign_flip": full_sign * fold_sign == -1,
                    }
                )

    fold_results = pd.DataFrame.from_records(records)
    grouped = fold_results.groupby(["method", "feature_a", "feature_b"])
    summary_records = []

    for feature_a, feature_b in pairs:
        summary = {
            "feature_a": feature_a,
            "feature_b": feature_b,
            "pair_group": _pair_group(feature_a, feature_b),
            "n_seasons": n_seasons,
            "n_loo_folds": n_seasons,
        }
        for method in METHODS:
            rows = grouped.get_group((method, feature_a, feature_b))
            correlations = rows["loo_correlation"]
            max_change = float(rows["abs_change_from_full"].max())
            influential = rows.loc[
                np.isclose(
                    rows["abs_change_from_full"],
                    max_change,
                    rtol=0,
                    atol=SIGN_TOLERANCE,
                ),
                "excluded_season",
            ].astype(str)
            metrics = {
                "full_correlation": float(rows["full_correlation"].iloc[0]),
                "loo_min": float(correlations.min()),
                "loo_max": float(correlations.max()),
                "loo_range": float(correlations.max() - correlations.min()),
                "max_abs_change": max_change,
                "most_influential_seasons": ";".join(influential),
                "positive_fold_count": int(rows["loo_sign"].eq(1).sum()),
                "negative_fold_count": int(rows["loo_sign"].eq(-1).sum()),
                "zero_fold_count": int(rows["loo_sign"].eq(0).sum()),
                "sign_flip_count": int(rows["sign_flip"].sum()),
                "any_sign_flip": bool(rows["sign_flip"].any()),
            }
            summary.update(
                {f"{method}_{name}": value for name, value in metrics.items()}
            )
        summary_records.append(summary)

    return fold_results, pd.DataFrame.from_records(summary_records)


def main() -> None:
    """Read the existing feature table, calculate all folds, and save results."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Feature table not found: {INPUT_PATH}. "
            "Run python -m src.analysis.analyze_feature_correlation first."
        )
    feature_df = pd.read_csv(INPUT_PATH, dtype={"season": str})
    fold_results, summary = analyze_correlation_stability(feature_df)

    # Compute and validate all folds before creating or replacing output files.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fold_results.to_csv(OUTPUT_DIR / "correlation_loso_folds.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "correlation_loso_summary.csv", index=False)

    print("=" * 72)
    print("Month-Level Weather Correlation Stability")
    print("=" * 72)
    print(f"Input: {INPUT_PATH}")
    print(f"Seasons: {len(feature_df)}")
    print("Included seasons: " + ", ".join(sorted(feature_df["season"])))
    print(f"Weather features: {len(MONTH_LEVEL_FEATURES)}")
    print(f"Unique feature pairs: {len(summary)}")
    print(f"LOSO folds per method: {len(feature_df)}")
    print(f"Retained seasons per fold: {len(feature_df) - 1}")
    for method in METHODS:
        count = int(summary[f"{method}_any_sign_flip"].sum())
        print(f"{method.capitalize()} pairs with a sign flip: {count}/{len(summary)}")
    print(f"[OK] Fold-level results: {len(fold_results)} rows")
    print(f"[OK] Pair summary: {len(summary)} rows")
    print(f"Output directory: {OUTPUT_DIR}")
    print("LOSO ranges are sensitivity ranges, not confidence intervals.")
    print("=" * 72)


if __name__ == "__main__":
    main()
