# Research Design Decisions

This document records the major analytical and engineering decisions made during the development of Operation Sugar.

Rather than describing implementation details, it explains why specific research and engineering choices were adopted and which alternatives were considered.

---

# Decision Principles

Each decision records:

- the decision;
- the rationale;
- the principal alternatives considered.

This structure improves transparency and documents the reasoning behind the project's analytical design.

---

# Section 1 — Research Decisions

## Decision 01 — Research Philosophy

### Decision

Research questions determine engineering implementation.

### Reason

Engineering should support scientific inquiry rather than define it.

---

## Decision 02 — Evidence Registry

### Decision

Assign a unique Paper ID to every major reference.

### Reason

Paper IDs improve traceability across documentation and reduce repetitive citations.

---

# Section 2 — Seasonal Decisions

## Decision 03 — Growing Stage Definition

### Decision

Treat vegetative development as a single analytical growing stage.

### Reason

Municipality-level phenological information is generally unavailable, making finer subdivisions difficult to support consistently.

### Alternatives Considered

- Separate developmental stages
- Calendar-year aggregation

---

## Decision 04 — Harvest Timing Definition

### Decision

Infer harvest timing directly from historical UNICA observations.

### Reason

Observed industrial activity provides a reproducible empirical definition of harvest timing.

### Alternatives Considered

- Fixed crop calendars
- Literature-defined harvest periods

---

# Section 3 — Weather Feature Decisions

## Decision 05 — Dry Day Definition

### Decision

Adopt the ETCCDI dry-day definition.

### Reason

It is internationally recognized and widely used in climate research.

### Alternatives Considered

- 0 mm
- 0.1 mm
- 2 mm

---

## Decision 06 — Maximum Consecutive Dry Days

### Decision

Use CDD as the primary drought indicator.

### Reason

Persistence better represents drought conditions than simple frequency.

### Alternatives Considered

- Dry-day count

---

## Decision 07 — Growing-Stage CDD

### Decision

Calculate CDD over the growing stage rather than the calendar year.

### Reason

Weather outside the biological growing period is less relevant to biomass accumulation.

### Alternatives Considered

- Annual CDD
- Ripening-stage CDD

---

## Decision 08 — Feature Selection Strategy

### Decision

Prioritize biologically meaningful variables.

### Reason

Variables should represent known biological or operational processes rather than arbitrary mathematical transformations.

---

# Summary

Operation Sugar records design decisions to make analytical assumptions explicit, reproducible, and transparent.

Each decision documents:

- what was chosen;
- why it was chosen;
- which alternatives were considered.