# EXP-01S Execution Report

## Definition and scope

EXP-01S analyzes the observed-only normalized / reported harvested-area share:

`w_obs(i,t) = A(i,t) / sum(A(j,t) for j in O_t)`

`O_t` includes reported numeric harvested area and explicit zero (`-`). Source
`...` remains unavailable (`NaN`) and is never imputed as zero. The results do
not estimate the unobserved true São Paulo harvested-area distribution.

TV and related metrics describe changes in the **reported municipality
harvested-area share distribution**, not literal physical redistribution of
hectares.

For TV only, each annual reported-share distribution is embedded on the union
of the two years' reported supports with probability mass zero outside its own
support. This is a mathematical representation of `w_obs`, not an assignment
of zero harvested area to a source `...` cell. Spearman uses only
municipalities reported in both compared years.

## Missingness materiality gate

- Gate: **passed**
- 127 municipalities contain at least one `...`.
- Four ever enter an annual Top-50: Guatapará, Tarumã, Motuca, and Santo Antônio
  do Aracanguá.
- All four contain `...` only in 1990–1992, and official IBGE histories record
  installation on 1993-01-01. Their high-share missingness is therefore
  explained by administrative availability.
- No municipality with unresolved `...` ever enters an annual Top-50.
- No affected municipality ever enters the annual Top-10; only Guatapará enters
  the annual Top-25.

## Validation

- 642 municipality rows in every year, 1990–2025.
- `(ibge_code, year)` duplicates: 0.
- Reconstructed `w_obs` sums to one within `1e-12` every year.
- Stored numeric `area_weight` matches reconstructed `w_obs` within `1e-12`.
- 1998 and 2006 remain in the primary analysis. The separately queried IBGE
  state total differs from the municipality sum by -200 ha (-0.0078%) and
  -2,372 ha (-0.0679%), respectively.

## Adjacent-year reported-share stability

- Total variation: mean 0.0612, median 0.0621, SD 0.0243, min 0.0233, max 0.1241.
- Spearman among municipalities reported in both adjacent years:
  mean 0.9680, median 0.9713, SD 0.0199, min 0.9229, max 0.9958.

Largest TV changes:

- 1992–1993: 0.1241
- 2007–2008: 0.1001
- 1993–1994: 0.0995
- 2006–2007: 0.0929
- 1995–1996: 0.0920

The largest value, 1992–1993, coincides with the installation of multiple new
municipalities on 1993-01-01. It therefore includes a change in reported
municipality support and must not be interpreted as literal physical movement
of harvested hectares. Anchor comparisons involving 1990 carry the same
administrative-boundary caveat.

Lowest adjacent-year rank correlations:

- 2001–2002: 0.9229
- 2000–2001: 0.9287
- 2008–2009: 0.9410
- 2006–2007: 0.9427
- 2009–2010: 0.9442

## Concentration and membership stability

- Mean Top-10 reported share: 13.6096%.
- Mean Top-25 reported share: 26.5182%.
- Mean Top-50 reported share: 41.9719%.
- Mean adjacent Top-10 overlap: 84.00%.
- Mean adjacent Top-25 overlap: 89.14%.
- Mean adjacent Top-50 overlap: 90.00%.

Municipalities with the largest mean reported shares:

- Morro Agudo: 2.2869%
- Piracicaba: 1.3747%
- Jaboticabal: 1.3029%
- Lençóis Paulista: 1.1672%
- Jaú: 1.1559%
- Paraguaçu Paulista: 1.1176%
- Ribeirão Preto: 1.0774%
- Araraquara: 1.0512%
- Guaíra: 1.0360%
- Pederneiras: 0.9553%

Largest municipality-level adjacent observed-share changes:

- Assis: maximum adjacent observed-share change 0.0137; mean adjacent change 0.0007
- Morro Agudo: maximum adjacent observed-share change 0.0118; mean adjacent change 0.0022
- Pederneiras: maximum adjacent observed-share change 0.0110; mean adjacent change 0.0015
- Ribeirão Preto: maximum adjacent observed-share change 0.0096; mean adjacent change 0.0011
- Pontal: maximum adjacent observed-share change 0.0083; mean adjacent change 0.0007

## Anchor-year comparison

- 1990–2000: TV 0.2435; Spearman 0.8313; Top-10/25/50 overlap 0.60/0.68/0.68
- 2000–2010: TV 0.2789; Spearman 0.7826; Top-10/25/50 overlap 0.40/0.64/0.66
- 2010–2020: TV 0.1231; Spearman 0.9396; Top-10/25/50 overlap 0.70/0.72/0.84
- 2020–2025: TV 0.0722; Spearman 0.9770; Top-10/25/50 overlap 0.70/0.72/0.96
- 1990–2025: TV 0.4578; Spearman 0.6479; Top-10/25/50 overlap 0.10/0.28/0.48

## 1998/2006 sensitivity

The sensitivity excludes adjacent pairs touching 1998 or 2006, leaving 31 of
35 adjacent comparisons. Mean results are:

- total_variation_reported_share: 0.0612 primary; 0.0596 excluding affected pairs; difference -0.0016
- spearman_common_reported: 0.9680 primary; 0.9683 excluding affected pairs; difference +0.0003
- top_10_membership_overlap: 0.8400 primary; 0.8419 excluding affected pairs; difference +0.0019
- top_25_membership_overlap: 0.8914 primary; 0.8916 excluding affected pairs; difference +0.0002
- top_50_membership_overlap: 0.9000 primary; 0.9032 excluding affected pairs; difference +0.0032

The exclusion does not reverse the descriptive finding: rank correlations and
Top-K overlaps remain high relative to the size of exact-share changes. The
full numerical sensitivity table is retained for review rather than imposing a
stable/unstable cutoff.

## Answers returned to Chat

1. Missing values have mixed semantics: `-` is explicit zero; `...` is
   unavailable. `w_obs` is normalized only over `O_t`.
2. Typical one-year change is summarized by the TV mean and median above.
3. The five largest-TV year pairs are listed above.
4. Rank stability is generally higher than exact-share stability, but zero
   ties and changing reported support remain limitations.
5. Top-producer concentration and membership are reported in the annual table.
6. Anchor comparisons show how cumulative differences exceed many adjacent
   changes; 1990–2025 results are in the anchor table.
7. The evidence supports testing fixed, lagged, and rolling weights later; it
   does not select one for EXP-01B.
8. Data-quality warnings remain: unavailable values, administrative availability,
   and small 1998/2006 state-versus-municipality reconciliation differences.

## Files and commands

Tables and figures are under this output directory. The analysis was run from
the repository's `data/processed/sp_sugarcane_annual.csv` and
`data/raw/tabela5457.xlsx`. No source downloader or existing ETL was changed.

Created or refreshed:

- `EXP_01S_execution_report.md`
- `EXP_01S_missingness_materiality_gate.md`
- 13 analysis and validation CSV tables under `tables/`
- `figures/annual_total_variation.png`
- `figures/annual_rank_stability.png`
- `figures/top_k_concentration.png`
- `figures/municipality_weight_heatmap.png`

Commands run:

- `python -m pytest -q -p no:cacheprovider work/exp01s_impl/src/tests/analysis`
- `python -m src.analysis.exp01s_observed_weight_stability --project-root <repo> --output <output>`
- Existing repository ETL validator test module.

Test results:

- EXP-01S analysis tests: 16 passed.
- Existing repository ETL validator tests: 9 passed.
