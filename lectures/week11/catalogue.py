#!/usr/bin/env python3
"""Describe the Lab 1 cohort the way Articles 77 and 78 require, and measure it.

    python3 catalogue.py                 # the whole thing
    python3 catalogue.py --entry         # the Article 77 dataset description
    python3 catalogue.py --completeness  # is the value there at all
    python3 catalogue.py --correctness   # is the value a legal value
    python3 catalogue.py --concordance   # do the sources agree with each other
    python3 catalogue.py --plausibility  # could the value be true
    python3 catalogue.py --currency      # how old is the most recent record
    python3 catalogue.py --label         # the data quality and utility label
    python3 catalogue.py --coverage      # what Article 78(3) asks that this cannot answer

Article 77 makes a health data holder publish a dataset description covering
the source, scope, main characteristics and nature of the data and the
conditions for making it available, in a machine readable national catalogue.
Article 78 adds a data quality and utility label, voluntary in general and
mandatory for any dataset collected with public money. Article 78(3)(b) names
six technical quality elements: completeness, uniqueness, accuracy, validity,
timeliness and consistency.

Five of those six are the dimensions from Week 7. Weiskopf and Weng called them
completeness, correctness, concordance, plausibility and currency, and this
script computes every one of them from the CSVs instead of asserting them.
A label that is asserted is a claim. A label that is computed is a measurement,
and the difference is the whole of Article 78(4), which lets the health data
access body revoke a label it does not believe.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import statistics as st
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))

TODAY = dt.date(2026, 11, 30)          # the Monday of Week 11

TOWN = {
    "71201": "Heraklion", "72100": "Agios Nikolaos", "72200": "Ierapetra",
    "72300": "Sitia", "73100": "Chania", "74100": "Rethymno",
}

FILES = ["patients.csv", "conditions.csv", "medications.csv",
         "encounters.csv", "observations.csv"]

# Columns the dataset holds out as populated. The others are populated when
# they apply: a death date applies to the dead, a stop date to a course of
# treatment that has stopped. Deciding which column belongs in which list is a
# judgement, it is made here, and it changes the completeness score.
EXPECTED = {
    "patients.csv": ["Id", "BIRTHDATE", "FIRST", "LAST", "GENDER", "ADDRESS",
                     "CITY", "ZIP", "LAT", "LON", "HEALTHCARE_EXPENSES",
                     "HEALTHCARE_COVERAGE", "INCOME"],
    "conditions.csv": ["START", "PATIENT", "ENCOUNTER", "SYSTEM", "CODE",
                       "DESCRIPTION"],
    "medications.csv": ["START", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION",
                        "BASE_COST", "TOTALCOST", "REASONCODE",
                        "REASONDESCRIPTION"],
    "encounters.csv": ["Id", "START", "STOP", "PATIENT", "ORGANIZATION",
                       "PROVIDER", "ENCOUNTERCLASS", "CODE", "DESCRIPTION",
                       "TOTAL_CLAIM_COST"],
    "observations.csv": ["DATE", "PATIENT", "ENCOUNTER", "CATEGORY", "CODE",
                         "DESCRIPTION", "VALUE", "TYPE"],
}

# Physiological ranges. Outside these a value is not wrong, it is impossible,
# which is what separates plausibility from correctness.
RANGES = {
    "Systolic Blood Pressure": (50.0, 300.0),
    "Diastolic Blood Pressure": (20.0, 200.0),
    "Body Weight": (0.5, 400.0),
    "Cholesterol [Mass/volume] in Serum or Plasma": (50.0, 500.0),
    "High Density Lipoprotein Cholesterol": (10.0, 150.0),
}

RE_SNOMED = re.compile(r"^\d{6,18}$")
RE_LOINC = re.compile(r"^\d{1,5}-\d$")
RE_RXNORM = re.compile(r"^\d{1,8}$")
RE_ZIP = re.compile(r"^\d{5}$")
UCUM = {"mm[Hg]", "kg", "mg/dL"}

GRADES = [(95.0, "A"), (85.0, "B"), (70.0, "C"), (50.0, "D"), (0.0, "E")]


def read(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        raise SystemExit(
            "Cannot find %s\nRun this from lectures/week11 inside the repository." % path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def iso(v):
    try:
        return dt.date.fromisoformat((v or "")[:10])
    except ValueError:
        return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


def grade(score):
    for threshold, letter in GRADES:
        if score >= threshold:
            return letter
    return "E"


def load():
    store = {f: read(f) for f in FILES}
    pts = store["patients.csv"]
    store["_birth"] = {p["Id"]: iso(p["BIRTHDATE"]) for p in pts}
    store["_death"] = {p["Id"]: iso(p["DEATHDATE"]) if p["DEATHDATE"] else None
                       for p in pts}
    store["_ids"] = {p["Id"] for p in pts}
    store["_enc"] = {e["Id"] for e in store["encounters.csv"]}
    problems = defaultdict(set)
    for r in store["conditions.csv"]:
        problems[r["PATIENT"]].add(r["DESCRIPTION"])
    store["_problems"] = problems
    return store


# ----------------------------------------------------------------------
# a check is (label, passed, checked)
# ----------------------------------------------------------------------
def completeness(store):
    checks = []
    for f in FILES:
        rows = store[f]
        passed = sum(1 for r in rows for c in EXPECTED[f]
                     if (r.get(c) or "").strip())
        checks.append(("%s, %d expected columns populated" % (f, len(EXPECTED[f])),
                       passed, len(rows) * len(EXPECTED[f])))
    n = len(store["patients.csv"])
    have = {
        "an encounter": {r["PATIENT"] for r in store["encounters.csv"]},
        "a recorded condition": {r["PATIENT"] for r in store["conditions.csv"]},
        "a prescription": {r["PATIENT"] for r in store["medications.csv"]},
        "a laboratory result": {r["PATIENT"] for r in store["observations.csv"]
                                if r["CATEGORY"] == "laboratory"},
        "a vital sign": {r["PATIENT"] for r in store["observations.csv"]
                         if r["CATEGORY"] == "vital-signs"},
    }
    for label, s in have.items():
        checks.append(("patients with %s" % label, len(s & store["_ids"]), n))
    return checks


def correctness(store):
    """Is the value a legal value of its declared type, domain or pattern.

    Article 78(3)(b) calls this accuracy and validity, and adds uniqueness,
    which is checked here too because it has nowhere else to go.
    """
    checks = []
    pts = store["patients.csv"]
    checks.append(("patient identifiers unique",
                   len({p["Id"] for p in pts}), len(pts)))
    enc = store["encounters.csv"]
    checks.append(("encounter identifiers unique",
                   len({e["Id"] for e in enc}), len(enc)))
    checks.append(("birth dates parse as ISO 8601",
                   sum(1 for p in pts if iso(p["BIRTHDATE"])), len(pts)))
    checks.append(("sex in the declared domain M or F",
                   sum(1 for p in pts if p["GENDER"] in ("M", "F")), len(pts)))
    checks.append(("postcodes are five digits",
                   sum(1 for p in pts if RE_ZIP.match(p["ZIP"])), len(pts)))
    cond = store["conditions.csv"]
    checks.append(("condition codes match the SNOMED CT pattern",
                   sum(1 for r in cond if RE_SNOMED.match(r["CODE"])), len(cond)))
    med = store["medications.csv"]
    checks.append(("medication codes match the RxNorm pattern",
                   sum(1 for r in med if RE_RXNORM.match(r["CODE"])), len(med)))
    obs = store["observations.csv"]
    checks.append(("observation codes match the LOINC pattern",
                   sum(1 for r in obs if RE_LOINC.match(r["CODE"])), len(obs)))
    numeric = [r for r in obs if r["TYPE"] == "numeric"]
    checks.append(("numeric observations parse as a number",
                   sum(1 for r in numeric if num(r["VALUE"]) is not None),
                   len(numeric)))
    checks.append(("numeric observations carry a UCUM unit",
                   sum(1 for r in numeric if r["UNITS"] in UCUM), len(numeric)))
    checks.append(("encounter start and stop parse as ISO 8601",
                   sum(1 for r in enc if iso(r["START"]) and iso(r["STOP"])),
                   len(enc)))
    return checks


def concordance(store):
    """Do two places in the dataset that record the same fact agree.

    This is the dimension that needs no external truth and that nobody checks,
    because every file passes every check inside itself.
    """
    checks = []
    probs = store["_problems"]
    med = [r for r in store["medications.csv"] if r["REASONDESCRIPTION"]]
    checks.append(("medication reason appears on the patient's problem list",
                   sum(1 for r in med if r["REASONDESCRIPTION"] in probs[r["PATIENT"]]),
                   len(med)))
    enc = [r for r in store["encounters.csv"] if r["REASONDESCRIPTION"]]
    checks.append(("encounter reason appears on the patient's problem list",
                   sum(1 for r in enc if r["REASONDESCRIPTION"] in probs[r["PATIENT"]]),
                   len(enc)))
    cond = store["conditions.csv"]
    checks.append(("condition points at an encounter that exists",
                   sum(1 for r in cond if r["ENCOUNTER"] in store["_enc"]), len(cond)))
    meds = store["medications.csv"]
    checks.append(("prescription points at an encounter that exists",
                   sum(1 for r in meds if r["ENCOUNTER"] in store["_enc"]), len(meds)))
    obs = store["observations.csv"]
    checks.append(("observation points at a patient that exists",
                   sum(1 for r in obs if r["PATIENT"] in store["_ids"]), len(obs)))
    # An observation taken during an encounter should carry that encounter's day.
    day = {e["Id"]: e["START"][:10] for e in store["encounters.csv"]}
    linked = [r for r in obs if r["ENCOUNTER"] in day]
    checks.append(("observation date matches its encounter's date",
                   sum(1 for r in linked if r["DATE"][:10] == day[r["ENCOUNTER"]]),
                   len(linked)))
    return checks


def plausibility(store):
    """Could the value be true of a person. Format is not the question here."""
    checks = []
    birth, death = store["_birth"], store["_death"]
    pts = store["patients.csv"]
    ages = []
    for p in pts:
        b = birth[p["Id"]]
        end = death[p["Id"]] or TODAY
        ages.append((end - b).days // 365)
    checks.append(("age at death or today is 115 or under",
                   sum(1 for a in ages if a <= 115), len(ages)))
    checks.append(("birth date is not in the future",
                   sum(1 for p in pts if birth[p["Id"]] <= TODAY), len(pts)))
    dead = [p for p in pts if death[p["Id"]]]
    checks.append(("death date falls after the birth date",
                   sum(1 for p in dead if death[p["Id"]] > birth[p["Id"]]), len(dead)))

    dated = []
    for f, col in (("conditions.csv", "START"), ("medications.csv", "START"),
                   ("encounters.csv", "START"), ("observations.csv", "DATE")):
        for r in store[f]:
            d = iso(r[col])
            if d:
                dated.append((r["PATIENT"], d))
    checks.append(("clinical record falls on or after the patient's birth",
                   sum(1 for pid, d in dated if pid in birth and d >= birth[pid]),
                   len(dated)))
    checks.append(("clinical record falls on or before the death date",
                   sum(1 for pid, d in dated
                       if not death.get(pid) or d <= death[pid]), len(dated)))
    enc = store["encounters.csv"]
    checks.append(("encounter stops at or after it starts",
                   sum(1 for r in enc if r["STOP"] >= r["START"]), len(enc)))
    checks.append(("total claim cost is not negative",
                   sum(1 for r in enc if (num(r["TOTAL_CLAIM_COST"]) or 0) >= 0),
                   len(enc)))

    obs = store["observations.csv"]
    in_range = checked = 0
    for r in obs:
        if r["DESCRIPTION"] in RANGES:
            checked += 1
            lo, hi = RANGES[r["DESCRIPTION"]]
            v = num(r["VALUE"])
            if v is not None and lo <= v <= hi:
                in_range += 1
    checks.append(("vital sign and laboratory value inside a physiological range",
                   in_range, checked))

    sbp, dbp = {}, {}
    for r in obs:
        if r["DESCRIPTION"] == "Systolic Blood Pressure":
            sbp[(r["PATIENT"], r["DATE"])] = num(r["VALUE"])
        elif r["DESCRIPTION"] == "Diastolic Blood Pressure":
            dbp[(r["PATIENT"], r["DATE"])] = num(r["VALUE"])
    pairs = [k for k in sbp if k in dbp]
    checks.append(("systolic pressure exceeds diastolic in the same reading",
                   sum(1 for k in pairs if sbp[k] > dbp[k]), len(pairs)))
    return checks


def recency(store):
    """Days since the most recent record of any kind, per living patient."""
    last = {}
    for f, col in (("conditions.csv", "START"), ("medications.csv", "START"),
                   ("encounters.csv", "START"), ("observations.csv", "DATE")):
        for r in store[f]:
            d = iso(r[col])
            pid = r["PATIENT"]
            if d and (pid not in last or d > last[pid]):
                last[pid] = d
    living = [p["Id"] for p in store["patients.csv"] if not store["_death"][p["Id"]]]
    return {pid: (TODAY - last[pid]).days for pid in living if pid in last}, living


def currency(store):
    ages, living = recency(store)
    checks = []
    for years in (1, 2, 5, 10):
        checks.append(("living patient has a record inside %d year%s"
                       % (years, "" if years == 1 else "s"),
                       sum(1 for v in ages.values() if v <= 365 * years),
                       len(living)))
    return checks


DIMENSIONS = [
    ("completeness", completeness, "is the value there at all"),
    ("correctness", correctness, "is the value a legal value"),
    ("concordance", concordance, "do two records of the same fact agree"),
    ("plausibility", plausibility, "could the value be true of a person"),
    ("currency", currency, "how old is the most recent record"),
]


def scores(store):
    out = []
    for name, fn, blurb in DIMENSIONS:
        checks = fn(store)
        rates = [pct(p, c) for _l, p, c in checks if c]
        out.append((name, blurb, checks, min(rates), st.mean(rates)))
    return out


def show_checks(name, blurb, checks):
    print("\n%s%s" % (name.upper(), " " * max(1, 16 - len(name)) + blurb))
    print("  %-58s %9s %9s %9s" % ("check", "passing", "checked", "rate"))
    for label, passed, checked in checks:
        print("  %-58s %9d %9d %8.2f%%" % (label, passed, checked,
                                           pct(passed, checked)))


# ----------------------------------------------------------------------
# reports
# ----------------------------------------------------------------------
def report_entry(store):
    pts = store["patients.csv"]
    dates = []
    for f, col in (("conditions.csv", "START"), ("medications.csv", "START"),
                   ("encounters.csv", "START"), ("observations.csv", "DATE")):
        for r in store[f]:
            d = iso(r[col])
            if d:
                dates.append(d)
    towns = Counter(TOWN.get(p["ZIP"], "unknown") for p in pts)
    sexes = Counter(p["GENDER"] for p in pts)
    ages = sorted((((store["_death"][p["Id"]] or TODAY) - store["_birth"][p["Id"]]).days
                   // 365) for p in pts)
    codes = {
        "conditions.csv": len({r["CODE"] for r in store["conditions.csv"]}),
        "medications.csv": len({r["CODE"] for r in store["medications.csv"]}),
        "observations.csv": len({r["CODE"] for r in store["observations.csv"]}),
    }
    print("\nTHE ARTICLE 77 DATASET DESCRIPTION")
    print("""
  Article 77(1) makes the health data holder give the health data access body a
  description covering the source, scope, main characteristics and nature of
  the data and the conditions under which it is made available, and Article
  77(3) makes the body publish it in a machine readable national catalogue.
  What follows is that description for this cohort, with every number in it
  computed from the files and none of it typed in.""")

    print("\n  identification")
    print("    %-34s %s" % ("title", "HY-489 teaching cohort, Crete"))
    print("    %-34s %s" % ("identifier", "urn:hy489:lab01:synthea-crete"))
    print("    %-34s %s" % ("publisher", "Computer Science Department, University of Crete"))
    print("    %-34s %s" % ("licence", "teaching use inside the course only"))

    print("\n  source, Article 77(1)")
    print("    %-34s %s" % ("origin", "Synthea synthetic patient generator"))
    print("    %-34s %s" % ("real persons", "none, and no record derives from one"))
    print("    %-34s %s" % ("collection method", "simulation, not clinical practice"))
    print("    %-34s %s" % ("legal basis for the original data", "not applicable"))

    print("\n  scope and main characteristics, Article 77(1)")
    print("    %-34s %d" % ("patients", len(pts)))
    for f in FILES:
        print("    %-34s %d" % ("rows in " + f, len(store[f])))
    print("    %-34s %d" % ("rows in all five files",
                            sum(len(store[f]) for f in FILES)))
    print("    %-34s %s to %s" % ("temporal coverage",
                                  min(dates).isoformat(), max(dates).isoformat()))
    print("    %-34s %d years" % ("duration of the observation window",
                                  (max(dates) - min(dates)).days // 365))
    print("    %-34s %s" % ("spatial coverage", "Crete, six postcode areas"))
    for town, n in towns.most_common():
        print("      %-32s %d" % (town, n))
    print("    %-34s %d female, %d male" % ("sex", sexes["F"], sexes["M"]))
    print("    %-34s %d to %d, median %d" % ("age at the reference date",
                                             ages[0], ages[-1], st.median(ages)))
    print("    %-34s %d deceased, %d living" %
          ("vital status", sum(1 for p in pts if store["_death"][p["Id"]]),
           sum(1 for p in pts if not store["_death"][p["Id"]])))

    print("\n  nature of the data, Article 77(1)")
    print("    %-34s %s" % ("Article 51 category", "(a) electronic health records"))
    print("    %-34s %s" % ("", "(e) administrative data, claims and cost"))
    print("    %-34s %s" % ("personal data", "no, synthetic throughout"))
    print("    %-34s %s" % ("direct identifiers present in the file",
                            "name, address, national identifier, all invented"))
    print("    %-34s %s" % ("coding systems",
                            "SNOMED CT declared, LOINC and RxNorm undeclared"))
    for f, n in codes.items():
        print("    %-34s %d" % ("distinct codes in " + f, n))

    print("\n  conditions for availability, Article 77(1)")
    print("    %-34s %s" % ("access route", "none, this is not a real dataset"))
    print("    %-34s %s" % ("secure processing environment", "not applicable"))
    print("    %-34s %s" % ("opt-out under Article 71", "not applicable"))
    print("    %-34s %s" % ("fee under Article 62", "none"))
    print("""
  Read the source block again. It is three lines long and it is the part a
  researcher reads first, because the scope tells you whether the data could
  answer your question and the source tells you whether to believe it. Article
  77(1) asks for the source and does not say what counts as describing it.

  This cohort is synthetic. That belongs at the top of the entry, in the
  machine readable field and not in a footnote, because a catalogue is read by
  software before it is read by a person.""")


def report_label(store):
    rows = scores(store)
    print("\nTHE DATA QUALITY AND UTILITY LABEL")
    print("""
  Article 78(3)(b) names six technical quality elements: completeness,
  uniqueness, accuracy, validity, timeliness and consistency. Weiskopf and Weng
  reduced ninety-five papers to five dimensions, and the two lists are the same
  list: accuracy and validity are correctness, consistency is concordance,
  timeliness is currency, uniqueness is checked inside correctness here because
  it has nowhere else to go.

  Each dimension's score is its worst check. A label that averages a failure
  away is a label nobody can act on, and Article 78(4) lets the health data
  access body revoke a label it does not believe. The mean is printed beside it
  so the choice can be argued with.""")
    print("\n  %-14s %-40s %8s %6s %8s %6s" %
          ("dimension", "worst check", "worst", "grade", "mean", "grade"))
    for name, _blurb, checks, worst, mean in rows:
        label = min((c for c in checks if c[2]), key=lambda c: pct(c[1], c[2]))[0]
        print("  %-14s %-40s %7.2f%% %6s %7.2f%% %6s" %
              (name, label[:40], worst, grade(worst), mean, grade(mean)))
    overall = min(r[3] for r in rows)
    overall_mean = st.mean([r[3] for r in rows])
    worst3 = sorted(rows, key=lambda r: r[3])[:3]
    print()
    print("  %-14s %-40s %7.2f%% %6s %7.2f%% %6s" %
          ("LABEL", "the worst dimension of the five", overall, grade(overall),
           overall_mean, grade(overall_mean)))
    print("\n  The three worst dimensions:")
    for i, (name, blurb, checks, worst, _mean) in enumerate(worst3, 1):
        label, passed, checked = min((c for c in checks if c[2]),
                                     key=lambda c: pct(c[1], c[2]))
        print("    %d. %-13s %-50s %7.2f%%  grade %s"
              % (i, name, label[:50], pct(passed, checked),
                 grade(pct(passed, checked))))
    print("""
  The label is grade %s, and it is grade %s because of %s. Grade the same
  dataset on the mean of its five dimensions instead and it comes out %s.

  Correctness and plausibility are near perfect and they are the two dimensions
  a data holder can fix by itself, with a schema and a range check. Concordance
  and currency are the two it cannot, because concordance is a question about
  whether two clinicians wrote the same thing down and currency is a question
  about whether anybody has seen the patient lately. The dimensions that score
  well are the ones that were cheap.

  A researcher reading this label learns that the values are legal and that
  roughly three quarters of the time the reason recorded against a prescription
  is not on that patient's problem list. The first fact is worth very little.
  The second decides whether a study of treatment by indication can be run at
  all, and under Article 78 it is on the label before anybody applies for a
  permit. That is the argument for the label: it moves a finding that used to
  arrive in month nine of a project into the catalogue entry.""" %
          (grade(overall), grade(overall), worst3[0][0], grade(overall_mean)))


def report_coverage(store):
    print("\nWHAT ARTICLE 78(3) ASKS THAT THIS SCRIPT CANNOT ANSWER")
    print("""
  Six element groups, of which the measurement above covers one and a half.""")
    groups = [
        ("(a) data documentation", "partly",
         ["the format, the standards used and the source are in",
          "the entry above. The data dictionary and the support",
          "documentation are not in the files."]),
        ("(b) technical quality", "in full",
         ["completeness, uniqueness, accuracy, validity, timeliness",
          "and consistency. This is the label section above."]),
        ("(c) quality management", "no",
         ["maturity of the data management processes, review and",
          "audit processes, bias examination. These are facts about",
          "an organisation, not about a file."]),
        ("(d) coverage", "partly",
         ["the temporal period and the duration are computed above.",
          "Population coverage and representativity need a",
          "from outside the dataset, and nothing in the CSVs says",
          "denominator, and how many people live in Crete."]),
        ("(e) access information", "no",
         ["time from collection to addition, and time to provision",
          "after approval. These are facts about a process that",
          "has not run yet."]),
        ("(f) data modifications", "no",
         ["merging, additions and linkage with other datasets. The",
          "files record no history of their own construction."]),
    ]
    print("\n  %-24s %-8s %s" % ("element group", "computed", "what it asks for"))
    for name, computed, lines in groups:
        print("  %-24s %-8s %s" % (name, computed, lines[0]))
        for extra in lines[1:]:
            print("  %-24s %-8s %s" % ("", "", extra))
    print("""
  One group of six can be computed from the data in full. One more can be
  computed in part. The other four are declarations by the data holder about
  itself, and Article 78(4) gives the health data access body the job of
  assessing whether they are accurate.

  That is the honest shape of the label. It is not a measurement with some
  paperwork attached. It is paperwork with one measured section, and the
  measured section is the one this script computes. When the implementing act
  under Article 78(6) lands, due 26 March 2027, the thing to look at first is
  how it proposes to verify (c), (e) and (f), because nothing in a file can.""")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("entry", "completeness", "correctness", "concordance",
                 "plausibility", "currency", "label", "coverage"):
        ap.add_argument("--" + flag, action="store_true")
    args = ap.parse_args()
    chosen = {f: getattr(args, f) for f in
              ("entry", "completeness", "correctness", "concordance",
               "plausibility", "currency", "label", "coverage")}
    run_all = not any(chosen.values())

    store = load()
    if chosen["entry"] or run_all:
        report_entry(store)
    for name, fn, blurb in DIMENSIONS:
        if chosen[name] or run_all:
            show_checks(name, blurb, fn(store))
    if run_all:
        ages, living = recency(store)
        v = sorted(ages.values())
        print("\n  Days since the most recent record, living patients only:")
        print("    median %d, 90th percentile %d, worst %d, %d of %d have no record"
              % (st.median(v), v[int(0.9 * len(v))], v[-1], len(living) - len(v),
                 len(living)))
    if chosen["label"] or run_all:
        report_label(store)
    if chosen["coverage"] or run_all:
        report_coverage(store)


if __name__ == "__main__":
    main()
