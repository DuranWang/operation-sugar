"""Build upper-one-metre soil-water features from validated native layers."""
import argparse
import csv
import json
import math
from pathlib import Path

from src.etl.open_meteo.download_advanced_weather import (
    ROOT,
    write_csv,
    write_json,
)

SOIL_WEIGHTS = {'0_to_7cm': 0.07, '7_to_28cm': 0.21, '28_to_100cm': 0.72}
FEATURE = 'soil_moisture_0_to_100cm_m3_m3'


def add_soil_moisture_features(rows):
    result = []
    for row in rows:
        values = {layer: float(row[f'soil_moisture_{layer}_m3_m3']) for layer in SOIL_WEIGHTS}
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in values.values()):
            raise ValueError('Soil layer is missing, nonfinite or outside [0, 1]')
        result.append({**row, FEATURE: sum(values[layer]*weight for layer, weight in SOIL_WEIGHTS.items())})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--input',
        type=Path,
        default=ROOT / 'data/processed/advanced_weather/era5/SP/2010-01-01_2010-12-31',
    )
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    out = args.output or args.input / 'features'
    if out.resolve() == args.input.resolve():
        raise ValueError('Feature output must not overwrite the ETL directory')
    coverage = json.loads((args.input / 'processing_coverage.json').read_text())
    count = 0
    # Only process grids validated by the latest ETL run; ignore stale files.
    for grid_id in coverage['completed_grid_ids']:
        for level in ('grid', 'municipality'):
            for frequency in ('daily', 'monthly'):
                source = args.input / level / frequency / (grid_id + '.csv')
                with source.open(newline='', encoding='utf-8') as stream:
                    rows = list(csv.DictReader(stream))
                write_csv(out / level / frequency / source.name, add_soil_moisture_features(rows))
                count += 1
    write_json(out / 'feature_coverage.json', {**coverage, 'feature': FEATURE,
               'layer_thickness_weights': SOIL_WEIGHTS, 'output_files': count,
               'interpretation': 'Thickness-weighted volumetric water content, not crop-specific root-zone water'})
    print(f"Soil features: {count} files; status={coverage['status']}")
    return 0 if coverage['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
