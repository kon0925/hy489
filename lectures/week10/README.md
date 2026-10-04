# Week 10 — Governance: who may access what, through which process

Three standard-library scripts. No installation, no network, no third-party
packages. Two of them read the Lab 1 cohort in `../../labs/lab01/data/`; the
third reads nothing.

```
python3 disclosure.py             # Session A: checking an aggregate output
python3 accesslog.py              # Session B: the audit log, and who reads it
python3 request.py                # Session B: the Five Safes, applied four times
```

Each script takes `--<section>` flags to run one part. The whole of all three
takes about one second. `common.py` holds the loading the first two share.

Weeks 8 and 9 were about the data and the analysis. This week is about the
people: a researcher who wants something, a committee that decides, a checker
who approves what leaves, and an auditor who is supposed to notice when
somebody looks at a record they had no reason to open.

## disclosure.py

Statistical disclosure control, done cell by cell on one real cross-tabulation:
patients with a recorded diagnosis of essential hypertension, by town and age
band, 36 cells over 376 patients.

| section | flag | what happens |
|---|---|---|
| the table | `--table` | the unprotected output, with row and column totals |
| threshold | `--threshold` | suppress cells below 5, then below 10 |
| recovery | `--recover` | subtract a suppressed cell back out of a published total |
| complementary | `--secondary` | suppress more cells until the subtraction fails |
| dominance | `--dominance` | the (n,k) and p% rules on a table of money |
| differencing | `--differencing` | two approved outputs that isolate one woman |

Key numbers, all printed by the script.

- At n < 5, two cells are suppressed, hiding 8 of 376 patients. 94.4% of cells
  and 97.9% of the count survive. At n < 10, 17 cells go, hiding 110 patients,
  and 52.8% of cells survive.
- Both suppressed cells are recoverable by subtraction, twice each. Heraklion
  publishes 5 + 8 + 17 + 18 + 14 = 62 against a row total of 66, so the hidden
  cell is 4.
- Complementary suppression takes the suppressed set from 2 cells to 7. Cells
  published falls from 94.4% to 80.6%; the count published falls from 97.9% to
  89.9%. The hidden cells are then known only to lie inside ranges such as
  0 to 10, which a linear program tightens further.
- The magnitude table is total medication spend for patients aged 80 and over,
  by drug and town. A minimum of 3 contributors suppresses nothing. The (1,50)
  rule suppresses 6 of 36 cells, (2,70) suppresses 10, the p% rule at p = 10
  suppresses 2. The worst cell holds 4 patients and 773 euro, of which one
  patient is 714 euro, or 92.3%.
- The differencing attack: two counts among women in Agios Nikolaos, one for
  those born in or before 1940 (11 of 15) and one for those born in or before
  1939 (10 of 14). Both pass a threshold of 10. The difference names one woman
  and her diagnosis. The same subtraction on total lifetime expenditure returns
  her figure to the cent, 294,850.31 euro, out of totals over 15 and 14 people.
  There are 99 such pairs in this cohort for this one condition and this one
  stratification.

## accesslog.py

A seeded synthetic access log over the cohort and 44 invented staff accounts:
24,741 events across 26 days, 952 a day. Seven incidents are planted in it,
400 events in all, and seven detectors run without ever seeing the labels.

| detector | alerts | per day | planted | found | precision |
|---|---|---|---|---|---|
| self-lookup | 7 | 0.3 | 7 | 7 | 100.0% |
| same surname | 1,320 | 50.8 | 7 | 7 | 0.5% |
| no treatment relationship | 1,047 | 40.3 | 44 | 44 | 4.2% |
| daily volume outlier | 342 | 13.2 | 144 | 144 | 42.1% |
| access to a flagged record | 100 | 3.8 | 6 | 6 | 6.0% |
| outside working hours | 1,715 | 66.0 | 12 | 12 | 0.7% |
| bulk export | 180 | 6.9 | 180 | 180 | 100.0% |
| all seven, events counted once | 3,931 | 151.2 | 400 | 400 | 10.2% |

Every incident is found. That is not the result. The result is the per-day
column: 151 alerts a day, at one minute each, is 2.5 hours of somebody's
morning, every morning, to find seven incidents in 26 days. The two detectors
with high precision are the two with an exact rule (an identifier equality and
a 50-patients-in-30-minutes window). The detector that watches six flagged
records runs at 6% precision against the 4.2% of the one that watches all
1,174, so the rule is no sharper. It is usable because four alerts a day is a
queue a person can finish.

## request.py

The Five Safes as fifteen criteria, three per safe, one point each, with a
stated decision rule: any safe at zero refuses, 12 or more with no safe below 2
approves, 8 or more with no safe below 1 approves with conditions.

Four worked requests, written out in full and scored line by line.

| request | people | projects | settings | data | outputs | total | decision |
|---|---|---|---|---|---|---|---|
| PhD student, whole table | 1 | 1 | 0 | 0 | 1 | 3 | refuse |
| Pharmaceutical company | 3 | 2 | 1 | 2 | 2 | 10 | approve with conditions |
| Internal quality audit | 2 | 3 | 3 | 0 | 1 | 9 | refuse |
| Newspaper | 1 | 2 | 1 | 2 | 0 | 6 | refuse |

The only request that proceeds is the commercial one, and the hospital auditing
its own readmission rate is refused on an empty safe data score. Both results
are arguments, and `--critique` prints four attacks on the rubric, including
the one that matters most: a 30-day readmission measure can never score a point
under safe data, because matching a readmission to a discharge requires the
identity and the exact dates. The standard resolution is to put service
evaluation outside the research access regime entirely, which leaves the
largest routine flow of identifiable data in any hospital with no scrutiny.

Every score in this script is a judgement somebody wrote down. Disagree with
them in class; that is what they are for.

## A standing rule

Nothing in this folder goes anywhere near real data or a real audit log.

`accesslog.py` generates a log and then attacks it. The detectors in it are
ordinary and the techniques are published, and running anything of this shape
against a real hospital's access log is monitoring identifiable staff
behaviour. It needs a lawful basis, a works council or union agreement in most
European jurisdictions, a data protection impact assessment, and a named person
accountable for what happens to somebody who appears in the output. None of
those is a formality. An alert is an accusation against a named employee, and
a detector with 0.5% precision gets 187 of them wrong for every one it gets right.

`disclosure.py` shows how to recover a suppressed cell and how to isolate one
person from two approved outputs. Do that to a real statistical release and you
have attacked the people in it, whatever you intended, and the fact that the
release was published does not make the people in it fair game.

The rules from Weeks 8 and 9 still stand. Nothing real goes to a public server.
You do not look up your own record, or a relative's, in a system you have
access to for another reason, and `accesslog.py` is the week's explanation of
why that is a rule and not advice.
