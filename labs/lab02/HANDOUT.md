# HY-489 · Lab 2 — FHIR in practice

**Friday 16 October 2026 · 09:00–11:00 · graded, 8% of your final mark**
**Deadline: Thursday 22 October, 23:59**

Lab 1 was diagnostic. This one counts. The marking rewards a pipeline that runs
end to end and an honest account of what it could not do, over a clever one that
half works. Work in pairs if you like; both names in the first cell.

Ask a TA after five minutes of being stuck, not after twenty-five.

---

## 0 · Setup `0:00 – 0:10`

```bash
cd hy489 && git pull
cd labs/lab02
source ../lab01/.venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks/lab02.ipynb
```

Run the first cell. It prints the server's FHIR version and the row counts from
`../lab01/data`. It also asserts that you have changed `SYSTEM` in
`src/mapping.py` to contain your student number. Do that now.

**Always pass a timeout to `requests`.** A public test server can stall, and a
cell with no timeout hangs until you restart the kernel.

### Ground rules on the public server

1. Never post anything real. The synthetic Lab 1 data is the only thing you post.
2. Everything you write is public, and anyone can delete it.
3. Tag every resource with an identifier in your own namespace.
4. Be polite: sequential requests, a timeout, and one Bundle instead of a
   hundred POSTs. If the shared server struggles, run your own with
   `docker run -p 8080:8080 hapiproject/hapi:latest`.

---

## Part A · Read `0:10 – 0:40`

### Ask the server what it supports

`GET {BASE}/metadata` returns a CapabilityStatement. Read it before writing a
query. It tells you the FHIR version, which interactions are allowed, and which
search parameters exist. Servers differ, and a search parameter that is not
listed will silently return something you did not ask for.

### A Bundle is not a list

Every search returns a Bundle:

* the resources are at `entry[i].resource`, not `entry[i]`
* `entry[i].search.mode` is `match` or `include`. Filter on it or your counts
  will include things you did not search for
* `total` is how many matched. `len(entry)` is how many you received. They are
  different numbers, and the difference is the whole point of paging
* `link` with `relation: "next"` means there is more. Follow the URL as given

`fc.fetch_all` in `src/fhirclient.py` does all of this. Use it.

### Search, in one page

| Query | Meaning |
|---|---|
| `?name=smith` | string match, prefix, case-insensitive |
| `?birthdate=ge1980-01-01` | prefixed comparison: `ge gt le lt eq ne ap` |
| `?identifier=urn:oid:1.2\|A103` | system and value, separated by a pipe |
| `?code:not=1234-5` | a modifier on a parameter |
| `?subject.name=maria` | chained search across a reference |
| `?_has:Observation:patient:code=1234-5` | reverse chain |
| `?_include=Observation:patient` | pull the target into the same Bundle |
| `?_sort=-date&_count=50` | order and page size |

Pass these through `params={}`, never by building the URL yourself. Pipes,
colons and commas all need encoding.

### ✅ Checkpoint 1 `12 min`

1. Print the server's FHIR version and the search parameters it supports for
   `Observation`.
2. Fetch any one `Patient` by id. Print id, gender, birthDate and the number of
   identifiers it carries.
3. Search for Patients with `gender=female` born on or after 1990-01-01.
   **How many matched, and how many did you receive?**
4. Pick a patient with data. Fetch their Observations with
   `_include=Observation:patient` and count only the matches.
5. Find the same patient's Conditions. How many carry a `coding`, and how many
   are `text` only?

> Keep the answer to task 5. A CodeableConcept with text and no coding is legal
> FHIR and useless for analysis: you cannot group it, map it or count it. The
> terminology lecture on 19 October opens with exactly this problem.

---

## Part B · Map `0:40 – 1:15`

This is the claim from Week 2 being cashed in. Your Lab 1 tables are the FHIR
resources, almost one for one.

| Lab 1 table | FHIR resource | The interesting part |
|---|---|---|
| patient | Patient | `birth_date` → `birthDate`; gender is a bound code |
| encounter | Encounter | start and stop become one `Period`; needs a `class` |
| condition | Condition | `code` is a CodeableConcept; needs `clinicalStatus` |
| observation | Observation | value becomes `value[x]`; needs `status` and `code` |

**What you lose by leaving the database.** Foreign keys were enforced for you.
FHIR references are strings, and nothing checks that `Patient/4021` exists until
something tries to resolve it. Load order is now your problem.

### Mint an identifier you can find again

