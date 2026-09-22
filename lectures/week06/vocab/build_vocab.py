"""Build the teaching vocabulary shipped in this folder.

You do not need to run this. The three CSV files beside it are committed, and
etl.py reads them. It is here so that nothing in the vocabulary is unexplained:
every row in concept.csv, concept_relationship.csv and concept_ancestor.csv
comes out of this script, and you can see exactly what was decided and why.

WHAT THIS IS NOT
----------------
This is not the OMOP standardised vocabulary. The real one is several
gigabytes, comes from athena.ohdsi.org, and requires you to accept the licence
terms of each vocabulary you download. Nothing here is a substitute for it.

CONCEPT IDS
-----------
Two kinds appear in these files.

1. A short list of real OMOP standard concept ids, reused so that the SQL on
   the lecture slides runs against this database unchanged. They are listed in
   REUSED_OMOP_IDS below.

2. Everything else is minted locally in the range at or above 2,000,000,000,
   which OMOP reserves for exactly this purpose: concepts you create yourself,
   guaranteed never to collide with a real one. Local ids are assigned in
   sorted order, so this script is reproducible.

If you see a concept_id below 2,000,000,000 that is not in REUSED_OMOP_IDS,
something has gone wrong.

THE DELIBERATE GAP
------------------
A real ETL always has an unmapped tail: local laboratory codes, local drug
codes, free text that never had a code. This synthetic cohort has none, because
every code in it is already a standard SNOMED, LOINC or RxNorm code. A CDM with
a zero unmapped fraction would teach the wrong lesson, so a small number of
codes are withheld from the vocabulary on purpose. See WITHHELD below, and see
the note in README.md before you conclude anything from the number.
"""

from __future__ import annotations

import csv
import os
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "labs", "lab01", "data"))

TODAY_START = "1970-01-01"
TODAY_END = "2099-12-31"

# Real OMOP standard concept ids, reused so the slide SQL runs here unchanged.
REUSED_OMOP_IDS = {
    316866: "Hypertensive disorder",
    320128: "Essential hypertension",
    201820: "Diabetes mellitus",
    201826: "Type 2 diabetes mellitus",
    9201: "Inpatient Visit",
    9202: "Outpatient Visit",
    9203: "Emergency Room Visit",
    8507: "MALE",
    8532: "FEMALE",
}

# Source codes deliberately left out of the vocabulary, so that the unmapped
# fraction is not zero. Both are ordinary SNOMED codes; there is nothing wrong
# with them. They stand in for the local codes a real hospital extract carries.
WITHHELD = {"196416002", "444814009"}

LOCAL_ID_BASE = 2_000_000_000

# Source code -> the real OMOP standard concept it maps to, where we reuse one.
CONDITION_TO_REUSED = {
    "38341003": 316866,   # Hypertensive disorder, systemic arterial
    "59621000": 320128,   # Essential hypertension
    "44054006": 201826,   # Type 2 diabetes mellitus
}

# Codes from conditions.csv whose standard concept sits in the Observation
# domain, not the Condition domain. This is not a trick: in the real OMOP
# vocabulary, findings like these are Observation concepts, and an ETL that
# routes by the source table rather than by the mapped concept's domain puts
# them in the wrong place. etl.py routes by domain, so they land in
# `observation`. That is the point.
CONDITION_DOMAIN_OVERRIDE = {
    "162864005": "Observation",   # Body mass index 30+ - obesity (finding)
    "72892002": "Observation",    # Normal pregnancy (finding)
    "15777000": "Observation",    # Prediabetes (finding)
}

# LOINC codes that are a question with a categorical answer rather than a
# quantity. They belong in `observation`, not `measurement`.
MEASUREMENT_DOMAIN_OVERRIDE = {
    "72166-2": "Observation",     # Tobacco smoking status NHIS
}

