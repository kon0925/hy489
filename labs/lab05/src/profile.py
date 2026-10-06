"""The PS3.15 attribute table, as data.

WRITTEN FOR YOU. Nothing in this file is a stub. Read it before you write
anything: every decision the rest of the lab makes is a lookup into this table,
and the table is where you argue with the lab if you think it is wrong.

DICOM PS3.15 Annex E is the Attribute Confidentiality Profiles. The Basic
Application Level Confidentiality Profile is the floor: a list of attributes
and, for each one, what a conformant de-identifier does to it. Table E.1-1 is
that list. It is about five hundred rows long and most of them are attributes
no archive you meet will ever contain.

PROFILE below is a subset: every Table E.1-1 attribute that occurs in the Lab 4
archive, plus the ones that occur in almost every real archive and happen not
to be here, plus a short list of attributes the archive does contain that
Table E.1-1 does not mention at all. That last group is the interesting one.
An attribute missing from Table E.1-1 is not an attribute the standard has
cleared. It is an attribute the standard has not considered, and the decision
about it is yours.

Verified against DICOM PS3.15 edition 2026c, Annex E, on 6 October 2026.
"""

import collections

#: The action codes of Table E.1-1a, quoted from the standard.
ACTION_CODES = {
    "D": "replace with a non-zero length value that may be a dummy value and "
         "consistent with the VR",
    "Z": "replace with a zero length value, or a non-zero length value that "
         "may be a dummy value",
    "X": "remove the attribute, and if it is a sequence, remove all its items",
    "K": "keep (unchanged for non-sequence attributes, cleaned for sequences)",
    "C": "clean, that is replace with values of similar meaning known not to "
         "contain identifying information",
    "U": "replace with a non-zero length UID that is internally consistent "
         "within a set of instances",
    "Z/D": "Z unless D is required to keep the IOD conformant",
    "X/Z": "X unless Z is required to keep the IOD conformant",
    "X/D": "X unless D is required to keep the IOD conformant",
    "X/Z/D": "X unless Z or D is required to keep the IOD conformant",
    "X/Z/U*": "X unless Z or UID replacement is required to keep the IOD "
              "conformant",
}

#: The options of E.3, with their CID 7050 codes. An option adds attributes
#: back that the Basic Profile would have removed. Claiming one is a claim you
#: have to be able to defend: Retain Longitudinal Full Dates puts every date
#: back, and dates are quasi-identifiers.
OPTIONS = {
    "BASIC": ("113100", "Basic Application Confidentiality Profile"),
    "CLEAN_PIXEL_DATA": ("113101", "Clean Pixel Data Option"),
    "CLEAN_VISUAL_FEATURES": ("113102", "Clean Recognizable Visual Features Option"),
    "CLEAN_GRAPHICS": ("113103", "Clean Graphics Option"),
    "CLEAN_STRUCTURED_CONTENT": ("113104", "Clean Structured Content Option"),
    "CLEAN_DESCRIPTORS": ("113105", "Clean Descriptors Option"),
    "RETAIN_FULL_DATES": ("113106", "Retain Longitudinal Temporal Information Full Dates Option"),
    "RETAIN_MODIFIED_DATES": ("113107", "Retain Longitudinal Temporal Information Modified Dates Option"),
    "RETAIN_PATIENT_CHARACTERISTICS": ("113108", "Retain Patient Characteristics Option"),
    "RETAIN_DEVICE_IDENTITY": ("113109", "Retain Device Identity Option"),
    "RETAIN_UIDS": ("113110", "Retain UIDs Option"),
    "RETAIN_SAFE_PRIVATE": ("113111", "Retain Safe Private Option"),
    "RETAIN_INSTITUTION_IDENTITY": ("113112", "Retain Institution Identity Option"),
}

