# Week 8 — Privacy, de-identification and the law

Two hands-on segments, both on the cohort you have had since Week 1.

Session A attacks it. Session B tries to protect it and counts what that costs.
Everything runs on Python's standard library.

```bash
cd lectures/week08
python3 reidentify.py              # how unique is everybody, and the join that names them
python3 reidentify.py --risk       # just the uniqueness table
python3 anonymise.py               # what each k costs, and the attacks k does not stop
python3 anonymise.py --lattice     # every generalisation and the k it reaches
python3 anonymise.py --k 5 --write release.csv
python3 dp.py                      # one count, made differentially private
python3 dp.py --small              # the same mechanism on a small cell
python3 dp.py --budget             # what happens when you ask more than once
```

## What is here

| File | What it is |
|---|---|
| `common.py` | Loading, the identifier lists, and the single sensitive value per patient |
| `reidentify.py` | Uniqueness at seven granularities, then a join against an external register |
| `anonymise.py` | Generalisation, suppression, k-anonymity, l-diversity, t-closeness, and the utility cost |
| `dp.py` | The Laplace mechanism on a count, at several budgets, with composition |

Nothing new is downloaded. All three read `../../labs/lab01/data/`.

## Hands-on A: attack your own cohort

Twenty-five minutes, Session A.

1. **See what is in the file.** `python3 reidentify.py --risk`. Every row carries
   a national identifier, a name, an address and a pair of coordinates. Removing
   those is step zero, and the rest of the exercise happens after that step.
2. **Read the uniqueness table.** Postcode, date of birth and sex make 99.7% of
   this cohort unique. Not hard to find. Alone.
3. **Find where the risk lives.** Compare the rows. Dropping the day and month
   of birth takes uniqueness to 34.3%; dropping the geography entirely takes it
   to 98.1%. Say why, before you read the explanation.
4. **Run the attack.** `python3 reidentify.py`. The script builds the register an
   attacker plausibly has and joins on three columns. Read the five named
   patients and their diagnoses.
5. **Change the attacker's coverage.** `--coverage 0.2`, then `--coverage 0.9`.
   The attacker does not need to be right about everybody. Decide what fraction
   would be enough to make you refuse to publish.
6. **Argue about the law.** You now have a file with no names in it that
   identifies 99.7% of the people in it. Is it personal data? Under GDPR
   Recital 26 the test is whether identification is reasonably likely by any
   means. You have just performed it in four minutes on a laptop.

## Hands-on B: protect it, and count the cost

Thirty minutes, Session B.

1. **Look at the lattice.** `python3 anonymise.py --lattice`. Sixty
   generalisations, each with the smallest group it produces. Find the cheapest
   one that reaches k = 5.
2. **Read the cost table.** `python3 anonymise.py`. k = 2 is nearly free; k = 10
   costs the town; k = 25 leaves you publishing a 5-year band for the whole
   island. Note that k = 25 suppresses fewer records than k = 10 and work out why.
3. **Write a release.** `python3 anonymise.py --k 5 --write release.csv` and open
   it. Decide whether you would publish it, then say what you would need to know
   before deciding.
4. **Attack it.** The homogeneity classes are named in the output. At k = 2 there
   are eight; at k = 5 there are none, and the script tells you that is luck.
5. **Change the cost weights.** `ZIP_COST`, `DATE_COST` and `SEX_COST` at the top
   of `anonymise.py` decide what "minimal" means. Change them so that losing the
   town is cheaper than losing the birth year, and rerun. The answer changes.
6. **Add noise instead.** `python3 dp.py`, then `--small`, then `--budget`. Work
   out at which epsilon the cohort-level count is still usable, and at which the
   eleven-person cell never was.
7. **Put the two together.** Which of the three releases, if any, would you hand
   to a colleague in another country without a contract? Write one sentence.

## Three honest notes about this cohort

**It is synthetic, and that is the only reason this is legal.** Every patient in
`labs/lab01/data` was generated. Running `reidentify.py` against a real extract,
including one you have lawful access to for another purpose, is a re-identification
attempt. Do not do it, on anybody's data, ever, including your own employer's.

**Its demographics are thin.** `RACE` and `ETHNICITY` take one value across all
1,174 rows, so they contribute nothing to the attack. In real data they are
high-risk quasi-identifiers and Article 9 special-category data at the same time.
Do not generalise from this cohort to that case.

**Its geography is six Cretan towns, with their real postcodes.** That makes the
attack sharper than the usual textbook version, not weaker: a postcode here names
a town of a few thousand to a few tens of thousands of people, and a date of birth
cuts that to one.

## The rule about real data

Nothing real goes near any of this. Not your record, not a relative's, not an
extract from a placement, and nothing you were given access to for another
purpose. The techniques in this folder are exactly the techniques an attacker
uses, which is why you are learning them on data that cannot be harmed.

## Going further

- Sweeney, *k-anonymity: a model for protecting privacy*, IJUFKS 10(5), 2002
- Sweeney, *Simple Demographics Often Identify People Uniquely*, 2000 — the 87% result
- Machanavajjhala et al., *l-diversity*, ACM TKDD 1(1), 2007
- Li, Li and Venkatasubramanian, *t-Closeness*, ICDE 2007
- Narayanan and Shmatikov, *Robust De-anonymization of Large Sparse Datasets*, IEEE S&P 2008 — the Netflix result
- Dwork and Roth, *The Algorithmic Foundations of Differential Privacy*, 2014 — free, and chapter 1 is enough
- Article 29 Working Party, *Opinion 05/2014 on Anonymisation Techniques* — still the clearest statement of the European legal test
- EDPB, *Guidelines 01/2025 on pseudonymisation* — what pseudonymisation does and does not buy you
