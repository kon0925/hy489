# Lab 2 — FHIR in practice

**Friday 16 October 2026 · 2 hours · Assignment 1**
**Individual. Delivered / not delivered. 3% of the final mark.**
**Deadline: Friday 23 October, 23:59**

Read a live FHIR server, map the Lab 1 tables to FHIR resources, validate them,
and write them back. Lab 3 starts from what you produce here.

## Contents

```
lab02/
├── HANDOUT.md              what to do, in order — start here
├── requirements.txt        requests, fhir.resources, pandas
├── check_submission.py     run this before you submit
├── src/
│   ├── fhirclient.py       written for you: get_json, fetch_all,
│   │                       validate_resource, post_resource, post_bundle
│   └── mapping.py          THE PART YOU DELIVER: four function stubs to fill in
├── examples/               one hand-written example of each resource type
│   ├── patient.json
│   ├── condition.json
│   ├── observation.json         a numeric result
│   ├── observation-text.json    a text result — note it is NOT a valueQuantity
│   └── bundle-transaction.json  three resources, urn:uuid references, ifNoneExist
└── notebooks/
    └── lab02.ipynb         the starter notebook you fill in
```

The data comes from `../lab01/data/`. There is no copy in this folder, so clone
the whole repository rather than just this directory.

## Setup

```bash
cd labs/lab02
source ../lab01/.venv/bin/activate      # Windows: ..\lab01\.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/lab02.ipynb
```

No Lab 1 environment?

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Server

Default is the public HAPI test server:

```python
BASE = "https://hapi.fhir.org/baseR4"
```

If it is slow, down, or wiped mid-session, run your own. It takes about a minute
and has no rate limits:

```bash
docker run -p 8080:8080 hapiproject/hapi:latest
# then: BASE = "http://localhost:8080/fhir"
```

The lab is marked on your code, not on which server you reached.

## Ground rules for the public server

1. **Never post anything real.** Not your own data, not a friend's, not an
   extract from a placement. The synthetic dataset in `labs/lab01/data` is the only
   thing you post.
2. Everything you write is public and anyone can delete it.
3. Put your student number in `SYSTEM` in `src/mapping.py`. Without a unique
   identifier namespace you cannot find your own resources, and neither can we.
4. Sequential requests, always with a timeout, no loops that POST a thousand
   resources one at a time. Use a transaction Bundle.

## What you deliver

Four files, by **Friday 23 October, 23:59**: the executed notebook,
`src/mapping.py`, `rejections.csv` and `NOTES.md`. Run
`python check_submission.py` first. Every failure it prints is a reason the work
would come back to you.

There is no mark out of 100. The assignment is delivered or it is not, and this
is what a delivery contains:

| Part | What has to be there |
|---|---|
| Reading (Checkpoint 1) | correct counts, paging handled, includes filtered out |
| Mapping (Checkpoint 2) | four working functions, correct datatypes, sensible `value[x]` |
| Error handling | a real rejection table, nothing dropped silently |
| Writing (Checkpoint 3) | a valid transaction Bundle, conditional create, verified by search |
| Notes and honesty | a clear account of what works, what does not, and why |

Two of those five rows are not about FHIR at all. That is on purpose: a pipeline
that reports what it could not process is the thing being asked for, and one that
quietly processes less is not a delivery.
