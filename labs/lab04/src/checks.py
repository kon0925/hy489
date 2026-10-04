"""Twelve things that can be wrong with an archive, and how to find them.

TWO STUBS IN THIS FILE: check_patient_consistency and check_slice_geometry.

A finding here is not an error message. It names the thing, says where it is,
and says what breaks if nobody acts on it. "SliceThickness is 3.0" is not a
finding. "SliceThickness says 3 mm, the slices are 5 mm apart and one gap is
10 mm, so any volume computed from this series is wrong by a factor that
changes down the stack" is a finding, and it is the kind of sentence Part A
asks you for.
"""

import collections

import numpy as np

Finding = collections.namedtuple("Finding", "check severity where detail")

#: Severity is a judgement, not a measurement. These are the ones used here.
#:   blocks   the data cannot be used for its purpose until somebody fixes it
#:   wrong    the data can be used and will give a wrong answer silently
#:   note     real, worth recording, does not by itself invalidate anything
SEVERITIES = ("blocks", "wrong", "note")


def report(findings):
    """Print findings grouped by severity, worst first."""
    by = collections.defaultdict(list)
    for f in findings:
        by[f.severity].append(f)
    total = 0
    for sev in SEVERITIES:
        items = by.get(sev, [])
        if not items:
            continue
        print("%s  (%d)" % (sev.upper(), len(items)))
        for f in items:
            print("  %-26s %s" % (f.check, f.where))
            print("  %-26s %s" % ("", f.detail))
            total += 1
        print()
    print("%d findings" % total)
    return total


# ---------------------------------------------------------------------------
# the stubs
# ---------------------------------------------------------------------------

def check_patient_consistency(df):
    """STUB 3. Does every study belong to exactly one patient?

    Group the instance table by study_uid and look at how many distinct
    patient_id values each study carries. One is correct. More than one means
    instances from two people are sitting under one study identifier, which is
    the single most consequential thing on this list: a report written on that
    study describes two bodies.

    Return a list of Finding. For each study with more than one patient, say
    which study, which patient ids, and how many instances each has. Severity
    "blocks".

    Then do the same thing one level up: a single patient_id that carries more
    than one patient_name, patient_birth or patient_sex. That one is severity
    "note" here, and Part C is where you decide what it means.
    """
    raise NotImplementedError("Lab 4, Part A, task 5")


def check_slice_geometry(df):
    """STUB 4. Do the geometry tags agree with the geometry?

    For every series with three or more instances that have a position_z:

      1. Sort the positions and take the differences between neighbours.
      2. If the differences are not all equal (allow 0.01 mm of float noise),
         the stack has a gap, an overlap or a duplicate. Say which and where.
      3. Compare the observed spacing against SpacingBetweenSlices and against
         SliceThickness. Thickness and spacing are allowed to differ, that is
         what an overlapping or gapped acquisition is, but a reconstruction
         that assumes one is the other is wrong by that ratio.
      4. A difference of exactly zero means two instances at the same place.
         That is a different problem and deserves its own finding.

    Return a list of Finding. Severity "wrong" for a spacing that contradicts
    the tags, "blocks" for two instances at the same position.
    """
    raise NotImplementedError("Lab 4, Part B, task 3")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def check_unreadable(failures):
    out = []
    for path, reason in failures:
        sev = "note" if reason == "not DICOM" else "blocks"
        out.append(Finding("unreadable file", sev, path,
                           "read failed: %s" % reason))
    return out


def check_duplicate_sop(df):
    """One SOPInstanceUID must mean one image, for ever, everywhere."""
    out = []
    counts = df["sop_uid"].value_counts()
    for uid, n in counts[counts > 1].items():
        rows = df[df["sop_uid"] == uid]
        out.append(Finding(
            "duplicate SOPInstanceUID", "blocks",
            ", ".join(rows["path"].tolist()),
            "%d files share %s. A UID identifies one image for all time, so "
            "one of these is not what its header says it is." % (n, uid)))
    return out


def check_photometric(df):
    """MONOCHROME1 means the stored value rises as the image gets darker."""
    out = []
    for _, r in df[df["photometric"] == "MONOCHROME1"].iterrows():
        out.append(Finding(
            "MONOCHROME1", "wrong", r["path"],
            "stored high means display dark. Any viewer that assumes "
            "MONOCHROME2 shows this image inverted, and an inverted chest "
            "radiograph still looks like a chest radiograph."))
    return out


