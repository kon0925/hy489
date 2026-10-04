#!/usr/bin/env python3
"""Generate a hospital access log, then try to find the snooping in it.

    python3 accesslog.py              # the whole thing
    python3 accesslog.py --log        # how the log is built, and what is in it
    python3 accesslog.py --self       # self-lookup and same-surname lookup
    python3 accesslog.py --treat      # access with no treatment relationship
    python3 accesslog.py --volume     # a user far above their own baseline
    python3 accesslog.py --vip        # the flagged record
    python3 accesslog.py --hours      # after hours, and bulk export
    python3 accesslog.py --review     # what the whole alert set costs to read

Audit logging is the control every hospital claims. It is also the control
that most often does nothing, because the log is written, retained, shown to
the auditor, and never read. The question this script asks is not whether the
events are recorded. It is whether a person could work through what the
detectors produce.

The log is synthetic and seeded, so every number here is reproducible. The
cohort is the Lab 1 cohort. The staff do not exist.

Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
from collections import Counter, defaultdict

from common import SEED, TOWN, TOWNS, pct, read

START_DAY = dt.date(2026, 10, 26)      # a Monday
N_DAYS = 26                            # four weeks and two days, weekends included
WORK_START, WORK_END = 7, 20           # the hours a daytime access is unremarkable

ROLES = [
    # role, how many, accesses per person per working day
    ("clinician", 16, (12, 30)),
    ("nurse", 10, (20, 45)),
    ("reception", 8, (30, 60)),
    ("lab", 4, (15, 30)),
    ("billing", 4, (25, 50)),
    ("it", 2, (2, 8)),
]
CLINICAL = ("clinician", "nurse")

# The planted incidents. Each one is a label on the events it generated, and
# the detectors never see the labels.
PLANTED = ["self", "kin", "browse", "volume", "vip", "night", "bulk"]


# ----------------------------------------------------------------------
# the people
# ----------------------------------------------------------------------
def build_staff(rng, patients):
    """Invent a staff list, with three members who are also in the cohort.

    A hospital employs people from the population it serves. Three of these
    staff have a patient record in the same system they log into, which is the
    ordinary situation and the reason self-lookup is worth detecting.
    """
    firsts = sorted({p["FIRST"] for p in patients})
    lasts = sorted({p["LAST"] for p in patients})
    staff = []
    used = set()
    for role, count, rate in ROLES:
        for _ in range(count):
            while True:
                first, last = rng.choice(firsts), rng.choice(lasts)
                uid = "%s.%s" % (first[0].lower(), last.lower())
                if uid not in used:
                    used.add(uid)
                    break
            staff.append({
                "user": uid,
                "first": first,
                "last": last,
                "role": role,
                "town": rng.choice(TOWNS),
                "rate": rng.randint(*rate),
                "patient_id": "",          # filled in below for three of them
                "panel": set(),
            })
    # three staff are also patients, matched on their own name where possible
    by_name = defaultdict(list)
    for p in patients:
        by_name[(p["FIRST"], p["LAST"])].append(p["Id"])
    employees = [s for s in staff if by_name.get((s["first"], s["last"]))]
    for s in employees[:3]:
        s["patient_id"] = sorted(by_name[(s["first"], s["last"])])[0]
    return staff


def build_panels(rng, staff, patients, encounters):
    """Who has ever treated whom, taken from encounters.csv.

    The source file records four providers for thirteen thousand encounters,
    which is a property of the generator and not of any hospital. We spread
    those encounters over the clinical staff: a patient has one named
    clinician, and four encounters in five go to that clinician, the rest to
    whoever was covering.
    """
    clinical = [s for s in staff if s["role"] in CLINICAL]
    primary = {}
    for p in sorted(patients, key=lambda r: r["Id"]):
        primary[p["Id"]] = rng.choice(clinical)["user"]
    by_user = {s["user"]: s for s in staff}
    for e in encounters:
        pid = e["PATIENT"]
        if pid not in primary:
            continue
        if rng.random() < 0.8:
            by_user[primary[pid]]["panel"].add(pid)
        else:
            by_user[rng.choice(clinical)["user"]]["panel"].add(pid)
    return primary


# ----------------------------------------------------------------------
# the log
# ----------------------------------------------------------------------
def stamp(rng, day, label=None):
    """A plausible time of day. Most access is in clinic hours."""
    if label == "night":
        hour = rng.randint(2, 4)
    else:
        r = rng.random()
        if r < 0.90:
            hour = rng.randint(WORK_START + 1, WORK_END - 2)
        elif r < 0.98:
            hour = rng.choice([WORK_START, WORK_END - 1, WORK_END])
        else:
            hour = rng.choice([5, 6, 21, 22, 23])
    return dt.datetime.combine(day, dt.time(hour, rng.randint(0, 59), rng.randint(0, 59)))


def generate(rng, staff, patients, primary, vips):
    pids = sorted(p["Id"] for p in patients)
    town_of = {p["Id"]: TOWN[p["ZIP"]] for p in patients}
    by_town = defaultdict(list)
    for pid in pids:
        by_town[town_of[pid]].append(pid)
    days = [START_DAY + dt.timedelta(days=i) for i in range(N_DAYS)]
    events = []

    def add(user, pid, when, action="view", label=""):
        events.append({"ts": when, "user": user["user"], "role": user["role"],
                       "patient": pid, "action": action, "label": label})

    # --- ordinary work -------------------------------------------------
    for s in staff:
        panel = sorted(s["panel"])
        town_pool = by_town[s["town"]]
        for day in days:
            weekend = day.weekday() >= 5
            if weekend and not (s["role"] in CLINICAL and s["rate"] % 4 == 0):
                continue
            n = int(rng.gauss(s["rate"], s["rate"] * 0.2))
            if weekend:
                n = max(1, n // 4)
            for _ in range(max(0, n)):
                if s["role"] in CLINICAL and panel and rng.random() < 0.92:
                    pid = rng.choice(panel)
                elif s["role"] == "reception":
                    pid = rng.choice(town_pool)
                else:
                    pid = rng.choice(pids)
                action = "view"
                r = rng.random()
                if r > 0.97:
                    action = "print"
                elif r > 0.94:
                    action = "amend"
                add(s, pid, stamp(rng, day), action)

    # --- planted incident 1: three staff look themselves up -------------
    for s in [x for x in staff if x["patient_id"]]:
        for _ in range(rng.randint(2, 4)):
            day = rng.choice(days)
            add(s, s["patient_id"], stamp(rng, day), "view", "self")

    # --- planted incident 2: four staff look up a relative --------------
    kin_staff = [s for s in staff if not s["patient_id"]][:4]
    for s in kin_staff:
        same = [pid for pid in pids
                if pid not in s["panel"] and name_of(patients, pid)[1] == s["last"]]
        if not same:
            continue
        pid = rng.choice(same)
        for _ in range(rng.randint(1, 3)):
            add(s, pid, stamp(rng, rng.choice(days)), "view", "kin")

    # --- planted incident 3: two staff browse records they never treated -
    browsers = [s for s in staff if s["role"] in CLINICAL][-2:]
    for s in browsers:
        outside = [pid for pid in pids if pid not in s["panel"]]
        day = rng.choice(days)
        for pid in rng.sample(outside, 22):
            add(s, pid, stamp(rng, day), "view", "browse")

    # --- planted incident 4: one user has a day eight times their usual -
    heavy = [s for s in staff if s["role"] == "clinician"][3]
    day = days[11]
    for _ in range(heavy["rate"] * 8):
        pid = rng.choice(pids)
        add(heavy, pid, stamp(rng, day), "view", "volume")

    # --- planted incident 5: the flagged record -------------------------
    care_team = {v: {primary[v]} for v in vips}
    for s in staff:
        for v in vips:
            if v in s["panel"]:
                care_team[v].add(s["user"])
    outsiders = [s for s in staff if s["role"] in CLINICAL]
    for v in vips[:3]:
        for s in rng.sample([x for x in outsiders if x["user"] not in care_team[v]], 2):
            add(s, v, stamp(rng, rng.choice(days)), "view", "vip")

    # --- planted incident 6: one user working at three in the morning ---
    owl = [s for s in staff if s["role"] == "nurse"][2]
    for day in (days[4], days[18]):
        for _ in range(6):
            add(owl, rng.choice(pids), stamp(rng, day, "night"), "view", "night")

    # --- planted incident 7: one bulk export ----------------------------
    exporter = [s for s in staff if s["role"] == "billing"][0]
    base = dt.datetime.combine(days[20], dt.time(16, 5))
    for i, pid in enumerate(rng.sample(pids, 180)):
        add(exporter, pid, base + dt.timedelta(seconds=7 * i), "export", "bulk")

    events.sort(key=lambda e: (e["ts"], e["user"], e["patient"]))
    return events


def name_of(patients, pid):
    if not hasattr(name_of, "_idx"):
        name_of._idx = {p["Id"]: (p["FIRST"], p["LAST"]) for p in patients}
    return name_of._idx[pid]


# ----------------------------------------------------------------------
# detectors
# ----------------------------------------------------------------------
def d_self(events, staff, ctx):
    own = {s["user"]: s["patient_id"] for s in staff if s["patient_id"]}
    return [e for e in events if own.get(e["user"]) == e["patient"]]


def d_kin(events, staff, ctx):
    last = {s["user"]: s["last"] for s in staff}
    return [e for e in events if last[e["user"]] == ctx["surname"][e["patient"]]]


def d_untreated(events, staff, ctx):
    panels = {s["user"]: s["panel"] for s in staff}
    return [e for e in events if e["role"] in CLINICAL
            and e["patient"] not in panels[e["user"]]]


def d_volume(events, staff, ctx):
    """A user-day far above that user's own median and above their peers.

    Two conditions, because either one alone is wrong. A user who is always
    busy fails a peer-group test every day of their life. A quiet user who
    doubles their quiet baseline is not an incident.
    """
    per_day = Counter((e["user"], e["ts"].date()) for e in events)
    by_user = defaultdict(list)
    for (user, day), n in per_day.items():
        by_user[user].append(n)
    role_of = {s["user"]: s["role"] for s in staff}
    peer = defaultdict(list)
    for user, counts in by_user.items():
        peer[role_of[user]].extend(counts)
    peer_p95 = {}
    for role, counts in peer.items():
        counts = sorted(counts)
        peer_p95[role] = counts[min(len(counts) - 1, int(0.95 * len(counts)))]
    flagged = set()
    for user, counts in by_user.items():
        med = sorted(counts)[len(counts) // 2]
        for (u, day), n in per_day.items():
            if u == user and n > 3 * med and n > peer_p95[role_of[user]]:
                flagged.add((user, day))
    return [e for e in events if (e["user"], e["ts"].date()) in flagged]


def d_vip(events, staff, ctx):
    return [e for e in events if e["patient"] in ctx["vips"]
            and e["user"] not in ctx["care_team"][e["patient"]]]


def d_hours(events, staff, ctx):
    out = []
    for e in events:
        t = e["ts"]
        if t.weekday() >= 5 or t.hour < WORK_START or t.hour >= WORK_END:
            out.append(e)
    return out


def d_bulk(events, staff, ctx, window=30, distinct=50):
    """At least `distinct` separate patients opened by one user in `window`
    minutes. A sliding window over each user's own stream."""
    by_user = defaultdict(list)
    for e in events:
        by_user[e["user"]].append(e)
    out = []
    for user, stream in by_user.items():
        stream.sort(key=lambda e: e["ts"])
        i = 0
        hit = set()
        for j in range(len(stream)):
            while (stream[j]["ts"] - stream[i]["ts"]).total_seconds() > window * 60:
                i += 1
            if len({s["patient"] for s in stream[i:j + 1]}) >= distinct:
                hit.update(range(i, j + 1))
        out.extend(stream[k] for k in sorted(hit))
    return out


