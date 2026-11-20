# Controls

Full justification is in `../protocol.md` (section Controls). Codes are in `codes.csv`.

| Control | Exposure | Outcome | True effect |
|---|---|---|---|
| Negative control outcome | Metformin initiation (E1) | New acute viral pharyngitis, SNOMED 195662009, in [+1, +730] | Zero |
| Negative control exposure | Amoxicillin initiation, RxNorm 308192 | Weight change O1 | Zero |
| Positive control (primary) | Amoxicillin initiation, with −2 kg and −5 kg injected into initiators' outcome weights | Weight change O1 | −2 kg, −5 kg (known, injected) |
| Positive control (secondary) | Antihypertensive initiation, RxNorm 308136 or 314076 | Systolic BP (LOINC 8480-6), same windows as O1 | Expected negative; may be absent in the generator |

All run through the same pipeline as the main analysis: same eligibility logic, index dates, windows, covariates and adjustment.

Note: in this cohort amoxicillin is always prescribed for acute viral pharyngitis, so the negative control exposure compares patients who had an acute infection with patients who did not.
