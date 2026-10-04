"""One row per instance, and the three levels above it.

TWO STUBS IN THIS FILE: index_instance and build. Everything else is written
for you.

The hierarchy you are rebuilding is the one from Week 4:

    Patient  ->  Study  ->  Series  ->  Instance

None of it is in the folder names. All of it is in four UIDs and a handful of
attributes, which is why an archive can be reorganised on disk, copied between
systems and renamed by a migration script without losing its structure, and
also why a single mistyped PatientID survives every one of those moves.
"""

import pandas as pd

from . import dicomio

#: The columns of the instance table. Keep this order: the notebook prints it.
INSTANCE_FIELDS = [
    "path",
    "patient_id", "patient_name", "patient_birth", "patient_sex",
    "study_uid", "study_id", "study_date", "study_description", "accession",
    "series_uid", "series_number", "series_description", "modality",
    "body_part",
    "sop_uid", "sop_class", "instance_number", "image_type",
    "rows", "columns", "photometric", "bits_allocated", "pixel_representation",
    "rescale_slope", "rescale_intercept",
    "pixel_spacing_row", "pixel_spacing_col",
    "slice_thickness", "spacing_between_slices", "position_z",
    "burned_in", "institution", "station",
]


def index_instance(ds, path, root):
    """STUB 1. Turn one dataset into one dict with the INSTANCE_FIELDS keys.

    Use dicomio.tag(ds, "SomeTag") for every read. Do not use ds.SomeTag: half
    the tags you want are absent from at least one file in this archive, and
    the first AttributeError will cost you ten minutes.

    Three that need a decision rather than a lookup:

      pixel_spacing_row, pixel_spacing_col
          PixelSpacing has VM 2 and comes back as a tuple (row, column), in
          that order, in millimetres. It is absent on several series here.

      position_z
          ImagePositionPatient has VM 3, (x, y, z) in millimetres, and z is the
          one that orders a stack. Absent on anything that is not a slice.

      image_type
          ImageType has VM 2 to n and comes back as a tuple. Keep it: the
          difference between ("ORIGINAL", "PRIMARY", "AXIAL") and
          ("DERIVED", "SECONDARY", "AXIAL") is the difference between an image
          the scanner produced and one somebody made later, and one of the
          findings in Part A turns on it.

      path
          dicomio.relname(path, root), not the absolute path. Your report has
          to be readable by somebody who put the archive somewhere else.
    """
    raise NotImplementedError("Lab 4, Part A, task 2")


def build(root):
    """STUB 2. Walk the archive and index everything that is an instance.

    Returns (rows, failures):
        rows      list of dicts from index_instance
        failures  list of (relative path, reason) for everything that did not
                  read, using the reason dicomio.read_header gave you

    A file that is not DICOM is a failure with the reason "not DICOM", and in
    this archive that is not a mistake by anybody: see what it is before you
    write it up as one.
    """
    raise NotImplementedError("Lab 4, Part A, task 3")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def to_frame(rows):
    """The instance table, with the columns in INSTANCE_FIELDS order."""
    df = pd.DataFrame(rows)
    for col in INSTANCE_FIELDS:
        if col not in df.columns:
            df[col] = None
    return df[INSTANCE_FIELDS]


def patients(df):
    """One row per distinct PatientID, with what the archive says about them."""
    g = df.groupby("patient_id", dropna=False)
    out = pd.DataFrame({
        "names": g["patient_name"].agg(lambda s: sorted(set(map(str, s)))),
        "birth_dates": g["patient_birth"].agg(lambda s: sorted(set(map(str, s)))),
        "sexes": g["patient_sex"].agg(lambda s: sorted(set(map(str, s)))),
        "studies": g["study_uid"].nunique(),
        "series": g["series_uid"].nunique(),
        "instances": g.size(),
    })
    return out.sort_index()


def studies(df):
    """One row per study. The counts here are what a PACS worklist shows."""
    g = df.groupby("study_uid", dropna=False)
    out = pd.DataFrame({
        "study_id": g["study_id"].first(),
        "date": g["study_date"].first(),
        "description": g["study_description"].first(),
        "accession": g["accession"].first(),
        "patient_ids": g["patient_id"].agg(lambda s: sorted(set(map(str, s)))),
        "modalities": g["modality"].agg(lambda s: sorted(set(map(str, s)))),
        "series": g["series_uid"].nunique(),
        "instances": g.size(),
    })
    return out.sort_values("date")


def series(df):
    """One row per series, which is the level a radiologist actually opens."""
    g = df.groupby("series_uid", dropna=False)
    out = pd.DataFrame({
        "study_uid": g["study_uid"].first(),
        "number": g["series_number"].first(),
        "modality": g["modality"].first(),
        "description": g["series_description"].first(),
        "instances": g.size(),
        "rows": g["rows"].first(),
        "columns": g["columns"].first(),
    })
    return out.sort_values(["study_uid", "number"])


def summarise(df, failures):
    """The four numbers to write at the top of the Part A report."""
    print("files that read       %5d" % len(df))
    print("files that did not    %5d" % len(failures))
    print("distinct patients     %5d" % df["patient_id"].nunique())
    print("distinct studies      %5d" % df["study_uid"].nunique())
    print("distinct series       %5d" % df["series_uid"].nunique())
    print("distinct instances    %5d" % df["sop_uid"].nunique())
    if len(df) != df["sop_uid"].nunique():
        print()
        print("  %d files and %d instance identifiers. Those should be equal."
              % (len(df), df["sop_uid"].nunique()))
