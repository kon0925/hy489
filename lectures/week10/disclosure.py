#!/usr/bin/env python3
"""Check an aggregate output the way an output checker checks it.

    python3 disclosure.py                 # the whole thing
    python3 disclosure.py --table         # the cross-tabulation, unprotected
    python3 disclosure.py --threshold     # the minimum cell count rule
    python3 disclosure.py --recover       # subtract a suppressed cell back out
    python3 disclosure.py --secondary     # complementary suppression, and its cost
    python3 disclosure.py --dominance     # the (n,k) and p% rules on a cost table
    python3 disclosure.py --differencing  # two approved outputs, one person

A trusted research environment lets a researcher compute on identifiable data
and take nothing out but aggregates. Somebody has to decide which aggregates
are safe to release. That job is statistical disclosure control, it is done by
a human against a rule book, and this script is the rule book.

Every number below comes from the Lab 1 cohort of 1,174 synthetic patients.

Stdlib only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from common import BAND_LABELS, TOWN, TOWNS, age_of, band_of, clean, pct, read

CONDITION = "Essential hypertension"

# Short labels, so the magnitude table fits on a slide.
DRUG_LABEL = {
    "24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet": "metformin 500 ER",
    "Salbutamol 0.83 MG/ML Inhalation Solution": "salbutamol 0.83",
    "amLODIPine 5 MG Oral Tablet": "amlodipine 5",
    "amoxicillin 500 MG Oral Capsule": "amoxicillin 500",
    "lisinopril 10 MG Oral Tablet": "lisinopril 10",
    "simvastatin 20 MG Oral Tablet": "simvastatin 20",
}
SUPPRESSED = "    ."          # a primary suppression in a printed table
SECONDARY = "    :"           # a complementary suppression


# ----------------------------------------------------------------------
# building the table
# ----------------------------------------------------------------------
def load_cohort():
    patients = read("patients.csv")
    conditions = read("conditions.csv")
    cond = defaultdict(set)
    for r in conditions:
        cond[r["PATIENT"]].add(clean(r["DESCRIPTION"]))
    for p in patients:
        p["_age"] = age_of(p)
        p["_band"] = band_of(p["_age"])
        p["_town"] = TOWN[p["ZIP"]]
        p["_conditions"] = cond[p["Id"]]
    return patients


def crosstab(patients, condition=CONDITION):
    """town by age band, counting patients with the condition."""
    tab = Counter()
    for p in patients:
        if condition in p["_conditions"]:
            tab[(p["_town"], p["_band"])] += 1
    return tab


def row_total(tab, r, cols):
    return sum(tab[(r, c)] for c in cols)


def col_total(tab, c, rows):
    return sum(tab[(r, c)] for r in rows)


def grand_total(tab):
    return sum(tab.values())


def show(tab, rows, cols, marks=None, title=None, width=16):
    """Print the table. marks maps a cell to the string printed in its place."""
    marks = marks or {}
    if title:
        print("  %s" % title)
    print("  %-*s %s %8s" % (width, "", " ".join("%7s" % c for c in cols), "total"))
    for r in rows:
        cells = []
        for c in cols:
            key = (r, c)
            cells.append("%7s" % marks[key] if key in marks else "%7d" % tab[key])
        print("  %-*s %s %8d" % (width, r, " ".join(cells), row_total(tab, r, cols)))
    print("  %-*s %s %8d" % (width, "total",
                             " ".join("%7d" % col_total(tab, c, rows) for c in cols),
                             grand_total(tab)))


# ----------------------------------------------------------------------
# the threshold rule
# ----------------------------------------------------------------------
def primary_suppression(tab, rows, cols, threshold):
    """Cells with a count of 1 to threshold-1. A zero is not a disclosure."""
    return {(r, c) for r in rows for c in cols if 0 < tab[(r, c)] < threshold}


def loss(tab, rows, cols, sup):
    cells = len(rows) * len(cols)
    hidden = sum(tab[k] for k in sup)
    return (len(sup), cells, hidden, grand_total(tab),
            pct(cells - len(sup), cells), pct(grand_total(tab) - hidden, grand_total(tab)))


def report_table(tab):
    print("\nTHE OUTPUT A RESEARCHER ASKS TO TAKE OUT")
    show(tab, TOWNS, BAND_LABELS,
         title="patients with a recorded diagnosis of %s, by town and age band" % CONDITION.lower())
    print("""
  Nothing in this table names anybody. It is counts of people, it answers a
  question a public health service would want answered, and a researcher who
  spent three months inside the environment would expect to walk out with it.

  Two cells in it are a disclosure. Finding them is the rest of this script.""")


def report_threshold(tab):
    print("\nRULE 1: MINIMUM CELL COUNT")
    print("  Suppress any cell holding fewer than n patients. A cell of 1 names a")
    print("  person to anybody who knows the town and the age band. A cell of 2")
    print("  lets each of the two work out the other.")
    for threshold in (5, 10):
        sup = primary_suppression(tab, TOWNS, BAND_LABELS, threshold)
        marks = {k: SUPPRESSED for k in sup}
        print()
        show(tab, TOWNS, BAND_LABELS, marks, title="n < %d suppressed" % threshold)
        ns, cells, hidden, total, cpct, vpct = loss(tab, TOWNS, BAND_LABELS, sup)
        print("    %d of %d cells suppressed, hiding %d of %d patients"
              % (ns, cells, hidden, total))
        print("    %.1f%% of cells published, %.1f%% of the count published"
              % (cpct, vpct))
    print("""
  At n < 5 the table loses 2 cells and 8 patients, and still answers the
  question it was asked. At n < 10 it loses 17 cells and 110 patients, the
  0-17 column goes entirely, the 18-34 column keeps two cells of six, and the
  researcher comes back to argue. Both thresholds are in use: Eurostat and
  most national statistics offices work at 5 for health counts, the UK Office
  for National Statistics uses 10 for small-area health data, and the number
  is a policy, not a theorem.

  The arithmetic in the next section is why the threshold on its own is not a
  rule at all.""")


# ----------------------------------------------------------------------
# recovery by subtraction
# ----------------------------------------------------------------------
def recoverable(tab, rows, cols, sup):
    """Lines holding exactly one suppressed cell. Each one gives that cell away."""
    out = []
    for r in rows:
        line = [(r, c) for c in cols if (r, c) in sup]
        if len(line) == 1:
            published = sum(tab[(r, c)] for c in cols if (r, c) not in sup)
            out.append(("row", r, line[0], row_total(tab, r, cols), published))
    for c in cols:
        line = [(r, c) for r in rows if (r, c) in sup]
        if len(line) == 1:
            published = sum(tab[(r, c)] for r in rows if (r, c) not in sup)
            out.append(("column", c, line[0], col_total(tab, c, rows), published))
    return out


def report_recover(tab):
    threshold = 5
    sup = primary_suppression(tab, TOWNS, BAND_LABELS, threshold)
    print("\nRECOVERING A SUPPRESSED CELL WITH SUBTRACTION")
    print("  The table was published with its row and column totals, because a table")
    print("  without totals is hard to read. The totals were computed before the")
    print("  suppression, which is the whole problem.")
    hits = recoverable(tab, TOWNS, BAND_LABELS, sup)
    print()
    print("  %-8s %-16s %-24s %7s %10s %9s" %
          ("line", "", "suppressed cell", "total", "published", "recovered"))
    for kind, label, cell, total, published in hits:
        print("  %-8s %-16s %-24s %7d %10d %9d"
              % (kind, label, "%s / %s" % cell, total, published, total - published))
    print("""
  Work through the first line by hand. The Heraklion row was published as
  5, suppressed, 8, 17, 18, 14, and the row total was published as 66. Add up
  what you can see: 5 + 8 + 17 + 18 + 14 = 62. The row total is 66. The cell
  the checker suppressed holds 4 people, and it took one subtraction.

  Both suppressed cells fall out twice, once from their row and once from their
  column, so the checker had two independent chances to notice and took
  neither. The suppression removed the number from the page and left it in the
  arithmetic.""")


# ----------------------------------------------------------------------
# complementary suppression
# ----------------------------------------------------------------------
def complementary(tab, rows, cols, sup):
    """Suppress more cells until no line holds exactly one suppression.

    The cheapest extra cell in a line is the smallest one, because the count it
    hides is the information the release gives up. Ties break on the cell key,
    so the result does not depend on dictionary order.
    """
    s = set(sup)
    added = set()
    changed = True
    while changed:
        changed = False
        for r in rows:
            cells = [(r, c) for c in cols]
            if len([k for k in cells if k in s]) == 1:
                free = sorted((tab[k], k) for k in cells if k not in s)
                if free:
                    s.add(free[0][1]); added.add(free[0][1]); changed = True
        for c in cols:
            cells = [(r, c) for r in rows]
            if len([k for k in cells if k in s]) == 1:
                free = sorted((tab[k], k) for k in cells if k not in s)
                if free:
                    s.add(free[0][1]); added.add(free[0][1]); changed = True
    return s, added


def intervals(tab, rows, cols, sup):
    """What an attacker can still say about each suppressed cell.

    A cell is bounded below by zero and above by whatever is left over in its
    row and in its column once the published cells are subtracted. A real
    attacker solves the whole system as a linear program and does better than
    this; these are the bounds a student can compute with a pencil.
    """
    out = []
    for (r, c) in sorted(sup):
        row_res = row_total(tab, r, cols) - sum(tab[(r, x)] for x in cols if (r, x) not in sup)
        col_res = col_total(tab, c, rows) - sum(tab[(x, c)] for x in rows if (x, c) not in sup)
        out.append(((r, c), tab[(r, c)], 0, min(row_res, col_res)))
    return out


def report_secondary(tab):
    threshold = 5
    sup = primary_suppression(tab, TOWNS, BAND_LABELS, threshold)
    full, added = complementary(tab, TOWNS, BAND_LABELS, sup)
    print("\nRULE 2: COMPLEMENTARY SUPPRESSION")
    print("  A suppressed cell has to hide behind another suppressed cell. Suppress")
    print("  extra cells until every row and every column either holds no")
    print("  suppression or holds at least two.")
    marks = {}
    for k in sup:
        marks[k] = SUPPRESSED
    for k in added:
        marks[k] = SECONDARY
    print()
    show(tab, TOWNS, BAND_LABELS, marks,
         title=". = the %d cells the threshold caught   : = the %d cells it cost to hide them"
               % (len(sup), len(added)))
    hits = recoverable(tab, TOWNS, BAND_LABELS, full)
    print("\n    lines still holding exactly one suppressed cell: %d" % len(hits))
    ns, cells, hidden, total, cpct, vpct = loss(tab, TOWNS, BAND_LABELS, full)
    print("    %d of %d cells suppressed, hiding %d of %d patients"
          % (ns, cells, hidden, total))
    print("    %.1f%% of cells published, %.1f%% of the count published"
          % (cpct, vpct))
    print("\n  What the attacker can still say about each hidden cell:")
    print("    %-26s %6s   %s" % ("cell", "truth", "what the totals allow"))
    for (r, c), truth, lo, hi in intervals(tab, TOWNS, BAND_LABELS, full):
        print("    %-26s %6d   %d to %d" % ("%s / %s" % (r, c), truth, lo, hi))
    print("""
  The subtraction now returns a sum over two or three cells instead of a
  value, and the best an attacker gets with a pencil is a range. Read the
  ranges before calling this solved: the two cells the threshold caught are
  now known to lie between 0 and 10, which is weaker than knowing them and
  stronger than knowing nothing. Linear programming over the whole system of
  row and column equations tightens every one of those ranges, and that is
  what a serious attacker does.

  Count the cost. Protecting 2 cells took 7, and the release went from 94.4%
  of cells to 80.6%. The cells it took were small ones, so most of the count
  survived, and the published share only fell from 97.9% to 89.9%. That
  asymmetry is the argument an output checker has with a researcher every
  week: the table still carries the population, and it has stopped carrying
  the young.""")


# ----------------------------------------------------------------------
# magnitude tables and dominance
# ----------------------------------------------------------------------
def spend_table(patients, min_age=80):
    """Total medication spend, by drug and town, for the oldest patients.

    A magnitude table adds up a quantity instead of counting people, and the
    threshold rule does not protect it. A cell can hold twenty contributors
    and still be one person's bill.
    """
    ages = {p["Id"]: p["_age"] for p in patients}
    towns = {p["Id"]: p["_town"] for p in patients}
    cells = defaultdict(Counter)
    for r in read("medications.csv"):
        pid = r["PATIENT"]
        if pid not in ages or ages[pid] < min_age:
            continue
        cells[(DRUG_LABEL[r["DESCRIPTION"]], towns[pid])][pid] += float(r["TOTALCOST"])
    return cells


def nk_rule(values, n, k):
    """(n,k): suppress if the largest n contributors hold k% or more of the cell."""
    v = sorted(values, reverse=True)
    total = sum(v)
    return total > 0 and 100.0 * sum(v[:n]) / total >= k


def p_rule(values, p):
    """p%: suppress if the contributors other than the largest two can estimate
    the largest to better than p%. The second largest is the attacker here: it
    knows its own value, so it subtracts it and whatever else it can see."""
    v = sorted(values, reverse=True)
    if len(v) < 2:
        return True
    residual = sum(v[2:])
    return residual < (p / 100.0) * v[0]


def report_dominance(patients):
    cells = spend_table(patients)
    drugs = sorted({d for d, _ in cells})
    print("\nRULE 3: DOMINANCE, ON A TABLE OF MONEY")
    print("  Total medication spend in euro, patients aged 80 and over, by drug")
    print("  and town. Every cell has at least three contributors, so a minimum")
    print("  count rule of 3 passes the whole table.")
    print()
    print("  %-18s %s" % ("", " ".join("%9s" % t[:9] for t in TOWNS)))
    for d in drugs:
        row = []
        for t in TOWNS:
            c = cells.get((d, t))
            row.append("%9.0f" % sum(c.values()) if c else "%9s" % "-")
        print("  %-18s %s" % (d, " ".join(row)))
    print()
    print("  Contributors in each cell, and the share held by the largest one:")
    print("  %-18s %s" % ("", " ".join("%9s" % t[:9] for t in TOWNS)))
    for d in drugs:
        row = []
        for t in TOWNS:
            c = cells.get((d, t))
            if not c:
                row.append("%9s" % "-"); continue
            v = sorted(c.values(), reverse=True)
            row.append("%5d/%3.0f%%" % (len(v), 100.0 * v[0] / sum(v)))
        print("  %-18s %s" % (d, " ".join(row)))

    total_cells = len(cells)
    rules = [("minimum 3 contributors", lambda v: len(v) < 3),
             ("(n,k) with n=1, k=50", lambda v: nk_rule(v, 1, 50)),
             ("(n,k) with n=2, k=70", lambda v: nk_rule(v, 2, 70)),
             ("p% rule with p=10", lambda v: p_rule(v, 10))]
    print("\n  %-28s %8s %10s %12s" % ("rule", "cells", "suppressed", "share of euro"))
    grand = sum(sum(c.values()) for c in cells.values())
    for label, fn in rules:
        hit = [k for k, c in cells.items() if fn(list(c.values()))]
        hidden = sum(sum(cells[k].values()) for k in hit)
        print("  %-28s %8d %10d %12.1f%%" % (label, total_cells, len(hit),
                                              pct(hidden, grand)))
    worst = max(cells.items(), key=lambda kv: max(kv[1].values()) / sum(kv[1].values()))
    v = sorted(worst[1].values(), reverse=True)
    print("\n  The worst cell: %s, %s" % (worst[0][1], worst[0][0]))
    print("    %d contributors, cell total %.0f euro" % (len(v), sum(v)))
    print("    largest contributor %.0f euro, %.1f%% of the cell"
          % (v[0], 100.0 * v[0] / sum(v)))
    print("    everyone else put together: %.0f euro" % (sum(v) - v[0]))
    print("""
  Publish that cell and the largest contributor's own bill is known to within
  %.0f euro by anybody who knows the other contributors, and known to within
  %.0f%% by anybody who knows nothing at all. The patient is not named. Their
  spend is still out.

  The minimum count rule suppresses none of this table, because the cells are
  not small. That is the point of a dominance rule: it protects against a
  disclosure that counting cannot see.""" % (sum(v) - v[0], 100.0 - 100.0 * v[0] / sum(v)))


# ----------------------------------------------------------------------
# differencing
# ----------------------------------------------------------------------
def find_differencing(patients, condition=CONDITION, threshold=10):
    """Two queries, approved separately, that differ by one patient.

    A researcher asks for a count among patients born in or before some year.
    A week later they ask for the same count among patients born in or before
    the year before. Both pass the threshold. If exactly one person in the
    stratum was born in the year between them, the difference is that person.
    """
    strata = defaultdict(list)
    for p in patients:
        strata[(p["_town"], p["GENDER"])].append(p)
    found = []
    for key in sorted(strata):
        group = strata[key]
        years = Counter(int(p["BIRTHDATE"][:4]) for p in group)
        for year in sorted(years):
            if years[year] != 1:
                continue
            a = [p for p in group if int(p["BIRTHDATE"][:4]) <= year]
            b = [p for p in group if int(p["BIRTHDATE"][:4]) <= year - 1]
            ca = sum(1 for p in a if condition in p["_conditions"])
            cb = sum(1 for p in b if condition in p["_conditions"])
            if ca >= threshold and cb >= threshold and ca - cb == 1:
                target = next(p for p in group if int(p["BIRTHDATE"][:4]) == year)
                found.append((key, year, ca, cb, len(a), len(b), target))
    return found


def report_differencing(patients):
    threshold = 10
    found = find_differencing(patients, threshold=threshold)
    print("\nRULE 4: THE OUTPUT YOU ALREADY APPROVED")
    print("  Every rule above checks one table. A researcher submits many tables,")
    print("  over months, and each one is checked on its own.")
    key, year, ca, cb, na, nb, target = found[0]
    town, sex = key
    who = "women" if sex == "F" else "men"
    one = "woman" if sex == "F" else "man"
    they = "She" if sex == "F" else "He"
    print("""
  Request 1, approved in October. How many %s in %s, born in or
  before %d, have a recorded diagnosis of %s?

      denominator %d %s, answer %d. Above the threshold of %d, released.

  Request 2, approved in November, by a different checker. Same question,
  born in or before %d.

      denominator %d %s, answer %d. Above the threshold of %d, released.
