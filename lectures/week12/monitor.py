#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HY-489 Week 12. Post-market performance monitoring, on the Week 9 model.

Article 72 of the AI Act requires a post-market monitoring system, and Article
61 of the MDR requires post-market clinical follow-up. Neither says which
metric, at what frequency, against what threshold, or who is told. This script
builds a monitoring plan out of measurement and then breaks it.
"""
import os, sys, math, random, csv
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
W9 = os.path.normpath(os.path.join(HERE, "..", "week09"))
SEED = 489


def load_week09():
    """Import the Week 9 model and cohort without copying either."""
    sys.path.insert(0, W9)
    spec = importlib.util.spec_from_file_location("w9model", os.path.join(W9, "model.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    spec2 = importlib.util.spec_from_file_location("w9cohort", os.path.join(W9, "cohort.py"))
    c = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(c)
    return m, c


M, C = load_week09()
FEATURES = ["age", "sbp", "dbp", "weight", "cholesterol", "hdl",
            "is_female", "hypertension_dx", "obesity_dx", "prediabetes_dx"]


def deciles(scores, labels, n=5):
    """Observed against predicted, in n groups of equal size. Calibration."""
    pairs = sorted(zip(scores, labels))
    out = []
    step = len(pairs) // n
    for i in range(n):
        chunk = pairs[i * step: (i + 1) * step if i < n - 1 else len(pairs)]
        if not chunk:
            continue
        pred = sum(p for p, _ in chunk) / len(chunk)
        obs = sum(y for _, y in chunk) / float(len(chunk))
        out.append((len(chunk), pred, obs))
    return out


def cal_error(dec):
    """Mean absolute difference between predicted and observed, weighted."""
    tot = sum(n for n, _, _ in dec)
    return sum(n * abs(p - o) for n, p, o in dec) / tot if tot else 0.0


def windows(rows, by_age=False):
    """Split the cohort into a development set and three later cohorts.

    There is no deployment date in a synthetic file. By default the split is
    random, which stands in for calendar time in a population that is not
    changing. With by_age=True the split is ordered by age instead, which stands
    in for a monitoring window that somebody has defined using a predictor."""
    rows = list(rows)
    if by_age:
        rows.sort(key=lambda r: float(r["age"]))
    else:
        random.Random(SEED).shuffle(rows)
    n = len(rows)
    return [("development", rows[: n // 2]),
            ("window 1", rows[n // 2: n * 5 // 8]),
            ("window 2", rows[n * 5 // 8: n * 3 // 4]),
            ("window 3", rows[n * 3 // 4:])]


def fit_dev(dev):
    X, y, _ = M.to_matrix(dev, FEATURES)
    Xs, scale = M.standardise(X)
    w, b = M.fit(Xs, y, epochs=1200, lr=0.5, l2=0.01)
    return w, b, scale


def score(rows, w, b, scale):
    X, y, _ = M.to_matrix(rows, FEATURES)
    s = M.predict(M.apply_scale(X, scale), w, b)
    return s, y


def report_baseline(rows):
    print("\nTHE MONITORING PLAN NOBODY WRITES")
    print("""  Article 72 of the AI Act requires a post-market monitoring system, and
  Article 61 of the MDR requires post-market clinical follow-up. Neither names
  a metric, a frequency, a threshold or a person. This section builds one out
  of measurement, and the next two break it.

  The model is Week 9's honest logistic regression: ten features, no leakage,
  l2 = 0.01. It is fitted once, on the development half of the cohort, and then
  never refitted, which is what a deployed model is.""")
    wins = windows(rows)
    w, b, scale = fit_dev(wins[0][1])
    print("\n  %-14s %7s %9s %9s %11s %11s"
          % ("window", "n", "prev", "AUC", "mean pred", "cal error"))
    for name, chunk in wins:
        s, y = score(chunk, w, b, scale)
        prev = sum(y) / float(len(y))
        a = M.auc(s, y)
        mp = sum(s) / len(s)
        ce = cal_error(deciles(s, y))
        print("  %-14s %7d %8.1f%% %9.3f %11.3f %11.3f"
              % (name, len(chunk), 100 * prev, a, mp, ce))
    print("""
  This is the baseline, and it is what stability looks like. The windows are a
  random partition of one population, so nothing has drifted and the numbers
  wander only by sampling noise. Note how much they wander anyway: on 146
  patients, AUC moves by several hundredths between windows for no reason at
  all, and a monitoring threshold tighter than that noise fires every month.

  Sample size is therefore the first thing a monitoring plan has to settle, and
  almost no published plan states it.""")
    print("\n  THE SAME MODEL, WITH WINDOWS DEFINED BY AGE")
    wins2 = windows(rows, by_age=True)
    w2, b2, sc2 = fit_dev(wins2[0][1])
    print("  %-14s %7s %9s %9s %11s %11s"
          % ("window", "n", "prev", "AUC", "mean pred", "cal error"))
    for name, chunk in wins2:
        s2, y2 = score(chunk, w2, b2, sc2)
        print("  %-14s %7d %8.1f%% %9.3f %11.3f %11.3f"
              % (name, len(chunk), 100 * sum(y2) / float(len(y2)), M.auc(s2, y2),
                 sum(s2) / len(s2), cal_error(deciles(s2, y2))))
    print("""
  Now the AUC collapses and the calibration error triples, and no drift has
  occurred: the same 1,174 patients, the same model, a different partition. Age
  is the strongest feature, so ordering the windows by age removes most of the
  variation the model uses inside each one, and discrimination has nothing left
  to discriminate on.

  Any monitoring window defined by a variable the model uses will do this. A
  plan that reports performance by ward, by clinic or by age band is doing it on
  purpose, and the resulting numbers are not comparable with the development
  figures or with each other.""")


def shift_sbp(rows, mmhg):
    """A new automated cuff reads systolic pressure higher than the old one.

    No model change, no retraining, no software release. A procurement
    decision in a different department."""
    out = []
    for r in rows:
        r2 = dict(r)
        try:
            r2["sbp"] = "%.1f" % (float(r2["sbp"]) + mmhg)
        except (ValueError, TypeError):
            pass
        out.append(r2)
    return out


def shift_mix(rows, extra, seed=SEED):
    """The case mix changes: a new referral pathway sends more positives."""
    rng = random.Random(seed)
    pos = [r for r in rows if int(r[M.LABEL])]
    out = list(rows)
    for _ in range(extra):
        out.append(dict(rng.choice(pos)))
    rng.shuffle(out)
    return out


def report_drift(rows):
    print("\nTWO REALISTIC FAILURES, AND WHAT THE MONITORING SEES")
    print("""  Neither of these is a change to the model. One is a procurement decision in
  a different department, and one is a change to who walks through the door.
  Nobody tells the model's owner about either.""")
    wins = windows(rows)
    w, b, scale = fit_dev(wins[0][1])
    later = wins[1][1] + wins[2][1] + wins[3][1]
    s0, y0 = score(later, w, b, scale)
    a0 = M.auc(s0, y0); c0 = cal_error(deciles(s0, y0)); m0 = sum(s0) / len(s0)

    print("\n  A NEW BLOOD PRESSURE CUFF THAT READS HIGH")
    print("  %-26s %9s %9s %11s %11s %11s"
          % ("systolic shift", "AUC", "d AUC", "mean pred", "cal error", "d cal err"))
    print("  %-26s %9.3f %9s %11.3f %11.3f %11s"
          % ("none", a0, "-", m0, c0, "-"))
    for mm in (5, 10, 20):
        d = shift_sbp(later, mm)
        sx, yx = score(d, w, b, scale)
        ax = M.auc(sx, yx); cx = cal_error(deciles(sx, yx)); mx = sum(sx) / len(sx)
        print("  %-26s %9.3f %+9.3f %11.3f %11.3f %+11.3f"
              % ("+%d mmHg on every reading" % mm, ax, ax - a0, mx, cx, cx - c0))

    print("\n  A CHANGE IN WHO IS REFERRED")
    print("  %-26s %9s %9s %11s %11s %11s"
          % ("extra positive cases", "AUC", "d AUC", "prevalence", "cal error", "d cal err"))
    print("  %-26s %9.3f %9s %11.3f %11.3f %11s"
          % ("none", a0, "-", sum(y0) / float(len(y0)), c0, "-"))
    for extra in (50, 100, 200, 400):
        d = shift_mix(later, extra)
        sx, yx = score(d, w, b, scale)
        ax = M.auc(sx, yx); cx = cal_error(deciles(sx, yx))
        print("  %-26s %9.3f %+9.3f %11.3f %11.3f %+11.3f"
              % ("+%d" % extra, ax, ax - a0, sum(yx) / float(len(yx)), cx, cx - c0))
    print("""
  Look along the AUC column in both tables. It does not move. Not by the cuff,
  not by the case mix, not at any size of either. A monitoring plan that watches
  AUC would have reported this model as healthy throughout.

  The two failures then show up in different places. The cuff shifts every
  reading by the same amount, so the ranking is untouched and what moves is the
  mean predicted risk: 0.315 to 0.307 at +10 mmHg, a 3% relative fall in the
  number of patients the model sends over any fixed threshold, caused by a
  purchasing decision. Calibration error happens to fall here, because this
  model was over-predicting and the shift pushed it the right way. That is luck,
  and it is worth saying out loud: a metric that improved for the wrong reason
  is not evidence of anything.

  The case mix is the clean one. Every individual prediction is exactly what it
  was and the prevalence underneath them rises, so calibration error goes from
  0.043 to 0.258 while AUC sits still. Six times worse on the metric nobody
  monitors, invisible on the metric everybody reports.""")


