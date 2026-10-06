"""Applying the profile to a dataset, and the three things that are left over.

TWO STUBS IN THIS FILE: apply_profile and shift_dates.

The shape of the run:

    for every instance
        blank the pixels, if this run claims the Clean Pixel Data Option
        apply_profile      the table in profile.py, attribute by attribute
        shift_dates        if this run claims Retain Longitudinal Modified Dates
        declare            write what was done into (0012,0062) and (0012,0064)
        sync_file_meta     the new SOPInstanceUID has to appear twice
        save

Everything in that list except the two stubs is written for you.
"""

import collections
import datetime
import os

from . import pixels as pixelmod
from . import profile as prof
from . import pseudonym as pseudo

#: Attributes each option puts back, and what it puts them back as. An option
#: is a set of edits to the table in profile.py and nothing more mysterious.
OPTION_OVERRIDES = {
    "RETAIN_FULL_DATES": {
        "StudyDate": "K", "SeriesDate": "K", "ContentDate": "K",
        "AcquisitionDate": "K", "InstanceCreationDate": "K",
        "StudyTime": "K", "SeriesTime": "K", "ContentTime": "K",
        "AcquisitionTime": "K", "InstanceCreationTime": "K",
    },
    "RETAIN_MODIFIED_DATES": {
        "StudyDate": "K", "SeriesDate": "K", "ContentDate": "K",
        "AcquisitionDate": "K", "InstanceCreationDate": "K",
        "StudyTime": "K", "SeriesTime": "K", "ContentTime": "K",
        "AcquisitionTime": "K", "InstanceCreationTime": "K",
    },
    "RETAIN_PATIENT_CHARACTERISTICS": {
        "PatientSex": "K", "PatientAge": "K",
    },
    "RETAIN_INSTITUTION_IDENTITY": {
        "InstitutionName": "K", "InstitutionAddress": "K",
        "InstitutionalDepartmentName": "K",
    },
    "RETAIN_DEVICE_IDENTITY": {
        "StationName": "K", "DeviceSerialNumber": "K",
    },
    "RETAIN_UIDS": {
        "StudyInstanceUID": "K", "SeriesInstanceUID": "K",
        "SOPInstanceUID": "K", "FrameOfReferenceUID": "K",
        "ReferencedSOPInstanceUID": "K",
    },
    "CLEAN_DESCRIPTORS": {
        "StudyDescription": "C", "SeriesDescription": "C",
        "ProtocolName": "C", "ImageComments": "C",
        "DerivationDescription": "C",
    },
    "CLEAN_STRUCTURED_CONTENT": {
        "ContentSequence": "C",
    },
}

#: What goes in when the action is D and the attribute is not an identifier
#: this lab mints. A dummy has to be the right VR and has to be obviously a
#: dummy, so that nobody six months later reads it as data.
DUMMY = {
    "PN": "ANONYMOUS^ANONYMOUS",
    "LO": "REMOVED",
    "SH": "REMOVED",
    "ST": "REMOVED",
    "LT": "REMOVED",
    "UT": "REMOVED",
    "DA": "19000101",
    "TM": "000000",
    "DT": "19000101000000",
    "CS": "REMOVED",
    "IS": "0",
    "DS": "0",
}

#: The descriptions this lab is willing to publish, keyed on (Modality,
#: BodyPartExamined). Anything not in here is removed by clean_value. This is
#: what "replace with values of similar meaning known not to contain
#: identifying information" looks like when you actually have to write it: an
#: allow-list somebody signed, not a regular expression.
SAFE_DESCRIPTIONS = {
    ("CT", "CHEST"): "CT CHEST",
    ("CT", "ABDOMEN"): "CT ABDOMEN",
    ("CR", "CHEST"): "CR CHEST",
    ("MR", None): "MR",
    ("US", "ABDOMEN"): "US ABDOMEN",
    ("US", None): "US",
    ("SC", None): "SECONDARY CAPTURE",
    ("SR", None): "STRUCTURED REPORT",
}


