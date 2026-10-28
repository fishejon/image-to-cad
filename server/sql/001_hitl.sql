-- HITL + run outcomes (domain-agnostic). Keyed by run_id for join with PostHog / Langfuse.
-- Apply: DATABASE_URL=… node tools/migrate.js

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL DEFAULT 'furniture',
  task TEXT,
  input_mode TEXT,
  quality TEXT,
  model TEXT,
  staged BOOLEAN,
  visual BOOLEAN,
  geometry_ok BOOLEAN,
  rounds INTEGER,
  likeness_penalty DOUBLE PRECISION,
  iou DOUBLE PRECISION,
  unlabeled_contacts INTEGER,
  duration_ms INTEGER,
  error TEXT,
  image_hash TEXT,
  image_url TEXT,
  image_consent BOOLEAN NOT NULL DEFAULT FALSE,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS runs_domain_created_idx ON runs (domain, created_at DESC);
CREATE INDEX IF NOT EXISTS runs_model_idx ON runs (model);

CREATE TABLE IF NOT EXISTS feedback (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT REFERENCES runs (run_id) ON DELETE SET NULL,
  domain TEXT NOT NULL DEFAULT 'furniture',
  rating TEXT NOT NULL CHECK (rating IN ('match', 'close', 'wrong')),
  failure_tags TEXT[] NOT NULL DEFAULT '{}',
  note TEXT NOT NULL DEFAULT '',
  object TEXT,
  model TEXT,
  quality TEXT,
  inventory JSONB,
  client_ts TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS feedback_run_id_idx ON feedback (run_id);
CREATE INDEX IF NOT EXISTS feedback_rating_idx ON feedback (rating);
CREATE INDEX IF NOT EXISTS feedback_created_idx ON feedback (created_at DESC);

CREATE TABLE IF NOT EXISTS examples (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT REFERENCES runs (run_id) ON DELETE SET NULL,
  domain TEXT NOT NULL DEFAULT 'furniture',
  object TEXT,
  inventory JSONB,
  spec_summary JSONB,
  hints TEXT,
  model TEXT,
  quality TEXT,
  client_ts TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS examples_run_id_idx ON examples (run_id);
CREATE INDEX IF NOT EXISTS examples_created_idx ON examples (created_at DESC);
