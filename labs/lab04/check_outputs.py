"""Self-check for Lab 4. Run it before you leave the room.

    python3 check_outputs.py

It is not a mark. Lab 4 is not graded. It is here so that you find out today
that your inventory is short of four instances, rather than on 27 November when
Lab 5 de-identifies it.

What it checks:

  1. notebooks/inventory.csv exists and has one row per readable file
  2. the columns are the ones in INSTANCE_FIELDS
  3. the six headline counts agree with the archive
  4. the four fields Lab 5 needs are populated
  5. notebooks/archive_report.md exists and is not a stub
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, "data", "archive")
NB = os.path.join(HERE, "notebooks")

EXPECTED = {
    "files on disk": 85,
    "rows in the inventory": 84,
    "distinct patients": 9,
    "distinct studies": 10,
    "distinct series": 12,
    "distinct instance UIDs": 83,
}

#: Lab 5 reads these four columns out of your inventory. Nothing else is
#: load-bearing across the two labs.
LAB5_NEEDS = ["path", "patient_id", "study_uid", "sop_uid"]

ok = True


def good(msg):
    print("  ok    %s" % msg)


def bad(msg):
    global ok
    ok = False
    print("  FAIL  %s" % msg)


def main():
    print("Lab 4 self-check")
    print()

    if not os.path.isdir(ARCHIVE):
        bad("data/archive is missing. Clone the whole repository.")
        return 1

    on_disk = sum(len(fs) for _, _, fs in os.walk(ARCHIVE))
    if on_disk == EXPECTED["files on disk"]:
        good("archive has %d files" % on_disk)
    else:
        bad("archive has %d files, expected %d. Something was deleted or added."
            % (on_disk, EXPECTED["files on disk"]))

    path = os.path.join(NB, "inventory.csv")
    if not os.path.isfile(path):
        bad("notebooks/inventory.csv not found. "
            'df.to_csv("inventory.csv", index=False) from the notebook.')
        return 1

    try:
        import pandas as pd
    except ImportError:
        bad("pandas is not installed in this environment")
        return 1

    df = pd.read_csv(path)
    good("inventory.csv read, %d rows, %d columns" % (len(df), len(df.columns)))

    try:
        sys.path.insert(0, HERE)
        from src.inventory import INSTANCE_FIELDS
    except Exception as exc:                        # noqa: BLE001
        bad("cannot import src.inventory: %s" % exc)
        return 1

    missing = [c for c in INSTANCE_FIELDS if c not in df.columns]
    if missing:
        bad("columns missing from the inventory: %s" % ", ".join(missing))
    else:
        good("all %d INSTANCE_FIELDS columns present" % len(INSTANCE_FIELDS))

    checks = [
        ("rows in the inventory", len(df)),
        ("distinct patients", df["patient_id"].nunique()
         if "patient_id" in df else -1),
        ("distinct studies", df["study_uid"].nunique()
         if "study_uid" in df else -1),
        ("distinct series", df["series_uid"].nunique()
         if "series_uid" in df else -1),
        ("distinct instance UIDs", df["sop_uid"].nunique()
         if "sop_uid" in df else -1),
    ]
    for label, got in checks:
        want = EXPECTED[label]
        if got == want:
            good("%-24s %d" % (label, got))
        else:
            bad("%-24s %d, expected %d" % (label, got, want))

    if len(df) == EXPECTED["rows in the inventory"] and \
            "sop_uid" in df and df["sop_uid"].nunique() == len(df):
        bad("every SOPInstanceUID is distinct. One of them is not, and the "
            "fact that yours are means something was deduplicated on the way "
            "into the table.")

    for col in LAB5_NEEDS:
        if col in df.columns and df[col].isna().sum() == 0:
            good("%-24s populated on every row (Lab 5 reads this)" % col)
        elif col in df.columns:
            bad("%-24s empty on %d rows; Lab 5 needs it on all of them"
                % (col, int(df[col].isna().sum())))

    report = os.path.join(NB, "archive_report.md")
    if not os.path.isfile(report):
        bad("notebooks/archive_report.md not found")
    else:
        text = open(report, encoding="utf-8").read().strip()
        if len(text) < 400:
            bad("archive_report.md is %d characters. The findings alone are "
                "longer than that." % len(text))
        else:
            good("archive_report.md, %d characters" % len(text))

    print()
    if ok:
        print("Everything checks. Bring inventory.csv to Lab 5.")
        return 0
    print("Fix the failures above. None of them is a mark; all of them are "
          "things Lab 5 will trip over.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
