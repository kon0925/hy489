# Outcome · change in body weight

**LOINC 29463-7**, Body Weight, kg. Recorded at encounters, so a patient with no encounter has no weight.

| | Definition | Why |
|---|---|---|
| **O1** (primary) | First weight in [+90, +730] days minus the last weight in [−365, 0]. | Starts after the first three months so early, transient changes do not dominate; wide enough to keep patients who are seen rarely. |
| **O2** (alternative) | Weight closest to day +365 within [+180, +540] minus the **mean** of all weights in [−365, 0]. | A fixed one-year horizon, and a baseline that is less sensitive to one unusual reading. |

Extra sensitivity: O1 with the window shortened to [+90, +365].

**Missingness.** The number of eligible patients with no weight in the window is reported by arm. If initiators are seen more often than non-initiators (they have a new prescription to follow up), weight is not missing at random, and this is the bias the negative control outcome is meant to detect.

Values are taken as recorded. Implausible values (for example below 30 kg or above 250 kg for an adult) are counted and reported, and excluded; the rule is fixed here so it is not decided after seeing the results.
