"""
Harvest-season configuration.

Each harvest season is mapped to the preceding growing-season
weather window used in Operation Sugar.
"""

HARVEST_SEASONS = {
    "2025/26": {
        "weather_start": "2024-09-01",
        "weather_end": "2025-04-30",
        "harvest_start_year": 2025,
    },
    "2026/27": {
        "weather_start": "2025-09-01",
        "weather_end": "2026-04-30",
        "harvest_start_year": 2026,
    },
}