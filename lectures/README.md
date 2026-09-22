# Lecture materials

Code and data for the hands-on segments of the lectures. Every 4-hour lecture
(Monday and Wednesday, 09:00–11:00) ends in a practical segment; this is what
those segments run on.

None of it is graded. The graded work is in [`../labs/`](../labs/).

| Week | Topic | Hands-on | Folder |
|---|---|---|---|
| 1 | The health-data landscape | Your first health dataset, in pandas | [`week01/`](week01/) |
| 2 | Health information systems | The mini-EHR, and an HL7 v2 parser | [`week02/`](week02/) |
| 3 | Interoperability I: HL7 & FHIR | Read a live FHIR server, then write to it | [`week03/`](week03/) |
| 4 | Interoperability II: imaging & DICOM | pydicom, then DICOMweb against your own archive | [`week04/`](week04/) |
| 5 | Terminologies & ontologies | Look up codes properly, then measure your own data | [`week05/`](week05/) |
| 6 | Common data models: OMOP & ETL | Build a miniature OMOP CDM, then characterise it | [`week06/`](week06/) |
| 7+ | | to follow | |

## Common ground

**The data.** Everything reads the synthetic cohort in
[`../labs/lab01/data/`](../labs/lab01/data/): 1,174 patients with their
encounters, conditions, observations and medications, in the Synthea export
schema. There is no second copy. Clone the whole repository rather than a single
folder.

**Dependencies.** Each week lists its own, and they are deliberately minimal.
Week 1 needs only pandas. Week 6 needs nothing at all beyond the standard
library: it builds its database with the SQLite that ships with Python.

**Servers.** Weeks 3 and 4 talk to a server. In both cases you can run your own
in about a minute, and you should:

```bash
docker run -p 8080:8080 hapiproject/hapi:latest          # FHIR, week 3
docker compose -f week04/docker-compose.yml up -d        # DICOM, week 4
```

Public test servers go down, get wiped, and do not enjoy a lecture theatre
hitting them at once.

**Never send real data anywhere.** Not to a public server, not to your own, not
into a notebook. The synthetic cohort is the only thing that goes on the wire.

## For the teaching team

Demo scripts, worked solutions, expected outputs and the per-week teaching notes
are not in this repository. They are in the teaching folder, which is kept
separately and is not distributed to students.
