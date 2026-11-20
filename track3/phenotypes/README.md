# Phenotypes

Every concept the study uses, each defined at least two ways, with its codes. `codes.csv` holds every code in one machine-readable list for `dataset.py`. Day windows are relative to the index date (day 0). The definitions here are version 1 and change only through `../amendments.md`.

| File | Concept | Definitions |
|---|---|---|
| `exposure_metformin.md` | Metformin initiation | E1, E2 |
| `outcome_weight.md` | Body weight change | O1, O2 |
| `population_t2d_prediabetes.md` | Type 2 diabetes or prediabetes | P1, P2 |
| `covariates.md` | Hypertension, obesity, hyperlipidaemia, smoking, pregnancy, age, sex, calendar year, encounters | two each where it applies |
| `controls.md` | Negative control outcome, negative control exposure, positive controls | — |

Code systems in the cohort: conditions are SNOMED CT, medications RxNorm, observations LOINC. There is no ICD-10 in this extract, so the "second code system" problem from Week 5 shows up here as **diagnosis list vs prescription reason**: the same condition recorded in two places that barely agree (see `lectures/week09/cohort.py`).
