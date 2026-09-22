#!/usr/bin/env python3
"""HY-489 Week 6: a miniature Achilles, and a miniature Data Quality Dashboard.

    python3 characterise.py            # characterisation: what is in this CDM?
    python3 characterise.py --checks   # quality checks: is any of it plausible?

The real tools are R packages and they run several hundred analyses and around
three thousand checks. This is perhaps thirty of each, chosen because they are
the ones that find something. The habit is what transfers: you characterise an
instance before you analyse it, and you run the checks before you believe a
number that came out of it.

    Achilles                 github.com/OHDSI/Achilles
    DataQualityDashboard     github.com/OHDSI/DataQualityDashboard

The checks below are grouped by the Kahn framework, the same way the Data
Quality Dashboard groups its own: conformance, completeness, plausibility, each
split into whether the data matches its own specification (verification) or
matches the world (validation).
"""

from __future__ import annotations

import argparse
import datetime
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "cdm.db")

CLINICAL_TABLES = [
    ("condition_occurrence", "condition_concept_id", "condition_start_date",
     "condition_source_value"),
    ("drug_exposure", "drug_concept_id", "drug_exposure_start_date",
     "drug_source_value"),
    ("measurement", "measurement_concept_id", "measurement_date",
     "measurement_source_value"),
    ("observation", "observation_concept_id", "observation_date",
     "observation_source_value"),
]


def rule(title):
    print()
    print(title)
    print("-" * 74)


def one(con, sql, *args):
    row = con.execute(sql, args).fetchone()
    return row[0] if row else None


def rows(con, sql, *args):
    return con.execute(sql, args).fetchall()


# ---------------------------------------------------------- characterisation

