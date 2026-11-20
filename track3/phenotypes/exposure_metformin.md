# Exposure · metformin initiation

The only metformin product in the cohort: **RxNorm 860975**, 24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet. Every one of its prescriptions records the reason as type 2 diabetes (SNOMED 44054006).

| | Definition | Why |
|---|---|---|
| **E1** (primary) | Index = START of the patient's first-ever 860975 prescription. No 860975 before it. | New-user design: we compare people starting the drug, not long-term users who are survivors of it. |
| **E2** (alternative) | As E1, and that first prescription has DISPENSES ≥ 2. | A single dispense may be a start that was abandoned. E2 asks whether the answer holds among people who actually continued at first. About a third of metformin prescriptions have a single dispense. |

Non-initiators: eligible patients with no 860975 prescription on or before their own index date. Those who start metformin later are censored at that date.

E2 uses information from the first prescription record only (dispenses recorded on it), not from later follow-up, so it does not introduce immortal time.
