#!/usr/bin/env python3
"""Score four data access requests against the Five Safes, and argue about it.

    python3 request.py                # all four, then the comparison
    python3 request.py --rubric       # the fifteen criteria and the decision rule
    python3 request.py --student      # a PhD student who wants the whole table
    python3 request.py --pharma       # a company that wants a linked cohort
    python3 request.py --audit        # the hospital auditing itself
    python3 request.py --journalist   # a newspaper
    python3 request.py --compare      # the four side by side
    python3 request.py --critique     # what this rubric gets wrong

The Five Safes (Ritchie, 2003, written for the UK Office for National
Statistics and now the frame most European health data bodies use) replaces
one question with five. Instead of asking whether data is anonymous, it asks
whether the people, the project, the setting, the data and the outputs are
each safe enough, and it accepts that the answer to each one depends on the
answers to the others. Identifiable data in a controlled room with trained
staff and checked outputs can be safer than an anonymised file emailed out.

The scoring below is a rubric, not a law. Every criterion in it is a judgement
somebody made, and the last section is an argument against four of them. The
point of the script is that you can read the reasoning and disagree with it.

No data is read. This one is all policy.

Stdlib only.
"""

from __future__ import annotations

import argparse

# ----------------------------------------------------------------------
# the rubric
# ----------------------------------------------------------------------
# safe, id, what the criterion asks, what to do when it is not met
CRITERIA = [
    ("people", "P1", "the applicant has completed accredited researcher training",
     "require accredited training before any access is granted"),
    ("people", "P2", "a named accountable organisation employs or supervises the applicant",
     "add a named supervisor or institutional signatory who carries the liability"),
    ("people", "P3", "the organisation has signed an agreement with enforceable sanctions",
     "execute a data access agreement with named penalties before release"),

    ("projects", "J1", "the purpose has a documented lawful basis and an ethics approval",
     "obtain ethics committee approval and record the lawful basis"),
    ("projects", "J2", "a public benefit follows that does not depend on who profits",
     "require a publication or service commitment independent of commercial outcome"),
    ("projects", "J3", "the fields requested are the minimum the question needs",
     "cut the request to the fields the stated analysis uses"),

    ("settings", "S1", "the analysis runs in an environment the controller operates",
     "move the analysis into the trusted research environment"),
    ("settings", "S2", "no record-level copy leaves that environment",
     "forbid download; the researcher works at the data, the data does not travel"),
    ("settings", "S3", "access is logged and somebody reviews the log",
     "name the person who reads the access log and how often"),

    ("data", "D1", "direct identifiers are removed",
     "strip name, national identifier, address and contact fields"),
    ("data", "D2", "no linkage key usable outside the environment is supplied",
     "replace any national identifier with a project-specific pseudonym held by the controller"),
    ("data", "D3", "dates and geography are no finer than the question needs",
     "generalise birth date to year and postcode to regional unit"),

    ("outputs", "O1", "what leaves is aggregate, not record level",
     "restrict the export to tables and model summaries"),
    ("outputs", "O2", "an independent checker reviews every output before release",
     "route every export through output checking by somebody not on the project"),
    ("outputs", "O3", "a cumulative record of this project's past outputs is kept and consulted",
     "maintain an output register and check each new request against it"),
]

SAFES = ["people", "projects", "settings", "data", "outputs"]
BY_SAFE = {s: [c for c in CRITERIA if c[0] == s] for s in SAFES}


