"""Build the Lab 4 imaging archive.

HY-489, Lab 4. You do not have to run this. It is here so that every defect in
the archive is auditable: if you think the archive is wrong, this file is where
you check.

The archive is synthetic. No part of it comes from a person. The patients are
taken from the Lab 1 cohort, which is itself a Synthea export, so the names,
birth dates and identifiers in the DICOM headers match the CSVs you have been
reading since Week 1. That is the point: Part C asks you to reconcile the two,
and reconciliation is only interesting when it almost works.

Determinism
-----------
Seeded with 489, the same seed as the Lab 1 and Lab 3 generators. Every student
gets byte-identical files. UIDs are derived from a hash of a label and not
drawn at random, so a rerun produces the same UIDs as well.

UIDs sit under the 2.25 arc. That arc is the UUID branch of the OID tree: any
UUID can be written as 2.25.<the UUID as a single decimal integer> and needs no
registration from anybody. A hospital that generates its own UIDs either does
this or registers a root of its own. Nothing here uses a root belonging to a
real organisation.

The thirteen planted defects
----------------------------
Each one is in the archive on purpose, each one happens in real departments, and
each one is a line you will write in the Part A report.

 1. MERGED STUDY. Four instances of the abdominal CT carry a different
    PatientID and PatientName from the rest of the study. A patient was
    selected on the console and not re-selected for the second series.
 2. DUPLICATE SOPInstanceUID. Two files in the chest follow-up carry the same
    SOPInstanceUID and different pixel data. Sent twice, modified in between.
    The instance count is right and one image is not what the header says.
 3. MONOCHROME1. The chest radiograph is stored inverted. Display it with the
    assumption everybody makes and the lungs are white.
 4. MISSING RescaleIntercept. One CT series has RescaleSlope and no intercept.
    Treat the absent tag as zero, which is what the standard says, and every
    number is 1024 too high. Air reads as 24 HU instead of -1000.
 5. NON-UNIFORM SPACING. The second chest CT skips a slice in the middle.
    ImagePositionPatient is honest about it; SliceThickness and
    SpacingBetweenSlices are not.
 6. NO PixelSpacing. The MR series has none. A distance measured on it is in
    pixels and cannot be converted into millimetres.
 7. FREE-TEXT DESCRIPTIONS. The same chest protocol is called four different
    things across four studies. Group by StudyDescription and you get four
    protocols; group by anything structured and you get one.
 8. BURNED-IN ANNOTATION. The secondary capture has the patient's name drawn
    into the pixels and says so: BurnedInAnnotation is YES. Lab 5 removes it.
    Lab 4 only has to find it.
 9. TRUNCATED FILE. One file is cut off mid-pixel-data. A walker that does not
    catch the exception stops at file 47 of 91.
10. STRAY NON-DICOM FILE. A text file sits in the tree. Anything that assumes
    every file under the root is an instance will crash on it.
11. OUTSIDE REFERRAL. One study belongs to a patient who is not in the Lab 1
    cohort at all. It is not an error and it must not be forced to match.
12. HEADER DISAGREEMENTS WITH THE CSV. For one patient the DICOM sex
    contradicts the cohort, and for another the surname is spelled
    differently. Both are real, both are common, and they are the reason
    Part C asks for a decision and not a number.
13. HEADER DISAGREEMENT WITH ITSELF. One PatientID carries two spellings of
    the name across two studies, one of them with a middle initial. The
    archive is inconsistent about a patient before anybody compares it to
    anything else.

Written with pydicom 3.0. Reading the output needs nothing newer than 2.3.
"""

import csv
import hashlib
import os
import random
import shutil
import sys
from datetime import date, datetime, timedelta

import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, UID

SEED = 489
HERE = os.path.dirname(os.path.abspath(__file__))
COHORT = os.path.join(HERE, "..", "lab01", "data", "patients.csv")
OUT = os.path.join(HERE, "data", "archive")

