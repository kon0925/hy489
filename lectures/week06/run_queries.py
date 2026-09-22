#!/usr/bin/env python3
"""Run queries.sql without the sqlite3 command-line tool.

    python3 run_queries.py                 # all of them
    python3 run_queries.py 3                # just query 3
    python3 run_queries.py --sql "SELECT 1" # your own

The sqlite3 CLI is not installed everywhere, particularly on Windows. Python's
standard library has the same database engine built in, so this file reads
queries.sql, strips the dot-commands the CLI understands and Python does not,
and prints the results in the same order.

If you do have the CLI, `sqlite3 cdm.db < queries.sql` gives you the same thing.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def split_statements(text):
    lines = [l for l in text.splitlines() if not l.startswith(".")]
    for chunk in "\n".join(lines).split(";"):
        chunk = chunk.strip()
        if chunk and not all(l.strip().startswith("--") or not l.strip()
                             for l in chunk.splitlines()):
            yield chunk


def show(cur):
    cols = [d[0] for d in cur.description] if cur.description else []
    data = cur.fetchall()
    if cols == ["q"]:                       # the section headings in queries.sql
        for row in data:
            print()
            print(row[0])
        return
    widths = [max(len(c), *(len(str(r[i])) for r in data)) if data else len(c)
              for i, c in enumerate(cols)]
    widths = [min(w, 52) for w in widths]
    print("  " + "  ".join(c.ljust(w)[:w] for c, w in zip(cols, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for row in data:
        print("  " + "  ".join(str(v).ljust(w)[:w] for v, w in zip(row, widths)))
    if not data:
        print("  (no rows)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("only", nargs="?", help="run only the query with this number")
    ap.add_argument("--db", default=os.path.join(HERE, "cdm.db"))
    ap.add_argument("--file", default=os.path.join(HERE, "queries.sql"))
    ap.add_argument("--sql", help="run this SQL instead of the file")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit("No database at %s. Run: python3 etl.py" % args.db)
    con = sqlite3.connect(args.db)

    if args.sql:
        show(con.execute(args.sql))
        con.close()
        return

    with open(args.file, encoding="utf-8") as fh:
        text = fh.read()
    current = None
    for stmt in split_statements(text):
        if "'---" in stmt:      # a section heading, possibly behind a comment
            current = stmt.split("---")[1].split(".")[0].strip()
        if args.only and current != args.only:
            continue
        try:
            show(con.execute(stmt))
        except sqlite3.Error as exc:
            print("  SQL error: %s" % exc)
    con.close()


if __name__ == "__main__":
    main()