class Context:
    """Everything one de-identification run has to remember.

    One Context per run, shared by every file. That sharing is the point: a
    UID map held per file is not a UID map, and a pseudonym recomputed per
    file without a cache is a bug waiting for the day somebody changes the
    secret halfway through.
    """

    def __init__(self, secret, options=("BASIC", "CLEAN_PIXEL_DATA",
                                        "RETAIN_MODIFIED_DATES")):
        self.secret = secret
        self.options = set(options)
        for name in self.options:
            if name not in prof.OPTIONS:
                raise ValueError("unknown option: %s" % name)
        self.uid_map = {}
        self.patient_map = {}
        self.date_offsets = {}
        self.counts = collections.Counter()
        self.log = []
        self.notes = []
        #: The PatientID of the file being processed right now, as it was
        #: before anything was touched. deidentify_file sets it. It is here so
        #: that the order you walk the profile in cannot change the pseudonym
        #: you write: once PatientID has been replaced, the dataset no longer
        #: knows who it belonged to.
        self.current_patient = None

    # -- what this run claims -------------------------------------------
    def claims(self, name):
        return name in self.options

    def effective_action(self, entry):
        """The action for one attribute, after the claimed options are applied.

        profile.resolve gives the Basic Profile's answer. An option overrides
        it. Reading this function is the shortest honest description of what
        an option is.
        """
        for name in self.options:
            override = OPTION_OVERRIDES.get(name, {})
            if entry.keyword in override:
                return override[entry.keyword]
        return prof.resolve(entry)

    # -- identifiers -----------------------------------------------------
    def pseudonym(self, patient_id):
        """The pseudonym for one PatientID, computed once and cached."""
        key = str(patient_id)
        if key not in self.patient_map:
            self.patient_map[key] = pseudo.patient_pseudonym(key, self.secret)
        return self.patient_map[key]

    def new_uid(self, original):
        """The replacement for one UID, consistent across the whole run."""
        return pseudo.remap_uid(original, self.uid_map, self.secret)

    def date_offset(self, patient_id):
        """Whole days to move this patient's dates by.

        Derived from the secret, so it is reproducible and not guessable from
        the released data. One offset per patient: intervals inside a patient
        survive, and two patients scanned on the same morning stop being
        scanned on the same morning.
        """
        key = str(patient_id)
        if key not in self.date_offsets:
            digest = pseudo.keyed_digest(self.secret, "dateshift", key)
            self.date_offsets[key] = int(digest[:8], 16) % 731 - 365
        return self.date_offsets[key]

    def record(self, path, keyword, action, before, after):
        """One line of the audit trail. Every edit goes through here."""
        self.counts[action] += 1
        self.log.append({"path": path, "keyword": keyword, "action": action,
                         "before": before, "after": after})


# ---------------------------------------------------------------------------
# the stubs
# ---------------------------------------------------------------------------

def apply_profile(ds, ctx, path=""):
    """STUB 3. Apply the profile in profile.py to one dataset.

    Walk profile.PROFILE. For each attribute, ask ctx.effective_action(entry)
    what to do, check whether the attribute is in ds, and do it. Record every
    edit with ctx.record(path, keyword, action, before, after) so that Part C
    has something to audit.

    Returns the number of attributes that were present and acted on.

    The six actions:

      X   delete the attribute. del ds[tag] or del ds.Keyword
      Z   present and empty. Setting it to "" is not the same as deleting it,
          and the difference is the whole of type 1 against type 2
      D   present with a dummy. dummy_for(entry, ds, ctx) gives you one, and
          for PatientID it gives you the pseudonym
      U   a new UID from ctx.new_uid(old). An absent UID stays absent
      K   leave it alone. Record it anyway: a K you cannot show you considered
          is indistinguishable from an attribute you forgot
      C   call clean_value(ds, entry, ctx), which is written for you

    Yours to decide:

      an attribute that is not in the dataset. There is nothing to remove and
      nothing to empty. Z on an absent attribute would add an empty tag that
      was never there, which changes the IOD

      the order you walk the table in. It should not matter and it does: once
      PatientID holds a pseudonym the dataset cannot say who it belonged to.
      ctx.current_patient holds the original and is set before this runs,
      which is one way out. Decide whether you rely on it or on the order

      what you log. The before value of PatientName is the patient's name. A
      log that holds it is a second copy of the thing you are removing, and
      Part C will find it if you write it next to the images
    """
    raise NotImplementedError("Lab 5, Part A, task 5")