CT_SOP = "1.2.840.10008.5.1.4.1.1.2"
CR_SOP = "1.2.840.10008.5.1.4.1.1.1"
MR_SOP = "1.2.840.10008.5.1.4.1.1.4"
US_SOP = "1.2.840.10008.5.1.4.1.1.6.1"
SC_SOP = "1.2.840.10008.5.1.4.1.1.7"
SR_SOP = "1.2.840.10008.5.1.4.1.1.88.11"


def uid(label):
    """A deterministic UID under the 2.25 (UUID) arc.

    2.25.<integer> is the one arc anybody may use without registering: the
    integer is a UUID written in decimal. Here the integer comes from a hash of
    the label instead of a random UUID, so that the archive is reproducible.
    """
    h = hashlib.sha256(("hy489:" + label).encode()).hexdigest()
    n = int(h, 16) % (10 ** 36)
    return UID("2.25.%d" % n)


# ----------------------------------------------------------------------------
# phantoms
# ----------------------------------------------------------------------------

def ct_chest(n, size=128, rng=None):
    """A stack of chest-shaped slices in Hounsfield units.

    Air -1000, soft tissue around 40, lung around -800, bone around 400. The
    numbers matter: Part B asks you to measure them back out, and they only
    come back out if the rescale is applied correctly.
    """
    out = []
    yy, xx = np.mgrid[0:size, 0:size]
    cy = cx = size / 2.0
    for k in range(n):
        img = np.full((size, size), -1000.0)
        # body: an ellipse that tapers at the top and bottom of the stack
        taper = 1.0 - 0.25 * abs(k - (n - 1) / 2.0) / max((n - 1) / 2.0, 1)
        a, b = 0.40 * size * taper, 0.30 * size * taper
        body = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1
        img[body] = 40.0
        # two lungs
        for sgn in (-1, 1):
            la, lb = 0.15 * size * taper, 0.19 * size * taper
            lcx = cx + sgn * 0.17 * size
            lung = ((xx - lcx) / la) ** 2 + ((yy - cy) / lb) ** 2 <= 1
            img[lung & body] = -800.0
        # spine, posterior
        sp = (xx - cx) ** 2 + (yy - (cy + 0.22 * size)) ** 2 <= (0.07 * size) ** 2
        img[sp & body] = 400.0
        if rng is not None:
            img = img + rng.normal(0, 12.0, img.shape)
        out.append(img)
    return out


def mr_brain(n, size=128, rng=None):
    out = []
    yy, xx = np.mgrid[0:size, 0:size]
    cy = cx = size / 2.0
    for k in range(n):
        img = np.zeros((size, size))
        taper = 1.0 - 0.35 * abs(k - (n - 1) / 2.0) / max((n - 1) / 2.0, 1)
        r = 0.38 * size * taper
        head = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
        img[head] = 320.0
        inner = (xx - cx) ** 2 + (yy - cy) ** 2 <= (r * 0.82) ** 2
        img[inner] = 640.0
        vent = ((xx - cx) / (0.10 * size)) ** 2 + ((yy - cy) / (0.16 * size)) ** 2 <= 1
        img[vent & inner] = 180.0
        if rng is not None:
            img = img + rng.normal(0, 18.0, img.shape) * head
        out.append(np.clip(img, 0, 4095))
    return out


def cr_chest(size=256, rng=None):
    """A projection radiograph, stored MONOCHROME1: high value means dark."""
    yy, xx = np.mgrid[0:size, 0:size]
    cy = cx = size / 2.0
    att = np.full((size, size), 0.05)
    body = ((xx - cx) / (0.42 * size)) ** 2 + ((yy - cy) / (0.46 * size)) ** 2 <= 1
    att[body] = 0.55
    for sgn in (-1, 1):
        lung = (((xx - (cx + sgn * 0.18 * size)) / (0.14 * size)) ** 2
                + ((yy - (cy - 0.03 * size)) / (0.24 * size)) ** 2 <= 1)
        att[lung & body] = 0.18
    spine = np.abs(xx - cx) <= 0.035 * size
    att[spine & body] = 0.92
    if rng is not None:
        att = att + rng.normal(0, 0.015, att.shape)
    # MONOCHROME1: the stored value rises as the film gets darker, so more
    # attenuation means a LOWER stored value.
    v = (1.0 - np.clip(att, 0, 1)) * 4000.0
    return v


