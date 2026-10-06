"""Identifiers out, identifiers in. And the map between them.

TWO STUBS IN THIS FILE: patient_pseudonym and remap_uid.

Two separate jobs that people run together and should not.

The first is the patient. Every instance in the archive carries a PatientID
and the release must not. Something has to go in its place, the same something
every time for the same person, or the archive stops being an archive and
becomes 84 unrelated images.

The second is the UID. StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID and
FrameOfReferenceUID are what hold the hierarchy together, and PS3.15 says U for
all of them: replace with a new UID that is consistent across the set. The
word doing the work is consistent. One original UID means one new UID, in
every file it appears in, including the ones that only reference it.

Where the new UIDs come from
----------------------------
The 2.25 arc. 2.25.<integer> is the branch of the OID tree that encodes a UUID
as a decimal integer, and anybody may use it without registering anything. The
Lab 4 generator does the same thing, for the same reason. A hospital that mints
its own UIDs either uses 2.25 or registers a root of its own, and a new UID
under somebody else's root is a UID that claims to have come from them.
"""

import csv
import hashlib
import hmac

from pydicom.uid import UID

#: The same seed as Lab 1, Lab 3 and Lab 4, so a rerun of this lab produces
#: the same output for everybody in the room.
SEED = 489

#: The prefix this lab puts on a patient pseudonym. It is not a standard and
#: it is not secret. It is there so that a pseudonym is obviously a pseudonym
#: and nobody downstream mistakes it for a hospital number.
PREFIX = "HY489"


def naive_pseudonym(value):
    """What almost everybody writes first. Do not ship it.

    A SHA-256 of the identifier, truncated. It is deterministic, it is
    collision-free in practice, it looks like cryptography, and it is
    reversible by anybody who can write a for loop.

    The reason is in Week 8: a hash is only one-way when the input cannot be
    guessed. A PAGNI number is six digits behind a fixed prefix. Hash all of
    them, compare, read the answer off. Part C makes you do it to your own
    output.
    """
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return "%s-%s" % (PREFIX, digest[:12].upper())


def patient_pseudonym(value, secret):
    """STUB 1. The identifier that goes into the release.

    Returns a string. Same input and same secret give the same output, every
    time, in every process, on every machine, because the whole archive has to
    agree with itself and so does the student sitting next to you.

    What the standard fixes: nothing. PS3.15 says Z/D for PatientID, which
    means a zero-length value or a dummy value of your choosing. Everything
    below is yours.

      the function        naive_pseudonym above is the thing to beat. Part C
                          breaks it in front of you, so write the version that
                          survives. A keyed hash is the usual answer: the
                          attacker can still enumerate the ID space and cannot
                          check a guess without the key.
      the secret          where it lives and who does not get it. A key that
                          travels with the data is decoration.
      the shape           how long, what alphabet, whether PREFIX is on it.
                          A pseudonym that can be mistaken for a hospital
                          number will be.

    Say in your report what a keyed hash buys and what it does not. It does
    not make the release anonymous: the holder of the key can reverse every
    pseudonym in it, which is the whole of GDPR Recital 26 on pseudonymisation
    in one sentence.
    """
    raise NotImplementedError("Lab 5, Part A, task 3")


def remap_uid(original, uid_map, secret):
    """STUB 2. One original UID in, one new UID out, consistently.

    Returns a pydicom UID under the 2.25 arc, and records the pair in uid_map,
    which is a plain dict of {original: new} shared by the whole run.

    The contract:

      called twice with the same original and the same uid_map, it returns the
      same new UID the second time, without computing anything

      two different originals never collide

      the new UID is at most 64 characters, because that is the length limit
      on VR UI and a longer one is not a UID

      the new UID is under 2.25, so it cannot collide with a real root

    Yours to decide:

      whether the new UID is derived from the original (deterministic, so two
      runs of your own code agree) or drawn at random and only kept in the map
      (so that nothing about the original survives in the new value)

      what happens when original is None or empty. Returning a new UID for an
      absent UID invents structure that was not there

    uid_from_int below turns an integer into a well-formed 2.25 UID. The
    integer is yours.
    """
    raise NotImplementedError("Lab 5, Part A, task 4")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def uid_from_int(n):
    """A well-formed UID under the 2.25 arc, from a non-negative integer.

    2.25 is the UUID branch: the component after it is a UUID written as a
    single decimal number. Anything up to 128 bits fits in the 64-character
    limit of VR UI with room to spare.
    """
    n = int(n) % (2 ** 128)
    out = UID("2.25.%d" % n)
    if len(out) > 64:
        raise ValueError("UID longer than 64 characters: %s" % out)
    return out


def keyed_digest(secret, *parts):
    """HMAC-SHA256 over the parts, as hex. The key is the secret.

    HMAC and not a plain hash of secret + value, because the plain
    construction has a length-extension problem and because HMAC is the thing
    every reviewer recognises. The parts are joined with a separator that
    cannot appear in a DICOM UID or a hospital number, so that ("AB", "C") and
    ("A", "BC") do not produce the same digest.
    """
    key = str(secret).encode("utf-8")
    msg = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def make_secret(passphrase):
    """Turn a passphrase typed in the notebook into the run's secret.

    Not a key derivation function. A real one is scrypt or Argon2 with a salt
    and a work factor, and the reason this is three lines instead is that the
    lab needs every student in the room to land on the same output from the
    same passphrase. Say so in your report if you use it.
    """
    return hashlib.sha256(("hy489:%d:%s" % (SEED, passphrase)).encode()).hexdigest()


def save_link_table(rows, path):
    """Write the key.

    The link table is the thing that makes the release pseudonymous instead of
    anonymous. It goes somewhere the release does not, held by somebody the
    recipient is not, and it is deleted when the retention period says so.
    Writing it next to the images is the most common way this goes wrong.
    """
    fields = ["pseudonym", "patient_id", "cohort_id", "link_status",
              "instances", "note"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return path


def load_link_table(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save_uid_map(uid_map, path):
    """The UID map is part of the key. Same rules as the link table."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["original_uid", "new_uid"])
        for k in sorted(uid_map):
            w.writerow([k, uid_map[k]])
    return path