The server assigns the `id`. You assign the `identifier`, and it is the only
thing that lets you locate your own work on a shared server.

```python
SYSTEM = "http://csd.uoc.gr/hy489/2026/AM1234"   # your student number
```

The system is a namespace; it does not have to resolve to anything. The value is
the source key from the CSV, which is what makes the mapping reversible. Later,
`?identifier={SYSTEM}|` with a trailing pipe finds everything you created.

### Dates and times

FHIR has four temporal types and they are not interchangeable:

* `date` — `2026-10-16`. This is what `birthDate` is. A timestamp here is invalid
* `dateTime` — `2026-10-16T09:41:00+03:00`. Keep the offset
* `instant` — sub-second, always with an offset
* `Period` — `{start, end}`; `end` may be absent while it is still running

Two traps: `row["BIRTHDATE"]` parsed by pandas is a `Timestamp`, so call
`.date()`. And pandas `NaN`/`NaT` is not `None` — it will reach the field and
fail validation with an unhelpful message. Use the `nn()` helper in
`src/mapping.py` on every optional field.

### Codes

```python
CodeableConcept(
    coding=[Coding(system="http://snomed.info/sct",
                   code=str(row["CODE"]),
                   display=row["DESCRIPTION"])],
    text=row["DESCRIPTION"],
)
```

`coding` is a list, because one concept can carry the same meaning in SNOMED and
in ICD-10. That is how a mapping is recorded, not by overwriting. Keep `text`
even when you have a perfect code: a mapping can be wrong and the text is the
evidence. No code at all? Send text only. That is valid, and it is an honest
signal to whoever gets your data next.

### Choosing a value[x]

| Your data | Use | Why |
|---|---|---|
| a number with a unit | `valueQuantity` | comparable and computable; UCUM in `Quantity.code` |
| a number with no unit | `valueQuantity` | omit `unit` rather than inventing one |
| a coded result | `valueCodeableConcept` | positive / negative / not detected |
| free text | `valueString` | last resort; nothing downstream can use it |
| several parts at once | `component[]` | systolic and diastolic belong in one Observation |

`unit` is for humans. `code` is the UCUM symbol a machine converts with. Rows
with an empty `UNITS` in `observations.csv` are exactly the ones that must not
become a `valueQuantity` — that is the answer to Lab 1 Checkpoint 1 question 4.

### Validate before the network

A local check costs milliseconds; a round trip costs a second. Build every
resource inside a `try`, and **collect the failures with their source key**.

```python
good, bad = [], []
for _, row in patients.iterrows():
    try:
        good.append(to_patient(row))
    except ValidationError as e:
        bad.append((row["Id"], e.errors()[0]["msg"]))
```

Do not let one bad row stop the run, and do not drop rows silently. The
rejection table is a deliverable in its own right: it tells a data owner exactly
which of their records cannot be represented. Submitting one earns marks.

### Errors you are about to see

| Message | What it means |
|---|---|
| `field required: status` | Observation, Condition and Encounter all require one |
| `value is not a valid date` | a `NaT`, or a timestamp where FHIR wants a date |
| `unexpected value; permitted: 'male'...` | gender is bound to a required value set; `M` is not in it |
| `Extra inputs are not permitted: class` | `class` is reserved in Python; the field is `class_fhir` |
| `none is not an allowed value` | a `NaN` reached a required field |
| `1 validation error for Reference` | a reference is a string like `Patient/123` |

### ✅ Checkpoint 2 `15 min`

1. Write `to_patient`, `to_encounter`, `to_condition` and `to_observation` in
   `src/mapping.py`.
2. Run them over the first 50 patients and everything belonging to them.
3. Collect every validation failure with its source key and message.
4. Report how many resources of each type you built, and how many were rejected
   and why.
5. For observations, report how many became `valueQuantity`,
   `valueCodeableConcept` and `valueString`.

> Fifty patients, not 1,174. You are proving the mapping works, not loading a
> warehouse.

---

## Part C · Write `1:15 – 1:45`

### Ask the server first

`POST {BASE}/Patient/$validate` runs the server's rules without storing
anything, and catches what the library cannot: invariants, bindings, and codes
it cannot resolve. Read the `issue` array. `error` must be fixed; `warning`
means it will be accepted but somebody should look; `information` with
"All OK" is what you want.

### Three ways to put a resource on a server

| Interaction | Request | Result |
|---|---|---|
| create | `POST /Patient` | server assigns an id; run it twice, get two patients |
| update | `PUT /Patient/my-id` | you choose the id; idempotent; not allowed everywhere |
| conditional create | `POST /Patient` + `If-None-Exist` | creates only if the search finds nothing |