#: One row of the profile.
#:   tag       (group, element)
#:   keyword   the pydicom keyword, which is how you address it in code
#:   action    the Basic Profile action code from Table E.1-1, or "K" for a
#:             row this lab added
#:   source    "E.1-1" if the row was read off the standard, "E.1-1?" if it
#:             came from a transcription of the standard that could not be
#:             checked against the standard itself (see the note below),
#:             "local" if this lab decided
#:   note      why the row is here, or what it costs
# ---------------------------------------------------------------------------
# A caveat about this table, which is also the point of it
# ---------------------------------------------------------------------------
#
# Fourteen rows below are marked "E.1-1?" instead of "E.1-1". Those action
# codes were taken from a third-party transcription of Table E.1-1 and could
# not be checked against the standard itself: the published HTML of Annex E
# runs to about 210,000 characters, the table is alphabetical by attribute
# name, and every tool available when this lab was written truncated the page
# before reaching S. Nineteen attributes appear in both the standard and the
# transcription and all nineteen agree, which is reassuring and is not proof.
#
# This is not an apology. It is the thing the lab is about. A de-identifier is
# exactly as correct as the copy of the table it was built from, nobody
# downstream can see which copy that was, and the output looks identical
# either way. Run profile.sources() and you can at least see which rows carry
# the risk. Most real de-identification code cannot tell you that, because
# nobody recorded it.
#
# If you are the TA: check these fourteen against a PDF of PS3.15 before the
# session and correct them in place. The lab does not depend on their exact
# values, and saying so out loud is worth more than quietly being right.

Attribute = collections.namedtuple("Attribute", "tag keyword action source note")

