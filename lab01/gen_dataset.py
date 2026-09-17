#!/usr/bin/env python3
"""Generate a synthetic cohort in Synthea's CSV schema for HY-489 Lab 1.

Deterministic (fixed seed) so every student gets the same numbers.
Not real data and not produced by Synthea: a compact stand-in with the
same column names and shape, so the lab runs without a large download.
"""
import csv, random, datetime as dt, uuid, pathlib

random.seed(489)
OUT = pathlib.Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)
N_PATIENTS = 1174
TODAY = dt.date(2026, 9, 28)

FIRST_F = ["Maria","Eleni","Katerina","Sofia","Anna","Georgia","Dimitra","Ioanna","Vasiliki","Christina","Angeliki","Despina"]
FIRST_M = ["Georgios","Ioannis","Nikolaos","Dimitrios","Konstantinos","Panagiotis","Christos","Vasilios","Michail","Andreas","Stavros","Emmanouil"]
LAST = ["Papadaki","Nikolaou","Georgiou","Vasileiou","Antoniou","Makris","Stefanidis","Christodoulou","Manolakis","Fragkaki","Dimitriou","Petrakis",
        "Samaras","Kalogeraki","Vlachos","Tsakiris","Markakis","Sfakianakis","Daskalaki","Zervas"]
CITIES = [("Heraklion","71201"),("Chania","73100"),("Rethymno","74100"),("Agios Nikolaos","72100"),("Ierapetra","72200"),("Sitia","72300")]
ORGS = ["PAGNI University Hospital","Venizeleio General Hospital","Chania General Hospital","Rethymno Health Centre"]

ENC_KINDS = [
    ("ambulatory","162673000","General examination of patient (procedure)",0.34),
    ("wellness","410620009","Well child visit (procedure)",0.18),
    ("outpatient","185349003","Encounter for check up (procedure)",0.22),
    ("emergency","50849002","Emergency room admission (procedure)",0.10),
    ("urgentcare","702927004","Urgent care clinic (procedure)",0.10),
    ("inpatient","32485007","Hospital admission (procedure)",0.06),
]
CONDITIONS = [
    ("59621000","Essential hypertension (disorder)",0.155),
    ("195662009","Acute viral pharyngitis (disorder)",0.140),
    ("72892002","Normal pregnancy (finding)",0.100),
    ("15777000","Prediabetes (finding)",0.092),
    ("271737000","Anemia (disorder)",0.085),
    ("44054006","Type 2 diabetes mellitus (disorder)",0.072),
    ("40055000","Chronic sinusitis (disorder)",0.065),
    ("239873007","Osteoarthritis of knee (disorder)",0.058),
    ("233678006","Childhood asthma (disorder)",0.052),
    ("162864005","Body mass index 30+ - obesity (finding)",0.048),
    ("38341003","Hypertensive disorder, systemic arterial (disorder)",0.045),
    ("55822004","Hyperlipidemia (disorder)",0.042),
    ("196416002","Otitis media (disorder)",0.026),
    ("444814009","Viral sinusitis (disorder)",0.020),
]
MEDS = [
    ("308136","amLODIPine 5 MG Oral Tablet","59621000","Essential hypertension (disorder)"),
    ("314076","lisinopril 10 MG Oral Tablet","59621000","Essential hypertension (disorder)"),
    ("860975","24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet","44054006","Type 2 diabetes mellitus (disorder)"),
    ("312961","simvastatin 20 MG Oral Tablet","55822004","Hyperlipidemia (disorder)"),
    ("308192","amoxicillin 500 MG Oral Capsule","195662009","Acute viral pharyngitis (disorder)"),
    ("745679","Salbutamol 0.83 MG/ML Inhalation Solution","233678006","Childhood asthma (disorder)"),
]

def pick(weighted):
    r = random.random(); acc = 0.0
    for item in weighted:
        acc += item[-1]
        if r <= acc: return item
    return weighted[-1]

def rdate(a, b):
    return a + dt.timedelta(days=random.randint(0, (b - a).days))

