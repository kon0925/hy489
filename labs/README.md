# Labs

Six TA-led sessions, Fridays, two hours each, in the lab slot. **Three of them
carry an assignment.** The other three carry none: they are preparation for the
labs that do, and for the project.

On the Fridays between the labs the same slot is used for **paper
presentations**, in room A113.

## How the course is assessed

| Component | Weight | How |
|---|---|---|
| Team project | 40% | submission and oral presentation, in groups of three |
| **Lab assignments (3)** | **10%** | **individual, marked delivered / not delivered** |
| Final written exam | 40% | short answer and problem solving |
| Paper presentation | 10% | to the TAs, in the lab slot |

### What "delivered / not delivered" means

The three lab assignments are not marked out of 100 and they are not ranked
against each other. Each one is either delivered or it is not, and the handout
for that lab lists exactly what has to be there.

That makes the bar the list. A missing file, a notebook that was never run from
the top, or a report section of one line is not a delivery, and the TA will say
so instead of deducting something. It also means an honest pipeline that reports
what it could not process counts the same as a clever one, which is what each of
these labs is asking for anyway.

**The assignments are individual.** The project is the group work.

## The schedule

| | Session | Date | Assignment | Weight | Deadline |
|---|---|---|---|---|---|
| 1 | [Foundations: environment, a real dataset, SQL refresher](lab01/) | Fri 2 Oct | — | — | — |
| 2 | [FHIR in practice: read, map, validate, write](lab02/) | Fri 16 Oct | **Assignment 1** | 3% | Fri 23 Oct, 23:59 |
| 3 | [Terminologies and mapping](lab03/) | Fri 30 Oct | **Assignment 2** | 3% | Fri 6 Nov, 23:59 |
| — | Paper presentations · A113 | Fri 6 Nov | ten presentations | | |
| 4 | [Imaging and DICOM](lab04/) | Fri 13 Nov | — | — | — |
| — | Paper presentations · A113 | Fri 20 Nov | ten presentations | | |
| 5 | [De-identification and privacy](lab05/) | Fri 27 Nov | **Assignment 3** | 4% | Fri 4 Dec, 23:59 |
| — | Paper presentations · A113 | Fri 4 Dec | ten presentations | | |
| 6 | Analytics on a common data model | Fri 11 Dec | — | — | `lab06/` *(to follow)* |
| — | Paper presentations · A113 | Fri 18 Dec | ten presentations | | |

**You get one week to deliver.** The lab runs on the Friday, the assignment is
due the following Friday at 23:59. Nothing is collected on the day of the lab.

Each folder has a `HANDOUT.md`, which is the one to read first, and a `README.md`
describing what is in the folder and how to set it up.

## The three labs without an assignment

They are not optional, and the reason is that every lab feeds the next one.

- **Lab 1** sets up the environment every later lab reuses, and introduces the
  cohort every lecture reads.
- **Lab 4** produces the imaging inventory that **Assignment 3** starts from. Turn
  up without it and Lab 5 begins with an hour of catching up.
- **Lab 6** is the last session of term, one week before the project is due, and
  it is the one that looks most like the project.

Lab 2 produces the identifier map Lab 3 starts from, Lab 3 produces the concept
map Lab 6 starts from, and Lab 4 produces the inventory Lab 5 starts from.
Skipping a session is not free.

## Paper presentations

Ten per session, four sessions, in room A113 in the lab slot: **6 November,
20 November, 4 December and 18 December.** You present one paper from the course
reading list to the TAs. It is 10% of the final mark, which is the same weight as
all three lab assignments together.

The reading list is published with the lecture material. The TAs allocate the
papers and the slots.

## The data

[`lab01/data/`](lab01/data/) holds the synthetic cohort used by every lab and
every lecture: 1,174 patients with their encounters, conditions, observations and
medications, in the Synthea export schema. There is no second copy anywhere in
the repository. Clone the whole thing.

## The environment

Lab 1 sets up a virtual environment in `lab01/.venv`. Later labs reuse it and add
whatever they need on top, so you only do the setup once:

```bash
cd labs/lab02
source ../lab01/.venv/bin/activate      # Windows: ..\lab01\.venv\Scripts\activate
pip install -r requirements.txt
```

## Delivering an assignment

Each of the three handouts says exactly what to submit and how to name it, and
ships a `check_submission.py` that verifies it. Run it before you submit: every
failure it prints is a reason the TA would hand the work back.

The labs without an assignment ship a self-check instead, `check_outputs.py`,
which verifies that what you produced is what the next lab needs. Nothing is
collected; the point is that you find out on the day rather than a fortnight
later.

## Never send real data anywhere

Not your own, not a friend's, not an extract from a placement. The synthetic
cohort is the only thing that goes into a notebook, onto a public FHIR or DICOM
server, or into this repository.
