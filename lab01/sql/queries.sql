-- HY-489 Lab 1 — Part C query stubs.
-- Fill in the ones marked TODO; the first is done as a worked example.

-- Verification 1: did everything arrive?
SELECT 'patient' AS t, count(*) FROM patient
UNION ALL SELECT 'encounter',   count(*) FROM encounter
UNION ALL SELECT 'condition',   count(*) FROM condition
UNION ALL SELECT 'observation', count(*) FROM observation;

-- Verification 2: any orphans? (should be zero - the FK guarantees it)
SELECT count(*) AS orphan_encounters
FROM encounter e LEFT JOIN patient p ON e.patient_id = p.patient_id
WHERE p.patient_id IS NULL;

-- Verification 3: do the dates look sane?
SELECT min(start_ts), max(start_ts) FROM encounter;


-- Q1  Cohort demographics: count and mean age by gender.
-- TODO. PostgreSQL: extract(year from age(birth_date))
--       SQLite:     (julianday('now') - julianday(birth_date)) / 365.25

-- Q2  The ten most common conditions, grouped by CODE (not description).
-- TODO. Then run it again grouped by description and compare the counts.

-- Q3  Distribution of encounters per patient. Is it skewed?
-- TODO. Hint: GROUP BY over a subquery that already counted per patient.

-- Q4  The full timeline for one patient: encounters, conditions and
--     observations in one chronological list.
-- TODO. Hint: three SELECTs joined with UNION ALL, then ORDER BY 1.

-- Q5  Find one thing that looks too clean to be real. Write it as a query.
-- TODO.
