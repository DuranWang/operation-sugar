# EXP-03 March soil-moisture depth and spatial-regime analysis

## Scope

This report reproduces the completed Step 4A/4B descriptive analysis from existing grid-specific March correlations. It does not refit EXP-03, use SoilGrids, or infer causality.

## Frozen regime reconstruction

- Usable grids: **76** under the existing minimum of **15 paired years**.
- Surface definition: March 0–7 cm grid-specific Spearman rho.
- Deep definition: arithmetic mean of March 28–100 and 100–255 cm grid-specific Spearman rho.
- Regime counts reconstructed from the correlations: **42 positive-positive, 19 depth-recovery, 13 persistent-negative, and 2 reverse**.

## Depth relationships

| regime | relationship | n_grids | mean_rho | median_rho | q25_rho | q75_rho | minimum_rho | maximum_rho | pct_positive | pct_negative |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth_recovery | deep_100_255_rho | 19 | 0.1321 | 0.1377 | 0.0618 | 0.1898 | -0.0261 | 0.2885 | 0.8947 | 0.1053 |
| depth_recovery | deep_28_100_rho | 19 | 0.0199 | 0.0344 | -0.0369 | 0.0848 | -0.1913 | 0.1354 | 0.6842 | 0.3158 |
| depth_recovery | deep_rho | 19 | 0.0760 | 0.0717 | 0.0429 | 0.0976 | 0.0222 | 0.1593 | 1.0000 | 0.0000 |
| depth_recovery | surface_0_7_rho | 19 | -0.0783 | -0.0929 | -0.1217 | -0.0349 | -0.1621 | -0.0065 | 0.0000 | 1.0000 |
| depth_recovery | upper_7_28_rho | 19 | -0.0535 | -0.0517 | -0.1085 | -0.0055 | -0.1456 | 0.0383 | 0.2105 | 0.7895 |
| persistent_negative | deep_100_255_rho | 13 | -0.0665 | -0.0919 | -0.1360 | -0.0077 | -0.1824 | 0.1032 | 0.2308 | 0.7692 |
| persistent_negative | deep_28_100_rho | 13 | -0.0975 | -0.0720 | -0.1031 | -0.0493 | -0.2933 | 0.0548 | 0.1538 | 0.8462 |
| persistent_negative | deep_rho | 13 | -0.0820 | -0.0853 | -0.1098 | -0.0561 | -0.1335 | -0.0057 | 0.0000 | 1.0000 |
| persistent_negative | surface_0_7_rho | 13 | -0.1258 | -0.1190 | -0.1982 | -0.0186 | -0.3132 | -0.0041 | 0.0000 | 1.0000 |
| persistent_negative | upper_7_28_rho | 13 | -0.1245 | -0.1384 | -0.1691 | -0.0488 | -0.3831 | 0.0322 | 0.0769 | 0.9231 |
| positive_positive | deep_100_255_rho | 42 | 0.1089 | 0.0897 | 0.0265 | 0.1853 | -0.0874 | 0.3450 | 0.8571 | 0.1429 |
| positive_positive | deep_28_100_rho | 42 | 0.1629 | 0.1617 | 0.1087 | 0.2350 | -0.0479 | 0.3631 | 0.9048 | 0.0952 |
| positive_positive | deep_rho | 42 | 0.1359 | 0.1290 | 0.0506 | 0.2077 | 0.0068 | 0.3381 | 1.0000 | 0.0000 |
| positive_positive | surface_0_7_rho | 42 | 0.1509 | 0.1255 | 0.0847 | 0.1797 | 0.0220 | 0.4556 | 1.0000 | 0.0000 |
| positive_positive | upper_7_28_rho | 42 | 0.1597 | 0.1353 | 0.0955 | 0.1978 | 0.0237 | 0.4347 | 1.0000 | 0.0000 |
| reverse | deep_100_255_rho | 2 | -0.0318 | -0.0318 | -0.0562 | -0.0074 | -0.0806 | 0.0171 | 0.5000 | 0.5000 |
| reverse | deep_28_100_rho | 2 | -0.0820 | -0.0820 | -0.1391 | -0.0248 | -0.1962 | 0.0323 | 0.5000 | 0.5000 |
| reverse | deep_rho | 2 | -0.0569 | -0.0569 | -0.0732 | -0.0405 | -0.0896 | -0.0242 | 0.0000 | 1.0000 |
| reverse | surface_0_7_rho | 2 | 0.1311 | 0.1311 | 0.1286 | 0.1337 | 0.1260 | 0.1363 | 1.0000 | 0.0000 |
| reverse | upper_7_28_rho | 2 | 0.0853 | 0.0853 | 0.0617 | 0.1088 | 0.0382 | 0.1323 | 1.0000 | 0.0000 |