def report_inputs(rows):
    print("\nWATCHING THE INPUTS INSTEAD OF THE OUTPUT")
    print("""  The outcome is not available for months, and sometimes never. A readmission
  is known in thirty days, a diagnosis in years, and a counterfactual never. So
  the only thing a monitoring system can watch in near real time is the inputs
  and the output distribution.

  Below: the same +10 mmHg cuff from the previous section, seen from the input
  side on the day it is installed, months before any outcome is known.""")
    wins = windows(rows)
    dev = wins[0][1]
    later = wins[1][1] + wins[2][1] + wins[3][1]
    drifted = shift_sbp(later, 10)
    print("\n  %-18s %12s %12s %12s %10s"
          % ("feature", "dev mean", "after", "shift", "shift/sd"))
    flagged = 0
    for f in FEATURES:
        A = [float(r[f]) for r in dev if r.get(f) not in (None, "")]
        B = [float(r[f]) for r in drifted if r.get(f) not in (None, "")]
        if not A or not B:
            continue
        ma = sum(A) / len(A); mb = sum(B) / len(B)
        va = sum((x - ma) ** 2 for x in A) / max(1, len(A) - 1)
        sd = math.sqrt(va) if va > 0 else 1.0
        z = (mb - ma) / sd
        mark = "  <--" if abs(z) >= 0.5 else ""
        if abs(z) >= 0.5:
            flagged += 1
        print("  %-18s %12.2f %12.2f %+12.2f %10.2f%s" % (f, ma, mb, mb - ma, z, mark))
    w, b, scale = fit_dev(dev)
    sd_, _ = score(dev, w, b, scale)
    sl_, _ = score(drifted, w, b, scale)
    md = sum(sd_) / len(sd_); ml = sum(sl_) / len(sl_)
    print("\n  %-18s %12.3f %12.3f %+12.3f" % ("model output", md, ml, ml - md))
    print("")
    for thr in (0.75, 0.50, 0.40, 0.25, 0.10):
        n = 0
        for f in FEATURES:
            A = [float(r[f]) for r in dev if r.get(f) not in (None, "")]
            B = [float(r[f]) for r in drifted if r.get(f) not in (None, "")]
            if not A or not B:
                continue
            ma = sum(A) / len(A); mb = sum(B) / len(B)
            va = sum((x - ma) ** 2 for x in A) / max(1, len(A) - 1)
            sdv = math.sqrt(va) if va > 0 else 1.0
            if abs((mb - ma) / sdv) >= thr:
                n += 1
        print("  alarm threshold %.2f sd  ->  %d of %d features flagged" % (thr, n, len(FEATURES)))
    print("""
  Read that sweep before congratulating the input monitor. The cuff moved
  systolic pressure by 0.49 standard deviations, and the rule of thumb everybody
  quotes is half a standard deviation. It missed, by a hundredth.

  Drop the threshold to 0.40 and it fires. Keep dropping it and nothing else
  appears, because these windows are a random partition of one stable
  population and the other nine features really did not move.

  That is the part a real deployment does not give you. Out there the inputs
  wander on their own: a seasonal case mix, a ward reorganisation, a new intake
  form. The false alarms come from that wandering, and you cannot choose a
  threshold without first measuring it. This is Week 10's alert arithmetic in a
  different costume: the detector is not the hard part, the threshold is.

  What the input monitor does buy, at any threshold, is time. It sees this on
  the day the cuff is installed. Performance monitoring on the same change needs
  outcomes that do not exist for a year, and when they arrive it reports a
  change in AUC of less than a thousandth.

  So the plan is: watch the inputs weekly, watch the output distribution weekly,
  watch performance when outcomes arrive, and say in advance which of the three
  fires an alarm, at what threshold, and who receives it.""")