def us_sector(size=256, rng=None):
    yy, xx = np.mgrid[0:size, 0:size]
    apex_y, apex_x = 8.0, size / 2.0
    dy, dx = yy - apex_y, xx - apex_x
    rad = np.sqrt(dy ** 2 + dx ** 2)
    ang = np.arctan2(dx, np.maximum(dy, 1e-6))
    sector = (rad < 0.92 * size) & (rad > 0.08 * size) & (np.abs(ang) < 0.62)
    img = np.zeros((size, size))
    if rng is None:
        rng = np.random.default_rng(0)
    speckle = rng.gamma(2.0, 28.0, (size, size))
    img[sector] = speckle[sector]
    cyst = (xx - 0.58 * size) ** 2 + (yy - 0.52 * size) ** 2 <= (0.11 * size) ** 2
    img[cyst & sector] = rng.gamma(1.2, 3.0, (size, size))[cyst & sector]
    return np.clip(img, 0, 255)


def sc_with_name(text, size=256):
    """A secondary capture with the patient's name drawn into the pixels.

    Five-by-seven block glyphs, enough that the name is readable on screen and
    unmistakably part of the image and not part of the header.
    """
    FONT = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
        "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
        "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
        "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
        "F": ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
        "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
        "H": ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
        "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
        "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
        "K": ["10001", "10010", "11100", "10100", "10010", "10010", "10001"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
        "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
        " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
        ",": ["00000", "00000", "00000", "00000", "00110", "00100", "01000"],
        ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    }
    img = us_sector(size, np.random.default_rng(7)) * 0.75
    scale = 2
    x0, y0 = 6, 6
    for ch in text.upper():
        rows = FONT.get(ch, FONT[" "])
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                if bit == "1":
                    img[y0 + r * scale: y0 + (r + 1) * scale,
                        x0 + c * scale: x0 + (c + 1) * scale] = 255
        x0 += (5 + 1) * scale
        if x0 > size - 7 * scale:
            break
    return np.clip(img, 0, 255)


# ----------------------------------------------------------------------------
# writing
# ----------------------------------------------------------------------------

def base(sop_class, sop_instance, patient, study, series):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = UID(sop_class)
    meta.MediaStorageSOPInstanceUID = sop_instance
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = uid("implementation")
    meta.ImplementationVersionName = "HY489_LAB04"

    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = UID(sop_class)
    ds.SOPInstanceUID = sop_instance
    ds.SpecificCharacterSet = "ISO_IR 192"

    ds.PatientName = patient["name"]
    ds.PatientID = patient["pid"]
    ds.PatientBirthDate = patient["birth"]
    ds.PatientSex = patient["sex"]

    ds.StudyInstanceUID = study["uid"]
    ds.StudyDate = study["date"]
    ds.StudyTime = study["time"]
    ds.StudyID = study["id"]
    ds.AccessionNumber = study["accession"]
    ds.StudyDescription = study["description"]
    ds.ReferringPhysicianName = "PAPADOPOULOU^ELENI"

    ds.SeriesInstanceUID = series["uid"]
    ds.SeriesNumber = series["number"]
    ds.SeriesDescription = series["description"]
    ds.Modality = series["modality"]
    ds.SeriesDate = study["date"]
    ds.SeriesTime = study["time"]

    ds.Manufacturer = series.get("manufacturer", "HY489 SIMULATOR")
    ds.InstitutionName = series.get("institution", "PAGNI University Hospital")
    ds.StationName = series.get("station", "CT01")
    return ds


