# EXP-03 Checkpoint 2B — Spatial Heterogeneity Audit

## Scope and directional convention

This audit uses the completed Checkpoint 2 outputs, the approved EXP-02 P50=10 municipality residual support, the exact annual `actual_weight`, and the existing municipality bridge. Exact-zero grid correlations are excluded from both agreeing and disagreeing directional counts, matching Checkpoint 2's strict `rho > 0` / `rho < 0` convention. No canonical definition was changed.

## 1. The 11 problematic late-window cells

| relative_month | calendar_interpretation | weather_variable | pooled_within_grid_rank_rho | median_grid_specific_rho | n_grids_agreeing_with_pooled_direction | n_grids_disagreeing_with_pooled_direction | pct_grids_agreeing | primary_standardized_high_minus_low_effect |
|---|---|---|---|---|---|---|---|---|
| m_-2 | Feb_(t) | nasa_total_rainfall_mm | 0.0242 | -0.0114 | 36 | 40 | 0.4737 | 0.0486 |
| m_-1 | Mar_(t) | vpd_mean_kpa | -0.0132 | 0.0060 | 37 | 39 | 0.4868 | -0.0861 |
| m_-1 | Mar_(t) | vpd_mean_daily_max_kpa | -0.0232 | -0.0061 | 40 | 36 | 0.5263 | -0.0969 |
| m_-2 | Feb_(t) | nasa_average_temperature_c | -0.0200 | -0.0172 | 41 | 35 | 0.5395 | -0.1702 |
| m_-1 | Mar_(t) | solar_radiation_mean_daily_mj_m2 | -0.0198 | -0.0254 | 42 | 34 | 0.5526 | -0.0396 |
| m_-2 | Feb_(t) | solar_radiation_total_mj_m2 | -0.0362 | -0.0155 | 42 | 34 | 0.5526 | -0.0882 |
| m_-1 | Mar_(t) | solar_radiation_total_mj_m2 | -0.0198 | -0.0254 | 42 | 34 | 0.5526 | -0.0396 |
| m_-2 | Feb_(t) | solar_radiation_mean_daily_mj_m2 | -0.0349 | -0.0285 | 43 | 33 | 0.5658 | -0.0890 |
| m_-1 | Mar_(t) | soil_moisture_0_to_7cm_m3_m3 | 0.0456 | 0.0600 | 44 | 32 | 0.5789 | 0.1392 |
| m_-1 | Mar_(t) | nasa_total_rainfall_mm | 0.0491 | 0.0421 | 45 | 31 | 0.5921 | 0.0883 |
| m_-2 | Feb_(t) | vpd_mean_kpa | -0.0218 | -0.0343 | 45 | 31 | 0.5921 | -0.2382 |

By variable:

| weather_variable | problematic_cells | distinct_late_months | minimum_pct_grids_agreeing |
|---|---|---|---|
| nasa_total_rainfall_mm | 2 | 2 | 0.4737 |
| solar_radiation_mean_daily_mj_m2 | 2 | 2 | 0.5526 |
| solar_radiation_total_mj_m2 | 2 | 2 | 0.5526 |
| vpd_mean_kpa | 2 | 2 | 0.4868 |
| nasa_average_temperature_c | 1 | 1 | 0.5395 |
| soil_moisture_0_to_7cm_m3_m3 | 1 | 1 | 0.5789 |
| vpd_mean_daily_max_kpa | 1 | 1 | 0.5263 |

By month:

| relative_month_index | relative_month | calendar_interpretation | problematic_cells | distinct_variables | minimum_pct_grids_agreeing |
|---|---|---|---|---|---|
| -2 | m_-2 | Feb_(t) | 5 | 5 | 0.4737 |
| -1 | m_-1 | Mar_(t) | 6 | 6 | 0.4868 |