PROFILE = [
    # ---- identifiers of the person -------------------------------------
    Attribute((0x0010, 0x0010), "PatientName", "Z", "E.1-1",
              "the name. Zero length is conformant; this lab writes a "
              "pseudonym instead, which is the D half of Z/D applied one row "
              "down and kept consistent here."),
    Attribute((0x0010, 0x0020), "PatientID", "Z/D", "E.1-1",
              "was Z until the 2024b edition and is Z/D now. Z/D is what lets "
              "you put a pseudonym here instead of emptying it."),
    Attribute((0x0010, 0x0021), "IssuerOfPatientID", "X", "E.1-1",
              "the namespace the ID belongs to. Keeping it narrows a "
              "pseudonym to one hospital's ID space."),
    Attribute((0x0010, 0x0030), "PatientBirthDate", "Z", "E.1-1",
              "Week 8: postcode plus full birth date plus sex is unique for "
              "1,170 of the 1,174 cohort patients."),
    Attribute((0x0010, 0x0040), "PatientSex", "Z", "E.1-1",
              "the Retain Patient Characteristics Option puts this back, and "
              "the uniqueness arithmetic is the reason that option is a "
              "decision and not a formality."),
    Attribute((0x0010, 0x1000), "OtherPatientIDs", "X", "E.1-1", ""),
    Attribute((0x0010, 0x1010), "PatientAge", "X", "E.1-1",
              "Retain Patient Characteristics keeps it. An age in years is a "
              "coarser quasi-identifier than a birth date and still a "
              "quasi-identifier."),
    Attribute((0x0010, 0x1040), "PatientAddress", "X", "E.1-1", ""),
    Attribute((0x0010, 0x2154), "PatientTelephoneNumbers", "X", "E.1-1", ""),
    Attribute((0x0010, 0x2160), "EthnicGroup", "X", "E.1-1",
              "GDPR Article 9 special category. Week 8 slide 15 said the Lab 1 "
              "cohort's single-valued RACE and ETHNICITY columns are a "
              "generator artefact and that nobody should generalise from them."),
    Attribute((0x0010, 0x2180), "Occupation", "X", "E.1-1", ""),
    Attribute((0x0010, 0x21B0), "AdditionalPatientHistory", "X", "E.1-1",
              "free text written by a human. Week 8: free text is the field "
              "nobody can certify."),
    Attribute((0x0010, 0x4000), "PatientComments", "X", "E.1-1", ""),

    # ---- identifiers of other people ------------------------------------
    Attribute((0x0008, 0x0090), "ReferringPhysicianName", "Z", "E.1-1?",
              "a clinician is a person too, and a referring physician plus a "
              "date plus a body part is a small population."),
    Attribute((0x0008, 0x1048), "PhysiciansOfRecord", "X", "E.1-1", ""),
    Attribute((0x0008, 0x1050), "PerformingPhysicianName", "X", "E.1-1", ""),
    Attribute((0x0008, 0x1070), "OperatorsName", "X/Z/D", "E.1-1", ""),
    Attribute((0x0040, 0xA075), "VerifyingObserverName", "D", "E.1-1?",
              "the radiologist who signed the report. D and not X, because a "
              "verified SR with no verifier is not a conformant SR."),
    Attribute((0x0040, 0xA027), "VerifyingOrganization", "D", "E.1-1?", ""),

    # ---- the accession and the order ------------------------------------
    Attribute((0x0008, 0x0050), "AccessionNumber", "Z", "E.1-1",
              "the order number. It is the join key back to the RIS, which is "
              "exactly why it goes."),
    Attribute((0x0020, 0x0010), "StudyID", "Z", "E.1-1?", ""),
    Attribute((0x0038, 0x0300), "CurrentPatientLocation", "X", "E.1-1",
              "the ward. A ward plus a date is a very small population."),
    Attribute((0x0040, 0x0254), "PerformedProcedureStepDescription", "X", "E.1-1", ""),
    Attribute((0x0032, 0x1060), "RequestedProcedureDescription", "X/Z", "E.1-1", ""),

    # ---- dates and times -------------------------------------------------
    Attribute((0x0008, 0x0012), "InstanceCreationDate", "X/D", "E.1-1", ""),
    Attribute((0x0008, 0x0013), "InstanceCreationTime", "X/Z/D", "E.1-1", ""),
    Attribute((0x0008, 0x0020), "StudyDate", "Z", "E.1-1?",
              "zero length by default. Two studies of one patient 49 days "
              "apart become two studies of one patient on no date at all."),
    Attribute((0x0008, 0x0021), "SeriesDate", "X/D", "E.1-1?", ""),
    Attribute((0x0008, 0x0022), "AcquisitionDate", "X/Z", "E.1-1", ""),
    Attribute((0x0008, 0x0023), "ContentDate", "Z/D", "E.1-1", ""),
    Attribute((0x0008, 0x0030), "StudyTime", "Z", "E.1-1?", ""),
    Attribute((0x0008, 0x0031), "SeriesTime", "X/D", "E.1-1?", ""),
    Attribute((0x0008, 0x0032), "AcquisitionTime", "X/Z", "E.1-1", ""),
    Attribute((0x0008, 0x0033), "ContentTime", "Z/D", "E.1-1", ""),

    # ---- the institution and the machine ---------------------------------
    Attribute((0x0008, 0x0080), "InstitutionName", "X/Z/D", "E.1-1",
              "the Retain Institution Identity Option keeps it. In a country "
              "with five hospitals doing a procedure, the institution is a "
              "quasi-identifier."),
    Attribute((0x0008, 0x0081), "InstitutionAddress", "X", "E.1-1", ""),
    Attribute((0x0008, 0x1040), "InstitutionalDepartmentName", "X", "E.1-1", ""),
    Attribute((0x0008, 0x1010), "StationName", "X/Z/D", "E.1-1?",
              "names the console. With a date it names a shift, and a shift "
              "has a short list of patients on it."),
    Attribute((0x0018, 0x1000), "DeviceSerialNumber", "X/Z/D", "E.1-1", ""),

    # ---- free text that describes the examination ------------------------
    Attribute((0x0008, 0x1030), "StudyDescription", "X", "E.1-1?",
              "Lab 4 found four spellings of one protocol in this field. The "
              "Basic Profile removes it and the Clean Descriptors Option is "
              "what you claim if you want it back scrubbed."),
    Attribute((0x0008, 0x103E), "SeriesDescription", "X", "E.1-1?", ""),
    Attribute((0x0008, 0x2111), "DerivationDescription", "X", "E.1-1", ""),
    Attribute((0x0018, 0x1030), "ProtocolName", "X/D", "E.1-1", ""),
    Attribute((0x0020, 0x4000), "ImageComments", "X", "E.1-1", ""),

    # ---- structured content ----------------------------------------------
    Attribute((0x0040, 0xA730), "ContentSequence", "D", "E.1-1",
              "D on the whole sequence. The Basic Profile does reach the "
              "report's free text, by replacing the entire report with a "
              "dummy. Keeping a usable report means claiming the Clean "
              "Structured Content Option and scrubbing item by item."),
    Attribute((0x0040, 0xA073), "VerifyingObserverSequence", "D", "E.1-1", ""),
    Attribute((0x0040, 0xA123), "PersonName", "D", "E.1-1",
              "a PN inside a content item. Removing (0010,0010) does not "
              "touch it."),
    Attribute((0x0070, 0x0001), "GraphicAnnotationSequence", "D", "E.1-1",
              "burned-in text that is not burned in: a presentation state can "
              "carry the name as an overlay object."),

    # ---- UIDs -------------------------------------------------------------
    Attribute((0x0008, 0x0018), "SOPInstanceUID", "U", "E.1-1",
              "U, not X. An instance with no SOPInstanceUID is not an "
              "instance. The new value has to be consistent everywhere the "
              "old one appeared."),
    Attribute((0x0020, 0x000D), "StudyInstanceUID", "U", "E.1-1?", ""),
    Attribute((0x0020, 0x000E), "SeriesInstanceUID", "U", "E.1-1?", ""),
    Attribute((0x0020, 0x0052), "FrameOfReferenceUID", "U", "E.1-1",
              "ties slices into one coordinate system. Remap it per instance "
              "and the stack falls apart."),
    Attribute((0x0008, 0x1155), "ReferencedSOPInstanceUID", "U", "E.1-1",
              "the reason a UID map has to be one map for the whole archive "
              "and not one map per file."),
    Attribute((0x0008, 0x2112), "SourceImageSequence", "X/Z/U*", "E.1-1?",
              "X/Z/U* is the only code with a star in it. The star means the "
              "sequence may be kept if its UIDs are remapped."),

    # ---- rows this lab added, which Table E.1-1 does not mention ---------
    Attribute((0x0008, 0x0060), "Modality", "K", "local",
              "not in Table E.1-1. Kept: a dataset with no modality cannot be "
              "used for anything and CT is not identifying."),
    Attribute((0x0008, 0x0070), "Manufacturer", "K", "local",
              "not in Table E.1-1, which surprises people. Manufacturer and "
              "ManufacturerModelName are absent from the table; StationName "
              "and DeviceSerialNumber are in it. The standard has drawn a "
              "line between the model of machine and the particular machine."),
    Attribute((0x0018, 0x0015), "BodyPartExamined", "K", "local",
              "not in Table E.1-1. Kept: Lab 4 showed this field plus "
              "Modality is the only reliable statement of what the "
              "examination was."),
    Attribute((0x0028, 0x0301), "BurnedInAnnotation", "K", "local",
              "not in Table E.1-1. Kept and then rewritten by pixels.py: the "
              "flag has to say NO after the pixels have been blanked, and has "
              "to keep saying YES if they have not."),
    Attribute((0x0018, 0x5100), "PatientPosition", "K", "local",
              "not in Table E.1-1. HFS is not identifying and a reconstruction "
              "needs it."),
    Attribute((0x0008, 0x0064), "ConversionType", "K", "local",
              "not in Table E.1-1. WSD says this object came off a screen, "
              "which is the hint that it may have pixels drawn into it."),
]