# ----------------------------------------------------------------------
# the requests
# ----------------------------------------------------------------------
# findings maps a criterion id to (met, the reason the assessor gave)
REQUESTS = [
    {
        "key": "student",
        "short": "PhD student, whole table",
        "title": "A PhD student who wants the whole table",
        "applicant": "Doctoral candidate, Computer Science, University of Crete",
        "asks_for": "patients.csv and conditions.csv in full, including SSN, "
                    "full date of birth, street address and postcode",
        "purpose": "a thesis chapter on type 2 diabetes prevalence by district",
        "setting": "the student's own laptop, at home, synced to a commercial cloud drive",
        "outputs": "whatever ends up in the thesis",
        "findings": {
            "P1": (0, "no accredited researcher training; the department does not run one"),
            "P2": (1, "a named supervisor and a university that can be held to account"),
            "P3": (0, "no agreement exists; the request arrived as an email"),
            "J1": (0, "ethics application submitted, not yet approved"),
            "J2": (1, "prevalence by district is a public health question with a public answer"),
            "J3": (0, "SSN, street address and full date of birth are in no part of the analysis"),
            "S1": (0, "a personal laptop is not an environment anybody controls"),
            "S2": (0, "the file is the copy; synced to a cloud drive it becomes several"),
            "S3": (0, "no access log exists on a laptop"),
            "D1": (0, "SSN and address requested explicitly"),
            "D2": (0, "SSN is the national linkage key"),
            "D3": (0, "full date of birth and street address for a district-level question"),
            "O1": (1, "a thesis chapter is aggregate by nature"),
            "O2": (0, "the supervisor reads the chapter; nobody checks the tables"),
            "O3": (0, "no output register"),
        },
    },
    {
        "key": "pharma",
        "short": "Pharmaceutical company",
        "title": "A pharmaceutical company that wants a linked cohort",
        "applicant": "Epidemiology unit of a marketing authorisation holder, incorporated in the EU",
        "asks_for": "pseudonymised prescriptions, conditions and mortality for all patients "
                    "dispensed an antihypertensive, linked to the company's own trial register "
                    "by national identifier",
        "purpose": "a post-authorisation safety study required by the regulator",
        "setting": "the company's own validated analysis environment, ISO 27001 certified",
        "outputs": "regulatory tables and a journal manuscript",
        "findings": {
            "P1": (1, "named analysts hold current accredited training"),
            "P2": (1, "a corporate entity with a legal address and an appointed DPO"),
            "P3": (1, "a signed agreement with liquidated damages and an audit right"),
            "J1": (1, "a regulator-mandated study with a documented lawful basis"),
            "J2": (1, "a safety signal benefits everybody taking the drug, including non-customers"),
            "J3": (0, "mortality and full prescription history exceed the stated safety question"),
            "S1": (0, "the environment is validated, and the controller does not operate it"),
            "S2": (0, "the whole request is a record-level transfer out"),
            "S3": (1, "the company logs access and submits to external audit"),
            "D1": (1, "no names or contact details requested"),
            "D2": (0, "linkage by national identifier re-identifies every row at the far end"),
            "D3": (1, "dates reduced to month, geography to regional unit"),
            "O1": (1, "regulatory tables and a manuscript are aggregates"),
            "O2": (0, "outputs are checked by the company's own staff"),
            "O3": (1, "the study protocol fixes the output list in advance"),
        },
    },
    {
        "key": "audit",
        "short": "Internal quality audit",
        "title": "The hospital auditing itself",
        "applicant": "Clinical governance team of the hospital that holds the records",
        "asks_for": "identifiable records for every patient discharged in the last two years",
        "purpose": "measure the 30-day readmission rate by ward and feed it back to the wards",
        "setting": "the hospital's own clinical system, inside the existing care context",
        "outputs": "a ward-level report circulated to clinical directors",
        "findings": {
            "P1": (0, "clinical governance staff hold information governance training, not research training"),
            "P2": (1, "employed by the controller itself"),
            "P3": (1, "employment contract and professional registration carry the sanction"),
            "J1": (1, "service evaluation under the controller's own lawful basis; no ethics approval needed"),
            "J2": (1, "readmission rates change how the wards are run"),
            "J3": (1, "discharge and readmission dates are what the measure is made of"),
            "S1": (1, "the controller operates the system"),
            "S2": (1, "nothing leaves; the report is produced inside"),
            "S3": (1, "the access log exists, and Week 10 spends a script on whether anybody reads it"),
            "D1": (0, "identifiable, by design, because the readmission has to be matched to the discharge"),
            "D2": (0, "the hospital number is the linkage key and the staff can resolve it"),
            "D3": (0, "full dates, because 30 days is the measure"),
            "O1": (1, "ward-level counts"),
            "O2": (0, "the team that produced the report decides what to circulate"),
            "O3": (0, "no register; the report is produced monthly and nobody compares them"),
        },
    },
    {
        "key": "journalist",
        "short": "Newspaper",
        "title": "A newspaper",
        "applicant": "Health correspondent, a regional daily",
        "asks_for": "counts of diabetes and hypertension by town and age band, and a route to "
                    "patients who would agree to be interviewed",
        "purpose": "an investigation into unequal provision of chronic disease care across Crete",
        "setting": "the newsroom",
        "outputs": "a published article",
        "findings": {
            "P1": (0, "no researcher training, and no accreditation scheme that fits"),
            "P2": (1, "a registered publisher with an editor and a regulator"),
            "P3": (0, "a newspaper will not sign a contract that lets the controller approve copy"),
            "J1": (1, "journalism has a lawful basis in its own right under GDPR Article 85"),
            "J2": (1, "unequal provision is a public interest question and the press is how it gets raised"),
            "J3": (0, "the contact route is a separate request wearing the same envelope"),
            "S1": (0, "a newsroom is not a controlled environment"),
            "S2": (1, "the counts requested are already aggregate"),
            "S3": (0, "no log, and no expectation of one"),
            "D1": (1, "the statistical part names nobody"),
            "D2": (1, "no linkage key sought for the statistical part"),
            "D3": (0, "town by age band produces cells below five, as disclosure.py shows"),
            "O1": (0, "the second half of the request is for individuals"),
            "O2": (0, "no output checking; the editor is not an output checker"),
            "O3": (0, "no register"),
        },
    },
]


