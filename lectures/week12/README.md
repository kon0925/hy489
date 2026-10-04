# Week 12 — The regulation of medical AI

Three standard-library scripts. No installation, no network, no third-party
packages. `monitor.py` and `annex4.py` import Week 9's model and cohort rather
than copying them, so every number they print comes from the same code you ran
in Week 9.

```
python3 classify.py               # MDR Rule 11 and AI Act Art. 6, over eight systems
python3 monitor.py                # post-market monitoring, and two realistic failures
python3 annex4.py                 # the technical documentation, generated from a run
```

Section flags: `classify.py --trees --paths --cost`,
`monitor.py --baseline --drift --inputs --plan`, `annex4.py --file --coverage`.
All three together take about eight seconds.

## classify.py

Two decision trees, printed question by question so that you can disagree with
an answer rather than only with the conclusion.

- **MDR Annex VIII Rule 11** decides the device class. Decision-support software
  is class IIa, IIb if the decision could cause serious deterioration or a
  surgical intervention, III if it could cause death or irreversible
  deterioration, and class I only as a residual.
- **AI Act Article 6(1)** then asks whether the product needs third-party
  conformity assessment. If it does, the system is automatically high risk, and
  its obligations apply from **2 August 2028**. Article 6(2), the Annex III
  route, applies from **2 December 2027**.

Of the eight worked systems, three are high risk from 2028, one from 2027, and
four are not high risk at all. The row to argue about is the in-house
readmission model: it lands in class I on one judgement about its intended
purpose, and changing that word moves it to class IIa, a notified body, and the
AI Act.

## monitor.py

Post-market performance monitoring on Week 9's honest logistic regression,
fitted once on half the cohort and never refitted.

- A baseline over random windows, showing how much AUC wanders on 146 patients
  when nothing at all has changed.
- The same model with windows ordered by age: AUC collapses from 0.624 to
  around 0.52 and no drift has occurred. Any monitoring window defined by a
  variable the model uses does this.
- Two realistic failures. A new blood pressure cuff reading 10 mmHg high moves
  the mean predicted risk from 0.315 to 0.307 and leaves AUC unchanged to three
  decimal places. A case-mix change takes calibration error from 0.043 to 0.258
  and leaves AUC unchanged. **AUC does not move for either.**
- Input monitoring on the cuff change, with a threshold sweep. The shift is 0.49
  standard deviations against a rule of thumb of 0.50, so it misses by a
  hundredth.

## annex4.py

An Annex IV technical documentation skeleton for the Week 9 model, with every
element that can be measured filled in from a real run and every element that
cannot marked, with a note saying who would have to write it.

The subgroup table is the part worth reading: held-out AUC is 0.655 under 50,
0.629 from 50 to 69, and 0.503 at 70 and over. The overall 0.605 conceals that
the model is a coin toss in the oldest group.

Of eighteen element groups, **three** can be generated in full by a script, four
in part, and eleven require a human decision.

## A standing rule

This is teaching code.

Do not present anything it generates as a regulatory submission, a conformity
assessment, or evidence of compliance. The Annex IV output says so on its first
line and that line stays in.

Do not run any of it against real patient data, or against a model that is
deployed and that you are not authorised to audit. Week 9's standing rule
applies here too: probing somebody else's deployed model is an attack on the
people in its training set.

The classifications in `classify.py` are worked judgements for a seminar. A real
classification is made by the manufacturer, documented, and defended to a
notified body, and getting it wrong is a regulatory offence rather than a lost
mark.
