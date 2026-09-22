# HY-489 · Lab 1 — Foundations

**Friday 2 October 2026 · 09:00–11:00**

By the end of this session you will have a working environment, a real-shaped
health dataset in a database, and the ability to ask clinical questions of it in
SQL. Labs 2–6 all build on top of this.

Work in pairs if you like. Ask a TA the moment something does not work — the
point of the session is that you leave with it working, not that you struggle
quietly.

---

## 0 · Setup `0:00 – 0:15`

```bash
git clone https://github.com/kon0925/hy489.git
cd hy489/labs/lab01
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/lab01.ipynb
```

Run the first cell. It prints your Python, pandas and SQLAlchemy versions and
lists the CSVs. If it throws, put a hand up — do not carry a broken environment
into Part A.

**Database.** Postgres if you already have it running; otherwise SQLite, which
needs no install at all. Every query in this lab works on both, and nothing in
Labs 2–6 will require Postgres. Losing the lab to an installer is the one
avoidable failure today.

---

## Part A · The dataset in pandas `0:15 – 0:45`

Five CSVs, one shared patient identifier, the shape of a genuine hospital
extract:

| file | rows | one row is |
|---|---|---|
| `patients.csv` | 1,174 | a person |
| `encounters.csv` | 13,550 | a contact with the health system |
| `conditions.csv` | 3,051 | a diagnosis recorded at an encounter |
| `observations.csv` | 50,493 | a measurement or a result |
| `medications.csv` | 1,343 | a prescription |

The data is synthetic. Nobody in it is real. But the shape, the sparsity and the
identifiers are what you would actually receive.

### Load it properly

```python
patients = pd.read_csv("../data/patients.csv", parse_dates=["BIRTHDATE"])
```

`parse_dates` is not cosmetic. A date stored as text sorts alphabetically, which
is right for ISO strings and wrong for everything else, and it breaks silently
the moment a second source uses a different format. Get types right at the door.

### Look before you trust

Four things to run on any table you have not seen before:

```python
df.head()             # what is in it
df.dtypes             # did the types load as you expected
df.isna().mean()      # which columns are sparse
df["COL"].value_counts()   # what is actually in a categorical column
```

### Look at the columns of `patients.csv`

`SSN`, `DRIVERS`, `PASSPORT`, `LAT`, `LON`. Direct identifiers, shipped in the
export, exactly as they would arrive. Nothing in the pipeline removes them for
you. Lab 5 is about what has to happen to this file before anyone outside the
care team can see it — for today, just notice they are there.

### ✅ Checkpoint 1 `10 min`

1. How many patients? How many encounters?
2. What is the date range of encounters — earliest START to latest STOP?
3. The five most common condition `DESCRIPTION`s?
4. Which columns in `observations.csv` have missing values, and how many?
5. Pick any patient Id and count their encounters.

> Expect roughly: 1,174 patients over 13,550 encounters; encounters spanning
> 1931 to 2026; hypertension, pharyngitis and pregnancy near the top; a mean of
> about 11.5 encounters per patient with a long right tail.
>
> **Question 4 has a real answer, and it is worth a minute.** Some observations
> have no `UNITS`. Why would a unit be missing on a row that clearly has a
> value? What kind of observation has no unit at all?

---

## Part B · Into the database `0:45 – 1:15`

pandas is fine for one file on one laptop. It is not fine for data several people
query concurrently, that must not lose a row, and that has to answer "who changed
this and when". That is what a database is for.

### Create the schema

```bash
psql -d hy489 -f ../sql/schema.sql     # or run it from the notebook for SQLite
```

Read `schema.sql` before you run it. Three columns in it would be missing from a
naive first schema, and each one exists because of something that happens in real
clinical data:

* **`encounter_id` on `observation`** — provenance. A potassium result means
  something different taken in the ED than in a routine outpatient draw. Losing
  the link to the encounter loses that.
* **`effective_ts` and `recorded_ts`** — *valid time* versus *transaction time*.
  When the blood was drawn versus when the result entered the system. They can
  differ by days, and the gap is where audits happen.
* **`status` and `supersedes`** — a corrected lab result does not overwrite the
  original. The wrong value was acted upon; the record of it must survive. In
  clinical data you correct by superseding, not by `UPDATE`.

### Load in the right order

`patient` → `encounter` → `condition` / `observation`.

Try it in the wrong order on purpose once. Every row will be rejected, and that
is the foreign key doing precisely its job — it is refusing to store an
observation for a patient that does not exist.

### Verify

```sql
SELECT count(*) FROM patient;
SELECT count(*) FROM encounter;
SELECT count(*) FROM observation;
```

Compare with the pandas shapes from Part A. If they disagree, something was
dropped silently — find it now.

### ✅ Checkpoint 2 `12 min`

1. Run `schema.sql`; all four tables exist.
2. Load `patient` and `encounter`.
3. Load `condition` and `observation`.
4. Run the three verification queries. Do the counts match Part A?
5. On a fresh database, load `condition` first. Read the error and keep it.

---

## Part C · Clinical questions in SQL `1:15 – 1:45`

Three queries are written for you in `sql/queries.sql`. Use them as models.

### ✅ Checkpoint 3 `15 min`

1. **Cohort demographics** — count and mean age by gender.
2. **Top ten conditions by code.** Then group by description instead and compare.
   If the two lists differ, which one is right, and what does that tell you about
   using free text as a key? (This question is the whole of Lab 3 in miniature.)
3. **Encounters per patient** — the distribution. Is it skewed? Most healthcare
   utilisation data is, heavily. What does a mean of 11.5 hide?
4. **A patient timeline** — one patient, their encounters, conditions and
   observations in one chronological list. Three `SELECT`s and `UNION ALL`.
   This is the shape of every "show me the chart" screen ever built.
5. **Find one thing that looks too clean to be real.** One sentence. Real
   extracts have duplicate patients, impossible dates, values in the wrong
   units, and free-text fields containing anything at all. This dataset has some
   of that and not all of it.

---

## Wrap-up `1:45 – 2:00`

### Submit

* the notebook, Checkpoints 1 and 3 answered, **restarted and run top to bottom
  without errors**
* `sql/queries.sql` with your Part B and Part C queries
* a five-line README — which database you used, what broke, and your answer to
  "what looks too clean"

**Deadline: Thursday 8 October, 23:59.** Lab 1 is ungraded. Submit it anyway: if
something is broken we would much rather find out now than on the morning of
Lab 2.

### Before Lab 2 — Friday 16 October, graded

* keep this virtualenv and this database; Lab 2 maps them to FHIR
* `pip install requests fhir.resources`
* skim the FHIR Patient and Observation resource pages at https://hl7.org/fhir/

### Where this goes

Today you have a database of encounters, conditions and observations. In Lab 2
the same data becomes FHIR resources and moves over an API. In Lab 3 the codes
in it get mapped between terminologies. In Lab 5 you take those identifier
columns out. In Lab 6 the whole thing becomes a common data model you can
actually analyse. Every one of those starts from what you built this morning.
