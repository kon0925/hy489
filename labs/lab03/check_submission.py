#!/usr/bin/env python3
"""Run this before you submit Lab 3.

It checks the four deliverables are present and in the right shape. It does not
mark your work; it catches the things that cost marks for no reason.

    python check_submission.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
ok = True

REQUIRED_COLUMNS = {"source_term", "target_code", "equivalence", "reason"}
EQUIVALENCES = {"equivalent", "wider", "narrower", "inexact", "unmatched"}


def check(label, passed, detail=""):
    """Print one result. The detail line is the fix, so it only shows on a FAIL."""
    global ok
    print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    if not passed and detail:
        print(f"       {detail}")
    ok = ok and passed


# ---- the notebook ---------------------------------------------------------
nb_path = HERE / "notebooks" / "lab03.ipynb"
check("notebooks/lab03.ipynb exists", nb_path.is_file())
if nb_path.is_file():
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    code = [c for c in cells if c.get("cell_type") == "code"]
    executed = [c for c in code if c.get("execution_count")]
    check("the notebook has been run", len(executed) > 0,
          "no cell has an execution count")
    counts = [c["execution_count"] for c in executed]
    check("it was run top to bottom", counts == sorted(counts),
          "restart the kernel and Run All before submitting")
    text = "\n".join("".join(c.get("source", [])) for c in cells)
    words = len(text.split())
    check("the 200 words are in there", "200 words" in text.lower() or words > 400,
          "the reflection goes in the last markdown cell")

# ---- the map --------------------------------------------------------------
map_path = HERE / "concept_map.csv"
check("concept_map.csv exists", map_path.is_file())
if map_path.is_file():
    with open(map_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    check("concept_map.csv has rows", len(rows) > 0)
    if rows:
        missing = REQUIRED_COLUMNS - set(rows[0].keys())
        check("it has the required columns", not missing, f"missing {sorted(missing)}")
        bad_eq = {r.get("equivalence") for r in rows} - EQUIVALENCES - {""}
        check("every equivalence is a valid R4 value", not bad_eq, f"found {sorted(bad_eq)}")
        mapped = [r for r in rows if r.get("target_code")]
        no_reason = [r for r in mapped if not (r.get("reason") or "").strip()]
        check("every mapped row has a reason", not no_reason,
              f"{len(no_reason)} mapped rows have an empty reason, and that is "
              f"where 30 of the marks are")

# ---- the loss report ------------------------------------------------------
unmapped_path = HERE / "UNMAPPED.md"
check("UNMAPPED.md exists", unmapped_path.is_file())
if unmapped_path.is_file():
    body = unmapped_path.read_text(encoding="utf-8")
    check("UNMAPPED.md is not a placeholder", len(body.split()) > 80,
          "group the unmapped rows by reason and say what you would do about each")

print()
print("READY TO SUBMIT" if ok else "NOT READY: fix the FAILs above")
sys.exit(0 if ok else 1)
