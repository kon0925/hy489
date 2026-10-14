# Lab 5 — De-identification and privacy

**Friday 27 November 2026 · 2 hours · Assignment 3**
**Individual. Delivered / not delivered. 4% of the final mark.**
**Deadline Friday 4 December 2026, 23:59**

Read [`HANDOUT.md`](HANDOUT.md) first. This file is the folder and the caveats.

## Setup

```bash
cd labs/lab05
source ../lab01/.venv/bin/activate      # Windows: ..\lab01\.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/lab05.ipynb
```

Anything from pydicom 2.3 upwards runs this lab.

## What is here

```
lab05/
├── HANDOUT.md            the written version of the session, and the rubric
├── README.md             this file
├── requirements.txt      pydicom, numpy, pandas, matplotlib
├── check_submission.py   run it before you submit
├── src/
│   ├── profile.py        written for you: PS3.15 Table E.1-1 as data
│   ├── pseudonym.py      patient_pseudonym, remap_uid            (2 stubs)
│   ├── deident.py        apply_profile, shift_dates              (2 stubs)
│   ├── pixels.py         blank_region                            (1 stub)
│   └── verify.py         written for you: the audit
└── notebooks/lab05.ipynb the session, with three checkpoints
```

Five stubs. Each docstring says what it must return and which of the decisions
inside it are yours instead of the standard's.

## The archive

**This lab ships no data.** It reads the Lab 4 archive where it is, at
`../lab04/data/archive`, the same way Lab 2 read `../lab01/data/`. Clone the
whole repository. 85 files, 3.2 MB, 84 DICOM instances across 9 patients, 10
studies and 12 series, plus one text file.

It also reads `../lab04/notebooks/inventory.csv`, which you produced in Lab 4.
If you do not have it, the handout says what to do; you can finish the lab
without it and the difference between a list of what you believe is in an
archive and a walk of what is on the disk is one of the things Part A asks you
to notice.

Your output goes to `out/` (the release), `key/` (the key) and `notebooks/`
(the report and the audit). None of them is in the repository until you put it
there.

## The profile

`src/profile.py` holds 60 attributes: 54 rows from DICOM PS3.15 Table E.1-1 and
6 this lab added. **It is a subset.** Table E.1-1 is about five hundred rows.
The 60 here are every Table E.1-1 attribute that occurs in this archive, the
ones that occur in almost every real archive and happen not to be here, and a
short list of attributes this archive does contain that the standard does not
mention at all.

That last group is the one to read. An attribute missing from Table E.1-1 is
not an attribute the standard has cleared. It is an attribute the standard has
not considered. `profile.coverage()` prints the 34 attributes in this archive
that the profile says nothing about, and every one of them is released exactly
as it is.

The table was verified against PS3.15 edition 2026c on 6 October 2026.

## Four caveats

**The archive is synthetic, so the hard half is missing.** There are no private
tags, no vendor overlays, no second line of burned-in text in mid-grey, no
Greek characters in a name that a normaliser mangles, no RT structure sets with
a patient name inside a sequence six levels down, no lossy transfer syntax that
has to be decoded and re-encoded. Real de-identification spends most of its
time on exactly those. When this lab feels tractable, that is why.

**One burned-in annotation, drawn at the maximum pixel value, in a clean band.**
`find_annotation_band` works on it because of all three of those properties.
A real console draws text at whatever value it likes, in several places, and
sometimes over the anatomy. Blanking a band is not certifying an image.

**The identifier space is tiny and the attack is therefore fast.** 110,000
guesses break an unkeyed hash of these patient IDs in under a second on a
laptop. A real hospital number space is larger and still enumerable, and the
only thing that changes is how long the loop runs.

**The file meta information is not in Table E.1-1 and is not touched here.**
`ImplementationClassUID` (0002,0012) survives into the release unchanged and
says which program wrote the original files. It identifies a program and not a
person. Decide for yourself whether that is a sentence you would be happy to
have written in a data protection impact assessment.

## Never run this over real data

Not your own images, not a friend's, not an extract from a placement. The
synthetic archive is the only thing that goes into this notebook, into `out/`,
onto a public DICOM server, or into this repository.

This matters more here than it did in Lab 4. A de-identification script is a
reason to open files, and "I was testing whether the script worked" is the
sentence people say after they have looked up a record they had no business
looking up. Looking up your own record, or a relative's, is the most common
data protection dismissal in health care. The script being good is not a
defence and neither is the intention behind it.

## What happens next

Week 10 takes secondary use, consent and governance, and the release you
produce today is the thing that gets governed. Week 11 is the EHDS, where the
same release crosses a border.

## The caveat that matters most

**Fourteen of the sixty rows in `src/profile.py` carry an action code this lab
could not check against the standard itself.** They are marked `E.1-1?` and
`profile.sources()` lists them. They came from a third-party transcription of
Table E.1-1; nineteen attributes appear in both that transcription and the
published standard and all nineteen agree, which is reassuring and is not
proof.

Run `profile.sources()` in Part A and look at the list. A de-identifier is
exactly as correct as the copy of the table it was built from, the output looks
identical either way, and nobody downstream can tell. Most real
de-identification code cannot even say which of its rows are which.

Nothing in the lab turns on those fourteen values. What the lab is about is
what D, Z, X, K, U and C mean, and what each one costs.