def check_rescale(df):
    """A CT with no RescaleIntercept is not a CT in Hounsfield units."""
    out = []
    ct = df[df["modality"] == "CT"]
    for suid, g in ct.groupby("series_uid"):
        it = g["image_type"].iloc[0]
        if it is not None and "LOCALIZER" in str(it):
            continue   # a scout is a projection; it is not in Hounsfield units
        missing = g["rescale_intercept"].isna().sum()
        if missing:
            out.append(Finding(
                "no RescaleIntercept", "wrong",
                "series %s (%s), %d of %d instances"
                % (str(suid)[-12:], g["series_description"].iloc[0],
                   missing, len(g)),
                "the standard says treat an absent intercept as 0, so every "
                "value reads about 1024 HU too high and air reads as soft "
                "tissue. Nothing warns you."))
    return out


def check_pixel_spacing(df):
    """No PixelSpacing means no millimetres, so no measurement."""
    out = []
    for suid, g in df.groupby("series_uid"):
        modality = str(g["modality"].iloc[0])
        if modality in ("SR", "SC", "US"):
            continue           # see the note in the handout: these are expected
        if g["pixel_spacing_row"].isna().all():
            out.append(Finding(
                "no PixelSpacing", "blocks",
                "series %s (%s %s)"
                % (str(suid)[-12:], modality, g["series_description"].iloc[0]),
                "nothing in the series says how big a pixel is, so a distance "
                "measured on it is in pixels and cannot be reported in mm."))
    return out


def check_burned_in(df):
    out = []
    for _, r in df[df["burned_in"] == "YES"].iterrows():
        out.append(Finding(
            "burned-in annotation", "note", r["path"],
            "the header says identifiers are drawn into the pixels. Removing "
            "the header tags does not remove these. Lab 5."))
    return out


def check_description_variants(df):
    """The same protocol, spelled by whoever was at the console.

    Two findings come out of this, and the second is the one that matters.

    The first is the easy half: descriptions that differ only in case,
    spacing and punctuation. A three-line normaliser merges those and you can
    show your work.

    The second is the half a normaliser cannot reach. "Chest CT" and
    "CT CHEST W/O CONTRAST" are the same examination and no amount of string
    processing will tell you so, because the information that would settle it
    was never written in that field. It is in Modality and BodyPartExamined,
    which are short, coded and boring, and that is the argument for coded
    fields in one paragraph.
    """
    out = []
    norm = (df["study_description"].astype(str)
            .str.lower().str.replace(r"[^a-z]+", " ", regex=True)
            .str.replace(r"\bwithout\b|\bwo\b|\bw o\b", "wo", regex=True)
            .str.split().apply(lambda t: " ".join(sorted(set(t)))))
    tmp = df.assign(_norm=norm)

    for key, g in tmp.groupby("_norm"):
        variants = sorted(set(g["study_description"].astype(str)))
        if len(variants) > 1:
            out.append(Finding(
                "description, spelling only", "note",
                "%d studies" % g["study_uid"].nunique(),
                "the same text written %d ways: %s. Case and spacing, so a "
                "normaliser fixes it." % (len(variants),
                                          "; ".join(repr(v) for v in variants))))

    ct = tmp[(tmp["modality"] == "CT") & (tmp["body_part"] == "CHEST")]
    if len(ct):
        raw = sorted(set(ct["study_description"].astype(str)))
        normed = sorted(set(ct["_norm"]))
        if len(normed) > 1:
            out.append(Finding(
                "description, meaning", "note",
                "%d studies, Modality=CT and BodyPartExamined=CHEST"
                % ct["study_uid"].nunique(),
                "%d raw descriptions, %d after normalising, and all of them "
                "are the same examination: %s. The free-text field cannot be "
                "reduced any further; the two coded fields already agreed."
                % (len(raw), len(normed), "; ".join(repr(v) for v in raw))))
    return out


def check_pixels_decode(root, df, read_pixels):
    """The header read. That is not the same as the image being there."""
    import os
    out = []
    for _, r in df.iterrows():
        ds, err = read_pixels(os.path.join(root, r["path"]))
        if err is not None:
            out.append(Finding(
                "pixel data will not decode", "blocks", r["path"],
                "the header read without complaint and the image does not "
                "exist: %s. stop_before_pixels hid this." % err))
    return out


def observed_spacing(positions):
    """Neighbour differences of a sorted position list, rounded to 0.01 mm."""
    z = np.sort(np.asarray(sorted(positions), dtype=float))
    return np.round(np.diff(z), 2)
