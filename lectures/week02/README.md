# Week 2 — Hands-on: health information systems

**Monday 28 and Wednesday 30 September 2026 · in class · not graded**

Two segments, one on each day.

* **Hands-on A (Monday)** — build the mini-EHR: six tables, load one patient's
  encounter, and write the three queries that matter clinically.
* **Hands-on B (Wednesday)** — parse a real HL7 v2 lab result and load it into
  the schema from Monday.

Nothing here is submitted. Lab 1 on 2 October is the graded-adjacent version.

## Contents

```
week02/
├── sql/
│   ├── schema.sql      six tables, portable Postgres/SQLite
│   ├── seed.sql        Maria's encounter, as rows
│   └── queries.sql     the three clinical queries + mini-lab A stubs
└── hl7/
    ├── sample_oru.hl7               the message from the slide
    ├── sample_oru_corrected.hl7     the same result, corrected to 231
    ├── sample_oru_full_panel.hl7    five OBX segments, including a text result
    └── parse_hl7.py                 the parser from the slide, plus the MSH fix
```

## Running it

**Hands-on A**, SQLite, no install:

```bash
cd sql
sqlite3 week02.db < schema.sql
sqlite3 week02.db < seed.sql
sqlite3 week02.db < queries.sql
```

PostgreSQL works the same way with `psql -d hy489 -f schema.sql`. The schema is
portable; only the turnaround-time query differs between the two, and the
query file says so where it matters.

**Hands-on B**, Python, no dependencies:

```bash
cd hl7
python3 parse_hl7.py sample_oru.hl7
python3 parse_hl7.py sample_oru_full_panel.hl7
```

Mini-lab B then asks you to write the loader yourself: parse two messages, insert
the first result, and apply the second as a correction that supersedes it rather
than overwriting it. When it works, the current view shows cholesterol 231 and
the history still holds the 215 that was acted upon. That pair of numbers is the
whole lesson of Week 2.

## What the code is for

Three columns in `schema.sql` would be missing from a naive student schema, and
each one is in the mini-lab for a reason:

| Column | Why it exists |
|---|---|
| `observation.order_id` | Provenance. A potassium result means something different from the ED than from a routine outpatient draw |
| `effective_ts` / `recorded_ts` | Valid time and transaction time. In the seed data they are 49 hours apart, which is normal |
| `status` + `supersedes` | A corrected result does not overwrite the original. The wrong value was acted upon, so the record of it must survive |

`parse_hl7.py` carries two authentic traps:

* **The MSH off-by-one.** In MSH the field separator itself is MSH-1, so every
  MSH field is shifted by one after a naive split. `msh_field()` handles it.
* **PV1-19 is not always at index 19.** Senders emit one pipe too few or too
  many in the run of empty fields. `visit_number()` tries the spec position and
  falls back to the last non-empty field. This is the optionality problem from
  Part 4, as four lines of code.
