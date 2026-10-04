#!/usr/bin/env python3
"""One differentially private count, worked end to end.

    python3 dp.py                  # the whole thing
    python3 dp.py --epsilon 1.0    # one privacy budget in detail
    python3 dp.py --small          # the same mechanism on a small cell
    python3 dp.py --budget         # what happens when you ask more than once

Differential privacy is a property of the MECHANISM, not of the output. It
says: whatever the attacker already knows, the answer you publish is almost
as likely whether or not any one person is in the file. "Almost" is epsilon.

    P(answer | file with you)  <=  e^epsilon  x  P(answer | file without you)

This script does one query, the simplest there is: a count. Everything about
the trade is visible in it.

Stdlib only.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics

from common import attach_sensitive, load_patients

TARGET = "Type 2 diabetes mellitus"


def laplace(scale, rng):
    """A Laplace draw, from a uniform one. Inverse transform, no numpy."""
    u = rng.random() - 0.5
    return -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))


def noisy_count(true_count, epsilon, rng, sensitivity=1.0):
    """The Laplace mechanism. Sensitivity of a count is 1: adding or removing
    one person changes the answer by at most one."""
    return true_count + laplace(sensitivity / epsilon, rng)


def describe_epsilon(eps):
    ratio = math.exp(eps)
    return "e^%.2f = %.2f, so any answer is at most %.2fx more likely with you in the file" % (
        eps, ratio, ratio)


def run_one(rows, epsilon, trials=10000, seed=489):
    rng = random.Random(seed)
    true = sum(1 for r in rows if r["_sensitive"] == TARGET)
    draws = sorted(noisy_count(true, epsilon, rng) for _ in range(trials))
    lo, hi = draws[int(0.025 * trials)], draws[int(0.975 * trials)]
    err = statistics.mean(abs(d - true) for d in draws)
    return true, lo, hi, err, draws


def report_main(rows):
    true = sum(1 for r in rows if r["_sensitive"] == TARGET)
    print("\nTHE QUERY")
    print("  How many people in the cohort have %s?" % TARGET.lower())
    print("  True answer: %d of %d." % (true, len(rows)))
    print("""
  Publishing that number exactly is not safe. If an attacker knows the answer
  for the file without one particular person, the exact answer with them in it
  reveals that person's diagnosis by subtraction. This is not hypothetical;
  it is how attacks on published aggregate statistics work.""")

    print("\nTHE SAME QUERY AT SEVERAL PRIVACY BUDGETS")
    print("  %-9s %-11s %-22s %s" % ("epsilon", "mean error", "95% of answers fall in", "what it means"))
    for eps, note in ((0.1, "strong privacy, noisy"),
                      (0.5, ""),
                      (1.0, "the usual starting point"),
                      (2.0, ""),
                      (10.0, "almost no protection")):
        t, lo, hi, err, _ = run_one(rows, eps)
        print("  %-9.1f %-11.1f %-22s %s" % (eps, err, "%.0f to %.0f" % (lo, hi), note))
    print("""
  The noise does not depend on how many people are in the file. It depends on
  how much one person could change the answer, which for a count is one. That
  is why a count over 1,174 people tolerates epsilon = 1 comfortably and a
  count over 12 people does not.""")


def report_small(rows):
    print("\nTHE SAME MECHANISM ON CELLS OF DIFFERENT SIZE")
    cells = {}
    for r in rows:
        y = int(r["BIRTHDATE"][:4])
        band = "%d-%d" % (y // 10 * 10, y // 10 * 10 + 9)
        key = (r["ZIP"], band)
        cells.setdefault(key, [0, 0])
        cells[key][0] += 1
        if r["_sensitive"] == TARGET:
            cells[key][1] += 1

    with_signal = [kv for kv in cells.items() if kv[1][1] >= 2]
    smallest = sorted(with_signal, key=lambda kv: kv[1][0])[0]
    largest = sorted(cells.items(), key=lambda kv: -kv[1][0])[0]
    whole = (("whole cohort",), [len(rows), sum(1 for r in rows if r["_sensitive"] == TARGET)])

    rng = random.Random(489)
    print("  %-24s %8s %9s  %s" % ("cell", "people", "with T2D", "ten noisy answers at epsilon = 1"))
    for key, (n, k) in (whole, largest, smallest):
        draws = [noisy_count(k, 1.0, rng) for _ in range(10)]
        print("  %-24s %8d %9d  %s" % (" / ".join(key), n, k,
                                       " ".join("%d" % round(d) for d in draws)))
    print("""
  Same mechanism, same epsilon, same noise, three different answers about how
  usable the result is. On the whole cohort the noise is a rounding error. On a
  cell of eleven people it is larger than the quantity being measured: a true
  count of 2 comes back as anything from -3 to 5, and a negative count of
  people is something this mechanism will hand you with a straight face.

  This is the honest objection to differential privacy in health research.
  Clinical questions are usually about small subgroups: one age band, one
  district, one rare condition. Exactly where the noise wins, and exactly where
  the privacy risk was highest in the first place.""")


def report_budget(rows):
    print("\nASKING MORE THAN ONCE")
    print("""  Epsilon composes. Two queries at epsilon = 0.5 give the attacker the same
  leverage as one at epsilon = 1.0. Ten give epsilon = 5. A researcher who
  explores a dataset interactively, as researchers do, spends the budget in an
  afternoon and the remaining answers are worthless.""")
    print("\n  %-28s %10s %14s" % ("usage", "total eps", "mean error"))
    for label, n, per in (("one query", 1, 1.0),
                          ("a table of 10 cells", 10, 0.1),
                          ("a table of 10 cells", 10, 1.0),
                          ("20 exploratory queries", 20, 1.0)):
        t, lo, hi, err, _ = run_one(rows, per)
        print("  %-28s %10.1f %14.1f   (%d queries at eps = %.1f each)"
              % (label, n * per, err, n, per))
    print("""
  The budget is the hard part, and it is a governance problem before it is a
  technical one. Somebody has to decide what the total epsilon for a dataset
  is, who gets to spend it, and what happens when it runs out. Almost no health
  data holder has that process, which is a large part of why almost no health
  dataset is released this way.

  Where it is used: the US Census Bureau applied it to the 2020 census, and
  several large technology companies use it for telemetry. Both are settings
  with one data holder, a fixed query set and enormous counts.""")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--epsilon", type=float)
    ap.add_argument("--small", action="store_true")
    ap.add_argument("--budget", action="store_true")
    args = ap.parse_args()

    rows = attach_sensitive(load_patients())

    if args.epsilon:
        t, lo, hi, err, draws = run_one(rows, args.epsilon)
        print("\ntrue count %d, epsilon %.2f" % (t, args.epsilon))
        print("  %s" % describe_epsilon(args.epsilon))
        print("  mean absolute error %.2f" % err)
        print("  95%% of answers fall between %.0f and %.0f" % (lo, hi))
        print("  ten draws: %s" % " ".join("%d" % round(d) for d in draws[::1000]))
        return
    if args.small:
        report_small(rows); return
    if args.budget:
        report_budget(rows); return

    report_main(rows)
    report_small(rows)
    report_budget(rows)


if __name__ == "__main__":
    main()
