#!/usr/bin/env python3
"""HY-489 Week 3 · Hands-on A — read a live FHIR server.

Every call here is a GET. Safe to run repeatedly; writes nothing.

    python3 handson_a.py
    python3 handson_a.py --base http://localhost:8080/fhir
"""
from __future__ import annotations

import argparse
import requests

TIMEOUT = 30
JSON = "application/fhir+json"


def get(base: str, path: str, **params) -> dict:
    """GET and return parsed JSON.

    Note this does not raise on a FHIR error: the server returns an
    OperationOutcome, which is still JSON. Check resourceType on the result
    rather than assuming success.
    """
    r = requests.get(f"{base}/{path}", params=params or None,
                     headers={"Accept": JSON}, timeout=TIMEOUT)
    return r.json()


def fetch_all(base: str, path: str, limit: int = 200, **params) -> list[dict]:
    """Follow link rel=next until exhausted or `limit` resources collected.

    Drops entries with search.mode == "include", so what comes back is the
    matches and nothing else. This is the single most common source of a wrong
    answer in this week's mini-lab.
    """
    url, out = f"{base}/{path}", []
    while url and len(out) < limit:
        b = requests.get(url, params=params or None,
                         headers={"Accept": JSON}, timeout=TIMEOUT).json()
        params = None                       # the next url already carries them
        for e in b.get("entry", []) or []:
            if e.get("search", {}).get("mode") == "include":
                continue
            if "resource" in e:
                out.append(e["resource"])
        url = next((l["url"] for l in b.get("link", []) or []
                    if l.get("relation") == "next"), None)
    return out[:limit]


def main(base: str) -> None:
    print(f"server: {base}\n")

    # ---------------------------------------------------------------- 1
    print("1. The contract")
    cs = get(base, "metadata")
    print("   fhirVersion:", cs.get("fhirVersion"))
    print("   software   :", cs.get("software", {}).get("name"))
    for res in cs.get("rest", [{}])[0].get("resource", []):
        if res.get("type") == "Observation":
            print("   Observation interactions:",
                  [i["code"] for i in res.get("interaction", [])])
            names = sorted(sp["name"] for sp in res.get("searchParam", []))
            print("   Observation search params:", names[:12], "...")
            break
    print()

    # ---------------------------------------------------------------- 2
    print("2. One resource")
    pt = get(base, "Patient/example")
    if pt.get("resourceType") == "OperationOutcome":
        print("   the example patient is not on this server; skipping")
    else:
        print("   id         :", pt.get("id"))
        print("   versionId  :", pt.get("meta", {}).get("versionId"))
        print("   gender     :", pt.get("gender"))
        print("   identifiers:", len(pt.get("identifier", [])))
    print()

    # ---------------------------------------------------------------- 3
    print("3. A search, and the number everybody gets wrong")
    b = get(base, "Patient", gender="female", birthdate="ge1990-01-01", _count=20)
    print("   resourceType :", b.get("resourceType"), "| type:", b.get("type"))
    print("   total        :", b.get("total"), " <- how many MATCHED")
    print("   len(entry)   :", len(b.get("entry", [])), " <- how many you RECEIVED")
    print("   has next page:", any(l.get("relation") == "next" for l in b.get("link", [])))
    print()

    # ---------------------------------------------------------------- 4
    print("4. _include changes the Bundle, not the match set")
    raw = get(base, "Observation", patient="example",
              _include="Observation:patient", _count=20)
    entries = raw.get("entry", [])
    modes = {}
    for e in entries:
        m = e.get("search", {}).get("mode", "?")
        modes[m] = modes.get(m, 0) + 1
    print("   entries by search.mode:", modes or "(none)")
    print("   naive count  :", len(entries))
    print("   correct count:", modes.get("match", 0))
    print()

    # ---------------------------------------------------------------- 5
    print("5. Paging, done properly")
    obs = fetch_all(base, "Observation", limit=120,
                    code="http://loinc.org|2093-3", _count=50)
    print(f"   collected {len(obs)} observations across pages")
    with_value = sum(1 for o in obs if "valueQuantity" in o)
    print(f"   of those, {with_value} carry a valueQuantity")
    print()

    # ---------------------------------------------------------------- 6
    print("6. The Week 5 preview: coded, or just text?")
    conds = fetch_all(base, "Condition", limit=100, _count=50)
    coded = sum(1 for c in conds if c.get("code", {}).get("coding"))
    text_only = sum(1 for c in conds
                    if not c.get("code", {}).get("coding") and c.get("code", {}).get("text"))
    print(f"   {len(conds)} conditions: {coded} with a coding, {text_only} text only")
    print("   A CodeableConcept with text and no coding is legal FHIR and useless")
    print("   for analysis. You cannot group it, map it or count it reliably.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://hapi.fhir.org/baseR4")
    base = ap.parse_args().base
    try:
        main(base)
    except requests.exceptions.RequestException as e:
        print(f"\nCould not reach {base}")
        print(f"  {type(e).__name__}: {e}")
        print()
        print("Three things to try, in order:")
        print("  1. Check the URL. It should end in /baseR4 with no trailing slash.")
        print("  2. The public server may be down or slow. It happens often.")
        print("  3. Run your own, which takes about a minute:")
        print("       docker run -p 8080:8080 hapiproject/hapi:latest")
        print("       python3 handson_a.py --base http://localhost:8080/fhir")
        raise SystemExit(1)
