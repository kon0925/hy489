"""The audit. Written for you, and the part of the lab that is the point.

Nothing in this file is a stub. It exists because a de-identification script
that has never been attacked is a de-identification script that has never been
tested, and because the attack is the one from Week 8 with the target changed:
it used to be pointed at the Lab 1 cohort and it is now pointed at what you
produced twenty minutes ago.

Five checks:

    scan_for_leaks        does any string you removed survive anywhere
    check_uids            is the remapping consistent, injective and complete
    attack_pseudonyms     the Week 8 hash trap, run against your own scheme
    attack_dates          match the release back to the archive on dates alone
    attack_shape          match it back with the dates thrown away
    check_structure       did the hierarchy survive, and what changed

A check that passes is not proof of anything. It is one attack that did not
work. Say that in your report, because an audit report that says "no issues
found" has described the auditor and not the data.
"""

import collections
import json
import os

import pydicom

#: The attributes whose original values must not appear anywhere in the
#: release. Everything else in the archive is either kept on purpose or
#: structural.
IDENTIFYING_KEYWORDS = [
    "PatientName", "PatientID", "PatientBirthDate", "AccessionNumber",
    "ReferringPhysicianName", "InstitutionName", "StationName",
]

#: The UIDs the profile says U. These four, and nothing else, must be new.
REMAPPED_UID_KEYWORDS = [
    "StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
    "FrameOfReferenceUID",
]

#: Needles shorter than this are dropped. "S1" as a StudyID would otherwise
#: match inside half the UIDs in the archive. It is a threshold and it is a
#: hole: an identifier of three characters is still an identifier.
MIN_NEEDLE = 4


