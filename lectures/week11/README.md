# Week 11 — The European Health Data Space

Three standard-library scripts. No installation, no network, no third-party
packages. Two of them read the Lab 1 cohort in `../../labs/lab01/data/`; the
third reads nothing.

```
python3 summary.py                # Session A: the exchange format, in practice
python3 permit.py                 # Session B: the data permit against the clock
python3 catalogue.py              # Session B: the dataset entry and the label
```

Each script takes `--<section>` flags to run one part. The whole of all three
takes under four seconds.

Week 10 was about who may access what, through which process, in one
institution. This week the process is a Regulation with dates in it:
Regulation (EU) 2025/327, adopted 11 February 2025, in force 26 March 2025,
applying from 26 March 2027, with the parts that matter clinically landing on
26 March 2029 and 26 March 2031. The research behind every article cited in
these scripts, with sources and retrieval dates, is in
`../../notes/week11_research.md`, including the things that could not be
verified.

## summary.py

Article 14(1)(a) makes the patient summary a priority category. Article 15(1)
says the European electronic health record exchange format is harmonised
datasets, coding systems and values, and technical interoperability
specifications. The clinical content is the International Patient Summary:
three sections required, four recommended.

| section | flag | what happens |
|---|---|---|
| sections | `--sections` | what the IPS requires against what the cohort holds |
| bundle | `--bundle` | one patient as a hand-written FHIR document Bundle |
| rules | `--rules` | the twelve required and two recommended checks |
| validate | `--validate` | the checks over all 1,174 patients |
| coding | `--coding` | the code systems the files actually declare |
| repair | `--repair` | four fixes, and what each one is worth |

Key numbers, all printed by the script.

- Of the three required IPS sections, two have no source file. 1,018 patients
  of 1,174 have a recorded condition and 768 have a prescription. Nobody has an
  allergy record and nobody has an immunisation record, because neither table
  was extracted.
- The worked Bundle is 51 resources and 1,682 lines of JSON for one patient
  with 11 problems, 2 medications, 30 laboratory results and 6 vital signs.
- Zero patients produce a summary that passes. The six header checks pass for
  everybody; every failure is in the clinical sections.
- The required elements missing most often: the allergies section for all 1,174
  patients; a code system on the laboratory results for 1,108; a code system on
  the medications for 768; a medication section with anything in it for 406.
- The conditions file declares `http://snomed.info/sct` in a SYSTEM column.
  medications.csv and observations.csv carry a CODE column and no SYSTEM
  column, across 1,343 medication rows and the 48,822 observation entries the
  summary uses. The values are RxNorm and LOINC and the files do not say so.
- Declaring the two code systems fixes nothing on its own, and asserting no
  known allergies fixes nothing on its own. The two together take the cohort
  from 0 complete summaries to 698, which is 59.5%. Adding an explicit
  assertion for the empty problem and medication lists takes it to 1,174.
- For 17 patients the repaired summary's entire clinical content is three
  assertions of absence and a blood pressure, and it passes every required
  check.

## permit.py

Article 68(4) gives a health data access body three months to issue or refuse a
data permit, extendable by three. Article 68(6) gives it two months, extendable
by one, for public bodies with a public health mandate. Article 60 gives each
health data holder three months to send the data. Article 68(7) gives the body
two further months to make it available. No article says how many people the
body employs.

| section | flag | what happens |
|---|---|---|
| law | `--law` | nine deadlines from four articles |
| model | `--model` | every assumption, and the arithmetic before any simulation |
| run | `--run` | one year at the default staffing |
| queue | `--queue` | the queue, month by month |
| discipline | `--discipline` | three ways to order the pile |
| staffing | `--staffing` | twelve staffing levels, ten simulated years each |
| endtoend | `--endtoend` | application to data in a secure processing environment |

The model: 240 applications in 2029, 15% on the accelerated route, 40% arriving
incomplete and a tenth of those never completed, 3 to 9 officer days for a
routine assessment and 14 to 26 for the complex fifth, 7 officers, 30 days of
leave and training each, 261 working days. Arrivals continue into 2030 so that
a body which is behind at the end of the year does not get a free year to catch
up. Everything in that list is an assumption and `--model` prints it.

Key numbers, all printed by the script.

- Total assessment effort 2,007 officer working days against 1,617 days of
  capacity at 7 officers: 124.1% utilisation, break-even 8.69 officers.
- At 7 officers, 146 of 230 live applications are decided inside the Article 68
  deadline (63.5%), 82 only inside the extended deadline (35.7%), and 2 past
  even that. Median 70 days, 90th percentile 114, worst 136.
- The queue runs from 3 applications at the end of January to 53 at the end of
  November. The oldest untouched application reached 92 days, and on 3 of the
  261 working days there was an application in the queue whose three month
  deadline had expired before any officer opened it.