def shift_dates(ds, ctx, patient_key, path=""):
    """STUB 4. Move this instance's dates, keeping the intervals.

    Only runs when the run claims RETAIN_MODIFIED_DATES. Without that option
    the dates are already Z and there is nothing here to move.

    patient_key is the ORIGINAL PatientID, because the offset has to be the
    same for every instance of one patient and apply_profile has already
    replaced the attribute by the time this runs. ctx.date_offset(patient_key)
    gives whole days, between -365 and +365.

    Returns a list of the keywords that were changed.

    Yours to decide:

      which attributes move. StudyDate and SeriesDate and ContentDate are
      dates. StudyTime is a time of day, and a time of day with no date is
      either harmless or the thing that says which shift was on

      an offset per patient or one offset for the whole archive. Per patient
      keeps each patient's own timeline and destroys the fact that two of
      them were scanned the same morning. One offset for the archive keeps
      both, which means it keeps a calendar that can be lined up against a
      staff rota

      what happens at the edges. 20260302 minus 61 days is in January, and a
      date arithmetic that does not go through datetime will produce 20260131
      or 20260230 depending on how wrong it is

      whether a shifted date still goes in a field called StudyDate. It does,
      and the thing that stops the next reader treating it as the real date
      is (0012,0063), which declare() writes
    """
    raise NotImplementedError("Lab 5, Part B, task 2")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def dummy_for(entry, ds, ctx):
    """The value to write when the action is D.

    PatientID is the one that matters and it is special: the dummy is the
    pseudonym, which is what makes the release joinable to itself. Everything
    else gets a visible placeholder of the right VR.
    """
    if entry.keyword in ("PatientID", "PatientName"):
        original = ctx.current_patient
        if original is None:
            original = ds.get("PatientID", "")
        return ctx.pseudonym(original)
    try:
        vr = str(ds[entry.tag].VR)
    except KeyError:
        vr = "LO"
    if vr == "SQ":
        # D on a sequence means a non-zero length sequence whose contents say
        # nothing. One empty item does that, and it is visibly not a report.
        # The alternative every real de-identifier reaches for is to drop the
        # object: an SR with a dummy content sequence is a conformant file
        # that nobody can use.
        from pydicom.dataset import Dataset as _Dataset
        return [_Dataset()]
    return DUMMY.get(vr, "REMOVED")


def clean_value(ds, entry, ctx):
    """Action C: keep the meaning, drop everything that could identify.

    Two cases are implemented, because they are the two in this archive.

    A descriptor is cleaned by throwing away what was typed and writing back
    the controlled term for (Modality, BodyPartExamined). Lab 4 found four
    spellings of one protocol in StudyDescription and showed that the two
    coded fields already agreed. This is what you do with that finding.

    A content sequence is cleaned by clean_structured_content below.
    """
    if entry.keyword == "ContentSequence":
        return clean_structured_content(ds, ctx)
    modality = str(ds.get("Modality", "") or "")
    body = ds.get("BodyPartExamined", None)
    body = str(body) if body else None
    safe = (SAFE_DESCRIPTIONS.get((modality, body))
            or SAFE_DESCRIPTIONS.get((modality, None)))
    if safe is None:
        if entry.keyword in ds:
            del ds[entry.tag]
        return None
    ds[entry.tag].value = safe
    return safe


