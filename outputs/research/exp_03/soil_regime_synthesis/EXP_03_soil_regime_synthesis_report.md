# EXP-03 bounded SoilGrids regime synthesis

## Scope

This report reproduces Step 4C-2 using the six native SoilGrids intervals through 200 cm. No 200-255 cm layer is created, and no static soil variable is added to a predictive model.

Primary comparison: 19 depth-recovery grids versus 13 persistent-negative grids. The 42 positive-positive grids provide reference context.

## Key profile contrasts

| scope | sample | soil_variable | depth_or_profile | n_depth_recovery | n_persistent_negative | n_positive_positive | median_depth_recovery | median_persistent_negative | median_positive_positive | median_difference_dr_minus_pn | cliffs_delta_dr_vs_pn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| profile | all_valid | awc_33_minus_1500 | deep_30_200 | 19 | 13 | 42 | 13.5681 | 12.3147 | 12.9494 | 1.2534 | 0.4980 |
| profile | all_valid | awc_33_minus_1500 | deep_minus_upper | 19 | 13 | 42 | -3.5165 | -6.0445 | -4.1084 | 2.5280 | 0.8300 |
| profile | all_valid | awc_33_minus_1500 | upper_0_30 | 19 | 13 | 42 | 17.6452 | 17.5274 | 17.0036 | 0.1178 | -0.1660 |
| profile | all_valid | bdod | deep_30_200 | 19 | 13 | 42 | 1.2929 | 1.1966 | 1.2494 | 0.0963 | 0.8219 |
| profile | all_valid | bdod | deep_minus_upper | 19 | 13 | 42 | -0.0260 | 0.0091 | -0.0272 | -0.0351 | -0.6194 |
| profile | all_valid | bdod | upper_0_30 | 19 | 13 | 42 | 1.3185 | 1.1870 | 1.2966 | 0.1316 | 0.8704 |
| profile | all_valid | cfvo | deep_30_200 | 19 | 13 | 42 | 6.8547 | 9.4245 | 7.6002 | -2.5698 | -0.7733 |
| profile | all_valid | cfvo | deep_minus_upper | 19 | 13 | 42 | 2.3342 | 2.4782 | 2.3808 | -0.1440 | -0.3036 |
| profile | all_valid | cfvo | upper_0_30 | 19 | 13 | 42 | 4.2661 | 6.9175 | 5.2319 | -2.6514 | -0.7490 |
| profile | all_valid | clay | deep_30_200 | 19 | 13 | 42 | 39.1549 | 44.0431 | 41.3697 | -4.8881 | -0.4737 |
| profile | all_valid | clay | deep_minus_upper | 19 | 13 | 42 | 6.9596 | 8.5312 | 6.8482 | -1.5716 | -0.3360 |
| profile | all_valid | clay | upper_0_30 | 19 | 13 | 42 | 33.0535 | 34.5776 | 34.3304 | -1.5241 | -0.2955 |
| profile | all_valid | sand | deep_30_200 | 19 | 13 | 42 | 45.3027 | 39.7602 | 42.7880 | 5.5424 | 0.5628 |
| profile | all_valid | sand | deep_minus_upper | 19 | 13 | 42 | -6.6401 | -7.3793 | -5.9405 | 0.7392 | 0.3360 |
| profile | all_valid | sand | upper_0_30 | 19 | 13 | 42 | 49.8354 | 46.3109 | 48.8732 | 3.5245 | 0.4251 |
| profile | all_valid | wv0033 | deep_30_200 | 19 | 13 | 42 | 31.1817 | 32.6475 | 31.5135 | -1.4658 | -0.6275 |
| profile | all_valid | wv0033 | deep_minus_upper | 19 | 13 | 42 | 0.3790 | -0.7678 | 0.1490 | 1.1468 | 0.7328 |
| profile | all_valid | wv0033 | upper_0_30 | 19 | 13 | 42 | 30.9040 | 33.3729 | 31.2342 | -2.4689 | -0.7652 |
| profile | all_valid | wv1500 | deep_30_200 | 19 | 13 | 42 | 17.6062 | 20.4341 | 18.8123 | -2.8279 | -0.7490 |
| profile | all_valid | wv1500 | deep_minus_upper | 19 | 13 | 42 | 3.9312 | 4.8179 | 4.3505 | -0.8867 | -0.7571 |
| profile | all_valid | wv1500 | upper_0_30 | 19 | 13 | 42 | 13.6575 | 15.3775 | 14.5199 | -1.7200 | -0.5628 |

