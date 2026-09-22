-- HY-489 Week 2 · Hands-on A — the mini-EHR
-- Portable between PostgreSQL and SQLite.
--
-- Six tables. Three columns in here would be missing from a naive schema, and
-- each one exists because of something that happens in real clinical data:
--   * observation.order_id   provenance: which order does this result answer
--   * effective_ts / recorded_ts   valid time vs transaction time
--   * status + supersedes    corrections without deletion

DROP TABLE IF EXISTS observation;
DROP TABLE IF EXISTS med_request;
DROP TABLE IF EXISTS lab_order;
DROP TABLE IF EXISTS condition;
DROP TABLE IF EXISTS encounter;
DROP TABLE IF EXISTS patient;

CREATE TABLE patient (
  patient_id   TEXT PRIMARY KEY,
  family_name  TEXT NOT NULL,
  given_name   TEXT,
  birth_date   DATE,
  sex          TEXT
);

CREATE TABLE encounter (
  encounter_id TEXT PRIMARY KEY,
  patient_id   TEXT NOT NULL REFERENCES patient(patient_id),
  class        TEXT NOT NULL,                  -- outpatient | inpatient | emergency
  start_ts     TIMESTAMP NOT NULL,
  end_ts       TIMESTAMP,                      -- null while the encounter is open
  practitioner TEXT
);

CREATE TABLE condition (
  condition_id TEXT PRIMARY KEY,
  encounter_id TEXT NOT NULL REFERENCES encounter(encounter_id),
  code         TEXT NOT NULL,
  code_system  TEXT NOT NULL,
  onset_date   DATE
);

CREATE TABLE lab_order (
  order_id     TEXT PRIMARY KEY,
  encounter_id TEXT NOT NULL REFERENCES encounter(encounter_id),
  code         TEXT NOT NULL,
  status       TEXT NOT NULL,                  -- active | in-progress | completed | cancelled
  ordered_ts   TIMESTAMP NOT NULL
);

CREATE TABLE observation (
  observation_id TEXT PRIMARY KEY,
  encounter_id   TEXT NOT NULL REFERENCES encounter(encounter_id),
  order_id       TEXT REFERENCES lab_order(order_id),   -- provenance. null for vitals
  code           TEXT NOT NULL,                         -- e.g. LOINC 2093-3
  code_system    TEXT NOT NULL,
  value_num      REAL,
  unit           TEXT,                                  -- never optional in practice
  ref_low        REAL,
  ref_high       REAL,
  effective_ts   TIMESTAMP NOT NULL,                    -- valid time: when observed
  recorded_ts    TIMESTAMP NOT NULL,                    -- transaction time: when stored
  status         TEXT NOT NULL,                         -- final | amended | entered-in-error
  supersedes     TEXT REFERENCES observation(observation_id)
);

CREATE TABLE med_request (
  request_id   TEXT PRIMARY KEY,
  encounter_id TEXT NOT NULL REFERENCES encounter(encounter_id),
  drug_code    TEXT NOT NULL,
  dose         TEXT,
  route        TEXT,
  freq         TEXT,
  start_date   DATE
);

CREATE INDEX idx_enc_patient  ON encounter(patient_id);
CREATE INDEX idx_obs_enc      ON observation(encounter_id);
CREATE INDEX idx_obs_order    ON observation(order_id);
CREATE INDEX idx_obs_supersed ON observation(supersedes);
CREATE INDEX idx_order_enc    ON lab_order(encounter_id);
