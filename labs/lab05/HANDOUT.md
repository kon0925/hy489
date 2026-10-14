# Lab 5 — De-identification and privacy

**Friday 27 November 2026 · 09:00–11:00 · Assignment 3 of 3**
**Individual work. Delivered / not delivered. 4% of your final mark.**
**Deadline Friday 4 December 2026, 23:59**

On 13 November you read an imaging archive and wrote down what was wrong with
it. Today you take the same archive, remove the identifiers, and then attack
what you produced.

Four of the things you found in Lab 4 come back today, and none of them is a
defect any more. Each one is a decision somebody has to make and sign.

| Lab 4 finding | Today |
|---|---|
| two patients under one study (S6) | de-identify it as one patient and you have pseudonymised two people to one identifier |
| one truncated instance, pixels will not decode | it is in the inventory and it has no image. Destroy it, or carry it forward as the record of something gone |
| a name drawn into the pixels | header editing does not reach it |
| a patient with no cohort identifier | there is no cohort scheme to take a pseudonym from. Mint one, or leave the patient out |

**Most of what you deliver is writing**, in `notebooks/deident_report.md`.
Two of its five sections contain no code at all. The reason is the same one Lab 2
and Lab 3 were built on: the code either runs or it does not, and the part of
this work somebody has to be able to defend two years later is the part in
sentences.

**Today** is two hours with the TAs in the room, and nothing is collected at the
end of it. **Afterwards** you have one week. There is no mark out of 100: the
assignment is delivered or it is not, and the list at the end is the bar. A
report section of two sentences is not a delivery.

---

## Before you start

```bash
cd labs/lab05
source ../lab01/.venv/bin/activate      # Windows: ..\lab01\.venv\Scripts\activate
pip install -r requirements.txt
python3 -c "import pydicom; print(pydicom.__version__)"
```

### What you need from Lab 4

Two things, both at `../lab04/`:

**The archive**, at `../lab04/data/archive`. This lab reads it in place and
ships no copy of it. If that folder is not there, clone the whole repository.

**`../lab04/notebooks/inventory.csv`**, which you wrote on 13 November. It is
the list of what you believe is in the archive. If you do not have it:

1. Fill the two stubs in `../lab04/src/inventory.py`, run Lab 4's Checkpoint 1,
   and write the CSV. That is twenty minutes and it is Lab 4's whole Part A.
2. If you cannot, ask the TA for the reference copy at the start of the
   session. There is one.
3. If neither, the notebook walks the archive instead and you can finish the
   lab. Say in your report that you did, because the first thing Checkpoint 1
   prints is the difference between the two lists, and with no inventory there
   is no difference to print.

### The ground rule

Nothing real goes into this notebook, into `out/`, onto a public DICOM server,
or into this repository. Not your own images, not a friend's, not an extract
from a placement. The archive is synthetic and `../lab04/gen_archive.py` is how
every file in it was made.

The rule has a particular shape today, because today you are writing a tool
whose purpose is to make files safe to look at. That is a reason to open files,
and "I was testing whether the script worked" is the sentence people say after
they have opened a record they had no business opening. Looking up your own
record, or a relative's, is the most common reason people are dismissed from
health care jobs in this country and everywhere else. The script being correct
is not a defence.

---

## Part A · The profile, 0:15 to 0:50

### The problem

"De-identified" is not a property of a file. It is a claim about what was done
to it, and DICOM has a standard for making that claim exactly:
**PS3.15 Annex E, the Attribute Confidentiality Profiles**.

The Basic Application Level Confidentiality Profile is a list of attributes
and, for each one, what a conformant de-identifier does to it. Six actions:

| | |
|---|---|
| **D** | replace with a non-zero length dummy value consistent with the VR |
| **Z** | replace with a zero length value, or a dummy |
| **X** | remove the attribute, and all items if it is a sequence |
| **K** | keep |
| **C** | clean: replace with a value of similar meaning known not to identify |
| **U** | replace with a new UID that is consistent across the set |

And five combinations, `Z/D`, `X/Z`, `X/D`, `X/Z/D` and `X/Z/U*`, each of which
means "the first one, unless the second is needed to keep the object
conformant". A combination code is a range the standard allows, and choosing
inside that range is your decision and not the standard's.

