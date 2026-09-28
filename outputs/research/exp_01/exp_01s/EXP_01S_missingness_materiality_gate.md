# EXP-01S Missingness Materiality Gate

## Weight definition

The analysis weight is the observed-only normalized / reported harvested-area
share:

`w_obs(i,t) = A(i,t) / sum(A(j,t) for j in O_t)`

`O_t` contains source numeric values and explicit zero (`-`) observations.
Source `...` values remain unavailable (`NaN`) and are not imputed as zero.
This is not an estimate of the unobserved true São Paulo harvested-area
distribution.

## Gate result

- Status: **passed**
- Conservative materiality criterion: affected municipality ever enters an annual Top-50 and its unavailable years are not explained by official municipality installation evidence
- Affected municipalities: 127
- Affected municipalities meeting the criterion:
  4
- Material municipalities explained by official installation evidence:
  4
- Material municipalities with unresolved missingness:
  0
- Maximum observed share among affected municipalities:
  1.0625%
- Maximum annual combined observed share of the affected set:
  5.8975%

Highest observed shares among affected municipalities:

- Guatapará: max observed share 1.0625%; max observed area 25,391 ha; Top-50=True
- Tarumã: max observed share 0.7968%; max observed area 21,471 ha; Top-50=True
- Motuca: max observed share 0.7204%; max observed area 17,900 ha; Top-50=True
- Santo Antônio do Aracanguá: max observed share 0.6622%; max observed area 27,925 ha; Top-50=True
- Monte Mor: max observed share 0.4510%; max observed area 12,000 ha; Top-50=False
- Suzanápolis: max observed share 0.4374%; max observed area 20,912 ha; Top-50=False
- Ilha Solteira: max observed share 0.3717%; max observed area 20,500 ha; Top-50=False
- Gavião Peixoto: max observed share 0.2990%; max observed area 17,000 ha; Top-50=False
- Novais: max observed share 0.2893%; max observed area 10,600 ha; Top-50=False
- Borebi: max observed share 0.2761%; max observed area 6,796 ha; Top-50=False

## Decision

If the status is `blocked`, the main metrics are not computed or interpreted.
If it is `passed`, every historically Top-50 affected municipality has official
evidence that its only unavailable years predate municipal installation.
