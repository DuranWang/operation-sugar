"""
Mappings used to transform raw UNICA data into the
standard Operation Sugar schema.
"""

# ============================================================
# TB_02: Biweekly sugarcane crush
# ============================================================

UNICA_CRUSH_COLUMN_MAP = {
    "SAFRA": "season",
    "QUINZENA": "period_end_date",
    "REGIÃO": "region",
    "MOAGEM": "crush_tonnes",
}


# ============================================================
# Standard region values
# ============================================================

UNICA_REGION_MAP = {
    "SÃO PAULO": "sao_paulo",
    "DEMAIS ESTADOS": "other_states",
}

# TB_04: Biweekly sugar production by region
UNICA_SUGAR_COLUMN_MAP = {
    "SAFRA": "season",
    "QUINZENA": "period_end_date",
    "REGIÃO": "region",
    "PRODUÇÃO": "sugar_tonnes",
}