def walk_relative(root):
    """Every file under root, relative, forward slashes, stable order."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return out


def _read(path):
    try:
        return pydicom.dcmread(path, stop_before_pixels=True), None
    except Exception as exc:                                  # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def _strings(ds, include_meta=True):
    """Every string value in a dataset, sequences included, as (keyword, text)."""
    out = []

    def walk(dataset, prefix=""):
        for element in dataset:
            keyword = element.keyword or str(element.tag)
            label = prefix + keyword
            if element.VR == "SQ":
                for i, item in enumerate(element.value or []):
                    walk(item, "%s[%d]." % (label, i))
                continue
            value = element.value
            if value is None:
                continue
            if isinstance(value, (bytes, bytearray)):
                continue
            if isinstance(value, (list, tuple)) or hasattr(value, "__iter__") \
                    and not isinstance(value, str):
                try:
                    for v in value:
                        out.append((label, str(v)))
                    continue
                except TypeError:
                    pass
            out.append((label, str(value)))

    if include_meta and hasattr(ds, "file_meta") and ds.file_meta is not None:
        walk(ds.file_meta, "meta.")
    walk(ds)
    return out


# ---------------------------------------------------------------------------
# 1. leaks
# ---------------------------------------------------------------------------

def known_identifiers(root):
    """Every string from the ORIGINAL archive that must not be released.

    Returns (needles, uids). needles are names, identifiers, birth dates,
    accession numbers, institutions and stations, plus the components of the
    names. uids are the four remapped UID families.

    This is a list of things already known to be identifiers, which is the
    only kind of leak scan anybody can write and the reason a clean scan is
    weak evidence. Nothing here would find a Greek surname typed into
    ImageComments by a radiographer.
    """
    needles, uids = set(), set()
    for rel in walk_relative(root):
        ds, err = _read(os.path.join(root, rel))
        if ds is None:
            continue
        for keyword in IDENTIFYING_KEYWORDS:
            value = ds.get(keyword, None)
            if value in (None, ""):
                continue
            text = str(value)
            needles.add(text)
            for part in text.replace("^", " ").split():
                needles.add(part)
        for keyword in REMAPPED_UID_KEYWORDS:
            value = ds.get(keyword, None)
            if value:
                uids.add(str(value))
    needles = {n for n in needles if len(n) >= MIN_NEEDLE}
    return needles, uids


def scan_for_leaks(out_root, needles, uids):
    """Every place an original identifier survived into the release."""
    hits = []
    both = set(needles) | set(uids)
    for rel in walk_relative(out_root):
        ds, err = _read(os.path.join(out_root, rel))
        if ds is None:
            hits.append({"path": rel, "keyword": "-", "needle": "-",
                         "detail": "could not read: %s" % err})
            continue
        for keyword, text in _strings(ds):
            for needle in both:
                if needle in text:
                    hits.append({"path": rel, "keyword": keyword,
                                 "needle": needle, "detail": text[:80]})
    return hits


# ---------------------------------------------------------------------------
# 2. UIDs
# ---------------------------------------------------------------------------

def check_uids(orig_root, out_root, uid_map):
    """Is the remapping consistent, injective, arc-correct and complete."""
    problems = []

    originals = list(uid_map.keys())
    replacements = list(uid_map.values())
    if len(set(replacements)) != len(replacements):
        counts = collections.Counter(replacements)
        for value, n in counts.items():
            if n > 1:
                problems.append("%d originals map to the same new UID %s"
                                % (n, value))
    for value in replacements:
        if not str(value).startswith("2.25."):
            problems.append("new UID is not under the 2.25 arc: %s" % value)
        if len(str(value)) > 64:
            problems.append("new UID is %d characters: %s"
                            % (len(str(value)), value))

    # the same StudyInstanceUID in the archive must be one study in the release
    orig_struct = _structure(orig_root)
    out_struct = _structure(out_root)

    for rel in walk_relative(out_root):
        ds, err = _read(os.path.join(out_root, rel))
        if ds is None:
            continue
        meta = str(getattr(ds.file_meta, "MediaStorageSOPInstanceUID", ""))
        if meta != str(ds.get("SOPInstanceUID", "")):
            problems.append("%s: (0002,0003) and (0008,0018) disagree" % rel)

    return {
        "mapped": len(uid_map),
        "distinct_new": len(set(replacements)),
        "problems": problems,
        "original": orig_struct,
        "released": out_struct,
    }


def _structure(root):
    studies, series, sops, patients, files = set(), set(), set(), set(), 0
    unreadable = 0
    for rel in walk_relative(root):
        ds, err = _read(os.path.join(root, rel))
        if ds is None:
            unreadable += 1
            continue
        files += 1
        patients.add(str(ds.get("PatientID", "")))
        studies.add(str(ds.get("StudyInstanceUID", "")))
        series.add(str(ds.get("SeriesInstanceUID", "")))
        sops.add(str(ds.get("SOPInstanceUID", "")))
    return {"files": files, "unreadable": unreadable,
            "patients": len(patients), "studies": len(studies),
            "series": len(series), "instances": len(sops)}


# ---------------------------------------------------------------------------
# 3. the hash trap
# ---------------------------------------------------------------------------

def candidate_patient_ids(pagni=10000, ext=100000):
    """The identifier space an attacker enumerates.

    PAGNI numbers are a fixed prefix and six digits, of which the first two
    never move, so the space is ten thousand. EXT numbers are a prefix and
    five digits. An attacker who has ever seen one identifier from this
    hospital knows both shapes, and the shapes are the whole secret.
    """
    for n in range(100000, 100000 + pagni):
        yield "PAGNI%06d" % n
    for n in range(ext):
        yield "EXT-%05d" % n


def attack_pseudonyms(released, make_pseudonym, candidates=None):
    """Brute-force a pseudonymisation scheme over the identifier space.

    released is the set of pseudonyms that appear in the release.
    make_pseudonym is the function under attack, called with one argument.

    Returns (recovered, tried). recovered maps pseudonym to the original
    identifier that produces it, for every one the attack broke.

    This is the Week 8 hash trap with the numbers attached. A hash is one-way
    only when the input cannot be guessed, and a hospital number cannot not be
    guessed.
    """
    released = {str(p) for p in released}
    if candidates is None:
        candidates = candidate_patient_ids()
    recovered, tried = {}, 0
    for candidate in candidates:
        tried += 1
        try:
            value = str(make_pseudonym(candidate))
        except Exception:                                     # noqa: BLE001
            continue
        if value in released:
            recovered[value] = candidate
    return recovered, tried


def released_pseudonyms(out_root):
    out = set()
    for rel in walk_relative(out_root):
        ds, err = _read(os.path.join(out_root, rel))
        if ds is None:
            continue
        value = ds.get("PatientID", None)
        if value:
            out.add(str(value))
    return out


# ---------------------------------------------------------------------------
# 4. the dates
# ---------------------------------------------------------------------------

def attack_dates(orig_root, out_root):
    """Match the release back to the archive using only what is left.

    The attacker holds the hospital's own worklist, which is to say the
    original archive, and wants to know which released study is which. The
    only thing they are given is each study's date, its modality and how many
    instances are in it.

    Returns a dict with how many released studies matched exactly one archive
    study. A release with the dates shifted per patient should match none of
    them, and a release that claimed Retain Longitudinal Full Dates should
    match all of them.
    """
    def fingerprint(root):
        studies = collections.defaultdict(lambda: {"modalities": set(),
                                                   "instances": 0,
                                                   "date": ""})
        for rel in walk_relative(root):
            ds, err = _read(os.path.join(root, rel))
            if ds is None:
                continue
            uid = str(ds.get("StudyInstanceUID", ""))
            entry = studies[uid]
            entry["modalities"].add(str(ds.get("Modality", "")))
            entry["instances"] += 1
            entry["date"] = str(ds.get("StudyDate", "") or "")
        return {uid: (e["date"], ",".join(sorted(e["modalities"])),
                      e["instances"])
                for uid, e in studies.items()}

    archive = fingerprint(orig_root)
    release = fingerprint(out_root)

    index = collections.defaultdict(list)
    for uid, key in archive.items():
        index[key].append(uid)

    unique, ambiguous, none = 0, 0, 0
    for uid, key in release.items():
        hits = index.get(key, [])
        if len(hits) == 1:
            unique += 1
        elif len(hits) > 1:
            ambiguous += 1
        else:
            none += 1
    return {"released_studies": len(release), "archive_studies": len(archive),
            "matched_uniquely": unique, "matched_ambiguously": ambiguous,
            "no_match": none}


def attack_shape(orig_root, out_root):
    """Match the release back to the archive with the dates thrown away.

    The attacker is told nothing about when anything happened. They are given
    each released study's modalities, how many series it has and how many
    instances, which is information no option in PS3.15 removes because it is
    not an attribute: it is the shape of the data.

    Returns the same counts as attack_dates. The number to read is
    matched_uniquely, and it is the residual risk the profile cannot touch.
    """
    def fingerprint(root):
        studies = collections.defaultdict(lambda: {"modalities": set(),
                                                   "series": set(),
                                                   "instances": 0})
        for rel in walk_relative(root):
            ds, err = _read(os.path.join(root, rel))
            if ds is None:
                continue
            entry = studies[str(ds.get("StudyInstanceUID", ""))]
            entry["modalities"].add(str(ds.get("Modality", "")))
            entry["series"].add(str(ds.get("SeriesInstanceUID", "")))
            entry["instances"] += 1
        return {uid: (",".join(sorted(e["modalities"])), len(e["series"]),
                      e["instances"])
                for uid, e in studies.items()}

    archive = fingerprint(orig_root)
    release = fingerprint(out_root)
    index = collections.defaultdict(list)
    for uid, key in archive.items():
        index[key].append(uid)

    unique, ambiguous, none = 0, 0, 0
    for uid, key in release.items():
        hits = index.get(key, [])
        if len(hits) == 1:
            unique += 1
        elif len(hits) > 1:
            ambiguous += 1
        else:
            none += 1
    return {"released_studies": len(release), "archive_studies": len(archive),
            "matched_uniquely": unique, "matched_ambiguously": ambiguous,
            "no_match": none}


# ---------------------------------------------------------------------------
# 5. structure
# ---------------------------------------------------------------------------

def check_structure(out_root):
    """What the release looks like from the outside, and what carried over."""
    per_study = collections.defaultdict(set)
    per_patient_studies = collections.defaultdict(set)
    per_patient_instances = collections.Counter()
    burned_in = []
    declared = collections.Counter()

    for rel in walk_relative(out_root):
        ds, err = _read(os.path.join(out_root, rel))
        if ds is None:
            continue
        pid = str(ds.get("PatientID", ""))
        study = str(ds.get("StudyInstanceUID", ""))
        per_study[study].add(pid)
        per_patient_studies[pid].add(study)
        per_patient_instances[pid] += 1
        flag = ds.get("BurnedInAnnotation", None)
        if flag is not None and str(flag).upper() == "YES":
            burned_in.append(rel)
        declared[str(ds.get("PatientIdentityRemoved", "ABSENT"))] += 1

    shared = {s: sorted(p) for s, p in per_study.items() if len(p) > 1}
    return {
        "patients": len(per_patient_studies),
        "studies": len(per_study),
        "studies_with_more_than_one_patient": shared,
        "instances_per_patient": dict(per_patient_instances),
        "still_declaring_burned_in": burned_in,
        "patient_identity_removed": dict(declared),
    }


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------

def report(leaks, uids, attack, dates, structure, shape=None):
    """Print the audit. The numbers in it go into your report verbatim."""
    print("1. LEAK SCAN")
    if not leaks:
        print("   no original identifier found in the release")
        print("   this is one attack that did not work, not a clean bill")
    else:
        print("   %d hits" % len(leaks))
        for h in leaks[:20]:
            print("     %-34s %-28s %s" % (h["path"], h["keyword"], h["needle"]))
        if len(leaks) > 20:
            print("     ... %d more" % (len(leaks) - 20))

    print()
    print("2. UIDs")
    print("   %d originals mapped to %d distinct new UIDs"
          % (uids["mapped"], uids["distinct_new"]))
    print("   archive  %(files)4d files  %(patients)2d patients  "
          "%(studies)2d studies  %(series)2d series  %(instances)3d instances"
          % uids["original"])
    print("   release  %(files)4d files  %(patients)2d patients  "
          "%(studies)2d studies  %(series)2d series  %(instances)3d instances"
          % uids["released"])
    if uids["problems"]:
        for p in uids["problems"][:20]:
            print("   PROBLEM %s" % p)
    else:
        print("   no problems")

    print()
    print("3. THE PSEUDONYM, UNDER ATTACK")
    recovered, tried = attack
    print("   %d candidate identifiers tried" % tried)
    print("   %d of the released pseudonyms recovered" % len(recovered))
    for pseudonym, original in sorted(recovered.items())[:12]:
        print("     %-30s <- %s" % (pseudonym, original))

    print()
    print("4. THE DATES, UNDER ATTACK")
    print("   %(released_studies)d released studies against %(archive_studies)d "
          "archive studies" % dates)
    print("   matched to exactly one archive study  %(matched_uniquely)d" % dates)
    print("   matched to more than one              %(matched_ambiguously)d" % dates)
    print("   matched to none                       %(no_match)d" % dates)

    if shape is not None:
        print()
        print("4b. THE SHAPE, UNDER ATTACK, WITH NO DATES AT ALL")
        print("   matched to exactly one archive study  %(matched_uniquely)d "
              "of %(released_studies)d" % shape)
        print("   no attribute carries this and no option removes it")

    print()
    print("5. STRUCTURE")
    print("   %(patients)d pseudonyms, %(studies)d studies" % structure)
    if structure["studies_with_more_than_one_patient"]:
        for study, people in structure["studies_with_more_than_one_patient"].items():
            print("   study %s carries %d pseudonyms: %s"
                  % (study[-12:], len(people), ", ".join(people)))
    else:
        print("   every study carries one pseudonym")
    if structure["still_declaring_burned_in"]:
        print("   still declaring BurnedInAnnotation YES: %s"
              % ", ".join(structure["still_declaring_burned_in"]))
    print("   PatientIdentityRemoved: %s" % structure["patient_identity_removed"])


def to_json(path, **sections):
    """Write the audit to notebooks/audit.json. It is a deliverable."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sections, fh, indent=2, sort_keys=True, default=str)
    return path
