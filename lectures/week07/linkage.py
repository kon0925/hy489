#!/usr/bin/env python3
"""Link site_a to site_b, and measure how wrong the link is.

    python3 linkage.py                  # the whole pipeline, scored
    python3 linkage.py --blocking       # what each blocking key costs
    python3 linkage.py --deterministic  # rules, for comparison
    python3 linkage.py --sweep          # precision and recall by threshold
    python3 linkage.py --errors         # the pairs it gets wrong, named
    python3 linkage.py --oracle-m       # how much the m values actually matter
    python3 linkage.py --threshold 8    # link at a chosen threshold

The method is Fellegi and Sunter (JASA, 1969). Every field comparison
contributes a weight in bits:

    agreement     log2( m / u )
    disagreement  log2( (1-m) / (1-u) )
    missing       0

m is how often the field agrees when two records are the same person; u is how
often it agrees when they are not. The weights add, and the total is the log
odds that the pair is a match.

Stdlib only. No pandas, no scikit, no Splink. All of those are better than this
for real work; none of them show you the arithmetic.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import random
import re
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

FIELDS = ["given_name", "surname", "birth_date", "sex", "postcode", "phone", "amka"]

# How often each field agrees when the two records ARE the same person.
# Defaults, not estimates. --oracle-m shows how much the choice matters.
M_DEFAULT = {
    "given_name": 0.70,     # short forms and typing
    "surname":    0.70,     # marriage, feminine forms, transliteration
    "birth_date": 0.92,
    "sex":        0.98,
    "postcode":   0.85,     # people move
    "phone":      0.80,
    "amka":       0.95,
}

# A 'close' comparison carries this fraction of the full agreement weight.
CLOSE_FRACTION = 0.6


# ----------------------------------------------------------------------
# standardisation
# ----------------------------------------------------------------------
def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


# ----------------------------------------------------------------------
# Jaro-Winkler, written out rather than imported
# ----------------------------------------------------------------------
def jaro(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    reach = max(len(a), len(b)) // 2 - 1
    if reach < 0:
        reach = 0
    a_hit = [False] * len(a)
    b_hit = [False] * len(b)
    matches = 0
    for i, ca in enumerate(a):
        lo, hi = max(0, i - reach), min(i + reach + 1, len(b))
        for j in range(lo, hi):
            if b_hit[j] or b[j] != ca:
                continue
            a_hit[i] = b_hit[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = transpositions = 0
    for i, ca in enumerate(a):
        if not a_hit[i]:
            continue
        while not b_hit[k]:
            k += 1
        if ca != b[k]:
            transpositions += 1
        k += 1
    t = transpositions // 2
    return (matches / len(a) + matches / len(b) + (matches - t) / matches) / 3.0


def jaro_winkler(a, b, p=0.1, max_prefix=4):
    j = jaro(a, b)
    if j < 0.7:
        return j
    prefix = 0
    for ca, cb in zip(a[:max_prefix], b[:max_prefix]):
        if ca != cb:
            break
        prefix += 1
    return j + prefix * p * (1 - j)


# ----------------------------------------------------------------------
# field comparison: agree / close / disagree / missing
# ----------------------------------------------------------------------
def compare_field(field, va, vb):
    va, vb = norm(va), norm(vb)
    if not va or not vb:
        return "missing"
    if field in ("given_name", "surname"):
        if va == vb:
            return "agree"
        return "close" if jaro_winkler(va, vb) >= 0.90 else "disagree"
    if field == "birth_date":
        if va == vb:
            return "agree"
        try:
            da = dt.date.fromisoformat(va.replace(" ", "-")[:10])
            db = dt.date.fromisoformat(vb.replace(" ", "-")[:10])
        except Exception:
            return "disagree"
        # a day/month swap, or one component wrong, is near agreement
        same = sum([da.year == db.year, da.month == db.month, da.day == db.day])
        if same >= 2:
            return "close"
        if (da.day, da.month) == (db.month, db.day) and da.year == db.year:
            return "close"
        return "disagree"
    return "agree" if va == vb else "disagree"


def compare(ra, rb):
    return {f: compare_field(f, ra.get(f), rb.get(f)) for f in FIELDS}


# ----------------------------------------------------------------------
# u from random pairs, m from defaults or from the answer key
# ----------------------------------------------------------------------
def estimate_u(a_rows, b_rows, n=20000, seed=489):
    """Almost no random pair is a match, so the agreement rate among random
    pairs IS u. No labels needed, which is why this half is the easy half."""
    rng = random.Random(seed)
    agree = defaultdict(int)
    seen = defaultdict(int)
    for _ in range(n):
        ra, rb = rng.choice(a_rows), rng.choice(b_rows)
        for f, outcome in compare(ra, rb).items():
            if outcome == "missing":
                continue
            seen[f] += 1
            if outcome in ("agree", "close"):
                agree[f] += 1
    u = {}
    for f in FIELDS:
        u[f] = max(agree[f] / seen[f], 1e-5) if seen[f] else 1e-5
    return u


def oracle_m(a_rows, b_rows, truth):
    """m computed from the answer key. Only possible because this is a
    teaching dataset. Here to show how little the answer moves."""
    a_by = {r["patient_id"]: r for r in a_rows}
    b_by = {r["patient_id"]: r for r in b_rows}
    agree = defaultdict(int)
    seen = defaultdict(int)
    for aid, bid in truth:
        for f, outcome in compare(a_by[aid], b_by[bid]).items():
            if outcome == "missing":
                continue
            seen[f] += 1
            if outcome in ("agree", "close"):
                agree[f] += 1
    return {f: (max(min(agree[f] / seen[f], 0.999), 0.001) if seen[f] else 0.5)
            for f in FIELDS}


def weights(m, u):
    w = {}
    for f in FIELDS:
        w[f] = {
            "agree": math.log2(m[f] / u[f]),
            "close": CLOSE_FRACTION * math.log2(m[f] / u[f]),
            "disagree": math.log2((1 - m[f]) / (1 - u[f])),
            "missing": 0.0,
        }
    return w


def score(ra, rb, w):
    return sum(w[f][outcome] for f, outcome in compare(ra, rb).items())


# ----------------------------------------------------------------------
# blocking
# ----------------------------------------------------------------------
def key_none(r):          return ["*"]
def key_birth_year(r):    return [(r.get("birth_date") or "")[:4]]
def key_surname_init(r):  return [norm(r.get("surname"))[:3]]
def key_postcode(r):      return [(r.get("postcode") or "").strip()]
def key_sex_year(r):      return ["%s|%s" % (r.get("sex", ""), (r.get("birth_date") or "")[:4])]

BLOCKS = {
    "none":           [key_none],
    "birth_year":     [key_birth_year],
    "surname_prefix": [key_surname_init],
    "postcode":       [key_postcode],
    "sex_birth_year": [key_sex_year],
    "multi":          [key_birth_year, key_surname_init, key_postcode],
}


def candidates(a_rows, b_rows, strategy="multi"):
    """Pairs that agree on at least one blocking key."""
    out = set()
    for keyfn in BLOCKS[strategy]:
        index = defaultdict(list)
        for rb in b_rows:
            for k in keyfn(rb):
                if k.strip(":") or k == "*":
                    index[k].append(rb)
        for ra in a_rows:
            for k in keyfn(ra):
                if not (k.strip(":") or k == "*"):
                    continue
                for rb in index.get(k, ()):
                    out.add((ra["patient_id"], rb["patient_id"]))
    return out


# ----------------------------------------------------------------------
# evaluation
# ----------------------------------------------------------------------
def evaluate(linked, truth):
    truth = set(truth)
    linked = set(linked)
    tp = len(linked & truth)
    fp = len(linked - truth)
    fn = len(truth - linked)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return tp, fp, fn, precision, recall, f1


def best_one_to_one(scored, threshold):
    """Each site_a row gets at most one site_b row, and the other way round.
    Greedy on the score, which is what most production systems do."""
    linked = []
    used_a, used_b = set(), set()
    for s, aid, bid in sorted(scored, reverse=True):
        if s < threshold:
            break
        if aid in used_a or bid in used_b:
            continue
        linked.append((aid, bid))
        used_a.add(aid)
        used_b.add(bid)
    return linked


# ----------------------------------------------------------------------
def load():
    def read(name):
        with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    a = read("site_a.csv")
    b = read("site_b.csv")
    with open(os.path.join(DATA, "truth.csv"), newline="", encoding="utf-8") as fh:
        truth = [(r["a_id"], r["b_id"]) for r in csv.DictReader(fh)]
    return a, b, truth


def score_all(a_rows, b_rows, pairs, w):
    a_by = {r["patient_id"]: r for r in a_rows}
    b_by = {r["patient_id"]: r for r in b_rows}
    return [(score(a_by[aid], b_by[bid], w), aid, bid) for aid, bid in pairs]


# ----------------------------------------------------------------------
def report_blocking(a, b, truth):
    truth_set = set(truth)
    print("\nBLOCKING            what each key costs")
    print("%-18s %10s %9s  %s" % ("strategy", "pairs", "recall", "what it loses"))
    notes = {
        "none": "nothing. This is the ceiling",
        "birth_year": "pairs with a mistyped birth year",
        "surname_prefix": "Chatzidakis against Hatzidakis",
        "postcode": "everyone whose postcode is blank",
        "sex_birth_year": "the same as birth_year, and any recorded sex error",
        "multi": "almost nothing, at a tolerable cost",
    }
    for name in ["none", "birth_year", "surname_prefix", "postcode", "sex_birth_year", "multi"]:
        pairs = candidates(a, b, name)
        kept = len(pairs & truth_set)
        print("%-18s %10d %8.1f%%  %s"
              % (name, len(pairs), 100.0 * kept / len(truth_set), notes[name]))
    print("\nPair completeness is the fraction of true matches that survive")
    print("blocking. It is a ceiling on recall that no later stage can raise.")


def report_deterministic(a, b, truth):
    print("\nDETERMINISTIC RULES      no model, no threshold")
    b_by_key = defaultdict(list)
    for rb in b:
        k = (norm(rb.get("surname")), rb.get("birth_date"), rb.get("postcode", "").strip())
        if k[0] and k[1] and k[2]:
            b_by_key[k].append(rb)
    rule1 = set()
    for ra in a:
        k = (norm(ra.get("surname")), ra.get("birth_date"), ra.get("postcode", "").strip())
        if not (k[0] and k[1] and k[2]):
            continue
        for rb in b_by_key.get(k, ()):
            rule1.add((ra["patient_id"], rb["patient_id"]))

    b_by_amka = defaultdict(list)
    for rb in b:
        if (rb.get("amka") or "").strip():
            b_by_amka[rb["amka"].strip()].append(rb)
    rule2 = set()
    for ra in a:
        v = (ra.get("amka") or "").strip()
        for rb in b_by_amka.get(v, ()):
            rule2.add((ra["patient_id"], rb["patient_id"]))

    for label, linked in (("surname + birth date + postcode", rule1),
                          ("AMKA equality", rule2),
                          ("either of the two", rule1 | rule2)):
        tp, fp, fn, p, r, f1 = evaluate(linked, truth)
        print("  %-34s links %4d   P %5.1f%%  R %5.1f%%  F1 %.3f"
              % (label, len(linked), 100 * p, 100 * r, f1))
    print("\n  A rule that requires a field to be equal discards every pair where")
    print("  that field is blank, and never reports that it did so.")


def report_sweep(scored, truth):
    print("\nTHRESHOLD SWEEP        %d candidate pairs scored" % len(scored))
    print("%10s %7s %7s %7s %8s %8s %7s" % ("threshold", "links", "TP", "FP", "prec", "recall", "F1"))
    best = (0, None)
    for t in [-8, -4, 0, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 30]:
        linked = best_one_to_one(scored, t)
        tp, fp, fn, p, r, f1 = evaluate(linked, truth)
        print("%10d %7d %7d %7d %7.1f%% %7.1f%% %7.3f" % (t, len(linked), tp, fp, 100 * p, 100 * r, f1))
        if f1 > best[0]:
            best = (f1, t)
    print("\n  best F1 %.3f at threshold %d" % (best[0], best[1]))
    return best[1]


def report_errors(a, b, truth, scored, threshold):
    a_by = {r["patient_id"]: r for r in a}
    b_by = {r["patient_id"]: r for r in b}
    linked = set(best_one_to_one(scored, threshold))
    truth_set = set(truth)
    by_pair = {(aid, bid): s for s, aid, bid in scored}

    def show(aid, bid, tag):
        ra, rb = a_by[aid], b_by[bid]
        s = by_pair.get((aid, bid))
        print("  %-3s %s %-14s %-16s %-11s | %s %-14s %-16s %-11s  score %s"
              % (tag, aid, ra["given_name"][:14], ra["surname"][:16], ra["birth_date"],
                 bid, rb["given_name"][:14], rb["surname"][:16], rb["birth_date"],
                 ("%.1f" % s) if s is not None else "not a candidate"))

    fps = sorted(linked - truth_set)
    fns = sorted(truth_set - linked)
    print("\nFALSE POSITIVES at threshold %d: %d" % (threshold, len(fps)))
    for aid, bid in fps[:10]:
        show(aid, bid, "FP")
    print("\nFALSE NEGATIVES at threshold %d: %d" % (threshold, len(fns)))
    for aid, bid in fns[:12]:
        show(aid, bid, "FN")
    print("\n  Read the false negatives as a list. If they have something in")
    print("  common, that is the next thing to build.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--blocking", action="store_true")
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--oracle-m", action="store_true")
    ap.add_argument("--strategy", default="multi", choices=sorted(BLOCKS))
    ap.add_argument("--threshold", type=float, default=8.0)
    args = ap.parse_args()

    a, b, truth = load()
    print("site_a %d rows   site_b %d rows   truth %d pairs   possible pairs %d"
          % (len(a), len(b), len(truth), len(a) * len(b)))

    if args.blocking:
        report_blocking(a, b, truth)
        return
    if args.deterministic:
        report_deterministic(a, b, truth)
        return

    u = estimate_u(a, b)
    m = M_DEFAULT
    w = weights(m, u)

    if args.oracle_m:
        om = oracle_m(a, b, truth)
        print("\nm FROM THE ANSWER KEY, against the defaults")
        print("%-14s %8s %8s %8s" % ("field", "default", "oracle", "diff"))
        for f in FIELDS:
            print("%-14s %8.3f %8.3f %+8.3f" % (f, m[f], om[f], om[f] - m[f]))
        pairs = candidates(a, b, args.strategy)
        for label, mm in (("default m", m), ("oracle m", om)):
            sc = score_all(a, b, pairs, weights(mm, u))
            best = max(((evaluate(best_one_to_one(sc, t), truth)[5], t)
                        for t in range(-8, 31)), key=lambda x: x[0])
            print("  %-10s best F1 %.3f at threshold %d" % (label, best[0], best[1]))
        print("\n  The inputs move a long way and the answer barely does. Spend the")
        print("  effort on blocking and on the threshold instead.")
        return

    print("\nWEIGHTS (bits)   u estimated from 20,000 random pairs")
    print("%-14s %7s %9s %8s %10s" % ("field", "m", "u", "agree", "disagree"))
    for f in FIELDS:
        print("%-14s %7.2f %9.5f %+8.2f %+10.2f" % (f, m[f], u[f], w[f]["agree"], w[f]["disagree"]))

    pairs = candidates(a, b, args.strategy)
    scored = score_all(a, b, pairs, w)
    print("\nblocking '%s' gives %d candidate pairs out of %d possible"
          % (args.strategy, len(pairs), len(a) * len(b)))

    if args.sweep:
        report_sweep(scored, truth)
        return

    linked = best_one_to_one(scored, args.threshold)
    tp, fp, fn, p, r, f1 = evaluate(linked, truth)
    print("\nAT THRESHOLD %g" % args.threshold)
    print("  links made        %d" % len(linked))
    print("  true positives    %d" % tp)
    print("  false positives   %d" % fp)
    print("  false negatives   %d" % fn)
    print("  precision         %.1f%%" % (100 * p))
    print("  recall            %.1f%%" % (100 * r))
    print("  F1                %.3f" % f1)

    if args.errors:
        report_errors(a, b, truth, scored, args.threshold)


if __name__ == "__main__":
    main()
