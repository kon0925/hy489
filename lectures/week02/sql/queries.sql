-- HY-489 Week 2 · Hands-on A — the three queries that matter clinically
-- Run these after schema.sql and seed.sql.

-- ---------------------------------------------------------------------------
-- 1. The patient timeline: everything, in clinical time order
-- ---------------------------------------------------------------------------
SELECT e.start_ts, 'observation' AS kind, o.code, o.value_num, o.unit
FROM   observation o
JOIN   encounter   e USING (encounter_id)
WHERE  e.patient_id = 'PAT-1'
ORDER  BY o.effective_ts;

-- ---------------------------------------------------------------------------
-- 2. What is still outstanding? (the safety question)
--    An order with no result is a patient nobody has followed up.
-- ---------------------------------------------------------------------------
SELECT *
FROM   lab_order
WHERE  status IN ('active', 'in-progress')
  AND  encounter_id IN (SELECT encounter_id FROM encounter WHERE patient_id = 'PAT-1');

-- the same question asked structurally, which catches a completed order
-- that still has no result attached
SELECT lo.*
FROM   lab_order lo
WHERE  NOT EXISTS (SELECT 1 FROM observation o WHERE o.order_id = lo.order_id);

-- ---------------------------------------------------------------------------
-- 3. The current view: only results nothing has superseded
--    In an append-only record "the current value" is derived, not stored.
--    Every clinical system computes this constantly, and getting it wrong
--    shows a superseded result to a doctor.
-- ---------------------------------------------------------------------------
SELECT o.*
FROM   observation o
WHERE  NOT EXISTS (SELECT 1 FROM observation n WHERE n.supersedes = o.observation_id)
  AND  o.status <> 'entered-in-error';

-- ---------------------------------------------------------------------------
-- Mini-lab A starts here. Five tasks, stubs below.
-- ---------------------------------------------------------------------------

-- A1. Every observation for PAT-1 in clinical (effective) time order.
--     (Query 1 above is most of the answer. What does it miss?)


-- A2. All orders with no matching result.


-- A3. A corrected cholesterol of 231 arrives for ORD-7.
--     Insert it WITHOUT losing the original.
--     Hint: a new row, a new id, supersedes pointing at OBS-2,
--     status 'amended', and a recorded_ts of now.


-- A4. Now re-run the current-view query. Does it return 231 and not 215?


-- A5. How long did the lab take? ordered_ts to recorded_ts, per order.
--     Postgres: age(o.recorded_ts, lo.ordered_ts)
--     SQLite:   julianday(o.recorded_ts) - julianday(lo.ordered_ts)
