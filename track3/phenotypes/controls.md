# Controls

Full justification is in `../protocol.md` (section Controls). Codes are in `codes.csv`.

| Control | Exposure | Outcome | True effect |
|---|---|---|---|
| Negative control outcome | Metformin initiation (E1) | New acute viral pharyngitis, SNOMED 195662009, in [+1, +730] | Zero |
| Negative control exposure | Amoxicillin initiation, RxNorm 308192 | Weight change O1 | Zero |
| Positive control | Metformin initiation (E1), with −2 kg and then −5 kg injected into initiators' follow-up weight | Weight change O1 | Estimate moves by −2 kg, −5 kg (known, injected) |

All run through the same pipeline as the main analysis: same eligibility logic, index dates, windows, covariates and adjustment.

Considered and dropped as a positive control: antihypertensive initiation → systolic blood pressure, because in this cohort the difference is about zero once age is accounted for (`lectures/week09/study.py`).

Note: in this cohort amoxicillin is always prescribed for acute viral pharyngitis, so the negative control exposure compares patients who had an acute infection with patients who did not.
