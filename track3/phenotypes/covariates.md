# Covariates

All measured in the baseline window, on or before index. Nothing measured after index is adjusted for.

| Covariate | Definition 1 (primary) | Definition 2 (alternative) |
|---|---|---|
| Hypertension | SNOMED 59621000 or 38341003, START ≤ index | Definition 1, or amlodipine (RxNorm 308136) or lisinopril (314076) START ≤ index. Week 9 showed most treated patients have no diagnosis row. |
| Obesity | SNOMED 162864005, START ≤ index | Definition 1, or last baseline weight ≥ 100 kg. Crude: the cohort has no height, so BMI cannot be computed. Baseline weight also enters the model as a continuous variable. |
| Hyperlipidaemia | SNOMED 55822004, START ≤ index | Definition 1, or simvastatin (RxNorm 312961) START ≤ index |
| Smoking | Last LOINC 72166-2 before index: never / former / current every day | Current vs not current. In both, "no record" is its own level, not "never". |
| Pregnancy | SNOMED 72892002. Exclusion if START in [−365, 0]; censoring at a START in follow-up. | Not handled (sensitivity analysis). |
| Age | Years at index, from BIRTHDATE | Age band (18–44, 45–64, 65+) for the stratified analysis |
| Sex | GENDER | — |
| Calendar year | Year of index | — |
| Healthcare use | Number of encounters in [−365, 0] | — |

Why these: each plausibly affects both whether metformin is started and how weight changes. Healthcare use is included because patients who are seen more often both get prescriptions and get weighed more often.