DETECTORS = [
    ("self-lookup", "self", d_self),
    ("same surname", "kin", d_kin),
    ("no treatment relationship", "browse", d_untreated),
    ("daily volume outlier", "volume", d_volume),
    ("access to a flagged record", "vip", d_vip),
    ("outside working hours", "night", d_hours),
    ("bulk export", "bulk", d_bulk),
]


def score(alerts, label):
    """alerts, the planted events of this kind, planted events of another kind,
    and the rest. The third number matters: a detector that catches somebody
    else's incident is not raising a false alarm, and counting it as one is an
    artefact of how the scoring is written."""
    tp = [e for e in alerts if e["label"] == label]
    other = [e for e in alerts if e["label"] and e["label"] != label]
    noise = [e for e in alerts if not e["label"]]
    return len(alerts), len(tp), len(other), len(noise)


# ----------------------------------------------------------------------
# reporting
# ----------------------------------------------------------------------
def report_log(events, staff, patients, ctx):
    days = len({e["ts"].date() for e in events})
    print("\nTHE LOG")
    print("  %-34s %8d" % ("events", len(events)))
    print("  %-34s %8d" % ("staff accounts", len(staff)))
    print("  %-34s %8d" % ("patients in the cohort", len(patients)))
    print("  %-34s %8d" % ("patients touched at least once", len({e["patient"] for e in events})))
    print("  %-34s %8d" % ("calendar days", days))
    print("  %-34s %8.0f" % ("events per day", len(events) / days))
    print("\n  by role:")
    byrole = Counter(e["role"] for e in events)
    users = Counter(s["role"] for s in staff)
    for role, _, _ in ROLES:
        print("    %-12s %3d users %8d events  %6.0f per user per day"
              % (role, users[role], byrole[role], byrole[role] / users[role] / days))
    print("\n  by action:")
    for action, n in Counter(e["action"] for e in events).most_common():
        print("    %-12s %8d  %5.1f%%" % (action, n, pct(n, len(events))))
    planted = Counter(e["label"] for e in events if e["label"])
    print("\n  planted inside it, %d events in seven incidents:" % sum(planted.values()))
    for label in PLANTED:
        print("    %-12s %5d" % (label, planted[label]))
    print("""
  Everything above this line is the generator. Everything below it is a
  detector that has never seen the labels. The detectors get the log, the
  staff list and the treatment relationships, which is what a real audit team
  has.""")


