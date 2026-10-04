#!/usr/bin/env python3
"""Profile a file against the five data quality dimensions.

    python3 quality.py                  # both site files
    python3 quality.py --file site_a    # one of them
    python3 quality.py --lab01          # the Lab 1 cohort, for comparison
    python3 quality.py --quiet          # findings only, no profile

Weiskopf and Weng (JAMIA, 2013) reviewed ninety-five papers on the quality of
electronic health record data and found that almost all of them were measuring
one of five things. Those five are the sections below. Nothing here is clever;
the value is that the five are checked separately and that a dimension with
nothing to report says so, instead of being quietly skipped.

Stdlib only. No pandas, no network, no server.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LAB01 = os.path.normpath(os.path.join(HERE, "..", "..", "labs", "lab01", "data"))
TODAY = dt.date(2026, 11, 1)

# The Lab 1 CSVs use uppercase column names. Rather than teach two vocabularies,
# map them onto the ones used here, so the same five checks run on both.
ALIASES = {
    "Id": "patient_id", "BIRTHDATE": "birth_date", "DEATHDATE": "death_date",
    "GENDER": "sex", "ZIP": "postcode", "FIRST": "given_name", "LAST": "surname",
    "START": "registration_date", "DATE": "sample_date",
}

SPECS = {
    # column          (required?, kind, pattern)
    "patient_id":        (True,  "id",   re.compile(r"^[A-Za-z0-9_-]+$")),
    "given_name":        (True,  "text", re.compile(r"^[A-Za-z' -]{2,40}$")),
    "surname":           (True,  "text", re.compile(r"^[A-Za-z' -]{2,40}$")),
    "birth_date":        (True,  "date", None),
    "sex":               (True,  "code", re.compile(r"^[MF]$")),
    "postcode":          (False, "code", re.compile(r"^\d{5}$")),
    "phone":             (False, "code", re.compile(r"^\d{4}-\d{6}$")),
    "amka":              (False, "code", re.compile(r"^\d{11}$")),
    "registration_date": (False, "date", None),
    "sample_date":       (False, "date", None),
    "death_date":        (False, "date", None),
    "address":           (False, "text", None),
}


def parse_date(v):
    try:
        return dt.date.fromisoformat(v[:10])
    except Exception:
        return None


def apply_aliases(rows):
    """Rename known uppercase columns so the checks below find them."""
    out = []
    for row in rows:
        out.append({ALIASES.get(k, k): v for k, v in row.items()})
    return out


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return apply_aliases(list(csv.DictReader(fh)))


def pct(n, d):
    return 0.0 if not d else 100.0 * n / d


# ----------------------------------------------------------------------
# 1. completeness — is the value there at all
# ----------------------------------------------------------------------
def completeness(rows, findings):
    print("\n1. COMPLETENESS            is the value present")
    print("   %-20s %8s %8s" % ("column", "present", "%"))
    n = len(rows)
    for col in rows[0]:
        present = sum(1 for r in rows if (r.get(col) or "").strip())
        p = pct(present, n)
        flag = ""
        req = SPECS.get(col, (False,))[0]
        if req and present < n:
            flag = "  <- required and missing"
            findings.append("completeness: %s is required and absent in %d rows" % (col, n - present))
        elif p < 60 and col in SPECS:
            flag = "  <- under 60%, cannot be relied on"
            findings.append("completeness: %s present in only %.0f%% of rows" % (col, p))
        elif p < 60:
            flag = "  <- sparse, and not a column this profile knows about"
        print("   %-20s %8d %7.1f%%%s" % (col, present, p, flag))


# ----------------------------------------------------------------------
# 2. correctness — does the value conform to what it claims to be
# ----------------------------------------------------------------------
def correctness(rows, findings):
    print("\n2. CORRECTNESS             does the value conform to its format")
    print("   %-20s %8s %8s" % ("column", "invalid", "of non-blank"))
    any_bad = False
    for col in rows[0]:
        spec = SPECS.get(col)
        if not spec:
            continue
        _, kind, pattern = spec
        vals = [(r.get(col) or "").strip() for r in rows]
        vals = [v for v in vals if v]
        bad = 0
        for v in vals:
            if kind == "date":
                if parse_date(v) is None:
                    bad += 1
            elif pattern is not None and not pattern.match(v):
                bad += 1
        if vals:
            print("   %-20s %8d %8d" % (col, bad, len(vals)))
        if bad:
            any_bad = True
            findings.append("correctness: %d values in %s do not match the expected format" % (bad, col))
    if not any_bad:
        print("   no format violations anywhere. This is the weakest of the five")
        print("   dimensions: a file can pass every format check and still be wrong.")


# ----------------------------------------------------------------------
# 3. concordance — do fields that should agree, agree
# ----------------------------------------------------------------------
def concordance(rows, findings):
    print("\n3. CONCORDANCE             do two fields that should agree, agree")
    checkable = disagree = 0
    examples = []
    for r in rows:
        amka = (r.get("amka") or "").strip()
        birth = parse_date((r.get("birth_date") or "").strip())
        if len(amka) != 11 or birth is None:
            continue
        checkable += 1
        try:
            embedded = (int(amka[0:2]), int(amka[2:4]), int(amka[4:6]))
        except ValueError:
            continue
        if embedded != (birth.day, birth.month, birth.year % 100):
            disagree += 1
            if len(examples) < 4:
                examples.append("%s  amka %s says %02d-%02d-%02d, birth_date says %s"
                                % (r.get("patient_id"), amka, embedded[0], embedded[1],
                                   embedded[2], birth.isoformat()))
    if checkable:
        print("   AMKA against date of birth")
        print("   the first six digits of an AMKA are the holder's date of birth,")
        print("   DDMMYY. Two independent fields, so they can be compared.")
        print("   checkable %d    disagree %d  (%.1f%%)" % (checkable, disagree, pct(disagree, checkable)))
        for e in examples:
            print("     %s" % e)
        if disagree:
            findings.append("concordance: %d of %d rows have an AMKA that contradicts the birth date beside it"
                            % (disagree, checkable))
    else:
        print("   no row carries both an AMKA and a birth date. Nothing to check,")
        print("   which is not the same as nothing wrong.")

    # sex against the grammatical form of a Greek surname
    fem = sum(1 for r in rows
              if (r.get("sex") or "") == "M" and (r.get("surname") or "").endswith(("ou", "aki", "a")))
    if fem:
        print("   sex against surname form: %d male rows carry a feminine surname ending." % fem)
        print("   In Greek this is a signal, not proof: it is also how many of these")
        print("   surnames are spelt in the nominative for men. Report it, do not act on it.")

    # death before birth, where both exist
    bad = 0
    for r in rows:
        b, d = parse_date(r.get("birth_date") or ""), parse_date(r.get("death_date") or "")
        if b and d and d < b:
            bad += 1
    if bad:
        print("   %d rows record a death before the birth." % bad)
        findings.append("concordance: %d rows record a death before the birth" % bad)


# ----------------------------------------------------------------------
# 4. plausibility — could this be true of a person
# ----------------------------------------------------------------------
def plausibility(rows, findings):
    print("\n4. PLAUSIBILITY            could this be true of a human being")
    births = [parse_date(r.get("birth_date") or "") for r in rows]
    births = [b for b in births if b]
    future = sum(1 for b in births if b > TODAY)
    ages = [(TODAY - b).days / 365.25 for b in births]
    old = sum(1 for a in ages if a > 115)
    print("   birth dates in the future            %d" % future)
    print("   implied ages over 115 years          %d" % old)
    if ages:
        print("   age range                            %.1f to %.1f years" % (min(ages), max(ages)))
    if future:
        findings.append("plausibility: %d birth dates are in the future" % future)
    if old:
        findings.append("plausibility: %d rows imply an age over 115" % old)

    for col, label in (("registration_date", "registration"), ("sample_date", "sample")):
        if col not in rows[0]:
            continue
        fut = before = 0
        for r in rows:
            d, b = parse_date(r.get(col) or ""), parse_date(r.get("birth_date") or "")
            if not d:
                continue
            if d > TODAY:
                fut += 1
            if b and d < b:
                before += 1
        print("   %s dates in the future%s%d" % (label, " " * (18 - len(label)), fut))
        print("   %s dates before the birth%s%d" % (label, " " * (14 - len(label)), before))
        if fut:
            findings.append("plausibility: %d %s dates are in the future" % (fut, label))
        if before:
            findings.append("plausibility: %d %s dates fall before the patient's birth" % (before, label))

    # uniqueness of an identifier that is supposed to be unique
    for col in ("amka", "patient_id"):
        if col not in rows[0]:
            continue
        vals = [(r.get(col) or "").strip() for r in rows]
        vals = [v for v in vals if v]
        dupes = [(v, c) for v, c in Counter(vals).items() if c > 1]
        print("   %-20s duplicated values  %d" % (col, len(dupes)))
        if dupes:
            for v, c in dupes[:3]:
                who = [r["patient_id"] for r in rows if (r.get(col) or "").strip() == v]
                print("     %s appears %d times: %s" % (v, c, ", ".join(who)))
            findings.append("plausibility: %s is not unique (%d repeated values)" % (col, len(dupes)))


# ----------------------------------------------------------------------
# 5. currency — is the record recent enough to mean anything
# ----------------------------------------------------------------------
def currency(rows, findings):
    print("\n5. CURRENCY                is the record recent enough to be true")
    col = "sample_date" if "sample_date" in rows[0] else "registration_date"
    if col not in rows[0]:
        print("   no date column to age the records by.")
        return
    ds = [parse_date(r.get(col) or "") for r in rows]
    ds = [d for d in ds if d and d <= TODAY]
    if not ds:
        print("   no usable dates.")
        return
    ages = sorted((TODAY - d).days for d in ds)
    med = ages[len(ages) // 2]
    over5 = sum(1 for a in ages if a > 5 * 365)
    print("   column used                          %s" % col)
    print("   oldest / median / newest (days)      %d / %d / %d" % (ages[-1], med, ages[0]))
    print("   records older than five years        %d  (%.1f%%)" % (over5, pct(over5, len(ages))))
    print("   An address or a phone number five years old is not wrong. It is")
    print("   just no longer a way to reach anybody, and linkage on it will fail.")
    if pct(over5, len(ages)) > 25:
        findings.append("currency: %.0f%% of records are more than five years old" % pct(over5, len(ages)))


def profile(path, label, quiet=False):
    rows = read(path)
    print("\n" + "=" * 72)
    print("%s      %d rows, %d columns" % (label, len(rows), len(rows[0])))
    print("=" * 72)
    findings = []
    completeness(rows, findings)
    correctness(rows, findings)
    concordance(rows, findings)
    plausibility(rows, findings)
    currency(rows, findings)
    print("\n   FINDINGS (%d)" % len(findings))
    if not findings:
        print("     none. Say which dimensions you checked, so that a reader can")
        print("     tell this apart from not having looked.")
    for f in findings:
        print("     - %s" % f)
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", choices=["site_a", "site_b"], help="profile only one")
    ap.add_argument("--lab01", action="store_true", help="profile the Lab 1 cohort instead")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.lab01:
        p = os.path.join(LAB01, "patients.csv")
        if not os.path.exists(p):
            raise SystemExit("Cannot find %s. Run this from lectures/week07 inside the repository." % p)
        found = profile(p, "labs/lab01/data/patients.csv", args.quiet)
        print("\n" + "-" * 72)
        print("Concordance, plausibility and currency report nothing at all, and the")
        print("completeness findings are columns the generator never fills. No")
        print("contradiction, no impossible age, no date in the future, no repeated")
        print("identifier. Real data never looks like this, and a pipeline tested")
        print("only on it will meet its first real file unprepared.")
        print("")
        print("That is also why Week 7 ships its own two files: the faults have to be")
        print("put there on purpose, because this cohort has none to find.")
        return

    names = [args.file] if args.file else ["site_a", "site_b"]
    for name in names:
        profile(os.path.join(DATA, "%s.csv" % name), "data/%s.csv" % name, args.quiet)


if __name__ == "__main__":
    main()