def identifying_strings(ds):
    """Every string in this dataset that is known to identify somebody.

    Used by clean_structured_content to redact free text. It is a list of
    things you already know are identifiers, which means it finds exactly
    those and nothing else. The name of a patient who is not this patient,
    the name of the referring clinic written out in a sentence, a phone
    number: none of them are in this list and none of them will be found.
    """
    out = set()
    for keyword in ("PatientName", "PatientID", "PatientBirthDate",
                    "AccessionNumber", "StudyID", "ReferringPhysicianName",
                    "InstitutionName", "StationName"):
        value = ds.get(keyword, None)
        if value in (None, ""):
            continue
        text = str(value)
        out.add(text)
        for part in text.replace("^", " ").split():
            if len(part) >= 3:
                out.add(part)
    return {s for s in out if s}


def clean_structured_content(ds, ctx, needles=None):
    """Walk a content sequence and redact the text items.

    Returns the number of text items changed.

    This is the honest version of free-text scrubbing, which is to say it is
    the dishonest problem written out so you can see the shape of it. It
    removes the strings you already knew were identifiers. Week 8's sentence
    about free text applies without modification: a report that says "the
    patient's daughter, who works here, asked about the result" is not
    reachable by any list of needles, and nothing in this function will find
    it. Say so in your report if you claim the Clean Structured Content
    Option.
    """
    if "ContentSequence" not in ds:
        return 0
    if needles is None:
        needles = identifying_strings(ds)
    changed = 0

    def walk(sequence):
        nonlocal changed
        for item in sequence:
            vt = str(item.get("ValueType", "") or "")
            if vt == "PNAME" and "PersonName" in item:
                item.PersonName = "ANONYMOUS^ANONYMOUS"
                changed += 1
            if "TextValue" in item:
                text = str(item.TextValue)
                new = text
                for needle in sorted(needles, key=len, reverse=True):
                    if needle and needle in new:
                        new = new.replace(needle, "[REDACTED]")
                if new != text:
                    item.TextValue = new
                    changed += 1
            if "ContentSequence" in item:
                walk(item.ContentSequence)

    walk(ds.ContentSequence)
    return changed


def declare(ds, ctx):
    """Write what was done into the file, which is what makes it conformant.

    (0012,0062) PatientIdentityRemoved  YES
    (0012,0063) DeidentificationMethod  a sentence a human reads
    (0012,0064) DeidentificationMethodCodeSequence  the CID 7050 codes

    A de-identified file that does not say so is a file the next system has to
    guess about, and the guess is usually that it is still identifiable, so it
    gets treated as identifiable, so the de-identification bought nothing.
    """
    from pydicom.dataset import Dataset

    ds.PatientIdentityRemoved = "YES"
    # (0012,0063) is VR LO, which is 64 characters. The full option names do
    # not fit, so this carries the CID 7050 code values and the sequence below
    # carries the meanings. A method string truncated in the middle of a word
    # is worse than a short one.
    codes = ",".join(prof.OPTIONS[o][0] for o in sorted(ctx.options))
    ds.DeidentificationMethod = ("HY-489 Lab 5; PS3.15 E; " + codes)[:64]

    seq = []
    for option in sorted(ctx.options):
        code, meaning = prof.OPTIONS[option]
        item = Dataset()
        item.CodeValue = code
        item.CodingSchemeDesignator = "DCM"
        item.CodeMeaning = meaning
        seq.append(item)
    ds.DeidentificationMethodCodeSequence = seq
    return ds


def sync_file_meta(ds):
    """The new SOPInstanceUID has to appear in two places.

    (0008,0018) is in the dataset and (0002,0003) MediaStorageSOPInstanceUID
    is in the file meta information, and they have to agree. Change one and
    not the other and the file still opens, still displays and is not
    conformant, and the system that rejects it will be the one in the other
    hospital three months from now.
    """
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    ds.file_meta.ImplementationVersionName = "HY489_LAB05"
    return ds


