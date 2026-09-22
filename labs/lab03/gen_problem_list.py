#!/usr/bin/env python3
"""Generate labs/lab03/data/problem_list.csv.

You do not need to run this. The CSV beside it is committed and every number in
the handout comes from that exact file. This script is here so the data is
reproducible and so you can see that the mess in it was put there on purpose.

WHAT THIS IS
------------
A synthetic problem list from a second hospital. Lab 1's cohort is a clean
Synthea export where every row already carries a standard SNOMED code. Real
second sources are not like that, and a mapping lab against a perfectly coded
file would teach the wrong lesson.

So this extract has what a real local problem list has:

  * the same clinical concepts written four or five different ways
  * local codes that mean something only inside this hospital
  * rows with no code at all, just what somebody typed
  * negations, laterality, severity and other detail that the target
    classification cannot carry
  * a few rows that are not diagnoses at all
  * some Greek, because a Greek hospital writes in Greek
  * one pair of terms that look identical and are not, because one of them
    was typed with a Latin letter in the middle of a Greek word

Every one of those is a category in the loss report you will write.

Seeded with random.seed(489), the same seed as the Lab 1 generator, so the file
is identical for everyone.
"""

from __future__ import annotations

import csv
import random
import datetime as dt
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "data" / "problem_list.csv"

random.seed(489)

# (local_code, local_term, weight, concept_key)
# concept_key is what the entry actually means, and is NOT in the CSV. It is
# only used here to decide how often each spelling appears. Working out that
# four spellings are one concept is Checkpoint 1.
ENTRIES = [
    # --- hypertension: one concept, five ways of writing it ----------------
    ("CARD-001", "Essential hypertension",            60, "htn"),
    ("CARD-001", "Hypertension, essential",           18, "htn"),
    ("CARD-H01", "HTN",                               34, "htn"),
    (None,       "essential  HTN",                    12, "htn"),
    # Two Greek spellings of hypertension. They look identical and they are
    # not: the first starts with a LATIN capital Y (U+0059) and the second
    # with a GREEK capital upsilon (U+03A5). A sending system that was
    # configured in the wrong locale really does produce this, and no amount
    # of lowercasing will make the two match. Finding it is Checkpoint 1
    # task 4; it is in here on purpose.
    (None,       "Yπέρταση",                            9, "htn_homoglyph"),
    (None,       "Υπέρταση",                            7, "htn"),

    # --- type 2 diabetes: four ways ---------------------------------------
    ("ENDO-002", "Type 2 diabetes mellitus",          41, "t2dm"),
    ("ENDO-002", "Diabetes mellitus type II",         14, "t2dm"),
    ("ENDO-D2",  "DM2",                               22, "t2dm"),
    (None,       "T2DM, diet controlled",             11, "t2dm"),

    # --- asthma, with severity the target cannot carry ---------------------
    ("RESP-010", "Asthma",                            26, "asthma"),
    ("RESP-010", "Childhood asthma",                  17, "asthma"),
    (None,       "Mild persistent asthma",            12, "asthma_mild"),
    (None,       "Asthma exacerbation, moderate",      8, "asthma_exac"),
    (None,       "no known asthma",                    6, "negation"),

    # --- osteoarthritis, with laterality the target cannot carry ----------
    ("ORTH-021", "Osteoarthritis of knee",            19, "oa_knee"),
    (None,       "OA left knee",                      14, "oa_knee_left"),
    (None,       "OA right knee",                     13, "oa_knee_right"),
    (None,       "Bilateral knee OA",                  7, "oa_knee_bilat"),

    # --- the rest of the Lab 1 concepts, less messily ---------------------
    ("HAEM-030", "Anaemia",                           25, "anaemia"),
    (None,       "Anemia",                            11, "anaemia"),
    ("ENT-040",  "Chronic sinusitis",                 21, "sinusitis_chronic"),
    ("ENT-041",  "Viral sinusitis",                    9, "sinusitis_viral"),
    ("ENT-042",  "Otitis media",                      12, "om"),
    ("RESP-011", "Acute viral pharyngitis",           28, "pharyngitis"),
    ("ENDO-003", "Hyperlipidaemia",                   23, "lipid"),
    (None,       "raised cholesterol",                 9, "lipid"),
    ("ENDO-004", "Prediabetes",                       18, "predm"),
    (None,       "impaired glucose tolerance",         8, "predm"),
    ("OBST-050", "Normal pregnancy",                  16, "pregnancy"),
    ("ENDO-005", "Obesity, BMI over 30",              14, "obesity"),

    # --- in ICD-10, but not in the SNOMED subset we ship ------------------
    ("CARD-060", "Atrial fibrillation",               17, "af"),
    ("NEUR-070", "Migraine without aura",             11, "migraine"),
    ("GAST-080", "Gastro-oesophageal reflux disease", 13, "gord"),
    ("PSYC-090", "Depressive episode, mild",           9, "depression"),
    ("MSK-100",  "Low back pain",                     15, "lbp"),

    # --- not a diagnosis at all -------------------------------------------
    ("ADMIN-01", "Consent obtained",                   7, "admin"),
    ("ADMIN-02", "Referred to dietitian",              6, "admin"),
    ("PROC-200", "Knee arthroscopy",                   5, "procedure"),

    # --- genuinely unclassifiable -----------------------------------------
    (None,       "?DM",                                6, "vague"),
    (None,       "for review",                         5, "vague"),
    (None,       "see clinic letter",                  5, "vague"),
    (None,       "χωρίς ευρήματα",                     4, "vague_el"),
    (None,       "παρακολούθηση",                      4, "vague_el"),
]

# A few rows arrive with an ICD-10 code already filled in by the sending
# system. Two of them are wrong, which is the point of Checkpoint 1 task 5.
PRESET_ICD10 = {
    "Essential hypertension": "I10",
    "Type 2 diabetes mellitus": "E11",
    "Atrial fibrillation": "I48",
    "Acute viral pharyngitis": "J02",
    "Anaemia": "D64",
    "Chronic sinusitis": "J01",      # WRONG: J01 is acute, J32 is chronic
    "Prediabetes": "E11",            # WRONG: prediabetes is not diabetes
}


def main():
    start = dt.date(2024, 1, 2)
    rows = []
    row_id = 0
    for local_code, term, weight, _key in ENTRIES:
        for _ in range(weight):
            row_id += 1
            # trailing and doubled whitespace, and inconsistent case, the way a
            # free-text field really arrives
            text = term
            if random.random() < 0.12:
                text = text.upper()
            if random.random() < 0.10:
                text = text.lower()
            if random.random() < 0.15:
                text = text + " "
            rows.append({
                "row_id": "PL-%04d" % row_id,
                "patient_ref": "H2-%05d" % random.randint(1, 900),
                "recorded_date": (start + dt.timedelta(days=random.randint(0, 700))).isoformat(),
                "local_code": local_code or "",
                "local_term": text,
                "icd10_source": PRESET_ICD10.get(term, ""),
                "recorded_by": random.choice(["clinic", "clinic", "ward", "ED", "letter"]),
            })
    random.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("wrote %s" % OUT)
    print("  rows                %5d" % len(rows))
    print("  distinct local_term %5d" % len({r["local_term"].strip().lower() for r in rows}))
    print("  distinct local_code %5d" % len({r["local_code"] for r in rows if r["local_code"]}))
    print("  rows with no code   %5d" % sum(1 for r in rows if not r["local_code"]))
    print("  rows with icd10     %5d" % sum(1 for r in rows if r["icd10_source"]))


if __name__ == "__main__":
    main()
