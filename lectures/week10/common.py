"""Shared loading for Week 10.

Governance is the week where the code stops being about the patients and
starts being about the people who hold the data. Two of the three scripts
still need the cohort, so the loading lives here, as it did in Week 8.

The cohort is the same 1,174 synthetic patients you have had since Week 1.
Nothing here corresponds to a real person, which is the only reason any of
this can be run in a lecture theatre.
"""

from __future__ import annotations

import csv
import datetime as dt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))

TODAY = dt.date(2026, 11, 23)          # the Monday of Week 10
SEED = 489

# The six postcodes in the cohort, and the town each one is.
TOWN = {
    "71201": "Heraklion",
    "72100": "Agios Nikolaos",
    "72200": "Ierapetra",
    "72300": "Sitia",
    "73100": "Chania",
    "74100": "Rethymno",
}
TOWNS = sorted(set(TOWN.values()))

AGE_BANDS = [(0, 17), (18, 34), (35, 49), (50, 64), (65, 79), (80, 200)]
BAND_LABELS = ["0-17", "18-34", "35-49", "50-64", "65-79", "80+"]


def read(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        raise SystemExit(
            "Cannot find %s\nRun this from lectures/week10 inside the repository." % path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def age_of(p, today=TODAY):
    """Age now, or age at death for the patients who died."""
    birth = dt.date.fromisoformat(p["BIRTHDATE"][:10])
    death = p["DEATHDATE"][:10]
    end = dt.date.fromisoformat(death) if death else today
    return (end - birth).days // 365


def band_of(a):
    for (lo, hi), label in zip(AGE_BANDS, BAND_LABELS):
        if lo <= a <= hi:
            return label
    return BAND_LABELS[-1]


def clean(desc):
    for suffix in (" (disorder)", " (finding)", " (procedure)"):
        if desc.endswith(suffix):
            return desc[: -len(suffix)]
    return desc


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b
