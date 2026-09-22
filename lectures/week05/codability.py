#!/usr/bin/env python3
"""HY-489 Week 5 · Hands-on B — the five metrics.

Run this on any coded dataset you are ever handed, in the first hour.
Needs pandas and nothing else. No network.

    python3 codability.py
    python3 codability.py --data /path/to/csvs/
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

LOCAL = Path(__file__).resolve().parents[2] / "labs" / "lab01" / "data"
REMOTE = "https://raw.githubusercontent.com/kon0925/hy489/main/labs/lab01/data/"


def rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def coded_fraction(df: pd.DataFrame, col: str) -> float:
    """Metric 1. What share of rows carry any code at all."""
    s = df[col]
    present = s.notna() & (s.astype(str).str.strip() != "")
    return float(present.mean())


def residual_fraction(df: pd.DataFrame, col: str) -> float:
    """Metric 4. What share sit in a residual category.

    Detected by description rather than by code, because the marker words differ
    between vocabularies. A high value tells you about the coding workflow and
    the time pressure on it, not about the patients.
    """
    marker = r"unspecified|not otherwise specified|\bNOS\b|other specified|\bother\b"
    return float(df[col].astype(str).str.contains(marker, case=False, regex=True).mean())


def consistency(df: pd.DataFrame, code: str, desc: str) -> tuple[pd.Series, pd.Series]:
    """Metric 3, in both directions.

    Descriptions carrying several codes means inconsistent CODING.
    Codes carrying several descriptions means inconsistent DISPLAY, which is
    harmless right up until somebody matches on the display.
    """
    per_desc = df.groupby(desc)[code].nunique()
    per_code = df.groupby(code)[desc].nunique()
    return per_desc, per_code


def report(name: str, df: pd.DataFrame, code: str, desc: str) -> None:
    rule(f"{name}  ({len(df):,} rows)")

    print(f"1. coded fraction          {coded_fraction(df, code):6.1%}")

    # Metric 2. System coverage: does anything say WHICH vocabulary?
    has_system = any(c.upper() in ("SYSTEM", "CODE_SYSTEM", "CODESYSTEM") for c in df.columns)
    print(f"2. system column present   {'yes' if has_system else 'NO'}"
          f"{'' if has_system else '   <- you are guessing the vocabulary from context'}")

    per_desc, per_code = consistency(df, code, desc)
    print(f"3. distinct codes          {df[code].nunique():,}")
    print(f"   descriptions with >1 code   {int((per_desc > 1).sum()):,}"
          f"   <- inconsistent coding")
    print(f"   codes with >1 description   {int((per_code > 1).sum()):,}"
          f"   <- inconsistent display")

    print(f"4. residual fraction       {residual_fraction(df, desc):6.1%}"
          f"   (unspecified / other / NOS)")

    top = df[desc].value_counts()
    head = top.head(20).sum() / len(df)
    print(f"5. head of the distribution {head:6.1%} of rows are the top 20 descriptions")
    print(f"   -> map those 20 first. That is metric 5's real message.")

    worst = per_desc[per_desc > 1].sort_values(ascending=False).head(5)
    if len(worst):
        print()
        print("   descriptions carrying several codes:")
        for d, n in worst.items():
            codes = sorted(df.loc[df[desc] == d, code].dropna().unique())[:4]
            print(f"     {n}x  {str(d)[:46]:<48}{codes}")


def main(a) -> None:
    src = f"{a.data}/" if Path(a.data).exists() else REMOTE
    print(f"reading from: {src}")

    # dtype=str on purpose: concept ids are strings, never integers.
    # Read them as numbers and long ids lose precision, exactly as the
    # lecture warned. Excel does this to you automatically.
    con = pd.read_csv(src + "conditions.csv", dtype={"CODE": str})
    report("conditions.csv", con, "CODE", "DESCRIPTION")

    obs = pd.read_csv(src + "observations.csv", dtype={"CODE": str})
    report("observations.csv", obs, "CODE", "DESCRIPTION")

    rule("What to take away")
    print("This dataset is synthetic, so it scores far better than anything you")
    print("will be handed by a hospital. Expect a real extract to show:")
    print("  - a coded fraction well below 100%")
    print("  - no system column at all")
    print("  - the same description under several codes, and the reverse")
    print("  - a residual fraction in the tens of percent")
    print()
    print("Run this script on the first day of any project. The numbers decide")
    print("what you can honestly promise.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(LOCAL))
    main(ap.parse_args())
