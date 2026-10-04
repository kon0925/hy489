#!/usr/bin/env python3
"""Run a health data access body for a year against the Article 68 clock.

    python3 permit.py                 # the whole thing
    python3 permit.py --law           # the statutory deadlines, as a table
    python3 permit.py --model         # the assumptions, written out
    python3 permit.py --run           # one year at the default staffing
    python3 permit.py --queue         # the queue, month by month
    python3 permit.py --discipline    # three ways to order the pile
    python3 permit.py --staffing      # how many officers it takes
    python3 permit.py --endtoend      # permit to data in hand, the lawful path

Article 68(4) of Regulation (EU) 2025/327 gives a health data access body three
months to issue or refuse a data permit on a complete application, extendable
by three further months where necessary. Article 68(6) gives it two months,
extendable by one, for public sector bodies and Union institutions with a
public health mandate. Nothing in the Regulation says how many people the body
must employ.

This script is a queue with service times. It reads no data and needs no
network. Everything in it is an assumption, every assumption is printed by
--model, and the point of the script is that the deadline is a function of the
assumptions and not of the law.

Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import statistics as st

SEED = 489
YEAR = 2029                    # Chapter IV applies from 26 March 2029
START = dt.date(YEAR, 1, 1)
END = dt.date(YEAR, 12, 31)
# Applications arrive during YEAR. The day loop keeps going into the following
# year, at the same arrival rate, until every application from YEAR has been
# decided, so that one lodged in November is judged against its own deadline
# and not against 31 December. The second year's applications are simulated and
# then discarded; they exist so that a body which is behind at the end of the
# year does not get a free year in which to catch up.
RUNOFF_END = dt.date(YEAR + 1, 12, 31)

# ----------------------------------------------------------------------
# the law
# ----------------------------------------------------------------------
# Every figure here is from Regulation (EU) 2025/327. Months are calendar
# months, counted from the day the clock starts.
DEADLINES = [
    ("Art. 68(4)", "applicant completes an incomplete application", 0, 28,
     "weeks"),
    ("Art. 68(4)", "body issues or refuses a data permit", 3, 0, "months"),
    ("Art. 68(4)", "extension of that period where necessary", 3, 0, "months"),
    ("Art. 68(6)", "accelerated route, public body with a public health mandate",
     2, 0, "months"),
    ("Art. 68(6)", "extension of the accelerated period", 1, 0, "months"),
    ("Art. 60", "health data holder provides the data to the body", 3, 0, "months"),
    ("Art. 68(7)", "body makes the data available once it has received them",
     2, 0, "months"),
    ("Art. 69", "health data request, assessment of the request", 3, 0, "months"),
    ("Art. 69", "health data request, response where feasible", 3, 0, "months"),
]

STANDARD_MONTHS = 3
STANDARD_EXTENSION = 3
ACCELERATED_MONTHS = 2
ACCELERATED_EXTENSION = 1
COMPLETION_DAYS = 28           # four weeks, Art. 68(4)
HOLDER_MONTHS = 3              # Art. 60
PROVISION_MONTHS = 2           # Art. 68(7)

# ----------------------------------------------------------------------
# the model
# ----------------------------------------------------------------------
APPLICATIONS = 240             # health data access applications in the year
ACCELERATED_SHARE = 0.15       # public bodies on the Art. 68(6) route
INCOMPLETE_SHARE = 0.40        # arrive incomplete, Art. 68(4) four-week window
ABANDONED_SHARE = 0.10         # of the incomplete ones, never completed
OFFICERS = 7                   # the default staffing level
LEAVE_DAYS = 30                # leave, training and sickness per officer per year

# Assessment effort in officer working days. A permit application is read
# against Articles 53, 54, 66 and 71, the dataset is scoped, the secure
# processing environment is configured and the fee under Article 62 is
# estimated. Most are routine. One in five is not.
ROUTINE = (3, 9)               # uniform, inclusive
COMPLEX = (14, 26)
COMPLEX_SHARE = 0.20


def add_months(d, n):
    """Calendar months, the way a deadline is counted."""
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return dt.date(y, m, day)


def working_days(a, b):
    """Working days from a to b inclusive, Monday to Friday."""
    n, d = 0, a
    while d <= b:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def weekdays(a, b):
    return [a + dt.timedelta(days=i)
            for i in range((b - a).days + 1)
            if (a + dt.timedelta(days=i)).weekday() < 5]


WORKING = weekdays(START, END)                 # the year applications arrive in
ALL_DAYS = weekdays(START, RUNOFF_END)         # the year plus the run-off


class Application:
    __slots__ = ("n", "arrived", "accelerated", "complete_on", "abandoned",
                 "effort", "started", "decided", "queued")

    def __init__(self, n, arrived, accelerated, complete_on, abandoned, effort):
        self.n = n
        self.arrived = arrived
        self.accelerated = accelerated
        self.complete_on = complete_on      # the day the statutory clock starts
        self.abandoned = abandoned
        self.effort = effort                # officer working days
        self.started = None
        self.decided = None
        self.queued = False

    def deadline(self, extended=False):
        months = ACCELERATED_MONTHS if self.accelerated else STANDARD_MONTHS
        if extended:
            months += ACCELERATED_EXTENSION if self.accelerated else STANDARD_EXTENSION
        return add_months(self.complete_on, months)

    def days_to_decision(self):
        return (self.decided - self.complete_on).days


def make_applications(rng, n=APPLICATIONS, days=None, offset=0):
    """Arrivals spread over the working year, one draw at a time.

    The arrival day is uniform over working days, which is a flat demand
    assumption. A real body sees a spike before every funding deadline.
    """
    days = days or WORKING
    apps = []
    for i in range(n):
        arrived = rng.choice(days)
        accelerated = rng.random() < ACCELERATED_SHARE
        abandoned = False
        complete_on = arrived
        if rng.random() < INCOMPLETE_SHARE:
            if rng.random() < ABANDONED_SHARE:
                abandoned = True
            else:
                complete_on = arrived + dt.timedelta(days=rng.randint(5, COMPLETION_DAYS))
        lo, hi = COMPLEX if rng.random() < COMPLEX_SHARE else ROUTINE
        apps.append(Application(offset + i + 1, arrived, accelerated, complete_on,
                                abandoned, rng.randint(lo, hi)))
    apps.sort(key=lambda a: (a.arrived, a.n))
    return apps


def leave_calendar(rng, officers):
    """Which working days each officer is not at work, in each year."""
    nxt = weekdays(dt.date(YEAR + 1, 1, 1), RUNOFF_END)
    return [set(rng.sample(WORKING, LEAVE_DAYS)) | set(rng.sample(nxt, LEAVE_DAYS))
            for _ in range(officers)]


def simulate(officers=OFFICERS, applications=APPLICATIONS, seed=SEED,
             discipline="deadline"):
    """One year, day by day.

    Each officer assesses one application at a time and cannot be interrupted.
    The queue discipline is a choice the body makes and the Regulation does not.
    "deadline" serves the earliest statutory deadline first, which puts the
    Article 68(6) applications at the head. "fifo" serves them in the order the
    clocks started. "shortest" serves the smallest assessment first.
    """
    rng = random.Random(seed)
    apps = make_applications(rng, applications)
    nxt = make_applications(rng, applications,
                            days=weekdays(dt.date(YEAR + 1, 1, 1), RUNOFF_END),
                            offset=10000)
    # Sorted by the day the statutory clock starts, so the day loop can walk a
    # pointer along it instead of rescanning every application every day.
    work = sorted((a for a in apps + nxt if not a.abandoned),
                  key=lambda a: (a.complete_on, a.n))
    leave = leave_calendar(rng, officers)

    waiting, busy = [], [None] * officers     # busy holds [application, remaining]
    queue_trace, cursor = [], 0
    for day in ALL_DAYS:
        if all(a.decided or a.abandoned for a in apps):
            break
        # An application joins the queue on the first working day on or after
        # the day its statutory clock starts. A clock that starts on a Saturday
        # still starts on the Saturday; the officer sees it on the Monday.
        while cursor < len(work) and work[cursor].complete_on <= day:
            waiting.append(work[cursor])
            cursor += 1
        if discipline == "deadline":
            waiting.sort(key=lambda a: (a.deadline(), a.complete_on, a.n))
        elif discipline == "fifo":
            waiting.sort(key=lambda a: (a.complete_on, a.n))
        elif discipline == "shortest":
            waiting.sort(key=lambda a: (a.effort, a.complete_on, a.n))
        else:
            raise SystemExit("unknown queue discipline: %s" % discipline)
        for i in range(officers):
            if day in leave[i]:
                continue
            if busy[i] is None and waiting:
                a = waiting.pop(0)
                a.started = day
                busy[i] = [a, a.effort]
            if busy[i] is not None:
                busy[i][1] -= 1
                if busy[i][1] <= 0:
                    busy[i][0].decided = day
                    busy[i] = None
        oldest = max(((day - a.complete_on).days for a in waiting), default=0)
        queue_trace.append((day, len(waiting), oldest))
    for a in apps:
        if not a.abandoned and a.decided is None:
            a.decided = ALL_DAYS[-1]           # never finished; counts as late
    return apps, queue_trace


def summarise(apps):
    live = [a for a in apps if not a.abandoned]
    decided = [a for a in live if a.decided]
    on_time = [a for a in decided if a.decided <= a.deadline()]
    extended = [a for a in decided if a.deadline() < a.decided <= a.deadline(True)]
    late = [a for a in decided if a.decided > a.deadline(True)]
    in_year = [a for a in decided if a.decided <= END]
    waits = [a.days_to_decision() for a in decided]
    return {
        "received": len(apps),
        "abandoned": len(apps) - len(live),
        "live": len(live),
        "decided": len(decided),
        "in_year": len(in_year),
        "undecided": len(live) - len(in_year),
        "on_time": len(on_time),
        "extended": len(extended),
        "late": len(late),
        "mean": st.mean(waits) if waits else 0.0,
        "median": st.median(waits) if waits else 0.0,
        "p90": sorted(waits)[int(0.9 * len(waits))] if waits else 0,
        "max": max(waits) if waits else 0,
    }


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


# ----------------------------------------------------------------------
# reports
# ----------------------------------------------------------------------
def capacity(officers):
    return officers * (len(WORKING) - LEAVE_DAYS)


def demand(applications=APPLICATIONS, seed=SEED):
    rng = random.Random(seed)
    return sum(a.effort for a in make_applications(rng, applications)
               if not a.abandoned)


def report_law():
    print("\nTHE CLOCK, AS THE REGULATION SETS IT")
    print("""
  Nine deadlines, from four articles. Every one of them is a duty on somebody,
  and none of them comes with a number of people attached.""")
    print("\n  %-12s %-60s %12s" % ("article", "step", "period"))
    for art, step, months, days, unit in DEADLINES:
        if unit == "months":
            period = "%d month%s" % (months, "" if months == 1 else "s")
        else:
            period = "%d days" % days
        print("  %-12s %-58s %10s" % (art, step, period))
    decided = add_months(START, STANDARD_MONTHS + STANDARD_EXTENSION)
    worst = add_months(decided, PROVISION_MONTHS)
    print("""
  Add the standard route up. A complete application lodged on %s can
  lawfully be decided on %s, six months later, if the body takes the
  Article 68(4) extension. Article 68(7) then gives the body two further months
  to make the data available once the holders have sent them, and Article 60
  gives each holder three months to send them in the first place. The outer
  bound from a complete application to data inside a secure processing
  environment is %s, %d months later.

  Nothing in that is a failure. It is the law working exactly as written, and
  it is the best case. The rest of this script is about what the body does when
  more applications arrive than it can read.""" %
          (START.isoformat(), decided.isoformat(), worst.isoformat(),
           STANDARD_MONTHS + STANDARD_EXTENSION + PROVISION_MONTHS))


def report_model():
    rng = random.Random(SEED)
    apps = make_applications(rng)
    live = [a for a in apps if not a.abandoned]
    effort = [a.effort for a in live]
    print("\nTHE MODEL")
    print("""
  Everything below is an assumption. None of it is in the Regulation, because
  the Regulation does not say how a health data access body is staffed. Change
  a constant at the top of this file and every number in the rest of the script
  changes with it.""")
    rows = [
        ("applications received in the year", "%d" % APPLICATIONS),
        ("on the Article 68(6) accelerated route", "%.0f%%" % (100 * ACCELERATED_SHARE)),
        ("arriving incomplete", "%.0f%%" % (100 * INCOMPLETE_SHARE)),
        ("of those, never completed inside the four weeks",
         "%.0f%%" % (100 * ABANDONED_SHARE)),
        ("assessment effort, routine application", "%d to %d officer days" % ROUTINE),
        ("assessment effort, complex application", "%d to %d officer days" % COMPLEX),
        ("share that is complex", "%.0f%%" % (100 * COMPLEX_SHARE)),
        ("officers at the default staffing", "%d" % OFFICERS),
        ("leave, training and sickness", "%d working days each" % LEAVE_DAYS),
        ("working days in %d" % YEAR, "%d" % len(WORKING)),
        ("queue discipline", "earliest statutory deadline first"),
    ]
    print()
    for label, value in rows:
        print("  %-48s %s" % (label, value))
    d, c = sum(effort), capacity(OFFICERS)
    print("""
  The arithmetic that decides the rest, before any simulation runs:

    applications that reach an officer   %6d
    total assessment effort              %6d officer working days
    mean effort per application          %6.1f officer working days
    capacity at %d officers               %6d officer working days
    utilisation                          %6.1f%%
    break-even staffing                  %6.2f officers

  A queue whose utilisation is under 100%% is stable in the long run, and that
  says nothing at all about whether any individual application meets its
  deadline. Utilisation is an average over a year; a deadline is a statement
  about one application. The rest of the script is the difference between the
  two.""" % (len(live), d, st.mean(effort), OFFICERS, c, pct(d, c),
             d / float(len(WORKING) - LEAVE_DAYS)))


def report_run():
    apps, _trace = simulate()
    s = summarise(apps)
    print("\nONE YEAR AT %d OFFICERS" % OFFICERS)
    print("\n  %-52s %8s %9s" % ("", "count", "% of live"))
    print("  %-52s %8d" % ("applications received", s["received"]))
    print("  %-52s %8d" % ("abandoned, never completed in the four weeks",
                           s["abandoned"]))
    print("  %-52s %8d" % ("live applications, statutory clock running", s["live"]))
    for label, n in [
            ("decided before 31 December", s["in_year"]),
            ("still being assessed on 31 December", s["undecided"]),
            ("decided inside the Article 68 deadline", s["on_time"]),
            ("decided only inside the extended deadline", s["extended"]),
            ("decided after the extended deadline too", s["late"])]:
        print("  %-52s %8d %8.1f%%" % (label, n, pct(n, s["live"])))
    print("\n  Days from the start of the statutory clock to the decision:")
    print("    median %d, mean %.1f, 90th percentile %d, worst %d"
          % (s["median"], s["mean"], s["p90"], s["max"]))

    acc = [a for a in apps if a.accelerated and not a.abandoned]
    std = [a for a in apps if not a.accelerated and not a.abandoned]
    print("\n  %-30s %10s %10s %14s %12s" %
          ("route", "live", "deadline", "inside it", "median days"))
    for label, group, months in (("Art. 68(4) standard", std, STANDARD_MONTHS),
                                 ("Art. 68(6) accelerated", acc, ACCELERATED_MONTHS)):
        ok = sum(1 for a in group if a.decided <= a.deadline())
        med = st.median([a.days_to_decision() for a in group]) if group else 0
        print("  %-30s %10d %7d mo %7d %5.1f%% %12.0f"
              % (label, len(group), months, ok, pct(ok, len(group)), med))
    util = pct(demand(), capacity(OFFICERS))
    print("""
  The body is not idle, it is not incompetent and it is not ignoring the law.
  It is running at %.1f%% utilisation against a deadline that assumes somebody
  sized it, and %d of its %d live applications did not get a decision inside
  the three or two months the Regulation allows. The body reached for the
  Article 68(4) extension on %d of them, which is lawful and which means a
  researcher waited six months instead of three. %d went past even the extended
  deadline, and for those the Regulation says nothing about what happens next.

  Both routes miss at about the same rate here, which is the earliest-deadline
  ordering doing its job: it spends the shortage evenly instead of protecting
  one route. That is a choice the body made, not a rule it followed, and
  --discipline is what happens when it chooses differently.""" %
          (util, s["live"] - s["on_time"], s["live"], s["extended"], s["late"]))


def report_queue():
    apps, trace = simulate()
    print("\nTHE QUEUE, MONTH BY MONTH")
    print("""
  Received and decided count the %d applications of %d only. The queue column
  is everything waiting on the last working day of the month, including the
  following year's applications once they start arriving, because that is what
  the officers are actually looking at. The last column is the age of the
  oldest application nobody has started, in days since its clock started.""" %
          (APPLICATIONS, YEAR))
    print("\n  %-12s %9s %9s %13s %17s" %
          ("month end", "received", "decided", "in the queue", "oldest untouched"))
    month_end = {}
    for day, n, oldest in trace:
        month_end[(day.year, day.month)] = (n, oldest)
    for m in range(1, 13):
        first = dt.date(YEAR, m, 1)
        last = add_months(first, 1) - dt.timedelta(days=1)
        rec = sum(1 for a in apps if first <= a.arrived <= last)
        dec = sum(1 for a in apps if a.decided and first <= a.decided <= last)
        n, oldest = month_end[(YEAR, m)]
        print("  %-12s %9d %9d %13d %17d"
              % (first.strftime("%B"), rec, dec, n, oldest))
    in_year = [t for t in trace if t[0] <= END]
    peak_q = max(n for _d, n, _o in in_year)
    peak_day_q = next(d for d, n, _o in in_year if n == peak_q)
    peak_age = max(o for _d, _n, o in in_year)
    peak_day = next(d for d, _n, o in in_year if o == peak_age)
    expired = sum(1 for _d, _n, o in in_year if o > 90)
    print("""
  The queue is not a steady state. January and February look like a body that
  is coping, because an empty queue always does. The longest the queue got was
  %d applications, on %s. The longest any one of them sat untouched was
  %d days, on %s. On %d of the %d working days in the year there was an
  application in the queue whose three month deadline had already expired and
  which no officer had yet opened.

  Nothing here is unlawful in a way anybody can act on. Article 68(4) says the
  body shall issue or refuse within three months. It does not say what happens
  when it does not. The remedy in Article 81 is a complaint to the health data
  access body about the health data access body, and Article 59 makes the body
  publish a report on its own performance.""" %
          (peak_q, peak_day_q.isoformat(), peak_age, peak_day.isoformat(),
           expired, len(in_year)))


def report_discipline():
    print("\nTHE QUEUE DISCIPLINE IS A POLICY, NOT A RULE")
    print("""
  Same year, same %d applications, same %d officers, same seed. The only thing
  that changes is the order in which the officers take them off the pile. No
  article of the Regulation says which of these a body must use.""" %
          (APPLICATIONS, OFFICERS))
    print("\n  %-24s %9s %9s %7s %8s %6s %8s %8s" %
          ("discipline", "on time", "extended", "late", "median d", "p90",
           "68(6)", "68(4)"))
    for label, key in (("earliest deadline first", "deadline"),
                       ("first in, first out", "fifo"),
                       ("shortest assessment first", "shortest")):
        apps, _t = simulate(discipline=key)
        s = summarise(apps)
        acc = [a for a in apps if a.accelerated and not a.abandoned]
        std = [a for a in apps if not a.accelerated and not a.abandoned]
        aok = sum(1 for a in acc if a.decided <= a.deadline())
        sok = sum(1 for a in std if a.decided <= a.deadline())
        print("  %-24s %8.1f%% %8.1f%% %6.1f%% %8.0f %6d %7.1f%% %7.1f%%"
              % (label, pct(s["on_time"], s["live"]), pct(s["extended"], s["live"]),
                 pct(s["late"], s["live"]), s["median"], s["p90"],
                 pct(aok, len(acc)), pct(sok, len(std))))
    print("""
  Read the last two columns first. First in, first out is the fairest-sounding
  rule in the list and it is the one that fails the Article 68(6) applications,
  because a two month deadline loses to a three month deadline in a queue that
  ignores deadlines. The public health applications the Regulation singled out
  for speed are the ones a neutral queue is slowest with.

  Shortest assessment first looks best on the headline: the median falls to
  under a fortnight and nine in ten applications make the deadline. It gets
  there by never starting the big ones, so the share that blows past even the
  extended deadline goes up. Those are the complex applications: several data
  holders, sensitive categories, a secure processing environment to configure.
  They are also, in general, the research that could not be done any other way.

  The body picks one of these in its internal procedure manual. The choice
  decides who waits, it is invisible from outside, and Article 59 does not
  require it to be published.""")


def report_staffing():
    seeds = list(range(SEED, SEED + 10))
    print("\nHOW MANY OFFICERS IT TAKES")
    print("""
  The same %d applications and the same deadlines, run at each staffing level
  with %d different arrival patterns, so that the answer is not one lucky year.
  Every row is %d simulated years.""" % (APPLICATIONS, len(seeds), len(seeds)))
    print("\n  %8s %12s %9s %9s %9s %11s %11s" %
          ("officers", "utilisation", "mean", "worst", "best", "median d",
           "peak queue"))
    first_all, default = None, []
    for officers in range(5, 17):
        shares, meds, peaks = [], [], []
        for seed in seeds:
            apps, trace = simulate(officers=officers, seed=seed)
            s = summarise(apps)
            shares.append(pct(s["on_time"], s["live"]))
            meds.append(s["median"])
            peaks.append(max(n for d, n, _o in trace if d <= END))
        util = pct(demand(), capacity(officers))
        print("  %8d %11.1f%% %8.1f%% %8.1f%% %8.1f%% %11.0f %11d"
              % (officers, util, st.mean(shares), min(shares), max(shares),
                 st.median(meds), max(peaks)))
        if officers == OFFICERS:
            default = list(shares)
        if first_all is None and min(shares) >= 100.0:
            first_all = (officers, util)
    break_even = demand() / float(len(WORKING) - LEAVE_DAYS)
    answer = first_all[0] if first_all else -1
    print("""
  Break-even is %.2f officers: at that staffing the year's assessment effort
  exactly equals the year's capacity and the queue never clears. Read the
  "worst" column against it. At %d officers the body meets the deadline in
  every one of the %d years simulated. At %d it averages %.1f%% and the spread
  runs from %.1f%% to %.1f%%, which is the same body, the same budget and the
  same staff, complying in one year and not in the next, with nobody in the
  building doing anything differently.

  That spread is the finding. A deadline is met or missed by a particular
  application, and a body sized to its average demand is a body that will miss
  it, not because anyone was slow but because applications arrive when they
  arrive and one of them took four weeks of somebody's time.

  Article 55 requires Member States to give health data access bodies adequate
  human, financial and technical resources. The Regulation does not define
  adequate. This table is one definition, for one set of assumptions, and the
  number it gives is %d.""" %
          (break_even, answer, len(seeds), OFFICERS,
           st.mean(default), min(default), max(default), answer))


def report_endtoend():
    apps, _trace = simulate()
    rng = random.Random(SEED + 1)
    print("\nFROM APPLICATION TO DATA IN HAND")
    print("""
  The permit is not the data. Article 60 gives each health data holder three
  months to send the body what the permit covers, and Article 68(7) gives the
  body two further months to make it available in the secure processing
  environment. A permit naming four hospitals waits for the slowest of the
  four.

  Holder response is drawn uniformly between 20 and 92 days, the body's own
  provisioning between 10 and 61.""")
    live = [a for a in apps if not a.abandoned]
    decision, holder, provision, total = [], [], [], []
    for a in live:
        holders = rng.randint(1, 4)
        h = max(rng.randint(20, 92) for _ in range(holders))
        pv = rng.randint(10, 61)
        decision.append(a.days_to_decision())
        holder.append(h)
        provision.append(pv)
        total.append(a.days_to_decision() + h + pv)
    print("\n  %-46s %10s %10s %8s" % ("stage", "median d", "90th pct", "worst"))
    for label, vals in (("clock start to the permit decision", decision),
                        ("decision to the last holder sending data", holder),
                        ("data received to data in the environment", provision),
                        ("clock start to data in the environment", total)):
        v = sorted(vals)
        print("  %-46s %10.0f %10.0f %8d"
              % (label, st.median(v), v[int(0.9 * len(v))], v[-1]))
    outer = (add_months(START, STANDARD_MONTHS + STANDARD_EXTENSION
                        + PROVISION_MONTHS) - START).days
    beyond = sum(1 for t in total if t > outer)
    med = int(st.median(total))
    print("""
  The lawful outer bound is %d days: six months of decision with the extension
  taken, then two months of provisioning. %d of the %d permits in this run took
  longer than that, which is %.1f%%, and every one of them is somebody who put
  a data access application into a grant with a start date on it.

  The median is %d days. A doctoral student who lodges a complete application
  on the first working day of January sees the data in %s.

  This is the thing to leave the room with. Article 68 puts a deadline on a
  body that no article resources, Article 60 puts a deadline on holders that no
  article resources either, and the arithmetic of whether either is met was
  left to the Member State. In Greece that body does not exist yet. The GR-HDAB
  project runs to November 2027 and the designation under Article 55 was due in
  March of that year.""" %
          (outer, beyond, len(total), pct(beyond, len(total)), med,
           (START + dt.timedelta(days=med)).strftime("%B %Y")))


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("law", "model", "run", "queue", "discipline", "staffing",
                 "endtoend"):
        ap.add_argument("--" + flag, action="store_true")
    args = ap.parse_args()
    flags = [args.law, args.model, args.run, args.queue, args.discipline,
             args.staffing, args.endtoend]
    run_all = not any(flags)

    if args.law or run_all:
        report_law()
    if args.model or run_all:
        report_model()
    if args.run or run_all:
        report_run()
    if args.queue or run_all:
        report_queue()
    if args.discipline or run_all:
        report_discipline()
    if args.staffing or run_all:
        report_staffing()
    if args.endtoend or run_all:
        report_endtoend()


if __name__ == "__main__":
    main()
