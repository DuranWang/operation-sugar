# Operation Sugar Analytical Framework

This document defines how Operation Sugar designs and constructs analytical variables for Brazilian sugarcane research.

It focuses on the translation of biological and operational processes into reproducible quantitative representations.

Statistical model design, benchmark comparison, cross-validation, and performance evaluation are documented separately in `modeling_framework.md`.

Related documentation:

- `seasonal_framework.md` defines the biological and operational stages of the sugarcane production cycle.
- `feature_dictionary.md` defines each engineered variable.
- `research_design_decisions.md` documents major analytical and engineering decisions.
- `modeling_framework.md` defines how analytical variables are statistically evaluated.

---

# 1. Research Objective

Operation Sugar transforms heterogeneous agricultural datasets into reproducible analytical variables for sugarcane research.

The platform integrates:

- NASA POWER weather observations;
- UNICA harvest reports;
- IBGE production statistics;
- agronomic literature.

Analytical variables are designed to represent interpretable biological or operational processes rather than arbitrary statistical transformations.

Every variable should answer a clearly defined research question and have a documented interpretation before engineering implementation begins.

---

# 2. Analytical Variable Design

Operation Sugar follows a research-first variable design workflow.

```text
Research Question
        │
        ▼
Available Data
        │
        ▼
Scientific Evidence
        │
        ▼
Analytical Definition
        │
        ▼
Variable Construction
        │
        ▼
Analytical Validation
```

Engineering implementation begins only after the analytical purpose, source data, temporal scope, units, and transformation rules have been defined.

Analytical validation confirms that the engineered variable is constructed consistently with its documented definition.

This may include checks for:

- expected columns;
- valid units;
- temporal coverage;
- duplicate observations;
- missing values;
- aggregation consistency;
- biologically or operationally plausible ranges.

Statistical usefulness is evaluated separately under the procedures defined in `modeling_framework.md`.

---

# 3. Weather Variable Design

Weather variables describe either historical environmental conditions or weather processes associated with sugarcane development.

## Baseline Variables

Baseline variables summarize observed weather conditions at standard temporal resolutions.

Examples include:

- monthly rainfall;
- monthly temperature;
- monthly relative humidity;
- rainy-day counts;
- dry-day counts;
- maximum daily rainfall;
- maximum consecutive dry days.

These variables establish reproducible descriptive datasets and provide inputs for later analytical construction.

---

## Biological Variables

Biological variables aggregate weather observations over analytically meaningful windows associated with sugarcane development.

Their purpose is to represent environmental conditions linked to specific biological processes rather than arbitrary calendar periods.

Examples may include weather conditions during:

- the growing stage;
- the maturation stage;
- pre-harvest periods;
- other stage-specific analytical windows.

The seasonal definitions governing these windows are documented in `seasonal_framework.md`.

---

## Daily-First Philosophy

Daily observations remain the primary source for weather feature construction.

Monthly and seasonal datasets support:

- descriptive analysis;
- historical benchmarking;
- visualization;
- statistical modeling.

Whenever a variable depends on event timing, thresholds, duration, or consecutive conditions, it should be derived from daily observations whenever possible.

This preserves analytical flexibility and reduces unnecessary information loss.

---

## Intended Analytical Value

Every newly engineered weather variable should have a clearly stated analytical purpose.

Variables should not be introduced solely to increase feature quantity.

Before implementation, each variable should specify:

- the biological or environmental process it represents;
- the source observations required;
- the relevant temporal window;
- the aggregation or transformation rule;
- the intended research use.

The incremental statistical value of engineered variables is evaluated separately under `modeling_framework.md`.

---

## Parsimony

Operation Sugar intentionally begins with a limited set of interpretable weather variables.

Simple and well-supported definitions are preferred over unnecessarily complex feature engineering.

Additional variables should only be introduced when supported by:

- a clearly defined research question;
- relevant scientific literature;
- appropriate source data;
- an interpretable construction method.

The objective is to improve analytical meaning rather than maximize feature quantity.

---

# 4. Harvest Variable Design

Harvest variables are derived from observed sugarcane crushing activity reported by UNICA.

Unlike weather variables, harvest variables primarily describe operational behavior rather than environmental conditions.

Harvest analytics are inferred from historical observations instead of being imposed through a predefined crop calendar.

Current harvest representations include:

- historical harvest calendars;
- monthly crushing distributions;
- cumulative crushing progress;
- harvest timing metrics;
- comparable historical snapshots;
- harvest-block aggregations;
- complete-season totals.

Each harvest variable should retain a clear relationship to the underlying reported crushing observations.

Detailed harvest definitions and design decisions are documented in:

- `research_design_decisions.md`;
- `feature_dictionary.md`;
- `harvest_intelligence.md`.

---

# 5. Design Principles

Operation Sugar follows four principles when designing analytical variables.

## Biological or Operational Meaning

Each variable should represent a plausible biological, environmental, or operational process.

Feature construction should begin with research interpretation rather than implementation convenience.

---

## Interpretability

Variables should remain understandable to both domain researchers and quantitative analysts.

Definitions should clearly describe:

- what the variable measures;
- how it is constructed;
- which period it represents;
- which source data it uses.

---

## Reproducibility

Each analytical variable should be reproducible from the documented source data and transformation rules.

Variable construction should produce consistent outputs when applied to equivalent datasets.

Definitions, units, temporal windows, and aggregation procedures should be documented explicitly.

---

## Simplicity Before Complexity

Simple and transparent variable definitions are preferred before more complicated feature construction.

Complexity should only be introduced when the underlying process cannot be represented adequately through a simpler definition.

This principle applies to feature construction only.

Statistical model complexity is governed separately by `modeling_framework.md`.

---

# Summary

Operation Sugar constructs analytical variables by translating biological and operational processes into reproducible quantitative representations.

The analytical framework follows this sequence:

```text
Research Question
        │
        ▼
Available Data
        │
        ▼
Scientific Evidence
        │
        ▼
Analytical Definition
        │
        ▼
Variable Construction
        │
        ▼
Analytical Validation
```

Seasonal definitions determine analytical windows.

Analytical windows determine variable construction.

Variable definitions determine engineering implementation and validation.

Statistical model design and evaluation begin only after this analytical construction process is complete and are documented separately in `modeling_framework.md`.