-- HY-489 Week 2 · Hands-on A — Maria's encounter, as rows
-- This is Exercise 2 from the lecture, loaded into the schema.
-- Load order matters: patient, encounter, then everything else.

INSERT INTO patient VALUES
  ('PAT-1', 'Papadaki', 'Maria', '1984-03-11', 'female');

INSERT INTO encounter VALUES
  ('ENC-9', 'PAT-1', 'outpatient', '2026-09-30 10:00', '2026-09-30 10:30', 'Nikolaou');

INSERT INTO condition VALUES
  ('CON-3', 'ENC-9', '55822004', 'SNOMED', '2026-09-30');   -- hyperlipidaemia

-- ordered on the day of the visit, resulted two days later
INSERT INTO lab_order VALUES
  ('ORD-7', 'ENC-9', '24331-1', 'completed', '2026-09-30 10:20');

-- a second order that never came back. This is the outstanding-results problem.
INSERT INTO lab_order VALUES
  ('ORD-8', 'ENC-9', '2345-7',  'active',    '2026-09-30 10:22');

INSERT INTO observation VALUES
  ('OBS-2', 'ENC-9', 'ORD-7', '2093-3', 'LOINC', 215, 'mg/dL',
   NULL, 200, '2026-10-02 07:40', '2026-10-02 11:42', 'final', NULL);

-- a blood pressure taken during the visit: no order behind it
INSERT INTO observation VALUES
  ('OBS-3', 'ENC-9', NULL, '8480-6', 'LOINC', 148, 'mm[Hg]',
   90, 120, '2026-09-30 10:05', '2026-09-30 10:06', 'final', NULL);

-- Note on OBS-2: the result belongs to ENC-9 even though it arrived after the
-- encounter ended, and its two timestamps are four hours apart. Both facts are
-- normal, and a schema without order_id or without the two timestamps cannot
-- represent either of them.