def report_detector(name, label, alerts, events, days, note):
    n, tp, other, noise = score(alerts, label)
    planted = sum(1 for e in events if e["label"] == label)
    print("\n  %s" % name.upper())
    print("    %-32s %7d   %8.1f per day" % ("alerts", n, n / days))
    print("    %-32s %7d   %8d found" % ("planted events of this kind", planted, tp))
    print("    %-32s %7d   %7.1f%% of the alerts" % ("part of a different incident", other, pct(other, n)))
    print("    %-32s %7d   %7.1f%% of the alerts" % ("ordinary work", noise, pct(noise, n)))
    print()
    for line in note.strip("\n").split("\n"):
        print("    %s" % line)


def report_self(events, staff, ctx, days):
    print("\nDETECTOR 1 AND 2: THE PERSON, NOT THE RECORD")
    report_detector("self-lookup", "self", d_self(events, staff, ctx), events, days, """
A staff member opening their own chart. The rule is an equality test between
two identifiers the hospital already holds, so it cannot be wrong, and it is
the only detector in this script with that property. It is also the easiest
rule to defeat: ask a colleague.""")
    report_detector("same surname", "kin", d_kin(events, staff, ctx), events, days, """
A staff member opening the chart of somebody who shares their surname. This
cohort holds 20 surnames across 1,174 patients, so roughly one access in
twenty matches by chance, and the detector drowns. Real registers are wider
than this one, and in Crete they are not much wider: a surname match is a
reason to look, never a finding.""")


