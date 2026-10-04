# Week 7 — Data quality and record linkage

Two hands-on segments. Monday profiles two files nobody has told you anything
about. Wednesday joins them to each other, and then measures how wrong the join
is against an answer key you are given.

Everything here runs on Python's standard library. No server, no licence, no
download beyond this repository.

```bash
cd lectures/week07
python3 gen_sites.py              # writes data/site_a.csv, site_b.csv, truth.csv
python3 quality.py                # the five dimensions, both files
python3 quality.py --lab01        # the same five on the Lab 1 cohort
python3 linkage.py --blocking     # what each blocking key costs
python3 linkage.py --deterministic
python3 linkage.py --sweep        # precision and recall by threshold
python3 linkage.py --errors --threshold 4
```

The three CSVs are committed, so `gen_sites.py` only has to be run if you want
to change the data. The seed is fixed: everybody gets the same files.

## What is here

| File | What it is |
|---|---|
| `gen_sites.py` | Builds the two files and the answer key. Read the docstring before you use the data |
| `data/site_a.csv` | A hospital patient register, 400 rows |
| `data/site_b.csv` | A laboratory's own record of the same town, 380 rows |
| `data/truth.csv` | Which site_a row is which site_b row. 300 pairs |
| `quality.py` | The five quality dimensions, with the AMKA concordance check |
| `linkage.py` | Standardise, block, compare, score. Fellegi-Sunter, written out |

## Hands-on A: profile two files you know nothing about

Twenty-five minutes, Session A.

1. **Look first.** `head data/site_a.csv` and `head data/site_b.csv`. Write down
   what you expect to be wrong before you measure anything.
2. **Run it.** `python3 quality.py`. Five sections per file, and a findings list
   at the end of each.
3. **Completeness.** Which columns in site_b are too sparse to build on? What
   would a pipeline that joins on one of them do, and would it say so?
4. **Correctness finds nothing.** Zero format violations in either file. Say out
   loud what that does and does not tell you.
5. **Concordance.** The first six digits of an AMKA are the holder's date of
   birth. 17 of the 187 site_b rows that carry both disagree. Find them, and
   decide which of the two fields you would believe.
6. **Plausibility.** Ages over 115, birth dates in the future, samples dated
   before the patient was born, and an AMKA that appears twice in site_a.
7. **Compare with Lab 1.** `python3 quality.py --lab01`. Four of the five
   dimensions report nothing at all. That is a fact about the generator, not a
   compliment to the data.

## Hands-on B: link them, and score the link

Thirty minutes, Session B.

1. **Count the pairs.** 400 by 380 is 152,000. Blocking is what makes this
   tractable: `python3 linkage.py --blocking`.
2. **Read the recall column.** Blocking on postcode keeps 40% of the true pairs,
   because the laboratory did not record a postcode for most people. No later
   stage can recover the rest.
3. **Try rules first.** `python3 linkage.py --deterministic`. The best single
   rule links 129 of the 300 pairs.
4. **Score it.** `python3 linkage.py --sweep`. Precision and recall at fourteen
   thresholds, measured against `truth.csv`.
5. **Read the errors.** `python3 linkage.py --errors --threshold 4`, and again at
   16. Both lists have an obvious pattern. Name it.
6. **Does m matter?** `python3 linkage.py --oracle-m` recomputes m from the
   answer key. The inputs move a long way. Watch what happens to the result.

## Three things about the data

**It is synthetic, and the answer key is why.** No row corresponds to a real
person. The only reason to build a file rather than use a real one is
`truth.csv`: without it you cannot compute recall, and a linkage exercise that
cannot compute recall teaches the wrong habits.

**The errors in it are planted, and each one has a purpose.** Feminine surnames,
three transliterations of Χατζηδάκης, short forms, a missing postcode column, a
half-captured AMKA, three sibling pairs and two duplicated AMKAs. Each defeats a
different technique, and `gen_sites.py` says which. Read that docstring before
you draw a conclusion from any number here.

**The numbers are not a benchmark.** 98.4% precision on these two files says
nothing about what your code would do on two files from Venizeleio and a private
laboratory. It is an exercise in measuring, not a score to beat.

## The rule about real data

Nothing real goes anywhere near this. Not your own record, not a relative's, not
an extract from a placement, and nothing you were given access to for another
purpose. If you want to try the code on something other than `data/`, generate
it, or ask.

## Going further

- Fellegi and Sunter, *A Theory for Record Linkage*, JASA 64(328), 1969 — the original, and still readable
- Christen, *Data Matching*, Springer 2012 — the standard textbook
- Weiskopf and Weng, *Methods and dimensions of electronic health record data quality assessment*, JAMIA 20(1), 2013 — where the five dimensions come from
- [Splink](https://moj-analytical-services.github.io/splink/) — Fellegi-Sunter at scale, with EM for m, open source
- [OHDSI Data Quality Dashboard](https://github.com/OHDSI/DataQualityDashboard) — Week 6's checks, and the same five dimensions underneath