# ----------------------------------------------------------------------
# scoring
# ----------------------------------------------------------------------
def safe_score(req, safe):
    return sum(req["findings"][c[1]][0] for c in BY_SAFE[safe])


def total(req):
    return sum(req["findings"][c[1]][0] for c in CRITERIA)


def decide(req):
    """The decision rule, stated so that it can be argued with.

    A zero on any one safe is fatal on its own, because the Five Safes trade
    against each other only while every one of them is above the floor. Below
    the floor there is nothing left to trade with.
    """
    scores = {s: safe_score(req, s) for s in SAFES}
    t = total(req)
    zeros = [s for s in SAFES if scores[s] == 0]
    if zeros:
        return "REFUSE", "a safe scored zero: %s" % ", ".join(zeros)
    if t >= 12 and min(scores.values()) >= 2:
        return "APPROVE", "total %d of 15, every safe at 2 or better" % t
    if t >= 8 and min(scores.values()) >= 1:
        return "APPROVE WITH CONDITIONS", "total %d of 15, weakest safe at %d" % (t, min(scores.values()))
    return "REFUSE", "total %d of 15 is below the floor of 8" % t


def conditions(req):
    return [(c[1], c[3]) for c in CRITERIA if req["findings"][c[1]][0] == 0]


# ----------------------------------------------------------------------
# reporting
# ----------------------------------------------------------------------
def report_rubric():
    print("\nTHE RUBRIC")
    print("  Fifteen criteria, three per safe, one point each.")
    for s in SAFES:
        print("\n  SAFE %s" % s.upper())
        for _, cid, text, _ in BY_SAFE[s]:
            print("    %-4s %s" % (cid, text))
    print("""
  THE DECISION RULE
    any safe scoring 0                        refuse
    total 12 or more and no safe below 2      approve
    total 8 or more and no safe below 1       approve with conditions
    anything else                             refuse

  The floor is doing most of the work here. A request can score 9 of 15 and be
  refused because one safe is empty, which happens to one of the four below,
  and a request can score 8 and proceed because the weakness is spread. That
  is the Five Safes claim: the safes substitute for each other over a range
  and stop substituting outside it.""")


