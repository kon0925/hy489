"""HY-489 Lab 2 - map the Lab 1 CSV rows to FHIR R4 resources.

This is the graded part. Fill in the four functions below.

Each one takes a single pandas Series (one row of the CSV) and returns a
fhir.resources model. Raise nothing: if a row cannot be mapped, let the
ValidationError propagate so the caller can record it. Do NOT swallow it.

Run `python -m pytest` is not required; the notebook exercises these.
"""
from __future__ import annotations

import pandas as pd
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter
from fhir.resources.identifier import Identifier
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference

# --------------------------------------------------------------------------
# Change this to your own namespace. Use your student number so that your
# resources can be found on a shared server. Both partners: pick one.
# --------------------------------------------------------------------------
SYSTEM = "http://csd.uoc.gr/hy489/2026/AM0000"

SNOMED = "http://snomed.info/sct"
LOINC = "http://loinc.org"
UCUM = "http://unitsofmeasure.org"
V3_ACTCODE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"

GENDER = {"M": "male", "F": "female"}

# Synthea ENCOUNTERCLASS -> v3-ActCode. Extend it if your data has more.
ENCOUNTER_CLASS = {
    "ambulatory": "AMB",
    "outpatient": "AMB",
    "emergency": "EMER",
    "inpatient": "IMP",
    "wellness": "AMB",
    "urgentcare": "AMB",
}


def nn(value):
    """pandas NaN/NaT -> None. Use this on every optional field.

    This single helper prevents the most common failure in this lab.
    """
    return None if value is None or pd.isna(value) else value


def ident(value) -> list[Identifier]:
    """The business identifier that lets you find this resource again."""
    return [Identifier(system=SYSTEM, value=str(value))]


# --------------------------------------------------------------------------
# TODO 1
# --------------------------------------------------------------------------
def to_patient(row: pd.Series) -> Patient:
    """patients.csv -> Patient.

    Map: Id -> identifier, GENDER -> gender, BIRTHDATE -> birthDate.
    Do not map SSN, DRIVERS, PASSPORT, LAT or LON. Be ready to say why.

    Remember birthDate is a FHIR `date`, not a dateTime.
    """
    raise NotImplementedError("TODO 1: build and return a Patient")


# --------------------------------------------------------------------------
# TODO 2
# --------------------------------------------------------------------------
def to_encounter(row: pd.Series, patient_ref: str) -> Encounter:
    """encounters.csv -> Encounter.

    `patient_ref` is what goes in subject.reference: either "Patient/{id}"
    once you know the server id, or a "urn:uuid:..." when you are building a
    transaction Bundle.

    Required: status, class. START/STOP become one Period.
    Note the field is `class_fhir`, because `class` is a Python keyword.
    """
    raise NotImplementedError("TODO 2: build and return an Encounter")


# --------------------------------------------------------------------------
# TODO 3
# --------------------------------------------------------------------------
def to_condition(row: pd.Series, patient_ref: str,
                 encounter_ref: str | None = None) -> Condition:
    """conditions.csv -> Condition.

    code is a CodeableConcept: a SNOMED coding built from CODE and
    DESCRIPTION, plus `text` carrying the original description.

    Required in R4: subject, and clinicalStatus if the condition is not
    entered-in-error. Decide what clinicalStatus these rows deserve and
    justify it in NOTES.md.
    """
    raise NotImplementedError("TODO 3: build and return a Condition")


# --------------------------------------------------------------------------
# TODO 4
# --------------------------------------------------------------------------
def to_observation(row: pd.Series, patient_ref: str,
                   encounter_ref: str | None = None) -> Observation:
    """observations.csv -> Observation.

    This is the interesting one. Choose value[x] from the data:

      * a number with a unit  -> valueQuantity, with UCUM in Quantity.code
      * a number, no unit     -> valueQuantity with no unit
      * a text value          -> valueCodeableConcept if you can code it,
                                 otherwise valueString

    Required: status and code. DATE becomes effectiveDateTime.
    Record in NOTES.md how many rows went down each branch.
    """
    raise NotImplementedError("TODO 4: build and return an Observation")
