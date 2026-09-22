# Labs

Six TA-led sessions, Fridays, alternating weeks, two hours each. Five of the six
are graded and together they are 25% of the final mark.

| | Lab | Date | Graded | Deadline | Folder |
|---|---|---|---|---|---|
| 1 | Foundations: environment, a real dataset, SQL refresher | Fri 2 Oct | no | — | [`lab01/`](lab01/) |
| 2 | FHIR in practice: read, map, validate, write | Fri 16 Oct | yes | Thu 22 Oct | [`lab02/`](lab02/) |
| 3 | Terminologies and mapping | Fri 30 Oct | yes | Thu 5 Nov | [`lab03/`](lab03/) |
| 4 | Imaging and DICOM | Fri 13 Nov | yes | | `lab04/` *(to follow)* |
| 5 | De-identification and privacy | Fri 27 Nov | yes | | `lab05/` *(to follow)* |
| 6 | Analytics on a common data model | Fri 11 Dec | yes | | `lab06/` *(to follow)* |

Each folder has a `HANDOUT.md`, which is the one to read first, and a `README.md`
describing what is in the folder and how to set it up.

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

## Submitting

Each graded lab says in its handout exactly what to submit and how to name it.
`lab02/check_submission.py` is the pattern later labs follow: run it before you
submit and it catches the things that cost marks for no reason.

## Never send real data anywhere

Not your own, not a friend's, not an extract from a placement. The synthetic
cohort is the only thing that goes into a notebook, onto a public FHIR or DICOM
server, or into this repository.
