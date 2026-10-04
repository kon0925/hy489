#!/usr/bin/env python3
"""Build a patient summary in the shape the EEHRxF asks for, then check it.

    python3 summary.py                # the whole thing
    python3 summary.py --sections     # what a patient summary has to contain
    python3 summary.py --bundle       # one patient, as a FHIR document Bundle
    python3 summary.py --rules        # the twelve checks, written out
    python3 summary.py --validate     # run the checks over all 1,174 patients
    python3 summary.py --coding       # the code systems this cohort actually uses
    python3 summary.py --repair       # fix three defects and validate again

Article 14(1)(a) of Regulation (EU) 2025/327 makes the patient summary one of
the six priority categories of personal electronic health data. Article 15(1)
says the European electronic health record exchange format consists of
harmonised datasets, coding systems and values, and technical interoperability
specifications. The clinical content of a European patient summary is the
International Patient Summary, which requires three sections and recommends
four more.

This script builds that document for a patient in the Lab 1 cohort, writes it
out as a FHIR document Bundle, and then runs a validator over every patient to
find out how many of them could cross a border.

Stdlib only. No FHIR library, no network, no server.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))

TODAY = dt.date(2026, 11, 30)          # the Monday of Week 11
AUTHORED = "2026-11-30T09:00:00+02:00"

# LOINC codes for the IPS sections. The composition type is the LOINC code for a
# patient summary document.
LOINC_COMPOSITION = ("60591-5", "Patient summary Document")
SECTION_CODES = {
    "problems":      ("11450-4", "Problem list - Reported"),
    "allergies":     ("48765-2", "Allergies and adverse reactions Document"),
    "medications":   ("10160-0", "History of Medication use Narrative"),
    "immunisations": ("11369-6", "History of Immunization Narrative"),
    "results":       ("30954-2", "Relevant diagnostic tests/laboratory data Narrative"),
    "vitals":        ("8716-3",  "Vital signs"),
}

# Required by the IPS, recommended by the IPS. The distinction is the whole
# argument in the --validate section.
REQUIRED_SECTIONS = ["problems", "allergies", "medications"]
RECOMMENDED_SECTIONS = ["immunisations", "results"]

# The five laboratory and vital-sign observations in this cohort, and which IPS
# section each one belongs in.
LAB_CODES = {"2093-3", "2085-9"}
VITAL_CODES = {"8480-6", "8462-4", "29463-7"}

SNOMED = "http://snomed.info/sct"
RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
ABSENT_CS = "http://hl7.org/fhir/uv/ips/CodeSystem/absent-unknown-uv-ips"
LOINC = "http://loinc.org"
UCUM = "http://unitsofmeasure.org"

# Administrative gender in FHIR is a fixed value set. The cohort uses M and F.
GENDER = {"M": "male", "F": "female"}

# UCUM is the unit system MyHealth@EU and the HL7 Europe guides use. These are
# the three unit strings that appear in observations.csv.
UCUM_UNITS = {"mm[Hg]", "kg", "mg/dL"}


def read(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        raise SystemExit(
            "Cannot find %s\nRun this from lectures/week11 inside the repository." % path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


def clean(desc):
    for suffix in (" (disorder)", " (finding)", " (procedure)"):
        if desc.endswith(suffix):
            return desc[: -len(suffix)]
    return desc


# ----------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------
def load():
    """One pass over the five CSVs, keyed by patient.

    Nothing here is clever. The point of reading it is to notice what the five
    files do not contain: there is no allergy file and no immunisation file,
    and two of the three required IPS sections have no source at all.
    """
    patients = {p["Id"]: p for p in read("patients.csv")}

    problems = defaultdict(list)
    for r in read("conditions.csv"):
        problems[r["PATIENT"]].append({
            "code": r["CODE"],
            "system": r["SYSTEM"],
            "display": clean(r["DESCRIPTION"]),
            "onset": r["START"][:10],
            "abated": r["STOP"][:10],
        })

    medications = defaultdict(list)
    for r in read("medications.csv"):
        medications[r["PATIENT"]].append({
            "code": r["CODE"],
            # medications.csv has a CODE column and no SYSTEM column. The file
            # does not say what vocabulary the code belongs to, so neither can
            # the summary built from it.
            "system": "",
            "display": r["DESCRIPTION"],
            "start": r["START"][:10],
            "stop": r["STOP"][:10],
        })

    results, vitals = defaultdict(list), defaultdict(list)
    org_of, last_enc = {}, {}
    with open(os.path.join(DATA, "observations.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            row = {
                "code": r["CODE"],
                # observations.csv likewise carries a CODE and no SYSTEM.
                "system": "",
                "display": r["DESCRIPTION"],
                "value": r["VALUE"],
                "unit": r["UNITS"],
                "date": r["DATE"][:10],
                "type": r["TYPE"],
            }
            if r["CODE"] in LAB_CODES:
                results[r["PATIENT"]].append(row)
            elif r["CODE"] in VITAL_CODES:
                vitals[r["PATIENT"]].append(row)

    for r in read("encounters.csv"):
        k, d = r["PATIENT"], r["START"][:10]
        if k not in last_enc or d > last_enc[k]:
            last_enc[k] = d
            org_of[k] = r["ORGANIZATION"]

    return patients, problems, medications, results, vitals, org_of, last_enc


# ----------------------------------------------------------------------
# building one summary
# ----------------------------------------------------------------------
def build_summary(pid, store, assume_no_allergies=False, declare_systems=False,
                  assert_empty_sections=False):
    """The patient summary as a plain dictionary, before any FHIR shaping.

    The three keyword arguments are the repairs in the --repair section. All
    three default to off, because none of them has been done to this cohort.
    """
    patients, problems, medications, results, vitals, org_of, last_enc = store
    p = patients[pid]

    meds = []
    for m in medications.get(pid, []):
        m = dict(m)
        if declare_systems:
            # RxNorm is what Synthea writes. Declaring it is a claim about the
            # file, made by the data holder, not something the file says.
            m["system"] = RXNORM
        meds.append(m)

    labs = []
    for r in results.get(pid, []):
        r = dict(r)
        if declare_systems:
            r["system"] = LOINC
        labs.append(r)

    probs = problems.get(pid, [])

    # The IPS way of saying a section is empty on purpose is an entry carrying
    # one of the absent-or-unknown codes, not an empty section. An empty
    # section means nobody looked. A clinician asserts these; a CSV cannot.
    absent = {}
    if assume_no_allergies:
        absent["allergies"] = ("no-known-allergies", "No known allergies")
    if assert_empty_sections:
        if not probs:
            absent["problems"] = ("no-known-problems", "No known problems")
        if not meds:
            absent["medications"] = ("no-known-medications", "No known medications")

    return {
        "patient_id": pid,
        "family": p["LAST"],
        "given": p["FIRST"],
        "birth_date": p["BIRTHDATE"][:10],
        "gender": GENDER.get(p["GENDER"], ""),
        "raw_gender": p["GENDER"],
        "country": "GR",
        "postcode": p["ZIP"],
        "custodian": org_of.get(pid, ""),
        "authored": AUTHORED,
        "sections": {
            "problems": probs,
            "allergies": [],
            "medications": meds,
            "immunisations": [],
            "results": labs,
            "vitals": vitals.get(pid, [])[-6:],
        },
        "absent": absent,
    }


def coding(code, system, display):
    c = {"code": code, "display": display}
    if system:
        c["system"] = system
    return {"coding": [c], "text": display}


def to_bundle(s):
    """The summary as a FHIR document Bundle, written by hand.

    A document Bundle is a Composition followed by every resource the
    Composition points at. The section entries below are references into the
    same Bundle, which is what makes it a document and not a pile of records.
    """
    entries, refs = [], defaultdict(list)

    def add(resource):
        rid = "%s-%d" % (resource["resourceType"].lower(), len(entries))
        resource["id"] = rid
        entries.append({"fullUrl": "urn:uuid:" + rid, "resource": resource})
        return "%s/%s" % (resource["resourceType"], rid)

    patient = {
        "resourceType": "Patient",
        "identifier": [{"system": "urn:oid:2.16.300.1", "value": s["patient_id"]}],
        "name": [{"family": s["family"], "given": [s["given"]]}],
        "birthDate": s["birth_date"],
        "address": [{"postalCode": s["postcode"], "country": s["country"]}],
    }
    if s["gender"]:
        patient["gender"] = s["gender"]
    patient_ref = add(patient)

    for pr in s["sections"]["problems"]:
        r = {
            "resourceType": "Condition",
            "clinicalStatus": coding("active" if not pr["abated"] else "resolved",
                                     "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                     "active" if not pr["abated"] else "resolved"),
            "code": coding(pr["code"], pr["system"], pr["display"]),
            "subject": {"reference": patient_ref},
            "onsetDateTime": pr["onset"],
        }
        refs["problems"].append(add(r))

    for m in s["sections"]["medications"]:
        r = {
            "resourceType": "MedicationStatement",
            "status": "active" if not m["stop"] else "completed",
            "medicationCodeableConcept": coding(m["code"], m["system"], m["display"]),
            "subject": {"reference": patient_ref},
            "effectivePeriod": {"start": m["start"]},
        }
        refs["medications"].append(add(r))

    for a in s["sections"]["allergies"]:
        refs["allergies"].append(add({
            "resourceType": "AllergyIntolerance",
            "code": coding(a["code"], a["system"], a["display"]),
            "patient": {"reference": patient_ref},
        }))
    ABSENT_TYPE = {"allergies": "AllergyIntolerance", "problems": "Condition",
                   "medications": "MedicationStatement"}
    for name, value in s["absent"].items():
        code, display = value
        refs[name].append(add({
            "resourceType": ABSENT_TYPE[name],
            "code": coding(code, ABSENT_CS, display),
            "subject": {"reference": patient_ref},
        }))

    for o in s["sections"]["results"] + s["sections"]["vitals"]:
        section = "results" if o["code"] in LAB_CODES else "vitals"
        r = {
            "resourceType": "Observation",
            "status": "final",
            "code": coding(o["code"], o["system"], o["display"]),
            "subject": {"reference": patient_ref},
            "effectiveDateTime": o["date"],
        }
        try:
            r["valueQuantity"] = {"value": float(o["value"]), "unit": o["unit"],
                                  "system": UCUM, "code": o["unit"]}
        except ValueError:
            r["valueString"] = o["value"]
        refs[section].append(add(r))

    sections = []
    for name in REQUIRED_SECTIONS + RECOMMENDED_SECTIONS + ["vitals"]:
        code, title = SECTION_CODES[name]
        sec = {"title": title, "code": coding(code, LOINC, title)}
        if refs[name]:
            sec["entry"] = [{"reference": r} for r in refs[name]]
        else:
            sec["emptyReason"] = coding(
                "unavailable", "http://terminology.hl7.org/CodeSystem/list-empty-reason",
                "Unavailable")
        sections.append(sec)

    composition = {
        "resourceType": "Composition",
        "status": "final",
        "type": coding(LOINC_COMPOSITION[0], LOINC, LOINC_COMPOSITION[1]),
        "subject": {"reference": patient_ref},
        "date": s["authored"],
        "title": "Patient Summary",
        "author": [{"display": s["custodian"] or "unknown"}],
        "custodian": {"display": s["custodian"] or "unknown"},
        "section": sections,
    }
    composition["id"] = "composition-0"
    entries.insert(0, {"fullUrl": "urn:uuid:composition-0", "resource": composition})

    return {
        "resourceType": "Bundle",
        "id": "ips-" + s["patient_id"][:8],
        "type": "document",
        "timestamp": s["authored"],
        "entry": entries,
    }


# ----------------------------------------------------------------------
# the validator
# ----------------------------------------------------------------------
# Each rule is (id, severity, description, function). Severity "required" is an
# element without which the document is not a patient summary. Severity
# "recommended" is an element the IPS asks for and tolerates the absence of.
def rules():
    def has(v):
        return bool(str(v or "").strip())

    def section_ok(s, name):
        return bool(s["sections"][name]) or bool(s["absent"].get(name))

    def all_coded(s, name):
        items = s["sections"][name]
        return all(has(i["code"]) and has(i["system"]) for i in items)

    return [
        ("H1", "required", "patient identifier present",
         lambda s: has(s["patient_id"])),
        ("H2", "required", "name present, family and given",
         lambda s: has(s["family"]) and has(s["given"])),
        ("H3", "required", "birth date present and ISO 8601",
         lambda s: len(s["birth_date"]) == 10 and s["birth_date"][4] == "-"),
        ("H4", "required", "administrative gender in the FHIR value set",
         lambda s: s["gender"] in ("male", "female", "other", "unknown")),
        ("H5", "required", "document date present",
         lambda s: has(s["authored"])),
        ("H6", "required", "custodian organisation named",
         lambda s: has(s["custodian"])),
        ("S1", "required", "problems section: an entry or an absent reason",
         lambda s: section_ok(s, "problems")),
        ("S2", "required", "allergies section: an entry or an absent reason",
         lambda s: section_ok(s, "allergies")),
        ("S3", "required", "medication section: an entry or an absent reason",
         lambda s: section_ok(s, "medications")),
        ("C1", "required", "every problem carries a code and a code system",
         lambda s: all_coded(s, "problems")),
        ("C2", "required", "every medication carries a code and a code system",
         lambda s: all_coded(s, "medications")),
        ("C3", "required", "every result: a code, a system and a UCUM unit",
         lambda s: all(has(i["code"]) and has(i["system"]) and i["unit"] in UCUM_UNITS
                       for i in s["sections"]["results"])),
        ("N1", "recommended", "immunisations section has an entry",
         lambda s: bool(s["sections"]["immunisations"])),
        ("N2", "recommended", "results section has at least one laboratory result",
         lambda s: bool(s["sections"]["results"])),
    ]


def validate(s, rs=None):
    """Return the set of rule ids this summary fails."""
    return {rid for rid, _sev, _d, fn in (rs or rules()) if not fn(s)}


def run_cohort(store, **kw):
    rs = rules()
    fails = Counter()
    complete = complete_with_recommended = 0
    for pid in store[0]:
        s = build_summary(pid, store, **kw)
        bad = validate(s, rs)
        for rid in bad:
            fails[rid] += 1
        hard = {rid for rid, sev, _d, _f in rs if sev == "required"}
        if not (bad & hard):
            complete += 1
            if not bad:
                complete_with_recommended += 1
    return fails, complete, complete_with_recommended


# ----------------------------------------------------------------------
# reports
# ----------------------------------------------------------------------
def report_sections(store):
    patients, problems, medications, results, vitals, org_of, _ = store
    n = len(patients)
    print("\nWHAT A EUROPEAN PATIENT SUMMARY HAS TO CONTAIN")
    print("""
  Article 14(1)(a) names the patient summary as a priority category. Article
  15(1) says the exchange format is harmonised datasets, coding systems and
  values, and technical interoperability specifications. The clinical content
  comes from the International Patient Summary, which marks three sections
  required, four recommended and the rest optional. Of the four recommended,
  two have a possible source in this cohort.

  Against each section, what the Lab 1 cohort can supply.""")
    have = {
        "problems": sum(1 for k in patients if problems.get(k)),
        "allergies": 0,
        "medications": sum(1 for k in patients if medications.get(k)),
        "immunisations": 0,
        "results": sum(1 for k in patients if results.get(k)),
        "vitals": sum(1 for k in patients if vitals.get(k)),
    }
    status = {"problems": "required", "allergies": "required", "medications": "required",
              "immunisations": "recommended", "results": "recommended",
              "vitals": "optional"}
    source = {"problems": "conditions.csv", "allergies": "no source file",
              "medications": "medications.csv", "immunisations": "no source file",
              "results": "observations.csv, laboratory",
              "vitals": "observations.csv, vital-signs"}
    print("\n  %-14s %-12s %-34s %8s %8s" %
          ("section", "status", "source in the cohort", "patients", "%"))
    for name in ["problems", "allergies", "medications", "immunisations", "results", "vitals"]:
        print("  %-14s %-12s %-34s %8d %7.1f%%" %
              (name, status[name], source[name], have[name], pct(have[name], n)))
    print("""
  Two of the three required sections have no source file. There is no allergy
  record anywhere in this cohort and no immunisation record anywhere in it.
  That is not a quirk of Synthea. It is the ordinary shape of data extracted
  from a hospital system for research: somebody chose five tables, and the
  three they did not choose are two thirds of what the summary requires.""")


def report_bundle(store):
    patients = store[0]
    # Pick a patient who exercises every section the cohort can fill: problems,
    # medications and laboratory results, and the most of each.
    best, best_key = None, None
    for pid in patients:
        s = build_summary(pid, store)
        key = (len(s["sections"]["problems"]), len(s["sections"]["medications"]),
               len(s["sections"]["results"]))
        if all(key) and (best_key is None or key > best_key):
            best, best_key = s, key
    bundle = to_bundle(best)
    text = json.dumps(bundle, indent=1)
    lines = text.splitlines()
    print("\nONE PATIENT, AS A FHIR DOCUMENT BUNDLE")
    print("  %s %s, born %s, %s" % (best["given"], best["family"],
                                    best["birth_date"], best["custodian"]))
    print("  %d problems, %d medications, %d laboratory results, %d vital signs"
          % (len(best["sections"]["problems"]), len(best["sections"]["medications"]),
             len(best["sections"]["results"]), len(best["sections"]["vitals"])))
    print("  %d resources in the Bundle, %d lines of JSON, %d bytes"
          % (len(bundle["entry"]), len(lines), len(text)))
    print("\n  The Composition, which is the document itself. The section entries are")
    print("  references into the same Bundle; their count is shown in place of the list.")
    comp = json.loads(json.dumps(bundle["entry"][0]["resource"]))
    for sec in comp["section"]:
        if "entry" in sec:
            sec["entry"] = "<%d references>" % len(sec["entry"])
        sec["code"] = sec["code"]["coding"][0]["code"]
    for line in json.dumps(comp, indent=1).splitlines():
        print("    " + line)

    print("\n  One problem entry and one medication entry, in full:")
    for want in ("Condition", "MedicationStatement"):
        res = next(e["resource"] for e in bundle["entry"]
                   if e["resource"]["resourceType"] == want)
        for line in json.dumps(res, indent=1).splitlines():
            print("    " + line)
    print("""
  Read the two coding blocks against each other. The Condition carries
  "system": "http://snomed.info/sct" and a SNOMED CT concept id. The
  MedicationStatement carries a code and no system, because medications.csv has
  a CODE column and no SYSTEM column. A receiving system in another Member
  State can resolve the first and cannot resolve the second.""")


def report_rules():
    print("\nTHE CHECKS")
    print("""
  Twelve required and two recommended. The required ones are the elements
  without which the document is not a patient summary; the recommended ones are
  elements the IPS asks for and tolerates the absence of.""")
    print("\n  %-5s %-12s %s" % ("id", "severity", "check"))
    for rid, sev, desc, _fn in rules():
        print("  %-5s %-12s %s" % (rid, sev, desc))


def report_validate(store):
    rs = rules()
    fails, complete, complete_rec = run_cohort(store)
    n = len(store[0])
    print("\nRUNNING THE CHECKS OVER ALL %d PATIENTS" % n)
    print("\n  %-5s %-12s %-49s %8s %8s" %
          ("id", "severity", "check", "failing", "%"))
    for rid, sev, desc, _fn in rs:
        print("  %-5s %-12s %-49s %8d %7.1f%%" %
              (rid, sev, desc, fails[rid], pct(fails[rid], n)))
    print("\n  patients with a complete summary, required checks only    %6d  %6.1f%%"
          % (complete, pct(complete, n)))
    print("  patients passing required and recommended                 %6d  %6.1f%%"
          % (complete_rec, pct(complete_rec, n)))
    ranked = sorted(((fails[rid], rid, sev) for rid, sev, _d, _f in rs if fails[rid]),
                    reverse=True)
    print("\n  The required elements missing most often:")
    for cnt, rid, sev in [r for r in ranked if r[2] == "required"][:4]:
        desc = next(d for i, _s, d, _f in rs if i == rid)
        print("    %-5s %-49s %6d  %5.1f%%" % (rid, desc, cnt, pct(cnt, n)))
    print("""
  Not one patient in the cohort can produce a patient summary that passes, and
  the six header checks are not the reason. Every patient has an identifier, a
  name, a birth date, a gender that maps to the FHIR value set, a document date
  and a named custodian organisation. The failures are all in the clinical
  sections, and they fall into three kinds.

  A missing table. S2 fails for every patient because there is no allergy file,
  and N1 fails for every patient because there is no immunisation file. Nothing
  in the five CSVs can fix this; somebody has to extract a sixth table.

  A missing declaration. C2 fails for the %d patients who have a prescription
  and C3 for the %d who have a laboratory result, because medications.csv and
  observations.csv carry a CODE column and no SYSTEM column. The data is there.
  The file does not say what vocabulary it is in, so the value cannot be
  resolved by anybody who did not already know.

  A missing assertion. S1 fails for the %d patients with no entry in
  conditions.csv and S3 for the %d with no entry in medications.csv. An empty
  required section is not a patient with no problems. It is a document that
  does not say whether anybody looked.""" %
          (fails["C2"], fails["C3"], fails["S1"], fails["S3"]))


def report_coding(store):
    patients, problems, medications, results, vitals, _o, _l = store
    print("\nTHE CODE SYSTEMS THIS COHORT ACTUALLY USES")
    print("""
  Article 15(1)(b) makes coding systems and values part of the exchange format,
  on the same footing as the datasets themselves. A summary with the right
  information in the right section and the wrong vocabulary does not exchange.""")
    rows = []
    sysc = Counter()
    codes = Counter()
    for v in problems.values():
        for i in v:
            sysc[("problems", i["system"] or "(none recorded)")] += 1
            codes[("problems", i["code"])] += 1
    for v in medications.values():
        for i in v:
            sysc[("medications", i["system"] or "(none recorded)")] += 1
            codes[("medications", i["code"])] += 1
    for v in results.values():
        for i in v:
            sysc[("results", i["system"] or "(none recorded)")] += 1
            codes[("results", i["code"])] += 1
    for v in vitals.values():
        for i in v:
            sysc[("vitals", i["system"] or "(none recorded)")] += 1
            codes[("vitals", i["code"])] += 1
    print("\n  %-14s %-44s %9s %9s" %
          ("section", "code system recorded in the file", "entries", "codes"))
    for (sec, sysname), cnt in sorted(sysc.items()):
        ncodes = len({c for (s, c) in codes if s == sec})
        print("  %-14s %-44s %9d %9d" % (sec, sysname, cnt, ncodes))
    meds_seen = Counter()
    for v in medications.values():
        for i in v:
            meds_seen[(i["code"], i["display"])] += 1
    print("\n  The six medication codes in the cohort, as the file writes them:")
    print("    %-10s %-56s %8s" % ("code", "description", "rows"))
    for (code, disp), cnt in sorted(meds_seen.items()):
        print("    %-10s %-56s %8d" % (code, disp[:56], cnt))
    print("""
  The conditions file names its vocabulary in a SYSTEM column and the other two
  do not. The values give the vocabularies away: the medication codes are
  RxNorm identifiers and the observation codes are LOINC. Both are correct
  codes in a real vocabulary, and neither is declared.

  LOINC is the right answer for a laboratory result and is used by MyHealth@EU.
  RxNorm is a United States drug vocabulary. The HL7 Europe prescription and
  dispense guide, which is the European profile behind MyHealth@EU, builds on
  EDQM Standard Terms for dose forms and routes, UCUM for units, SNOMED CT and
  the EMA substance services for the product itself, and says ATC is not
  recommended for medication codes because it is too coarse. RxNorm is not in
  that list. A Greek prescription carrying RxNorm 314076 arrives in a Cypriot
  pharmacy as a number nobody has a table for.

  This is Week 5 arriving with a legal deadline attached. The coding problem is
  the same problem. What changed is that from 26 March 2029 the patient has a
  right under Article 7 to have the thing exchanged, and getting the vocabulary
  wrong is the reason it will not be.""")


def hollow(store):
    """Patients whose repaired summary carries no clinical entry at all.

    Every required section satisfied by an assertion of absence, nothing in
    results, nothing in immunisations. The only real observation is a vital
    sign, which the IPS treats as optional.
    """
    _p, problems, medications, results, _v, _o, _l = store
    return sum(1 for pid in store[0]
               if not problems.get(pid) and not medications.get(pid)
               and not results.get(pid))


def report_repair(store):
    n = len(store[0])
    print("\nFOUR REPAIRS")
    print("""
  Take the failures one kind at a time and fix the ones that can be fixed
  without collecting anything new.

  Repair 1. Declare the medication code system. The data holder states that
  medications.csv is coded in RxNorm and the summary carries the system URI.
  One line of metadata.

  Repair 2. Declare the observation code system as LOINC, the same way.

  Repair 3. Assert no known allergies, as an entry carrying the IPS
  no-known-allergies code.

  Repair 4. Assert no known problems and no known medications for the patients
  whose problem list or medication list is empty, the same way.

  Repairs 1 and 2 are statements about a file. Repairs 3 and 4 are clinical
  statements about a person, and somebody has to be willing to sign them.""")
    settings = [
        ("as extracted", {}),
        ("1 and 2, code systems declared", {"declare_systems": True}),
        ("3, no known allergies asserted", {"assume_no_allergies": True}),
        ("1, 2 and 3", {"declare_systems": True, "assume_no_allergies": True}),
        ("all four", {"declare_systems": True, "assume_no_allergies": True,
                      "assert_empty_sections": True}),
    ]
    hard = {rid for rid, sev, _d, _f in rules() if sev == "required"}
    soft = {rid for rid, sev, _d, _f in rules() if sev == "recommended"}
    print("\n  %-34s %9s %8s %16s %14s" %
          ("repairs applied", "complete", "%", "required failing", "rec. failing"))
    final = None
    for label, kw in settings:
        fails, complete, _rec = run_cohort(store, **kw)
        still = ",".join(sorted(rid for rid in hard if fails[rid])) or "none"
        stills = ",".join(sorted(rid for rid in soft if fails[rid])) or "none"
        print("  %-34s %9d %7.1f%% %16s %14s" %
              (label, complete, pct(complete, n), still, stills))
        final = (fails, complete)
    fails, complete = final
    base = run_cohort(store)[1]
    print("""
  Neither metadata repair helps on its own, because the sections they fix are
  not the sections that were empty. Neither assertion helps on its own, because
  the codes they leave undeclared are still undeclared. Applied together, all
  four take the cohort from %d complete summaries to %d, which is %.1f%% of
  %d patients.

  Now read the last column. N1 still fails for all %d patients, because no
  repair invents an immunisation record. The document validates and it tells a
  receiving clinician in another Member State nothing about this patient's
  vaccinations, and it does not tell them that it is not telling them.

  Three of the four repairs were assertions that something is absent, and for
  %d patients in this cohort that is the entire clinical content of the
  document: no problems, no medications, no allergies, no immunisations, no
  laboratory result, and a blood pressure. Conformance is not completeness, and
  the validator cannot tell the difference. The person who signs the assertion
  can.""" %
          (base, complete, pct(complete, n), n, fails["N1"], hollow(store)))


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("sections", "bundle", "rules", "validate", "coding", "repair"):
        ap.add_argument("--" + flag, action="store_true")
    args = ap.parse_args()
    flags = [args.sections, args.bundle, args.rules, args.validate,
             args.coding, args.repair]
    run_all = not any(flags)

    store = load()
    if args.sections or run_all:
        report_sections(store)
    if args.bundle or run_all:
        report_bundle(store)
    if args.rules or run_all:
        report_rules()
    if args.validate or run_all:
        report_validate(store)
    if args.coding or run_all:
        report_coding(store)
    if args.repair or run_all:
        report_repair(store)


if __name__ == "__main__":
    main()
