#!/usr/bin/env python3
"""Re-identify the cohort you have been using since Week 1.

    python3 reidentify.py              # the whole attack
    python3 reidentify.py --risk       # uniqueness at each granularity
    python3 reidentify.py --attack     # the join against an external register
    python3 reidentify.py --coverage 0.4   # a smaller external register

The claim this script is here to make concrete:

    removing the names is not anonymisation.

We strip every direct identifier from patients.csv, which is what "de-identified"
means in most of the health data you will ever be handed. Then we attack what is
left, using nothing but demographic fields that somebody else also holds.

Stdlib only. The data is synthetic; nothing here corresponds to a real person,
and that is the only reason it is safe to do this in a lecture theatre.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict

from common import (DIRECT_IDENTIFIERS, QUASI_IDENTIFIERS, attach_sensitive,
                    load_patients, pct, risk)

# Each entry: (label, how to build the key from a row)
GRANULARITIES = [
    ("ZIP + full birth date + sex", lambda r: (r["ZIP"], r["BIRTHDATE"], r["GENDER"])),
    ("ZIP + birth month + sex",     lambda r: (r["ZIP"], r["BIRTHDATE"][:7], r["GENDER"])),
    ("ZIP + birth year + sex",      lambda r: (r["ZIP"], r["BIRTHDATE"][:4], r["GENDER"])),
    ("first 3 of ZIP + year + sex", lambda r: (r["ZIP"][:3], r["BIRTHDATE"][:4], r["GENDER"])),
    ("county + birth year + sex",   lambda r: (r["COUNTY"], r["BIRTHDATE"][:4], r["GENDER"])),
    ("full birth date + sex, no geography", lambda r: (r["BIRTHDATE"], r["GENDER"])),
    ("birth year + sex only",       lambda r: (r["BIRTHDATE"][:4], r["GENDER"])),
    ("5-year band + sex",           lambda r: (str(int(r["BIRTHDATE"][:4]) // 5 * 5), r["GENDER"])),
    ("10-year band + sex",          lambda r: (str(int(r["BIRTHDATE"][:4]) // 10 * 10), r["GENDER"])),
]


def show_what_is_in_the_file(rows):
    print("\nWHAT IS IN patients.csv")
    present_direct = [c for c in DIRECT_IDENTIFIERS if c in rows[0]]
    present_quasi = [c for c in QUASI_IDENTIFIERS if c in rows[0]]
    print("  direct identifiers    %s" % ", ".join(present_direct))
    print("  quasi-identifiers     %s" % ", ".join(present_quasi))
    filled = sum(1 for r in rows if r.get("SSN", "").strip())
    print("\n  every one of the %d rows carries a social security number (%d non-blank)."
          % (len(rows), filled))
    print("  In a Greek file that column is an AMKA, and it is there for the same")
    print("  operational reason: somebody downstream needs to bill.")
    print("\n  Step zero is to drop the direct identifiers. Everything below happens")
    print("  AFTER that step, on a file a lawyer would call de-identified.")


def report_risk(rows):
    n = len(rows)
    print("\nUNIQUENESS, after every direct identifier has been removed")
    print("  %-38s %10s %10s %10s %7s" % ("quasi-identifier set", "unique", "k<=2", "k<=5", "classes"))
    for label, keyfn in GRANULARITIES:
        u, k2, k5, classes, smallest = risk(rows, keyfn)
        print("  %-38s %4d %5.1f%% %4d %5.1f%% %4d %5.1f%% %7d"
              % (label, u, pct(u, n), k2, pct(k2, n), k5, pct(k5, n), classes))
    print("""
  Read the top row first. With a postcode, a date of birth and a sex, 99.7%
  of this cohort is alone in its own group. Not 'hard to identify': alone.
  Anyone who learns those three facts about a person has found their row.

  Then read down the first column. Giving up the day and the month of birth
  takes uniqueness from 99.7% to 34.3%. Giving up the geography entirely
  takes it from 99.7% to 98.1%, which is almost nothing.

  In this cohort the birth date carries nearly all the risk, because there are
  only six postcodes in it. Generalising a field only helps where the field had
  resolution to lose. Check which of your fields that is before you decide what
  to blur.""")


def race_note(rows):
    races = Counter(r.get("RACE", "") for r in rows)
    eths = Counter(r.get("ETHNICITY", "") for r in rows)
    if len(races) == 1 and len(eths) == 1:
        print("""
  One more thing this table does not show. RACE and ETHNICITY take a single
  value across all 1,174 rows, so they contribute nothing to the attack. That
  is an artefact of the generator, not a property of health data: in a real
  file they are high-risk quasi-identifiers precisely because they are rare in
  some combinations, and under GDPR Article 9 they are also special-category
  data in their own right. Do not conclude from this cohort that they are safe.""")


def build_external_register(rows, coverage, seed=489):
    """What an attacker plausibly has.

    An electoral roll, a customer list, a marketing database, a leaked
    breach, a school register, or a few hundred profiles scraped from social
    media. It holds a name and the same demographics, for SOME of the
    population. It does not hold anybody's diagnoses.
    """
    rng = random.Random(seed)
    reg = []
    for r in rows:
        if rng.random() > coverage:
            continue
        reg.append({
            "name": "%s %s" % (r["FIRST"], r["LAST"]),
            "ZIP": r["ZIP"],
            "BIRTHDATE": r["BIRTHDATE"],
            "GENDER": r["GENDER"],
        })
    return reg


def attack(rows, coverage):
    register = build_external_register(rows, coverage)
    print("\nTHE ATTACK")
    print("  the attacker holds a register of %d people: name, postcode," % len(register))
    print("  date of birth, sex. No diagnoses. %.0f%% of the cohort is in it." % (100 * coverage))

    index = defaultdict(list)
    for e in register:
        index[(e["ZIP"], e["BIRTHDATE"], e["GENDER"])].append(e)

    cohort_counts = Counter((r["ZIP"], r["BIRTHDATE"], r["GENDER"]) for r in rows)

    named, ambiguous, not_in_register = 0, 0, 0
    examples = []
    for r in rows:
        key = (r["ZIP"], r["BIRTHDATE"], r["GENDER"])
        hits = index.get(key, [])
        if not hits:
            not_in_register += 1
        elif len(hits) == 1 and cohort_counts[key] == 1:
            named += 1
            if len(examples) < 5:
                examples.append((hits[0]["name"], key, r["_sensitive"]))
        else:
            ambiguous += 1

    n = len(rows)
    print("\n  %4d records named outright        %5.1f%%" % (named, pct(named, n)))
    print("  %4d narrowed to a small group     %5.1f%%" % (ambiguous, pct(ambiguous, n)))
    print("  %4d not in the register at all    %5.1f%%" % (not_in_register, pct(not_in_register, n)))
    print("\n  Named, with the diagnosis attached:")
    for name, key, sens in examples:
        print("    %-26s %s %s %-2s   ->  %s" % (name, key[0], key[1], key[2], sens))
    print("""
  The attacker learned a diagnosis. That is the harm, and notice what it took:
  no cryptography, no breach of the hospital, and no access to anything the
  hospital considers confidential. A join, on three columns, against a list
  anybody can assemble.

  The attacker also does not need to be right about everybody. One confirmed
  match on one person they care about is the whole attack.""")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--risk", action="store_true", help="only the uniqueness table")
    ap.add_argument("--attack", action="store_true", help="only the attack")
    ap.add_argument("--coverage", type=float, default=0.6,
                    help="fraction of the cohort the attacker's register holds")
    args = ap.parse_args()

    rows = attach_sensitive(load_patients())
    if not args.attack:
        show_what_is_in_the_file(rows)
        report_risk(rows)
        race_note(rows)
    if not args.risk:
        attack(rows, args.coverage)


if __name__ == "__main__":
    main()
