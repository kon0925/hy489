# Week 6 — Common data models: OMOP and ETL

Two hands-on segments. The first queries a CDM you did not build. The second
builds one from the Lab 1 cohort and then checks whether it is any good.

Everything here runs on Python's standard library. No server, no licence, no
download beyond this repository.

```bash
cd lectures/week06
python3 etl.py                    # builds cdm.db from ../../labs/lab01/data
python3 run_queries.py            # the nine queries, no sqlite3 CLI needed
python3 characterise.py           # a miniature Achilles
python3 characterise.py --checks  # a miniature Data Quality Dashboard
```

If you have the `sqlite3` command-line tool, `sqlite3 cdm.db < queries.sql`
does the same as `run_queries.py`.

## What is here

| File | What it is |
|---|---|
| `cdm/schema.sql` | Eleven tables: a teaching subset of the OMOP CDM, in SQLite |
| `vocab/` | A tiny hand-built vocabulary, and the script that built it |
| `etl.py` | The ETL. Reads the Lab 1 CSVs, writes the CDM, prints a load report |
| `queries.sql` | Nine queries, the first three straight off the slides |
| `run_queries.py` | Runs `queries.sql` without the sqlite3 CLI |
| `characterise.py` | Characterisation, and quality checks with `--checks` |

## Hands-on A: query a CDM you did not build

Twenty minutes, Session A.

1. **Build it.** `python3 etl.py`. Read the load report: rows in, rows loaded,
   rows unmapped, per table. The report is the point, not the database.
2. **Count the zeros.** Which rows landed with `concept_id` 0, and what were
   their source values? Query 4 does it, or write your own.
3. **Top conditions.** Query 2, by standard concept. Compare with the answer
   you got in Week 1 by grouping on `DESCRIPTION`.
4. **Use the hierarchy.** Query 3 counts people with any hypertensive disorder
   through `concept_ancestor`, with no code list. Query 9 asks the same thing
   by source value. The two numbers are different, and the difference is the
   argument for the entire week.
5. **Check the denominator.** Query 6 computes a crude prevalence. What is the
   denominator, and which table gave it to you?
6. **Break it.** Query `condition_occurrence` by `condition_source_value`
   instead of `condition_concept_id`. What do you get, and what is missing?

## Hands-on B: characterise your own CDM

Twenty-five minutes, Session B.

1. **Read the report.** `python3 characterise.py`. Record counts, records per
   person, concept frequencies, the distribution over time, the age and sex
   profile, and the unmapped tail. What looks wrong?
2. **Find the zeros.** They are at the bottom of the report, ranked by
   frequency. That ranking is your mapping backlog.
3. **Run the checks.** `python3 characterise.py --checks`. Forty-three checks,
   grouped the way the Data Quality Dashboard groups its own.
4. **Break it deliberately.** `python3 etl.py --no-observation-period`, then
   run the checks again. Which ones catch it? Which ones pass for the wrong
   reason?
5. **Compute a rate.** Hypertension prevalence, using `concept_ancestor` for
   the numerator and `observation_period` for the denominator.

## Three things about the vocabulary

**It is not the real one.** The OMOP standardised vocabulary comes from
[athena.ohdsi.org](https://athena.ohdsi.org), is several gigabytes, and
requires you to accept the licence terms of each vocabulary you download. What
is in `vocab/` is about forty concepts, hand-built to cover this dataset, so
that the hands-on runs in a lecture theatre. Nothing here is a substitute for
Athena, and any real project starts by downloading the real thing.

**Most of the concept ids are local.** OMOP reserves every id at or above
2,000,000,000 for concepts you mint yourself, guaranteed never to collide with
a real one. Ours are in that range, with nine exceptions: the real standard
concept ids for hypertensive disorder, essential hypertension, diabetes
mellitus, type 2 diabetes mellitus, the three visit concepts and the two gender
concepts, reused so the SQL on the slides runs here unchanged. `vocab/build_vocab.py`
lists them.

**The unmapped tail was put there on purpose.** Every code in this synthetic
cohort is already a standard SNOMED, LOINC or RxNorm code, so a faithful
mapping would leave nothing unmapped, and a CDM with a zero unmapped fraction
teaches exactly the wrong lesson. Two condition codes are therefore withheld
from `vocab/concept.csv`. They stand in for the local laboratory and drug codes
that make up the tail in any real hospital extract. Find them with task 2
before you look up which they are.

## Two things the ETL does that are worth reading the code for

**It routes by domain, not by source file.** Some codes in `conditions.csv`
are findings whose standard concept lives in the Observation domain, so those
rows land in `observation`, not `condition_occurrence`. An ETL that loads the
diagnosis file straight into `condition_occurrence` puts them where no study
will ever look. The load report says how many rows moved.

**`person_id` is a hash, not a counter.** The same source patient gets the same
`person_id` on every run, so a cohort exported last month can be compared with
one exported today. A counter would renumber everybody on each full reload,
and every saved analysis referencing `person_id` would quietly become wrong.

## The six decisions

They are marked `DECISION` in `etl.py`, with the reason beside each one:

1. Who is a person: one row per source patient id, no deduplication.
2. What counts as observed: first to last encounter, no grace period.
3. Which date: the source start date, no time component.
4. Unmapped codes: `concept_id` 0, and keep the row. Never drop it.
5. Visit rollup: one source encounter, one visit.
6. What not to load: payers, costs, providers, organisations, addresses, race.

Any of the six could defensibly have gone the other way. Making the choice by
accident and not writing it down is the part that is never defensible.

## Going further

- [The Book of OHDSI](https://ohdsi.github.io/TheBookOfOhdsi/) — free, and the right starting point
- [The CDM specification](https://ohdsi.github.io/CommonDataModel/) — every table, every column, per version
- [Athena](https://athena.ohdsi.org) — the real vocabularies
- [ATLAS demo](https://atlas-demo.ohdsi.org) — define a cohort without installing anything
- [Data Quality Dashboard](https://github.com/OHDSI/DataQualityDashboard) — the checks this file imitates