# ---------------- patients ----------------
patients = []
for _ in range(N_PATIENTS):
    pid = str(uuid.UUID(int=random.getrandbits(128)))
    gender = random.choice("MF")
    birth = rdate(dt.date(1930, 1, 1), dt.date(2021, 12, 31))
    dead = ""
    if birth.year < 1960 and random.random() < 0.18:
        d = rdate(birth + dt.timedelta(days=365 * 62), TODAY)
        if d < TODAY: dead = d.isoformat()
    city, zipc = random.choice(CITIES)
    first = random.choice(FIRST_F if gender == "F" else FIRST_M)
    patients.append({
        "Id": pid, "BIRTHDATE": birth.isoformat(), "DEATHDATE": dead,
        "SSN": f"999-{random.randint(10,99)}-{random.randint(1000,9999)}",
        "DRIVERS": f"S{random.randint(10000000,99999999)}" if birth.year < 2008 else "",
        "PASSPORT": f"X{random.randint(10000000,99999999)}X" if random.random() < 0.55 else "",
        "PREFIX": "Mrs." if gender == "F" and birth.year < 2006 else ("Mr." if gender == "M" and birth.year < 2006 else ""),
        "FIRST": first, "LAST": random.choice(LAST), "SUFFIX": "", "MAIDEN": "",
        "MARITAL": random.choice(["M","S","W",""]) if birth.year < 2006 else "",
        "RACE": "white", "ETHNICITY": "nonhispanic", "GENDER": gender,
        "BIRTHPLACE": f"{random.choice(CITIES)[0]}  Crete  GR",
        "ADDRESS": f"{random.randint(1,180)} {random.choice(['Knossou','Dikaiosynis','Kalokairinou','Idomeneos','Ethnikis Antistaseos'])} Street",
        "CITY": city, "STATE": "Crete", "COUNTY": f"{city} Regional Unit", "ZIP": zipc,
        "LAT": f"{35.0 + random.random():.6f}", "LON": f"{24.0 + random.random()*2:.6f}",
        "HEALTHCARE_EXPENSES": f"{random.uniform(3000, 900000):.2f}",
        "HEALTHCARE_COVERAGE": f"{random.uniform(1000, 60000):.2f}",
        "INCOME": str(random.randint(9000, 92000)),
    })

