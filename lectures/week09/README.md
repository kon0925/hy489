# Week 9 — Secondary use: what a study claims and what a model remembers

Three standard-library scripts. No installation, no network, no third-party
packages. They read the Lab 1 cohort in `../../labs/lab01/data/`.

```
python3 cohort.py                 # one row per patient, built three ways
python3 study.py                  # Session A: the observational study
python3 model.py                  # Session B: the model and its four traps
```

`model.py` also takes `--leakage`, `--split`, `--membership`, `--coef` to run
one section at a time. The whole of `model.py` takes about 40 seconds; the
`--split` section is the slow part, because it runs a nearest-neighbour search
in pure Python.

## cohort.py

Collapses the five Lab 1 CSVs into one row per patient. The point of the script
is the part that usually gets skipped: deciding who counts as a case.

Each condition is defined three ways.

| phenotype | source |
|---|---|
| `*_dx` | a row in `conditions.csv` |
| `*_rx` | a medication in `medications.csv` prescribed for it |
| `*_any` | either of the above |

For type 2 diabetes these give 192, 203 and 353 patients out of 1,174, and only
42 patients satisfy both definitions. Prevalence in this cohort is 16%, 17% or
30% depending on which column you believe. Every number in the rest of the week
inherits that choice.

## study.py

An observational study of antihypertensives and blood pressure, run badly and
then run less badly.

- the naive comparison: treated patients have *higher* systolic pressure
- the reason: treated patients are ten years older, and were treated because
  they were sick (confounding by indication)
- stratification, first on recorded diagnosis, then on age band
- negative controls: the same comparison on weight, cholesterol and HDL, where
  the drug should do nothing
- a positive control: metformin against age, where the same bias must reappear
- immortal time bias: an "ever treated" exposure definition that gives the drug
  credit for the time before it was prescribed

## model.py

A logistic regression written out in the standard library: batch gradient
descent, standardised features, AUC by counting concordant pairs. Roughly sixty
lines, so that nothing is hidden behind a library call.

Four traps, planted and then measured.

1. **Target leakage.** Predict `diabetes_any` with `on_metformin` in the feature
   list. Test AUC 0.81. Remove it: 0.60. The leaked column is a treatment for
   the thing being predicted, so it is unavailable at the moment the prediction
   would be useful.
2. **Splitting by row instead of by patient.** The visit table has 11.5 rows per
   patient. Two of its columns are baseline values, which are properties of the
   person and repeat on all of their rows. A nearest-neighbour model scores 0.79
   on a random row split and 0.50 on a patient split.
3. **Membership inference.** Train on 300 patients with no regularisation, then
   guess membership from the model's loss. Attack AUC 0.53 for the plain model,
   0.59 once squares and pairwise products raise its capacity, with no new
   information about any patient.
4. **Reading coefficients as effects.** The ranking is an association inside one
   cohort. Three of the signs contradict the clinical literature, which is a
   property of the generator that produced the file.

## A standing rule

These scripts are written for a synthetic cohort and they stay on it.

Do not run the membership attack, or anything like it, against a model trained
on real patient data that you did not train yourself and are not authorised to
audit. Probing someone else's deployed model to find out who was in its
training set is an attack on the people in that training set, whatever your
intentions are, and it is the kind of thing that ends a career rather than a
coursework submission.

The same rule from Week 8 still applies to the data: nothing real goes to a
public server, and you do not look up your own record, or a relative's, in a
system you have access to for another reason.
