# Week 6 hands-on: instructor notes

Run `python3 etl.py` and `python3 characterise.py --checks` before the session.
Both take a few seconds. The numbers below are from a run on 22 September 2026.

## Expected load report

```
table                       rows in     loaded   unmapped unmapped%
person                         1174       1174          0      0.0%
observation_period             1174       1174          0      0.0%
visit_occurrence              13550      13550          0      0.0%
condition_occurrence           3051       2261        124      5.5%
drug_exposure                  1343       1343          0      0.0%
measurement                   48822      48822          0      0.0%
observation                    2461       2461          0      0.0%
death                             -         68          0      0.0%
```

Two numbers to point at.

**3051 in, 2261 loaded.** The missing 790 are not lost. They are findings whose
standard concept lives in the Observation domain (prediabetes 301, BMI 30+ 147,
normal pregnancy 342) and the ETL routed them to `observation` by domain. The
load report says so on its own line. This is the single best illustration of
"the domain decides the table" and it happens in their own data.

**124 unmapped, 5.5%.** Otitis media (74) and viral sinusitis (50), the two
codes withheld from the shipped vocabulary. Students who go looking will find
them in about a minute with query 4. The withholding is documented in
`vocab/build_vocab.py` and in README.md, and it is worth saying out loud that
it is a teaching device: the cohort itself is entirely coded, which is the same
"too clean" observation they met in Week 1 and again in Week 5.

## Expected query answers

| Query | Answer | What to say about it |
|---|---|---|
| 1 | 1174 persons, mean 42.9 observed years | Ask where 42.9 came from. Answer: our own observation_period rule |
| 2 | Essential hypertension 454, acute viral pharyngitis 444, anemia 249 | Same top three as their Week 1 `value_counts()`, now by concept |
| 3 | **462** people with a hypertensive disorder | Via `concept_ancestor`, no code list |
| 9 | **376** people by source value `59621000` | The same question, 86 people short |
| 5 | condition_occurrence 5.48% unmapped, everything else 0 | The number you publish |
| 6 | 462 / 1174 = 39.4% crude prevalence | Ask what the denominator would be without observation_period |

Queries 3 and 9 are the pair to spend time on. 462 against 376 is the argument
for the entire week, in two numbers they computed themselves. The 86 people in
the gap were recorded with SNOMED 38341003, the parent code, which a source
value match for essential hypertension never sees.

## Expected checks

43 checks. On a clean run in late 2026 you should see either 0 or 2 failures.

The two possible failures are `drug_exposure not in the future` (1 row) and
`measurement not in the future` (3 rows). The synthetic cohort runs a few days
past the date it was generated, so those rows are future-dated until the
calendar catches up, which it does around 25 September 2026. If you see them,
they are a genuine finding about the data and worth showing. If you do not,
say that the same check catches a real and common bug: a source system writing
a default date of 9999-12-31, which lands in the future and is invisible to
anyone who does not check for it.

## The break-it task

```bash
python3 etl.py --no-observation-period
python3 characterise.py --checks
```

Two checks fail immediately: `observation_period is not empty` and
`every person is observed` (1174). That is the expected answer.

The better answer, and the one to draw out of the room, is the note the script
prints at the end: every `within observation` check passed, because there was
nothing to test. A check that passes with no rows is not a passing check. Real
dashboards report those separately for exactly this reason, and a site that
reports "all checks green" without saying how many were vacuous has told you
almost nothing.

## Timings

- Hands-on A: 5 minutes to run the ETL and read the report, 10 minutes on
  tasks 2 to 4, 5 minutes to compare queries 3 and 9 as a room.
- Hands-on B: 5 minutes on the characterisation output, 10 minutes on the
  checks, 5 minutes on the break-it task, 5 minutes on the rate.

## If something goes wrong

**`Cannot find .../lab01/data`** — they cloned the folder rather than the
repository, or they are running from the wrong directory. `cd lectures/week06`.

**No `sqlite3` command** — expected on Windows. `python3 run_queries.py` needs
nothing extra.

**Different numbers from the ones above** — check `python3 vocab/build_vocab.py`
was not rerun against changed data. The committed CSVs are the ones the numbers
come from.

## Exercise answers, Session B

Exercise 3 asks for defensible ETL decisions for a Greek hospital warehouse.
There is no single right answer; the marking is whether the decision is stated
with its consequence. The ETL in this folder makes all six and writes each one
down, so it is a usable worked example if the room stalls.

Exercise 4 asks them to read an Achilles-style report with planted problems.
The intended chase order is: the March 2024 cliff first, because a step change
corrupts every rate computed over a period spanning it and is the only finding
of the four that silently affects results a reader would never suspect.