On top of the Basic Profile sit twelve **options**, each of which puts some
attributes back: Clean Pixel Data, Clean Recognizable Visual Features, Clean
Graphics, Clean Structured Content, Clean Descriptors, Retain Longitudinal
Temporal Information with Full Dates, the same with Modified Dates, Retain
Patient Characteristics, Retain Device Identity, Retain Institution Identity,
Retain UIDs, Retain Safe Private. Each has a code in CID 7050 and you write the
codes into the file, so that the next system knows what it is holding.

### Task 1 — read the table

```python
profile.describe()
```

60 attributes. 54 of them are rows of Table E.1-1 and 6 are rows this lab
added, and the `source` column says which is which. Answer in the notebook:

1. `PatientID` is `Z/D` and `SOPInstanceUID` is `U`. Both identify something.
   Why is one allowed to become empty and the other not?
2. What is the difference between an attribute the standard says `K` about and
   an attribute the standard does not mention?
3. `profile.RESOLUTION` turns every combination code into exactly one action.
   Find one row you would have resolved differently and say what it costs.

### Task 1b — where the table came from

```python
profile.sources()
```

Three values in that column, not two. Forty rows were read off the standard.
Six are this lab's own, for attributes the standard does not list. **Fourteen
are marked `E.1-1?`: their action codes came from somebody else's transcription
of Table E.1-1 and could not be checked against the standard itself.** Nineteen
attributes appear in both sources and all nineteen agree. That is reassuring
and it is not proof.

Look at the list of fourteen. Then:

1. Pick one of them and say what would actually happen if its code were wrong
   in the direction that releases more. Name the attribute and the consequence.
2. Your release will look exactly the same whether those fourteen are right or
   wrong. Nothing downstream can tell. Say what that means for somebody
   receiving a file marked `PatientIdentityRemoved = YES`.
3. This file can tell you which of its rows were checked. Almost no real
   de-identification code can, because nobody recorded it. Should it have to?

This is the lab's own argument arriving a little early. A de-identifier is
exactly as correct as the copy of the table it was built from.

### Task 2 — the archive against the table

```python
covered, uncovered = profile.coverage(sorted(seen))
```

The archive contains 60 distinct attributes. The profile says something about
26 of them. The other 34 are released exactly as they are, and most of them are
geometry and encoding and are fine. Read the list before you decide that.

### Task 3 — `patient_pseudonym`, in `src/pseudonym.py`

Something has to go where the PatientID was, the same something every time for
the same person.

`naive_pseudonym` is written for you: SHA-256 of the identifier, truncated. It
is deterministic, it looks like cryptography and it is the thing Part C breaks.
Week 8 said why: a hash is one-way only when the input cannot be guessed, and a
hospital number is a fixed prefix and six digits.

Write the version that survives. Say in your report what it buys and what it
does not.

### Task 4 — `remap_uid`, in `src/pseudonym.py`

One original UID, one replacement, in every file it appears in. Not one map per
file: one map for the run. New UIDs go under the `2.25` arc, which is the UUID
branch of the OID tree and needs no registration from anybody. A new UID under
somebody else's root is a UID that claims to have come from them.

`pseudonym.uid_from_int` turns an integer into a well-formed `2.25` UID. The
integer is yours.

### Task 5 — `apply_profile`, in `src/deident.py`

Walk the profile, ask `ctx.effective_action(entry)` what to do, do it, record
it. Run it on one instance first and read the before and after side by side.
One row will have changed in a way you did not expect, and finding out which
one is the point of doing it on one file before doing it on 84.

### Checkpoint 1 — 0:50

```python
ctx = deident.Context(SECRET)
rows, summary = deident.run_archive(ARCHIVE, RELEASE, ctx, paths=paths)
deident.summarise(summary)
```

Six numbers and two lists. The lists are the difference between your inventory
and the disk. One file is on disk and not in your list. Say what it is and why
that is correct.

---

## Part B · What the profile does not reach, 0:50 to 1:30

### Task 1 — UID consistency

```python
uids = verify.check_uids(ARCHIVE, RELEASE, ctx.uid_map)
```

The profile said `U` four times and 112 original UIDs were remapped. Check that
every replacement is distinct, that every one of them is under `2.25`, and that
`(0002,0003)` in the file meta agrees with `(0008,0018)` in the dataset. A file
where those two disagree opens, displays and is not conformant, and the system
that rejects it is the one in the other hospital three months from now.

The release has 84 files and 83 distinct instance identifiers, which is Lab 4's
duplicate `SOPInstanceUID`, still there. Should de-identification have fixed
it? Write a sentence.

