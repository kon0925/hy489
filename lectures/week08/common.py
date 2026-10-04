"""Shared loading and the quasi-identifier definitions for Week 8.

All three scripts in this folder work on the Lab 1 cohort, which you have had
since Week 1 and have by now queried half a dozen ways. That is the point: the
file you have been treating as a harmless teaching dataset carries a direct
identifier in every row and a quasi-identifier combination that is unique for
almost everybody in it.

It is synthetic. Nothing here corresponds to a real person, and that is the
only reason it is safe to attack it in a lecture theatre.
"""

from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))

# Fields that name a person on their own. Removing these is step zero, and on
# its own it is not anonymisation.
DIRECT_IDENTIFIERS = ["Id", "SSN", "DRIVERS", "PASSPORT", "FIRST", "LAST",
                      "MAIDEN", "PREFIX", "SUFFIX", "ADDRESS", "LAT", "LON"]

# Fields that do not name anybody but that somebody else may also hold. These
# are what the attack runs on.
QUASI_IDENTIFIERS = ["ZIP", "BIRTHDATE", "GENDER", "CITY", "COUNTY",
                     "MARITAL", "BIRTHPLACE", "RACE", "ETHNICITY"]

# The sensitive attribute, derived once so that every script agrees.
# One value per patient: the highest-priority chronic condition recorded for
# them, or "none recorded". A single categorical value per record is what
# l-diversity and t-closeness are defined over.
CHRONIC_PRIORITY = [
    "Type 2 diabetes mellitus",
    "Prediabetes",
    "Essential hypertension",
    "Hypertensive disorder, systemic arterial",
    "Hyperlipidemia",
    "Body mass index 30+ - obesity",
    "Chronic sinusitis",
    "Childhood asthma",
    "Osteoarthritis of knee",
    "Anemia",
]
NONE = "none recorded"


def clean(desc):
    for suffix in (" (disorder)", " (finding)", " (procedure)"):
        if desc.endswith(suffix):
            return desc[: -len(suffix)]
    return desc


def load_patients():
    path = os.path.join(DATA, "patients.csv")
    if not os.path.exists(path):
        raise SystemExit(
            "Cannot find %s\nRun this from lectures/week08 inside the repository." % path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_sensitive():
    """patient id -> one sensitive value."""
    path = os.path.join(DATA, "conditions.csv")
    by_patient = defaultdict(set)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_patient[row["PATIENT"]].add(clean(row["DESCRIPTION"]))
    out = {}
    for pid, names in by_patient.items():
        out[pid] = next((c for c in CHRONIC_PRIORITY if c in names), NONE)
    return out


def attach_sensitive(rows):
    sens = load_sensitive()
    for r in rows:
        r["_sensitive"] = sens.get(r["Id"], NONE)
    return rows


def group_sizes(rows, keyfn):
    return Counter(keyfn(r) for r in rows)


def risk(rows, keyfn):
    """(unique, k<=2, k<=5, number of classes, smallest class)."""
    counts = group_sizes(rows, keyfn)
    n = len(rows)
    u = sum(1 for r in rows if counts[keyfn(r)] == 1)
    k2 = sum(1 for r in rows if counts[keyfn(r)] <= 2)
    k5 = sum(1 for r in rows if counts[keyfn(r)] <= 5)
    return u, k2, k5, len(counts), min(counts.values())


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b
