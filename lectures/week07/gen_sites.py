#!/usr/bin/env python3
"""Build the two files Week 7 links together.

    python3 gen_sites.py

Writes three CSVs into data/:

    site_a.csv    a hospital patient register
    site_b.csv    a laboratory's own record of the same town
    truth.csv     which row in site_a is which row in site_b

WHY THIS FILE EXISTS
--------------------
The Lab 1 cohort is one file with one identifier, so nothing in it has to be
linked to anything. Record linkage needs two files that overlap in people and
share no key you can trust, and no public dataset gives you that together with
an answer key. So we build one.

Everything here is synthetic. No row corresponds to a real person. The names
are common Greek names; any resemblance to somebody you know is what happens
when a country has a few hundred surnames.

WHAT IS PLANTED, AND WHY
------------------------
The corruptions are not random noise. Each one stands for something that
happens in Greek health data, and each one defeats a different technique:

  feminine surnames      Papadopoulos / Papadopoulou. Defeats exact matching,
                         survives string similarity.
  transliteration        Chatzidakis / Hatzidakis / Xatzidakis. Defeats exact
                         matching, and the X form defeats similarity too.
  short forms            Emmanouil / Manolis, Paraskevi / Voula. Defeats
                         everything except a table of Greek name equivalences.
  missing postcode       The laboratory never needed one. Defeats blocking on
                         postcode, silently.
  missing AMKA           Captured for about half the laboratory rows. Defeats
                         any pipeline that joins on AMKA and stops.
  AMKA / birth date      A handful of AMKAs whose embedded date contradicts
    disagreement         the birth date beside them. Invisible to format checks.
                         The corrupted birth dates above add to this count, so
                         quality.py reports more disagreements than are planted
                         here. That is the honest number: both causes produce
                         the same symptom and the check cannot tell them apart.
  siblings               Three pairs sharing surname, birth date, address and
                         landline. These are the false positives, and no
                         threshold separates them.
  duplicate AMKA         Two site_a rows carrying the same AMKA, so that a join
                         on it multiplies those patients.

The seed is fixed, so everybody in the room gets the same files and the same
answer key, and the numbers in the slides stay true.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
SEED = 489
TODAY = dt.date(2026, 11, 1)

# (formal name, [short forms and variants the other system might hold])
MALE_NAMES = [
    ("Ioannis", ["Giannis", "Yannis", "Jannis"]),
    ("Georgios", ["Giorgos", "Yorgos", "Gewrgios"]),
    ("Konstantinos", ["Kostas", "Ntinos"]),
    ("Dimitrios", ["Dimitris", "Mimis"]),
    ("Nikolaos", ["Nikos"]),
    ("Emmanouil", ["Manolis", "Manos"]),
    ("Michail", ["Michalis"]),
    ("Athanasios", ["Thanasis", "Sakis"]),
    ("Eleftherios", ["Lefteris"]),
    ("Christos", ["Christakis"]),
    ("Panagiotis", ["Panos", "Takis"]),
    ("Vasileios", ["Vasilis"]),
    ("Antonios", ["Antonis"]),
    ("Stylianos", ["Stelios"]),
    ("Charalampos", ["Babis", "Charis"]),
    ("Evangelos", ["Vangelis"]),
    ("Petros", []),
    ("Andreas", []),
    ("Stavros", []),
    ("Theodoros", ["Thodoris"]),
]

FEMALE_NAMES = [
    ("Maria", ["Marietta"]),
    ("Eleni", ["Lenio"]),
    ("Aikaterini", ["Katerina", "Katina"]),
    ("Vasiliki", ["Vaso", "Vicky"]),
    ("Sophia", ["Sofia"]),
    ("Paraskevi", ["Voula", "Evi"]),
    ("Georgia", ["Giorgia"]),
    ("Dimitra", ["Mimi"]),
    ("Anna", []),
    ("Despoina", ["Despo"]),
    ("Chrysoula", ["Chrysa"]),
    ("Panagiota", ["Giota", "Penny"]),
    ("Anastasia", ["Natasa", "Sia"]),
    ("Kalliopi", ["Popi"]),
    ("Stavroula", ["Voula"]),
    ("Irini", ["Eirini"]),
    ("Zoi", []),
    ("Olga", []),
    ("Magdalini", ["Magda"]),
    ("Theodora", ["Dora"]),
]

# (masculine form, feminine form, [transliteration variants of the masculine])
SURNAMES = [
    ("Papadopoulos", "Papadopoulou", []),
    ("Chatzidakis", "Chatzidaki", ["Hatzidakis", "Xatzidakis"]),
    ("Giannakakis", "Giannakaki", ["Yannakakis"]),
    ("Vlachakis", "Vlachaki", ["Blachakis"]),
    ("Nikolaou", "Nikolaou", []),
    ("Maragkakis", "Maragkaki", ["Maragakis"]),
    ("Daskalakis", "Daskalaki", []),
    ("Kritikos", "Kritikou", []),
    ("Fragkiadakis", "Fragkiadaki", ["Frangiadakis"]),
    ("Psarakis", "Psaraki", []),
    ("Tzanakis", "Tzanaki", ["Dzanakis"]),
    ("Kalogeridis", "Kalogeridou", []),
    ("Markakis", "Markaki", []),
    ("Stavrakakis", "Stavrakaki", []),
    ("Theodorakis", "Theodoraki", []),
    ("Lambrakis", "Lambraki", ["Lamprakis"]),
    ("Sfakianakis", "Sfakianaki", []),
    ("Mavrakis", "Mavraki", []),
    ("Koutsoubelis", "Koutsoubeli", ["Koutsoumpelis"]),
    ("Papoutsakis", "Papoutsaki", []),
    ("Zacharioudakis", "Zacharioudaki", ["Zaharioudakis"]),
    ("Perakis", "Peraki", []),
    ("Saridakis", "Saridaki", []),
    ("Kefalogiannis", "Kefalogianni", ["Kefaloyannis"]),
    ("Manousakas", "Manousaka", []),
]

# Heraklion and the surrounding prefecture.
POSTCODES = ["70100", "71201", "71202", "71303", "71304", "71409",
             "70014", "70007", "72100", "73100", "74100"]

STREETS = ["Knossou", "Dikaiosynis", "Kalokairinou", "Ethnikis Antistaseos",
           "Leoforos 62 Martyron", "Smyrnis", "Idomeneos", "Arkoleontos",
           "Daidalou", "Chandakos", "Monis Odigitrias", "Papandreou"]


def amka_for(birth: dt.date, serial: int) -> str:
    """AMKA: the first six digits are the date of birth, DDMMYY."""
    return "%02d%02d%02d%05d" % (birth.day, birth.month, birth.year % 100, serial)


def typo(rng: random.Random, s: str) -> str:
    """One realistic keyboard slip."""
    if len(s) < 4:
        return s
    kind = rng.choice(["swap", "drop", "double", "sub"])
    i = rng.randrange(1, len(s) - 1)
    if kind == "swap":
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    if kind == "drop":
        return s[:i] + s[i + 1:]
    if kind == "double":
        return s[:i] + s[i] + s[i:]
    return s[:i] + rng.choice("aeiou") + s[i + 1:]


def main():
    rng = random.Random(SEED)
    os.makedirs(OUT, exist_ok=True)

    N_SHARED = 300          # people in both files
    N_A_ONLY = 97           # hospital patients the laboratory never saw
    N_B_ONLY = 77           # laboratory patients who were never admitted

    people = []
    serial = 10000
    for i in range(N_SHARED + N_A_ONLY + N_B_ONLY):
        sex = rng.choice(["M", "F"])
        if sex == "M":
            formal, shorts = rng.choice(MALE_NAMES)
            sur_m, sur_f, translit = rng.choice(SURNAMES)
            surname = sur_m
        else:
            formal, shorts = rng.choice(FEMALE_NAMES)
            sur_m, sur_f, translit = rng.choice(SURNAMES)
            surname = sur_f
        year = rng.randint(1935, 2010)
        birth = dt.date(year, rng.randint(1, 12), rng.randint(1, 28))
        serial += rng.randint(1, 7)
        people.append({
            "given": formal, "shorts": shorts,
            "surname": surname, "translit": translit, "masc": sur_m,
            "birth": birth, "sex": sex,
            "postcode": rng.choice(POSTCODES),
            "street": "%s %d" % (rng.choice(STREETS), rng.randint(1, 180)),
            "phone": "2810-%06d" % rng.randint(200000, 899999),
            "amka": amka_for(birth, serial),
        })

    shared = people[:N_SHARED]
    a_only = people[N_SHARED:N_SHARED + N_A_ONLY]
    b_only = people[N_SHARED + N_A_ONLY:]

    # ---- three sibling pairs ------------------------------------------
    # Same surname, same date of birth, same address, same landline, and a
    # different given name. One of each pair goes into each file, so the
    # linkage is offered a pair that agrees on everything it can measure.
    SIBLINGS = [
        ("Konstantinos", "Emmanouil", "M"),
        ("Georgios", "Ioannis", "M"),
        ("Maria", "Eleni", "F"),
    ]
    sibling_rows = []
    for idx, (name_a, name_b, sex) in enumerate(SIBLINGS):
        sur_m, sur_f, translit = SURNAMES[idx + 2]
        surname = sur_m if sex == "M" else sur_f
        birth = dt.date(1970 + idx * 4, 3 + idx, 14 + idx)
        serial += 11
        base = {
            "surname": surname, "translit": translit, "masc": sur_m,
            "birth": birth, "sex": sex,
            "postcode": POSTCODES[1 + idx],
            "street": "%s %d" % (STREETS[idx], 40 + idx),
            "phone": "2810-44%04d" % (5100 + idx),
        }
        twin_a = dict(base, given=name_a, shorts=[], amka=amka_for(birth, serial))
        twin_b = dict(base, given=name_b, shorts=[], amka=amka_for(birth, serial + 1))
        sibling_rows.append((twin_a, twin_b))

    # ---- site_a: the hospital register --------------------------------
    a_rows, truth = [], []
    a_index = {}
    for i, person in enumerate(shared + a_only):
        pid = "A%04d" % (i + 1)
        a_index[id(person)] = pid
        a_rows.append({
            "patient_id": pid,
            "given_name": person["given"],
            "surname": person["surname"],
            "birth_date": person["birth"].isoformat(),
            "sex": person["sex"],
            "address": person["street"],
            "postcode": person["postcode"],
            "phone": person["phone"],
            "amka": person["amka"],
            "registration_date": "",      # filled below
        })
    for twin_a, _ in sibling_rows:
        pid = "A%04d" % (len(a_rows) + 1)
        a_rows.append({
            "patient_id": pid, "given_name": twin_a["given"],
            "surname": twin_a["surname"], "birth_date": twin_a["birth"].isoformat(),
            "sex": twin_a["sex"], "address": twin_a["street"],
            "postcode": twin_a["postcode"], "phone": twin_a["phone"],
            "amka": twin_a["amka"], "registration_date": "",
        })

    # registration dates: mostly sensible, with two planted faults
    for i, row in enumerate(a_rows):
        birth = dt.date.fromisoformat(row["birth_date"])
        span = (TODAY - birth).days
        if i % 50 == 7:                       # ~2%: registered in the future
            d = TODAY + dt.timedelta(days=rng.randint(5, 400))
        elif i % 66 == 11:                    # ~1.5%: registered before birth
            d = birth - dt.timedelta(days=rng.randint(30, 3000))
        else:
            d = birth + dt.timedelta(days=rng.randint(max(1, span - 7000), span))
        row["registration_date"] = d.isoformat()

    # the hospital captures AMKA for most but not all of its patients
    for i, row in enumerate(a_rows):
        if i % 11 == 3:
            row["amka"] = ""

    # two pairs of site_a rows sharing an AMKA
    a_rows[5]["amka"] = a_rows[4]["amka"]
    a_rows[77]["amka"] = a_rows[76]["amka"]

    # ---- site_b: the laboratory's own record --------------------------
    b_rows = []
    b_source = list(shared)
    rng.shuffle(b_source)
    b_people = b_source + b_only

    for i, person in enumerate(b_people):
        pid = "B%04d" % (i + 1)
        given = person["given"]
        surname = person["surname"]
        birth = person["birth"]
        amka_val = person["amka"]

        # given name: a short form about a third of the time, a typo rarely
        if person["shorts"] and rng.random() < 0.34:
            given = rng.choice(person["shorts"])
        elif rng.random() < 0.06:
            given = typo(rng, given)

        # surname: sometimes a transliteration variant, sometimes the
        # masculine form written for a woman, sometimes a typo
        r = rng.random()
        if person["translit"] and r < 0.18:
            variant = rng.choice(person["translit"])
            surname = variant if person["sex"] == "M" else variant[:-1] if variant.endswith("s") else variant
        elif person["sex"] == "F" and r < 0.30:
            surname = person["masc"]
        elif r < 0.36:
            surname = typo(rng, surname)

        # birth date: a day/month swap, or a single digit wrong
        if rng.random() < 0.04 and birth.day <= 12:
            birth = dt.date(birth.year, birth.day, birth.month)
        elif rng.random() < 0.03:
            birth = dt.date(birth.year + rng.choice([-1, 1]), birth.month, birth.day)

        # postcode: the laboratory often did not ask
        postcode = person["postcode"] if rng.random() < 0.42 else ""
        # phone: captured more often than the postcode, still not always
        phone = person["phone"] if rng.random() < 0.55 else ""
        # AMKA: captured about half the time
        amka = amka_val if rng.random() < 0.51 else ""

        b_rows.append({
            "patient_id": pid,
            "given_name": given,
            "surname": surname,
            "birth_date": birth.isoformat(),
            "sex": person["sex"],
            "postcode": postcode,
            "phone": phone,
            "amka": amka,
            "sample_date": "",
        })
        if person in shared:
            truth.append((a_index[id(person)], pid))

    for _, twin_b in sibling_rows:
        pid = "B%04d" % (len(b_rows) + 1)
        b_rows.append({
            "patient_id": pid, "given_name": twin_b["given"],
            "surname": twin_b["surname"], "birth_date": twin_b["birth"].isoformat(),
            "sex": twin_b["sex"], "postcode": twin_b["postcode"],
            "phone": twin_b["phone"], "amka": twin_b["amka"], "sample_date": "",
        })

    # sample dates, with three planted faults
    for i, row in enumerate(b_rows):
        birth = dt.date.fromisoformat(row["birth_date"])
        span = max(1, (TODAY - birth).days)
        if i == 13:                          # a sample taken before birth
            d = birth - dt.timedelta(days=200)
        elif i in (41, 203):                 # samples dated in the future
            d = TODAY + dt.timedelta(days=rng.randint(10, 120))
        else:
            d = TODAY - dt.timedelta(days=rng.randint(0, min(900, span)))
        row["sample_date"] = d.isoformat()

    # ---- planted AMKA / birth date disagreements ----------------------
    # The AMKA is right and the birth date beside it is wrong, or the other
    # way round. Nothing about either field looks invalid on its own.
    changed = 0
    for row in b_rows:
        if changed >= 8:
            break
        if row["amka"]:
            b = dt.date.fromisoformat(row["birth_date"])
            try:
                shifted = b.replace(day=b.day + 1)
            except ValueError:
                continue
            row["birth_date"] = shifted.isoformat()
            changed += 1

    # one birth date in the future, and a handful of implausible ages
    b_rows[7]["birth_date"] = (TODAY + dt.timedelta(days=90)).isoformat()
    for j, row in enumerate(b_rows[20:26]):
        row["birth_date"] = dt.date(1899 + j, 6, 12).isoformat()

    # ---- write --------------------------------------------------------
    def write(name, rows):
        path = os.path.join(OUT, name)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        return path

    write("site_a.csv", a_rows)
    write("site_b.csv", b_rows)
    with open(os.path.join(OUT, "truth.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["a_id", "b_id"])
        w.writerows(sorted(truth))

    a_amka = sum(1 for r in a_rows if r["amka"])
    b_amka = sum(1 for r in b_rows if r["amka"])
    b_post = sum(1 for r in b_rows if r["postcode"])
    print("site_a.csv   %4d rows   AMKA %3d (%.0f%%)" % (len(a_rows), a_amka, 100.0 * a_amka / len(a_rows)))
    print("site_b.csv   %4d rows   AMKA %3d (%.0f%%)   postcode %3d (%.0f%%)"
          % (len(b_rows), b_amka, 100.0 * b_amka / len(b_rows), b_post, 100.0 * b_post / len(b_rows)))
    print("truth.csv    %4d pairs" % len(truth))
    print("possible pairs %d" % (len(a_rows) * len(b_rows)))
    print("planted: 3 sibling pairs, 2 shared AMKAs in site_a, %d AMKA/birth-date disagreements" % changed)


if __name__ == "__main__":
    main()
