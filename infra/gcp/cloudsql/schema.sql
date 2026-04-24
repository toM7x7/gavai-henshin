-- New route durable schema for Cloud SQL PostgreSQL.
-- Source of truth split:
-- - Cloud SQL: source rows, versions, trials, events, audit.
-- - GCS: JSON artifacts, generated textures, GLB, replay script, media.
-- - Firestore: live Quest/operator state only.

create table if not exists projects (
  project_id text primary key,
  display_name text not null,
  status text not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists suits (
  suit_id text primary key,
  project_id text references projects(project_id),
  status text not null default 'DRAFT',
  canonical_version integer not null default 1,
  latest_manifest_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists suit_versions (
  suit_id text not null references suits(suit_id),
  version integer not null,
  suitspec_schema_version text not null,
  suitspec_json jsonb not null,
  suitspec_gcs_uri text,
  manifest_id text,
  manifest_gcs_uri text,
  created_by text,
  created_at timestamptz not null default now(),
  primary key (suit_id, version)
);

create table if not exists part_catalogs (
  catalog_id text primary key,
  schema_version text not null,
  status text not null,
  catalog_json jsonb not null,
  catalog_gcs_uri text,
  created_at timestamptz not null default now()
);

create table if not exists transform_sessions (
  session_id text primary key,
  suit_id text references suits(suit_id),
  manifest_id text not null,
  operator_id text,
  device_id text,
  tracking_source text,
  state text not null,
  started_at timestamptz not null,
  completed_at timestamptz,
  session_json jsonb not null,
  replay_script_gcs_uri text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists transform_events (
  event_id text primary key,
  session_id text not null references transform_sessions(session_id) on delete cascade,
  sequence integer not null,
  event_type text not null,
  occurred_at timestamptz not null,
  actor_json jsonb,
  state_before text,
  state_after text,
  payload_json jsonb not null default '{}'::jsonb,
  idempotency_key text,
  created_at timestamptz not null default now(),
  unique (session_id, sequence),
  unique (session_id, idempotency_key)
);

create table if not exists audit_logs (
  audit_id bigserial primary key,
  subject_type text not null,
  subject_id text not null,
  action text not null,
  actor_id text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_suit_versions_manifest_id on suit_versions(manifest_id);
create index if not exists idx_transform_sessions_suit_id on transform_sessions(suit_id);
create index if not exists idx_transform_events_session_sequence on transform_events(session_id, sequence);
