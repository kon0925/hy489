# Week 5 — Hands-on: terminologies and ontologies

**Monday 19 and Wednesday 21 October 2026 · in class · not graded**

* **Hands-on A (Monday)** — look a code up properly: the browsers, then a
  terminology server over HTTP.
* **Hands-on B (Wednesday)** — measure your own data: the five codability
  metrics, then validate every code against a real terminology.

Lab 3 on 30 October is the graded version and starts from what you produce here.

## Contents

```
week05/
├── codability.py     the five metrics. pandas only, no network
├── terminology.py    $lookup, $subsumes, $expand, $validate-code, $translate
└── requirements.txt
```

## Running it

```bash
pip install -r requirements.txt

python3 codability.py                  # offline, always works
python3 terminology.py --demo          # the five operations, needs network
python3 terminology.py --validate-dataset
```

`codability.py` reads `../../labs/lab01/data/` and falls back to the GitHub raw URL,
so it works from a clone or from Colab. Point it elsewhere with `--data`.

## The browsers, for Hands-on A

| Tool | Where | Notes |
|---|---|---|
| SNOMED CT browser | browser.ihtsdotools.org | Free, no account. Search, read the hierarchy, run ECL |
| LOINC search | loinc.org/search | Free with registration |
| ICD-11 browser | icd.who.int/browse | Free, no account |
| FHIR terminology server | tx.fhir.org/r4 | Free community server. It does go down |

## Ground rules

1. **tx.fhir.org is a shared free service.** Sequential requests, always with a
   timeout, no loops over thousands of codes. `--validate-dataset` is slow on
   purpose.
2. If it is down, the offline half still teaches the lesson. Run `codability.py`
   and do Hands-on A entirely in the browsers.
3. Nothing here sends data anywhere. Both scripts only ask questions about codes.

## What the scripts are for

`codability.py` computes the five numbers from the lecture:

| Metric | What it tells you |
|---|---|
| Coded fraction | What share of rows carry any code at all |
| System coverage | Whether anything records *which* vocabulary |
| Distinct codes per concept, both directions | Descriptions with several codes means inconsistent coding. Codes with several descriptions means inconsistent display |
| Residual fraction | Share sitting in unspecified / other / NOS. This is a fact about the coding workflow, not about the patients |
| Head of the distribution | What share the top 20 descriptions cover. This is what makes a mapping project finishable |

It reads `CODE` with `dtype=str` on purpose. Concept ids are strings; read them
as numbers and long ids lose precision, which is what Excel does to them
automatically.

`terminology.py` wraps the five FHIR operations. The one to run first is
`$subsumes`, both ways round: the answer flips from `subsumes` to `subsumed-by`,
which is the whole of the SNOMED hierarchy in one HTTP call.

`--validate-dataset` looks up every distinct condition code against a real
server. On this synthetic dataset almost everything resolves. On a hospital
extract, the unresolved list is the most valuable output of the day: it is the
set of codes somebody invented, mistyped, or took from a different edition.

## Note on the data

The Lab 1 cohort is synthetic and scores far better on these metrics than
anything a hospital will hand you. That gap is the Week 1 "too clean" lesson
returning, and the lecture says so explicitly.