# A small, hand-written hierarchy. Parents that are not themselves in the data
# are minted here. Every relationship below is true in SNOMED CT; this is a
# subset of concept_ancestor, not a replacement for it.
HIERARCHY_PARENTS = [
    # (parent name, parent source code or None, reused OMOP id or None, [child source codes])
    ("Hypertensive disorder", "38341003", None, ["59621000"]),
    ("Diabetes mellitus", "73211009", 201820, ["44054006"]),
    ("Disorder of respiratory system", "50043002", None,
     ["233678006", "40055000", "195662009", "444814009"]),
]

# Encounter class -> visit concept. Three real OMOP visit concepts, plus one
# local concept for the classes that have no clean standard equivalent here.
VISIT_MAP = {
    "inpatient": 9201,
    "outpatient": 9202,
    "ambulatory": 9202,
    "wellness": 9202,
    "emergency": 9203,
    "urgentcare": 9203,
}

# Type concepts. Locally minted: the real ones are standard concepts in the
# Type Concept vocabulary and we are not shipping it.
TYPE_CONCEPTS = [
    ("EHR encounter record", "Type Concept"),
    ("EHR problem list entry", "Type Concept"),
    ("EHR order", "Type Concept"),
    ("Lab result", "Type Concept"),
    ("Patient reported", "Type Concept"),
    ("EHR death record", "Type Concept"),
]

