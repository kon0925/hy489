#!/usr/bin/env python3
"""Make the cohort k-anonymous, and count what it costs.

    python3 anonymise.py                 # the whole thing
    python3 anonymise.py --k 5           # one value of k, in detail
    python3 anonymise.py --lattice       # every generalisation, with its k
    python3 anonymise.py --attacks       # homogeneity and background knowledge
    python3 anonymise.py --write out.csv # a k-anonymous release you can inspect

k-anonymity (Samarati and Sweeney, 1998): every record is indistinguishable
from at least k-1 others on the quasi-identifiers. You get there by
generalising (a date of birth becomes a year, a postcode becomes a region) and
by suppressing the records that will not join a large enough group.

The interesting number is never k. It is what k cost you.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict

from common import NONE, attach_sensitive, load_patients, pct

# ---------------------------------------------------------------------
# generalisation hierarchies
# ---------------------------------------------------------------------
# Each level is coarser than the last. Level 0 is the raw value.

REGION = {
    "71201": "Heraklion RU", "72100": "Lasithi RU", "72200": "Lasithi RU",
    "72300": "Lasithi RU", "73100": "Chania RU", "74100": "Rethymno RU",
}


def gen_zip(v, level):
    if level == 0:
        return v
    if level == 1:
        return REGION.get(v, "other")
    return "Crete"


ZIP_LEVELS = ["postcode", "regional unit", "Crete"]


def gen_date(v, level):
    y = int(v[:4])
    if level == 0:
        return v                       # 1979-06-07
    if level == 1:
        return v[:7]                   # 1979-06
    if level == 2:
        return v[:4]                   # 1979
    if level == 3:
        return "%d-%d" % (y // 5 * 5, y // 5 * 5 + 4)
    if level == 4:
        return "%d-%d" % (y // 10 * 10, y // 10 * 10 + 9)
    return "any"


DATE_LEVELS = ["exact date", "year and month", "year", "5-year band",
               "10-year band", "suppressed"]


def gen_sex(v, level):
    return v if level == 0 else "any"


SEX_LEVELS = ["M/F", "suppressed"]

LATTICE = [(z, d, s)
           for z in range(len(ZIP_LEVELS))
           for d in range(len(DATE_LEVELS))
           for s in range(len(SEX_LEVELS))]


def key_for(row, levels):
    z, d, s = levels
    return (gen_zip(row["ZIP"], z), gen_date(row["BIRTHDATE"], d), gen_sex(row["GENDER"], s))


def classes_for(rows, levels):
    out = defaultdict(list)
    for r in rows:
        out[key_for(r, levels)].append(r)
    return out


# ---------------------------------------------------------------------
# k-anonymity
# ---------------------------------------------------------------------
def apply_k(rows, levels, k, max_suppress):
    """Generalise, then suppress every class smaller than k.

    Returns (kept rows, suppressed rows, classes) or None if suppression
    would exceed the budget."""
    cls = classes_for(rows, levels)
    kept, dropped = [], []
    for key, members in cls.items():
        (kept if len(members) >= k else dropped).extend(members)
    if len(dropped) > max_suppress * len(rows):
        return None
    surviving = {key: m for key, m in cls.items() if len(m) >= k}
    return kept, dropped, surviving


# What each level costs an analyst. These weights are a judgement, not a
# theorem: they say that losing the birth date altogether hurts far more than
# coarsening it, and that losing sex hurts more than either. Change them and
# the "minimal" generalisation changes, which is itself worth knowing.
ZIP_COST = [0, 1, 3]
DATE_COST = [0, 1, 2, 3, 4, 9]
SEX_COST = [0, 7]


def cost(levels):
    """How much information the generalisation gives up. Lower is better."""
    z, d, s = levels
    return ZIP_COST[z] + DATE_COST[d] + SEX_COST[s]


def minimal_generalisation(rows, k, max_suppress):
    best = None
    for levels in LATTICE:
        res = apply_k(rows, levels, k, max_suppress)
        if res is None:
            continue
        kept, dropped, surviving = res
        c = (cost(levels), len(dropped))
        if best is None or c < best[0]:
            best = (c, levels, kept, dropped, surviving)
    return best


# ---------------------------------------------------------------------
# l-diversity and t-closeness
# ---------------------------------------------------------------------
def l_diversity(surviving):
    """Smallest number of distinct sensitive values in any class."""
    if not surviving:
        return 0, None
    worst_key, worst_l = None, None
    for key, members in surviving.items():
        l = len(set(m["_sensitive"] for m in members))
        if worst_l is None or l < worst_l:
            worst_l, worst_key = l, key
    return worst_l, worst_key


def tv_distance(p, q):
    """Total variation distance between two distributions over the same keys."""
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(x, 0.0) - q.get(x, 0.0)) for x in keys)


def t_closeness(rows, surviving):
    glob = Counter(r["_sensitive"] for r in rows)
    n = sum(glob.values())
    gdist = {k: v / n for k, v in glob.items()}
    worst_t, worst_key = 0.0, None
    for key, members in surviving.items():
        c = Counter(m["_sensitive"] for m in members)
        m = sum(c.values())
        d = tv_distance({k: v / m for k, v in c.items()}, gdist)
        if d > worst_t:
            worst_t, worst_key = d, key
    return worst_t, worst_key


# ---------------------------------------------------------------------
# utility
# ---------------------------------------------------------------------
def utility(rows, kept, levels, surviving):
    """Three questions somebody might actually want to ask."""
    z, d, s = levels
    out = {}
    out["records published"] = "%d of %d (%.1f%%)" % (len(kept), len(rows), pct(len(kept), len(rows)))
    out["geography"] = ZIP_LEVELS[z] + (
        "" if z == 0 else "  (per-town rates no longer answerable)")
    out["age"] = DATE_LEVELS[d] + (
        "" if d <= 2 else "  (exact age no longer answerable)")
    out["sex"] = SEX_LEVELS[s] + ("" if s == 0 else "  (no rate by sex at all)")
    sizes = [len(m) for m in surviving.values()]
    out["equivalence classes"] = "%d, smallest %d, mean %.1f" % (
        len(sizes), min(sizes) if sizes else 0,
        (sum(sizes) / len(sizes)) if sizes else 0)
    # a concrete analytic question
    before = diabetes_by_band(rows, 4, 0)
    after = diabetes_by_band(kept, max(d, 4), s)
    out["cells in 'diabetes by decade and sex'"] = "%d before, %d after" % (len(before), len(after))
    return out


def diabetes_by_band(rows, dlevel, slevel):
    cells = defaultdict(lambda: [0, 0])
    for r in rows:
        key = (gen_date(r["BIRTHDATE"], dlevel), gen_sex(r["GENDER"], slevel))
        cells[key][0] += 1
        if r["_sensitive"] == "Type 2 diabetes mellitus":
            cells[key][1] += 1
    return cells


# ---------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------
def report_lattice(rows):
    print("\nEVERY GENERALISATION, AND THE k IT ACHIEVES WITH NO SUPPRESSION")
    print("  %-14s %-16s %-10s %8s %9s" % ("geography", "date of birth", "sex", "min k", "classes"))
    for levels in LATTICE:
        z, d, s = levels
        cls = classes_for(rows, levels)
        mink = min(len(m) for m in cls.values())
        print("  %-14s %-16s %-10s %8d %9d"
              % (ZIP_LEVELS[z], DATE_LEVELS[d], SEX_LEVELS[s], mink, len(cls)))
    print("""
  Nothing in the top half of this table is publishable. A release with min k = 1
  contains somebody who is alone in their group, and that somebody is named the
  moment an attacker holds the same three fields.""")


def report_k(rows, k, max_suppress, verbose=True):
    best = minimal_generalisation(rows, k, max_suppress)
    if best is None:
        print("\n  k = %-3d  no generalisation reaches it within a %.0f%% suppression budget"
              % (k, 100 * max_suppress))
        return None
    (_, nd), levels, kept, dropped, surviving = best
    z, d, s = levels
    if not verbose:
        l, _ = l_diversity(surviving)
        t, _ = t_closeness(rows, surviving)
        print("  %-4d %-14s %-16s %-10s %6d %7.1f%% %6d %7d %7.2f"
              % (k, ZIP_LEVELS[z], DATE_LEVELS[d], SEX_LEVELS[s], len(dropped),
                 pct(len(dropped), len(rows)), len(surviving), l, t))
        return best
    print("\nk = %d, suppression budget %.0f%%" % (k, 100 * max_suppress))
    print("  minimal generalisation found:")
    print("    geography      %s" % ZIP_LEVELS[z])
    print("    date of birth  %s" % DATE_LEVELS[d])
    print("    sex            %s" % SEX_LEVELS[s])
    print("    suppressed     %d records (%.1f%%)" % (len(dropped), pct(len(dropped), len(rows))))
    print("\n  what the release can still answer:")
    for label, value in utility(rows, kept, levels, surviving).items():
        print("    %-38s %s" % (label, value))
    l, lkey = l_diversity(surviving)
    t, tkey = t_closeness(rows, surviving)
    print("\n  and what k does not tell you:")
    print("    smallest l-diversity   %d   in class %s" % (l, lkey))
    print("    worst t-closeness      %.2f   in class %s" % (t, tkey))
    return best


def report_attacks(rows, k=5, max_suppress=0.15):
    print("\nTWO ATTACKS THAT SURVIVE k-ANONYMITY")

    print("\n  1. HOMOGENEITY. If every member of a class shares a diagnosis,")
    print("     knowing somebody is in the class tells you their diagnosis,")
    print("     and k was no protection at all.")
    for kk in (2, 3, 5, 10):
        best = minimal_generalisation(rows, kk, max_suppress)
        if best is None:
            continue
        _, levels, kept, dropped, surviving = best
        homog = [(key, m) for key, m in surviving.items()
                 if len(set(x["_sensitive"] for x in m)) == 1]
        print("     k = %-3d  %3d of %3d classes hold a single sensitive value"
              % (kk, len(homog), len(surviving)))
        for key, m in homog[:2]:
            print("              %-32s %2d people, all '%s'"
                  % (" / ".join(str(x) for x in key), len(m), m[0]["_sensitive"]))
    print("""
     Note what happens as k rises: the homogeneous classes disappear. They
     disappear because the classes got big, not because anything checked for
     them. On another file, at the same k, they would not. k says nothing at
     all about the sensitive column, which is the column the attacker wants.""")

    best = minimal_generalisation(rows, k, max_suppress)
    if best is None:
        return
    _, levels, kept, dropped, surviving = best
    print("\n  2. BACKGROUND KNOWLEDGE. An attacker who can rule out one value")
    print("     shrinks the class from the outside. A class of %d holding only" % k)
    print("     two distinct diagnoses is one ruled-out value away from certainty.")
    two = [(key, m) for key, m in surviving.items()
           if len(set(x["_sensitive"] for x in m)) == 2]
    print("     at k = %d: %d of %d classes hold exactly two distinct values"
          % (k, len(two), len(surviving)))
    for key, m in two[:2]:
        vals = sorted(set(x["_sensitive"] for x in m))
        print("              %-32s %2d people: %s"
              % (" / ".join(str(x) for x in key), len(m), " | ".join(vals)))
    print("""
  This is why l-diversity (Machanavajjhala, 2007) asks for l well-represented
  values in every class, and why t-closeness (Li, 2007) asks that each class
  look like the file as a whole. Each costs more generalisation than the last,
  and each has its own published attack. There is no setting of k, l and t that
  ends the argument.""")


def write_release(rows, path, k, max_suppress):
    best = minimal_generalisation(rows, k, max_suppress)
    if best is None:
        raise SystemExit("no release at k = %d" % k)
    _, levels, kept, dropped, _ = best
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "birth", "sex", "condition"])
        for r in kept:
            key = key_for(r, levels)
            w.writerow([key[0], key[1], key[2], r["_sensitive"]])
    print("\n  wrote %s: %d rows, %d suppressed" % (path, len(kept), len(dropped)))
    print("  Open it. Every direct identifier is gone, every quasi-identifier is")
    print("  blurred, and it is still a file about 1,174 real people in a real")
    print("  prefecture. Decide for yourself whether you would publish it.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, help="report one value of k in detail")
    ap.add_argument("--suppress", type=float, default=0.15, help="suppression budget")
    ap.add_argument("--lattice", action="store_true")
    ap.add_argument("--attacks", action="store_true")
    ap.add_argument("--write", metavar="PATH")
    args = ap.parse_args()

    rows = attach_sensitive(load_patients())
    print("cohort %d records, %d distinct sensitive values"
          % (len(rows), len(set(r["_sensitive"] for r in rows))))

    if args.lattice:
        report_lattice(rows); return
    if args.write:
        write_release(rows, args.write, args.k or 5, args.suppress); return
    if args.attacks:
        report_attacks(rows, args.k or 5, args.suppress); return
    if args.k:
        report_k(rows, args.k, args.suppress); return

    print("\nWHAT EACH k COSTS   (suppression budget %.0f%%)" % (100 * args.suppress))
    print("  %-4s %-14s %-16s %-10s %6s %8s %6s %7s %7s"
          % ("k", "geography", "date of birth", "sex", "suppr", "", "classes", "min l", "max t"))
    for k in (2, 5, 10, 25, 50):
        report_k(rows, k, args.suppress, verbose=False)
    print("""
  Read the geography and date columns together. k = 2 is nearly free: a 5-year
  band and 7 records dropped. k = 5 costs the exact date of birth. k = 10 costs
  the town as well, and suppresses 135 people. By k = 25 the geography is "Crete"
  and you are publishing a 5-year band for an island of 650,000, which answers
  almost nothing a clinical study wants to ask.

  Two things in this table surprise people. k = 25 suppresses FEWER records than
  k = 10, because the generalisation got coarse enough that the small classes
  merged instead of being dropped: generalisation and suppression trade against
  each other, and the search picks whichever is cheaper. And the min l column
  rises on its own, without anything ever checking it, which is the next slide.""")
    report_k(rows, 5, args.suppress)
    report_attacks(rows, 5, args.suppress)


if __name__ == "__main__":
    main()
