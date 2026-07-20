# Feature Dictionary

This document defines all weather features used or proposed in Operation Sugar.

Each feature includes its definition, measurement unit, and agronomic rationale. Detailed discussions of feature selection and design philosophy are provided separately in `feature_engineering_design.md`.

## 3. Feature Categories

### 3.1 Baseline Weather Features

These features summarize overall weather conditions during a specified period.

| Feature Name | Definition | Unit | Purpose |
|--------------|------------|------|---------|
| `total_rainfall` | Sum of daily precipitation | mm | Measures total water supply |
| `average_temperature` | Mean daily temperature | °C | Measures general thermal conditions |
| `average_humidity` | Mean daily relative humidity | % | Measures atmospheric moisture |
| `rainy_days` | Number of days with rainfall greater than 1 mm | days | Measures rainfall frequency |
| `weather_observation_days` | Number of daily observations available | days | Serves as a data-quality check |

### 3.2 Rainfall Distribution Features

Total rainfall alone does not describe how rainfall is distributed through time.

| Feature Name | Definition | Unit | Agronomic Rationale |
|--------------|------------|------|---------------------|
| `heavy_rain_days` | Number of days with precipitation above a selected threshold | days | Identifies intense rainfall events |
| `max_daily_rainfall` | Maximum daily precipitation | mm | Measures the largest rainfall event |
| `rainfall_intensity` | Total rainfall divided by the number of rainy days | mm per rainy day | Distinguishes frequent light rainfall from concentrated heavy rainfall |
| `dry_days` | Number of days with rainfall at or below 1 mm | days | Measures the frequency of dry conditions |
| `max_consecutive_dry_days` | Longest sequence of days with rainfall at or below 1 mm | days | Measures persistent water stress |
| `rainfall_variability` | Standard deviation of daily precipitation | mm | Measures variability in rainfall distribution |

> **Note:** Rainfall thresholds should initially be treated as configurable parameters rather than fixed scientific constants.

### 3.3 Temperature Features

Temperature affects growth rate, plant respiration, maturation, and sucrose accumulation.

| Feature Name | Definition | Unit | Agronomic Rationale |
|--------------|------------|------|---------------------|
| `temperature_mean` | Mean daily temperature | °C | Measures the overall thermal environment |
| `temperature_std` | Standard deviation of daily temperature | °C | Measures temperature variability |
| `hot_days` | Number of days above a selected temperature threshold | days | Identifies potential heat stress |
| `cool_days` | Number of days below a selected temperature threshold | days | Identifies conditions that may slow vegetative growth or support maturation |
| `max_temperature` | Highest daily temperature during the period | °C | Measures extreme heat exposure |
| `min_temperature` | Lowest daily temperature during the period | °C | Measures cold exposure |
| `growing_degree_days` | Sum of positive temperature accumulation above a base temperature | degree-days | Approximates accumulated crop development |

> **Note:** The base temperature used for growing degree days should be determined based on agronomic literature before implementation.

### 3.4 Humidity Features

Humidity may influence evapotranspiration, crop water demand, disease pressure, and harvesting operations.

| Feature Name | Definition | Unit | Agronomic Rationale |
|--------------|------------|------|---------------------|
| `humidity_mean` | Mean daily relative humidity | % | Measures the overall atmospheric moisture level |
| `humidity_std` | Standard deviation of daily relative humidity | percentage points | Measures humidity variability |
| `high_humidity_days` | Number of days above a selected humidity threshold | days | Identifies conditions favorable for disease development or prolonged wetness |
| `low_humidity_days` | Number of days below a selected humidity threshold | days | Identifies periods of high evaporative demand and potential crop water stress |

> **Note:** Humidity thresholds should remain configurable until appropriate values are established through literature review or exploratory analysis.

#### 3.5 Crop-Stage Features

Weather effects may differ depending on when they occur during the crop cycle.

The exact timing of crop stages varies according to:

- Planting date
- Plant cane versus ratoon cane
- Cultivar
- Municipality
- Harvest season
- Management practices

Therefore, the initial implementation should not assume a single crop calendar for all municipalities.

| Feature Name | Definition | Agronomic Rationale |
|--------------|------------|---------------------|
| `rainfall_establishment` | Total rainfall during the estimated establishment period | Adequate early moisture supports crop establishment |
| `rainfall_grand_growth` | Total rainfall during the rapid biomass accumulation period | Water availability supports stalk growth |
| `dry_spell_grand_growth` | Longest dry spell during the rapid-growth period | Persistent drought may reduce biomass accumulation |
| `temperature_grand_growth` | Mean temperature during the rapid-growth period | Temperature influences vegetative development |
| `temperature_maturation` | Mean temperature during the maturation period | Cooler conditions may promote sucrose accumulation |
| `rainfall_maturation` | Total rainfall during the maturation period | Excess rainfall may delay maturation or dilute sucrose concentration |
| `dry_days_preharvest` | Number of dry days immediately before harvest | Dry weather may improve harvestability |
| `rainfall_preharvest` | Total rainfall immediately before harvest | Heavy rainfall may interrupt harvesting operations |

### 3.6 Rolling-Window Features

Rolling-window features summarize weather conditions over fixed periods preceding a target date or harvest period.

| Feature Name | Definition |
|--------------|------------|
| `rainfall_previous_30d` | Total rainfall during the previous 30 days |
| `temperature_previous_90d` | Mean temperature during the previous 90 days |
| `dry_days_previous_120d` | Number of dry days during the previous 120 days |
| `temperature_maturation_150d` | Mean temperature during the estimated 150-day maturation period |

> **Note:** Highly correlated rolling windows should not automatically be included in predictive models. Window lengths should be selected based on agronomic evidence and model performance.
### 3.7 Harvest-Weighted Features

Harvest-weighted features incorporate harvest progress to better represent the economic relevance of weather conditions throughout the harvesting season.

| Feature Name | Definition |
|--------------|------------|
| `harvest_weighted_rainfall` | Rainfall weighted by harvest activity |
| `harvest_weighted_temperature` | Temperature weighted by harvest activity |
| `harvest_weighted_dry_days` | Dry-day exposure weighted by harvest activity |
| `preharvest_weighted_temperature` | Temperature during the maturation window preceding each harvest period, weighted by harvest volume |

> **Note:** These features require careful interpretation because UNICA harvest data are generally available at the state or regional level rather than the municipality level.

### 3.8 Data-Quality Features

These features monitor the completeness and reliability of weather observations and should be generated even when they are not directly used in predictive models.

| Feature Name | Definition |
|--------------|------------|
| `missing_weather_days` | Expected number of weather observations minus the number of observed days |
| `rainfall_missing_days` | Number of missing precipitation observations |
| `temperature_missing_days` | Number of missing temperature observations |
| `humidity_missing_days` | Number of missing relative humidity observations |
| `weather_coverage_ratio` | Number of observed weather days divided by the expected number of days |
| `has_complete_weather_period` | Boolean indicator of acceptable weather data completeness |