All 11 cells occur in February (`m_-2`) or March (`m_-1`). Solar radiation contributes four cells, rainfall and mean VPD two each, and temperature, maximum VPD, and surface soil moisture one each. Relative humidity and the three deeper soil-moisture layers contribute none. **5** of 11 cells touch the broader core-variable family, but the most stable humidity and deeper-moisture portion of the provisional story is unaffected.

## 2. Disagreeing ERA5 grids and concentration

There are **379** problematic-cell × disagreeing-grid occurrences across **70** distinct grids. **59** grids disagree in at least three problematic cells. The five most frequent grids account for **13.5%** of all disagreement occurrences.

Most frequent grids:

| era5_grid_id | problematic_cells_disagreed | distinct_variables_affected | distinct_late_months_affected | grid_latitude | grid_longitude | n_eligible_municipalities_in_grid | municipality_names |
|---|---|---|---|---|---|---|---|
| era5_-23.00_-47.00 | 11 | 7 | 2 | -23.0000 | -47.0000 | 8 | Campinas; Hortolândia; Indaiatuba; Itatiba; Itupeva; Jundiaí; Louveira; Paulínia |
| era5_-23.00_-49.00 | 10 | 7 | 2 | -23.0000 | -49.0000 | 5 | Arandu; Avaré; Cerqueira César; Iaras; Águas de Santa Bárbara |
| era5_-24.50_-48.50 | 10 | 7 | 2 | -24.5000 | -48.5000 | 1 | Iporanga |
| era5_-21.00_-49.00 | 10 | 6 | 2 | -21.0000 | -49.0000 | 16 | Ariranha; Cajobi; Catanduva; Catiguá; Elisiário; Embaúba; Guapiaçu; Ibirá; Novais; Palmares Paulista; Paraíso; Pindorama; Santa Adélia; Severínia; Tabapuã; Uchoa |
| era5_-22.50_-50.50 | 10 | 6 | 2 | -22.5000 | -50.5000 | 10 | Assis; Borá; Cruzália; Cândido Mota; Florínia; Lutécia; Maracaí; Paraguaçu Paulista; Pedrinhas Paulista; Tarumã |
| era5_-23.00_-46.50 | 10 | 6 | 2 | -23.0000 | -46.5000 | 8 | Atibaia; Bom Jesus dos Perdões; Bragança Paulista; Jarinu; Joanópolis; Nazaré Paulista; Pedra Bela; Piracaia |
| era5_-21.00_-48.00 | 9 | 7 | 2 | -21.0000 | -48.0000 | 8 | Barrinha; Dumont; Jardinópolis; Pitangueiras; Pontal; Ribeirão Preto; Sales Oliveira; Sertãozinho |
| era5_-21.50_-49.00 | 9 | 7 | 2 | -21.5000 | -49.0000 | 5 | Borborema; Itajobi; Itápolis; Marapoama; Novo Horizonte |
| era5_-22.50_-51.50 | 9 | 7 | 2 | -22.5000 | -51.5000 | 9 | Anhumas; Estrela do Norte; Iepê; Nantes; Narandiba; Pirapozinho; Sandovalina; Taciba; Tarabai |
| era5_-23.50_-49.00 | 9 | 7 | 2 | -23.5000 | -49.0000 | 2 | Itaí; Taquarituba |
| era5_-22.00_-50.50 | 9 | 6 | 2 | -22.0000 | -50.5000 | 7 | Arco-Íris; Bastos; Herculândia; Iacri; Quatá; Quintana; Tupã |
| era5_-22.00_-51.50 | 9 | 6 | 2 | -22.0000 | -51.5000 | 10 | Emilianópolis; Indiana; Piquerobi; Presidente Bernardes; Presidente Prudente; Regente Feijó; Ribeirão dos Índios; Santo Anastácio; Santo Expedito; Álvares Machado |

Coordinate-based geographic summary, derived from actual grid latitude/longitude rather than grid-ID text:

