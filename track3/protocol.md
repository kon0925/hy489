# Protocol · target trial

Owner: Nikiforos (WP1). Reviewed by Myron (eligibility, index date, windows, comparator) and Michalis (analysis plan, controls, sensitivity).
Version 1, 20 November 2026. Committed before any outcome value was computed. Every change after this commit goes in `amendments.md` with its date and reason.

**Question.** Among adults with type 2 diabetes or prediabetes, is starting metformin followed by a change in body weight over the following one to two years, compared with similar patients who were not started?

Phenotype definitions and codes are in `phenotypes/`. Where this file says "primary" and "alternative", the alternative is run as a sensitivity analysis.

## Target trial

| Component | Target trial (the one we would run) | Emulation in the Lab 1 cohort |
|---|---|---|
| Eligibility | Adults (≥ 18) with type 2 diabetes or prediabetes, never treated with metformin, not pregnant, with a recent weight. | At index: age ≥ 18; ≥ 365 days of record before index (first encounter ≥ 365 days earlier); T2D or prediabetes by phenotype **P1** (diagnosis on or before index; P2 as alternative); no metformin prescription before index; at least one body weight in the baseline window [−365, 0] days; no pregnancy recorded in [−365, 0]; alive at index. |
| Treatment strategies | (1) Start metformin at baseline. (2) Do not start metformin during follow-up. | (1) Initiators: first-ever metformin prescription (exposure phenotype **E1**; E2 as alternative). (2) Non-initiators: eligible patients with no metformin prescription up to their index date. |
| Assignment | Random. | Not random. Emulated by adjusting for baseline confounders measured in [−365, 0]: age, sex, baseline weight, obesity, hypertension, hyperlipidaemia, T2D vs prediabetes, smoking status, calendar year of index, number of encounters in the baseline year. Nothing measured after index is adjusted for. |
| Outcome | Change in body weight (kg) about one year after baseline. | Primary **O1**: first weight in [+90, +730] days minus last weight in [−365, 0]. Alternative **O2**: weight closest to day +365 within [+180, +540] minus mean of weights in [−365, 0]. Body weight is LOINC 29463-7, kg. |
| Follow-up start | Randomisation. | Index date. Initiators: date of first metformin prescription. Non-initiators: the first encounter on or after the date they first meet eligibility (provisional rule; Myron to confirm it is implementable). Both groups start the clock at their own index, so neither gets credit for time before it. |
| Follow-up end | Outcome measured, death, loss to follow-up, or end of study. | Earliest of: the outcome measurement; +730 days; death; end of data (2026-09-25); for non-initiators, the date of a first metformin prescription (censored); start of a recorded pregnancy (censored). |
| Causal contrast | Intention-to-treat and per-protocol. | Analogue of intention-to-treat: initiation vs non-initiation, whatever happened afterwards. Per-protocol is not attempted, because the prescription records do not show reliably who kept taking the drug. |
| Analysis plan | Difference in mean weight change between arms. | See below. |

## Analysis plan

1. **Naive estimate.** Difference in mean weight change (initiators minus non-initiators) with 95% CI, no adjustment.
2. **Adjusted estimate (primary).** Linear regression of weight change on treatment plus the baseline covariates listed under Assignment. Reported as the treatment coefficient in kg with 95% CI.
3. **Simpler adjustment, for comparison.** Stratification by age band and baseline weight band, as in `lectures/week09/study.py`.
4. **Going further, if time allows.** Propensity-score weighting (IPTW), balance checked with standardised mean differences; target < 0.1 for every covariate.
5. **Baseline table.** Table 1 for both arms with standardised differences (WP2).
6. **Missing outcome.** The number of eligible patients with no weight in the outcome window is reported by arm. The primary analysis is complete-case; the share missing and how it differs by arm are reported as a main result, not a footnote, because 129 of 203 metformin users have no encounter in the two years after index.
7. **Immortal time.** The main analysis uses the index dates above. As a demonstration, the naive "ever on metformin, clock starts at first encounter" version is also run, and the difference is reported.
8. **Sensitivity.** The adjusted estimate is re-run for every combination of exposure (E1, E2), outcome (O1, O2) and population (P1, P2) phenotype, and with the outcome window shortened to [+90, +365]. The results table shows how far the estimate moves.
9. **Controls.** Run with exactly the same pipeline (below).
10. **What we report.** The effect in kg with its interval and what the controls say about bias. Not a p-value on its own.

