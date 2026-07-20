"""
Portuguese-to-English mappings used across Operation Sugar.

This module standardizes column names and categorical values from
UNICA, CONAB, and IBGE datasets.
"""
#======================================================================================
# To use this translation module in any file,

# from dictionaries.portuguese_to_english import translate_dataframe

# raw_df = pd.read_excel("data/raw/unica/tabela5457.xlsx")

# processed_df = translate_dataframe(raw_df)

# print(processed_df.head())
# import panda as pd
#==========================================================================================

# ============================================================
# Column names
# ============================================================
import pandas as pd

COLUMN_MAP = {
    # General identifiers
    "SAFRA": "season",
    "Safra": "season",
    "ESTADO": "state",
    "Estado": "state",
    "MUNICÍPIO": "municipality",
    "Município": "municipality",
    "REGIÃO": "region",
    "Região": "region",
    "DATA": "date",
    "Data": "date",
    "QUINZENA": "fortnight",
    "Quinzena": "fortnight",

    # Feedstock and product
    "MATÉRIA-PRIMA": "feedstock",
    "Matéria-prima": "feedstock",
    "TIPO DE PRODUTO": "product_type",
    "Tipo de produto": "product_type",

    # Production
    "MOAGEM": "crush_tonnes",
    "Moagem": "crush_tonnes",
    "AÇÚCAR": "sugar_tonnes",
    "Açúcar": "sugar_tonnes",
    "PRODUÇÃO": "production",
    "Produção": "production",

    # Ethanol
    "ETANOL ANIDRO": "anhydrous_ethanol_m3",
    "Etanol anidro": "anhydrous_ethanol_m3",
    "ETANOL HIDRATADO": "hydrous_ethanol_m3",
    "Etanol hidratado": "hydrous_ethanol_m3",
    "ETANOL TOTAL": "total_ethanol_m3",
    "Etanol total": "total_ethanol_m3",

    # Agricultural area
    "ÁREA CULTIVADA": "cultivated_area_ha",
    "Área cultivada": "cultivated_area_ha",
    "ÁREA COLHIDA": "harvested_area_ha",
    "Área colhida": "harvested_area_ha",
    "ÁREA DE VIVEIROS": "nursery_area_ha",
    "Área de viveiros": "nursery_area_ha",
    "ÁREA EM REFORMA": "renewal_area_ha",
    "Área em reforma": "renewal_area_ha",

    # Yield and quality
    "PRODUTIVIDADE": "yield_tonnes_per_ha",
    "Produtividade": "yield_tonnes_per_ha",
    "ATR": "atr_kg_per_tonne",
    "ATR MÉDIO": "average_atr_kg_per_tonne",
    "ATR médio": "average_atr_kg_per_tonne",

    # Sales and exports
    "VENDAS": "sales",
    "Vendas": "sales",
    "EXPORTAÇÃO": "exports",
    "Exportação": "exports",

    # Geographic totals
    "SÃO PAULO": "sao_paulo",
    "CENTRO-SUL": "centre_south",
    "DEMAIS ESTADOS": "other_states",

    # Variation
    "VAR. (%)": "percentage_change",
    "Var. (%)": "percentage_change",
}


# ============================================================
# Feedstock values
# ============================================================

FEEDSTOCK_MAP = {
    "CANA-DE-AÇÚCAR": "sugarcane",
    "Cana-de-açúcar": "sugarcane",
    "CANA DE AÇÚCAR": "sugarcane",
    "MILHO": "corn",
    "Milho": "corn",
}


# ============================================================
# Product values
# ============================================================

PRODUCT_MAP = {
    "AÇÚCAR": "sugar",
    "Açúcar": "sugar",
    "ETANOL ANIDRO": "anhydrous_ethanol",
    "Etanol anidro": "anhydrous_ethanol",
    "ETANOL HIDRATADO": "hydrous_ethanol",
    "Etanol hidratado": "hydrous_ethanol",
    "ETANOL TOTAL": "total_ethanol",
    "Etanol total": "total_ethanol",
}


# ============================================================
# Brazilian state names
# ============================================================

STATE_MAP = {
    "ACRE": "AC",
    "ALAGOAS": "AL",
    "AMAPÁ": "AP",
    "AMAZONAS": "AM",
    "BAHIA": "BA",
    "CEARÁ": "CE",
    "DISTRITO FEDERAL": "DF",
    "ESPÍRITO SANTO": "ES",
    "GOIÁS": "GO",
    "MARANHÃO": "MA",
    "MATO GROSSO": "MT",
    "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG",
    "PARÁ": "PA",
    "PARAÍBA": "PB",
    "PARANÁ": "PR",
    "PERNAMBUCO": "PE",
    "PIAUÍ": "PI",
    "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS",
    "RONDÔNIA": "RO",
    "RORAIMA": "RR",
    "SANTA CATARINA": "SC",
    "SÃO PAULO": "SP",
    "SERGIPE": "SE",
    "TOCANTINS": "TO",
}


# ============================================================
# Region values
# ============================================================

REGION_MAP = {
    "CENTRO-SUL": "centre_south",
    "Centro-Sul": "centre_south",
    "NORTE-NORDESTE": "north_northeast",
    "Norte-Nordeste": "north_northeast",
    "DEMAIS ESTADOS": "other_states",
    "Demais Estados": "other_states",
    "SÃO PAULO": "sao_paulo",
    "São Paulo": "sao_paulo",
}


"""
    Translate and standardize Portuguese column names and values.

    Parameters
    ----------
    df:
        Raw dataframe downloaded from a Brazilian data source.

    Returns
    -------
    pd.DataFrame
        A translated copy of the dataframe.
    """

def translate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    
    translated_df = df.copy()

    translated_df = translated_df.rename(columns=COLUMN_MAP)

    if "feedstock" in translated_df.columns:
        translated_df["feedstock"] = (
            translated_df["feedstock"]
            .astype("string")
            .str.strip()
            .replace(FEEDSTOCK_MAP)
        )

    if "product_type" in translated_df.columns:
        translated_df["product_type"] = (
            translated_df["product_type"]
            .astype("string")
            .str.strip()
            .replace(PRODUCT_MAP)
        )

    if "state" in translated_df.columns:
        translated_df["state"] = (
            translated_df["state"]
            .astype("string")
            .str.strip()
            .replace(STATE_MAP)
        )

    if "region" in translated_df.columns:
        translated_df["region"] = (
            translated_df["region"]
            .astype("string")
            .str.strip()
            .replace(REGION_MAP)
        )

    return translated_df