#!/usr/bin/env python3
"""HY-489 Week 2 · Hands-on B — SOLUTION to mini-lab B task 3.

From pipes to rows: parse an ORU^R01 and load its results into the Monday
schema, handling the correction case.

    python load_to_db.py                 # builds week02.db and loads both messages
"""
from __future__ import annotations

import sqlite3
import datetime as dt
from pathlib import Path

from parse_hl7 import parse_hl7, patient, order, observations

HERE = Path(__file__).parent
DB = HERE / "week02.db"


def visit_number(msg: dict) -> str | None:
    """PV1-19, the visit number, which is our encounter_id.

    Written defensively on purpose. PV1-19 should be at index 19, but senders
    routinely emit one pipe too few or too many in the long run of empty fields
    before it, so a hard-coded index breaks on the second hospital you connect.
    Try the spec position, then fall back to the last non-empty field.

    This is the HL7 v2 optionality problem from Part 4, in four lines of code.
    """
    pv1 = msg.get("PV1", [[]])[0]
    if len(pv1) > 19 and pv1[19].strip():
        return pv1[19].split("^")[0]
    tail = [f for f in pv1 if f.strip()]
    return tail[-1].split("^")[0] if tail else None


def now() -> str:
    """recorded_ts: the moment OUR system received the message.

    This is mini-lab B task 4. Nothing in the message carries it. The message
    has MSH-7, which is when the SENDER built it, and that is not the same
    thing: a message can sit in a queue for hours. If you need the sender's
    time as well, store both.
    """
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def load(conn: sqlite3.Connection, path: Path) -> None:
    msg = parse_hl7(path.read_text(encoding="utf-8"))
    pat, ordr = patient(msg), order(msg)
    enc_id = visit_number(msg)

    cur = conn.cursor()

    for i, obs in enumerate(observations(msg), start=1):
        # Task 5: a second ORU arrives with the same OBR but a corrected value.
        # OBX-11 tells us: F is final, C is a correction, P is preliminary.
        is_correction = obs["status"] == "C"

        prior = None
        if is_correction:
            cur.execute(
                "SELECT observation_id FROM observation "
                "WHERE order_id = ? AND code = ? "
                "  AND NOT EXISTS (SELECT 1 FROM observation n "
                "                  WHERE n.supersedes = observation.observation_id) "
                "ORDER BY recorded_ts DESC LIMIT 1",
                (ordr["order_id"], obs["code"]),
            )
            row = cur.fetchone()
            prior = row[0] if row else None
            if prior is None:
                # A correction for something we never received. Do not silently
                # insert it as if it were final: flag it.
                print(f"  WARNING: correction for {obs['code']} has no prior result")

        obs_id = f"OBS-{path.stem}-{i}"
        cur.execute(
            "INSERT OR REPLACE INTO observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (obs_id, enc_id, ordr["order_id"], obs["code"], "LOINC",
             obs["value_num"], obs["unit"] or None,
             obs["ref_low"], obs["ref_high"],
             obs["effective_ts"], now(),
             "amended" if is_correction else "final",
             prior),
        )
        print(f"  {obs_id:<28}{obs['code']:<10}{obs['value_num']} "
              f"{'(supersedes ' + prior + ')' if prior else ''}")

    conn.commit()


def main() -> None:
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript((HERE.parent / "sql" / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript((HERE.parent / "sql" / "seed.sql").read_text(encoding="utf-8"))
    # seed.sql already inserted OBS-2; remove it so the message load is the
    # only source of truth for ORD-7 in this demo
    conn.execute("DELETE FROM observation WHERE observation_id = 'OBS-2'")
    conn.commit()

    print("loading sample_oru.hl7 (the original result)")
    load(conn, HERE / "sample_oru.hl7")
    print()
    print("loading sample_oru_corrected.hl7 (the correction)")
    load(conn, HERE / "sample_oru_corrected.hl7")
    print()

    print("current view, nothing superseded:")
    for r in conn.execute(
        "SELECT observation_id, code, value_num, status, supersedes FROM observation o "
        "WHERE NOT EXISTS (SELECT 1 FROM observation n WHERE n.supersedes = o.observation_id) "
        "  AND o.status <> 'entered-in-error'"):
        print("  ", r)

    print()
    print("full history, including what was superseded:")
    for r in conn.execute(
        "SELECT observation_id, code, value_num, status, recorded_ts, supersedes "
        "FROM observation ORDER BY recorded_ts"):
        print("  ", r)
    conn.close()


if __name__ == "__main__":
    main()
