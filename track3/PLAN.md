# PLAN · Track 3 · An observational study

**Group:** Nikiforos (WP1), Myron (WP2), Michalis (WP3)  
**Status:** DRAFT. To be agreed by all three and committed with `protocol.md` before Fri 20 Nov, 23:59. No outcome value has been computed. This is a working plan: windows, covariates and controls are provisional, and any change after the protocol commit is logged in `amendments.md` with its date and reason.

## Question

Among adults with type 2 diabetes or prediabetes, is **starting metformin** followed by a **change in body weight**, compared with comparable patients who were not started?

## Why this question (feasibility, `feasibility.py`)

Counts of exposure and of whether a measurement *exists*. No outcome values were read.

| | new users | measured before and after index |
|---|---|---|
| statin → total cholesterol | 228 | 14 to 38, depending on window |
| **metformin → body weight** | **203** | **68 to 132**, depending on window |

Cholesterol is tested about once every 6.5 years in this cohort; weight is recorded at every encounter. 129 of 203 metformin new users have no encounter in the two years after index, so the outcome window has to be wide and missingness by group is a main result, not a footnote.

## Design (target trial, detail in `protocol.md`)

- **Eligibility:** age ≥ 18 at index; ≥ 1 year of record before index; T2D or prediabetes by the phenotype in `phenotypes/`; no metformin before index; a weight in the baseline window.
- **Strategies:** start metformin at index vs do not start.
- **Index date:** first metformin prescription. Comparators get an index date from an eligible encounter in the same calendar period (rule fixed in the protocol), so neither group gets credit for time before index.
- **Outcome:** weight change = first weight in the follow-up window minus last weight in the baseline window. Window to be fixed in the protocol (candidate 90 to 730 days).
- **Censoring:** death, end of data (2026-09-25), comparator starting metformin.
- **Confounders (baseline only):** age, sex, baseline weight, obesity, hypertension, T2D vs prediabetes, calendar year, number of baseline encounters.
- **Adjustment:** regression; propensity score weighting with balance diagnostics as the "going further" item.
- **Controls (candidates, final choice and justification in the protocol):** negative control outcome: a new acute viral pharyngitis in follow-up, which metformin should not affect; negative control exposure: starting amoxicillin, which should not change weight; positive control: starting an antihypertensive → systolic blood pressure, a known effect in this cohort. All run through the same pipeline.
- **Immortal time:** both groups start follow-up at their own index date; the naive "ever treated" version is reported alongside to show the size of the bias.
- **Sensitivity:** every exposure/outcome phenotype definition, plus the outcome window.

## Who does what

| | Owner | Produces |
|---|---|---|
| WP1 · protocol and phenotypes | Nikiforos | `protocol.md`, `phenotypes/`, `amendments.md`, R1 |
| WP2 · analysis dataset | Myron | `dataset.py`, Table 1, flow diagram, missingness, R2 |
| WP3 · estimate and controls | Michalis | `analysis.py`, results, controls, sensitivity, R3 |
| Shared | all | R4, `REPORT.md`, slides, two rehearsals |

All three review each other's work every week.

## Timeline

| Dates | Done by the end |
|---|---|
| by 20 Nov | PLAN, protocol and phenotypes committed |
| 23 Nov to 4 Dec | dataset, Table 1, adjusted estimate, controls; R1, R2 drafts |
| 7 to 13 Dec | sensitivity, interpretation, R3, R4, report, slides |
| 14 or 16 Dec | presentation |