with open(OUT / "patients.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(patients[0].keys())); w.writeheader(); w.writerows(patients)

# ---------------- encounters / conditions / observations / medications ----------------
enc_rows, cond_rows, obs_rows, med_rows = [], [], [], []
for p in patients:
    birth = dt.date.fromisoformat(p["BIRTHDATE"])
    end = dt.date.fromisoformat(p["DEATHDATE"]) if p["DEATHDATE"] else TODAY
    span_years = max(1, (end - birth).days // 365)
    n_enc = max(1, min(60, int(random.gammavariate(2.0, 3.0)) + span_years // 8))
    org = random.choice(ORGS)
    for _ in range(n_enc):
        start_d = rdate(birth, end)
        cls, ccode, cdesc, _ = pick(ENC_KINDS)
        hh, mm = random.randint(7, 19), random.choice([0, 15, 30, 45])
        start = dt.datetime.combine(start_d, dt.time(hh, mm))
        stop = start + dt.timedelta(minutes=random.choice([15, 20, 30, 45, 60]) if cls != "inpatient" else random.randint(1440, 7200))
        eid = str(uuid.UUID(int=random.getrandbits(128)))
        base = round(random.uniform(75, 160), 2)
        total = round(base + random.uniform(0, 900), 2)
        cov = round(total * random.uniform(0.35, 0.95), 2)
        reason_c = reason_d = ""
        if random.random() < 0.30:
            cc, cd, _ = pick(CONDITIONS)
            reason_c, reason_d = cc, cd
        enc_rows.append([eid, start.isoformat(sep=" ", timespec="seconds"), stop.isoformat(sep=" ", timespec="seconds"),
                         p["Id"], org, org + " Clinician", "Greek NHS (EOPYY)", cls, ccode, cdesc,
                         f"{base:.2f}", f"{total:.2f}", f"{cov:.2f}", reason_c, reason_d])

        if random.random() < 0.22:
            cc, cd, _ = pick(CONDITIONS)
            stopd = "" if random.random() < 0.65 else (start_d + dt.timedelta(days=random.randint(20, 900))).isoformat()
            if stopd and stopd > end.isoformat(): stopd = ""
            cond_rows.append([start_d.isoformat(), stopd, p["Id"], eid, "http://snomed.info/sct", cc, cd])

        age = (start_d - birth).days / 365.25
        # every encounter records a BP pair and a body weight; some record a lipid panel
        sysv = int(random.gauss(124 + (age * 0.32), 13)); diav = int(random.gauss(76 + (age * 0.10), 9))
        obs_rows.append([start.isoformat(sep=" ", timespec="seconds"), p["Id"], eid, "vital-signs",
                         "8480-6", "Systolic Blood Pressure", str(max(85, min(205, sysv))), "mm[Hg]", "numeric"])
        obs_rows.append([start.isoformat(sep=" ", timespec="seconds"), p["Id"], eid, "vital-signs",
                         "8462-4", "Diastolic Blood Pressure", str(max(50, min(125, diav))), "mm[Hg]", "numeric"])
        obs_rows.append([start.isoformat(sep=" ", timespec="seconds"), p["Id"], eid, "vital-signs",
                         "29463-7", "Body Weight", f"{random.gauss(74, 15):.1f}", "kg", "numeric"])
        if random.random() < 0.30:
            obs_rows.append([start.isoformat(sep=" ", timespec="seconds"), p["Id"], eid, "laboratory",
                             "2093-3", "Cholesterol [Mass/volume] in Serum or Plasma",
                             f"{random.gauss(196, 34):.1f}", "mg/dL", "numeric"])
            obs_rows.append([start.isoformat(sep=" ", timespec="seconds"), p["Id"], eid, "laboratory",
                             "2085-9", "High Density Lipoprotein Cholesterol", f"{random.gauss(56, 13):.1f}", "mg/dL", "numeric"])
        if random.random() < 0.12:
            # a text-valued observation: UNITS is legitimately empty (as in real Synthea exports)
            obs_rows.append([start.isoformat(sep=" ", timespec="seconds"), p["Id"], eid, "survey",
                             "72166-2", "Tobacco smoking status NHIS",
                             random.choice(["Never smoker","Former smoker","Current every day smoker"]), "", "text"])
        if random.random() < 0.10:
            mcode, mdesc, rc, rd = random.choice(MEDS)
            mstop = "" if random.random() < 0.4 else (start_d + dt.timedelta(days=random.choice([7, 30, 90, 365]))).isoformat()
            if mstop and mstop > end.isoformat(): mstop = ""
            bc = round(random.uniform(4, 60), 2); disp = random.choice([1, 1, 2, 3, 6, 12])
            med_rows.append([start_d.isoformat(), mstop, p["Id"], "Greek NHS (EOPYY)", eid, mcode, mdesc,
                             f"{bc:.2f}", f"{bc*disp*random.uniform(0.3,0.9):.2f}", str(disp),
                             f"{bc*disp:.2f}", rc, rd])

def dump(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    return len(rows)

n_e = dump("encounters.csv", ["Id","START","STOP","PATIENT","ORGANIZATION","PROVIDER","PAYER","ENCOUNTERCLASS","CODE","DESCRIPTION",
                              "BASE_ENCOUNTER_COST","TOTAL_CLAIM_COST","PAYER_COVERAGE","REASONCODE","REASONDESCRIPTION"], enc_rows)
n_c = dump("conditions.csv", ["START","STOP","PATIENT","ENCOUNTER","SYSTEM","CODE","DESCRIPTION"], cond_rows)
n_o = dump("observations.csv", ["DATE","PATIENT","ENCOUNTER","CATEGORY","CODE","DESCRIPTION","VALUE","UNITS","TYPE"], obs_rows)
n_m = dump("medications.csv", ["START","STOP","PATIENT","PAYER","ENCOUNTER","CODE","DESCRIPTION","BASE_COST","PAYER_COVERAGE",
                               "DISPENSES","TOTALCOST","REASONCODE","REASONDESCRIPTION"], med_rows)
print(f"patients={len(patients)} encounters={n_e} conditions={n_c} observations={n_o} medications={n_m}")
