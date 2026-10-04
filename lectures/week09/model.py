#!/usr/bin/env python3
"""Train a model on patient records, four ways, and watch three of them lie.

    python3 model.py              # all of it
    python3 model.py --leakage    # the feature that encodes the answer
    python3 model.py --split      # splitting by row against splitting by patient
    python3 model.py --membership # can you tell who was in the training set?
    python3 model.py --coef       # what the model actually learned

The model is logistic regression, written out: about fifty lines of gradient
descent. Nothing here needs scikit-learn, and the point of writing it out is
that when the AUC comes back at 0.99 you can see there is no trick in the
model, which means the trick is in the data.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
import statistics as st
from collections import defaultdict

from cohort import DATA, build

SEED = 489


# ----------------------------------------------------------------------
# logistic regression, written out
# ----------------------------------------------------------------------
def sigmoid(z):
    if z < -30:
        return 1e-13
    if z > 30:
        return 1 - 1e-13
    return 1.0 / (1.0 + math.exp(-z))


def standardise(X):
    """Centre and scale each column, so one learning rate works for all of them."""
    cols = list(zip(*X))
    mean = [st.mean(c) for c in cols]
    sd = [st.pstdev(c) or 1.0 for c in cols]
    return [[(v - m) / s for v, m, s in zip(row, mean, sd)] for row in X], (mean, sd)


def apply_scale(X, scale):
    mean, sd = scale
    return [[(v - m) / s for v, m, s in zip(row, mean, sd)] for row in X]


def fit(X, y, epochs=1200, lr=0.5, l2=0.0):
    n, d = len(X), len(X[0])
    w = [0.0] * d
    b = 0.0
    for _ in range(epochs):
        gw = [0.0] * d
        gb = 0.0
        for xi, yi in zip(X, y):
            p = sigmoid(sum(wj * xj for wj, xj in zip(w, xi)) + b)
            err = p - yi
            for j in range(d):
                gw[j] += err * xi[j]
            gb += err
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def predict(X, w, b):
    return [sigmoid(sum(wj * xj for wj, xj in zip(w, xi)) + b) for xi in X]


def auc(scores, labels):
    """Area under the ROC curve, by counting concordant pairs."""
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return float("nan")
    pairs = ties = 0
    for p in pos:
        for q in neg:
            if p > q:
                pairs += 1
            elif p == q:
                ties += 1
    return (pairs + 0.5 * ties) / (len(pos) * len(neg))


def knn1(Xtr, ytr, Xte):
    """One nearest neighbour. Ten lines, and enough capacity to recognise a
    person rather than a condition, which is the whole point of this section."""
    out = []
    for q in Xte:
        best, best_y = None, 0
        for xi, yi in zip(Xtr, ytr):
            d = sum((a - b) ** 2 for a, b in zip(q, xi))
            if best is None or d < best:
                best, best_y = d, yi
        out.append(float(best_y))
    return out


def log_loss(scores, labels):
    return -st.mean(l * math.log(s) + (1 - l) * math.log(1 - s) for s, l in zip(scores, labels))


# ----------------------------------------------------------------------
# the patient-level table
# ----------------------------------------------------------------------
LABEL = "diabetes_any"      # problem list OR a drug prescribed for it

HONEST = ["age", "sbp", "dbp", "weight", "cholesterol", "hdl",
          "is_female", "hypertension_dx", "obesity_dx", "prediabetes_dx"]
LEAKY = HONEST + ["on_metformin"]


def to_matrix(rows, features):
    X, y, ids = [], [], []
    for r in rows:
        if any(r.get(f, "") == "" for f in ("age", "sbp", "dbp", "weight", "cholesterol", "hdl")):
            continue
        vals = []
        for f in features:
            if f == "is_female":
                vals.append(1.0 if r["sex"] == "F" else 0.0)
            elif f in ("hypertension_dx", "obesity_dx", "prediabetes_dx", "on_metformin"):
                vals.append(float(r[f]))
            else:
                vals.append(float(r[f]))
        X.append(vals)
        y.append(int(r[LABEL]))
        ids.append(r["patient_id"])
    return X, y, ids


def split(items, frac, seed=SEED):
    rng = random.Random(seed)
    idx = list(range(len(items)))
    rng.shuffle(idx)
    cut = int(frac * len(idx))
    return set(idx[:cut]), set(idx[cut:])


def train_test(X, y, train_idx, test_idx, **kw):
    Xtr = [X[i] for i in sorted(train_idx)]
    ytr = [y[i] for i in sorted(train_idx)]
    Xte = [X[i] for i in sorted(test_idx)]
    yte = [y[i] for i in sorted(test_idx)]
    Xtr_s, scale = standardise(Xtr)
    Xte_s = apply_scale(Xte, scale)
    w, b = fit(Xtr_s, ytr, **kw)
    return (auc(predict(Xtr_s, w, b), ytr), auc(predict(Xte_s, w, b), yte),
            w, b, scale, (Xtr_s, ytr), (Xte_s, yte))


# ----------------------------------------------------------------------
def report_leakage(rows):
    print("\nTHE TASK")
    print("  Predict which patients have type 2 diabetes, from their record.")
    print("  Label: %s, which is the problem list OR a drug prescribed for it." % LABEL)
    n_pos = sum(1 for r in rows if r[LABEL] == "1")
    print("  %d of %d patients, %.1f%% positive." % (n_pos, len(rows), 100.0 * n_pos / len(rows)))

    print("\nMODEL 1: everything in the table")
    Xl, yl, _ = to_matrix(rows, LEAKY)
    tr, te = split(Xl, 0.7)
    a_tr, a_te, w, b, _, _, _ = train_test(Xl, yl, tr, te)
    print("  features: %s" % ", ".join(LEAKY))
    print("  train AUC %.3f    test AUC %.3f" % (a_tr, a_te))
    worst = max(zip(LEAKY, w), key=lambda kv: abs(kv[1]))
    print("  largest coefficient: %s  %+.2f" % worst)

    print("\nMODEL 2: the same, without on_metformin")
    Xh, yh, _ = to_matrix(rows, HONEST)
    tr, te = split(Xh, 0.7)
    a_tr2, a_te2, w2, b2, _, _, _ = train_test(Xh, yh, tr, te)
    print("  train AUC %.3f    test AUC %.3f" % (a_tr2, a_te2))
    print("""
  Metformin is prescribed FOR type 2 diabetes. The column does not predict the
  diagnosis, it records it, and a model given both has been handed the answer.

  An AUC of %.2f on a clinical prediction task should be read as an accusation,
  not a result. The question to ask of any such number is: could this feature
  have been written down before the thing I am predicting happened? If not, it
  is not a predictor.

  Target leakage is quiet because the model does not complain, the code is
  correct, and the metric is excellent. It only fails in production, where the
  leaky column is not available yet, which is the one place it matters.""" % a_te)


def visit_table(rows):
    """One row per (patient, date) with the vitals recorded that day, plus two
    baseline features of the kind clinical pipelines add as a matter of course:
    the patient's first recorded weight and first recorded systolic pressure.

    This is what health data really looks like: many rows per person, and some
    columns that are a property of the person and not of the visit."""
    by_patient = {r["patient_id"]: r for r in rows}
    vals = defaultdict(dict)
    with open(os.path.join(DATA, "observations.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = r["DESCRIPTION"]
            if d not in ("Systolic Blood Pressure", "Diastolic Blood Pressure", "Body Weight"):
                continue
            try:
                vals[(r["PATIENT"], r["DATE"][:10])][d] = float(r["VALUE"])
            except ValueError:
                pass

    # baseline = the earliest recorded value for that patient
    first = {}
    for (pid, date), v in sorted(vals.items(), key=lambda kv: kv[0][1]):
        if pid not in first and "Body Weight" in v and "Systolic Blood Pressure" in v:
            first[pid] = (v["Body Weight"], v["Systolic Blood Pressure"])

    X, y, pids = [], [], []
    for (pid, date), v in vals.items():
        if len(v) < 3 or pid not in by_patient or pid not in first:
            continue
        p = by_patient[pid]
        bw, bs = first[pid]
        X.append([float(p["age"]),
                  v["Systolic Blood Pressure"], v["Diastolic Blood Pressure"], v["Body Weight"],
                  1.0 if p["sex"] == "F" else 0.0,
                  float(p["hypertension_dx"]), float(p["obesity_dx"]), float(p["prediabetes_dx"]),
                  bw, bs])
        y.append(int(p[LABEL]))
        pids.append(pid)
    return X, y, pids


VISIT_FEATURES = ["age", "sbp", "dbp", "weight", "is_female",
                  "hypertension_dx", "obesity_dx", "prediabetes_dx",
                  "baseline_weight", "baseline_sbp"]


def report_split(rows):
    X, y, pids = visit_table(rows)
    total_rows, total_pts = len(X), len(set(pids))
    # a sample of PATIENTS, keeping every visit they made, so that one nearest
    # neighbour runs in seconds rather than minutes
    rng = random.Random(SEED)
    sample_pts = set(rng.sample(sorted(set(pids)), 350))
    keep = [i for i, q in enumerate(pids) if q in sample_pts]
    X = [X[i] for i in keep]; y = [y[i] for i in keep]; pids = [pids[i] for i in keep]

    print("\nTHE SAME DATA, ONE ROW PER VISIT")
    print("  %d rows for %d patients in the full table, %.1f visits each"
          % (total_rows, total_pts, total_rows / float(total_pts)))
    print("  working below with %d patients and all %d of their visits"
          % (len(sample_pts), len(X)))
    print("  The label is a property of the PATIENT: every visit by one person")
    print("  carries the same answer.")

    Xs, _ = standardise(X)

    def run(train_idx, test_idx, label):
        Xtr = [Xs[i] for i in sorted(train_idx)]; ytr = [y[i] for i in sorted(train_idx)]
        Xte = [Xs[i] for i in sorted(test_idx)]; yte = [y[i] for i in sorted(test_idx)]
        w, b = fit(Xtr, ytr, epochs=200, lr=0.5)
        lr_auc = auc(predict(Xte, w, b), yte)
        nn_auc = auc(knn1(Xtr, ytr, Xte), yte)
        shared = len({pids[i] for i in train_idx} & {pids[i] for i in test_idx})
        print("  %-22s %12.3f %14.3f %12d" % (label, lr_auc, nn_auc, shared))

    print("\n  %-22s %12s %14s %12s"
          % ("split", "logistic AUC", "1-NN test AUC", "shared patients"))
    tr, te = split(X, 0.7)
    run(tr, te, "randomly, by row")

    pts = sorted(set(pids))
    rng2 = random.Random(SEED)
    rng2.shuffle(pts)
    train_pts = set(pts[:int(0.7 * len(pts))])
    tr2 = {i for i, p in enumerate(pids) if p in train_pts}
    te2 = {i for i, p in enumerate(pids) if p not in train_pts}
    run(tr2, te2, "by patient")

    print("""
  Read the 1-NN column first. Split by row and the score is high; split by
  patient and it falls to a coin toss. Nothing about the disease changed
  between those two lines. What changed is whether the person in the test row
  also sat in the training set, and 324 of the 350 did.

  Two of the ten columns, baseline_weight and baseline_sbp, are properties of
  the patient and not of the visit. They are the first values recorded for that
  person and they repeat on every one of their rows. Nobody added them to cheat:
  a baseline value is a standard clinical covariate. But together they are close
  to a serial number, so the nearest neighbour of a test visit is usually the
  same person's visit from another year, carrying the answer with it. What the
  model has learned to recognise is the person.

  Logistic regression moves less, from 0.619 to 0.559, because it has ten
  parameters and cannot memorise anybody. The size of the inflation is a property
  of the model's capacity, and every model you would actually deploy has more
  capacity than this one.

  Deployment is always on a patient the model has never seen, so only the second
  row estimates anything you care about. The fix is one line. It also needs
  Week 7's question answered first: who is one person? Split on an unreliable
  patient identifier and you have not split at all.""")


def expand(X):
    """Every feature, every square, every pairwise product. No new information
    about the patient, and a great deal more capacity to memorise them with."""
    out = []
    for row in X:
        e = list(row)
        for i in range(len(row)):
            for j in range(i, len(row)):
                e.append(row[i] * row[j])
        out.append(e)
    return out


def report_membership(rows):
    print("\nMEMBERSHIP INFERENCE")
    print("""  Week 8 left this open: a model trained on 1,174 patients has seen all of
  them. Can somebody who holds the model work out whether a particular person
  was in the training set?""")

    X, y, ids = to_matrix(rows, HONEST)
    rng = random.Random(SEED)
    idx = list(range(len(X)))
    rng.shuffle(idx)
    members = set(idx[:300])
    outsiders = set(idx[300:600])

    def attack(features, label, epochs, lr):
        a_tr, a_te, w, b, scale, _, _ = train_test(features, y, members, outsiders,
                                                   epochs=epochs, lr=lr, l2=0.0)
        scores = predict(apply_scale(features, scale), w, b)
        def loss(i):
            return -(y[i] * math.log(scores[i]) + (1 - y[i]) * math.log(1 - scores[i]))
        lin = [loss(i) for i in sorted(members)]
        lout = [loss(i) for i in sorted(outsiders)]
        a = auc([-l for l in lin] + [-l for l in lout],
                [1] * len(lin) + [0] * len(lout))
        print("  %-28s %9d %10.3f %11.3f %12.4f %12.4f %11.3f"
              % (label, len(features[0]), a_tr, a_te, st.mean(lin), st.mean(lout), a))
        return a

    print("""
  Both models below are trained on the same 300 patients, with no
  regularisation, and attacked by the same single line of code: call a record a
  member if the model's loss on it is low.""")
    print("\n  %-28s %9s %10s %11s %12s %12s %11s"
          % ("model", "features", "train AUC", "held-out", "loss in", "loss out", "ATTACK AUC"))
    small = attack(X, "logistic, 10 features", 1500, 0.5)
    big = attack(expand(X), "the same, plus products", 6000, 0.3)
    print("\n  0.500 would mean the model leaks nothing about who was in it.")

    print("""
  The attack works because a model fits its training data better than it fits
  anything else, and that gap is a signal about who was inside.

  The second model was given no new information about any patient. Squares and
  products of columns it already had, and that was enough to raise the leak.
  Capacity is the variable: a bigger model, a smaller training set, or a patient
  out in the tail of the distribution all push the same way. Published attacks
  on large models reach far higher, and attacks on generative models recover
  training examples word for word.

  Which is why Week 8's slide stands: treat a model trained on patient data as
  a release of that data, and ask of it everything you would ask of a
  published table.""")