#: How this lab resolves each combination code. The standard gives a range and
#: the choice inside it is the de-identifier's. These are this lab's choices,
#: and two of them are what the written part of the submission has to defend.
#:
#:   PatientID      Z/D   -> D    a pseudonym, so the archive stays joinable
#:                                to itself and to the link table
#:   everything     X/Z   -> X    remove. Z would leave an empty tag that a
#:   else           X/D   -> X    downstream tool reads as "measured and
#:                  X/Z/D -> X    empty" instead of "never released"
#:                  Z/D   -> Z
#:                  X/Z/U*-> X
RESOLUTION = {
    "Z/D": "Z",
    "X/Z": "X",
    "X/D": "X",
    "X/Z/D": "X",
    "X/Z/U*": "X",
}

#: The one exception to RESOLUTION, stated as an exception so that it is
#: visible instead of buried in a branch.
RESOLUTION_OVERRIDE = {
    "PatientID": "D",
}


def resolve(entry):
    """The single action code this profile applies to one attribute.

    The combination codes are a range the standard allows. This function is
    where the range becomes one answer, and the answer is a decision somebody
    has to be able to defend in a data protection impact assessment.
    """
    if entry.keyword in RESOLUTION_OVERRIDE:
        return RESOLUTION_OVERRIDE[entry.keyword]
    return RESOLUTION.get(entry.action, entry.action)


