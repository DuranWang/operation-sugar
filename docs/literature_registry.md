# Literature Registry

This document records the core scientific literature that directly influenced
feature engineering decisions in Operation Sugar.

Only publications that materially affect feature definitions or design
decisions are included in this registry.

---

## P01

**Cardozo, N. P., & Sentelhas, P. C.**

*Sugarcane Ripening: A Review.*

**Research Area**

Sugarcane Physiology

**Key Findings**

- Rainfall during the ripening period strongly affects sucrose accumulation.
- Temperature is another major factor controlling ripening.
- The period approximately 120-150 days before harvest is particularly important.

**Used For**

- Total Rainfall
- Maturation Window Rainfall
- Maturation Window Temperature

---

## P02

**ETCCDI**

Expert Team on Climate Change Detection and Indices

**Research Area**

Climate Science

**Key Findings**

- Defines Dry Day as daily precipitation < 1 mm.
- Defines CDD (Maximum Consecutive Dry Days).

**Used For**

- Dry Day
- Dry Day Count
- CDD

---

## P03

**Nature (2024)**

Observation-constrained projections reveal longer-than-expected dry spells.

**Research Area**

Climate Extremes

**Key Findings**

- Explains why CDD is widely adopted internationally.
- Highlights persistence of dryness rather than rainfall frequency.

**Used For**

- Dry Day
- CDD

---

## P04

Agricultural & Forest Meteorology (2021)

Dry and Wet Spells and Crop Yields

**Research Area**

Agrometeorology

**Key Findings**

- Rainfall distribution is often more informative than total rainfall.
- Dry spell metrics explain crop yield variability.

**Used For**

- Scientific motivation for CDD

---

## P05

Food and Agriculture Organization (FAO)

Crop Information: Sugarcane

**Research Area**

Agronomy

**Key Findings**

- Water deficit sensitivity differs across growth stages.
- Provides crop water requirement information.

**Used For**

- Growing Season
- Crop Calendar

---

## P06

Embrapa

Manejo Varietal na Produção da Cana-de-Açúcar

**Research Area**

Brazilian Agronomy

**Key Findings**

- Defines Brazilian sugarcane growth stages.
- Provides management recommendations.

**Used For**

- Growing Season
- Maturation Window

---

## P07

Journal of Experimental Botany

Sugarcane for Water-Limited Environments

**Research Area**

Crop Physiology

**Key Findings**

- Introduces cumulative water stress concepts.
- APSIM modeling of water stress.

**Used For**

- Water Stress (v1.1)

---

## P08

Field Crops Research

Sugarcane Water Stress Criteria for Irrigation

**Research Area**

Irrigation Science

**Key Findings**

- Plant response depends on soil water availability.
- Soil moisture is more informative than rainfall alone.

**Used For**

- Soil Moisture (v1.1)

---

## P09

Agronomy (2023)

Differential Physiological Responses to Different Drought Durations

**Research Area**

Plant Physiology

**Key Findings**

- Longer drought duration causes substantially greater physiological damage.

**Used For**

- Scientific interpretation of CDD