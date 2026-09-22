-- HY-489 Lab 1 — mini-EHR schema
-- Portable between PostgreSQL and SQLite.
-- Load order matters: patient -> encounter -> condition / observation.

DROP TABLE IF EXISTS observation;
DROP TABLE IF EXISTS condition;
DROP TABLE IF EXISTS encounter;
DROP TABLE IF EXISTS patient;

CREATE TABLE patient (
  patient_id   TEXT PRIMARY KEY,
  birth_date   DATE,
  gender       TEXT,
  city         TEXT
);

CREATE TABLE encounter (
  encounter_id TEXT PRIMARY KEY,
  patient_id   TEXT NOT NULL REFERENCES patient(patient_id),
  start_ts     TIMESTAMP,
  stop_ts      TIMESTAMP,
  enc_class    TEXT,
  description  TEXT
);

CREATE TABLE condition (
  condition_id  INTEGER PRIMARY KEY,
  patient_id    TEXT NOT NULL REFERENCES patient(patient_id),
  encounter_id  TEXT          REFERENCES encounter(encounter_id),
  code          TEXT NOT NULL,
  code_system   TEXT NOT NULL,
  description   TEXT,
  onset_date    DATE
);

-- The three columns a naive schema would omit are all here:
--   encounter_id  -> provenance: which visit this belongs to
--   effective_ts / recorded_ts -> valid time vs transaction time
--   status + supersedes -> corrections without deletion
CREATE TABLE observation (
  observation_id INTEGER PRIMARY KEY,
  patient_id     TEXT NOT NULL REFERENCES patient(patient_id),
  encounter_id   TEXT          REFERENCES encounter(encounter_id),
  code           TEXT NOT NULL,
  code_system    TEXT NOT NULL,
  description    TEXT,
  value_num      REAL,
  value_text     TEXT,
  units          TEXT,
  effective_ts   TIMESTAMP NOT NULL,
  recorded_ts    TIMESTAMP NOT NULL,
  status         TEXT NOT NULL DEFAULT 'final',
  supersedes     INTEGER REFERENCES observation(observation_id)
);

CREATE INDEX idx_encounter_patient    ON encounter(patient_id);
CREATE INDEX idx_condition_patient    ON condition(patient_id);
CREATE INDEX idx_observation_patient  ON observation(patient_id);
CREATE INDEX idx_observation_code     ON observation(code);
