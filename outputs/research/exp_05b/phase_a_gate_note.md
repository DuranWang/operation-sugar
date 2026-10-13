# EXP-05B Phase A gate

**PASS for deterministic modeling.** Frozen target reconstruction and weight normalization are rechecked by the EXP-05 loader; target-month T/V values and missingness match EXP-05 exactly. All four antecedent modifiers are derived from complete, calendar-safe prior months only, with full matched-municipality weight coverage. No upstream data were regenerated.

The pre-1981 weather boundary removes the first otherwise-eligible year for Jan–Mar_(t−1) and Jan–Mar_t primary antecedents; other slots have no additional primary-antecedent loss beyond the EXP-05 T/V sample. There are 76 grids with at least 20 paired primary years in each of 16 slots. See `sample_coverage.csv` for every modifier and slot.

Deep-source provenance: the project requests Open-Meteo `models=era5` and `soil_moisture_100_to_255cm`; its ETL averages 24 hourly values to daily and daily values to monthly without depth rescaling. Open-Meteo's ERA5 variable mapping points that API label to `volumetric_soil_water_layer_4`; ECMWF specifies ERA5 native layer 4 as 100–289 cm. The API label is retained as a field name, while this native layer definition is documented separately. This is a sensitivity proxy, not verified crop root-zone water stress.

Sources: [Open-Meteo API](https://open-meteo.com/en/docs/historical-weather-api), [Open-Meteo ERA5 variable mapping](https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Era5/Era5Variables.swift), [ECMWF ERA5 native layers](https://confluence.ecmwf.int/plugins/viewsource/viewpagesrc.action?pageId=488287070).
