# Lab 3 — Terminologies and mapping

**Friday 30 October 2026 · 2 hours · graded, 8% of the final mark**
**Deadline: Thursday 5 November, 23:59**

The written version of the slides. Read this if you get lost, and read the
rubric at the end before you start, not after.

---

## Setup

```bash
cd labs/lab03
source ../lab01/.venv/bin/activate      # Windows: ..\lab01\.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/lab03.ipynb
```

No server, no licence, no network. If pandas imports, you are ready.

## The situation

A second hospital has sent you its problem list: `data/problem_list.csv`, 651
rows. You are going to put it onto ICD-10 so that it can be counted alongside
everything else, and then you are going to report what that cost.

It is not the Lab 1 export and it is not tidy:

- local codes that mean something only inside that hospital
- 151 rows with no code at all, just what somebody typed
- the same condition written five different ways
- 210 rows that arrive with an ICD-10 code already filled in, two of which are
  wrong
- a few rows that are not diagnoses
- some Greek

That is what a second source looks like. Week 5 argued about it in the
abstract; this is the same argument with your hands in it.

## What is in the folder

| | |
|---|---|
| `data/problem_list.csv` | the extract: 651 rows, 23 local codes, 44 distinct terms once you normalise |
| `vocab/snomed_subset.csv` | 14 SNOMED concepts, with FSN, preferred term, synonyms and parent |
| `vocab/icd10_subset.csv` | 25 ICD-10 codes, with block, chapter and a residual flag |
| `vocab/official_map.csv` | SNOMED to ICD-10 for those 14, with a note on what each one costs |
| `src/vocab.py` | written for you: loading and lookup, no decisions |
| `src/mapping.py` | **the graded part**: four stubs |
| `src/metrics.py` | written for you: coverage, collapse, residual, loss |

Read the `note` column of `official_map.csv` before you write a line of code.
Fourteen mappings, and almost none of them is free. That file is the shape of
the answer you are about to produce.

---

## Part A · Read the source before you map it

**0:15 – 0:45.** Five tasks, and none of them involves mapping anything.

Every mapping project that goes wrong goes wrong here, because somebody started
mapping before they knew what they were mapping.

### Checkpoint 1

1. **Count the distinct terms twice**, raw and after stripping whitespace and
   case. The two numbers are not close. The difference is not clinical.
2. **Write `normalise()`** in `src/mapping.py`. Whitespace and case, nothing
   else. It must not eat a negation, a laterality or a severity: if
   `no known asthma` normalises to `asthma` you have just given a patient a
   diagnosis they do not have.
3. **Find the concept written the most different ways**, and count the rows it
   accounts for altogether. This is the Week 5 opening slide, in your data.
4. **Two terms look identical and are not.** Find them, print the code point of
   each character, and say what happened. It is not a Python puzzle. A sending
   system configured in the wrong locale really does emit a Latin letter in the
   middle of a Greek word, and nothing you do downstream will make the two
   match.
5. **Two of the preset `icd10_source` codes are wrong.** Find them, give the
   right code, and then answer the harder question: what do you now do with the
   other 210 rows that arrived with a code you did not check?

---

## Part B · Build the map

**0:45 – 1:15.** Three stubs, then run them over everything.

The official map covers 14 SNOMED concepts and costs you nothing: recognise the
concept, look it up, take its target. Everything else is a decision you make
and record.

### Checkpoint 2

1. **`propose(term, local_code, vocab)`** returns candidate ICD-10 targets,
   best first, each with a `via` and a one-sentence `reason`. Suggested order:
   a preset code you have checked, then the official map via the SNOMED
   concept, then a direct read of the ICD-10 title, then nothing.
2. **Run it over every row** and look at what comes back empty. Do not fix them
   yet. Look first.
3. **`equivalence_for(term, icd10_code, vocab)`** returns one of the five R4
   values. The one people get wrong: if the target says *more* than the source
   did, that is `narrower`, not `equivalent`, and it is the dangerous
   direction. Mapping `Type 2 diabetes mellitus` onto `Type 2 diabetes mellitus
   without complications` invents the absence of complications, and somebody
   downstream will count it.
4. **`classify_unmappable(term, local_code)`** returns one of the six reasons.
   An administrative row and a Greek free-text row are both unmapped and they
   are not the same problem.
5. **Write `concept_map.csv`.** Every mapped row needs a reason a clinician
   could read.

---

## Part C · Measure what it cost

**1:15 – 1:45.** The part the marks are really in.

`src/metrics.py` computes the four numbers the same way for everybody, so they
are comparable across the room. Reading them is your job.

### Checkpoint 3

1. **Run `metrics.report(rows, vocab)`.**
2. **Coverage and collapse in one sentence.** Write the sentence you would send
   to the other hospital. It has to contain both numbers. Coverage alone
   flatters any map: put everything on 'unspecified' and you reach 100% having
   destroyed the data.
3. **The residual fraction.** What share of your mapped rows sits on an 'other'
   or 'unspecified' code? Take the worst one and say what a researcher who
   counted it would actually be counting.
4. **Write `UNMAPPED.md`.** Group the unmapped rows by reason, and for each
   group say what you would do and roughly what it would cost. A missing
   synonym is a morning. A Greek free-text field is a different project. An
   administrative row was never a diagnosis. Treating all three the same way is
   the mistake this task exists to prevent.
5. **Name one number you would refuse to publish** without the sentence that
   goes with it.

---

## The 200 words

A clinician at the second hospital asks: **can we count our diabetics from
this?**

Answer in about 200 words, using your own numbers. Say what the count would
include, what it would miss, and what you would need to give a figure you would
stand behind. Do not hedge it into uselessness and do not promise more than
your map can carry.

---

## What to submit

One zip, named `hy489-lab03-<surname1>-<surname2>.zip`, containing:

1. `notebooks/lab03.ipynb` — all three checkpoints answered, run top to bottom,
   outputs visible, both names in the first cell
2. `concept_map.csv` — your map
3. `UNMAPPED.md` — the loss report
4. the 200 words, in the last markdown cell of the notebook

Run `python check_submission.py` first. It catches the things that cost marks
for no reason.

## Marking

| | Marks | |
|---|---|---|
| Checkpoint 1 | 20 | The five answers, including the homoglyph and the two wrong preset codes |
| The map | 25 | `concept_map.csv` complete, valid equivalences, runs from your own code |
| Reasons | 20 | Every mapped row defensible in a sentence. Generic reasons score nothing |
| The loss report | 20 | `UNMAPPED.md` grouped by reason, with a cost for each group |
| The 200 words | 15 | Uses your own numbers, states the limits, commits to an answer |

**How to lose marks for no reason**

- A reason column full of "matched by name". That is not a reason.
- Coverage reported without collapse. It is the one thing this lab is trying to
  stop you doing.
- An unmapped tail with no reasons, or all of it under one reason.
- Dropping the rows that would not map instead of recording them. The CDM looks
  cleaner and the evidence is gone, which is Week 6's argument arriving early.
- A notebook that was not run top to bottom before you zipped it.

## Bonus, if you finish early

- Map the same extract to the **Lab 1 SNOMED concepts** instead of ICD-10 and
  compare the two loss profiles. Which target loses less, and why?
- The official map's `note` column says what each shipped mapping costs. Write
  the same note for each of *your* decisions, and see how many you can defend.
- Look up three of your targets in the real classification at
  [icd.who.int/browse](https://icd.who.int/browse). Did the shipped subset get
  them right?

## Before Lab 4

Keep `concept_map.csv`. Lab 6 builds a common data model over both hospitals,
and this map is what lets the second one join it.