def report_treat(events, staff, ctx, days):
    print("\nDETECTOR 3: NO TREATMENT RELATIONSHIP")
    alerts = d_untreated(events, staff, ctx)
    report_detector("no treatment relationship", "browse", alerts, events, days, """
A clinician or nurse opening a record for a patient with no encounter of
theirs anywhere in the history. The planted browsing is in there. So is every
cover shift, every second opinion, every handover and every triage.""")
    by_user = Counter(e["user"] for e in alerts)
    worst = by_user.most_common(5)
    print("\n    the five noisiest accounts under this rule:")
    for user, n in worst:
        planted = sum(1 for e in alerts if e["user"] == user and e["label"] == "browse")
        print("      %-18s %5d alerts   %4d of them planted" % (user, n, planted))
    print("""
    The account at the top is not one of the browsers. It is the volume
    incident from detector 4, which produced 162 accesses in a day and almost
    none of them inside a panel. The two planted browsers come second and
    fourth. Ranking by count is what puts all three in front of a human; the
    rule itself separated nothing.""")


def report_volume(events, staff, ctx, days):
    print("\nDETECTOR 4: DAILY VOLUME")
    alerts = d_volume(events, staff, ctx)
    report_detector("daily volume outlier", "volume", alerts, events, days, """
A user-day above three times that user's own median and above the 95th
percentile of their role. Both tests have to fire. Dropping either one of
them is the standard way this detector gets switched off within a month.""")
    flagged = sorted({(e["user"], e["ts"].date(), e["role"]) for e in alerts})
    print("\n    user-days flagged: %d" % len(flagged))
    per_day = Counter((e["user"], e["ts"].date()) for e in events)
    for user, day, role in flagged:
        counts = sorted(n for (u, d), n in per_day.items() if u == user)
        med = counts[len(counts) // 2]
        print("      %-18s %-10s %-10s %4d accesses, median %3d, ratio %.1f"
              % (user, role, day.isoformat(), per_day[(user, day)], med,
                 per_day[(user, day)] / med))


def report_vip(events, staff, ctx, days):
    print("\nDETECTOR 5: THE FLAGGED RECORD")
    print("  Six patients are marked. In a real system the mark goes on a politician,")
    print("  a footballer, a colleague, or a patient who asked for it after a court")
    print("  case. Any access from outside the named care team raises an alert.")
    report_detector("access to a flagged record", "vip", d_vip(events, staff, ctx),
                    events, days, """
Six in a hundred alerts are the planted accesses. Detector 3 runs at four in
a hundred, so the rule is no sharper. The difference is volume. Four alerts a
day is a queue one person can read to the bottom every morning, and reading
it to the bottom is how the six get found. The rule did not improve. The
watched population got smaller, and shrinking the watched population is the
only move in this script that changes the arithmetic of reviewing.""")


def report_hours(events, staff, ctx, days):
    print("\nDETECTOR 6 AND 7: WHEN, AND HOW MUCH AT ONCE")
    report_detector("outside working hours", "night", d_hours(events, staff, ctx),
                    events, days, """
Anything before 07:00, after 20:00, or at a weekend. A hospital runs at
night, so this fires on the night shift, the weekend cover and the planted
pair of three-in-the-morning sessions without distinguishing them.""")
    alerts = d_bulk(events, staff, ctx)
    report_detector("bulk export", "bulk", alerts, events, days, """
Fifty distinct patients inside a thirty-minute window. This is the one
pattern in the script that corresponds to the thing people actually fear,
which is a copy of the database leaving the building.""")
    if alerts:
        users = Counter(e["user"] for e in alerts)
        print("\n    accounts flagged: %s" % ", ".join("%s (%d)" % kv for kv in users.most_common()))


def n_planted_found(events, staff, ctx):
    """Planted events caught by at least one of the seven detectors."""
    caught = set()
    for _, _, fn in DETECTORS:
        for e in fn(events, staff, ctx):
            if e["label"]:
                caught.add(id(e))
    return len(caught)


def report_review(events, staff, ctx, days):
    print("\nWHAT THE WHOLE ALERT SET COSTS")
    print("  %-30s %8s %8s %8s %9s %9s"
          % ("detector", "alerts", "per day", "planted", "found", "precision"))
    total = 0
    union = set()
    for name, label, fn in DETECTORS:
        alerts = fn(events, staff, ctx)
        n, tp, other, noise = score(alerts, label)
        planted = sum(1 for e in events if e["label"] == label)
        total += n
        union.update(id(e) for e in alerts)
        print("  %-30s %8d %8.1f %8d %9d %8.1f%%"
              % (name, n, n / days, planted, tp, pct(tp, n)))
    n_planted = sum(1 for e in events if e["label"])
    print("  %-30s %8d %8.1f %8d %9s %8s"
          % ("all seven, events once each", len(union), len(union) / days,
             n_planted, "", ""))
    per_day = len(union) / days
    print("""
  Read the per-day column, then decide who reads it. %.0f alerts a day, at one
  minute each, is %.1f hours of one person's morning, every morning, to find
  seven incidents in %d days. Precision across the seven rules is %.1f%%.

  That is the failure mode of audit logging. The log was complete, the
  detectors fired, and the alerts went into a queue nobody was staffed to
  read. Most published cases of a member of staff reading a neighbour's chart
  came to light the other way round: somebody complained, and the log was
  consulted afterwards to confirm what had already been alleged.

  Three ways out, and none of them is a better rule. Shrink the watched
  population, which is detector 5. Rank instead of alert, which is what made
  detector 3 usable. Or tell the staff the log is read, and read enough of it
  that the claim is true.""" % (per_day, per_day / 60.0, days,
                                pct(n_planted_found(events, staff, ctx), len(union))))


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("log", "self", "treat", "volume", "vip", "hours", "review"):
        ap.add_argument("--" + flag, action="store_true")
    args = ap.parse_args()
    chosen = [args.log, args.self, args.treat, args.volume, args.vip, args.hours, args.review]
    run_all = not any(chosen)

    rng = random.Random(SEED)
    patients = read("patients.csv")
    encounters = read("encounters.csv")
    staff = build_staff(rng, patients)
    primary = build_panels(rng, staff, patients, encounters)
    vips = sorted(rng.sample(sorted(p["Id"] for p in patients), 6))
    events = generate(rng, staff, patients, primary, vips)

    care_team = {v: {primary[v]} for v in vips}
    for s in staff:
        for v in vips:
            if v in s["panel"]:
                care_team[v].add(s["user"])
    ctx = {"surname": {p["Id"]: p["LAST"] for p in patients},
           "vips": set(vips), "care_team": care_team}
    days = len({e["ts"].date() for e in events})

    if args.log or run_all:
        report_log(events, staff, patients, ctx)
    if args.self or run_all:
        report_self(events, staff, ctx, days)
    if args.treat or run_all:
        report_treat(events, staff, ctx, days)
    if args.volume or run_all:
        report_volume(events, staff, ctx, days)
    if args.vip or run_all:
        report_vip(events, staff, ctx, days)
    if args.hours or run_all:
        report_hours(events, staff, ctx, days)
    if args.review or run_all:
        report_review(events, staff, ctx, days)


if __name__ == "__main__":
    main()