| coordinate_region | distinct_disagreeing_grids | disagreement_occurrences | distinct_variables | distinct_late_months | minimum_latitude | maximum_latitude | minimum_longitude | maximum_longitude |
|---|---|---|---|---|---|---|---|---|
| south-east | 24 | 140 | 7 | 2 | -24.5000 | -22.5000 | -49.0000 | -45.0000 |
| north-east | 19 | 108 | 7 | 2 | -22.0000 | -20.0000 | -49.0000 | -47.0000 |
| north-west | 18 | 89 | 7 | 2 | -22.0000 | -20.0000 | -52.0000 | -49.5000 |
| south-west | 9 | 42 | 7 | 2 | -23.5000 | -22.5000 | -53.0000 | -49.5000 |

The disagreements are distributed across multiple coordinate regions and many grids, while some grids recur across several variables. This is better described as broad regional/grid heterogeneity with recurring local contributors than as noise from only one or two statewide outliers.

## 3. Municipality composition and influence

The composition table contains **2501** problematic-cell × disagreeing-grid × eligible-municipality rows. It records zero for years when an eligible municipality is absent from matched residual support, so mean/median weight describe influence over the full valid grid-year history.

Leave-one-municipality-out reconstruction is scientifically valid here because both the P50=10 grid residual and grid weather are linear aggregates over the stored municipality-year support using the same `actual_weight`. For each removal, both outcome and weather are recomputed and remaining weights are renormalized. A result is reported only when every original paired year remains valid.

- LOO rows: **2501**.
- Same-year support not preserved: **171** rows; these are explicitly non-estimable.
- Descriptive `high_influence` rows: **380**.
- These flags involve **154** municipalities across **54** grids, so influence is not confined to one municipality or one region.
- The flag is triggered by a sign flip, `|delta rho| >= 0.10`, or movement toward the pooled direction of at least 0.10. This is a transparent diagnostic threshold, not a formal statistical classification.

Largest flagged changes:

| relative_month | weather_variable | era5_grid_id | municipality_removed | original_grid_rho | leave_one_out_rho | delta_rho | sign_flips | movement_toward_pooled_direction | mean_weight_all_grid_years | share_years_largest_weight | high_influence_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| m_-1 | nasa_total_rainfall_mm | era5_-22.00_-50.50 | Quatá | -0.1425 | 0.2734 | 0.4159 | True | 0.4159 | 0.7087 | 1.0000 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | nasa_total_rainfall_mm | era5_-23.00_-46.50 | Jarinu | -0.2218 | 0.1512 | 0.3731 | True | 0.3731 | 0.2860 | 0.4808 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-1 | soil_moisture_0_to_7cm_m3_m3 | era5_-22.00_-50.50 | Quatá | -0.1271 | 0.1925 | 0.3197 | True | 0.3197 | 0.7087 | 1.0000 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | solar_radiation_mean_daily_mj_m2 | era5_-20.50_-50.00 | Fernandópolis | 0.1829 | -0.1246 | -0.3075 | True | 0.3075 | 0.3869 | 0.6538 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | solar_radiation_total_mj_m2 | era5_-20.50_-50.00 | Fernandópolis | 0.1700 | -0.1312 | -0.3012 | True | 0.3012 | 0.3869 | 0.6538 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | vpd_mean_kpa | era5_-20.50_-50.00 | Fernandópolis | 0.1123 | -0.1611 | -0.2734 | True | 0.2734 | 0.3869 | 0.6538 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | solar_radiation_mean_daily_mj_m2 | era5_-22.50_-46.50 | Serra Negra | 0.1935 | -0.0792 | -0.2727 | True | 0.2727 | 0.4898 | 0.6346 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-1 | nasa_total_rainfall_mm | era5_-23.00_-46.50 | Jarinu | -0.2554 | -0.0032 | 0.2521 | False | 0.2521 | 0.2860 | 0.4808 | absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-1 | vpd_mean_kpa | era5_-23.00_-49.00 | Cerqueira César | 0.0397 | -0.2121 | -0.2519 | True | 0.2519 | 0.3339 | 0.3654 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | solar_radiation_total_mj_m2 | era5_-22.50_-46.50 | Serra Negra | 0.2018 | -0.0469 | -0.2488 | True | 0.2488 | 0.4898 | 0.6346 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-1 | vpd_mean_daily_max_kpa | era5_-23.00_-49.00 | Cerqueira César | 0.0968 | -0.1510 | -0.2478 | True | 0.2478 | 0.3339 | 0.3654 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |
| m_-2 | vpd_mean_kpa | era5_-23.50_-49.00 | Itaí | 0.0602 | -0.1801 | -0.2403 | True | 0.2403 | 0.8374 | 1.0000 | sign_flip;absolute_delta_rho_ge_0.10;movement_toward_pooled_ge_0.10 |

