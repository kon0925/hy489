# Population · type 2 diabetes or prediabetes

| | Definition | Why |
|---|---|---|
| **P1** (primary) | SNOMED **44054006** (Type 2 diabetes mellitus) or **15777000** (Prediabetes) in `conditions.csv`, with START on or before index. | Identifies initiators and non-initiators the same way, from the problem list. |
| **P2** (alternative) | P1, or any prescription whose REASONCODE is 44054006 with START on or before index. | Recovers patients treated for diabetes whose problem list has no diagnosis. In Week 9 the two sources agreed for only a minority of patients. |

**P2 is asymmetric.** A non-initiator has, by definition, no metformin prescription, so the only extra route P2 adds is through metformin itself, which only initiators have. P2 therefore changes who the initiators are without changing who the comparators are. It is kept as a sensitivity analysis precisely to show how much this moves the answer.

**T2D vs prediabetes** is a covariate. A T2D-only analysis (44054006 only) is part of the sensitivity set, because no metformin prescription in the cohort is recorded for prediabetes.
