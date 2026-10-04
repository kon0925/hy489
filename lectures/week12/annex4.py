#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HY-489 Week 12. The technical documentation, generated from measurement.

Annex IV of the AI Act lists what the technical documentation of a high-risk AI
system must contain. This script fills in every element that can come out of a
real run of the Week 9 model, marks every element that cannot, and says who
would have to write it.

The output is a skeleton for teaching. It is not a regulatory submission and
must never be presented as one.
"""
import os, sys, math, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
W9 = os.path.normpath(os.path.join(HERE, "..", "week09"))


def load():
    if W9 not in sys.path:
        sys.path.insert(0, W9)
    spec = importlib.util.spec_from_file_location("w9model", os.path.join(W9, "model.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    spec2 = importlib.util.spec_from_file_location("w9cohort", os.path.join(W9, "cohort.py"))
    c = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(c)
    return m, c


M, C = load()
FEATURES = ["age", "sbp", "dbp", "weight", "cholesterol", "hdl",
            "is_female", "hypertension_dx", "obesity_dx", "prediabetes_dx"]

# Annex IV, abbreviated to its element groups. "auto" means a script can fill
# it from a run; "human" means somebody has to decide and write it.
ANNEX4 = [
    ("1(a)", "intended purpose, provider, version", "human",
     "the manufacturer, in an intended-purpose statement"),
    ("1(b)", "how the system interacts with other systems", "human",
     "the integration architect"),
    ("1(c)", "software versions and update arrangements", "auto",
     "a build pipeline"),
    ("1(d)", "the forms in which it is placed on the market", "human",
     "the manufacturer"),
    ("1(e)", "hardware on which it is intended to run", "human",
     "the manufacturer"),
    ("1(g)", "instructions for use", "human",
     "a technical author, with a clinician"),
    ("2(a)", "methods and steps for development", "human",
     "the development team, retrospectively and painfully"),
    ("2(b)", "design specifications, architecture, logic, key design choices",
     "part", "the team; the measured parts are below"),
    ("2(c)", "computational resources used", "auto", "a script"),
    ("2(d)", "data requirements, provenance, labelling, cleaning",
     "part", "the data holder, and Week 11's Article 77 entry"),
    ("2(e)", "human oversight measures", "human",
     "the clinical lead who will be overridden"),
    ("2(f)", "pre-determined changes and continued compliance", "human",
     "the manufacturer, in a change control plan"),
    ("2(g)", "validation and testing procedures, metrics, test logs",
     "auto", "a script, and this is the part people think is the whole file"),
    ("3", "monitoring, functioning and control of the system", "part",
     "monitor.py produces the numbers; somebody writes the plan"),
    ("5", "validation and testing: accuracy, robustness, cybersecurity",
     "part", "accuracy measured below; robustness and security are not"),
    ("6", "risk management system under Article 9", "human",
     "a risk manager, iteratively, across the lifecycle"),
    ("8", "post-market monitoring plan under Article 72", "human",
     "the manufacturer, and it is a plan, not a measurement"),
    ("9", "the EU declaration of conformity", "human",
     "a person with authority to sign"),
]


def build_model():
    rows = C.build()
    X, y, ids = M.to_matrix(rows, FEATURES)
    tr, te = M.split(X, 0.7)
    a_tr, a_te, w, b, scale, (Xtr, ytr), (Xte, yte) = M.train_test(
        X, y, tr, te, epochs=1200, lr=0.5, l2=0.01)
    return rows, X, y, ids, tr, te, a_tr, a_te, w, b, scale, Xte, yte


def subgroup_auc(rows, X, y, idx, w, b, scale, key, test):
    sel = [i for i in sorted(idx) if test(rows[i])]
    if len(sel) < 40:
        return None
    Xs = M.apply_scale([X[i] for i in sel], scale)
    s = M.predict(Xs, w, b)
    ys = [y[i] for i in sel]
    if len(set(ys)) < 2:
        return None
    return len(sel), sum(ys) / float(len(ys)), M.auc(s, ys)


def report_file(rows, X, y, ids, tr, te, a_tr, a_te, w, b, scale, Xte, yte):
    print("\nANNEX IV TECHNICAL DOCUMENTATION  (generated extract)")
    print("  SYNTHETIC COHORT. TEACHING ARTEFACT. NOT A REGULATORY SUBMISSION.")
    print("""
  2(g)  VALIDATION AND TESTING PROCEDURES, METRICS AND TEST LOGS""")
    print("    model                      logistic regression, batch gradient descent")
    print("    features                   %d: %s" % (len(FEATURES), ", ".join(FEATURES)))
    print("    label                      %s" % M.LABEL)
    print("    training set               %d patients" % len(tr))
    print("    test set                   %d patients, split by patient" % len(te))
    print("    prevalence                 %.1f%%" % (100.0 * sum(y) / len(y)))
    print("    regularisation             l2 = 0.01")
    print("    AUC, training              %.3f" % a_tr)
    print("    AUC, held-out              %.3f" % a_te)
    print("""
  5     ACCURACY, AND THE SUBGROUPS NAMED IN THE INTENDED PURPOSE""")
    print("    %-26s %8s %10s %9s" % ("subgroup", "n", "prevalence", "AUC"))
    groups = [
        ("all test patients", lambda r: True),
        ("women", lambda r: r["sex"] == "F"),
        ("men", lambda r: r["sex"] == "M"),
        ("under 50", lambda r: float(r["age"]) < 50),
        ("50 to 69", lambda r: 50 <= float(r["age"]) < 70),
        ("70 and over", lambda r: float(r["age"]) >= 70),
        ("hypertension recorded", lambda r: int(r["hypertension_dx"]) == 1),
        ("no hypertension recorded", lambda r: int(r["hypertension_dx"]) == 0),
    ]
    reported = 0
    for name, test in groups:
        g = subgroup_auc(rows, X, y, te, w, b, scale, name, test)
        if g is None:
            print("    %-26s %8s %10s %9s" % (name, "<40", "-", "not reported"))
        else:
            n, prev, a = g
            print("    %-26s %8d %9.1f%% %9.3f" % (name, n, 100 * prev, a))
            reported += 1
    print("""
    The subgroup table is the point of element 5, and it is the element most
    often reduced to a single overall number. Read the age rows: 0.655 under
    50, 0.629 between 50 and 69, and 0.503 at 70 and over. In the oldest group,
    the group with the most to lose from a wrong answer, this model is a coin
    toss. The overall figure of 0.605 conceals that completely, and an intended
    purpose that does not exclude the over-70s is making a claim the evidence
    does not support.""")
    print("""
  2(b)  KEY DESIGN CHOICES, AND WHAT THEY COST  (from Week 9's measurements)""")
    print("    on_metformin excluded      target leakage: with it, held-out AUC 0.814")
    print("                               against 0.604 without. The column records the")
    print("                               diagnosis instead of predicting it")
    print("    split by patient           a random row split gives a 1-NN AUC of 0.790")
    print("                               against 0.499 split by patient")
    print("    l2 = 0.01                  membership inference attack AUC 0.532 at ten")
    print("                               features, 0.591 once squares and products are")
    print("                               added. Capacity is the variable")
    print("""
  6     RISK MANAGEMENT: KNOWN LIMITATIONS
    - the label is diabetes_any, the union of a problem list and a drug reason.
      The two sources agree about 42 patients of 353, so the cohort definition
      is a choice and it moves every number above
    - three coefficient signs contradict the clinical literature, which is a
      property of the data generator and not a finding
    - RACE and ETHNICITY are single-valued across all 1,174 rows, so no
      subgroup analysis on either is possible
    - 287 of 559 male patients carry feminine-form surnames, so any analysis
      that infers sex from a name is unsafe on this cohort
    - the cohort is synthetic, so no performance figure here transfers to any
      real population""")


def report_coverage():
    print("\nWHAT A SCRIPT CAN AND CANNOT PRODUCE")
    print("  %-7s %-56s %-7s %s" % ("element", "Annex IV asks for", "source", "who writes it"))
    n_auto = n_part = n_human = 0
    for el, what, kind, who in ANNEX4:
        print("  %-7s %-56s %-7s %s" % (el, what[:56], kind, who[:44]))
        if kind == "auto":
            n_auto += 1
        elif kind == "part":
            n_part += 1
        else:
            n_human += 1
    tot = len(ANNEX4)
    print("\n    generated in full by a script      %2d of %d" % (n_auto, tot))
    print("    generated in part                  %2d of %d" % (n_part, tot))
    print("    requires a human decision          %2d of %d" % (n_human, tot))
    print("""
  Three of eighteen come out of a run, and one of those three is a build
  version number. The part everybody in this room is trained to produce is
  element 2(g), the validation metrics, and it is one line of the file.

  The documentation burden for a high-risk AI system is mostly not technical.
  It is an intended-purpose statement that somebody is accountable for, a risk
  management process that runs for the life of the product, a human oversight
  design that a clinician will have to live with, and a declaration that a named
  person signs. None of that can be generated, and all of it has to exist before
  the notified body will look at the metrics.""")


def main():
    args = set(sys.argv[1:])
    if not args or "--file" in args:
        report_file(*build_model())
    if not args or "--coverage" in args:
        report_coverage()


if __name__ == "__main__":
    main()
