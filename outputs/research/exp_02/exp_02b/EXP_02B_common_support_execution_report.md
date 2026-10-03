# EXP-02B Common-Support Audit Execution Report

## Status

**COMMON-SUPPORT REFERENCE-WEIGHT AUDIT COMPLETED; STOPPED BEFORE THE RESIDUAL EXPERIMENT.**

## Created outputs

- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\common_support_reference_weights.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\common_support_grid_audit.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\common_support_distribution.csv`
- `D:\Desktop\Operation Sugar\outputs\research\exp_02\exp_02b\EXP_02B_common_support_reference_audit.md`

## Boundaries honored

- No actual-vs-fixed residual calculation was run.
- No support exclusion rule was selected.
- No weather result was used.
- No EXP-03 or EXP-04 work was started.

## Command and tests

- Command: `py -3 -m analysis.exp02b_composition_sensitivity --stage common-support-audit --project-root <repository>` with `PYTHONPATH=src`.
- Focused common-support tests plus relevant EXP-02A and source-semantics regressions: **46 passed**.
- Python compilation check passed.