- Queue discipline at the same staffing: earliest deadline first gives 63.5% on
  time with the two routes at 65.7% and 63.1%; first in first out gives 65.2%
  overall but drops the Article 68(6) route to 37.1%; shortest assessment first
  gives 91.7% on time and a median of 12 days, and takes the share that blows
  past the extended deadline from 0.9% to 6.5%, because it never starts the big
  applications.
- Staffing: at 7 officers the on-time share across ten simulated years runs
  from 46.3% to 88.2%, mean 72.2%. At 8 the worst year is 90.0%. At 9 every one
  of the ten years is 100%. Break-even is 8.69.
- End to end: median 170 days from the start of the statutory clock to data in
  the environment, 90th percentile 227. The lawful outer bound is 243 days and
  4 of 230 permits exceeded it.

The spread at 7 officers is the result to argue about. It is the same body, the
same budget and the same staff, complying in one year and not in the next, with
nobody doing anything differently.

## catalogue.py

Article 77 makes the data holder publish a dataset description and the body
publish a machine readable catalogue. Article 78 adds a data quality and utility
label, voluntary in general and mandatory for anything collected with public
money, over six element groups. Article 78(3)(b) names six technical quality
elements, and five of them are the Weiskopf and Weng dimensions from Week 7.

| section | flag | what happens |
|---|---|---|
| entry | `--entry` | the Article 77 description, computed from the files |
| completeness | `--completeness` | is the value there at all |
| correctness | `--correctness` | is the value a legal value |
| concordance | `--concordance` | do two records of the same fact agree |
| plausibility | `--plausibility` | could the value be true of a person |
| currency | `--currency` | how old is the most recent record |
| label | `--label` | the computed label and the three worst dimensions |
| coverage | `--coverage` | what Article 78(3) asks that no file can answer |

Each dimension scores as its worst check, with the mean printed beside it.
Grades: A at 95, B at 85, C at 70, D at 50, E below.

Key numbers, all printed by the script.

- The entry: 1,174 patients, 69,611 rows across five files, temporal coverage
  1931-12-09 to 2026-09-25, six postcode areas in Crete, 615 female and 559
  male, ages 4 to 96 with a median of 53, 68 deceased.
- Completeness: every expected column is populated in every row of all five
  files. Patient level, 86.7% have a recorded condition, 65.4% a prescription,
  94.4% a laboratory result, 100% an encounter and a vital sign. Worst check
  65.42%, grade D.
- Correctness: eleven checks, all at 100.00%. Identifiers unique, dates parse,
  codes match the SNOMED, LOINC and RxNorm patterns, units are UCUM. Grade A.
- Concordance: the medication reason is on the patient's problem list 27.40% of
  the time and the encounter reason 25.22% of the time. The four referential
  checks are all at 100%. Worst check 25.22%, grade E.
- Plausibility: eight checks at 100.00% and one at 99.96%, which is 5 blood
  pressure readings of 13,550 where the diastolic value is not below the
  systolic. Grade A.
- Currency: 21.25% of living patients have a record inside a year, 37.52%
  inside two, 69.08% inside five. Median 1,036 days since the most recent
  record of any kind. Worst check 21.25%, grade E.
- The label is grade E on its worst dimension and grade D on the mean of the
  five, for the same dataset.
- Of the six Article 78(3) element groups, one can be computed from the data in
  full, one in part, and four are declarations by the data holder about itself.

The two dimensions that score A are the two a data holder can fix alone, with a
schema and a range check. The two that score E are the two it cannot.

## A standing rule

Nothing in this folder goes to any server, and nothing in it is real.

`summary.py` emits a FHIR document Bundle. It is a synthetic patient. Do not
post a Bundle built from a real record to a public FHIR validator, a test
server, a pastebin or a language model. A patient summary is the densest
clinical document about a person that exists: problems, medications, allergies
and results in one file, with the name and the identifier in the header. There
are public validators that will take it, and sending it to one is a disclosure
of special category data to a third country in most cases, with no lawful basis
and no contract. Validate against a local copy of the specification, or against
nothing.

`permit.py` is a simulation. Do not submit a data access application to a real
health data access body as a class exercise. An application under Article 67
names a controller, states a purpose, and commits an institution to the
Article 61 duties of a health data user. It is a legal act by an organisation,
it consumes the time of a body that this script spends two sections showing is
short of it, and a teaching exercise that lands in that queue displaces real
research. If you want to see a real application, the templates under Article 70
are published and the bodies that exist publish their decisions under
Article 59.

`catalogue.py` writes a dataset description and computes a quality label for a
cohort that came out of a generator. The entry says so in its source block, in
a field and not a footnote, and any derived version of it must keep that line.
A catalogue is read by software before it is read by a person, and a synthetic
dataset described as if it were a real one is a worse problem than an
undescribed dataset. The same applies to the label: it is computed from these
files and it is evidence about these files and nothing else.

The rules from Weeks 8, 9 and 10 still stand. Nothing real goes to a public
server. You do not look up your own record, or a relative's, in a system you
have access to for another reason. Under Article 3 you have a right to your own
record, and that right is exercised through the access service, not through the
database.
