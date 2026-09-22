"""THE GRADED PART. Four functions, all of them stubs.

Fill them in, run the notebook, and the rest of the lab follows. The marking
rubric is on the slides and in HANDOUT.md; 30 of the 100 marks are for the
honesty of what you write down when a decision is not clean.

Nothing here needs a network connection, a licence or a server. It needs you to
decide what a line of somebody else's text means, and to record why.

A rule worth reading twice before you start: a mapping is not a lookup table.
It is a series of clinical judgements, and the ones you cannot defend in a
sentence are the ones that will be wrong.
"""

from __future__ import annotations

import re

from .vocab import Vocab

# Reasons a row cannot be mapped. Use these exact strings: metrics.py groups on
# them and the marking sheet expects them.
REASONS = (
    "no_match",          # a real clinical concept, but nothing in our vocabulary fits
    "not_in_subset",     # a real concept that ICD-10 has and our shipped subset does not
    "not_a_diagnosis",   # administrative, procedural, or otherwise not a problem
    "negation",          # the row says the patient does NOT have something
    "too_vague",         # nobody could say what was meant
    "free_text_other",   # text this pipeline is not equipped to read
)

# FHIR R4 ConceptMap equivalence values, the ones Week 5 used. R5 renamed these
# to relationship codes; the course baseline is R4.
EQUIVALENCES = ("equivalent", "wider", "narrower", "inexact", "unmatched")


def normalise(term: str) -> str:
    """Return a comparable form of a free-text term.

    CHECKPOINT 1 DEPENDS ON THIS. The extract has 644 rows and, if you count
    the raw strings, 144 different ones. Most of that difference is not
    clinical: it is capitals, doubled spaces and trailing whitespace. A correct
    normalise() collapses those away and leaves the genuine differences alone.

    What it must do:
      * strip leading and trailing whitespace
      * collapse runs of whitespace to one space
      * case-fold

    What it must NOT do:
      * throw away a negation ('no known asthma' must not become 'asthma')
      * throw away laterality or severity
      * translate anything

    Returns:
        the normalised term
    """
    raise NotImplementedError("Checkpoint 1, task 2")


def propose(term: str, local_code: str, vocab: Vocab) -> list[dict]:
    """Propose ICD-10 targets for one source row, best first.

    This is where the official map earns its place. The route that costs you
    nothing is: recognise the SNOMED concept the term names, look that concept
    up in the official map, and take its target. Everything the official map
    does not cover is a decision you make and record.

    Suggested order:
      1. the row already carries an icd10_source code, and it is in our subset
         -> propose it, but do not trust it: two of the preset codes in this
            extract are wrong, and finding them is Checkpoint 1 task 5
      2. vocab.snomed_by_text(term) finds a concept
         -> vocab.official_target(concept_id) gives the target
      3. the term names an ICD-10 title directly
         -> vocab.icd10_by_text(term)
      4. nothing matches
         -> return an empty list and let classify_unmappable say why

    Each proposal is a dict:
        {"icd10_code": "I10",
         "via": "official_map" | "icd10_title" | "icd10_source" | "manual",
         "reason": "one sentence a clinician could read"}

    Returns:
        a list of proposals, best first. An empty list means you found nothing.
    """
    raise NotImplementedError("Checkpoint 2, task 1")


def equivalence_for(term: str, icd10_code: str, vocab: Vocab) -> str:
    """Return the R4 equivalence value for one mapping, from EQUIVALENCES.

    The rule that catches people out: 'equivalent' means the two say the same
    thing. If the target says MORE than the source did, that is not equivalent
    and it is not harmless, because you have asserted something no clinician
    wrote. Mapping 'Type 2 diabetes mellitus' onto 'Type 2 diabetes mellitus
    without complications' invents the absence of complications.

      equivalent  the same meaning, nothing gained or lost
      wider       the target is broader; detail in the source is lost
      narrower    the target is more specific; you have added an assertion
      inexact     they overlap but neither contains the other
      unmatched   there is no target

    Returns:
        one of EQUIVALENCES
    """
    raise NotImplementedError("Checkpoint 2, task 3")


def classify_unmappable(term: str, local_code: str) -> str:
    """Say why a row could not be mapped. Return one of REASONS.

    The unmapped rows are not failures and they are not noise. They are the
    part of the source that the target classification cannot hold, and a map
    that does not report them is dishonest. Grouping them by reason is what
    turns 'we lost 14%' into something somebody can act on: a missing synonym
    is a morning's work, a Greek free-text field is a different project, and an
    administrative row was never a diagnosis in the first place.

    Returns:
        one of REASONS
    """
    raise NotImplementedError("Checkpoint 2, task 4")


# ---------------------------------------------------------------------------
# Written for you: the one that turns your three functions into a row of the
# concept map. Do not change it. If your map comes out wrong, the fault is in
# a function above, which is where the marks are anyway.
# ---------------------------------------------------------------------------

def map_row(row: dict, vocab: Vocab) -> dict:
    term = row["local_term"]
    local_code = row.get("local_code", "")
    proposals = propose(term, local_code, vocab)
    if proposals:
        best = proposals[0]
        return {
            "source_term": normalise(term),
            "source_code": local_code,
            "target_code": best["icd10_code"],
            "equivalence": equivalence_for(term, best["icd10_code"], vocab),
            "via": best["via"],
            "reason": best["reason"],
            "unmapped_reason": "",
        }
    return {
        "source_term": normalise(term),
        "source_code": local_code,
        "target_code": "",
        "equivalence": "unmatched",
        "via": "",
        "reason": "",
        "unmapped_reason": classify_unmappable(term, local_code),
    }