def report_request(req):
    print("\n" + "=" * 74)
    print("REQUEST: %s" % req["title"])
    print("=" * 74)
    print("  applicant   %s" % req["applicant"])
    print("  asks for    %s" % wrap(req["asks_for"], 60, 14))
    print("  purpose     %s" % wrap(req["purpose"], 60, 14))
    print("  setting     %s" % wrap(req["setting"], 60, 14))
    print("  outputs     %s" % wrap(req["outputs"], 60, 14))
    print()
    for s in SAFES:
        print("  SAFE %-10s %d of 3" % (s.upper(), safe_score(req, s)))
        for _, cid, text, _ in BY_SAFE[s]:
            met, reason = req["findings"][cid]
            print("    %-4s %s  %s" % (cid, "yes" if met else " no", text))
            print("         %s" % reason)
        print()
    verdict, why = decide(req)
    print("  SCORES      %s" % "  ".join("%s %d" % (s[:4], safe_score(req, s)) for s in SAFES))
    print("  TOTAL       %d of 15" % total(req))
    print("  DECISION    %s" % verdict)
    print("  BECAUSE     %s" % why)
    conds = conditions(req)
    if verdict.startswith("APPROVE"):
        print("\n  CONDITIONS ATTACHED (%d), one per criterion that failed:" % len(conds))
    else:
        print("\n  WHAT WOULD HAVE TO CHANGE (%d), before this could be approved:" % len(conds))
    for cid, remedy in conds:
        print("    %-4s %s" % (cid, remedy))
    print()
    for line in req["note"].strip("\n").split("\n"):
        print(("  " + line).rstrip())


def wrap(text, width, indent):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return ("\n" + " " * indent).join(lines)


def report_compare():
    print("\nTHE FOUR SIDE BY SIDE")
    print("  %-26s %6s %8s %8s %6s %8s %6s  %s"
          % ("", "people", "projects", "settings", "data", "outputs", "total", "decision"))
    for req in REQUESTS:
        verdict, _ = decide(req)
        print("  %-26s %6d %8d %8d %6d %8d %6d  %s"
              % (req["short"], safe_score(req, "people"), safe_score(req, "projects"),
                 safe_score(req, "settings"), safe_score(req, "data"),
                 safe_score(req, "outputs"), total(req), verdict))
    print("""
  Three of the four are refused, and the one that proceeds is the commercial
  request. Start there, because it is the result people expect least.

  The company scores 3 on safe people and 2 on safe projects: trained
  analysts, a corporate entity with something to lose, a study the regulator
  demanded. The student scores 1 and 1 with a smaller request for less data,
  and is refused. The rubric does not score the quantity of data. It scores
  who holds it, where they hold it, and what may leave.

  Then read the audit row, which is the one that broke while this script was
  being written. The hospital auditing its own readmission rate scores 9 of
  15, the second highest of the four, with 3 on settings and 3 on projects,
  and it is refused, because safe data scores 0. Every criterion under safe
  data fails for the same reason: matching a readmission to a discharge needs
  the identity and the exact dates, and that is what the measure is made of.

  No hospital would accept that answer, and no hospital gets it, because
  direct care and service evaluation are held outside the research access
  regime entirely. Notice what that exemption does. The largest routine flow
  of identifiable patient data inside any hospital is the one flow this rubric
  never sees.""")