Most recurrent flagged municipalities across problematic cells:

| era5_grid_id | ibge_code_removed | municipality_removed | high_influence_cells | distinct_variables | distinct_late_months | sign_flips | maximum_absolute_delta_rho | mean_weight_all_grid_years | share_years_largest_weight |
|---|---|---|---|---|---|---|---|---|---|
| era5_-23.00_-46.50 | 3525201 | Jarinu | 10 | 6 | 2 | 6 | 0.3731 | 0.2860 | 0.4808 |
| era5_-22.00_-50.50 | 3541703 | Quatá | 9 | 6 | 2 | 9 | 0.4159 | 0.7087 | 1.0000 |
| era5_-22.00_-51.50 | 3542404 | Regente Feijó | 8 | 6 | 2 | 3 | 0.2214 | 0.2018 | 0.1923 |
| era5_-22.00_-51.50 | 3541406 | Presidente Prudente | 8 | 5 | 2 | 6 | 0.2070 | 0.2369 | 0.5385 |
| era5_-22.50_-50.50 | 3535507 | Paraguaçu Paulista | 8 | 6 | 2 | 5 | 0.1813 | 0.3051 | 0.6923 |
| era5_-23.00_-49.00 | 3504503 | Avaré | 8 | 5 | 2 | 8 | 0.1446 | 0.5099 | 0.6538 |
| era5_-23.50_-49.00 | 3521804 | Itaí | 7 | 6 | 2 | 7 | 0.2403 | 0.8374 | 1.0000 |
| era5_-20.50_-50.00 | 3515509 | Fernandópolis | 6 | 5 | 2 | 6 | 0.3075 | 0.3869 | 0.6538 |
| era5_-23.00_-49.00 | 3511409 | Cerqueira César | 6 | 6 | 2 | 6 | 0.2519 | 0.3339 | 0.3654 |
| era5_-23.50_-46.00 | 3518305 | Guararema | 6 | 4 | 2 | 2 | 0.1613 | 0.2579 | 0.4082 |
| era5_-21.00_-48.00 | 3543402 | Ribeirão Preto | 6 | 4 | 2 | 6 | 0.1452 | 0.1881 | 0.7115 |
| era5_-23.00_-47.00 | 3536505 | Paulínia | 6 | 6 | 1 | 3 | 0.1438 | 0.3338 | 0.6538 |

The audit identifies municipalities capable of materially changing particular grid correlations, but it does not support causal attribution. Repeated disagreement is not explained solely by one municipality statewide; it reflects a combination of grid composition and genuinely heterogeneous local historical associations.

## 4. Effect on the Checkpoint 2 interpretation

This audit **does not materially overturn** the late-season humidity/soil-moisture versus temperature/VPD story, but it reinforces the Checkpoint 2 classification of **B — Partially robust**. The 11 weak-consistency cells are confined to February and March, include duplicated solar representations, and exclude relative humidity and deeper soil moisture. They do show that rainfall, VPD, temperature, surface moisture, and radiation responses are not spatially uniform enough to justify a single statewide mechanistic interpretation.

## Stop boundary

No feature engineering, variable reduction, nonlinear or predictive modeling, biological labeling, causal interpretation, harvest-share weighting, or harvest-progress reconstruction was performed.