Conditional create is what makes a load script re-runnable. Without it, a run
that fails halfway leaves duplicates and the next run adds more.

### One request, one graph

A transaction Bundle solves the reference problem: give each resource a
`urn:uuid:` `fullUrl`, reference it from its children, and the server swaps in
the real ids it assigns. See `examples/bundle-transaction.json`.

* `transaction` is atomic: one bad entry and the whole Bundle is rejected
* `batch` is the same shape with entries applied independently
* POST it to the base URL, not to `/Bundle`

### Find what you wrote

The response gives `status` and `location` per entry. But the check we mark is
the independent one: search by your identifier namespace and confirm the counts.

```python
mine = fc.get_json(f"{BASE}/Patient",
                   params={"identifier": f"{SYSTEM}|", "_count": 100})
print(mine.get("total"))
```

Save the source-key to server-id mapping as `id_map.csv`. **Lab 3 starts from
it.**

### When the server says no

| Status | Usual cause here |
|---|---|
| 400 | malformed JSON, or `Content-Type: application/json` instead of `application/fhir+json` |
| 404 | wrong base URL, or a reference to something not in the Bundle and not on the server |
| 422 | valid JSON, invalid FHIR — read the OperationOutcome, it names the element |
| 412 | a conditional create whose search matched more than one resource |
| 500 | usually yours, occasionally theirs |

Always read the body. `r.status_code` tells you something failed;
`r.json()` tells you what.

### ✅ Checkpoint 3 `12 min`

1. Run `$validate` on one Patient, one Condition and one Observation. Record
   every issue returned.
2. Build a transaction Bundle for five patients and all of their encounters,
   conditions and observations.
3. Use `urn:uuid:` internal references, and `ifNoneExist` on every Patient entry.
4. POST it. Report the status of every entry, and save the source-key to
   server-id mapping.
5. Search by your identifier namespace and confirm the counts match.

> Post the Bundle twice. With `ifNoneExist` the second run creates no duplicate
> patients. Report what you observed.

---

## Wrap `1:45 – 2:00`

### Submit four things

1. `notebooks/lab02.ipynb` — all three checkpoints answered, executed, outputs
   visible, both names in the first cell
2. `src/mapping.py` — your four functions, importable
3. `rejections.csv` — every row that failed, with its source key and the error.
   An empty file with a header is a valid answer if nothing failed
4. `NOTES.md` — ten to twenty lines: which server, your identifier namespace,
   what you could not finish, and one thing about FHIR that surprised you

Then run `python check_submission.py`.

**Deadline: Thursday 22 October, 23:59.**

### Marking, out of 100

| Criterion | Marks | What earns them |
|---|---|---|
| Reading (Checkpoint 1) | 20 | correct counts, paging handled, includes filtered out |
| Mapping (Checkpoint 2) | 30 | four working functions, correct datatypes, sensible value[x] |
| Error handling | 15 | a real rejection table; nothing dropped silently |
| Writing (Checkpoint 3) | 20 | valid transaction Bundle, conditional create, verified by search |
| Notes and honesty | 15 | a clear account of what works, what does not, and why |

Thirty of the hundred marks are not about FHIR. That ratio is deliberate.

### How to lose marks without noticing

* a notebook that does not survive restart-and-run-all
* reporting `len(entry)` as if it were `total`
* `try/except pass` instead of a rejection table
* inventing a UCUM code — worse than no unit at all
* leaving `SYSTEM` as the default, so we cannot find your resources
* one name on a pair submission

### If you finish early

* **Round-trip it.** Read your resources back and reconstruct the CSV rows. What
  survived?
* **Add Provenance.** Who created each resource, and from which source file.
* **Try `$everything`.** `GET Patient/{id}/$everything`. Compare with what you sent.
* **Profile your data.** A StructureDefinition requiring an identifier in your
  namespace, then `$validate` against it.
* **Break it deliberately.** Post an Observation referencing a patient that does
  not exist. Does the server care? Should it?

### Before Lab 3 — Friday 30 October

Keep `id_map.csv` and your count of text-only Conditions. Lab 3 is terminologies
and mapping, and it starts from the resources you created today.

Read: `hl7.org/fhir/terminologies.html`, the SNOMED CT browser at
`browser.ihtsdotools.org` (search one code from your data), and `loinc.org`
(find the code for a serum potassium).
