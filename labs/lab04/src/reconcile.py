"""Matching the archive against the cohort you have had since Week 1.

ONE STUB IN THIS FILE: match.

The imaging archive and the EHR extract are two systems that were never
designed to agree. The archive knows PAGNI100275; the CSV knows
8c3793c8-230d-ee62-60bf-fe61dcadd0d1. Neither identifier appears in the other
file, so the only way across is the demographics, and the demographics
disagree.

This is Week 7's record linkage again, with two differences. The population is
tiny, so you can look at every pair by hand. And the answer is not a score: it
is a decision about each patient, which somebody has to sign.
"""

import csv
import unicodedata


def load_cohort(path):
    """The Lab 1 patients.csv, as a list of dicts."""
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def normalise_name(value):
    """Fold a name to something two systems might agree on.

    Upper case, accents stripped, everything that is not a letter removed. It
    is blunt on purpose: anything cleverer is a decision you should be making
    explicitly rather than hiding in a helper.
    """
    if value is None:
        return ""
    s = unicodedata.normalize("NFKD", str(value))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.upper() if c.isalpha())


def split_dicom_name(value):
    """DICOM PersonName is family^given^middle^prefix^suffix.

    Returns (family, given), both normalised. Components that are not there
    come back empty, which is normal and not an error.
    """
    parts = (str(value or "")).split("^")
    family = normalise_name(parts[0] if len(parts) > 0 else "")
    given = normalise_name(parts[1] if len(parts) > 1 else "")
    return family, given


def cohort_key(row):
    """(family, given, birthdate as YYYYMMDD, sex) for one CSV row."""
    return (normalise_name(row["LAST"]), normalise_name(row["FIRST"]),
            row["BIRTHDATE"].replace("-", ""), row["GENDER"])


def match(archive_patients, cohort):
    """STUB 7. Decide, for each patient in the archive, who they are.

    archive_patients is the table inventory.patients() produced: the index is
    PatientID and the columns names, birth_dates, sexes, studies, series and
    instances. Several of those are lists, because the archive does not always
    agree with itself about one patient.

    cohort is the list of dicts from load_cohort.

    Return a list of dicts, one per archive PatientID, each with:

        patient_id      as it appears in the archive
        status          one of: "exact", "partial", "ambiguous", "none"
        cohort_id       the Id from patients.csv for an accepted match, else None
        best_cohort_id  the Id of the closest row, ALWAYS, even for "none"
        agreed          which of family, given, birth, sex matched the closest row
        disagreed       which did not
        note            one sentence a person could act on

    Fill best_cohort_id even when you reject the match. A patient you could
    not link and a patient with no plausible candidate are two different
    problems and the report has to tell them apart.

    One more thing to carry: archive_patients gives you a LIST of names,
    birth dates and sexes per PatientID, because one of these patients is
    recorded two ways inside the archive itself. Picking the first silently is
    a decision. Say in the note which value you matched on.

    The four statuses:

        exact       all four of family, given, birth and sex agree with
                    exactly one cohort row
        partial     birth date and family name agree with exactly one cohort
                    row and something else does not. These are the interesting
                    ones. Say what disagrees; do not silently accept them
        ambiguous   more than one cohort row fits equally well
        none        nothing fits. Not an error on its own: see the handout

    Match on the normalised values, not the raw ones, and use birth date as the
    strongest field: a date is harder to mistype into another valid date than a
    name is to spell differently.
    """
    raise NotImplementedError("Lab 4, Part C, task 2")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def report(results, archive_patients):
    """Print the reconciliation, and the sentence that goes with it."""
    order = {"exact": 0, "partial": 1, "ambiguous": 2, "none": 3}
    rows = sorted(results, key=lambda r: (order[r["status"]], r["patient_id"]))

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    print("%-13s %-10s %-9s %s" % ("PatientID", "status", "instances", "note"))
    print("-" * 92)
    for r in rows:
        n = int(archive_patients.loc[r["patient_id"], "instances"])
        print("%-13s %-10s %9d %s" % (r["patient_id"], r["status"], n,
                                      r["note"]))
    print()
    total = len(rows)
    linked = counts.get("exact", 0)
    print("%d of %d archive patients link to the cohort on all four fields."
          % (linked, total))
    for status in ("partial", "ambiguous", "none"):
        if counts.get(status):
            print("  %-10s %d" % (status, counts[status]))

    unmatched_instances = sum(
        int(archive_patients.loc[r["patient_id"], "instances"])
        for r in rows if r["status"] != "exact")
    print()
    print("%d of %d instances belong to a patient this process did not "
          "resolve outright." % (unmatched_instances,
                                 int(archive_patients["instances"].sum())))
    print()
    print("Write the next sentence yourself. The rate is not the finding: the "
          "finding is which patients are in the leftover and whether a study "
          "that cannot be linked should still be counted in a cohort.")
