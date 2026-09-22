# Lab 1 — Foundations

**Friday 2 October 2026 · 2 hours · ungraded (but submitted)**

Environment set up, a real-shaped health dataset loaded, and enough SQL to ask
clinical questions of it. Everything in Labs 2–6 assumes this one works.

## Contents

```
labs/lab01/
├── HANDOUT.md              what to do, in order — start here
├── requirements.txt        Python dependencies
├── gen_dataset.py          how data/ was generated (you do not need to run it)
├── data/                   5 CSVs, Synthea export schema
│   ├── patients.csv          1,174 rows
│   ├── encounters.csv       13,550 rows
│   ├── conditions.csv        3,051 rows
│   ├── observations.csv     50,493 rows
│   └── medications.csv       1,343 rows
├── notebooks/
│   └── lab01.ipynb         the starter notebook you fill in
└── sql/
    ├── schema.sql          four tables, run this as-is
    └── queries.sql         3 worked queries + the ones you write
```

## Setup

```bash
cd labs/lab01
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/lab01.ipynb
```

The first cell of the notebook checks your environment. If it throws, fix that
before anything else.

## Database

PostgreSQL if you have it. **SQLite if you do not** — every query in this lab is
portable between the two, and no query in Labs 2–6 will require Postgres. Do not
lose the session to an installer.

```python
# Postgres
engine = create_engine("postgresql+psycopg://hy489:hy489@localhost:5432/hy489")
# SQLite — zero install
engine = create_engine("sqlite:///../lab01.db")
```

## Submission

The notebook, `sql/queries.sql`, and a five-line README of your own.
**Deadline: Thursday 8 October, 23:59.** Ungraded — submit it anyway.

## About the data

Synthetic, generated with `gen_dataset.py` (seeded, so it is reproducible).
It keeps the Synthea column names, including `SSN`, `DRIVERS`, `PASSPORT`,
`LAT` and `LON` — those columns are there on purpose. Look at them, and note
what would have to happen before a file like this could leave a hospital.
