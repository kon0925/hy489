#!/usr/bin/env python3
"""HY-489 Week 2 · Hands-on B — a minimal HL7 v2 parser.

Fifteen lines gets you 80% of the way, which is exactly why so much bespoke
HL7 parsing exists in the wild. The remaining 20% is where the pain is, and
two pieces of it are handled here: the MSH off-by-one, and repeating segments.

Run it:
    python parse_hl7.py sample_oru.hl7
    python parse_hl7.py sample_oru_full_panel.hl7
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# The parser from the slide
# ---------------------------------------------------------------------------

def parse_hl7(raw: str) -> dict[str, list[list[str]]]:
    """Group segments by name; each segment is a list of fields.

    Segments can repeat (a lab result has one OBX per analyte), so every
    segment name maps to a LIST of segments, never to a single one.
    """
    msg: dict[str, list[list[str]]] = {}
    for line in raw.strip().replace("\r\n", "\n").replace("\r", "\n").splitlines():
        if not line.strip():
            continue
        fields = line.split("|")
        msg.setdefault(fields[0], []).append(fields)
    return msg


# ---------------------------------------------------------------------------
# The MSH trap
# ---------------------------------------------------------------------------

def msh_field(msg: dict, n: int) -> str:
    """Return MSH-n, correcting for the off-by-one.

    In MSH the field separator itself is MSH-1, so after splitting on "|" the
    element at index k holds MSH-(k+1). Every other segment is off by nothing.
    Real parsers special-case this. So does this one.
    """
    seg = msg["MSH"][0]
    if n == 1:
        return "|"
    return seg[n - 1]


def comp(field: str, n: int, sep: str = "^") -> str:
    """Component n (1-based) of a field, or '' if absent."""
    parts = field.split(sep)
    return parts[n - 1] if len(parts) >= n else ""


# ---------------------------------------------------------------------------
# Pulling out what the schema needs
# ---------------------------------------------------------------------------

def patient(msg: dict) -> dict:
    pid = msg["PID"][0]
    return {
        "patient_id":  comp(pid[3], 1),          # PAT-1
        "family_name": comp(pid[5], 1),          # PAPADAKI
        "given_name":  comp(pid[5], 2),          # MARIA
        "birth_date":  hl7_date(pid[7]),         # 1984-03-11
        "sex":         {"F": "female", "M": "male"}.get(pid[8], None),
    }


def order(msg: dict) -> dict:
    obr = msg["OBR"][0]
    return {
        "order_id":    obr[2],                   # ORD-7, the placer order number
        "filler_id":   obr[3],                   # LAB-9987, the lab's own number
        "code":        comp(obr[4], 1),          # 24331-1
        "code_system": comp(obr[4], 3),          # LN
        "display":     comp(obr[4], 2),          # Lipid panel
        "ordered_ts":  hl7_ts(obr[7]),
    }


def observations(msg: dict) -> list[dict]:
    """One dict per OBX. Note this returns a LIST: a panel has several."""
    out = []
    for obx in msg.get("OBX", []):
        value_type = obx[2]                      # NM numeric, ST string, CE coded
        raw_value = obx[5]
        low, high = parse_range(obx[7] if len(obx) > 7 else "")
        out.append({
            "code":         comp(obx[3], 1),
            "code_system":  comp(obx[3], 3),
            "display":      comp(obx[3], 2),
            "value_type":   value_type,
            "value_num":    float(raw_value) if value_type == "NM" and raw_value else None,
            "value_text":   raw_value if value_type != "NM" else None,
            "unit":         obx[6] if len(obx) > 6 else "",
            "ref_low":      low,
            "ref_high":     high,
            "flag":         obx[8] if len(obx) > 8 else "",     # H high, L low, A abnormal
            "status":       obx[11] if len(obx) > 11 else "",   # F final, C correction, P preliminary
            "effective_ts": hl7_ts(obx[14]) if len(obx) > 14 else None,
        })
    return out


# ---------------------------------------------------------------------------
# The small conversions that are never as simple as they look
# ---------------------------------------------------------------------------

def hl7_date(v: str) -> str | None:
    """YYYYMMDD -> YYYY-MM-DD."""
    return f"{v[0:4]}-{v[4:6]}-{v[6:8]}" if len(v) >= 8 else None


def hl7_ts(v: str) -> str | None:
    """YYYYMMDDHHMMSS -> YYYY-MM-DD HH:MM:SS.

    Note what is missing: a timezone. HL7 v2 allows an offset and most senders
    omit it, so you are storing a local time whose locality you have to know
    out of band. This is a real and common source of one-hour errors.
    """
    if len(v) < 8:
        return None
    d = hl7_date(v)
    t = f"{v[8:10] or '00'}:{v[10:12] or '00'}:{v[12:14] or '00'}"
    return f"{d} {t}"


def parse_range(v: str) -> tuple[float | None, float | None]:
    """'<200' -> (None, 200). '>40' -> (40, None). '3.5-5.1' -> (3.5, 5.1)."""
    v = (v or "").strip()
    try:
        if v.startswith("<"):
            return None, float(v[1:])
        if v.startswith(">"):
            return float(v[1:]), None
        if "-" in v:
            lo, hi = v.split("-", 1)
            return float(lo), float(hi)
    except ValueError:
        pass
    return None, None


# ---------------------------------------------------------------------------

def main(path: str) -> None:
    msg = parse_hl7(Path(path).read_text(encoding="utf-8"))

    print("segments:", {k: len(v) for k, v in msg.items()})
    print()
    print("message type :", msh_field(msg, 9))
    print("sending app  :", msh_field(msg, 3))
    print("sent at      :", hl7_ts(msh_field(msg, 7)))
    print()
    print("patient:", patient(msg))
    print()
    print("order  :", order(msg))
    print()
    for o in observations(msg):
        print(f"  {o['code']:<10}{str(o['value_num'] or o['value_text']):<24}"
              f"{o['unit']:<8}{o['flag']:<3}{o['status']}")
    print()
    print("Note: nothing in this message carries recorded_ts. That is YOUR")
    print("transaction time, the moment your system received it, and only you")
    print("can record it.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample_oru.hl7")