### Task 2 — `blank_region`, in `src/pixels.py`

The secondary capture has the patient's name drawn into the pixels and
`BurnedInAnnotation` says `YES`. Every attribute in the profile can be removed
and the name is still legible.

`find_annotation_band` is written for you and finds one band of saturated
pixels. The blanking is yours: the fill value, the margin, and what you do
about the fact that finding one band is not the same as certifying an image.

Look at the before and the after. A redaction you cannot see is a redaction
nobody can check.

### Task 3 — the structured report

The report instance has no pixels and carries free text. The Basic Profile's
action on `ContentSequence` is **D**, which replaces the whole report with a
dummy. The profile does reach the free text, and the way it reaches it is to
destroy the object.

Claim the Clean Structured Content Option and the lab scrubs item by item
instead. Run both and compare. The scrub will change nothing, because this
report contains no identifier, and that tells you something about this report
and nothing about reports. Say which of the two releases you would ship.

### Task 4 — `shift_dates`, in `src/deident.py`

The Basic Profile empties `StudyDate`. Two studies of one patient 49 days apart
become two studies of one patient on no date at all, and every longitudinal
question in the archive is gone.

The Retain Longitudinal Temporal Information with Modified Dates Option is how
you keep the intervals. This run claims it, which is why `StudyDate` survived
Part A. Fill the stub and then check that the 49 days are still 49 days.

Decisions in the docstring: which attributes move, one offset per patient or
one for the archive, and what you do with the times of day.

### Task 5 — the instance whose pixels are gone

`incoming_2026_04/img_0071.dcm`. The header is complete, the pixel data is
17,450 bytes of an expected 32,768, and nothing decodes. De-identification
works on it perfectly, because de-identification is a header operation.

You released it, or you did not. Both are defensible. What is not defensible is
doing either without recording it: a release that silently drops an instance
has told the recipient there were 83, and a release that silently includes it
has told them there is an image.

### Checkpoint 2 — 1:30

On screen: the UID check with no problems, the two pictures of the secondary
capture, the two versions of the report, the date intervals before and after,
and the broken instance.

---

## Part C · Prove it, 1:30 to 1:55

Everything so far was you being careful. This is the part where somebody who is
not you tries to undo it, and the somebody is Week 8's attack with the target
changed.

### Task 1 — the leak scan

```python
needles, original_uids = verify.known_identifiers(ARCHIVE)
leaks = verify.scan_for_leaks(RELEASE, needles, original_uids)
```

70 strings and 112 UIDs taken out of the original archive, looked for in every
string of every released file, sequences included. It should find nothing.

Finding nothing is weak evidence and you have to say so in the report. The scan
looks for things already known to be identifiers. A Greek surname typed into a
comment field by a radiographer is not on the list and will not be found.

### Task 2 — the hash trap

```python
recovered, tried = verify.attack_pseudonyms(set(naive.values()),
                                            pseudonym.naive_pseudonym)
```

110,000 candidate identifiers: `PAGNI100000` to `PAGNI109999` and `EXT-00000`
to `EXT-99999`. Hash every one, compare against the released pseudonyms, read
the answer off. Against the unkeyed hash this recovers **9 of 9** in under a
second.

Then run the same attack against your own scheme twice, once with the secret
and once without it. With the secret it recovers all nine, and that is not a
bug. It is GDPR Recital 26: a pseudonymised dataset is personal data, because
somebody can still get back to the person. Write that sentence.

### Task 3 — the dates

```python
dates = verify.attack_dates(ARCHIVE, RELEASE)
```

The attacker holds the hospital's own worklist, which is this archive, and is
given the release. They match on study date, modality and instance count, and
nothing else.

Run it against your release and against a second release that claims Retain
Longitudinal Full Dates. One of them matches 0 of 10 studies and the other
matches 10 of 10. That pair of numbers is the argument for the shift, and it is
the only place in this lab where an option is shown to be the wrong choice.

A third release, the Basic Profile alone with the dates emptied, also matches 0
of 10, which says that shifting the dates cost nothing against this attack and
bought you every interval in the archive.

### Task 4 — the shape

```python
shape = verify.attack_shape(ARCHIVE, RELEASE)
```

Now take the dates away from the attacker as well. They are left with each
study's modalities, how many series it has and how many instances. That matches
**7 of the 10 studies to exactly one archive study**, and the other 3 to more
than one.