## Phenotypes (summary; codes in `phenotypes/`)

| Concept | Primary | Alternative |
|---|---|---|
| Exposure: metformin initiation | **E1** first-ever prescription of RxNorm 860975 | **E2** as E1, and the prescription has ≥ 2 dispenses (sustained start) |
| Outcome: weight change | **O1** first weight in [+90, +730] minus last in [−365, 0] | **O2** weight nearest +365 in [+180, +540] minus mean in [−365, 0] |
| Population: T2D or prediabetes | **P1** SNOMED 44054006 or 15777000 recorded on or before index | **P2** P1, or any prescription with reason 44054006 on or before index |
| Hypertension | SNOMED 59621000 or 38341003 | or an antihypertensive (RxNorm 308136, 314076) before index |
| Obesity | SNOMED 162864005 | or baseline weight ≥ 100 kg (crude; the cohort has no height, so no BMI) |
| Hyperlipidaemia | SNOMED 55822004 | or simvastatin (RxNorm 312961) before index |
| Smoking | last LOINC 72166-2 before index, three levels | current vs not current; missing as its own level in both |
| Pregnancy (exclusion, censoring) | SNOMED 72892002 | ignored (sensitivity: does handling pregnancy matter?) |

**Known asymmetry in P2.** Non-initiators can only be identified by a diagnosis, while initiators can also be identified by their prescription's reason. P2 therefore admits initiators by a route the comparators do not have. That is why P1 is primary; P2 is kept to show how much the population definition moves the answer.

**Prediabetes.** In this cohort every metformin prescription records type 2 diabetes as the reason, never prediabetes. Including prediabetes widens the comparator pool; the T2D vs prediabetes indicator is adjusted for, and a T2D-only analysis is part of the sensitivity set.

## Controls

**Negative control outcome: new acute viral pharyngitis (SNOMED 195662009) in [+1, +730] days.** Metformin has no plausible effect on a viral throat infection, so the true effect is zero. Same population, index dates, covariates and adjustment as the main analysis; the outcome is binary, so the estimate is a risk difference. A non-zero result means the arms differ in something we did not adjust for. The most likely candidate is how often they are seen: a patient with more encounters has more chances to have pharyngitis recorded, and the same is true of a weight. So this control checks the detection bias that matters most for our outcome.

**Negative control exposure: starting amoxicillin (RxNorm 308192), outcome O1.** Amoxicillin is a short antibiotic course and should not change weight over a year. The outcome window starts at +90 days, after any short-term weight loss from the infection itself. In this cohort amoxicillin is always prescribed for acute viral pharyngitis, so the comparison is between patients who had an acute infection and patients who did not. A non-zero weight change here says our pipeline produces effects from who gets treated, not from the drug.

**Positive control (primary): injected effect.** We do not yet know a true drug effect on weight in this synthetic cohort, and finding it out would mean reading the generator's outcome code before the protocol is committed. So the positive control is synthetic: in a copy of the negative-control-exposure dataset (amoxicillin, true effect assumed zero) we subtract a known amount, 2 kg and then 5 kg, from every initiator's outcome weight, re-run the full pipeline, and check that the estimate recovers the injected effect within its interval. A design that cannot find an effect we put in ourselves is not ready to look for one we did not.

**Positive control (secondary, exploratory): antihypertensive initiation (RxNorm 308136, 314076) → systolic blood pressure change**, same new-user design. Pharmacologically expected. But `lectures/week09/study.py` suggests the generator may not contain this effect, so a null here would tell us about the generator rather than about our design. Reported, not relied on.

## What was looked at before this commit

- Counts of exposures and whether a weight or cholesterol measurement *exists* in a window (`feasibility.py`). No outcome values.
- The list of drugs, their codes and their recorded reasons, and the list of condition and observation codes, to write the phenotypes.
- In `labs/lab01/gen_dataset.py`, only the table of drugs and their reasons (lines 30–55). The code that generates weight was not read. Reading it is planned after the results, as the "going further" comparison with the generator.
