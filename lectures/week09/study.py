#!/usr/bin/env python3
"""Run an observational study on the cohort, and get the wrong answer.

    python3 study.py               # the whole thing
    python3 study.py --naive       # just the headline
    python3 study.py --adjust      # stratification, step by step
    python3 study.py --negative    # the negative control outcomes
    python3 study.py --immortal    # immortal time, measured in person-years

The question: do patients taking an antihypertensive have lower blood pressure
than patients who are not?

It is a reasonable question, the data has everything needed to answer it, and
the answer you get is that the drug raises blood pressure by 3 mmHg. Working
out why is the whole of Session A.

Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import statistics as st

from cohort import build, num

OUTCOME = "sbp"
TREATMENT = "on_antihypertensive"


def mean_diff(rows, outcome=OUTCOME, treat=TREATMENT):
    t = num(rows, outcome, lambda r: r[treat] == "1")
    u = num(rows, outcome, lambda r: r[treat] == "0")
    if len(t) < 2 or len(u) < 2:
        return None
    diff = st.mean(t) - st.mean(u)
    # standard error of a difference in means
    se = math.sqrt(st.variance(t) / len(t) + st.variance(u) / len(u))
    return len(t), st.mean(t), len(u), st.mean(u), diff, 1.96 * se


def line(label, res, width=34):
    if res is None:
        print("  %-*s  too few patients" % (width, label)); return
    nt, mt, nu, mu, d, ci = res
    print("  %-*s %5d %8.1f %6d %8.1f   %+6.1f  (%+.1f to %+.1f)"
          % (width, label, nt, mt, nu, mu, d, d - ci, d + ci))


def header(width=34):
    print("  %-*s %5s %8s %6s %8s   %6s  %s"
          % (width, "", "n_tx", "mean", "n_un", "mean", "diff", "95% CI"))


def report_naive(rows):
    print("\nTHE QUESTION")
    print("  Do patients on an antihypertensive have lower systolic blood pressure?")
    print("\nTHE NAIVE ANSWER")
    header()
    line("everybody", mean_diff(rows))
    print("""
  Treated patients have blood pressure about 3 mmHg HIGHER than untreated ones,
  and the confidence interval excludes zero. Written up without further thought,
  this is "antihypertensive therapy is associated with raised blood pressure".

  Nobody believes that. The useful question is what, exactly, is wrong with it,
  because the same shape of error is publishable when the drug is new and the
  direction is not obviously absurd.""")


def report_adjust(rows):
    print("\nWHO GETS TREATED?")
    t_age = num(rows, "age", lambda r: r[TREATMENT] == "1")
    u_age = num(rows, "age", lambda r: r[TREATMENT] == "0")
    print("  mean age, treated      %.1f" % st.mean(t_age))
    print("  mean age, untreated    %.1f" % st.mean(u_age))
    print("  difference             %.1f years" % (st.mean(t_age) - st.mean(u_age)))
    print("""
  There it is. The treated are eleven years older, and systolic pressure rises
  with age in everybody, treated or not. The drug is not raising blood pressure;
  age is, and age is also what gets you prescribed the drug.

  This is confounding by indication: the reason for treatment is also a cause of
  the outcome. It is the single most common error in health data research, and
  no amount of data fixes it, because the data is not the problem.""")

    print("\nADJUSTING, BADLY: stratify on the recorded diagnosis")
    header()
    for lab, keep in (("no hypertension recorded", lambda r: r["hypertension_dx"] == "0"),
                      ("hypertension recorded", lambda r: r["hypertension_dx"] == "1")):
        line(lab, mean_diff([r for r in rows if keep(r)]))
    print("""
  Barely moves. Two reasons, and both matter. The diagnosis label does not
  capture severity, which is what actually drives prescribing. And 205 of the
  361 treated patients have no hypertension row at all, so the strata are not
  what they claim to be.""")

    print("\nADJUSTING, PROPERLY: stratify on age")
    header()
    bands = [(0, 34), (35, 49), (50, 64), (65, 79), (80, 200)]
    for lo, hi in bands:
        sub = [r for r in rows if lo <= r["age"] <= hi]
        line("age %d-%s" % (lo, hi if hi < 200 else "+"), mean_diff(sub))
    print("""
  Inside an age band the difference is around zero and the intervals span it.
  The 3 mmHg was age, start to finish.

  Be careful what you conclude from how clean that was. This is a synthetic
  cohort with one confounder; in real data, adjustment usually shrinks a bias
  without removing it, and what is left is unmeasured. The next section is how
  you find out whether anything is left.""")


def report_negative(rows):
    print("\nNEGATIVE CONTROL OUTCOMES")
    print("  An antihypertensive cannot change these. If the analysis says it does,")
    print("  the analysis is measuring the difference between the two groups of")
    print("  people, not the effect of the drug.")
    print()
    header(width=28)
    for col, label in (("weight", "body weight (kg)"),
                       ("cholesterol", "total cholesterol"),
                       ("hdl", "HDL cholesterol")):
        line(label, mean_diff(rows, outcome=col), width=28)
    print("""
  All three straddle zero, which is the result you want: it says the comparison
  is not wildly contaminated. Run the same controls on the age-stratified
  analysis and they stay there.

  A negative control that comes back positive is the most useful finding in
  observational research. It tells you the design is broken before a reviewer
  does, and it costs one extra query.""")

    print("\n  The same idea, the other way round: a POSITIVE control")
    header(width=28)
    line("metformin -> diabetes dx", mean_diff(
        [r for r in rows if r["diabetes_dx"] in ("0", "1")],
        outcome="age", treat="on_metformin"), width=28)
    print("""  (here, that metformin users are older, which they are, and which the design
  should be able to recover. A design that cannot find a known association is
  not ready to look for an unknown one.)""")


def report_immortal(rows):
    print("\nIMMORTAL TIME")
    print("""  Now a different study. Define the exposed group as "ever prescribed an
  antihypertensive", start the clock at each patient's first encounter, and
  compare mortality.""")
    treated = [r for r in rows if r[TREATMENT] == "1" and r["first_antihypertensive"] and r["first_encounter"]]
    untreated = [r for r in rows if r[TREATMENT] == "0"]
    d_t = sum(1 for r in treated if r["died"] == "1")
    d_u = sum(1 for r in untreated if r["died"] == "1")
    print("\n  deaths, treated      %3d of %4d   %.1f%%" % (d_t, len(treated), 100.0 * d_t / len(treated)))
    print("  deaths, untreated    %3d of %4d   %.1f%%" % (d_u, len(untreated), 100.0 * d_u / len(untreated)))

    gaps = []
    for r in treated:
        a = dt.date.fromisoformat(r["first_encounter"])
        b = dt.date.fromisoformat(r["first_antihypertensive"])
        if (b - a).days >= 0:
            gaps.append((b - a).days)
    gaps.sort()
    print("\n  Days from first encounter to first prescription, in the treated arm:")
    print("    median %d    mean %.0f    maximum %d" % (gaps[len(gaps) // 2], st.mean(gaps), gaps[-1]))
    print("    total %.0f person-years" % (sum(gaps) / 365.25))
    print("""
  Every one of those %.0f person-years is time during which a patient was
  counted as treated and could not possibly have died, because dying would have
  stopped them reaching their prescription. The exposure was defined using
  information from the future.

  Assign that time to the treated arm and the drug looks protective. Assign it
  correctly, as unexposed time before the prescription, and the apparent benefit
  goes away. This is immortal time bias, it has produced dozens of retracted
  findings, and it is invisible in the output: nothing about the analysis looks
  wrong.""" % (sum(gaps) / 365.25))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--naive", action="store_true")
    ap.add_argument("--adjust", action="store_true")
    ap.add_argument("--negative", action="store_true")
    ap.add_argument("--immortal", action="store_true")
    args = ap.parse_args()

    rows = build()
    any_flag = args.naive or args.adjust or args.negative or args.immortal
    if args.naive or not any_flag:
        report_naive(rows)
    if args.adjust or not any_flag:
        report_adjust(rows)
    if args.negative or not any_flag:
        report_negative(rows)
    if args.immortal or not any_flag:
        report_immortal(rows)


if __name__ == "__main__":
    main()