## Latitude association

| soil_variable | profile_metric | n_grids | spearman_rho_with_latitude |
| --- | --- | --- | --- |
| awc_33_minus_1500 | upper_0_30 | 32 | -0.2835 |
| awc_33_minus_1500 | deep_30_200 | 32 | 0.3724 |
| awc_33_minus_1500 | deep_minus_upper | 32 | 0.8040 |
| bdod | upper_0_30 | 32 | 0.8853 |
| bdod | deep_30_200 | 32 | 0.7847 |
| bdod | deep_minus_upper | 32 | -0.5789 |
| cfvo | upper_0_30 | 32 | -0.7489 |
| cfvo | deep_30_200 | 32 | -0.7879 |
| cfvo | deep_minus_upper | 32 | -0.3399 |
| clay | upper_0_30 | 32 | -0.3041 |
| clay | deep_30_200 | 32 | -0.6456 |
| clay | deep_minus_upper | 32 | -0.7331 |
| sand | upper_0_30 | 32 | 0.5578 |
| sand | deep_30_200 | 32 | 0.7478 |
| sand | deep_minus_upper | 32 | 0.6936 |
| silt | upper_0_30 | 32 | -0.5877 |
| silt | deep_30_200 | 32 | -0.5611 |
| silt | deep_minus_upper | 32 | 0.5732 |
| wv0033 | upper_0_30 | 32 | -0.8089 |
| wv0033 | deep_30_200 | 32 | -0.7714 |
| wv0033 | deep_minus_upper | 32 | 0.6445 |
| wv1500 | upper_0_30 | 32 | -0.5571 |
| wv1500 | deep_30_200 | 32 | -0.7803 |
| wv1500 | deep_minus_upper | 32 | -0.8220 |

## Existing production-support context

| regime | n_grids | municipality_count_mean | municipality_count_median | valid_grid_years_min | valid_grid_years_median | paired_years_min | paired_years_median | harvested_area_mean_ha | harvested_area_median_ha | hhi_mean | hhi_median | dominant_share_mean | dominant_share_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth_recovery | 19 | 8.3684 | 8.0000 | 46 | 52.0000 | 44 | 44.0000 | 67333.8463 | 60507.6154 | 0.3268 | 0.2874 | 0.3640 | 0.3714 |
| persistent_negative | 13 | 4.4615 | 4.0000 | 27 | 52.0000 | 25 | 44.0000 | 17997.5443 | 5707.6538 | 0.6165 | 0.6320 | 0.6002 | 0.5619 |
| positive_positive | 42 | 6.7143 | 7.0000 | 22 | 52.0000 | 22 | 44.0000 | 37461.2753 | 29716.4519 | 0.4222 | 0.3906 | 0.4224 | 0.3643 |
| reverse | 2 | 5.0000 | 5.0000 | 52 | 52.0000 | 44 | 44.0000 | 29519.3846 | 29519.3846 | 0.5425 | 0.5425 | 0.5194 | 0.5194 |

## Reproduced interpretation

- Depth-recovery grids tend to be sandier and less clay-rich, especially at depth.
- Their modeled absolute theta33 and theta1500 values are generally lower.
- Upper-profile `awc_33_minus_1500` levels are similar, while the deep-minus-upper decline is less negative in depth-recovery grids.
- Bulk-density and coarse-fragment contrasts are strong descriptively but co-occur with the broader geographic soil pattern.
- The strongest soil summaries materially track latitude, while production-support structure also differs by regime.

**Classification: suggestive / partial explanatory evidence.** These static modeled soil properties provide context but do not establish an independent or causal explanation.
