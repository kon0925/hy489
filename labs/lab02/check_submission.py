#!/usr/bin/env python3
"""Run this before you submit Lab 2.

It checks the four required files are present, that the notebook has been
executed, and that src/mapping.py imports. It does not mark your work; it
catches the things that cost marks for no reason.

    python check_submission.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
ok = True


def check(label: str, passed: bool, detail: str = "") -> None:
    global ok
    print(f"[{'PASS' if passed else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    ok = ok and passed


nb_path = HERE / "notebooks" / "lab02.ipynb"
check("notebooks/lab02.ipynb exists", nb_path.is_file())

if nb_path.is_file():
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    executed = [c for c in code_cells if c.get("execution_count")]
    check("notebook has been executed", len(executed) > 0,
          f"{len(executed)}/{len(code_cells)} code cells have output")
    counts = [c["execution_count"] for c in executed if c.get("execution_count")]
    check("cells run in order (restart and run all)",
          counts == sorted(counts),
          "execution counts are out of order" if counts != sorted(counts) else "")
    first = "".join(cells[0].get("source", [])) if cells else ""
    check("names in the first cell", len(first.strip()) > 10,
          "put both names in the first cell if you worked in a pair")

check("src/mapping.py exists", (HERE / "src" / "mapping.py").is_file())
check("rejections.csv exists", (HERE / "rejections.csv").is_file(),
      "an empty file with just a header is a valid answer")
check("NOTES.md exists", (HERE / "NOTES.md").is_file())

notes = HERE / "NOTES.md"
if notes.is_file():
    n = len([l for l in notes.read_text(encoding="utf-8").splitlines() if l.strip()])
    check("NOTES.md has something in it", n >= 8, f"{n} non-empty lines, expected at least 8")

sys.path.insert(0, str(HERE))
try:
    from src import mapping  # noqa: F401
    check("src/mapping.py imports", True)
    todo = [f for f in ("to_patient", "to_encounter", "to_condition", "to_observation")
            if not hasattr(mapping, f)]
    check("all four mapping functions defined", not todo, ", ".join(todo))
    check("identifier namespace changed from the default",
          mapping.SYSTEM.rstrip("/").split("/")[-1] != "AM0000",
          "SYSTEM still ends in AM0000; put your student number in it")
except Exception as e:  # noqa: BLE001
    check("src/mapping.py imports", False, f"{type(e).__name__}: {e}")

print()
print("Ready to submit." if ok else "Fix the FAIL lines above before submitting.")
sys.exit(0 if ok else 1)
