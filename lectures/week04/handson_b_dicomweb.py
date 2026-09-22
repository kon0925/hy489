#!/usr/bin/env python3
"""HY-489 Week 4 · Hands-on B — query an archive over DICOMweb.

Everything is HTTP, so a browser, curl or requests all work.

Start an archive first (about a minute, no internet needed after the pull):

    docker compose up -d
    # upload any DICOM file at http://localhost:8042  (orthanc / orthanc)

Then:

    python3 handson_b_dicomweb.py
    python3 handson_b_dicomweb.py --base http://localhost:8042/dicom-web

NEVER upload anything real. Not your own scans, not a friend's, not a study from
a placement. This is a public teaching exercise.
"""
from __future__ import annotations

import argparse
import requests

TIMEOUT = 30
DICOM_JSON = "application/dicom+json"

# DICOM JSON is keyed by eight-character hex tags, not names. Every parser
# needs a small helper like tag(). Write it once and keep it.
TAGS = {
    "StudyInstanceUID":  "0020000D",
    "SeriesInstanceUID": "0020000E",
    "SOPInstanceUID":    "00080018",
    "StudyDate":         "00080020",
    "StudyDescription":  "00081030",
    "SeriesDescription": "0008103E",
    "SeriesNumber":      "00200011",
    "Modality":          "00080060",
    "PatientID":         "00100020",
    "PatientName":       "00100010",
    "NumberOfStudyRelatedInstances": "00201208",
    "NumberOfSeriesRelatedInstances": "00201209",
    "SliceThickness":    "00180050",
    "PixelSpacing":      "00280030",
}


def tag(obj: dict, name: str, default=None):
    """Read a named attribute out of a DICOM JSON object.

    PatientName comes back as {"Alphabetic": "..."} because PN has components,
    so unwrap that case too.
    """
    v = obj.get(TAGS.get(name, name), {}).get("Value")
    if not v:
        return default
    first = v[0]
    if isinstance(first, dict):
        return first.get("Alphabetic", default)
    return first


def get(base: str, path: str, auth, **params):
    r = requests.get(f"{base}/{path}", params=params or None, auth=auth,
                     headers={"Accept": DICOM_JSON}, timeout=TIMEOUT)
    if r.status_code == 204:
        return []                 # QIDO: matched nothing. Not an error.
    r.raise_for_status()
    return r.json()


def main(a) -> None:
    auth = (a.user, a.password) if a.user else None
    print(f"archive: {a.base}\n")

    # ---------------------------------------------------------------- QIDO
    print("--- QIDO-RS: find the studies")
    studies = get(a.base, "studies", auth, limit=50)
    if not studies:
        print("  no studies. Upload one at http://localhost:8042 and re-run.")
        print("  The pydicom example files from Hands-on A will do.")
        return
    for st in studies:
        print(f"  {str(tag(st, 'StudyInstanceUID'))[-16:]:<18}"
              f"{str(tag(st, 'StudyDate', '')):<10}"
              f"{str(tag(st, 'PatientID', '')):<12}"
              f"{str(tag(st, 'StudyDescription', ''))[:34]}")
    print(f"  {len(studies)} studies\n")

    uid = tag(studies[0], "StudyInstanceUID")

    # ---------------------------------------------------------------- series
    print("--- QIDO-RS: go down a level")
    series = get(a.base, f"studies/{uid}/series", auth)
    for se in series:
        print(f"  series {str(tag(se, 'SeriesNumber', '?')):<4}"
              f"{str(tag(se, 'Modality', '')):<5}"
              f"{str(tag(se, 'NumberOfSeriesRelatedInstances', '?')):>6} instances   "
              f"{str(tag(se, 'SeriesDescription', ''))[:38]}")
    print(f"  {len(series)} series in this study\n")
    print("  One study is not one image. A study routinely holds five to fifteen")
    print("  series: localiser, phases, reconstructions, and a dose report.\n")

    suid = tag(series[0], "SeriesInstanceUID")

    # ---------------------------------------------------------------- WADO
    print("--- WADO-RS: metadata only, no pixels crossed the network")
    meta = get(a.base, f"studies/{uid}/series/{suid}/metadata", auth)
    print(f"  {len(meta)} instances")
    if meta:
        m = meta[0]
        print("  first instance:")
        print("    SliceThickness:", tag(m, "SliceThickness", "(absent)"))
        print("    PixelSpacing  :", tag(m, "PixelSpacing", "(absent)"))
    print("  This is the pattern for every archive-scale task: index on metadata,")
    print("  fetch pixels only where you need them.\n")

    # ---------------------------------------------------------------- both routes
    iuid = tag(meta[0], "SOPInstanceUID") if meta else None
    if iuid:
        stem = f"{a.base}/studies/{uid}/series/{suid}/instances/{iuid}"
        rendered = requests.get(f"{stem}/rendered", auth=auth,
                                headers={"Accept": "image/png"}, timeout=TIMEOUT)
        native = requests.get(stem, auth=auth,
                              headers={"Accept": "multipart/related; type=application/dicom"},
                              timeout=TIMEOUT)
        print("--- Two ways to get the same image")
        print(f"  /rendered  {len(rendered.content):>9,} bytes   "
              f"{rendered.headers.get('Content-Type','')}")
        print(f"  native     {len(native.content):>9,} bytes   "
              f"{native.headers.get('Content-Type','')[:40]}")
        print()
        print("  /rendered is convenient and lossy: an 8-bit picture with someone")
        print("  else's window already applied. Fine for a thumbnail, never for")
        print("  analysis. The native route returns a multipart body you unwrap")
        print("  before pydicom can read it.")

    print()
    print("Task 6: send an object back with STOW-RS, then send the same object")
    print("again. The archive will not duplicate it, because a SOPInstanceUID")
    print("identifies the object itself. That is Monday's UID rule, enforced.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8042/dicom-web")
    ap.add_argument("--user", default="orthanc")
    ap.add_argument("--password", default="orthanc")
    args = ap.parse_args()
    try:
        main(args)
    except requests.exceptions.RequestException as e:
        print(f"Could not reach {args.base}\n  {type(e).__name__}: {e}\n")
        print("Start an archive first:")
        print("  docker compose up -d")
        print("  then upload a DICOM file at http://localhost:8042")
        raise SystemExit(1)
