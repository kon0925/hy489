"""Self-check for Lab 5. Run it before you submit.

    python3 check_submission.py

It is not the mark. It checks the things that cost marks for no reason: a
deliverable that is not there, a notebook that was not run in order, a key
sitting inside the release, and a pseudonym scheme left at the one the lab told
you to break.

What it checks:

  1. the six deliverables exist and are not stubs
  2. out/ holds a release and key/ holds the key, and they are not the same
     folder
  3. the notebook was restarted and run from the top
  4. your patient_pseudonym is not naive_pseudonym, and it is keyed
  5. your remap_uid is consistent and produces UIDs under the 2.25 arc
  6. every released instance declares (0012,0062) and (0012,0064)
  7. no PatientID, PatientName, birth date, accession number or original UID
     from the Lab 4 archive appears anywhere in out/
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.abspath(os.path.join(HERE, "..", "lab04", "data", "archive"))
OUT = os.path.join(HERE, "out")
RELEASE = os.path.join(OUT, "archive")
KEY = os.path.join(HERE, "key")
NB = os.path.join(HERE, "notebooks")

REPORT_SECTIONS = [
    "## 1. The profile",
    "## 2. Identifiers and UIDs",
    "## 3. The four decisions",
    "## 4. What the profile did not reach",
    "## 5. The audit, read back",
]

ok = True


def good(msg):
    print("  ok    %s" % msg)


def bad(msg):
    global ok
    ok = False
    print("  FAIL  %s" % msg)


def warn(msg):
    print("  note  %s" % msg)


def check_files():
    print("deliverables")
    if not os.path.isdir(RELEASE):
        bad("out/archive/ not found. That is the release.")
        return False
    n = sum(len(fs) for _, _, fs in os.walk(RELEASE))
    if n == 0:
        bad("out/archive/ is empty")
        return False
    good("out/archive/ holds %d files" % n)

    for path, label in ((os.path.join(OUT, "manifest.csv"), "out/manifest.csv"),
                        (os.path.join(KEY, "link_table.csv"),
                         "key/link_table.csv"),
                        (os.path.join(KEY, "uid_map.csv"), "key/uid_map.csv"),
                        (os.path.join(NB, "lab05.ipynb"),
                         "notebooks/lab05.ipynb"),
                        (os.path.join(NB, "deident_report.md"),
                         "notebooks/deident_report.md"),
                        (os.path.join(NB, "audit.json"),
                         "notebooks/audit.json")):
        if os.path.isfile(path):
            good("%s" % label)
        else:
            bad("%s not found" % label)

    # the key must not be inside the release
    for dirpath, _, filenames in os.walk(OUT):
        for name in filenames:
            if name in ("link_table.csv", "uid_map.csv"):
                bad("%s is inside out/. The key does not ship with the data."
                    % os.path.relpath(os.path.join(dirpath, name), HERE))
    return True


def check_report():
    path = os.path.join(NB, "deident_report.md")
    if not os.path.isfile(path):
        return
    text = open(path, encoding="utf-8").read()
    print()
    print("the written report")
    for heading in REPORT_SECTIONS:
        if heading not in text:
            bad("section missing: %s" % heading)
            continue
        start = text.index(heading) + len(heading)
        ends = [text.index(h) for h in REPORT_SECTIONS
                if h in text and text.index(h) > start]
        body = text[start:min(ends)] if ends else text[start:]
        if len(body.strip()) < 200:
            bad("%s is %d characters. 55 of the 100 marks are here."
                % (heading, len(body.strip())))
        else:
            good("%-38s %5d characters" % (heading, len(body.strip())))


def check_notebook():
    path = os.path.join(NB, "lab05.ipynb")
    if not os.path.isfile(path):
        return
    print()
    print("the notebook")
    try:
        nb = json.load(open(path, encoding="utf-8"))
    except Exception as exc:                                  # noqa: BLE001
        bad("notebooks/lab05.ipynb is not valid JSON: %s" % exc)
        return
    counts = [c.get("execution_count") for c in nb.get("cells", [])
              if c.get("cell_type") == "code" and "".join(c.get("source", [])).strip()]
    if not counts:
        bad("no executed code cells")
        return
    if any(c is None for c in counts):
        bad("%d code cells were never run" % sum(1 for c in counts if c is None))
        return
    if counts != sorted(counts) or counts[0] != 1:
        bad("execution counts are %s. Restart the kernel and run all, so that "
            "the numbers go 1, 2, 3 down the page." % counts[:8])
    else:
        good("%d code cells, run in order from 1" % len(counts))


def check_code():
    print()
    print("your code")
    sys.path.insert(0, HERE)
    try:
        from src import pseudonym
    except Exception as exc:                                  # noqa: BLE001
        bad("cannot import src.pseudonym: %s" % exc)
        return

    try:
        a = pseudonym.patient_pseudonym("PAGNI100001", "secret one")
    except NotImplementedError:
        bad("patient_pseudonym is still a stub")
        return
    except Exception as exc:                                  # noqa: BLE001
        bad("patient_pseudonym raised %s" % type(exc).__name__)
        return

    if str(a) == pseudonym.naive_pseudonym("PAGNI100001"):
        bad("patient_pseudonym returns what naive_pseudonym returns. Part C "
            "breaks that in 110,000 guesses.")
    else:
        good("patient_pseudonym is not naive_pseudonym")

    b = pseudonym.patient_pseudonym("PAGNI100001", "secret two")
    if str(a) == str(b):
        bad("two different secrets give the same pseudonym, so the secret is "
            "not doing anything")
    else:
        good("the secret changes the output")

    c = pseudonym.patient_pseudonym("PAGNI100001", "secret one")
    if str(a) != str(c):
        bad("the same input and secret gave two different answers. The archive "
            "cannot agree with itself.")
    else:
        good("same input, same secret, same answer")

    uid_map = {}
    try:
        u1 = pseudonym.remap_uid("1.2.840.113619.2.1", uid_map, "secret one")
        u2 = pseudonym.remap_uid("1.2.840.113619.2.1", uid_map, "secret one")
        u3 = pseudonym.remap_uid("1.2.840.113619.2.2", uid_map, "secret one")
    except NotImplementedError:
        bad("remap_uid is still a stub")
        return
    except Exception as exc:                                  # noqa: BLE001
        bad("remap_uid raised %s" % type(exc).__name__)
        return
    if str(u1) != str(u2):
        bad("remap_uid gave two answers for one original UID")
    elif str(u1) == str(u3):
        bad("remap_uid gave one answer for two different originals")
    elif not str(u1).startswith("2.25."):
        bad("remap_uid returned %s, which is not under the 2.25 arc" % u1)
    elif len(str(u1)) > 64:
        bad("remap_uid returned %d characters; a UID is at most 64" % len(str(u1)))
    else:
        good("remap_uid is consistent, injective on this pair and under 2.25")


def check_release():
    if not os.path.isdir(RELEASE):
        return
    print()
    print("the release")
    try:
        import pydicom
    except ImportError:
        bad("pydicom is not installed in this environment")
        return
    sys.path.insert(0, HERE)
    from src import verify

    needles, uids = verify.known_identifiers(ARCHIVE)
    hits = verify.scan_for_leaks(RELEASE, needles, uids)
    if hits:
        bad("%d original identifiers survive in out/" % len(hits))
        for h in hits[:10]:
            print("          %-30s %-26s %s"
                  % (h["path"], h["keyword"], h["needle"]))
    else:
        good("no original identifier found in out/ (%d needles, %d UIDs)"
             % (len(needles), len(uids)))

    missing_declaration, total = 0, 0
    for rel in verify.walk_relative(RELEASE):
        try:
            ds = pydicom.dcmread(os.path.join(RELEASE, rel),
                                 stop_before_pixels=True)
        except Exception:                                     # noqa: BLE001
            continue
        total += 1
        if str(ds.get("PatientIdentityRemoved", "")) != "YES" \
                or "DeidentificationMethodCodeSequence" not in ds:
            missing_declaration += 1
    if missing_declaration:
        bad("%d of %d released instances do not declare what was done to them"
            % (missing_declaration, total))
    else:
        good("all %d released instances carry (0012,0062) and (0012,0064)"
             % total)

    structure = verify.check_structure(RELEASE)
    if structure["still_declaring_burned_in"]:
        warn("%d instance(s) still declare BurnedInAnnotation YES: %s"
             % (len(structure["still_declaring_burned_in"]),
                ", ".join(structure["still_declaring_burned_in"])))
        warn("that is a defensible decision and section 3 has to say it is one")
    if structure["studies_with_more_than_one_patient"]:
        warn("%d released study carries more than one pseudonym"
             % len(structure["studies_with_more_than_one_patient"]))
        warn("that is Lab 4's merged study and section 3 has to say what you "
             "did with it")


def main():
    print("Lab 5 self-check")
    print()
    if not os.path.isdir(ARCHIVE):
        print("  FAIL  ../lab04/data/archive not found. Lab 5 reads the Lab 4 "
              "archive in place; clone the whole repository.")
        return 1
    if check_files():
        check_code()
        check_release()
    check_notebook()
    check_report()
    print()
    if ok:
        print("Everything checks. Submit out/, key/, notebooks/ and src/.")
        return 0
    print("Fix the failures above before you submit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
