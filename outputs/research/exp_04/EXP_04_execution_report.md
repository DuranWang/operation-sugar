# EXP-04 Execution Report

- Commit: `1a3f5a9fea60d064f2af84ba282f87fbc52be482`; existing unrelated untracked spatial audit and `update_v171_docs.py` were preserved.
- Inputs: frozen 38-item Step-5 universe; EXP-02B actual/fixed P50=10 and P50=12 targets and municipality actual-area weights; canonical 1981–2025 municipality monthly combined weather. Input SHA-256 values and alignment are in `config.json` and `input_manifest.json`.
- Lineage: 511 eligible municipalities, 78 grids, maximum target reconstruction error 1.2e-14 t/ha. No partial weather weight support among paired rows.
- Deterministic: 143,374 candidate-grid-year rows, 2,964 candidate-grid estimates, 2,888 L fits, 2,736 Q fits; 76 L rows below the gate. All 38 core pooled models PL/PQ/HL/HQ fit on their fixed Q rosters.
- Bootstrap: smoke 50 attempts per scheme, minimum pooled validity 100.0%; full 1000 attempts per scheme, minimum pooled validity 99.9%. Schemes are synchronized iid years, noncircular overlapping 3-year and 5-year moving blocks on the full calendar axis. Seeds, original rosters/scales/anchors and draw-count matrices are saved.
- Full bootstrap estimand rows with ≥1 invalid attempt: 6 of 19824; original roster never changes within a replicate. Pointwise percentile intervals with fewer than 800 valid draws are marked provisional.
- The six invalid-estimand records are the same single block-5 draw in pooled MA/MAD/MAD_HA for both Dec–Jan aggregate candidates; reason: `fixed_roster_grid_failure`. No roster was changed and the corresponding intervals use 999 valid attempts.
- Independent verification: direct regressions, A/D equivalence, synthetic quadratic contrasts, nonbridging calendar blocks and pooled cross-product equivalence are covered by focused tests; commands/results are recorded below.

## Commands and checks

- `PYTHONPATH=src python -m analysis.exp04_response_characterization --stage deterministic` — passed.
- `PYTHONPATH=src python -m analysis.exp04_bootstrap --stage smoke` — passed; 50 attempts per scheme, independent of full draws.
- `PYTHONPATH=src python -m analysis.exp04_bootstrap --stage full` — passed; 1,000 attempts per scheme.
- `PYTHONPATH=src python -m analysis.exp04_finalize` — passed.
- Focused pytest: `PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/analysis/test_exp04_response_characterization.py src/tests/analysis/test_exp02b_composition_sensitivity.py` — 17 passed. Output reconciliation checks applied.

## Files and limits

- New code: `src/analysis/exp04_response_characterization.py`, `src/analysis/exp04_bootstrap.py`, `src/analysis/exp04_finalize.py`; focused test: `src/tests/analysis/test_exp04_response_characterization.py`.
- Main outputs: 38-row candidate manifest/summary, support, grid and pooled estimates, A/D ladders, target comparisons, grid and pooled LOYO, smoke/full bootstrap diagnostics/intervals/calendar draw files, processed EXP-04 panel, and figure atlases under `figures/`.
- The sample threshold is only an operational identifiability screen. Pointwise intervals do not cover detrending uncertainty, source exposure error or the search across 38 candidates. No causal or out-of-sample inference is made.