def save(ds, path):
    """Write one dataset, on pydicom 2 or 3."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    try:
        ds.save_as(path, enforce_file_format=True)
    except TypeError:
        ds.save_as(path, write_like_original=False)
    return path


def shift_one_date(value, days):
    """YYYYMMDD plus or minus whole days, through datetime, as a string.

    Here so that nobody writes the version that does the arithmetic on the
    digits. February is the reason.
    """
    text = str(value).strip()
    if len(text) != 8 or not text.isdigit():
        return None
    base = datetime.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    return (base + datetime.timedelta(days=int(days))).strftime("%Y%m%d")


def deidentify_file(path, root, ctx):
    """One file in, one de-identified dataset and one manifest row out.

    Returns (dataset, row). The dataset is None when the file could not be
    read at all.

    The pixel decode is attempted and allowed to fail. Lab 4 found one
    instance in this archive whose header is perfect and whose pixels are
    gone, and the decision about that instance is Part B's, not this
    function's: here it is read, recorded as pixels_ok False, and passed on.
    """
    import pydicom

    rel = os.path.relpath(path, root).replace(os.sep, "/")
    row = {"source": rel, "status": "ok", "pixels_ok": None,
           "annotation": "", "modality": "", "pseudonym": "",
           "cleaned_text_items": 0, "date_shift_days": "", "output": ""}

    try:
        ds = pydicom.dcmread(path)
    except Exception as exc:                                  # noqa: BLE001
        row["status"] = "unreadable: %s" % type(exc).__name__
        return None, row

    original_patient_id = str(ds.get("PatientID", "") or "")
    ctx.current_patient = original_patient_id
    row["modality"] = str(ds.get("Modality", "") or "")

    # 1. the pixels, before any header is touched
    if "PixelData" in ds:
        try:
            arr = ds.pixel_array
            row["pixels_ok"] = True
        except Exception as exc:                              # noqa: BLE001
            arr = None
            row["pixels_ok"] = False
            row["status"] = "pixels did not decode: %s" % type(exc).__name__
        if arr is not None and ctx.claims("CLEAN_PIXEL_DATA"):
            box = pixelmod.find_annotation_band(arr)
            declared = pixelmod.declares_burned_in(ds)
            if box is not None:
                cleaned = pixelmod.blank_region(arr, box)
                pixelmod.write_pixels(ds, cleaned)
                ds.BurnedInAnnotation = "NO"
                row["annotation"] = "blanked %s" % (box,)
            elif declared == "YES":
                row["annotation"] = "declared YES, nothing found"
            else:
                row["annotation"] = "none found"

    # 2. the structured content, before the Basic Profile would destroy it
    if ctx.claims("CLEAN_STRUCTURED_CONTENT"):
        row["cleaned_text_items"] = clean_structured_content(ds, ctx)

    # 3. the header
    apply_profile(ds, ctx, path=rel)

    # 4. the dates
    if ctx.claims("RETAIN_MODIFIED_DATES"):
        changed = shift_dates(ds, ctx, original_patient_id, path=rel)
        if changed:
            row["date_shift_days"] = ctx.date_offset(original_patient_id)

    # 5. say what was done, and make the file internally consistent
    declare(ds, ctx)
    sync_file_meta(ds)

    row["pseudonym"] = ctx.pseudonym(original_patient_id)
    return ds, row


def output_path(ds, ctx, out_root, counters):
    """Where a de-identified instance goes.

    Not where it came from. The Lab 4 archive is in folders called
    incoming_2026_03 and incoming_2026_04, which name the month of the
    transfer, and a release that keeps those folder names has published a
    date it just spent an hour removing from the headers.
    """
    pseudonym = str(ds.get("PatientID", "UNKNOWN"))
    study = str(ds.get("StudyInstanceUID", ""))
    series = str(ds.get("SeriesInstanceUID", ""))
    s_index = counters["study"].setdefault((pseudonym, study),
                                           len(counters["study"]) + 1)
    r_index = counters["series"].setdefault((pseudonym, series),
                                            len(counters["series"]) + 1)
    counters["instance"][(pseudonym, series)] = \
        counters["instance"].get((pseudonym, series), 0) + 1
    n = counters["instance"][(pseudonym, series)]
    return os.path.join(out_root, pseudonym, "study_%02d" % s_index,
                        "series_%02d" % r_index, "inst_%04d.dcm" % n)


def run_archive(root, out_root, ctx, paths=None):
    """De-identify a whole archive.

    paths is the list of relative paths to process, which is where the Lab 4
    inventory goes. Pass None to walk the tree instead. The two are not the
    same list and the difference is reported: the inventory is what you
    believe is in the archive and the walk is what is on the disk.
    """
    from . import verify  # local import: verify imports nothing from here

    on_disk = verify.walk_relative(root)
    if paths is None:
        todo = list(on_disk)
        extra, missing = [], []
    else:
        todo = list(paths)
        extra = [p for p in on_disk if p not in set(todo)]
        missing = [p for p in todo if p not in set(on_disk)]

    counters = {"study": {}, "series": {}, "instance": {}}
    rows = []
    for rel in todo:
        ds, row = deidentify_file(os.path.join(root, rel), root, ctx)
        if ds is not None:
            path = output_path(ds, ctx, out_root, counters)
            save(ds, path)
            row["output"] = os.path.relpath(path, out_root).replace(os.sep, "/")
        rows.append(row)

    summary = {
        "requested": len(todo),
        "written": sum(1 for r in rows if r["output"]),
        "unreadable": sum(1 for r in rows if r["status"].startswith("unreadable")),
        "pixels_failed": sum(1 for r in rows if r["pixels_ok"] is False),
        "on_disk_not_requested": extra,
        "requested_not_on_disk": missing,
        "pseudonyms": len(ctx.patient_map),
        "uids_remapped": len(ctx.uid_map),
        "actions": dict(ctx.counts),
    }
    return rows, summary


def summarise(summary):
    print("instances requested        %5d" % summary["requested"])
    print("instances written          %5d" % summary["written"])
    print("could not be read          %5d" % summary["unreadable"])
    print("pixels did not decode      %5d" % summary["pixels_failed"])
    print("pseudonyms minted          %5d" % summary["pseudonyms"])
    print("UIDs remapped              %5d" % summary["uids_remapped"])
    print()
    print("attribute actions applied")
    for action in sorted(summary["actions"]):
        print("  %-6s %5d" % (action, summary["actions"][action]))
    if summary["on_disk_not_requested"]:
        print()
        print("on disk and not in the list you passed:")
        for p in summary["on_disk_not_requested"]:
            print("  %s" % p)
    if summary["requested_not_on_disk"]:
        print()
        print("in the list you passed and not on disk:")
        for p in summary["requested_not_on_disk"]:
            print("  %s" % p)


def save_manifest(rows, path):
    """The release-safe half of what run_archive returned.

    One row per released instance, naming it by where it is in the release and
    not by where it came from. The source path is left out on purpose: the Lab
    4 archive is in folders named after the month of the transfer, and a
    manifest that carries incoming_2026_03/img_0001.dcm has published that
    month and has also handed anybody a direct line back to the original file.
    That column goes in the crosswalk, which is key material.
    """
    import csv as _csv
    fields = ["output", "pseudonym", "modality", "status", "pixels_ok",
              "annotation", "date_shift_days", "cleaned_text_items"]
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            if not r.get("output"):
                continue
            w.writerow({k: r.get(k, "") for k in fields})
    return path


def save_crosswalk(rows, path):
    """Which original file became which released file. KEY MATERIAL.

    Goes with the link table and the UID map, in the folder the recipient does
    not get.
    """
    import csv as _csv
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["source", "output", "pseudonym"])
        for r in rows:
            w.writerow([r.get("source", ""), r.get("output", ""),
                        r.get("pseudonym", "")])
    return path
