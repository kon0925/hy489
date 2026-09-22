#!/usr/bin/env python3
"""HY-489 Week 5 · Hands-on A and B — talk to a FHIR terminology server.

Five operations, one small module. Needs network.

    python3 terminology.py --demo               # the operations, on known codes
    python3 terminology.py --validate-dataset   # check every code in labs/lab01/data

GROUND RULES: tx.fhir.org is a free community server. Be polite: sequential
requests, a timeout, and no loops over thousands of codes. If it is down, the
offline half of the hands-on (codability.py) still stands on its own.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import requests

TIMEOUT = 30
JSON = "application/fhir+json"

SCT = "http://snomed.info/sct"
LOINC = "http://loinc.org"
ICD10 = "http://hl7.org/fhir/sid/icd-10"

LOCAL = Path(__file__).resolve().parents[2] / "labs" / "lab01" / "data"
REMOTE = "https://raw.githubusercontent.com/kon0925/hy489/main/labs/lab01/data/"


# ---------------------------------------------------------------------------
# The five operations
# ---------------------------------------------------------------------------

def _params(body: dict) -> dict:
    """FHIR Parameters come back as a list of {name, value[x]}. Flatten it."""
    out = {}
    for p in body.get("parameter", []) or []:
        for k, v in p.items():
            if k.startswith("value"):
                out.setdefault(p["name"], v)
    return out


def lookup(base: str, system: str, code: str) -> dict:
    """$lookup — what is this code? Display, and whatever properties exist."""
    r = requests.get(f"{base}/CodeSystem/$lookup",
                     params={"system": system, "code": code},
                     headers={"Accept": JSON}, timeout=TIMEOUT)
    return _params(r.json()) if r.ok else {"error": r.status_code}


def subsumes(base: str, system: str, code_a: str, code_b: str) -> str:
    """$subsumes — does A subsume B, or B subsume A, or neither?

    Try it both ways round. The answer flips from subsumes to subsumed-by, and
    that asymmetry is the whole of Part 2 in one HTTP call.
    """
    r = requests.get(f"{base}/CodeSystem/$subsumes",
                     params={"system": system, "codeA": code_a, "codeB": code_b},
                     headers={"Accept": JSON}, timeout=TIMEOUT)
    return _params(r.json()).get("outcome", f"error {r.status_code}") if r.ok else f"error {r.status_code}"


def expand(base: str, value_set_url: str, filter_text: str | None = None,
           count: int = 50) -> list[tuple[str, str]]:
    """$expand — what codes are in this value set, today?

    Note 'today'. The same value set expands differently against different
    terminology versions, which is a feature and a reproducibility hazard.
    """
    params = {"url": value_set_url, "count": count}
    if filter_text:
        params["filter"] = filter_text
    r = requests.get(f"{base}/ValueSet/$expand", params=params,
                     headers={"Accept": JSON}, timeout=TIMEOUT)
    if not r.ok:
        return []
    contains = r.json().get("expansion", {}).get("contains", []) or []
    return [(c.get("code", ""), c.get("display", "")) for c in contains]


def validate_code(base: str, value_set_url: str, system: str, code: str) -> bool:
    """$validate-code — is this code permitted here?"""
    r = requests.get(f"{base}/ValueSet/$validate-code",
                     params={"url": value_set_url, "system": system, "code": code},
                     headers={"Accept": JSON}, timeout=TIMEOUT)
    return bool(_params(r.json()).get("result")) if r.ok else False


def translate(base: str, system: str, code: str, target: str) -> list[tuple[str, str]]:
    """$translate — what does this code become in that system?

    Remember Part 5: the answer is lossy and directional. A result here is a
    candidate with an equivalence, not a fact.
    """
    r = requests.get(f"{base}/ConceptMap/$translate",
                     params={"system": system, "code": code, "targetsystem": target},
                     headers={"Accept": JSON}, timeout=TIMEOUT)
    if not r.ok:
        return []
    out = []
    for p in r.json().get("parameter", []) or []:
        if p.get("name") == "match":
            rel, con = None, None
            for part in p.get("part", []) or []:
                if part.get("name") in ("equivalence", "relationship"):
                    rel = part.get("valueCode")
                if part.get("name") == "concept":
                    con = part.get("valueCoding", {})
            if con:
                out.append((con.get("code", ""), f"{con.get('display','')}  [{rel}]"))
    return out


# ---------------------------------------------------------------------------

# The implicit value set URL: a subhierarchy, without authoring a ValueSet.
def isa(concept_id: str) -> str:
    return f"{SCT}?fhir_vs=isa/{concept_id}"


def demo(base: str) -> None:
    print(f"server: {base}\n")

    print("--- $lookup: what is 59621000?")
    for k, v in lookup(base, SCT, "59621000").items():
        if k in ("name", "display", "version"):
            print(f"    {k:<10}{v}")
    print()

    print("--- $subsumes, both directions")
    print("    Hypertensive disorder vs Essential hypertension:",
          subsumes(base, SCT, "38341003", "59621000"))
    print("    the same pair, swapped              :",
          subsumes(base, SCT, "59621000", "38341003"))
    print("    That flip is why you ask the hierarchy instead of matching strings.")
    print()

    print("--- $expand: the implicit value set for a subhierarchy")
    rows = expand(base, isa("38341003"), count=15)
    for c, d in rows[:10]:
        print(f"    {c:<14}{d}")
    print(f"    ... {len(rows)} returned (capped). Nobody could enumerate these by hand.")
    print()

    print("--- $validate-code")
    for code, label in [("59621000", "Essential hypertension"), ("22298006", "Myocardial infarction")]:
        ok = validate_code(base, isa("38341003"), SCT, code)
        print(f"    {label:<28}in the hypertension value set? {ok}")
    print()

    print("--- $translate: SNOMED to ICD-10")
    matches = translate(base, SCT, "59621000", ICD10)
    if matches:
        for c, d in matches:
            print(f"    {c:<10}{d}")
    else:
        print("    no map available on this server for this pair.")
        print("    That is itself a finding: $translate only works where a")
        print("    ConceptMap has been loaded, and most public servers load few.")


def validate_dataset(base: str, data: str) -> None:
    import pandas as pd
    src = f"{data}/" if Path(data).exists() else REMOTE
    print(f"reading from: {src}\n")

    con = pd.read_csv(src + "conditions.csv")
    codes = sorted(con["CODE"].dropna().astype(str).unique())
    print(f"{len(codes)} distinct condition codes. Checking each against {base}")
    print("(sequential and slow on purpose: be polite to a shared server)\n")

    unknown = []
    for i, c in enumerate(codes, 1):
        res = lookup(base, SCT, c)
        display = res.get("display")
        if display:
            print(f"  {i:>3}. {c:<14} {display}")
        else:
            unknown.append(c)
            print(f"  {i:>3}. {c:<14} NOT FOUND")

    print()
    print(f"resolved: {len(codes) - len(unknown)} / {len(codes)}")
    if unknown:
        print("unresolved:", unknown)
        print()
        print("In a real extract this list is your most valuable output of the day.")
        print("It is the set of codes somebody invented, mistyped, or took from a")
        print("different edition, and nobody has noticed until now.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://tx.fhir.org/r4")
    ap.add_argument("--data", default=str(LOCAL))
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--validate-dataset", action="store_true")
    a = ap.parse_args()
    try:
        if a.validate_dataset:
            validate_dataset(a.base, a.data)
        else:
            demo(a.base)
    except requests.exceptions.RequestException as e:
        print(f"Could not reach {a.base}\n  {type(e).__name__}: {e}\n")
        print("tx.fhir.org is a free community server and it does go down.")
        print("The offline half of this hands-on still works:")
        print("    python3 codability.py")
        raise SystemExit(1)
