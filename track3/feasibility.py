"""Feasibility counts for the candidate questions, run before the protocol.

Counts EXPOSURES and whether an outcome MEASUREMENT EXISTS in a window.
It never reads an outcome VALUE, so it is safe to run before the protocol
is committed.

    python3 feasibility.py

Stdlib only. Reads the cohort from ../labs/lab01/data/.
"""

import csv
import datetime as dt
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "labs", "lab01", "data"))

STATIN = {"simvastatin 20 MG Oral Tablet"}
METFORMIN = {"24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet"}
OUTCOMES = {
    "Cholesterol [Mass/volume] in Serum or Plasma": "cholesterol",
    "Body Weight": "weight",
}
# (days before index, first day after, last day after)
WINDOWS = [(365, 90, 730), (730, 90, 730), (730, 30, 1095), (1095, 1, 1825)]


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def day(s):
    return dt.date.fromisoformat(s[:10])


def first_rx(meds, names):
    first = {}
    for r in meds:
        if r["DESCRIPTION"] in names:
            p, d = r["PATIENT"], day(r["START"])
            first[p] = min(first.get(p, d), d)
    return first


def main():
    meds = read("medications.csv")
    encounters = defaultdict(list)
    for r in read("encounters.csv"):
        encounters[r["PATIENT"]].append(day(r["START"]))

    # dates only; VALUE is never read
    measured = defaultdict(list)
    with open(os.path.join(DATA, "observations.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            col = OUTCOMES.get(r["DESCRIPTION"])
            if col:
                measured[(r["PATIENT"], col)].append(day(r["DATE"]))

    for label, names, outcome in (("statin -> total cholesterol", STATIN, "cholesterol"),
                                  ("metformin -> body weight", METFORMIN, "weight")):
        first = first_rx(meds, names)
        none_after = sum(1 for p, d in first.items()
                         if not any(0 < (x - d).days <= 730 for x in encounters[p]))
        print("\n%s" % label)
        print("  new users                               %4d" % len(first))
        print("  no encounter at all in 2y after index   %4d" % none_after)
        for pre, lo, hi in WINDOWS:
            both = sum(1 for p, d in first.items()
                       if any(-pre <= (x - d).days <= 0 for x in measured[(p, outcome)])
                       and any(lo <= (x - d).days <= hi for x in measured[(p, outcome)]))
            print("  measured in [-%4d,0] and [%3d,%4d]   %4d" % (pre, lo, hi, both))


if __name__ == "__main__":
    main()