def by_keyword():
    """The profile as a dict, keyed on pydicom keyword."""
    return {e.keyword: e for e in PROFILE}


def coverage(keywords):
    """Split a list of attribute keywords into covered and not covered.

    Returns (covered, uncovered). The uncovered list is the honest output of
    this function and the one to read: these are attributes the archive
    contains and this profile says nothing about. Every one of them is
    released unchanged unless somebody looks at it.
    """
    table = by_keyword()
    covered = [k for k in keywords if k in table]
    uncovered = [k for k in keywords if k not in table]
    return covered, uncovered


def describe(only=None):
    """Print the profile. Pass a list of keywords to print just those rows."""
    rows = PROFILE if only is None else [e for e in PROFILE if e.keyword in only]
    print("%-11s %-42s %-7s %-7s %s"
          % ("tag", "keyword", "E.1-1", "applied", "source"))
    print("-" * 92)
    for e in rows:
        print("(%04X,%04X) %-42s %-7s %-7s %s"
              % (e.tag[0], e.tag[1], e.keyword, e.action, resolve(e), e.source))
    print()
    print("%d attributes, %d of them from Table E.1-1 and %d added by this lab."
          % (len(rows),
             sum(1 for e in rows if e.source == "E.1-1"),
             sum(1 for e in rows if e.source == "local")))


def action_counts():
    """How many attributes get each applied action. One line for the report."""
    out = collections.Counter(resolve(e) for e in PROFILE)
    return dict(out)


def sources():
    """Where each row's action code came from, and which ones to re-check.

    Three values. "E.1-1" was read off the standard. "E.1-1?" came from a
    transcription of the standard that could not be checked against it.
    "local" is a decision this lab made, for an attribute the standard does
    not list.

    Print this before you trust anything downstream of the profile. Every
    de-identifier ever written has a version of this table inside it and
    almost none of them can tell you which rows are which.
    """
    groups = {}
    for a in PROFILE:
        groups.setdefault(a.source, []).append(a)
    order = ["E.1-1", "E.1-1?", "local"]
    label = {
        "E.1-1": "read off the standard",
        "E.1-1?": "from a transcription, NOT checked against the standard",
        "local": "this lab decided, the standard does not list the attribute",
    }
    for key in order:
        rows = groups.get(key, [])
        if not rows:
            continue
        print("%-8s %2d  %s" % (key, len(rows), label[key]))
    print()
    for a in groups.get("E.1-1?", []):
        print("  re-check  (%04X,%04X) %-32s %s"
              % (a.tag[0], a.tag[1], a.keyword, a.action))
    print()
    print("The lab does not depend on the exact codes of those %d. It depends"
          % len(groups.get("E.1-1?", [])))
    print("on what D, Z, X, K, U and C mean, and on what each one costs.")
    return groups
