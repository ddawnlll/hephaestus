-- db/migrations/001_candidates.sql
-- Migration 001: candidate manifest tables (DL-2, #97).
--
-- Mirrors the JSON Schema in schema/candidate.schema.json (BE-1 #82) into
-- Postgres tables. JSONB columns carry the flexible data field; fixed
-- columns carry the searchable / indexable fields.
--
-- Apply: python3 -m db.connection migrate

\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS vector;

-- candidates: main table
CREATE TABLE IF NOT EXISTS hephaestus.candidates (
    id                   UUID PRIMARY KEY,
    source_hypothesis    TEXT NOT NULL,
    workspace            TEXT NOT NULL,
    base_state_hash      CHAR(64) NOT NULL,
    base_state_tick      BIGINT NOT NULL,
    effect_class         TEXT NOT NULL CHECK (effect_class IN
                              ('reversible_internal', 'compensable_external', 'irreversible_external')),
    merge_policy         TEXT NOT NULL CHECK (merge_policy IN
                              ('pr_only', 'pr_gated_auto')) DEFAULT 'pr_only',
    schema_version       INTEGER NOT NULL,
    state                TEXT NOT NULL CHECK (state IN
                              ('PROPOSED', 'MATERIALIZING', 'MATERIALIZED', 'VERIFYING',
                               'SHADOWING', 'CANARY', 'PROMOTED', 'OBSERVING',
                               'RETAINED', 'ROLLED_BACK', 'DISCARDED',
                               'REBASE_REQUIRED', 'DEAD')),
    kill_pause_freeze_clear BOOLEAN NOT NULL DEFAULT true,
    base_state_current   BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_tick         BIGINT NOT NULL,
    last_transition_tick BIGINT,
    last_transition_at   TIMESTAMPTZ,
    data                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_history        JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_candidates_state ON hephaestus.candidates(state);
CREATE INDEX IF NOT EXISTS idx_candidates_effect_class ON hephaestus.candidates(effect_class);
CREATE INDEX IF NOT EXISTS idx_candidates_merge_policy ON hephaestus.candidates(merge_policy);
CREATE INDEX IF NOT EXISTS idx_candidates_data_gin ON hephaestus.candidates USING GIN (data);
CREATE INDEX IF NOT EXISTS idx_candidates_state_history_gin ON hephaestus.candidates USING GIN (state_history);
CREATE INDEX IF NOT EXISTS idx_candidates_base_state_hash ON hephaestus.candidates(base_state_hash);

-- Conditional invariants via CHECK constraints (subset of the JSON Schema allOf).
ALTER TABLE hephaestus.candidates
    DROP CONSTRAINT IF EXISTS chk_irreversible_human_always;
ALTER TABLE hephaestus.candidates
    ADD CONSTRAINT chk_irreversible_human_always
    CHECK (
        effect_class <> 'irreversible_external'
        OR (data ? 'human_always' AND (data->>'human_always')::boolean = true)
    );

ALTER TABLE hephaestus.candidates
    DROP CONSTRAINT IF EXISTS chk_compensable_has_plan;
ALTER TABLE hephaestus.candidates
    ADD CONSTRAINT chk_compensable_has_plan
    CHECK (
        effect_class <> 'compensable_external'
        OR (data ? 'compensation_plan' AND data ? 'standing_policy')
    );

ALTER TABLE hephaestus.candidates
    DROP CONSTRAINT IF EXISTS chk_gated_auto_not_irreversible;
ALTER TABLE hephaestus.candidates
    ADD CONSTRAINT chk_gated_auto_not_irreversible
    CHECK (
        merge_policy <> 'pr_gated_auto'
        OR effect_class <> 'irreversible_external'
    );

-- rollback_snapshots: from BE-3 (#86) snapshot manifests
CREATE TABLE IF NOT EXISTS hephaestus.rollback_snapshots (
    candidate_id      UUID PRIMARY KEY REFERENCES hephaestus.candidates(id) ON DELETE CASCADE,
    asset_type        TEXT NOT NULL,
    captured_at_tick  BIGINT NOT NULL,
    captured_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    strategy          TEXT NOT NULL CHECK (strategy IN
                          ('git_reset', 'yaml_restore', 'schema_down', 'journal_revert')),
    rollback_ref      JSONB NOT NULL,
    verification      JSONB NOT NULL,
    expires_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rollback_snapshots_expires ON hephaestus.rollback_snapshots(expires_at);

-- intent_queue: from A-2 (#77) workspace intents
CREATE TABLE IF NOT EXISTS hephaestus.intent_queue (
    intent_id   UUID PRIMARY KEY,
    tick_id     BIGINT NOT NULL,
    actor       TEXT NOT NULL CHECK (actor IN ('human', 't4', 'reflector')),
    priority    SMALLINT NOT NULL CHECK (priority BETWEEN 0 AND 2),
    operation   TEXT NOT NULL,
    target      TEXT NOT NULL,
    evidence    TEXT,
    applied     BOOLEAN NOT NULL DEFAULT false,
    shadowed_by UUID,
    queued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_at  TIMESTAMPTZ,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_intent_queue_queued ON hephaestus.intent_queue(queued_at);
CREATE INDEX IF NOT EXISTS idx_intent_queue_priority ON hephaestus.intent_queue(priority, queued_at);
CREATE INDEX IF NOT EXISTS idx_intent_queue_unapplied
    ON hephaestus.intent_queue(queued_at) WHERE applied = false;

-- precedents: from BE-6 (#84) precedent memory
CREATE TABLE IF NOT EXISTS hephaestus.precedents (
    tick_id     BIGINT PRIMARY KEY,
    situation   JSONB NOT NULL,
    decision    TEXT,
    override    TEXT,
    outcome     TEXT NOT NULL CHECK (outcome IN
                  ('PROMOTED', 'ROLLED_BACK', 'DISCARDED', 'DEAD', 'HOLD')),
    lesson      TEXT NOT NULL DEFAULT '',
    stored_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_precedents_situation_gin ON hephaestus.precedents USING GIN (situation);
CREATE INDEX IF NOT EXISTS idx_precedents_outcome ON hephaestus.precedents(outcome);