None of those three things is an attribute. There is no row in Table E.1-1 for
them and no option that removes them, because they are the shape of the data
and removing them means not releasing the data. This is the number that does
not go down when you claim another option, and it is the reason the Five Safes
put controls on the person and the setting and not only on the file.

### Checkpoint 3 — 1:55

```python
verify.report(leaks, uids, (no_key, tried), dates, structure)
verify.to_json("audit.json", ...)
```

Five sections printed, `audit.json` written. Then write the manifest, the
crosswalk, the UID map and the link table, and notice which of the four go in
`out/` and which go in `key/`.

---

## Wrap, 1:55 to 2:00

### What to submit

| what | where |
|---|---|
| the release | `out/archive/` and `out/manifest.csv` |
| the key | `key/link_table.csv`, `key/uid_map.csv`, `key/crosswalk.csv` |
| the notebook, restarted and run from the top | `notebooks/lab05.ipynb` |
| the written report | `notebooks/deident_report.md` |
| the audit | `notebooks/audit.json` |
| your code | `src/` |

Delete `scratch/` first. It holds the two experimental releases from Part B and
Part C, and one of them retains full dates.

Then:

```bash
python3 check_submission.py
```

### The report

Exactly these five headings, in this order:

```
## 1. The profile
## 2. Identifiers and UIDs
## 3. The four decisions
## 4. What the profile did not reach
## 5. The audit, read back
```

`check_submission.py` checks that all five are there and that none of them is
two lines long. It does not check whether what is under them is any good.

### What counts as delivered

There is no score. The TA checks that each of the five is present and is real
work. The last column says where the substance of that section sits.

| # | Section | Code or writing |
|---|---|---|
| 1 | **The profile.** `apply_profile` does what the table says, the release is readable, and section 1 defends two of the combination-code resolutions and names two attributes the profile does not cover | both |
| 2 | **Identifiers and UIDs.** A keyed pseudonym, a consistent and injective UID map, the key written somewhere the release is not, and section 2 saying what the scheme buys and does not | mostly code |
| 3 | **The four decisions.** The merged study, the truncated instance, the burned-in name, the patients with no cohort identifier. Each one gets the decision, the reason, and what the other choice would have cost | writing only |
| 4 | **What the profile did not reach.** The pixels blanked and visible, the dates shifted with the intervals intact, the report handled one way or the other, and section 4 on what is still in the release | mostly code |
| 5 | **The audit, read back.** `audit.json` produced, and section 5 reading the results back as evidence of something limited, including the 7 of 10 that no option removes | both |

If something is missing and there is still time before the deadline, the TA will
ask you to resubmit. After the deadline it is recorded as not delivered.

### How a delivery fails for no reason

- **Submitting without running `check_submission.py`.** Every failure it prints
  is a reason the work would come back to you.
- **A notebook that was not restarted and run from the top.** Execution counts
  that go 1, 4, 2, 9 mean nobody can reproduce what you got, including you.
- **Shipping `naive_pseudonym`.** It is written in the file you are editing and
  the lab breaks it in front of you.
- **The key inside `out/`.** A key that travels with the data is decoration.
  `check_submission.py` fails on this one.
- **A section of the report that is two sentences.** Most of this assignment is
  the report, and a section that short is not delivered.
- **"No issues found."** An audit that reports nothing has described the
  auditor. Say what each check covered and what it could not cover.
- **Reporting the rate.** "No identifiers leaked" is not the finding. Which
  attacks were run, against what, and what each one would have missed is the
  finding.

### Bonus, if you finish early

- Claim Retain Patient Characteristics, rerun, and work out from the Week 8
  uniqueness table what it costs on a cohort of 1,174.
- Write the `C` branch for `StudyDescription` yourself instead of using the
  allow-list in `deident.SAFE_DESCRIPTIONS`, and say why an allow-list beats a
  regular expression here.
- Point `find_annotation_band` at the chest radiograph. Work out why it finds
  nothing and what that proves.

### What this connects to

- **Week 4** gave the DICOM data model, the UIDs and PS3.15. Slide 72 of Week 8
  pointed forward to today.
- **Week 8** gave quasi-identifiers, the uniqueness arithmetic, Recital 26, the
  hash trap, the options and the Five Safes. Part C is Week 8's attack with the
  target changed.
- **Lab 4** gave the archive, the inventory and the four decisions.
- **Week 10** takes secondary use, consent and governance. The release you make
  today is the thing that gets governed, and the key is the thing the
  governance is about.
