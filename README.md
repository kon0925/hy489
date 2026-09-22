# HY-489 · Health Data Management

Undergraduate elective, Computer Science Department, University of Crete.
**Autumn semester 2026-27.**

Everything the hands-on parts of the course run on. Lecture slides are
distributed separately through the course page.

| | |
|---|---|
| **Lectures** | Monday & Wednesday, 09:00–11:00 |
| **Labs** | Friday, alternating weeks (see the schedule below) |
| **First lecture** | Monday 21 September 2026 |
| **Course page** | https://www.csd.uoc.gr/CSD/index.jsp?content=courses_catalog_new&lang=en&course=281 |

## Two folders

```
hy489/
├── labs/         the six graded lab sessions, one folder each
│   └── lab01/
│       └── data/     the synthetic cohort. One copy, used by everything
└── lectures/     the hands-on segment of each lecture, one folder per week
```

**[`labs/`](labs/)** is where the assessed work is. Each lab folder holds its
handout, its notebook and its starter code, and is self-contained apart from the
dataset.

**[`lectures/`](lectures/)** is what the live segments run on. None of it is
graded and nothing there is submitted.

The dataset lives in [`labs/lab01/data/`](labs/lab01/data/) and there is exactly
one copy. Every lab and every lecture script reads it from there, so clone the
whole repository rather than a single folder.

## Labs

| | Lab | Date | Graded | Folder |
|---|---|---|---|---|
| 1 | Foundations: environment, a real dataset, SQL refresher | Fri 2 Oct | no | [`labs/lab01/`](labs/lab01/) |
| 2 | FHIR in practice: read, map, validate, write | Fri 16 Oct | yes | [`labs/lab02/`](labs/lab02/) |
| 3 | Terminologies and mapping | Fri 30 Oct | yes | [`labs/lab03/`](labs/lab03/) |
| 4 | Imaging and DICOM | Fri 13 Nov | yes | `labs/lab04/` *(to follow)* |
| 5 | De-identification and privacy | Fri 27 Nov | yes | `labs/lab05/` *(to follow)* |
| 6 | Analytics on a common data model | Fri 11 Dec | yes | `labs/lab06/` *(to follow)* |

## Lectures

| Week | Topic | Hands-on | Folder |
|---|---|---|---|
| 1 | The health-data landscape | Your first health dataset, in pandas | [`lectures/week01/`](lectures/week01/) |
| 2 | Health information systems | The mini-EHR, and an HL7 v2 parser | [`lectures/week02/`](lectures/week02/) |
| 3 | Interoperability I: HL7 & FHIR | Read a live FHIR server, then write to it | [`lectures/week03/`](lectures/week03/) |
| 4 | Interoperability II: imaging & DICOM | pydicom, then DICOMweb | [`lectures/week04/`](lectures/week04/) |
| 5 | Terminologies & ontologies | Look up codes properly, then measure your own data | [`lectures/week05/`](lectures/week05/) |
| 6 | Common data models: OMOP & ETL | Build a miniature OMOP CDM, then characterise it | [`lectures/week06/`](lectures/week06/) |

## Getting started

```bash
git clone https://github.com/kon0925/hy489.git
cd hy489/labs/lab01
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then open `notebooks/lab01.ipynb` and read `HANDOUT.md`. Before each session,
`git pull` from the top of the repository.

## What is not here

Worked solutions, answer keys and the running notes for the teaching team are
kept outside this repository and are not published. If you have found a file
here that looks like an answer key, it is a mistake: please tell the instructor.

## A note on the data

All datasets in this repository are **synthetic**. They are generated to have the
shape, messiness and identifier structure of real clinical extracts, but no row
describes a real person.

Never put real patient data in this repository, in a notebook, or on any public
server used in this course, including the public FHIR test servers in Lab 2.

## Licence

Code and teaching materials: [MIT](LICENSE).