def characterise(con):
    print("=" * 74)
    print("CHARACTERISATION")
    print("=" * 74)

    src = con.execute("SELECT * FROM cdm_source").fetchone()
    if src:
        names = [d[0] for d in con.execute("SELECT * FROM cdm_source LIMIT 0").description]
        rule("Who made this, and when")
        for name, value in zip(names, src):
            print("  %-26s %s" % (name, value))
        print()
        print("  A CDM instance with an empty cdm_source is one nobody can cite.")

    rule("Record counts per table")
    print("  A table with zero rows means a source that was never loaded, or a")
    print("  domain that routed somewhere else. Both are worth explaining.")
    print()
    for table in ("person", "observation_period", "visit_occurrence",
                  "condition_occurrence", "drug_exposure", "measurement",
                  "observation", "death", "concept", "concept_ancestor"):
        print("  %-24s %10d" % (table, one(con, "SELECT count(*) FROM %s" % table)))

    rule("Records per person")
    print("  %-24s %8s %8s %8s %8s" % ("table", "persons", "mean", "max", "with 0"))
    n_person = one(con, "SELECT count(*) FROM person")
    for table, _concept, _date, _src in CLINICAL_TABLES:
        with_any = one(con, "SELECT count(DISTINCT person_id) FROM %s" % table)
        total = one(con, "SELECT count(*) FROM %s" % table)
        biggest = one(con, "SELECT max(n) FROM (SELECT count(*) AS n FROM %s "
                           "GROUP BY person_id)" % table) or 0
        print("  %-24s %8d %8.1f %8d %8d" % (
            table, with_any, (total / with_any) if with_any else 0,
            biggest, n_person - with_any))
    print()
    print("  A person with an implausible number of rows is either a data error")
    print("  or a very unusual patient. Both are worth finding.")

    rule("Observed time")
    row = con.execute(
        "SELECT count(*), min(observation_period_start_date), "
        "max(observation_period_end_date), "
        "round(avg(julianday(observation_period_end_date) "
        "          - julianday(observation_period_start_date)) / 365.25, 1) "
        "FROM observation_period").fetchone()
    if row and row[0]:
        print("  periods %d, from %s to %s, mean %.1f years" % row)
        print()
        print("  This is the denominator of every rate you will compute.")
    else:
        print("  NO OBSERVATION PERIODS. Every rate computed from this instance")
        print("  would have no denominator, and you would have to invent one.")

    rule("Concept frequency, top 10 per domain")
    for table, concept_col, _date, _src in CLINICAL_TABLES:
        print()
        print("  %s" % table)
        for name, n in rows(con,
                            "SELECT c.concept_name, count(*) AS n FROM %s t "
                            "LEFT JOIN concept c ON c.concept_id = t.%s "
                            "GROUP BY 1 ORDER BY n DESC LIMIT 10" % (table, concept_col)):
            print("    %-56s %8d" % ((name or "(unmapped, concept_id 0)")[:56], n))
    print()
    print("  Read these as a clinician would. If the commonest condition in a")
    print("  hospital is administrative, something is wrong with the mapping.")

    rule("Records over time")
    print("  A cliff or a step is a system migration, a coding change, or a load")
    print("  that failed halfway. It is almost never epidemiology.")
    print()
    for table, _concept, date_col, _src in CLINICAL_TABLES:
        series = rows(con, "SELECT substr(%s, 1, 4) AS yr, count(*) FROM %s "
                           "WHERE %s <> '' GROUP BY 1 ORDER BY 1" % (date_col, table, date_col))
        if not series:
            continue
        top = max(n for _y, n in series) or 1
        print("  %s" % table)
        for year, n in series[-12:]:
            bar = "#" * max(1, int(40.0 * n / top))
            print("    %-6s %7d  %s" % (year, n, bar))

    rule("Age and sex")
    this_year = datetime.date.today().year
    for label, n in rows(con,
                         "SELECT COALESCE(c.concept_name, 'unmapped'), count(*) "
                         "FROM person p LEFT JOIN concept c "
                         "ON c.concept_id = p.gender_concept_id GROUP BY 1 ORDER BY 2 DESC"):
        print("  %-24s %8d" % (label, n))
    print()
    bands = rows(con,
                 "SELECT CASE WHEN (? - year_of_birth) < 18 THEN '00-17' "
                 "            WHEN (? - year_of_birth) < 40 THEN '18-39' "
                 "            WHEN (? - year_of_birth) < 65 THEN '40-64' "
                 "            WHEN (? - year_of_birth) < 80 THEN '65-79' "
                 "            ELSE '80+' END AS band, count(*) "
                 "FROM person GROUP BY 1 ORDER BY 1",
                 this_year, this_year, this_year, this_year)
    top = max([n for _b, n in bands] or [1])
    for band, n in bands:
        print("  %-8s %7d  %s" % (band, n, "#" * max(1, int(40.0 * n / top))))
    print()
    print("  Does this look like the population the source serves? A paediatric")
    print("  hospital with a median age of 54 has a problem.")

    rule("The unmapped tail, ranked")
    found = False
    for table, concept_col, _date, source_col in CLINICAL_TABLES:
        for code, n in rows(con,
                            "SELECT %s, count(*) AS n FROM %s WHERE %s = 0 "
                            "GROUP BY 1 ORDER BY n DESC LIMIT 10"
                            % (source_col, table, concept_col)):
            print("  %-22s %-16s %8d" % (table, code, n))
            found = True
    if not found:
        print("  Nothing unmapped in any table.")
        print()
        print("  On a real instance, be suspicious of this. It usually means the")
        print("  ETL is dropping what it cannot map rather than keeping it.")
    else:
        print()
        print("  This list is your mapping backlog, in priority order. Work down")
        print("  it by frequency, not alphabetically.")
    print()


# ----------------------------------------------------------------- the checks

