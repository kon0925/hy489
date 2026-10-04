#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HY-489 Week 12. Two decision trees, run over eight worked systems.

MDR Annex VIII Rule 11 decides the device class. AI Act Articles 6(1) and 6(2)
decide whether the thing is a high-risk AI system. They are different questions
with different answers and they are frequently run together by mistake.

Every question in both trees is printed, so that a student can disagree with the
answer rather than only with the conclusion.
"""
import sys

# ----------------------------------------------------------------- the systems
# Each system answers a fixed set of questions. The answers are judgements, not
# facts, and several of them are arguable. That is the point of the exercise.
SYSTEMS = [
    dict(name="Sepsis early warning",
         blurb="flags deterioration six hours ahead, on a ward, from vitals and labs",
         medical_purpose=True, informs_decision=True, diagnostic_or_therapeutic=True,
         harm="death", monitors_physiology=True, vital_params=True, immediate_danger=True,
         annex1_product=True, annex3_use=None, in_house=False, safety_component=False),
    dict(name="Radiology triage",
         blurb="reorders the worklist so suspected intracranial haemorrhage is read first",
         medical_purpose=True, informs_decision=True, diagnostic_or_therapeutic=True,
         harm="death", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=True, annex3_use=None, in_house=False, safety_component=False),
    dict(name="Theatre scheduling optimiser",
         blurb="allocates operating theatre slots to maximise utilisation",
         medical_purpose=False, informs_decision=False, diagnostic_or_therapeutic=False,
         harm="none", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=False, annex3_use=None, in_house=True, safety_component=False),
    dict(name="Note completion in the EHR",
         blurb="suggests the next phrase while a clinician types a clinical note",
         medical_purpose=False, informs_decision=False, diagnostic_or_therapeutic=False,
         harm="none", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=False, annex3_use=None, in_house=False, safety_component=False),
    dict(name="Patient-facing symptom checker",
         blurb="tells a member of the public whether to seek care, and how urgently",
         medical_purpose=True, informs_decision=True, diagnostic_or_therapeutic=True,
         harm="death", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=True, annex3_use=None, in_house=False, safety_component=False),
    dict(name="In-house readmission model",
         blurb="the hospital's own 30-day readmission score, used to target follow-up calls",
         medical_purpose=True, informs_decision=True, diagnostic_or_therapeutic=False,
         harm="none", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=True, annex3_use=None, in_house=True, safety_component=False),
    dict(name="Vendor readmission model",
         blurb="the same model, bought from a company and installed in forty hospitals",
         medical_purpose=True, informs_decision=True, diagnostic_or_therapeutic=False,
         harm="none", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=True, annex3_use=None, in_house=False, safety_component=False),
    dict(name="CV screening for nursing posts",
         blurb="ranks applicants for a band 5 nursing vacancy in the same hospital",
         medical_purpose=False, informs_decision=False, diagnostic_or_therapeutic=False,
         harm="none", monitors_physiology=False, vital_params=False, immediate_danger=False,
         annex1_product=False, annex3_use="employment", in_house=True, safety_component=False),
]

# ------------------------------------------------------------------ MDR Rule 11
def rule11(s, trace):
    """MDR Annex VIII Rule 11, as written. Returns a class string."""
    trace.append(("Is it software with a medical purpose, so a device at all?",
                  yn(s["medical_purpose"])))
    if not s["medical_purpose"]:
        trace.append(("Rule 11 does not apply: this is not a medical device.", ""))
        return "none"
    trace.append(("Does it provide information used to take decisions with a "
                  "diagnostic or therapeutic purpose?", yn(s["diagnostic_or_therapeutic"])))
    if s["diagnostic_or_therapeutic"]:
        trace.append(("  Could those decisions cause death or an irreversible "
                      "deterioration of health?", yn(s["harm"] == "death")))
        if s["harm"] == "death":
            return "III"
        trace.append(("  Could they cause serious deterioration, or a surgical "
                      "intervention?", yn(s["harm"] == "serious")))
        if s["harm"] == "serious":
            return "IIb"
        return "IIa"
    trace.append(("Is it intended to monitor physiological processes?",
                  yn(s["monitors_physiology"])))
    if s["monitors_physiology"]:
        trace.append(("  Vital physiological parameters, where variation could "
                      "put the patient in immediate danger?",
                      yn(s["vital_params"] and s["immediate_danger"])))
        if s["vital_params"] and s["immediate_danger"]:
            return "IIb"
        return "IIa"
    trace.append(("None of the above applies, so the residual limb of Rule 11.", ""))
    return "I"


def notified_body(cls):
    return cls in ("IIa", "IIb", "III")


# -------------------------------------------------------------------- AI Act
def ai_act(s, cls, trace):
    """Articles 6(1) and 6(2). Returns (tier, route, date)."""
    trace.append(("Is it a product, or a safety component of one, covered by "
                  "Union harmonisation legislation in Annex I?",
                  yn(s["annex1_product"] and s["medical_purpose"])))
    if s["annex1_product"] and s["medical_purpose"]:
        nb = notified_body(cls)
        trace.append(("  Must that product undergo third-party conformity "
                      "assessment under the sectoral act?", yn(nb)))
        if nb:
            return "HIGH RISK", "Art. 6(1), Annex I", "2 Aug 2028"
        trace.append(("  Class I self-certifies, so Art. 6(1) is not triggered.", ""))
    trace.append(("Is the intended purpose one of the Annex III use cases?",
                  s["annex3_use"] or "no"))
    if s["annex3_use"]:
        return "HIGH RISK", "Art. 6(2), Annex III", "2 Dec 2027"
    trace.append(("Does it interact with people, or generate synthetic content, "
                  "so that Art. 50 transparency applies?", "see note"))
    return "not high risk", "Art. 50 may still apply", "2 Aug 2026 for Art. 50"


def yn(b):
    return "yes" if b else "no"


# --------------------------------------------------------------------- reports
def report_trees():
    print("\nTWO TREES, ONE PRODUCT")
    print("""  The MDR asks what the software does to a patient. The AI Act asks whether
  somebody already has to check it. They are different questions, and running
  them together is the commonest mistake in this area.

  Rule 11 runs first, because Article 6(1) of the AI Act depends on its answer:
  a device that needs a notified body is automatically a high-risk AI system,
  and a class I device that self-certifies is not high-risk by that route.""")
    print("\n  %-30s %-9s %-7s %-13s %-22s %s"
          % ("system", "MDR class", "NB?", "AI Act", "route", "applies from"))
    for s in SYSTEMS:
        t = []
        cls = rule11(s, t)
        tier, route, date = ai_act(s, cls, t)
        print("  %-30s %-9s %-7s %-13s %-22s %s"
              % (s["name"][:30], cls, yn(notified_body(cls)), tier, route, date))
    print("""
  Read the last two columns together. Three of these systems are high risk from
  2 August 2028, one is high risk from 2 December 2027, and four are not high
  risk at all. Those are three different dates for things a hospital would
  describe in one sentence as "our AI projects".

  The row to argue about is the readmission model. It comes out class I here,
  because targeting follow-up telephone calls was judged not to be a decision
  with a diagnostic or therapeutic purpose. Change that one judgement and the
  model becomes class IIa, needs a notified body, and becomes a high-risk AI
  system from 2 August 2028. One word in an intended-purpose statement moves it,
  and the word is written by the manufacturer.""")


def report_paths():
    print("\nTHE PATH EACH SYSTEM TAKES")
    for s in SYSTEMS:
        t = []
        cls = rule11(s, t)
        tier, route, date = ai_act(s, cls, t)
        print("\n  " + s["name"].upper())
        print("  " + s["blurb"])
        for q, a in t:
            if a:
                print("    %-74s %s" % (q, a))
            else:
                print("    %s" % q)
        print("    => MDR class %s, notified body %s; %s under %s, from %s"
              % (cls, yn(notified_body(cls)), tier, route, date))
        if s["in_house"] and cls != "none":
            print("    NOTE: built in-house. Art. 5(5) may exempt it from CE marking,")
            print("          at the price of a quality management system, a justification")
            print("          that no equivalent CE-marked device meets the need, and a")
            print("          prohibition on giving it to any other legal entity.")


def report_cost():
    print("\nWHAT EACH ROUTE COSTS THE BUILDER")
    rows = [
        ("not a device, not high risk", "nothing under either instrument",
         "Art. 50 transparency if it talks to people or makes content"),
        ("class I device", "self-certify: technical documentation, declaration, CE mark",
         "no notified body; not high risk by the Art. 6(1) route"),
        ("class IIa or IIb device", "notified body audits the QMS and samples the file",
         "and the AI Act applies on top, from 2 Aug 2028"),
        ("class III device", "notified body assesses the design dossier itself",
         "plus the AI Act, plus clinical investigation expectations"),
        ("Annex III high risk", "no notified body for most of it, but Chapter III applies in full",
         "from 2 Dec 2027"),
        ("in-house, Art. 5(5)", "QMS, classification, GSPRs, clinical review, documentation",
         "and you may not transfer it to anybody"),
    ]
    print("  %-28s %-52s %s" % ("route", "what you must do", "and"))
    for r in rows:
        print("  %-28s %-52s %s" % r)
    print("""
  The jump that matters is between class I and class IIa, because that is where
  a notified body enters and the cost stops being a documentation exercise. Rule
  11 puts almost every piece of clinical decision support on the far side of it.
  In the Johner Institute's phrase, there is hardly any standalone software left
  that is class I.

  That is the real regulatory design choice in this area, and it was made in
  2017 in a classification rule, not in 2024 in the AI Act.""")


def main():
    args = set(sys.argv[1:])
    if not args or "--trees" in args:
        report_trees()
    if not args or "--paths" in args:
        report_paths()
    if not args or "--cost" in args:
        report_cost()


if __name__ == "__main__":
    main()
