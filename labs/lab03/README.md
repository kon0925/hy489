# Lab 3 — Terminologies and mapping

**Friday 30 October 2026 · 2 hours · graded, 8% of the final mark**
**Deadline: Thursday 5 November, 23:59**

A second hospital sends you its problem list. Harmonise it onto ICD-10, then
report honestly what the harmonisation destroyed.

Nothing here needs a network connection, a server or a licence. The vocabulary
you need is in this folder.

## Contents

```
labs/lab03/
├── HANDOUT.md              what to do, in order — start here
├── requirements.txt        pandas and jupyter, nothing else
├── check_submission.py     run this before you submit
├── data/
│   └── problem_list.csv    651 rows from the second hospital
├── vocab/
│   ├── snomed_subset.csv   14 concepts, with synonyms and parents
│   ├── icd10_subset.csv    25 ICD-10 codes, with a residual flag
│   └── official_map.csv    SNOMED to ICD-10, with what each one costs
├── src/
│   ├── vocab.py            written for you: loading and lookup
│   ├── mapping.py          THE GRADED PART: four stubs to fill in
│   └── metrics.py          written for you: coverage, collapse, residual, loss
├── notebooks/
│   └── lab03.ipynb         the starter notebook you fill in
└── gen_problem_list.py     the seeded generator, so the data is reproducible
```

## Setup

```bash
cd labs/lab03
source ../lab01/.venv/bin/activate      # Windows: ..\lab01\.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/lab03.ipynb
```

## What you are mapping

`data/problem_list.csv` is a synthetic problem list from a second hospital. It
is not the Lab 1 export and it is not tidy. It has local codes that mean
something only inside that hospital, rows with no code at all, the same
condition written five different ways, and a handful of rows that are not
diagnoses. That is what a second source looks like.

The Lab 1 cohort is still there in the background: most of the clinical
concepts in this extract are the ones you have been working with since
October, which is why the shipped SNOMED subset covers them.

## What you hand in

| | |
|---|---|
| `concept_map.csv` | your map: source term, target code, equivalence, and a reason |
| `UNMAPPED.md` | what would not map, grouped by why, with what you would do about it |
| `notebooks/lab03.ipynb` | run top to bottom, all three checkpoints answered |
| 200 words | at the end of the notebook: what you would tell a clinician who asks whether they can count their diabetics from this |

## Three things about the vocabulary

**It is not the real thing.** The real SNOMED to ICD-10 map is a licensed
artefact from SNOMED International, and Greece is not a member, which is the
Week 5 licensing slide arriving in your lab. What is in `vocab/` is a
hand-built teaching subset: 14 SNOMED concepts, 25 ICD-10 codes and a map
between them. Check anything you are unsure of against
[icd.who.int/browse](https://icd.who.int/browse) and
[browser.ihtsdotools.org](https://browser.ihtsdotools.org), both free.

**The ICD-10 here is WHO ICD-10, not ICD-10-CM.** Three to four characters,
no US clinical modification. If you look a code up and find a five-character
version with laterality in it, you have found the CM.

**The official map covers 14 concepts and your extract has more.** Everything
it does not cover is a decision you make and write down. That is the lab.

## The rule that decides most of the marks

A mapping is not a lookup table. Every row of your `concept_map.csv` is a
claim about what somebody meant, and the ones you cannot defend in a sentence
are the ones that are wrong. Thirty of the hundred marks are for the reasons
and the unmapped tail, not for the matches.

Report coverage and collapse together, always. A map that reaches 100% by
putting everything on 'unspecified' has lost the data and passed the test.

## Never send real data anywhere

Not your own, not a friend's, not an extract from a placement. Both datasets
in this repository are synthetic and they are the only things that go into a
notebook.