UNIT_NAMES = {
    "mm[Hg]": "millimeter mercury column",
    "kg": "kilogram",
    "mg/dL": "milligram per deciliter",
}


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    concepts = OrderedDict()   # concept_id -> row dict
    relationships = []         # (concept_id_1, concept_id_2, relationship_id)
    ancestors = []             # (ancestor, descendant, min_levels, max_levels)
    next_local = [LOCAL_ID_BASE + 1]

    def add(concept_id, name, domain, vocab, cls, standard, code):
        concepts[concept_id] = {
            "concept_id": concept_id,
            "concept_name": name,
            "domain_id": domain,
            "vocabulary_id": vocab,
            "concept_class_id": cls,
            "standard_concept": standard,
            "concept_code": code,
            "valid_start_date": TODAY_START,
            "valid_end_date": TODAY_END,
            "invalid_reason": "",
        }
        return concept_id

    def mint(name, domain, vocab, cls, standard, code):
        cid = next_local[0]
        next_local[0] += 1
        return add(cid, name, domain, vocab, cls, standard, code)

    def clean(desc):
        for suffix in (" (disorder)", " (finding)", " (procedure)"):
            if desc.endswith(suffix):
                return desc[: -len(suffix)]
        return desc

    # ---- conditions -------------------------------------------------------
    by_code = OrderedDict()
    for row in read("conditions.csv"):
        by_code.setdefault(row["CODE"], row["DESCRIPTION"])
    code_to_concept = {}
    for code in sorted(by_code):
        if code in WITHHELD:
            continue
        name = clean(by_code[code])
        domain = CONDITION_DOMAIN_OVERRIDE.get(code, "Condition")
        if code in CONDITION_TO_REUSED:
            cid = CONDITION_TO_REUSED[code]
            add(cid, REUSED_OMOP_IDS[cid], domain, "SNOMED", "Clinical Finding", "S", code)
        else:
            cid = mint(name, domain, "SNOMED", "Clinical Finding", "S", code)
        code_to_concept[code] = cid

    # ---- observations: LOINC ---------------------------------------------
    obs_rows = read("observations.csv")
    obs_codes = OrderedDict()
    for row in obs_rows:
        obs_codes.setdefault(row["CODE"], (row["DESCRIPTION"], row["UNITS"], row["TYPE"]))
    for code in sorted(obs_codes):
        name, _unit, _kind = obs_codes[code]
        domain = MEASUREMENT_DOMAIN_OVERRIDE.get(code, "Measurement")
        code_to_concept[code] = mint(name, domain, "LOINC", "Lab Test", "S", code)

    # ---- medications: RxNorm ---------------------------------------------
    med_codes = OrderedDict()
    for row in read("medications.csv"):
        med_codes.setdefault(row["CODE"], row["DESCRIPTION"])
    for code in sorted(med_codes):
        code_to_concept[code] = mint(med_codes[code], "Drug", "RxNorm", "Clinical Drug", "S", code)

    # ---- visits, gender, units, types ------------------------------------
    for cid, name in ((9201, "Inpatient Visit"), (9202, "Outpatient Visit"),
                      (9203, "Emergency Room Visit")):
        add(cid, name, "Visit", "Visit", "Visit", "S", name.replace(" ", "_").upper())
    add(8507, "MALE", "Gender", "Gender", "Gender", "S", "M")
    add(8532, "FEMALE", "Gender", "Gender", "Gender", "S", "F")
    unit_ids = {}
    for unit in sorted(u for u in UNIT_NAMES):
        unit_ids[unit] = mint(UNIT_NAMES[unit], "Unit", "UCUM", "Unit", "S", unit)
    type_ids = {}
    for name, vocab in TYPE_CONCEPTS:
        type_ids[name] = mint(name, "Type Concept", vocab, "Type Concept", "S", name)

    # ---- 'Maps to' --------------------------------------------------------
    # In the real vocabulary every standard concept has a 'Maps to' row
    # pointing at itself, and every non-standard source concept has one
    # pointing at its standard equivalent. etl.py follows these rows rather
    # than matching on concept_code, because that is what a real ETL does.
    for cid, row in concepts.items():
        if row["standard_concept"] == "S":
            relationships.append((cid, cid, "Maps to"))

    # ---- concept_ancestor -------------------------------------------------
    for cid, row in concepts.items():
        if row["domain_id"] in ("Condition", "Observation", "Measurement", "Drug"):
            ancestors.append((cid, cid, 0, 0))
    for parent_name, parent_code, reuse_id, children in HIERARCHY_PARENTS:
        if parent_code in code_to_concept:
            pid = code_to_concept[parent_code]
        elif reuse_id is not None:
            pid = add(reuse_id, parent_name, "Condition", "SNOMED",
                      "Clinical Finding", "S", parent_code)
            ancestors.append((pid, pid, 0, 0))
            relationships.append((pid, pid, "Maps to"))
        else:
            pid = mint(parent_name, "Condition", "SNOMED", "Clinical Finding", "S", parent_code)
            ancestors.append((pid, pid, 0, 0))
            relationships.append((pid, pid, "Maps to"))
        for child_code in children:
            child = code_to_concept.get(child_code)
            if child is None:
                continue          # a withheld code has no concept to hang under
            if child == pid:
                continue
            ancestors.append((pid, child, 1, 1))

    # ---- write ------------------------------------------------------------
    out = os.path.join(HERE, "concept.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(next(iter(concepts.values())).keys()))
        w.writeheader()
        for cid in sorted(concepts):
            w.writerow(concepts[cid])
    with open(os.path.join(HERE, "concept_relationship.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["concept_id_1", "concept_id_2", "relationship_id",
                    "valid_start_date", "valid_end_date", "invalid_reason"])
        for a, b, rel in sorted(set(relationships)):
            w.writerow([a, b, rel, TODAY_START, TODAY_END, ""])
    with open(os.path.join(HERE, "concept_ancestor.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ancestor_concept_id", "descendant_concept_id",
                    "min_levels_of_separation", "max_levels_of_separation"])
        for row in sorted(set(ancestors)):
            w.writerow(row)

    print("concepts            %5d" % len(concepts))
    print("  reused OMOP ids   %5d" % sum(1 for c in concepts if c < LOCAL_ID_BASE))
    print("  locally minted    %5d" % sum(1 for c in concepts if c >= LOCAL_ID_BASE))
    print("'Maps to' rows      %5d" % len(set(relationships)))
    print("ancestor rows       %5d" % len(set(ancestors)))
    print("withheld codes      %5d  (%s)" % (len(WITHHELD), ", ".join(sorted(WITHHELD))))


if __name__ == "__main__":
    main()
