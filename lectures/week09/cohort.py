"""Assemble one analysis table from the five Lab 1 CSVs.

Every script in this folder starts here. The table is one row per patient, which
is already a decision: the source data is one row per observation, and flattening
it to one row per person throws away everything about when things happened.
Week 9 is largely about what that throwing away costs.

    python3 cohort.py              # build it and describe it
    python3 cohort.py --write      # also write data/cohort.csv so you can look

Stdlib only. No pandas, no downloads.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))
TODAY = dt.date(2026, 11, 16)          # the Monday of Week 9

# The two antihypertensives in this cohort. Both are prescribed, in every single
# case, with REASONDESCRIPTION = "Essential hypertension (disorder)".
ANTIHYPERTENSIVES = {
    "amLODIPine 5 MG Oral Tablet",
    "lisinopril 10 MG Oral Tablet",
}
METFORMIN = "24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet"
STATIN = "simvastatin 20 MG Oral Tablet"

# The observations we flatten to one value per patient.
VITALS = {
    "Systolic Blood Pressure": "sbp",
    "Diastolic Blood Pressure": "dbp",
    "Body Weight": "weight",
    "Cholesterol [Mass/volume] in Serum or Plasma": "cholesterol",
    "High Density Lipoprotein Cholesterol": "hdl",
}


def read(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        raise SystemExit("Cannot find %s\nRun this from lectures/week09 inside the repository." % path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def clean(desc):
    for suffix in (" (disorder)", " (finding)", " (procedure)"):
        if desc.endswith(suffix):
            return desc[: -len(suffix)]
    return desc


def build():
    patients = read("patients.csv")
    conditions = read("conditions.csv")
    medications = read("medications.csv")
    encounters = read("encounters.csv")

    cond = defaultdict(set)
    for r in conditions:
        cond[r["PATIENT"]].add(clean(r["DESCRIPTION"]))

    # The reason a drug was prescribed is a diagnosis, recorded somewhere other
    # than the problem list. In this cohort the two sources barely agree, which
    # is the first finding of the week.
    reason = defaultdict(set)
    meds = defaultdict(set)
    first_rx = {}
    for r in medications:
        meds[r["PATIENT"]].add(r["DESCRIPTION"])
        if r["REASONDESCRIPTION"]:
            reason[r["PATIENT"]].add(clean(r["REASONDESCRIPTION"]))
        if r["DESCRIPTION"] in ANTIHYPERTENSIVES:
            d = r["START"][:10]
            k = r["PATIENT"]
            if k not in first_rx or d < first_rx[k]:
                first_rx[k] = d

    first_enc, last_enc, n_enc = {}, {}, defaultdict(int)
    for r in encounters:
        k, d = r["PATIENT"], r["START"][:10]
        n_enc[k] += 1
        if k not in first_enc or d < first_enc[k]:
            first_enc[k] = d
        if k not in last_enc or d > last_enc[k]:
            last_enc[k] = d

    # last value per patient per vital. "Last" is itself a decision: a patient
    # whose last reading was taken in a crisis looks worse than they usually are.
    last_value = {}
    with open(os.path.join(DATA, "observations.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            col = VITALS.get(r["DESCRIPTION"])
            if not col:
                continue
            key = (r["PATIENT"], col)
            if key not in last_value or r["DATE"] > last_value[key][0]:
                try:
                    last_value[key] = (r["DATE"][:10], float(r["VALUE"]))
                except ValueError:
                    pass

    rows = []
    for p in patients:
        pid = p["Id"]
        birth = dt.date.fromisoformat(p["BIRTHDATE"][:10])
        death = p["DEATHDATE"][:10] or ""
        end = dt.date.fromisoformat(death) if death else TODAY
        row = {
            "patient_id": pid,
            "sex": p["GENDER"],
            "birth_date": birth.isoformat(),
            "age": (end - birth).days // 365,
            "died": "1" if death else "0",
            "death_date": death,
            "postcode": p["ZIP"],
            "first_encounter": first_enc.get(pid, ""),
            "last_encounter": last_enc.get(pid, ""),
            "n_encounters": n_enc.get(pid, 0),
            # three phenotypes for the same condition, from two sources
            "hypertension_dx": "1" if any("ypertens" in c for c in cond[pid]) else "0",
            "hypertension_rx": "1" if "Essential hypertension" in reason[pid] else "0",
            "diabetes_dx": "1" if "Type 2 diabetes mellitus" in cond[pid] else "0",
            "diabetes_rx": "1" if "Type 2 diabetes mellitus" in reason[pid] else "0",
            "prediabetes_dx": "1" if "Prediabetes" in cond[pid] else "0",
            "obesity_dx": "1" if "Body mass index 30+ - obesity" in cond[pid] else "0",
            "on_antihypertensive": "1" if pid in first_rx else "0",
            "first_antihypertensive": first_rx.get(pid, ""),
            "on_metformin": "1" if METFORMIN in meds[pid] else "0",
            "on_statin": "1" if STATIN in meds[pid] else "0",
        }
        row["hypertension_any"] = "1" if (row["hypertension_dx"] == "1" or row["hypertension_rx"] == "1") else "0"
        row["diabetes_any"] = "1" if (row["diabetes_dx"] == "1" or row["diabetes_rx"] == "1") else "0"
        for col in VITALS.values():
            v = last_value.get((pid, col))
            row[col] = ("%.1f" % v[1]) if v else ""
        rows.append(row)
    return rows


def num(rows, col, where=None):
    out = []
    for r in rows:
        if where and not where(r):
            continue
        v = r.get(col, "")
        if v != "":
            out.append(float(v))
    return out


def describe(rows):
    n = len(rows)
    print("\nCOHORT: %d patients, one row each" % n)
    print("  %-26s %6s %8s" % ("column", "filled", "summary"))
    for col in ("age", "sbp", "dbp", "weight", "cholesterol", "hdl"):
        v = num(rows, col)
        print("  %-26s %6d %8s" % (col, len(v), "mean %.1f" % st.mean(v) if v else "-"))
    for col in ("hypertension_dx", "hypertension_rx", "hypertension_any",
                "diabetes_dx", "diabetes_rx", "diabetes_any",
                "prediabetes_dx", "obesity_dx",
                "on_antihypertensive", "on_metformin", "on_statin", "died"):
        k = sum(1 for r in rows if r[col] == "1")
        print("  %-26s %6d %8s" % (col, k, "%.1f%%" % (100.0 * k / n)))

    print("\n  THE SAME CONDITION, TWO SOURCES, THREE ANSWERS")
    print("  %-14s %10s %10s %8s %8s %8s" % ("condition", "problem", "drug", "either", "both", "agree"))
    print("  %-14s %10s %10s %8s %8s %8s" % ("", "list", "reason", "", "", ""))
    for label, dx, rx in (("type 2 diabetes", "diabetes_dx", "diabetes_rx"),
                          ("hypertension", "hypertension_dx", "hypertension_rx")):
        a = {r["patient_id"] for r in rows if r[dx] == "1"}
        b = {r["patient_id"] for r in rows if r[rx] == "1"}
        print("  %-14s %10d %10d %8d %8d %7.0f%%"
              % (label, len(a), len(b), len(a | b), len(a & b), 100.0 * len(a & b) / len(a | b)))

    treated = [r for r in rows if r["on_antihypertensive"] == "1"]
    no_dx = [r for r in treated if r["hypertension_dx"] == "0"]
    print("""
  Read the diabetes row. The prevalence of type 2 diabetes in this cohort is
  16%%, or 17%%, or 30%%, depending on which column you believe, and the two
  sources agree about 42 patients out of 353. They are not two measurements of
  the same thing that happen to disagree; they are two different populations.

  A computable phenotype is the rule you use to decide who has the condition.
  Every study has one, most papers do not state it, and the choice moves the
  answer further than anything else you will do all day.

  Two more things before you analyse anything.

  1. %d of the %d patients on an antihypertensive have NO hypertension row in
     conditions.csv, even though every one of those prescriptions records the
     reason as essential hypertension. A cohort defined from diagnosis codes
     alone misses %.0f%% of the treated patients.

  2. Every vital here is the LAST recorded value, which is a choice nobody
     asked you to justify. A patient measured once, in a crisis, contributes
     that crisis value. The source data has 50,493 readings; this table has one.
""" % (len(no_dx), len(treated), 100.0 * len(no_dx) / len(treated)))


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("  wrote %s" % path)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    rows = build()
    describe(rows)
    if args.write:
        out = os.path.join(HERE, "data")
        os.makedirs(out, exist_ok=True)
        write_csv(rows, os.path.join(out, "cohort.csv"))