def set_pixels(ds, arr, bits=16, signed=True, photometric="MONOCHROME2",
               rescale=None, window=None):
    arr = np.asarray(arr)
    if bits == 8:
        data = np.clip(np.round(arr), 0, 255).astype(np.uint8)
        ds.BitsAllocated, ds.BitsStored, ds.HighBit = 8, 8, 7
        ds.PixelRepresentation = 0
    elif signed:
        data = np.clip(np.round(arr), -32768, 32767).astype(np.int16)
        ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 16, 15
        ds.PixelRepresentation = 1
    else:
        data = np.clip(np.round(arr), 0, 65535).astype(np.uint16)
        ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 16, 15
        ds.PixelRepresentation = 0

    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = photometric
    ds.Rows, ds.Columns = data.shape
    ds.PixelData = data.tobytes()

    if rescale is not None:
        slope, intercept = rescale
        ds.RescaleSlope = str(slope)
        if intercept is not None:
            ds.RescaleIntercept = str(intercept)
        ds.RescaleType = "HU"
    if window is not None:
        ds.WindowCenter, ds.WindowWidth = str(window[0]), str(window[1])
    return ds


def save(ds, folder, name):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    ds.save_as(path, enforce_file_format=True)
    return path


# ----------------------------------------------------------------------------
# the cohort
# ----------------------------------------------------------------------------

