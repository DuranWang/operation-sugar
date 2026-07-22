# Operation Sugar Architecture

```
IBGE
NASA POWER
UNICA
      │
      ▼
ETL
      │
      ▼
Validation
      │
      ▼
Feature Engineering
      │
      ▼
Processed Dataset
```

---

# UNICA ETL Pipeline

## Historical Database

```
Official Historical Database (.xlsx)
            │
            ▼
process_unica_crush.py
            │
            ▼
unica_biweekly_crush.csv
```

## Incremental Update

```
Latest UNICA Biweekly PDF
            │
            ▼
unica_table_extractor.py
            │
            ▼
unica_normalizer.py
            │
            ▼
update_crushing_history.py
            │
            ▼
unica_biweekly_crush.csv
```

### Design Notes

- The historical database follows the schema of the official UNICA Historical Database workbook.
- Only the official historical regions (`sao_paulo` and `other_states`) are stored in `unica_biweekly_crush.csv`.
- Aggregate `centre_south` observations are retained in normalized report files but are intentionally excluded from the historical database.
- Existing historical observations are never overwritten. Incremental updates append only new validated observations.

- The historical workbook is treated as the authoritative data source.
Biweekly PDF reports are used only to extend the historical database
when the official workbook has not yet been updated.