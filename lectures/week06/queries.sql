-- HY-489 Week 6, Hands-on A: query a CDM you did not build.
--
--     sqlite3 cdm.db < queries.sql
--
-- Nine queries. The first three are the ones on the slides. Read each one
-- before you read its output, and ask yourself what it would have taken to
-- answer the same question against the raw CSV files from Week 1.

.mode column
.headers on
.width 46 12 12

SELECT '--- 1. How many people, and over how much observed time?' AS q;
SELECT count(*)                                              AS persons,
       round(avg(julianday(observation_period_end_date)
                 - julianday(observation_period_start_date)) / 365.25, 1)
                                                             AS mean_years
FROM   person JOIN observation_period USING (person_id);

SELECT '--- 2. Top conditions, by STANDARD concept. Never by source string.' AS q;
SELECT c.concept_name                                        AS condition,
       count(*)                                              AS n
FROM   condition_occurrence co
JOIN   concept c ON c.concept_id = co.condition_concept_id
GROUP  BY 1 ORDER BY n DESC LIMIT 8;

SELECT '--- 3. A cohort by hierarchy, with no code list. This is the payoff.' AS q;
SELECT count(DISTINCT co.person_id)                          AS people_with_hypertension
FROM   condition_occurrence co
JOIN   concept_ancestor ca ON ca.descendant_concept_id = co.condition_concept_id
WHERE  ca.ancestor_concept_id = 316866;      -- Hypertensive disorder

SELECT '--- 4. The unmapped tail. Run this on any CDM, first thing.' AS q;
SELECT 'condition_occurrence' AS tbl, condition_source_value AS source_code,
       count(*)               AS n
FROM   condition_occurrence WHERE condition_concept_id = 0
GROUP  BY 2
UNION ALL
SELECT 'measurement', measurement_source_value, count(*)
FROM   measurement WHERE measurement_concept_id = 0 GROUP BY 2
UNION ALL
SELECT 'drug_exposure', drug_source_value, count(*)
FROM   drug_exposure WHERE drug_concept_id = 0 GROUP BY 2
ORDER  BY n DESC;

SELECT '--- 5. Unmapped as a fraction, per table. The number to publish.' AS q;
SELECT 'condition_occurrence' AS tbl,
       count(*)               AS rows_total,
       sum(condition_concept_id = 0) AS unmapped,
       round(100.0 * sum(condition_concept_id = 0) / count(*), 2) AS pct
FROM   condition_occurrence
UNION ALL
SELECT 'measurement', count(*), sum(measurement_concept_id = 0),
       round(100.0 * sum(measurement_concept_id = 0) / count(*), 2) FROM measurement
UNION ALL
SELECT 'drug_exposure', count(*), sum(drug_concept_id = 0),
       round(100.0 * sum(drug_concept_id = 0) / count(*), 2) FROM drug_exposure
UNION ALL
SELECT 'observation', count(*), sum(observation_concept_id = 0),
       round(100.0 * sum(observation_concept_id = 0) / count(*), 2) FROM observation;

SELECT '--- 6. A crude prevalence, with the denominator the model gives you.' AS q;
SELECT (SELECT count(DISTINCT co.person_id)
        FROM   condition_occurrence co
        JOIN   concept_ancestor ca
                 ON ca.descendant_concept_id = co.condition_concept_id
        WHERE  ca.ancestor_concept_id = 316866)              AS numerator,
       (SELECT count(*) FROM observation_period)             AS denominator,
       round(100.0 * (SELECT count(DISTINCT co.person_id)
                      FROM   condition_occurrence co
                      JOIN   concept_ancestor ca
                               ON ca.descendant_concept_id = co.condition_concept_id
                      WHERE  ca.ancestor_concept_id = 316866)
             / (SELECT count(*) FROM observation_period), 1) AS pct;

SELECT '--- 7. Where did each row come from? The type concept answers.' AS q;
SELECT c.concept_name                                        AS provenance,
       count(*)                                              AS n
FROM   condition_occurrence co
JOIN   concept c ON c.concept_id = co.condition_type_concept_id
GROUP  BY 1 ORDER BY n DESC;

SELECT '--- 8. Measurements need a unit. Check that they have one.' AS q;
SELECT c.concept_name                                        AS measurement,
       u.concept_name                                        AS unit,
       count(*)                                              AS n,
       round(avg(m.value_as_number), 1)                      AS mean_value
FROM   measurement m
JOIN   concept c ON c.concept_id = m.measurement_concept_id
LEFT   JOIN concept u ON u.concept_id = m.unit_concept_id
GROUP  BY 1, 2 ORDER BY n DESC;

SELECT '--- 9. The same question asked the wrong way, for comparison.' AS q;
-- This is query 3 done by source value, the way Week 1 did it by string
-- matching. It finds one code, not a hierarchy, and it will silently miss
-- every synonym, every child concept and every code the source did not use.
SELECT count(DISTINCT person_id)                             AS by_source_value
FROM   condition_occurrence
WHERE  condition_source_value = '59621000';
