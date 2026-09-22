# Week 4 — Hands-on: medical imaging & DICOM

**Monday 12 and Wednesday 14 October 2026 · in class · not graded**

* **Hands-on A (Monday)** — open a real DICOM study with pydicom.
* **Hands-on B (Wednesday)** — query an archive over DICOMweb.

Lab 4 on 13 November is the graded imaging lab and assumes Orthanc is running.
Students who set it up in October have an easy lab; the rest spend the first
twenty minutes on Docker.

## Contents

```
week04/
├── handson_a_pydicom.py    read tags, geometry, pixels, identifiers, index a folder
├── handson_b_dicomweb.py   QIDO-RS, WADO-RS, and the rendered-vs-native comparison
├── docker-compose.yml      Orthanc: your own archive, DICOMweb and DIMSE
└── requirements.txt
```

## Hands-on A

```bash
pip install -r requirements.txt
python3 handson_a_pydicom.py
```

With no argument it uses the CT that ships with pydicom, so there is no
download, no login and no PHI. Pass a folder to index a real study:

```bash
python3 handson_a_pydicom.py path/to/study/
```

The Cancer Imaging Archive publishes full de-identified collections if you want
something bigger.

**`pylibjpeg` matters.** Without a decoder, any compressed transfer syntax
raises the moment you touch `pixel_array`. That is the single most common
support question in the imaging lab, and it is in `requirements.txt` for that
reason.

## Hands-on B

```bash
docker compose up -d
# upload a DICOM file at http://localhost:8042   (orthanc / orthanc)
python3 handson_b_dicomweb.py
```

Run your own archive rather than a public demo server. Public servers go down,
get wiped, and do not enjoy twenty laptops hitting them during a lecture. Orthanc
is one container, speaks both DIMSE and DICOMweb, and has a usable web interface.

**Never upload anything real.** Not your own scans, not a friend's, not a study
from a placement.

## What the scripts demonstrate

`handson_a_pydicom.py` prints, for the bundled example CT:

| Output | The point |
|---|---|
| raw min 128, max 2191 | These are **stored values**, not Hounsfield units |
| after modality LUT: -896 to 1167 HU | `RescaleSlope` and `RescaleIntercept` applied. The minimum is air |
| `PixelRepresentation = 1` | Signed, because air is negative. Read it as unsigned and the lungs go white |
| three windows, three visible fractions | Windowing is display, not data. The file always holds the full range |
| six identifying attributes in one object | Name, ID, institution, study description, dates. Before the pixels are even considered |

`handson_b_dicomweb.py` walks study to series to metadata to pixels, and ends by
fetching the same image twice, once through `/rendered` and once natively, so the
size difference makes the argument: `/rendered` is an 8-bit picture with someone
else's window baked in. Fine for a thumbnail, never for analysis.