def load_cohort():
    rows = []
    with open(COHORT, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def dicom_name(first, last):
    return "%s^%s" % (last.upper(), first.upper())


def main():
    rng_py = random.Random(SEED)
    rng = np.random.default_rng(SEED)

    cohort = load_cohort()
    adults = [r for r in cohort
              if r["DEATHDATE"] == ""
              and date.today().year - int(r["BIRTHDATE"][:4]) >= 30]
    adults.sort(key=lambda r: r["Id"])
    picked = rng_py.sample(adults, 8)

    people = []
    for i, r in enumerate(picked):
        people.append({
            "cohort_id": r["Id"],
            "pid": "PAGNI%06d" % (100001 + i * 137),
            "name": dicom_name(r["FIRST"], r["LAST"]),
            "birth": r["BIRTHDATE"].replace("-", ""),
            "sex": r["GENDER"],
            "first": r["FIRST"],
            "last": r["LAST"],
        })

    # defect 12a: the DICOM sex of person 3 contradicts the CSV
    people[2]["sex"] = "M" if people[2]["sex"] == "F" else "F"
    # defect 12b: person 5's surname is spelled differently in the header
    people[4]["name"] = people[4]["name"].replace("AKI", "AKH")

    # defect 11: a patient who is in no CSV at all
    outsider = {
        "cohort_id": None,
        "pid": "EXT-44187",
        "name": "GEORGIOU^NIKOLAOS",
        "birth": "19580412",
        "sex": "M",
        "first": "Nikolaos",
        "last": "Georgiou",
    }

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    folders = {
        "a": os.path.join(OUT, "incoming_2026_03"),
        "b": os.path.join(OUT, "incoming_2026_04"),
        "c": os.path.join(OUT, "outside_referrals"),
        "d": os.path.join(OUT, "misc"),
    }

    written = []
    counter = [0]

    def nextname():
        counter[0] += 1
        return "img_%04d.dcm" % counter[0]

    def study_of(label, person, d, desc, accession):
        return {
            "uid": uid("study:" + label),
            "date": d.strftime("%Y%m%d"),
            "time": "%02d%02d00" % (8 + int(hashlib.md5(label.encode()).hexdigest(), 16) % 9,
                                    int(hashlib.md5(label.encode()).hexdigest(), 16) % 60),
            "id": label.upper()[:16],
            "accession": accession,
            "description": desc,
        }

    def series_of(label, number, modality, desc, **kw):
        s = {"uid": uid("series:" + label), "number": number,
             "modality": modality, "description": desc}
        s.update(kw)
        return s

    def write_ct_series(folder, person, study, series, images, *,
                        spacing=5.0, thickness=5.0, pixel_spacing=(0.7, 0.7),
                        intercept=-1024, omit_intercept=False,
                        gap_after=None, start_z=-150.0,
                        patient_override=None, label=""):
        z = start_z
        paths = []
        for k, img in enumerate(images):
            who = patient_override[k] if patient_override and k in patient_override else person
            sop = uid("inst:%s:%d" % (label, k))
            ds = base(CT_SOP, sop, who, study, series)
            ds.InstanceNumber = k + 1
            ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
            ds.KVP = "120"
            ds.BodyPartExamined = series.get("body_part", "CHEST")
            ds.PatientPosition = "HFS"
            ds.FrameOfReferenceUID = uid("for:" + label)
            ds.ImagePositionPatient = [-90.0, -90.0, round(z, 3)]
            ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
            ds.PixelSpacing = [str(pixel_spacing[0]), str(pixel_spacing[1])]
            ds.SliceThickness = str(thickness)
            ds.SpacingBetweenSlices = str(spacing)
            ds.SliceLocation = str(round(z, 3))
            # stored value = (HU - intercept) / slope, with slope 1. When
            # omit_intercept is set the pixels are encoded the normal way and
            # the tag is simply not written, which is defect 4: the reader
            # has no way to know and the standard tells it to assume zero.
            stored = img - intercept
            set_pixels(ds, stored, signed=True,
                       rescale=(1, None if omit_intercept else intercept),
                       window=(-600, 1500))
            paths.append(save(ds, folder, nextname()))
            z += spacing
            if gap_after is not None and k == gap_after:
                z += spacing  # defect 5: one slice is missing, position says so
        return paths

    # ---- study 1: P0, chest CT, clean, plus a localiser -------------------
    p = people[0]
    st = study_of("s1", p, date(2026, 3, 2), "CT CHEST W/O CONTRAST", "A2600101")
    sr = series_of("s1-2", 2, "CT", "AXIAL 5MM")
    written += write_ct_series(folders["a"], p, st, sr,
                               ct_chest(12, rng=rng), label="s1-2")
    sr0 = series_of("s1-1", 1, "CT", "SCOUT")
    ds = base(CT_SOP, uid("inst:s1-1:0"), p, st, sr0)
    ds.InstanceNumber = 1
    ds.ImageType = ["ORIGINAL", "PRIMARY", "LOCALIZER"]
    ds.PixelSpacing = ["1.0", "1.0"]
    ds.SliceThickness = "1.0"
    ds.ImagePositionPatient = [-128.0, -128.0, 0.0]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 0, -1]
    set_pixels(ds, cr_chest(rng=rng) - 1024, signed=True,
               rescale=(1, -1024), window=(-200, 2000))
    written.append(save(ds, folders["a"], nextname()))

    # ---- study 2: P1, chest CT with a gap and a lying SliceThickness ------
    p = people[1]
    st = study_of("s2", p, date(2026, 3, 6), "Chest CT", "A2600114")
    sr = series_of("s2-1", 1, "CT", "CHEST AXIAL")
    written += write_ct_series(folders["a"], p, st, sr, ct_chest(12, rng=rng),
                               spacing=5.0, thickness=3.0, gap_after=5,
                               label="s2-1")

    # ---- study 3: P2, chest radiograph, MONOCHROME1 -----------------------
    p = people[2]
    st = study_of("s3", p, date(2026, 3, 11), "CHEST PA", "A2600131")
    sr = series_of("s3-1", 1, "CR", "PA", station="CR02")
    ds = base(CR_SOP, uid("inst:s3-1:0"), p, st, sr)
    ds.InstanceNumber = 1
    ds.ImageType = ["ORIGINAL", "PRIMARY"]
    ds.ViewPosition = "PA"
    ds.BodyPartExamined = "CHEST"
    ds.PixelSpacing = ["0.175", "0.175"]
    set_pixels(ds, cr_chest(rng=rng), bits=16, signed=False,
               photometric="MONOCHROME1", window=(2000, 4000))
    written.append(save(ds, folders["a"], nextname()))

    # ---- study 4: P3, MR brain, no PixelSpacing ---------------------------
    p = people[3]
    st = study_of("s4", p, date(2026, 3, 17), "MRI BRAIN", "A2600148")
    sr = series_of("s4-1", 1, "MR", "AX T2", station="MR01")
    z = -40.0
    for k, img in enumerate(mr_brain(10, rng=rng)):
        ds = base(MR_SOP, uid("inst:s4-1:%d" % k), p, st, sr)
        ds.InstanceNumber = k + 1
        ds.ImageType = ["ORIGINAL", "PRIMARY", "M", "NORM"]
        ds.ScanningSequence = "SE"
        ds.SequenceVariant = "NONE"
        ds.MagneticFieldStrength = "1.5"
        ds.SliceThickness = "4.0"
        ds.ImagePositionPatient = [-110.0, -110.0, round(z, 3)]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.FrameOfReferenceUID = uid("for:s4")
        # defect 6: no PixelSpacing anywhere in the series
        set_pixels(ds, img, signed=False, window=(400, 800))
        written.append(save(ds, folders["b"], nextname()))
        z += 4.0

    # ---- study 5: P4, ultrasound ------------------------------------------
    p = people[4]
    st = study_of("s5", p, date(2026, 4, 1), "US ABDOMEN", "A2600166")
    sr = series_of("s5-1", 1, "US", "RUQ", station="US03")
    ds = base(US_SOP, uid("inst:s5-1:0"), p, st, sr)
    ds.InstanceNumber = 1
    ds.ImageType = ["ORIGINAL", "PRIMARY"]
    ds.BodyPartExamined = "ABDOMEN"
    set_pixels(ds, us_sector(rng=rng), bits=8)
    written.append(save(ds, folders["b"], nextname()))

    # ---- study 6: P5, abdominal CT, merged with another patient -----------
    p = people[5]
    other = people[6]
    st = study_of("s6", p, date(2026, 4, 8), "CT ABDOMEN", "A2600179")
    sr = series_of("s6-1", 1, "CT", "ABDOMEN PORTAL", body_part="ABDOMEN")
    override = {k: other for k in (8, 9, 10, 11)}  # defect 1
    written += write_ct_series(folders["b"], p, st, sr, ct_chest(12, rng=rng),
                               patient_override=override, label="s6-1")

    # ---- study 7: P6, secondary capture with a burned-in name -------------
    p = people[6]
    st = study_of("s7", p, date(2026, 4, 14), "US ABDOMEN REPORT", "A2600188")
    sr = series_of("s7-1", 99, "SC", "SCREEN CAPTURE", station="PACS-WS4")
    ds = base(SC_SOP, uid("inst:s7-1:0"), p, st, sr)
    ds.InstanceNumber = 1
    ds.ConversionType = "WSD"
    ds.BurnedInAnnotation = "YES"  # defect 8
    set_pixels(ds, sc_with_name("%s %s" % (p["last"], p["first"])), bits=8)
    written.append(save(ds, folders["b"], nextname()))

    # ---- study 8: P0 again, follow-up, with a duplicate SOPInstanceUID ----
    p = people[0]
    # defect 13: same PatientID, the name typed again with a middle initial
    p = dict(p)
    p["name"] = p["name"] + "^G"
    st = study_of("s8", p, date(2026, 4, 20), "ct chest w/o", "A2600203")
    sr = series_of("s8-1", 1, "CT", "CHEST 5MM AXIAL")
    imgs = ct_chest(12, rng=rng)
    written += write_ct_series(folders["b"], p, st, sr, imgs,
                               omit_intercept=True, label="s8-1")  # defect 4
    # defect 2: write slice 3's UID again over different pixels
    ds = base(CT_SOP, uid("inst:s8-1:3"), p, st, sr)
    ds.InstanceNumber = 4
    ds.ImageType = ["DERIVED", "SECONDARY", "AXIAL"]
    ds.PixelSpacing = ["0.7", "0.7"]
    ds.SliceThickness = "5.0"
    ds.SpacingBetweenSlices = "5.0"
    ds.ImagePositionPatient = [-90.0, -90.0, -135.0]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.FrameOfReferenceUID = uid("for:s8-1")
    set_pixels(ds, (imgs[3] * 0.6 + 200) + 1024, signed=True,
               rescale=(1, None), window=(-600, 1500))
    written.append(save(ds, folders["b"], nextname()))

    # ---- study 9: P7, chest CT, a fourth spelling of the same protocol ----
    p = people[7]
    st = study_of("s9", p, date(2026, 4, 24), "CT  CHEST WO CONTRAST",
                  "A2600211")
    sr = series_of("s9-1", 1, "CT", "Chest axial 5mm")
    s9_paths = write_ct_series(folders["b"], p, st, sr, ct_chest(12, rng=rng),
                               label="s9-1")
    written += s9_paths

    # ---- study 10: the outside referral ------------------------------------
    st = study_of("s10", outsider, date(2026, 2, 19), "CT CHEST OUTSIDE",
                  "EXT-9912")
    sr = series_of("s10-1", 1, "CT", "AXIAL",
                   institution="Venizeleio General Hospital", station="CT-A")
    written += write_ct_series(folders["c"], outsider, st, sr,
                               ct_chest(8, rng=rng), label="s10-1")

    # ---- a structured report: an instance with no pixels -------------------
    p = people[0]
    st = study_of("s1", p, date(2026, 3, 2), "CT CHEST W/O CONTRAST", "A2600101")
    sr = series_of("s1-900", 900, "SR", "REPORT")
    ds = base(SR_SOP, uid("inst:s1-900:0"), p, st, sr)
    ds.InstanceNumber = 1
    ds.CompletionFlag = "COMPLETE"
    ds.VerificationFlag = "VERIFIED"
    ds.ValueType = "CONTAINER"
    ds.ContinuityOfContent = "SEPARATE"
    cn = Dataset()
    cn.CodeValue = "18748-4"
    cn.CodingSchemeDesignator = "LN"
    cn.CodeMeaning = "Diagnostic imaging report"
    ds.ConceptNameCodeSequence = [cn]
    item = Dataset()
    item.RelationshipType = "CONTAINS"
    item.ValueType = "TEXT"
    iname = Dataset()
    iname.CodeValue = "121070"
    iname.CodingSchemeDesignator = "DCM"
    iname.CodeMeaning = "Findings"
    item.ConceptNameCodeSequence = [iname]
    item.TextValue = ("No focal consolidation. No pleural effusion. "
                      "Heart size within normal limits.")
    ds.ContentSequence = [item]
    written.append(save(ds, folders["a"], nextname()))

    # ---- defect 9: truncate one file ---------------------------------------
    victim = s9_paths[7]
    with open(victim, "rb") as fh:
        blob = fh.read()
    with open(victim, "wb") as fh:
        fh.write(blob[: int(len(blob) * 0.55)])

    # ---- defect 10: a stray non-DICOM file ---------------------------------
    os.makedirs(folders["d"], exist_ok=True)
    with open(os.path.join(folders["d"], "transfer_notes.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(
            "Transfer notes, modality worklist migration.\n"
            "Batch 2026-03 and 2026-04 exported from the old archive.\n"
            "Outside referrals kept separate because the patient IDs do not\n"
            "match ours. Someone needs to reconcile them.\n"
        )

    print("wrote %d DICOM files under %s" % (len(written), OUT))
    print("truncated file (defect 9): %s"
          % os.path.relpath(victim, OUT).replace(os.sep, "/"))
    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(OUT) for f in fs)
    print("archive size: %.1f MB" % (total / 1e6))
    print()
    print("cohort patients used:")
    for q in people:
        print("  %-12s %-28s %s %s  cohort=%s"
              % (q["pid"], q["name"], q["birth"], q["sex"], q["cohort_id"]))
    print("  %-12s %-28s %s %s  cohort=None (outside referral)"
          % (outsider["pid"], outsider["name"], outsider["birth"],
             outsider["sex"]))


if __name__ == "__main__":
    sys.exit(main())