def report_coef(rows):
    X, y, _ = to_matrix(rows, HONEST)
    tr, te = split(X, 0.7)
    _, _, w, b, _, _, _ = train_test(X, y, tr, te)
    print("\nWHAT THE MODEL LEARNED   (standardised coefficients, honest features)")
    for name, wj in sorted(zip(HONEST, w), key=lambda kv: -abs(kv[1])):
        bar = "#" * int(abs(wj) * 12)
        print("  %-18s %+7.3f  %s" % (name, wj, bar))
    print("""
  Read the ranking, not the values. A coefficient here is an association inside
  this cohort, adjusted for the other nine columns and nothing else. It is not
  an effect, it is not causal, and a patient cannot change their outcome by
  changing one of these numbers.

  Then look at the signs. HDL comes out positive, systolic pressure and weight
  come out negative. Every one of those contradicts what the clinical
  literature says about type 2 diabetes. Two explanations are available: the
  model found something real, or the data generator never encoded those
  relationships. Here it is the second, and you can only tell by knowing where
  the file came from. On real data you would be arguing about it for a week.

  Session A was an entire morning on why that distinction is hard. A model
  makes it easier to forget, because the coefficients line up so neatly.""")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--leakage", action="store_true")
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--membership", action="store_true")
    ap.add_argument("--coef", action="store_true")
    args = ap.parse_args()

    rows = build()
    any_flag = args.leakage or args.split or args.membership or args.coef
    if args.leakage or not any_flag:
        report_leakage(rows)
    if args.split or not any_flag:
        report_split(rows)
    if args.membership or not any_flag:
        report_membership(rows)
    if args.coef or not any_flag:
        report_coef(rows)


if __name__ == "__main__":
    main()