def report_critique():
    print("\nFOUR ARGUMENTS AGAINST THIS RUBRIC")
    print("""
  1. P1 and P3 reward institutional affiliation, not trustworthiness. An
     independent researcher with twenty years in the field scores zero on
     safe people because nobody will sign for them. A first-week doctoral
     student at a university with a template agreement scores two. The
     criterion measures who has a legal department.

  2. The rubric refuses the internal audit, and no hospital would run on a
     rule that does. That is not the audit failing the rubric; it is the
     rubric being used outside what it was written for. Ritchie wrote the
     Five Safes for releasing data to external researchers. Applied to a
     controller analysing its own records for its own service, safe data asks
     a question with no good answer. The standard fix is to exempt service
     evaluation, and the standard consequence is that the largest flow of
     identifiable data in the building gets no scrutiny at all. The other
     half of that argument is accesslog.py: S3 asks whether an access log
     exists, and a log that exists and is never read scores the same point as
     a log somebody reads.

  3. J2, public benefit, is scored by reading the applicant's own description
     of their purpose. Every applicant writes a public benefit. The criterion
     has no independent evidence behind it and it carries the same weight as
     the criteria that do.

  4. The rubric scores a request once, at the start. disclosure.py shows a
     disclosure assembled from two outputs that were each correctly approved
     months apart. O3 is the only criterion that looks at the history, it is
     worth one point out of fifteen, and three of these four requests fail it
     without that failure changing any decision.

  A last one to argue about in class. The journalist is refused, and the
  question the journalist asked, whether chronic disease care is provided
  unequally across Crete, is a question the health service should want
  answered in public. Refusing the request does not make the question go
  away. It moves the answer to whoever will supply it without a rubric.""")


NOTES = {
    "student": """
  Three of fifteen, the lowest of the four, and the refusal is not about the
  student. All six failures under safe settings and safe data disappear if
  the same analysis runs inside a trusted research environment on an extract
  with the SSN and the address removed and the birth date cut to a year. The
  thesis chapter is unchanged. The request was written as a file transfer
  because a file transfer is how this student has received every dataset of
  their degree, including the one this course handed them in Week 1.""",
    "pharma": """
  Ten of fifteen and the only one of the four that proceeds, which is worth
  arguing about. Safe people scores 3: trained analysts, a corporate entity
  with something to lose, a signed agreement with damages in it. The weakness
  is safe settings at 1, and the reason is that the whole request is a
  transfer out of record-level data into an environment the controller does
  not operate.

  Two changes close most of the gap and cost the company nothing it needs.
  Run the analysis inside the controller's environment, which takes settings
  from 1 to 3. Replace the national identifier with a pseudonym the
  controller holds and resolves, which takes D2. The company keeps its
  linkage, the regulator keeps its study, and the ability to name every row
  stays on the controller's side of the wall.""",
    "audit": """
  Nine of fifteen, the second highest of the four, and refused on a single
  empty safe. Read the three failures under safe data together: they are one
  failure, stated three times, and it is that a readmission has to be matched
  to a discharge. There is no version of this measure that scores a point
  there, so the rubric cannot approve a 30-day readmission audit at all.

  Most European systems resolve that by putting direct care and service
  evaluation outside the research access regime, under the controller's own
  lawful basis. The exemption is defensible. It also means the two failures
  that would matter most here go unexamined: O2, because the team that
  produces the report decides what goes in it, and O3, because nobody
  compares this month's report with last month's.""",
    "journalist": """
  The statistical half of this request is the one the rubric handles worst. It
  is a request for the table in disclosure.py, and disclosure.py already shows
  what has to happen to that table before it can be released. Split the
  request in two and the statistical half becomes a routine output check with
  a suppression rule attached. The contact half stays refused, because consent
  to be interviewed is something the patient gives, and the controller cannot
  give it for them.""",
}


def main():
    for r in REQUESTS:
        r["note"] = NOTES[r["key"]]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("rubric", "student", "pharma", "audit", "journalist", "compare", "critique"):
        ap.add_argument("--" + flag, action="store_true")
    args = ap.parse_args()
    chosen = [k for k in ("rubric", "student", "pharma", "audit", "journalist",
                          "compare", "critique") if getattr(args, k)]
    run_all = not chosen

    if "rubric" in chosen or run_all:
        report_rubric()
    for req in REQUESTS:
        if req["key"] in chosen or run_all:
            report_request(req)
    if "compare" in chosen or run_all:
        report_compare()
    if "critique" in chosen or run_all:
        report_critique()


if __name__ == "__main__":
    main()
