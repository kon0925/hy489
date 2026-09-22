# Week 1 · Hands-on — lecturer's live-demo script

**Wednesday 23 September, Part 5 of the lecture. About 35 minutes including the mini-lab.**

Everything below is meant to be typed live on the projector. Students follow in
`notebooks/week01_handson.ipynb`. Nobody needs a working install today: Lab 1 on
2 October is where environments get set up properly, so anyone stuck should pair up
and watch.

Have the solutions notebook open in a second window with its output already produced,
so that if the live cell fails you can switch to a screen that works.

---

## Before the room fills (5 minutes, once)

1. Open `notebooks/week01_handson_SOLUTIONS.ipynb` and run it top to bottom.
2. Write the real numbers on the board or into your notes: patient count, gender
   split, top five conditions, mean encounters per patient. You will want them when
   someone asks whether their answer is right.
3. Put the repository URL on the projector and leave it there:
   `https://github.com/kon0925/hy489`
4. Check the room WiFi actually reaches GitHub. If it does not, hand out the CSVs on
   a USB stick and tell students to set `DATA` by hand in the first cell.

---

## 0 · Framing (2 min, slide "Why we start with synthetic data")

Say the constraint out loud before showing the answer:

> "You cannot download real patient data. Not because it is hard to find, because it
> is illegal. Access needs ethics approval, a contract and usually a secure room you
> physically sit in."

Then the reframe: synthetic data is not a teaching compromise, it is standard
industry practice for development and testing. And the caveat, which matters more
than anything else in this segment:

> "It is only as good as the model behind it. Real data is always messier. Hold on to
> that, because in fifteen minutes I am going to ask you to prove it."

---

## 1 · Load the data (5 min, slide "Walkthrough — load the data")

Type it. Do not paste.

```python
import pandas as pd

DATA = "../../lab01/data/"
patients   = pd.read_csv(DATA + "patients.csv")
conditions = pd.read_csv(DATA + "conditions.csv")
encounters = pd.read_csv(DATA + "encounters.csv")

print(len(patients))
patients[["Id", "BIRTHDATE", "GENDER", "CITY"]].head()
```

**Two things to point at while it runs.**

*The shared key.* `PATIENT` in `conditions` and `encounters` is `Id` in `patients`.
That is a foreign key. This is HY-360, with clinical meaning poured into it.

*The column names.* Scroll `patients.columns` on screen for three seconds and let
somebody notice `SSN`, `DRIVERS`, `PASSPORT`, `LAT`, `LON`. Do not teach
de-identification now. Just say:

> "Those are fake. But that is the shape a real export arrives in, and nothing in the
> pipeline removes them for you. We spend a whole lab on that in November."

---

## 2 · The same patient as FHIR (4 min, slide "Anatomy of a FHIR Patient resource")

The goal is to make FHIR feel approachable, not to teach it. The line that works:

> "It's just JSON."

```python
import json

def to_fhir_patient(row):
    return {
        "resourceType": "Patient",
        "id":        str(row["Id"]),
        "gender":    {"M": "male", "F": "female"}.get(row["GENDER"]),
        "birthDate": row["BIRTHDATE"],
        "name":    [{"family": row["LAST"], "given": [row["FIRST"]]}],
        "address": [{"city": row["CITY"]}],
    }

print(json.dumps(to_fhir_patient(patients.iloc[0]), indent=2))
```

Put the flat CSV row and the nested resource on screen together. Three observations,
no more:

* `resourceType` tells you what it is. Everything in FHIR is a typed resource.
* `name` and `address` are **lists of objects**, because a person can have several of
  each. The CSV could not express that.
* Other resources will point at this `id`. That is how the record gets reassembled.

Then stop. Week 3 is the FHIR week.

---

## 3 · Mini-lab (15 min, slide "Explore the cohort")

Put the five questions on screen and leave them there. Say the rules:

> "Fifteen minutes. Pairs are fine, pairs are better. One to three are warm-ups. Four
> needs a filter and a sort. Five has no code answer and it is the one I actually care
> about."

**Circulate.** Do not sit at the desk. The two things you will be asked most:

| They say | You say |
|---|---|
| "How do I count them?" | `.value_counts()` on the column |
| "How do I get per-patient?" | `.groupby("PATIENT").size()` |
| "My numbers differ from my neighbour's" | They should not. Same file, same answer. Compare the line that loads the CSV |
| "It says FileNotFoundError" | Check `DATA`. If GitHub is unreachable, pair up |

At ten minutes, call out: *"If you are still on question one, skip to question five.
It is the one worth having an answer to."*

---

## 4 · Debrief (7 min, slide "Debrief — what the data taught us")

Collect **question 5 answers first**, out loud, three or four of them, before you show
anything. This is the highest-value minute of the lecture. What usually comes up:

* no missing values anywhere
* everybody has a tidy birth date
* no duplicate patients
* every condition has a code
* names are all spelled correctly

Write them on the board as students say them. Then:

> "Every one of those is a thing that is false in every hospital database on the
> planet. That gap is what this course is about."

Then walk the four debrief cards:

1. **You already used HY-360.** `value_counts`, `groupby`, a join. Health data is the
   relational model underneath.
2. **Meaning needs codes.** Question 2 counted free text. If two hospitals spell a
   condition differently, your count is wrong and you cannot tell. That is Week 5.
3. **Synthetic is too tidy.** The cleanliness that makes this safe to hand out is
   exactly what hides the problems. Weeks 7 and 9.
4. **One patient, many tables.** Question 4 needed a filter and a sort across two
   files. A record must be reassembled. That is the integration problem, live.

**The one thing to get right in this segment:** do not let the debrief become a
lecture about pandas. The pandas was the excuse. The point was the last thirty
seconds of it.

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Nobody can reach GitHub | USB stick, or project your screen and make it a demo instead of a lab. It still works |
| Half the room has no Python | Expected in week one. Pairs. Lab 1 fixes it |
| A cell fails on the projector | Switch to the pre-run solutions notebook. Do not debug in front of 80 people |
| You are 10 minutes behind | Cut the FHIR resource slide and the merge in question 4. Keep question 5 |
| You are 10 minutes ahead | Ask which columns would have to go before this file could leave a hospital. Sets up Lab 5 |