class Checks:
    def __init__(self):
        self.results = []

    def check(self, category, kind, name, failing, threshold=0, note=""):
        ok = failing <= threshold
        self.results.append((category, kind, name, failing, ok, note))

    def report(self):
        print("=" * 74)
        print("DATA QUALITY CHECKS")
        print("=" * 74)
        print("%-14s %-13s %-36s %8s %6s" % (
            "category", "kind", "check", "failing", ""))
        print("-" * 80)
        last = None
        for category, kind, name, failing, ok, note in self.results:
            if category != last:
                print()
                last = category
            print("%-14s %-13s %-36s %8d %6s" % (
                category, kind, name[:36], failing, "pass" if ok else "FAIL"))
            if note and not ok:
                print("%48s %s" % ("", note))
        failed = [r for r in self.results if not r[4]]
        print()
        print("-" * 80)
        print("%d checks, %d failing." % (len(self.results), len(failed)))
        if failed:
            print()
            print("A failing check is not a reason to stop. It is a reason to find out")
            print("which ETL decision produced it, and either fix the ETL or write the")
            print("failure down where the next analyst will see it.")
        return len(failed)


def run_checks(con):
    ch = Checks()
    today = datetime.date.today().isoformat()

    # ---- conformance: does the data match its own specification? ----------
    for table, concept_col, date_col, _src in CLINICAL_TABLES:
        ch.check("conformance", "verification",
                 "%s concept exists" % table,
                 one(con, "SELECT count(*) FROM %s t LEFT JOIN concept c "
                          "ON c.concept_id = t.%s "
                          "WHERE t.%s <> 0 AND c.concept_id IS NULL"
                          % (table, concept_col, concept_col)),
                 note="a concept_id that is not in the concept table")
        ch.check("conformance", "verification",
                 "%s person exists" % table,
                 one(con, "SELECT count(*) FROM %s t LEFT JOIN person p "
                          "USING (person_id) WHERE p.person_id IS NULL" % table),
                 note="a clinical row for a person who is not in person")
        ch.check("conformance", "verification",
                 "%s date is a date" % table,
                 one(con, "SELECT count(*) FROM %s WHERE %s IS NULL "
                          "OR length(%s) <> 10 OR date(%s) IS NULL"
                          % (table, date_col, date_col, date_col)),
                 note="a date column that will not parse")

    ch.check("conformance", "verification", "person gender is mapped",
             one(con, "SELECT count(*) FROM person WHERE gender_concept_id = 0"),
             note="gender_concept_id 0 means the source value did not map")

    # ---- completeness: is anything missing that should be there? ----------
    ch.check("completeness", "verification", "person is not empty",
             1 if one(con, "SELECT count(*) FROM person") == 0 else 0,
             note="no people, no CDM")
    ch.check("completeness", "verification", "observation_period is not empty",
             1 if one(con, "SELECT count(*) FROM observation_period") == 0 else 0,
             note="without it, no rate computed here has a denominator")
    ch.check("completeness", "verification", "every person is observed",
             one(con, "SELECT count(*) FROM person p LEFT JOIN observation_period o "
                      "USING (person_id) WHERE o.person_id IS NULL"),
             note="a person with no observation period is invisible to any rate")
    ch.check("completeness", "verification", "measurements have a unit",
             one(con, "SELECT count(*) FROM measurement "
                      "WHERE value_as_number IS NOT NULL AND unit_concept_id IS NULL"),
             note="a number with no unit cannot be compared with another site")
    ch.check("completeness", "verification", "conditions have a visit",
             one(con, "SELECT count(*) FROM condition_occurrence "
                      "WHERE visit_occurrence_id IS NULL"),
             threshold=0,
             note="a row with no visit has lost the context it happened in")
    for table, concept_col, _date, _src in CLINICAL_TABLES:
        total = one(con, "SELECT count(*) FROM %s" % table) or 1
        unmapped = one(con, "SELECT count(*) FROM %s WHERE %s = 0" % (table, concept_col))
        ch.check("completeness", "validation",
                 "%s unmapped under 20%%" % table,
                 unmapped, threshold=int(0.20 * total),
                 note="%d of %d rows (%.1f%%) did not map" % (
                     unmapped, total, 100.0 * unmapped / total))

    # ---- plausibility: could this be true? --------------------------------
    for table, _concept, date_col, _src in CLINICAL_TABLES:
        ch.check("plausibility", "verification",
                 "%s not before birth" % table,
                 one(con, "SELECT count(*) FROM %s t JOIN person p USING (person_id) "
                          "WHERE substr(t.%s, 1, 4) <> '' "
                          "AND CAST(substr(t.%s, 1, 4) AS INTEGER) < p.year_of_birth"
                          % (table, date_col, date_col)),
                 note="an event dated before the patient was born")
        ch.check("plausibility", "verification",
                 "%s not after death" % table,
                 one(con, "SELECT count(*) FROM %s t JOIN death d USING (person_id) "
                          "WHERE t.%s > d.death_date" % (table, date_col)),
                 note="an event dated after the patient died")
        ch.check("plausibility", "verification",
                 "%s not in the future" % table,
                 one(con, "SELECT count(*) FROM %s WHERE %s > ?" % (table, date_col), today),
                 note="an event dated after today")
        ch.check("plausibility", "validation",
                 "%s within observation" % table,
                 one(con, "SELECT count(*) FROM %s t JOIN observation_period o "
                          "USING (person_id) WHERE t.%s < o.observation_period_start_date "
                          "OR t.%s > o.observation_period_end_date"
                          % (table, date_col, date_col)),
                 note="an event outside the period the person was said to be observable")

    ch.check("plausibility", "verification", "observation period is ordered",
             one(con, "SELECT count(*) FROM observation_period "
                      "WHERE observation_period_end_date < observation_period_start_date"),
             note="a period that ends before it starts")
    ch.check("plausibility", "verification", "visit is ordered",
             one(con, "SELECT count(*) FROM visit_occurrence "
                      "WHERE visit_end_date IS NOT NULL AND visit_end_date < visit_start_date"),
             note="a discharge before an admission")
    ch.check("plausibility", "validation", "systolic BP in range",
             one(con, "SELECT count(*) FROM measurement m JOIN concept c "
                      "ON c.concept_id = m.measurement_concept_id "
                      "WHERE c.concept_code = '8480-6' "
                      "AND (m.value_as_number < 50 OR m.value_as_number > 300)"),
             note="a systolic blood pressure outside 50 to 300 mmHg"),
    ch.check("plausibility", "validation", "body weight in range",
             one(con, "SELECT count(*) FROM measurement m JOIN concept c "
                      "ON c.concept_id = m.measurement_concept_id "
                      "WHERE c.concept_code = '29463-7' "
                      "AND (m.value_as_number <= 0 OR m.value_as_number > 400)"),
             note="a body weight outside 0 to 400 kg")
    ch.check("plausibility", "validation", "age at death is plausible",
             one(con, "SELECT count(*) FROM death d JOIN person p USING (person_id) "
                      "WHERE CAST(substr(d.death_date, 1, 4) AS INTEGER) "
                      "      - p.year_of_birth NOT BETWEEN 0 AND 115"),
             note="a death more than 115 years after a birth, or before it")

    failed = ch.report()
    if one(con, "SELECT count(*) FROM observation_period") == 0:
        print()
        print("Note: every 'within observation' check above passed because there is")
        print("nothing to check. A check that has no rows to test is not a passing")
        print("check, and a real dashboard reports those separately for that reason.")
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=DEFAULT_DB, help="the CDM to read (default: ./cdm.db)")
    ap.add_argument("--checks", action="store_true",
                    help="run the quality checks instead of the characterisation")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit("No database at %s. Run: python3 etl.py" % args.db)
    con = sqlite3.connect(args.db)
    if args.checks:
        failed = run_checks(con)
        con.close()
        sys.exit(1 if failed else 0)
    characterise(con)
    con.close()


if __name__ == "__main__":
    main()