## Geography

| regime | n_grids | latitude_mean | latitude_median | latitude_q25 | latitude_q75 | longitude_mean | longitude_median | longitude_q25 | longitude_q75 | municipality_count_mean | municipality_count_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth_recovery | 19 | -21.5263 | -21.5000 | -22.2500 | -21.0000 | -49.5789 | -49.5000 | -50.5000 | -48.5000 | 8.3684 | 8.0000 |
| persistent_negative | 13 | -23.1154 | -23.0000 | -23.5000 | -23.0000 | -48.0000 | -48.5000 | -49.0000 | -47.0000 | 4.4615 | 4.0000 |
| positive_positive | 42 | -21.9167 | -22.0000 | -22.5000 | -21.0000 | -48.8810 | -49.0000 | -50.0000 | -47.5000 | 6.7143 | 7.0000 |
| reverse | 2 | -22.7500 | -22.7500 | -23.1250 | -22.3750 | -47.2500 | -47.2500 | -47.3750 | -47.1250 | 5.0000 | 5.0000 |

## March rainfall correspondence

| regime | n_grids | paired_years_min | paired_years_median | rainfall_rho_mean | rainfall_rho_median | rainfall_rho_q25 | rainfall_rho_q75 | pct_rainfall_positive | pct_rainfall_negative |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth_recovery | 19 | 44 | 44.0000 | -0.0257 | -0.0444 | -0.1047 | 0.0171 | 0.3158 | 0.6842 |
| persistent_negative | 13 | 25 | 44.0000 | -0.0425 | -0.0273 | -0.0730 | 0.0168 | 0.3846 | 0.6154 |
| positive_positive | 42 | 22 | 44.0000 | 0.1086 | 0.1221 | 0.0271 | 0.2064 | 0.7619 | 0.2381 |
| reverse | 2 | 44 | 44.0000 | 0.1172 | 0.1172 | 0.1168 | 0.1176 | 1.0000 | 0.0000 |

## Existing production support

| regime | n_grids | municipality_count_mean | municipality_count_median | valid_grid_years_min | valid_grid_years_median | paired_years_min | paired_years_median | harvested_area_mean_ha | harvested_area_median_ha | hhi_mean | hhi_median | dominant_share_mean | dominant_share_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth_recovery | 19 | 8.3684 | 8.0000 | 46 | 52.0000 | 44 | 44.0000 | 67333.8463 | 60507.6154 | 0.3268 | 0.2874 | 0.3640 | 0.3714 |
| persistent_negative | 13 | 4.4615 | 4.0000 | 27 | 52.0000 | 25 | 44.0000 | 17997.5443 | 5707.6538 | 0.6165 | 0.6320 | 0.6002 | 0.5619 |
| positive_positive | 42 | 6.7143 | 7.0000 | 22 | 52.0000 | 22 | 44.0000 | 37461.2753 | 29716.4519 | 0.4222 | 0.3906 | 0.4224 | 0.3643 |
| reverse | 2 | 5.0000 | 5.0000 | 52 | 52.0000 | 44 | 44.0000 | 29519.3846 | 29519.3846 | 0.5425 | 0.5425 | 0.5194 | 0.5194 |

## Interpretation boundary

The regime split is spatially structured and differs in municipality composition and production support. March rainfall correspondence overlaps the soil-moisture regimes only partially. These are descriptive competing explanations; none establishes a causal mechanism.
