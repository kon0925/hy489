"""The four numbers, and the report. Written for you.

    from src.metrics import report
    report(concept_map_rows, source_rows, vocab)

You do not write these. You write the map; this measures it, the same way for
everyone, so the numbers are comparable across the room and markable.

What is measured, and why each one is in here:

  1. COVERAGE          the share of rows and of distinct terms that got a
                       target. On its own it flatters a bad map: mapping
                       everything onto 'unspecified' scores 100%.
  2. COLLAPSE          how many distinct source terms landed on each target.
                       This is the number coverage hides. Week 5's example was
                       five source concepts collapsing onto one I50.9, and it
                       is why 'we mapped 100%' is not an answer.
  3. RESIDUAL          the share of mapped rows sitting on an 'other' or
                       'unspecified' code. High residual means the coding
                       workflow, not the patients.
  4. LOSS              rows whose source carried detail the target cannot:
                       laterality, severity, negation, organism, age of onset.

Report the first two together, always. A map with 98% coverage and a worst
collapse of 5-to-1 is a different artefact from one with 86% coverage and no
collapse at all, and only one of them can answer a clinical question.
"""

from __future__ import annotations

from collections import Counter, defaultdict

# Source detail the target classification cannot carry. Crude on purpose: it
# finds the obvious cases so you can argue about the rest.
LOSS_MARKERS = {
    "laterality": ("left", "right", "bilateral", "unilateral", " l ", " r "),
    "severity": ("mild", "moderate", "severe", "persistent", "acute on chronic"),
    "negation": ("no ", "not ", "denies", "nil "),
    "organism": ("viral", "bacterial", "fungal"),
    "onset": ("childhood", "paediatric", "pediatric", "juvenile", "adult onset"),
    "control": ("diet controlled", "well controlled", "uncontrolled", "insulin dependent"),
}


def _mapped(rows):
    return [r for r in rows if r.get("target_code")]


def coverage(rows):
    """Share of rows, and of distinct normalised terms, that got a target."""
    total = len(rows)
    mapped = _mapped(rows)
    terms = {r["source_term"] for r in rows}
    mapped_terms = {r["source_term"] for r in mapped}
    return {
        "rows_total": total,
        "rows_mapped": len(mapped),
        "rows_pct": 100.0 * len(mapped) / total if total else 0.0,
        "terms_total": len(terms),
        "terms_mapped": len(mapped_terms),
        "terms_pct": 100.0 * len(mapped_terms) / len(terms) if terms else 0.0,
    }


def collapse_table(rows):
    """For each target: the distinct source terms that landed on it, and the
    row count. Sorted worst first."""
    by_target = defaultdict(set)
    counts = Counter()
    for r in _mapped(rows):
        by_target[r["target_code"]].add(r["source_term"])
        counts[r["target_code"]] += 1
    table = [{"target_code": t,
              "distinct_sources": len(s),
              "rows": counts[t],
              "sources": sorted(s)}
             for t, s in by_target.items()]
    table.sort(key=lambda d: (-d["distinct_sources"], -d["rows"]))
    return table


def collapse_ratio(rows):
    """Distinct source terms per distinct target. 1.0 means nothing collapsed."""
    mapped = _mapped(rows)
    sources = {r["source_term"] for r in mapped}
    targets = {r["target_code"] for r in mapped}
    return len(sources) / len(targets) if targets else 0.0


def residual_fraction(rows, vocab):
    """Share of mapped rows sitting on an 'other' or 'unspecified' code."""
    mapped = _mapped(rows)
    resid = [r for r in mapped if vocab.is_residual(r["target_code"])]
    return {
        "rows_mapped": len(mapped),
        "rows_residual": len(resid),
        "pct": 100.0 * len(resid) / len(mapped) if mapped else 0.0,
        "codes": Counter(r["target_code"] for r in resid).most_common(),
    }


def loss_table(rows):
    """Mapped rows whose source term carried detail the target cannot."""
    found = defaultdict(list)
    for r in _mapped(rows):
        term = r["source_term"]
        for kind, markers in LOSS_MARKERS.items():
            if any(m in term for m in markers):
                found[kind].append(term)
    return {k: {"rows": len(v), "examples": sorted(set(v))[:4]}
            for k, v in sorted(found.items(), key=lambda kv: -len(kv[1]))}


def unmapped_reasons(rows):
    """The unmapped rows, grouped by the reason you gave."""
    unmapped = [r for r in rows if not r.get("target_code")]
    by_reason = defaultdict(list)
    for r in unmapped:
        by_reason[r.get("unmapped_reason") or "(none given)"].append(r["source_term"])
    return {k: {"rows": len(v), "terms": sorted(set(v))}
            for k, v in sorted(by_reason.items(), key=lambda kv: -len(kv[1]))}


def equivalence_mix(rows):
    return Counter(r.get("equivalence") or "(none)" for r in _mapped(rows)).most_common()


def report(rows, vocab):
    """Print all of it. This output is what you paste into your notebook."""
    line = "-" * 72
    cov = coverage(rows)
    print("=" * 72)
    print("MAPPING REPORT")
    print("=" * 72)

    print("\n1. COVERAGE")
    print(line)
    print("   rows    %5d of %5d   %5.1f%%" % (cov["rows_mapped"], cov["rows_total"], cov["rows_pct"]))
    print("   terms   %5d of %5d   %5.1f%%" % (cov["terms_mapped"], cov["terms_total"], cov["terms_pct"]))
    print("   On its own this number flatters any map. Read it with the next one.")

    print("\n2. COLLAPSE")
    print(line)
    print("   %.2f distinct source terms per target" % collapse_ratio(rows))
    print("   %-10s %9s %6s  %s" % ("target", "sources", "rows", "what landed there"))
    for t in collapse_table(rows)[:8]:
        if t["distinct_sources"] < 2:
            continue
        print("   %-10s %9d %6d  %s" % (
            t["target_code"], t["distinct_sources"], t["rows"],
            ", ".join(s[:22] for s in t["sources"][:4])))

    resid = residual_fraction(rows, vocab)
    print("\n3. RESIDUAL")
    print(line)
    print("   %d of %d mapped rows (%.1f%%) are on an 'other' or 'unspecified' code"
          % (resid["rows_residual"], resid["rows_mapped"], resid["pct"]))
    for code, n in resid["codes"][:6]:
        print("      %-8s %5d" % (code, n))

    print("\n4. LOSS")
    print(line)
    losses = loss_table(rows)
    if not losses:
        print("   Nothing detected. Check that: this extract has laterality and")
        print("   severity in it, so an empty table usually means normalise() ate them.")
    for kind, d in losses.items():
        print("   %-12s %5d rows   e.g. %s" % (kind, d["rows"], "; ".join(d["examples"][:2])))

    print("\n5. UNMAPPED, BY REASON")
    print(line)
    for reason, d in unmapped_reasons(rows).items():
        print("   %-18s %5d rows   %d distinct terms" % (reason, d["rows"], len(d["terms"])))

    print("\n6. EQUIVALENCE MIX")
    print(line)
    for eq, n in equivalence_mix(rows):
        print("   %-12s %5d" % (eq, n))
    print()
    print("Coverage and collapse go in your 200 words together. Reporting one")
    print("without the other is the thing this lab is trying to stop you doing.")
    print()
