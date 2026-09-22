#!/usr/bin/env python3
"""HY-489 Week 6: load the Lab 1 cohort into a miniature OMOP CDM.

    python3 etl.py                 # builds cdm.db beside this file
    python3 etl.py --db /tmp/x.db  # somewhere else

This is a real ETL in miniature. It reads the Synthea-shaped CSV export in
../../labs/lab01/data, maps every source code through the vocabulary in ./vocab, and
writes eight CDM tables into SQLite. It prints a load report: rows in, rows
out, rows unmapped. Read that report. It is the deliverable, not the database.

THE SIX DECISIONS
-----------------
Every ETL makes these, whether or not it writes them down. This one writes
them down, which is the whole difference. Each is marked DECISION in the code.

  1. Who is a person       one row per source patient id, no deduplication
  2. What counts as observed  first to last encounter date, no grace period
  3. Which date            the source START date, no time component
  4. Unmapped codes        concept_id 0 and keep the row. Never drop.
  5. Visit rollup          one source encounter, one visit. No rollup.
  6. What not to load      payers, costs, providers, organisations, addresses

Any of the six could defensibly have gone the other way. What is not
defensible is making the choice by accident and not recording it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sqlite3
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))
VOCAB = os.path.join(HERE, "vocab")
SCHEMA = os.path.join(HERE, "cdm", "schema.sql")

CDM_VERSION = "v5.4 (teaching subset)"
VOCAB_VERSION = "HY-489 teaching vocabulary, built by vocab/build_vocab.py"

# DECISION 5: source encounter class -> visit concept. Six source classes
# collapse onto three standard visit concepts, which loses the distinction
# between an urgent-care attendance and an emergency department attendance.
# Recorded here so that anyone comparing our emergency counts with another
# site's knows what went into them.
VISIT_MAP = {
    "inpatient": 9201,
    "outpatient": 9202,
    "ambulatory": 9202,
    "wellness": 9202,
    "emergency": 9203,
    "urgentcare": 9203,
}

GENDER_MAP = {"M": 8507, "F": 8532}


# --------------------------------------------------------------- utilities

def read_csv(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        sys.exit(
            "Cannot find %s\n"
            "This script reads the Lab 1 data from ../../labs/lab01/data.\n"
            "Clone the whole hy489 repository rather than this folder alone." % path
        )
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            yield row


def read_vocab(name):
    with open(os.path.join(VOCAB, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def person_id_for(source_id: str) -> int:
    """DECISION 1, and the part that makes results reproducible.

    person_id is a stable hash of the source identifier, not a counter. Rerun
    the ETL, reload from scratch, load the files in a different order: the same
    patient gets the same person_id every time. A counter would give you a
    different person_id on every full reload, and a cohort you exported last
    month could not be compared with one you export today.
    """
    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)          # 48 bits, comfortably unique here


def date_only(value: str) -> str:
    return (value or "")[:10]


# ------------------------------------------------------------------ mapping

class Vocabulary:
    """The vocabulary, and the only way source codes become concepts.

    Note what this class does NOT do: match on concept_code directly. It
    follows 'Maps to' rows in concept_relationship, because that is what a real
    ETL has to do. Most SNOMED and LOINC concepts map to themselves; some map
    to a different concept; some have no valid map at all and give you a 0.
    """

    def __init__(self):
        self.concepts = {}
        for row in read_vocab("concept.csv"):
            row["concept_id"] = int(row["concept_id"])
            self.concepts[row["concept_id"]] = row
        self.by_code = {}
        for row in self.concepts.values():
            self.by_code[(row["vocabulary_id"], row["concept_code"])] = row["concept_id"]
        self.maps_to = {}
        for row in read_vocab("concept_relationship.csv"):
            if row["relationship_id"] == "Maps to" and not row["invalid_reason"]:
                self.maps_to[int(row["concept_id_1"])] = int(row["concept_id_2"])

    def lookup(self, vocabulary_id: str, code: str):
        """Return (standard_concept_id, source_concept_id, domain_id).

        standard_concept_id is 0 when the code is not in the vocabulary or has
        no valid 'Maps to'. The row still gets loaded. Dropping it would make
        the CDM look cleaner and destroy the evidence that anything was there.
        """
        source_id = self.by_code.get((vocabulary_id, code))
        if source_id is None:
            return 0, 0, None
        target = self.maps_to.get(source_id, 0)
        domain = self.concepts[target]["domain_id"] if target else None
        return target, source_id, domain


# ---------------------------------------------------------------- the load

class Report:
    """Rows in, rows out, rows unmapped. Build this before anything else."""

    def __init__(self):
        self.rows_in = Counter()
        self.rows_out = Counter()
        self.unmapped = Counter()
        self.unmapped_codes = defaultdict(Counter)
        self.skipped = Counter()
        self.routed = Counter()

    def note_unmapped(self, table, code, description):
        self.unmapped[table] += 1
        self.unmapped_codes[table][(code, description)] += 1

    def print(self):
        print()
        print("LOAD REPORT")
        print("=" * 74)
        print("%-24s %10s %10s %10s %9s" % ("table", "rows in", "loaded", "unmapped", "unmapped%"))
        print("-" * 74)
        total_out = total_unmapped = 0
        for table in ("person", "observation_period", "visit_occurrence",
                      "condition_occurrence", "drug_exposure", "measurement",
                      "observation", "death"):
            out = self.rows_out[table]
            unm = self.unmapped[table]
            pct = (100.0 * unm / out) if out else 0.0
            print("%-24s %10s %10d %10d %8.1f%%" % (
                table, self.rows_in.get(table, "-"), out, unm, pct))
            total_out += out
            total_unmapped += unm
        print("-" * 74)
        print("%-24s %10s %10d %10d %8.1f%%" % (
            "all clinical tables", "", total_out, total_unmapped,
            100.0 * total_unmapped / total_out if total_out else 0.0))
        if self.routed:
            print()
            print("Rows routed by the mapped concept's domain, not by source file:")
            for note, n in self.routed.most_common():
                print("  %-58s %6d" % (note, n))
        if self.skipped:
            print()
            print("Rows not loaded, and why:")
            for reason, n in self.skipped.most_common():
                print("  %-58s %6d" % (reason, n))
        if self.unmapped_codes:
            print()
            print("The unmapped tail, by source code:")
            for table in sorted(self.unmapped_codes):
                for (code, desc), n in self.unmapped_codes[table].most_common(10):
                    print("  %-22s %-12s %-34s %6d" % (table, code, desc[:34], n))
        print()
        print("Every unmapped row was KEPT, with concept_id 0 and its source value")
        print("intact. That is decision 4, and it is the one to argue about.")
        print()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.path.join(HERE, "cdm.db"),
                    help="where to write the database (default: ./cdm.db)")
    ap.add_argument("--no-observation-period", action="store_true",
                    help="skip the observation_period derivation, to see what breaks")
    args = ap.parse_args()

    if os.path.exists(args.db):
        os.remove(args.db)
    con = sqlite3.connect(args.db)
    with open(SCHEMA, encoding="utf-8") as fh:
        con.executescript(fh.read())

    vocab = Vocabulary()
    rep = Report()

    # ---- vocabulary tables ------------------------------------------------
    con.executemany(
        "INSERT INTO concept VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(r["concept_id"], r["concept_name"], r["domain_id"], r["vocabulary_id"],
          r["concept_class_id"], r["standard_concept"] or None, r["concept_code"],
          r["valid_start_date"], r["valid_end_date"], r["invalid_reason"] or None)
         for r in vocab.concepts.values()])
    con.executemany(
        "INSERT INTO concept_relationship VALUES (?,?,?,?,?,?)",
        [(int(r["concept_id_1"]), int(r["concept_id_2"]), r["relationship_id"],
          r["valid_start_date"], r["valid_end_date"], r["invalid_reason"] or None)
         for r in read_vocab("concept_relationship.csv")])
    con.executemany(
        "INSERT INTO concept_ancestor VALUES (?,?,?,?)",
        [(int(r["ancestor_concept_id"]), int(r["descendant_concept_id"]),
          int(r["min_levels_of_separation"]), int(r["max_levels_of_separation"]))
         for r in read_vocab("concept_ancestor.csv")])

    def type_concept(name):
        return vocab.by_code[("Type Concept", name)]

    T_ENC = type_concept("EHR encounter record")
    T_PROBLEM = type_concept("EHR problem list entry")
    T_ORDER = type_concept("EHR order")
    T_LAB = type_concept("Lab result")
    T_PATIENT = type_concept("Patient reported")
    T_DEATH = type_concept("EHR death record")

    # ---- person and death -------------------------------------------------
    persons = {}
    person_rows, death_rows = [], []
    for row in read_csv("patients.csv"):
        rep.rows_in["person"] += 1
        pid = person_id_for(row["Id"])
        if pid in persons:
            rep.skipped["duplicate person_id after hashing"] += 1
            continue
        persons[row["Id"]] = pid
        birth = row["BIRTHDATE"]
        if not birth:
            rep.skipped["patient with no birth date"] += 1
            continue
        gender = GENDER_MAP.get(row["GENDER"], 0)
        if gender == 0:
            rep.note_unmapped("person", row["GENDER"] or "(empty)", "gender")
        person_rows.append((
            pid, gender, int(birth[:4]), int(birth[5:7]), int(birth[8:10]),
            0,      # DECISION 6: race is not loaded. It is in the source, it is
            0,      # sensitive, and no question this course asks needs it. An
                    # ETL that loads a column "because it is there" is how
                    # identifying data ends up in a research warehouse.
            row["Id"], row["GENDER"]))
        if row["DEATHDATE"]:
            death_rows.append((pid, date_only(row["DEATHDATE"]), T_DEATH, None))
    con.executemany("INSERT INTO person VALUES (?,?,?,?,?,?,?,?,?)", person_rows)
    con.executemany("INSERT INTO death VALUES (?,?,?,?)", death_rows)
    rep.rows_out["person"] = len(person_rows)
    rep.rows_out["death"] = len(death_rows)

    # ---- visits -----------------------------------------------------------
    visits = {}
    visit_rows = []
    spans = defaultdict(lambda: [None, None])
    for row in read_csv("encounters.csv"):
        rep.rows_in["visit_occurrence"] += 1
        pid = persons.get(row["PATIENT"])
        if pid is None:
            rep.skipped["encounter for a patient not in person"] += 1
            continue
        vid = person_id_for(row["Id"])
        visits[row["Id"]] = vid
        concept = VISIT_MAP.get(row["ENCOUNTERCLASS"], 0)
        if concept == 0:
            rep.note_unmapped("visit_occurrence", row["ENCOUNTERCLASS"], "encounter class")
        start, end = date_only(row["START"]), date_only(row["STOP"])
        visit_rows.append((vid, pid, concept, start, end or None, T_ENC,
                           row["ENCOUNTERCLASS"]))
        span = spans[pid]
        if span[0] is None or start < span[0]:
            span[0] = start
        if span[1] is None or (end or start) > span[1]:
            span[1] = end or start
    con.executemany("INSERT INTO visit_occurrence VALUES (?,?,?,?,?,?,?)", visit_rows)
    rep.rows_out["visit_occurrence"] = len(visit_rows)

    # ---- observation_period ----------------------------------------------
    # DECISION 2, and the most consequential one in the file.
    #
    # The source has no enrolment table, so observability has to be inferred.
    # We take first contact to last contact, with no grace period at either
    # end. That choice biases two ways, and you should be able to state both:
    #
    #   * a patient becomes observable on the day of their first visit, so any
    #     incidence you compute in that first period is artificially low;
    #   * a patient stops being observable at their last visit, so anyone who
    #     moved away, or is simply healthy, leaves the denominator early.
    #
    # A claims database would not need this guess. That is why the model has
    # the table, and why every ETL over an EHR has to publish its rule.
    if not args.no_observation_period:
        op_rows = [(person_id_for("op:" + str(pid)), pid, s, e, T_ENC)
                   for pid, (s, e) in sorted(spans.items()) if s]
        con.executemany("INSERT INTO observation_period VALUES (?,?,?,?,?)", op_rows)
        rep.rows_out["observation_period"] = len(op_rows)
        rep.rows_in["observation_period"] = len(spans)
    else:
        print("!! observation_period skipped on purpose (--no-observation-period)")

    # ---- conditions -------------------------------------------------------
    # DECISION and the lesson of the week: the row is routed by the DOMAIN of
    # the concept it maps to, not by which source file it came out of. Some
    # codes in conditions.csv are findings whose standard concept lives in the
    # Observation domain, and they belong in `observation`. An ETL that loads
    # conditions.csv straight into condition_occurrence puts them where no
    # study will ever look for them.
    cond_rows, cond_as_obs = [], []
    for i, row in enumerate(read_csv("conditions.csv"), start=1):
        rep.rows_in["condition_occurrence"] += 1
        pid = persons.get(row["PATIENT"])
        if pid is None:
            rep.skipped["condition for a patient not in person"] += 1
            continue
        concept, source_concept, domain = vocab.lookup("SNOMED", row["CODE"])
        if concept == 0:
            rep.note_unmapped("condition_occurrence", row["CODE"], row["DESCRIPTION"])
        target = cond_rows if domain != "Observation" else cond_as_obs
        target.append((
            i, pid, concept, date_only(row["START"]), date_only(row["STOP"]) or None,
            T_PROBLEM, visits.get(row["ENCOUNTER"]), row["CODE"], source_concept))
    con.executemany("INSERT INTO condition_occurrence VALUES (?,?,?,?,?,?,?,?,?)", cond_rows)
    rep.rows_out["condition_occurrence"] = len(cond_rows)

    # ---- drugs ------------------------------------------------------------
    # DECISION: these rows are prescriptions, so the type concept says so. They
    # are not evidence that anyone swallowed anything.
    drug_rows = []
    for i, row in enumerate(read_csv("medications.csv"), start=1):
        rep.rows_in["drug_exposure"] += 1
        pid = persons.get(row["PATIENT"])
        if pid is None:
            rep.skipped["medication for a patient not in person"] += 1
            continue
        concept, source_concept, _domain = vocab.lookup("RxNorm", row["CODE"])
        if concept == 0:
            rep.note_unmapped("drug_exposure", row["CODE"], row["DESCRIPTION"])
        drug_rows.append((
            i, pid, concept, date_only(row["START"]), date_only(row["STOP"]) or None,
            T_ORDER, float(row["DISPENSES"] or 0) or None,
            visits.get(row["ENCOUNTER"]), row["CODE"], source_concept))
    con.executemany("INSERT INTO drug_exposure VALUES (?,?,?,?,?,?,?,?,?,?)", drug_rows)
    rep.rows_out["drug_exposure"] = len(drug_rows)

    # ---- measurements and observations ------------------------------------
    # Same routing rule. A LOINC code with a numeric answer is a measurement; a
    # LOINC code whose answer is a category is an observation. The vocabulary
    # decides, not the source file, and not us.
    meas_rows = []
    obs_rows = [(oid, pid, c, start, T_PROBLEM, None, None, None, None, vis, sv, sc)
                for (oid, pid, c, start, _end, _t, vis, sv, sc) in cond_as_obs]
    next_obs_id = 10_000_000
    for i, row in enumerate(read_csv("observations.csv"), start=1):
        pid = persons.get(row["PATIENT"])
        concept, source_concept, domain = vocab.lookup("LOINC", row["CODE"])
        unit_concept = vocab.by_code.get(("UCUM", row["UNITS"]), 0) if row["UNITS"] else 0
        type_concept_id = T_LAB if row["CATEGORY"] == "laboratory" else (
            T_PATIENT if row["CATEGORY"] == "survey" else T_ENC)
        numeric = None
        if row["TYPE"] == "numeric":
            try:
                numeric = float(row["VALUE"])
            except ValueError:
                numeric = None
        if domain == "Observation":
            rep.rows_in["observation"] += 1
            if pid is None:
                rep.skipped["observation for a patient not in person"] += 1
                continue
            if concept == 0:
                rep.note_unmapped("observation", row["CODE"], row["DESCRIPTION"])
            next_obs_id += 1
            obs_rows.append((
                next_obs_id, pid, concept, date_only(row["DATE"]), type_concept_id,
                numeric, None if numeric is not None else row["VALUE"], None,
                unit_concept or None, visits.get(row["ENCOUNTER"]),
                row["CODE"], source_concept))
        else:
            rep.rows_in["measurement"] += 1
            if pid is None:
                rep.skipped["measurement for a patient not in person"] += 1
                continue
            if concept == 0:
                rep.note_unmapped("measurement", row["CODE"], row["DESCRIPTION"])
            if numeric is None and row["TYPE"] == "numeric":
                rep.skipped["numeric result that would not parse"] += 1
            meas_rows.append((
                i, pid, concept, date_only(row["DATE"]), type_concept_id,
                numeric, None, unit_concept or None,
                visits.get(row["ENCOUNTER"]), row["CODE"], source_concept,
                row["UNITS"] or None))
    con.executemany(
        "INSERT INTO measurement VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", meas_rows)
    con.executemany(
        "INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", obs_rows)
    rep.rows_out["measurement"] = len(meas_rows)
    rep.rows_out["observation"] = len(obs_rows)
    rep.rows_in["observation"] += len(cond_as_obs)
    if cond_as_obs:
        rep.routed["conditions.csv rows whose concept is an Observation"] = len(cond_as_obs)

    # ---- cdm_source -------------------------------------------------------
    con.execute(
        "INSERT INTO cdm_source VALUES (?,?,?,?,?,?,?,?,?)",
        ("HY-489 teaching cohort", "HY489", "CSD, University of Crete",
         "Synthetic Synthea-style export used across HY-489. Not real patients.",
         "lectures/week06/etl.py", "2026-09-01",
         __import__("datetime").date.today().isoformat(),
         CDM_VERSION, VOCAB_VERSION))

    con.commit()
    rep.print()

    counts = {t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
              for t in ("person", "observation_period", "visit_occurrence",
                        "condition_occurrence", "drug_exposure", "measurement",
                        "observation", "death", "concept", "concept_ancestor")}
    print("Tables in %s" % os.path.relpath(args.db, HERE))
    for table, n in counts.items():
        print("  %-22s %8d" % (table, n))
    print()
    print("Next: sqlite3 %s < queries.sql" % os.path.relpath(args.db, HERE))
    con.close()


if __name__ == "__main__":
    main()