""" % (who, town, year, CONDITION.lower(),
       na, who, ca, threshold, year - 1, nb, who, cb, threshold))
    print("  %d minus %d is 1. The two denominators differ by one %s, and" % (ca, cb, one))
    print("  there is exactly one %s in %s born in %d:" % (one, town, year))
    print("\n      %s %s, born %s, %s" % (target["FIRST"], target["LAST"],
                                          target["BIRTHDATE"][:10], target["_town"]))
    print("\n  %s has %s. Neither output named her, neither output"
          % (they, CONDITION.lower()))
    print("  held a cell below ten, and both were correctly approved.")

    print("\n  The same subtraction on a magnitude query, which is worse:")
    group = [p for p in patients if p["_town"] == town and p["GENDER"] == sex]
    a = [p for p in group if int(p["BIRTHDATE"][:4]) <= year]
    b = [p for p in group if int(p["BIRTHDATE"][:4]) <= year - 1]
    sa = sum(float(p["HEALTHCARE_EXPENSES"]) for p in a)
    sb = sum(float(p["HEALTHCARE_EXPENSES"]) for p in b)
    print("    total lifetime healthcare expenditure, %d %s   %12.2f euro" % (len(a), who, sa))
    print("    total lifetime healthcare expenditure, %d %s   %12.2f euro" % (len(b), who, sb))
    print("    difference                                        %12.2f euro" % (sa - sb))
    print("    her recorded expenditure                          %12.2f euro"
          % float(target["HEALTHCARE_EXPENSES"]))
    print("""
  Not a range, not an estimate. Her exact figure, to the cent, out of two
  totals over %d and %d people.

  There are %d such pairs in this cohort for this one condition, this one
  stratification and this one threshold. A checker who approves outputs one at
  a time cannot see any of them, because neither output is the problem. The
  defence is not a better rule; it is a record of every output a project has
  ever taken out, and a checker who reads it before approving the next one.
  That record is the thing nobody budgets for.""" % (len(a), len(b), len(found)))


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("table", "threshold", "recover", "secondary", "dominance", "differencing"):
        ap.add_argument("--" + flag, action="store_true")
    args = ap.parse_args()
    flags = [args.table, args.threshold, args.recover, args.secondary,
             args.dominance, args.differencing]
    run_all = not any(flags)

    patients = load_cohort()
    tab = crosstab(patients)
    if args.table or run_all:
        report_table(tab)
    if args.threshold or run_all:
        report_threshold(tab)
    if args.recover or run_all:
        report_recover(tab)
    if args.secondary or run_all:
        report_secondary(tab)
    if args.dominance or run_all:
        report_dominance(patients)
    if args.differencing or run_all:
        report_differencing(patients)


if __name__ == "__main__":
    main()
