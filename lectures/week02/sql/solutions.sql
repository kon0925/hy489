-- HY-489 Week 2 · Hands-on A — SOLUTIONS (instructor copy)

-- A1. Every observation for PAT-1 in clinical (effective) time order.
--     What query 1 misses: it drops observations whose encounter has been
--     superseded, and it says nothing about status. A defensible answer:
SELECT o.effective_ts, o.recorded_ts, o.code, o.value_num, o.unit, o.status
FROM   observation o
JOIN   encounter   e USING (encounter_id)
WHERE  e.patient_id = 'PAT-1'
ORDER  BY o.effective_ts;
-- Expect OBS-3 (BP, 30 Sep 10:05) before OBS-2 (cholesterol, 2 Oct 07:40).
-- Note they arrive in a different order than they were recorded.

-- A2. Orders with no matching result.
SELECT lo.order_id, lo.code, lo.status, lo.ordered_ts
FROM   lab_order lo
WHERE  NOT EXISTS (SELECT 1 FROM observation o WHERE o.order_id = lo.order_id);
-- Expect ORD-8 only. Point out that ORD-8 is still 'active', so the status
-- column and the structural check agree here. They often do not.

-- A3. The correction. A new row, never an UPDATE.
INSERT INTO observation VALUES
  ('OBS-4', 'ENC-9', 'ORD-7', '2093-3', 'LOINC', 231, 'mg/dL',
   NULL, 200, '2026-10-02 07:40', '2026-10-02 16:15', 'amended', 'OBS-2');
-- effective_ts is unchanged: the blood was drawn when it was drawn.
-- recorded_ts is new: this is when the correction reached us.
-- supersedes points back at the row it replaces.
-- This is the single most important line of SQL in Week 2.

-- A4. The current view now returns 231 and not 215.
SELECT o.observation_id, o.code, o.value_num, o.status
FROM   observation o
WHERE  NOT EXISTS (SELECT 1 FROM observation n WHERE n.supersedes = o.observation_id)
  AND  o.status <> 'entered-in-error';
-- Expect OBS-3 (BP 148) and OBS-4 (cholesterol 231). OBS-2 is gone from the
-- view but still in the table, which is the whole point.

-- A5. Turnaround time, ordered to resulted.
-- PostgreSQL:
SELECT lo.order_id, lo.code,
       age(min(o.recorded_ts), lo.ordered_ts) AS turnaround
FROM   lab_order lo JOIN observation o USING (order_id)
GROUP  BY lo.order_id, lo.code, lo.ordered_ts;

-- SQLite:
SELECT lo.order_id, lo.code,
       round((julianday(min(o.recorded_ts)) - julianday(lo.ordered_ts)) * 24, 1) AS hours
FROM   lab_order lo JOIN observation o USING (order_id)
GROUP  BY lo.order_id, lo.code, lo.ordered_ts;
-- Expect about 49 hours for ORD-7. Ask the room whether that is the lab being
-- slow or the courier, and note that the data cannot tell you which.

-- ---------------------------------------------------------------------------
-- The question students ask, and the answer
-- ---------------------------------------------------------------------------
-- "Why not just UPDATE the row?"
--
-- Because the wrong value was acted upon. Somebody saw 215 and made a decision
-- at 11:42 on 2 October. If you overwrite it, the record no longer explains why
-- that decision was made, and neither an audit nor a court can reconstruct it.
-- In clinical data you correct by superseding.
