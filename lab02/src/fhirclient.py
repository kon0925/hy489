"""Minimal FHIR REST helpers for HY-489 Lab 2.

These are written for you. Use them rather than calling requests directly:
they set the right Content-Type, always pass a timeout, and handle paging.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

import requests

JSON_CT = "application/fhir+json"
TIMEOUT = 30


def get_json(url: str, params: dict | None = None, timeout: int = TIMEOUT) -> dict:
    """GET and return parsed JSON. Raises for transport errors only.

    A FHIR error still returns JSON (an OperationOutcome), so check
    resourceType on the result rather than assuming success.
    """
    r = requests.get(url, params=params, headers={"Accept": JSON_CT}, timeout=timeout)
    return r.json()


def fetch_all(url: str, params: dict | None = None, limit: int = 500,
              include_includes: bool = False) -> list[dict]:
    """Follow Bundle link rel=next until exhausted or `limit` resources collected.

    By default entries with search.mode == "include" are dropped, so the count
    you get back is the number of matches, not matches plus included targets.
    """
    out: list[dict] = []
    while url and len(out) < limit:
        b = get_json(url, params)
        params = None  # the next url already carries the query
        for e in b.get("entry", []) or []:
            mode = e.get("search", {}).get("mode")
            if mode == "include" and not include_includes:
                continue
            if "resource" in e:
                out.append(e["resource"])
        url = next((l["url"] for l in b.get("link", []) or []
                    if l.get("relation") == "next"), None)
    return out[:limit]


def validate_resource(base: str, resource: Any, rtype: str | None = None) -> list[dict]:
    """POST to {base}/{Type}/$validate and return the list of issues.

    `resource` may be a fhir.resources model, a dict, or a JSON string.
    """
    body, rtype = _as_json(resource, rtype)
    r = requests.post(f"{base}/{rtype}/$validate", data=body,
                      headers={"Content-Type": JSON_CT}, timeout=TIMEOUT)
    return r.json().get("issue", [])


def post_resource(base: str, resource: Any, rtype: str | None = None,
                  if_none_exist: str | None = None) -> tuple[int, dict]:
    """Create a resource. Pass `if_none_exist` (a search string) to make it
    conditional, so re-running a load does not create duplicates.

    Returns (status_code, parsed body).
    """
    body, rtype = _as_json(resource, rtype)
    headers = {"Content-Type": JSON_CT}
    if if_none_exist:
        headers["If-None-Exist"] = if_none_exist
    r = requests.post(f"{base}/{rtype}", data=body, headers=headers, timeout=TIMEOUT)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {}


def post_bundle(base: str, bundle: dict, timeout: int = 60) -> dict:
    """POST a transaction or batch Bundle to the base URL."""
    r = requests.post(base, data=json.dumps(bundle),
                      headers={"Content-Type": JSON_CT}, timeout=timeout)
    return r.json()


def transaction_bundle(entries: Iterable[tuple[str, dict, str, str | None]]) -> dict:
    """Build a transaction Bundle.

    Each entry is (full_url, resource_dict, resource_type, if_none_exist_or_None).
    full_url is normally a urn:uuid: value that other resources reference.
    """
    out = {"resourceType": "Bundle", "type": "transaction", "entry": []}
    for full_url, resource, rtype, ine in entries:
        request = {"method": "POST", "url": rtype}
        if ine:
            request["ifNoneExist"] = ine
        out["entry"].append({"fullUrl": full_url, "resource": resource, "request": request})
    return out


def issues_summary(issues: list[dict]) -> str:
    """One line per issue: severity, code and the human-readable diagnostics."""
    if not issues:
        return "(no issues returned)"
    return "\n".join(
        f"{i.get('severity','?'):<12}{i.get('code','?'):<20}{i.get('diagnostics','')}"
        for i in issues
    )


def _as_json(resource: Any, rtype: str | None) -> tuple[str, str]:
    if isinstance(resource, str):
        body = resource
        rtype = rtype or json.loads(resource)["resourceType"]
    elif isinstance(resource, dict):
        body = json.dumps(resource)
        rtype = rtype or resource["resourceType"]
    else:  # a fhir.resources model
        body = resource.json()
        rtype = rtype or resource.resource_type
    return body, rtype
