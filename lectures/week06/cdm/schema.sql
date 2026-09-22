-- HY-489 Week 6: a teaching subset of the OMOP Common Data Model.
--
-- Eight clinical tables plus three vocabulary tables, in SQLite. The real CDM
-- v5.4 has around forty tables and every table here has columns we have left
-- out. The specification is at ohdsi.github.io/CommonDataModel; read it before
-- you build anything real.
--
-- What is faithful:
--   * the table names and the column names
--   * the concept triple on every clinical table
--   * person_id as the spine, visit_occurrence_id as the context
--   * observation_period as the denominator
--
-- What is not:
--   * no cost, payer, provider, care_site, location, note, or device tables
--   * no *_datetime columns, only dates
--   * no era tables (drug_era, condition_era, dose_era)
--   * SQLite types, not the DDL the specification prescribes

DROP TABLE IF EXISTS person;
DROP TABLE IF EXISTS observation_period;
DROP TABLE IF EXISTS visit_occurrence;
DROP TABLE IF EXISTS condition_occurrence;
DROP TABLE IF EXISTS drug_exposure;
DROP TABLE IF EXISTS measurement;
DROP TABLE IF EXISTS observation;
DROP TABLE IF EXISTS death;
DROP TABLE IF EXISTS concept;
DROP TABLE IF EXISTS concept_relationship;
DROP TABLE IF EXISTS concept_ancestor;
DROP TABLE IF EXISTS cdm_source;

-- ---------------------------------------------------------------- vocabulary

CREATE TABLE concept (
    concept_id        INTEGER PRIMARY KEY,
    concept_name      TEXT    NOT NULL,
    domain_id         TEXT    NOT NULL,
    vocabulary_id     TEXT    NOT NULL,
    concept_class_id  TEXT,
    standard_concept  TEXT,            -- 'S', 'C', or NULL. NULL means non-standard.
    concept_code      TEXT    NOT NULL,
    valid_start_date  TEXT,
    valid_end_date    TEXT,
    invalid_reason    TEXT             -- NULL means currently valid.
);

CREATE TABLE concept_relationship (
    concept_id_1      INTEGER NOT NULL,
    concept_id_2      INTEGER NOT NULL,
    relationship_id   TEXT    NOT NULL,
    valid_start_date  TEXT,
    valid_end_date    TEXT,
    invalid_reason    TEXT
);

CREATE TABLE concept_ancestor (
    ancestor_concept_id         INTEGER NOT NULL,
    descendant_concept_id       INTEGER NOT NULL,
    min_levels_of_separation    INTEGER,
    max_levels_of_separation    INTEGER
);

-- ------------------------------------------------------------------ clinical

CREATE TABLE person (
    person_id             INTEGER PRIMARY KEY,
    gender_concept_id     INTEGER NOT NULL,
    year_of_birth         INTEGER NOT NULL,
    month_of_birth        INTEGER,
    day_of_birth          INTEGER,
    race_concept_id       INTEGER NOT NULL,
    ethnicity_concept_id  INTEGER NOT NULL,
    person_source_value   TEXT,          -- the source system's own identifier
    gender_source_value   TEXT
);

-- The denominator. Without it you cannot tell "no diabetes" from "not looking".
CREATE TABLE observation_period (
    observation_period_id          INTEGER PRIMARY KEY,
    person_id                      INTEGER NOT NULL,
    observation_period_start_date  TEXT    NOT NULL,
    observation_period_end_date    TEXT    NOT NULL,
    period_type_concept_id         INTEGER NOT NULL
);

CREATE TABLE visit_occurrence (
    visit_occurrence_id     INTEGER PRIMARY KEY,
    person_id               INTEGER NOT NULL,
    visit_concept_id        INTEGER NOT NULL,
    visit_start_date        TEXT    NOT NULL,
    visit_end_date          TEXT,
    visit_type_concept_id   INTEGER NOT NULL,
    visit_source_value      TEXT
);

CREATE TABLE condition_occurrence (
    condition_occurrence_id      INTEGER PRIMARY KEY,
    person_id                    INTEGER NOT NULL,
    condition_concept_id         INTEGER NOT NULL,   -- 0 when unmapped
    condition_start_date         TEXT    NOT NULL,
    condition_end_date           TEXT,
    condition_type_concept_id    INTEGER NOT NULL,
    visit_occurrence_id          INTEGER,
    condition_source_value       TEXT,               -- what the source said
    condition_source_concept_id  INTEGER             -- the source code as a concept
);

CREATE TABLE drug_exposure (
    drug_exposure_id             INTEGER PRIMARY KEY,
    person_id                    INTEGER NOT NULL,
    drug_concept_id              INTEGER NOT NULL,
    drug_exposure_start_date     TEXT    NOT NULL,
    drug_exposure_end_date       TEXT,
    drug_type_concept_id         INTEGER NOT NULL,   -- prescription? dispensing?
    quantity                     REAL,
    visit_occurrence_id          INTEGER,
    drug_source_value            TEXT,
    drug_source_concept_id       INTEGER
);

CREATE TABLE measurement (
    measurement_id                INTEGER PRIMARY KEY,
    person_id                     INTEGER NOT NULL,
    measurement_concept_id        INTEGER NOT NULL,
    measurement_date              TEXT    NOT NULL,
    measurement_type_concept_id   INTEGER NOT NULL,
    value_as_number               REAL,
    value_as_concept_id           INTEGER,
    unit_concept_id               INTEGER,
    visit_occurrence_id           INTEGER,
    measurement_source_value      TEXT,
    measurement_source_concept_id INTEGER,
    unit_source_value             TEXT
);

CREATE TABLE observation (
    observation_id                INTEGER PRIMARY KEY,
    person_id                     INTEGER NOT NULL,
    observation_concept_id        INTEGER NOT NULL,
    observation_date              TEXT    NOT NULL,
    observation_type_concept_id   INTEGER NOT NULL,
    value_as_number               REAL,
    value_as_string               TEXT,
    value_as_concept_id           INTEGER,
    unit_concept_id               INTEGER,
    visit_occurrence_id           INTEGER,
    observation_source_value      TEXT,
    observation_source_concept_id INTEGER
);

CREATE TABLE death (
    person_id              INTEGER PRIMARY KEY,
    death_date             TEXT    NOT NULL,
    death_type_concept_id  INTEGER NOT NULL,
    cause_concept_id       INTEGER
);

-- One row. The first thing a collaborator reads, and the first thing real ETLs
-- forget to fill in.
CREATE TABLE cdm_source (
    cdm_source_name             TEXT,
    cdm_source_abbreviation     TEXT,
    cdm_holder                  TEXT,
    source_description          TEXT,
    cdm_etl_reference           TEXT,
    source_release_date         TEXT,
    cdm_release_date            TEXT,
    cdm_version                 TEXT,
    vocabulary_version          TEXT
);

CREATE INDEX idx_co_person   ON condition_occurrence (person_id);
CREATE INDEX idx_co_concept  ON condition_occurrence (condition_concept_id);
CREATE INDEX idx_meas_person ON measurement (person_id);
CREATE INDEX idx_obs_person  ON observation (person_id);
CREATE INDEX idx_vo_person   ON visit_occurrence (person_id);
CREATE INDEX idx_ca_anc      ON concept_ancestor (ancestor_concept_id);
CREATE INDEX idx_ca_desc     ON concept_ancestor (descendant_concept_id);
