# Feature Dictionary

This document defines the analytical variables currently implemented in Operation Sugar.

Each feature includes its definition, measurement unit, and analytical purpose.

Analytical methodology is documented in `analytical_framework.md`.

Future variables are documented in `ROADMAP.md`.

---

# Weather Features

## Baseline Weather Features

These variables summarize historical weather conditions over a specified analytical period.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `total_rainfall` | Sum of daily precipitation | mm | Measures total water supply |
| `average_temperature` | Mean daily temperature | °C | Measures general thermal conditions |
| `average_humidity` | Mean daily relative humidity | % | Measures atmospheric moisture |
| `rainy_days` | Number of days with precipitation greater than 1 mm | days | Measures rainfall frequency |
| `weather_observation_days` | Number of available daily observations | days | Data-quality indicator |

---

## Rainfall Distribution Features

These variables describe how rainfall is distributed through time rather than simply its total amount.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `dry_days` | Number of days with precipitation at or below 1 mm | days | Measures the frequency of dry conditions |
| `max_consecutive_dry_days` | Longest sequence of days with precipitation at or below 1 mm | days | Measures the persistence of dry conditions |

---

# Data Quality Features

These variables monitor the completeness of weather observations.

| Feature | Definition | Unit | Purpose |
|---------|------------|------|---------|
| `weather_observation_days` | Number of available daily observations | days | Measures observation completeness |

---

# Future Variables

Additional analytical variables are planned for future releases and are documented separately in:

- `ROADMAP.md`