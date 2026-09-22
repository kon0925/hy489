# HY-489 · Health Data Management

Undergraduate elective, Computer Science Department, University of Crete.
**Autumn semester 2026-27.**

Lecture and lab materials for the hands-on parts of the course. Lecture slides are
distributed separately through the course page.

| | |
|---|---|
| **Lectures** | Monday & Wednesday, 09:00–11:00 |
| **Labs** | Friday, alternating weeks (see the schedule below) |
| **First lecture** | Monday 21 September 2026 |
| **Course page** | https://www.csd.uoc.gr/CSD/index.jsp?content=courses_catalog_new&lang=en&course=281 |

## Labs

Each lab lives in its own subfolder with its data, notebooks, SQL and handout.

| | Lab | Date | Graded | Folder |
|---|---|---|---|---|
| 1 | Foundations — environment, a real dataset, SQL refresher | Fri 2 Oct | no | [`lab01/`](lab01/) |
| 2 | FHIR in practice — read, map, validate, write | Fri 16 Oct | yes | [`lab02/`](lab02/) |
| 3 | Terminologies and mapping | Fri 30 Oct | yes | `lab03/` *(to follow)* |
| 4 | Imaging and DICOM | Fri 13 Nov | yes | `lab04/` *(to follow)* |
| 5 | De-identification and privacy | Fri 27 Nov | yes | `lab05/` *(to follow)* |
| 6 | Analytics on a common data model | Fri 11 Dec | yes | `lab06/` *(to follow)* |

Each lab folder is self-contained: you can clone once at the start of term and
`git pull` before each session.

## Lectures

Code for the hands-on segment of each lecture lives in [`lectures/`](lectures/).
None of it is graded; it is what the live segments run on, plus the instructor
scripts and solutions.

| Week | Topic | Hands-on | Folder |
|---|---|---|---|
| 1 | The health-data landscape | Your first health dataset, in pandas | [`lectures/week01/`](lectures/week01/) |
| 2 | Health information systems | The mini-EHR, and an HL7 v2 parser | [`lectures/week02/`](lectures/week02/) |
| 3 | Interoperability I: HL7 & FHIR | Read a live FHIR server, then write to it | [`lectures/week03/`](lectures/week03/) |
| 4 | Interoperability II: imaging & DICOM | pydicom, then DICOMweb | [`lectures/week04/`](lectures/week04/) |

## Getting started

```bash
git clone https://github.com/kon0925/hy489.git
cd hy489/lab01
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then open `notebooks/lab01.ipynb` and read `HANDOUT.md`.

## A note on the data

All datasets in this repository are **synthetic**. They are generated to have the
shape, messiness and identifier structure of real clinical extracts, but no row
describes a real person.

Never put real patient data in this repository, in a notebook, or on any public
server used in this course — including the public FHIR test servers in Lab 2.

## Licence

Code and teaching materials: [MIT](LICENSE).
