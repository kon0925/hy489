#!/usr/bin/env python3
"""HY-489 Week 3 · Hands-on B — a row becomes a Patient, then ships.

Build a FHIR resource from a CSV row, validate it locally, validate it on the
server, then create it with a conditional POST so the script is re-runnable.

    python3 handson_b.py --dry-run
    python3 handson_b.py --system http://csd.uoc.gr/hy489/2026/AM1234

--dry-run builds and validates locally and touches no network. Use it first.

GROUND RULES: never post anything real. The synthetic data in labs/lab01/data is the
only thing you post. Everything you write to a public server is public, and
anyone can delete it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

from fhir.resources.patient import Patient
from fhir.resources.identifier import Identifier

TIMEOUT = 30
JSON_CT = "application/fhir+json"

GENDER = {"M": "male", "F": "female"}

# The data lives one folder up in the repo. No copy is kept here.
LOCAL = Path(__file__).resolve().parents[2] / "labs" / "lab01" / "data"
REMOTE = "https://raw.githubusercontent.com/kon0925/hy489/main/labs/lab01/data/"


def load_patients(n: int) -> pd.DataFrame:
    src = f"{LOCAL}/" if LOCAL.exists() else REMOTE
    print(f"reading from: {src}")
    return pd.read_csv(src + "patients.csv", parse_dates=["BIRTHDATE"]).head(n)


# ---------------------------------------------------------------------------
# A row becomes a Patient
# ---------------------------------------------------------------------------

def to_patient(row: pd.Series, system: str) -> Patient:
    """Map one CSV row to a FHIR Patient.

    Note what is NOT mapped: SSN, DRIVERS, PASSPORT, LAT, LON. The dataset is
    synthetic, but the habit is the point. Map only what your use case needs,
    and be able to justify every field you kept.

    gender is bound to a required value set, so an unrecognised code becomes
    None rather than an invented value. Absent is incomplete; invented is wrong.
    """
    return Patient(
        identifier=[Identifier(system=system, value=str(row["Id"]))],
        gender=GENDER.get(row["GENDER"]),
        birthDate=row["BIRTHDATE"].date(),
    )


# ---------------------------------------------------------------------------
# Validate, then post
# ---------------------------------------------------------------------------

def validate_on_server(base: str, resource: Patient) -> list[dict]:
    """$validate runs the server's rules without storing anything.

    It catches what the library cannot: invariants, bindings, and codes the
    server cannot resolve.
    """
    r = requests.post(f"{base}/Patient/$validate", data=resource.json(),
                      headers={"Content-Type": JSON_CT}, timeout=TIMEOUT)
    return r.json().get("issue", [])


def post_conditional(base: str, resource: Patient, system: str, key: str):
    """Create only if a resource with this identifier does not already exist.

    Without If-None-Exist, a load that fails halfway leaves duplicates behind
    and the next run adds more. On a public server that is untidy. In a hospital
    it is a safety incident.
    """
    r = requests.post(
        f"{base}/Patient", data=resource.json(),
        headers={"Content-Type": JSON_CT, "If-None-Exist": f"identifier={system}|{key}"},
        timeout=TIMEOUT)
    return r.status_code, r.headers.get("Location", ""), r


def summarise(issues: list[dict]) -> str:
    if not issues:
        return "      (no issues returned)"
    return "\n".join(
        f"      {i.get('severity','?'):<12}{i.get('code','?'):<22}{i.get('diagnostics','')}"
        for i in issues)


def main(a) -> None:
    rows = load_patients(a.count)
    print(f"building {len(rows)} Patient resources under {a.system}\n")

    built, rejected = [], []
    for _, row in rows.iterrows():
        try:
            built.append((row["Id"], to_patient(row, a.system)))
        except Exception as e:                      # noqa: BLE001
            # Collect failures with the source key. Never except: pass.
            rejected.append((row["Id"], f"{type(e).__name__}: {e}"))

    print(f"local validation: {len(built)} built, {len(rejected)} rejected")
    for key, err in rejected[:5]:
        print(f"   {key}  {err}")
    print()

    print("first resource:")
    print(json.dumps(json.loads(built[0][1].json()), indent=2))
    print()

    if a.dry_run:
        print("--dry-run: nothing was sent. Drop the flag to validate and post.")
        return

    key, pt = built[0]
    print("server-side $validate:")
    print(summarise(validate_on_server(a.base, pt)))
    print()

    print(f"posting {min(a.post, len(built))} resources with If-None-Exist")
    for key, pt in built[:a.post]:
        status, loc, _ = post_conditional(a.base, pt, a.system, key)
        print(f"   {key}  ->  {status} {loc}")
    print("   201 means created. 200 means it already existed and nothing was duplicated.")
    print()

    print("the independent check: search by your namespace")
    r = requests.get(f"{a.base}/Patient", params={"identifier": f"{a.system}|", "_count": 100},
                     headers={"Accept": JSON_CT}, timeout=TIMEOUT).json()
    print(f"   total under {a.system}: {r.get('total')}")
    print()
    print("Run this script twice. The second run creates no duplicates, because")
    print("of one HTTP header. That is the whole point of Hands-on B.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://hapi.fhir.org/baseR4")
    ap.add_argument("--system", default="http://csd.uoc.gr/hy489/2026/AM0000",
                    help="your identifier namespace. Put your student number in it.")
    ap.add_argument("--count", type=int, default=5, help="rows to build")
    ap.add_argument("--post", type=int, default=2, help="how many to actually POST")
    ap.add_argument("--dry-run", action="store_true", help="build and validate locally only")
    args = ap.parse_args()
    if not args.dry_run and args.system.endswith("AM0000"):
        raise SystemExit("Refusing to post under the default namespace. "
                         "Pass --system with your student number in it.")
    try:
        main(args)
    except requests.exceptions.RequestException as e:
        print(f"\nCould not reach {args.base}\n  {type(e).__name__}: {e}")
        print("\nRun your own server instead:")
        print("  docker run -p 8080:8080 hapiproject/hapi:latest")
        print("  python3 handson_b.py --base http://localhost:8080/fhir --system ...")
        raise SystemExit(1)
