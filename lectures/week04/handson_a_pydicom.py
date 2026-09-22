#!/usr/bin/env python3
"""HY-489 Week 4 · Hands-on A — open a real study with pydicom.

Everything here is standard Python. Nothing needs a hospital.

    python3 handson_a_pydicom.py                  # uses pydicom's bundled example
    python3 handson_a_pydicom.py path/to/study/   # a folder of .dcm files
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pydicom
from pydicom import dcmread


# ---------------------------------------------------------------------------
# 1. First look
# ---------------------------------------------------------------------------

def first_look(ds) -> None:
    """Printing the whole dataset is the fastest way to understand any DICOM
    object you have never seen. Here we pull out the attributes that matter."""
    print("--- 1. First look")
    print("  SOP class     :", ds.file_meta.get("MediaStorageSOPClassUID", "?"))
    print("  transfer syntax:", ds.file_meta.get("TransferSyntaxUID", "?"))
    print("  modality      :", ds.get("Modality"))
    print("  manufacturer  :", ds.get("Manufacturer"))
    print("  kVp           :", ds.get("KVP"))
    print("  rows x cols   :", ds.get("Rows"), "x", ds.get("Columns"))
    print("  pixel spacing :", ds.get("PixelSpacing"))
    print("  slice thickness:", ds.get("SliceThickness"))

    # Use .get() for anything that is not type 1. Conditional and optional
    # attributes are missing constantly in real data, and a pipeline that
    # assumes presence crashes on the third study rather than the first.
    print("  contrast agent:", ds.get("ContrastBolusAgent", "(absent)"))
    print()


# ---------------------------------------------------------------------------
# 2. Geometry
# ---------------------------------------------------------------------------

def geometry(ds) -> None:
    print("--- 2. Geometry")
    ipp = ds.get("ImagePositionPatient")
    iop = ds.get("ImageOrientationPatient")
    print("  ImagePositionPatient   :", ipp, " <- x,y,z of the first voxel, in mm")
    print("  ImageOrientationPatient:", iop, " <- direction cosines of row and column")
    print("  FrameOfReferenceUID    :", ds.get("FrameOfReferenceUID", "(absent)"))
    print()
    print("  DICOM axes are the patient's anatomy, not the scanner or the screen:")
    print("    +X = Left   +Y = Posterior   +Z = Superior   (this is LPS)")
    print("  Most neuroimaging research software uses RAS instead. The first two")
    print("  axes are flipped. Convert without handling it and left and right swap.")
    print()


# ---------------------------------------------------------------------------
# 3. The pixels, done properly
# ---------------------------------------------------------------------------

def pixels(ds) -> None:
    print("--- 3. Getting the pixels right")
    try:
        raw = ds.pixel_array
    except Exception as e:                                    # noqa: BLE001
        print(f"  cannot decode pixel data: {type(e).__name__}: {e}")
        print("  This is almost always a missing decoder for a compressed")
        print("  transfer syntax. Install pylibjpeg and pylibjpeg-libjpeg.")
        print()
        return

    print(f"  raw dtype {raw.dtype}, min {raw.min()}, max {raw.max()}")
    print("  These are STORED values. They are not Hounsfield units.")

    slope = float(ds.get("RescaleSlope", 1))
    intercept = float(ds.get("RescaleIntercept", 0))
    print(f"  RescaleSlope {slope}, RescaleIntercept {intercept}")

    if ds.get("Modality") == "CT":
        try:
            from pydicom.pixels import apply_modality_lut
        except ImportError:                                   # pydicom < 3
            from pydicom.pixel_data_handlers.util import apply_modality_lut
        hu = apply_modality_lut(raw, ds)
        print(f"  after modality LUT: min {hu.min():.0f}, max {hu.max():.0f} HU")
        print("  A minimum near -1000 is air, which is why PixelRepresentation")
        print(f"  is signed. This file says PixelRepresentation = {ds.get('PixelRepresentation')}")

        # windowing is display, not data. The file always holds the full range.
        for name, centre, width in [("lung", -600, 1500), ("soft tissue", 50, 400),
                                    ("bone", 500, 2000)]:
            lo, hi = centre - width / 2, centre + width / 2
            inside = np.mean((hu >= lo) & (hu <= hi))
            print(f"    {name:<12} window [{lo:>6.0f},{hi:>6.0f}]  "
                  f"{inside:6.1%} of voxels visible")
        print("  Same pixels, three different images. Windowing never changes the file.")
    print()


# ---------------------------------------------------------------------------
# 4. Where identity hides
# ---------------------------------------------------------------------------

IDENTIFYING = [
    "PatientName", "PatientID", "PatientBirthDate", "PatientAddress",
    "PatientTelephoneNumbers", "OtherPatientIDs", "AccessionNumber",
    "InstitutionName", "InstitutionAddress", "ReferringPhysicianName",
    "PerformingPhysicianName", "OperatorsName", "StudyDescription",
    "SeriesDescription", "StudyDate", "StudyTime",
]


def identifiers(ds) -> None:
    print("--- 4. Hunt for identifiers")
    found = [(k, ds.get(k)) for k in IDENTIFYING if k in ds and str(ds.get(k)).strip()]
    for k, v in found:
        print(f"  {k:<26}{v}")
    print(f"  {len(found)} identifying attributes present in this one object.")
    priv = [e for e in ds if e.tag.group % 2 == 1]
    print(f"  plus {len(priv)} private-tag elements, which are undocumented and")
    print("  have been observed to contain names and accession numbers.")
    print("  This is the whole exercise in Lab 5, on 27 November.")
    print()


# ---------------------------------------------------------------------------
# 5. Turn a folder into a study index
# ---------------------------------------------------------------------------

def index_folder(folder: Path) -> None:
    """The most useful thing you will write this week.

    stop_before_pixels=True is the difference between indexing a thousand slices
    in two seconds and in four minutes. Read headers first, decode pixels only
    for the series you actually want.
    """
    print(f"--- 5. Indexing {folder}")
    try:
        import pandas as pd
    except ImportError:
        print("  pandas not installed; skipping")
        return

    rows = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        try:
            ds = dcmread(f, stop_before_pixels=True)
        except Exception:                                     # noqa: BLE001
            continue                      # not DICOM, or unreadable. Skip quietly.
        rows.append({
            "series": str(ds.get("SeriesInstanceUID", ""))[-12:],
            "n": ds.get("SeriesNumber"),
            "desc": ds.get("SeriesDescription", ""),
            "mod": ds.get("Modality", ""),
            "thick": ds.get("SliceThickness"),
            "sop": str(ds.get("SOPInstanceUID", ""))[-8:],
        })

    if not rows:
        print("  no DICOM files found")
        return
    df = pd.DataFrame(rows)
    print(df.groupby(["n", "desc", "mod"], dropna=False).size().to_string())
    print()
    print(f"  {len(df)} instances in {df['series'].nunique()} series.")
    print("  A study is not one image. A stroke protocol CT is seven series and")
    print("  over two thousand instances, including a dose report that is not")
    print("  an image at all.")


# ---------------------------------------------------------------------------

def main(arg: str | None) -> None:
    if arg:
        path = Path(arg)
        if path.is_dir():
            files = [f for f in sorted(path.rglob("*")) if f.is_file()]
            ds = dcmread(files[0])
            print(f"study folder: {path}\n")
        else:
            ds = dcmread(path)
            print(f"file: {path}\n")
    else:
        # pydicom ships test data. No download, no login, no PHI.
        try:
            from pydicom import examples
            ds = examples.ct
        except ImportError:                                   # pydicom < 3
            from pydicom.data import get_testdata_file
            ds = dcmread(get_testdata_file("CT_small.dcm"))
        path = None
        print("using pydicom's bundled example CT\n")

    first_look(ds)
    geometry(ds)
    pixels(ds)
    identifiers(ds)
    if arg and Path(arg).is_dir():
        index_folder(Path(arg))
    else:
        print("--- 5. Indexing")
        print("  Pass a folder of DICOM files to see the study index:")
        print("    python3 handson_a_pydicom.py path/to/study/")
        print("  The Cancer Imaging Archive publishes full de-identified studies.")


if __name__ == "__main__":
    print(f"pydicom {pydicom.__version__}\n")
    main(sys.argv[1] if len(sys.argv) > 1 else None)