def report_plan():
    print("\nWHAT A MONITORING PLAN HAS TO SAY")
    rows = [
        ("the metric", "AUC, calibration error, and the input and output distributions"),
        ("the frequency", "inputs weekly, output weekly, performance when outcomes arrive"),
        ("the threshold", "a number, chosen in advance, that triggers something"),
        ("the trigger", "what happens: recalibrate, retrain, withdraw, or tell somebody"),
        ("the person", "a name, with the authority to switch it off"),
        ("the subgroups", "every one you named in the documentation, monitored separately"),
        ("the record", "Art. 72: the monitoring system itself is part of the technical file"),
        ("serious incidents", "Art. 73: reportable to the market surveillance authority"),
    ]
    print("  %-22s %s" % ("element", "what it must contain"))
    for r in rows:
        print("  %-22s %s" % r)
    print("""
  Seven of those eight are a decision somebody has to make and write down, and
  only the first is technical. That is the shape of this whole week: the model
  is the easy part, the documentation is the work, and the hard part is naming
  the person who can switch it off and giving them the authority to do it.""")


def main():
    rows = C.build()
    args = set(sys.argv[1:])
    if not args or "--baseline" in args:
        report_baseline(rows)
    if not args or "--drift" in args:
        report_drift(rows)
    if not args or "--inputs" in args:
        report_inputs(rows)
    if not args or "--plan" in args:
        report_plan()


if __name__ == "__main__":
    main()
