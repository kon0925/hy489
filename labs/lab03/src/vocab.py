"""Loading and lookup for the three vocabulary files. Written for you.

    from src.vocab import Vocab
    v = Vocab()
    v.snomed_by_text("HTN")            -> the Essential hypertension row, or None
    v.official_target("59621000")      -> the official_map row, or None
    v.icd10("I10")                     -> the ICD-10 row
    v.is_residual("J45.9")             -> True

Nothing here makes a decision. It finds things. Every decision is in
mapping.py, which is the part you write and the part that is marked.

THE FILES
---------
vocab/snomed_subset.csv   14 SNOMED concepts, the ones in the Lab 1 cohort,
                          with their fully specified name, preferred term,
                          synonyms and immediate parent.
vocab/icd10_subset.csv    25 ICD-10 codes, with block, chapter and a flag for
                          the residual ones (the .8 and .9 'other' and
                          'unspecified' categories).
vocab/official_map.csv    SNOMED to ICD-10 for those 14 concepts, with an
                          equivalence and a note saying what each one costs.

All three are hand-built teaching subsets, not the real thing. The real SNOMED
to ICD-10 map is a licensed artefact from SNOMED International and Greece is
not a member, which is the Week 5 licensing slide arriving in your lab. Check
anything you are unsure of against icd.who.int/browse and
browser.ihtsdotools.org, both of which are free.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

VOCAB_DIR = Path(__file__).resolve().parent.parent / "vocab"


def _read(name):
    with open(VOCAB_DIR / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def simple_key(text: str) -> str:
    """A crude normalisation, used only for the lookup index in this file.

    It is deliberately not the one you write in mapping.normalise(): this one
    is just enough to index the vocabulary, and it will not handle the mess in
    the extract. Do not import it and call it done.
    """
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9Ͱ-Ͽ ]+", " ", text)
    return re.sub(r"\s+", " ", text)


class Vocab:
    def __init__(self):
        self.snomed = _read("snomed_subset.csv")
        self.icd10_rows = _read("icd10_subset.csv")
        self.official = _read("official_map.csv")

        self._snomed_by_code = {r["concept_id"]: r for r in self.snomed}
        self._icd10_by_code = {r["code"]: r for r in self.icd10_rows}
        self._official_by_snomed = {r["snomed_code"]: r for r in self.official}

        # every string that names a SNOMED concept: its FSN, its preferred
        # term and each synonym, all under the same concept
        self._snomed_index = {}
        for row in self.snomed:
            names = [row["fsn"], row["preferred_term"]]
            names += [s for s in row["synonyms"].split("|") if s]
            # the FSN carries a semantic tag in brackets; index it both ways
            names.append(re.sub(r"\s*\([^)]*\)\s*$", "", row["fsn"]))
            for name in names:
                self._snomed_index.setdefault(simple_key(name), row)

        self._icd10_index = {}
        for row in self.icd10_rows:
            self._icd10_index.setdefault(simple_key(row["title"]), row)

    # ---- SNOMED ----------------------------------------------------------

    def snomed_by_code(self, code):
        return self._snomed_by_code.get(str(code).strip())

    def snomed_by_text(self, text):
        """Exact match on FSN, preferred term or synonym, after simple_key.

        Returns None for anything it has not seen before, which is most of the
        extract. Widening this is your job, not this function's.
        """
        return self._snomed_index.get(simple_key(text))

    def snomed_parent(self, code):
        row = self.snomed_by_code(code)
        if not row or not row["parent_id"]:
            return None
        return {"concept_id": row["parent_id"], "preferred_term": row["parent_term"]}

    # ---- ICD-10 ----------------------------------------------------------

    def icd10(self, code):
        return self._icd10_by_code.get(str(code).strip())

    def icd10_by_text(self, text):
        return self._icd10_index.get(simple_key(text))

    def icd10_exists(self, code):
        return str(code).strip() in self._icd10_by_code

    def is_residual(self, code):
        """True for the 'other' and 'unspecified' categories.

        The share of your map that lands on these is the residual fraction,
        and it is one of the four numbers Checkpoint 3 asks for.
        """
        row = self.icd10(code)
        return bool(row) and row["residual"] == "yes"

    def chapter(self, code):
        row = self.icd10(code)
        return row["chapter"] if row else None

    # ---- the official map ------------------------------------------------

    def official_target(self, snomed_code):
        """The shipped SNOMED to ICD-10 row, or None if the concept is not in it."""
        return self._official_by_snomed.get(str(snomed_code).strip())

    def official_targets(self):
        """Every ICD-10 code the official map points at, with how many SNOMED
        concepts point at each. The first collapse you will see."""
        counts = {}
        for row in self.official:
            counts.setdefault(row["icd10_code"], []).append(row["snomed_term"])
        return counts
