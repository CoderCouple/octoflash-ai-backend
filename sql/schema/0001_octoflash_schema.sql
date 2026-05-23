-- ============================================================================
-- Octoflash AI Backend — Full schema (greenfield bootstrap)
-- ----------------------------------------------------------------------------
-- Design decisions:
--   * IDs: TEXT with '<prefix>_' || gen_random_uuid()
--   * Enums: native PG ENUM types at DB layer + Python str-Enum at app layer.
--     SQLAlchemy binds via Enum(MyEnum, name='my_enum', create_type=False).
--   * Tenancy: User → OrgMembership → Organization → Workspace → Project (video).
--     `organization` is the billing boundary; `subscription` is 1:1 with org.
--     `workspace` groups projects inside an org and is the per-request
--     tenancy unit (X-Workspace-Id header).
--   * Auth: Cognito-backed. `user.cognito_sub` is the upstream identity;
--     signup/login/MFA live in Cognito Hosted UI, not in this backend.
--   * Audit: created_by / updated_by are nullable FK → "user"(id).
--   * Soft delete: is_deleted on owning entities (not membership / sub / billing_event).
--   * JSON: JSONB throughout.
--   * No CHECK constraints — enums enforce values.
--   * Reserved-word avoidance: workflow_execution.trigger_kind, workflow_node_prop.prop_group.
--   * "user" is double-quoted because USER is a reserved word.
--   * `source` = input library (channels the user pulls source content FROM).
--     `target` = publishing destinations (accounts the user posts the final video TO).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid()

-- ============================================================================
-- ENUM TYPES
-- ============================================================================
-- NOTE: role / membership_status / plan / subscription_status are stored as
-- VARCHAR rather than PG enums (Org tier values change on every billing
-- experiment — keeping them as text avoids ALTER TYPE migrations).

CREATE TYPE project_status_enum AS ENUM (
  'queued', 'analyzing', 'analyzed', 'generating', 'generated', 'published', 'failed'
);
CREATE TYPE scene_status_enum AS ENUM (
  'draft', 'scripting', 'rendering', 'ready', 'failed'
);
CREATE TYPE orientation_enum AS ENUM ('portrait', 'landscape');
CREATE TYPE quality_enum     AS ENUM ('480p', '720p', '1080p');
CREATE TYPE render_method_enum AS ENUM (
  'claude_voice', 'claude_voice_retry', 'claude_novoice',
  'claude_novoice_fresh', 'simple_fallback'
);

CREATE TYPE source_platform_enum   AS ENUM ('youtube');
CREATE TYPE source_video_kind_enum AS ENUM ('short', 'landscape');

CREATE TYPE target_platform_enum AS ENUM ('youtube', 'tiktok', 'instagram', 'linkedin', 'x');
CREATE TYPE target_status_enum   AS ENUM ('active', 'disconnected', 'expired');

CREATE TYPE workflow_status_enum AS ENUM ('DRAFT', 'PUBLISHED');
CREATE TYPE workflow_kind_enum AS ENUM (
  'analyze', 'generate', 'regenerate_clip', 'export', 'preview', 'transcribe'
);

CREATE TYPE node_prop_group_enum AS ENUM ('input', 'output', 'readonly');
CREATE TYPE node_prop_type_enum  AS ENUM ('string', 'number', 'boolean', 'json');

CREATE TYPE execution_trigger_enum AS ENUM ('MANUAL', 'CRON', 'API');
CREATE TYPE execution_status_enum AS ENUM (
  'PENDING', 'RUNNING', 'COMPLETED', 'FAILED',
  'CANCELED', 'TERMINATED', 'TIMED_OUT'
);
CREATE TYPE execution_phase_status_enum AS ENUM (
  'CREATED', 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
);
CREATE TYPE log_level_enum AS ENUM ('DEBUG', 'INFO', 'WARN', 'ERROR');

-- ============================================================================
-- IDENTITY (Cognito-backed)
-- ============================================================================

CREATE TABLE "user" (
  id                    TEXT PRIMARY KEY DEFAULT ('user_' || gen_random_uuid()) NOT NULL,
  cognito_sub           TEXT         UNIQUE NOT NULL,
  email                 VARCHAR(320),
  display_name          VARCHAR(255),
  avatar_url            VARCHAR(2048),
  default_org_id        TEXT,
  default_workspace_id  TEXT,
  last_login_at         TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_user_cognito_sub ON "user"(cognito_sub);
CREATE INDEX ix_user_email       ON "user"(email);

-- Per-user settings, satellite table. JSONB blob means new preferences are
-- a Pydantic-model edit only — no DB migration. user_id is PK (strict 1:1).
CREATE TABLE user_preference (
  user_id     TEXT PRIMARY KEY REFERENCES "user"(id) ON DELETE CASCADE,
  prefs       JSONB        NOT NULL DEFAULT '{}'::jsonb,
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE credential (
  id           TEXT PRIMARY KEY DEFAULT ('cred_' || gen_random_uuid()) NOT NULL,
  user_id      TEXT NOT NULL REFERENCES "user"(id),
  name         VARCHAR(255) NOT NULL,
  value        TEXT NOT NULL,  -- OAuth blob for targets, or generic secret
  created_by   TEXT REFERENCES "user"(id),
  updated_by   TEXT REFERENCES "user"(id),
  is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_credential_user_id ON credential(user_id);

-- ============================================================================
-- MULTI-TENANCY — Organization / OrgMembership / Workspace
-- ----------------------------------------------------------------------------
-- `organization` is the billing boundary and the root of multi-tenancy.
-- `org_membership` joins users to orgs with a role; user_id is nullable to
-- support email-only invitations (filled in on first sign-in by matching
-- invited_email).
-- `workspace` is the top-level grouping inside an org and the per-request
-- tenancy unit (X-Workspace-Id header). Slugs are unique per org.
-- ============================================================================

CREATE TABLE organization (
  id          TEXT PRIMARY KEY DEFAULT ('org_' || gen_random_uuid()) NOT NULL,
  name        VARCHAR(255) NOT NULL,
  slug        VARCHAR(255) NOT NULL UNIQUE,
  plan        VARCHAR(30)  NOT NULL DEFAULT 'free',   -- free | pro | enterprise (denorm of subscription.plan)
  logo_url    VARCHAR(2048),
  is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
  created_by  TEXT,
  updated_by  TEXT,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_organization_slug ON organization(slug);

CREATE TABLE org_membership (
  id            TEXT PRIMARY KEY DEFAULT ('om_' || gen_random_uuid()) NOT NULL,
  org_id        TEXT         NOT NULL,
  user_id       TEXT,                                 -- NULL until invited email signs up
  role          VARCHAR(30)  NOT NULL DEFAULT 'member',  -- owner | admin | member
  status        VARCHAR(30)  NOT NULL DEFAULT 'active',  -- active | invited | suspended
  invited_by    TEXT,
  invited_email VARCHAR(320),
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT uq_org_membership_org_user UNIQUE (org_id, user_id)
);
CREATE INDEX ix_org_membership_org_id  ON org_membership(org_id);
CREATE INDEX ix_org_membership_user_id ON org_membership(user_id);

CREATE TABLE workspace (
  id          TEXT PRIMARY KEY DEFAULT ('ws_' || gen_random_uuid()) NOT NULL,
  org_id      TEXT         NOT NULL,
  name        VARCHAR(255) NOT NULL,
  slug        VARCHAR(255) NOT NULL,
  description TEXT,
  is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
  created_by  TEXT,
  updated_by  TEXT,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT uq_workspace_org_slug UNIQUE (org_id, slug)
);
CREATE INDEX ix_workspace_org_id ON workspace(org_id);

-- ============================================================================
-- BILLING — Stripe-backed per-organization
-- ----------------------------------------------------------------------------
-- `subscription` is 1:1 with organization; carries the Stripe customer +
-- subscription IDs and the current plan/status/seat_count/period dates.
-- `billing_event` is the append-only audit log of every processed Stripe
-- webhook, deduplicated by `stripe_event_id`.
-- ============================================================================

CREATE TABLE subscription (
  id                     TEXT PRIMARY KEY DEFAULT ('sub_' || gen_random_uuid()) NOT NULL,
  org_id                 TEXT          NOT NULL UNIQUE,
  stripe_customer_id     VARCHAR(255)  NOT NULL,
  stripe_subscription_id VARCHAR(255)  UNIQUE,           -- NULL on free tier
  plan                   VARCHAR(30)   NOT NULL DEFAULT 'free',
  status                 VARCHAR(30)   NOT NULL DEFAULT 'active',
  seat_count             INTEGER       NOT NULL DEFAULT 1,
  current_period_start   TIMESTAMPTZ,
  current_period_end     TIMESTAMPTZ,
  cancel_at_period_end   VARCHAR(5)    NOT NULL DEFAULT 'false',
  created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_subscription_org_id                 ON subscription(org_id);
CREATE INDEX ix_subscription_stripe_customer_id     ON subscription(stripe_customer_id);
CREATE INDEX ix_subscription_stripe_subscription_id ON subscription(stripe_subscription_id);

CREATE TABLE billing_event (
  id               TEXT PRIMARY KEY DEFAULT ('be_' || gen_random_uuid()) NOT NULL,
  stripe_event_id  VARCHAR(255) NOT NULL UNIQUE,
  event_type       VARCHAR(100) NOT NULL,
  org_id           TEXT,
  payload          TEXT         NOT NULL,
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_billing_event_stripe_event_id ON billing_event(stripe_event_id);
CREATE INDEX ix_billing_event_org_id          ON billing_event(org_id);

-- ============================================================================
-- SOURCES — user's input library (channels they pull source content FROM)
-- ============================================================================

CREATE TABLE source (
  id                TEXT PRIMARY KEY DEFAULT ('src_' || gen_random_uuid()) NOT NULL,
  user_id           TEXT NOT NULL REFERENCES "user"(id),
  platform          source_platform_enum NOT NULL DEFAULT 'youtube',
  source_url        TEXT NOT NULL,
  external_id       VARCHAR(128),
  handle            VARCHAR(128),
  name              VARCHAR(255) NOT NULL,
  description       TEXT,
  thumbnail_url     TEXT,
  subscriber_count  BIGINT,
  accent_color      VARCHAR(16),
  last_synced_at    TIMESTAMPTZ,
  is_deleted        BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_source_user_id     ON source(user_id);
CREATE INDEX idx_source_external_id ON source(external_id);

CREATE TABLE source_video (
  id                TEXT PRIMARY KEY DEFAULT ('srcv_' || gen_random_uuid()) NOT NULL,
  source_id         TEXT NOT NULL REFERENCES source(id) ON DELETE CASCADE,
  external_id       VARCHAR(64) NOT NULL,
  source_url        TEXT NOT NULL,
  title             TEXT NOT NULL,
  description       TEXT,
  thumbnail_url     TEXT,
  kind              source_video_kind_enum NOT NULL DEFAULT 'landscape',
  duration_seconds  INTEGER,
  view_count        BIGINT,
  published_at      TIMESTAMPTZ,
  fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_source_video_external_id UNIQUE (source_id, external_id)
);
CREATE INDEX idx_source_video_source_id ON source_video(source_id);

-- ============================================================================
-- TARGETS — user's publishing destinations (where they post the final video TO)
-- ============================================================================

CREATE TABLE target (
  id               TEXT PRIMARY KEY DEFAULT ('tgt_' || gen_random_uuid()) NOT NULL,
  user_id          TEXT NOT NULL REFERENCES "user"(id),
  platform         target_platform_enum NOT NULL,
  external_id      VARCHAR(128),
  handle           VARCHAR(128),
  display_name     VARCHAR(255),
  avatar_url       TEXT,
  status           target_status_enum NOT NULL DEFAULT 'active',
  credential_id    TEXT UNIQUE REFERENCES credential(id) ON DELETE SET NULL,  -- 1:1 OAuth blob
  connected_at     TIMESTAMPTZ,
  disconnected_at  TIMESTAMPTZ,
  last_synced_at   TIMESTAMPTZ,
  is_deleted       BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_target_user_platform_external UNIQUE (user_id, platform, external_id)
);
CREATE INDEX idx_target_user_id  ON target(user_id);
CREATE INDEX idx_target_platform ON target(platform);

-- ============================================================================
-- VIDEO DOMAIN — PROJECT + SCENE
-- ----------------------------------------------------------------------------
-- `project.org_id` + `project.workspace_id` are nullable while the legacy
-- routes are migrated to require auth. Newly created rows from authenticated
-- paths must populate both; a follow-up will tighten to NOT NULL.
-- ============================================================================

CREATE TABLE project (
  id               TEXT PRIMARY KEY DEFAULT ('prj_' || gen_random_uuid()) NOT NULL,
  user_id          TEXT NOT NULL REFERENCES "user"(id),
  org_id           TEXT,                                -- tenancy (nullable for now)
  workspace_id     TEXT,                                -- tenancy (nullable for now)
  title            VARCHAR(255) NOT NULL,
  source_url       TEXT,
  status           project_status_enum NOT NULL DEFAULT 'queued',
  orientation      orientation_enum    NOT NULL DEFAULT 'portrait',
  quality          quality_enum        NOT NULL DEFAULT '720p',
  voiceover        BOOLEAN             NOT NULL DEFAULT TRUE,
  voice_id         VARCHAR(64),
  voice_gender     VARCHAR(16),
  voice_accent     VARCHAR(32),
  target_duration  DOUBLE PRECISION,
  transcript       TEXT,
  description      TEXT,
  manim_prompt     TEXT,
  source_duration  DOUBLE PRECISION,
  frames_dir       TEXT,
  final_portrait_video_url   TEXT,
  final_landscape_video_url  TEXT,
  is_deleted       BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_project_user_id      ON project(user_id);
CREATE INDEX idx_project_status       ON project(status);
CREATE INDEX ix_project_org_id        ON project(org_id);
CREATE INDEX ix_project_workspace_id  ON project(workspace_id);

CREATE TABLE scene (
  id                 TEXT PRIMARY KEY DEFAULT ('scn_' || gen_random_uuid()) NOT NULL,
  project_id         TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  orientation        orientation_enum NOT NULL DEFAULT 'portrait',
  n                  INTEGER NOT NULL,
  title              VARCHAR(255),
  prompt             TEXT,
  duration           DOUBLE PRECISION,
  script_code        TEXT,
  script_code_hash   VARCHAR(64),
  script_file        TEXT,
  voice_id_override  VARCHAR(64),
  video_url          TEXT,
  render_method      render_method_enum,
  eval_score         INTEGER,
  eval_feedback      TEXT,
  status             scene_status_enum NOT NULL DEFAULT 'draft',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_scene_project_orientation_n UNIQUE (project_id, orientation, n)
);
CREATE INDEX idx_scene_project_id        ON scene(project_id);
CREATE INDEX idx_scene_script_code_hash  ON scene(script_code_hash);

-- ============================================================================
-- WORKFLOW / DAG
-- ============================================================================

CREATE TABLE workflow (
  id                TEXT PRIMARY KEY DEFAULT ('workflow_' || gen_random_uuid()) NOT NULL,
  project_id        TEXT UNIQUE NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  user_id           TEXT NOT NULL REFERENCES "user"(id),
  name              VARCHAR(255),
  description       VARCHAR(1024),
  definition        JSONB,                                              -- React Flow nodes+edges
  execution_plan    JSONB,                                              -- derived topo order
  status            workflow_status_enum NOT NULL DEFAULT 'DRAFT',
  cron              VARCHAR(100),
  credits_cost      NUMERIC,
  last_run_at       TIMESTAMPTZ,
  last_run_id       VARCHAR(64),
  last_run_status   VARCHAR(50),
  next_run_at       TIMESTAMPTZ,
  created_by        TEXT REFERENCES "user"(id),
  updated_by        TEXT REFERENCES "user"(id),
  is_deleted        BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_workflow_user_id ON workflow(user_id);
CREATE INDEX idx_workflow_status  ON workflow(status);

CREATE TABLE workflow_node_type (
  id              TEXT PRIMARY KEY DEFAULT ('node_' || gen_random_uuid()) NOT NULL,
  name            VARCHAR(255) NOT NULL,
  type            VARCHAR(100) UNIQUE NOT NULL,  -- machine key: source_url, scene, target, ...
  retries         INTEGER     NOT NULL DEFAULT 0,
  timeout_seconds INTEGER     NOT NULL DEFAULT 30,
  error_message   TEXT,
  created_by      TEXT REFERENCES "user"(id),
  updated_by      TEXT REFERENCES "user"(id),
  is_deleted      BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workflow_node_prop (
  id           TEXT PRIMARY KEY DEFAULT ('nprop_' || gen_random_uuid()) NOT NULL,
  node_id      TEXT NOT NULL REFERENCES workflow_node_type(id) ON DELETE CASCADE,
  key          VARCHAR(100) NOT NULL,
  value        TEXT NOT NULL,
  prop_group   node_prop_group_enum NOT NULL,
  type         node_prop_type_enum  NOT NULL,
  created_by   TEXT REFERENCES "user"(id),
  updated_by   TEXT REFERENCES "user"(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_workflow_node_prop_node_key UNIQUE (node_id, key)
);

CREATE TABLE workflow_node_instance (
  id           TEXT PRIMARY KEY DEFAULT ('wni_' || gen_random_uuid()) NOT NULL,
  workflow_id  TEXT NOT NULL REFERENCES workflow(id) ON DELETE CASCADE,
  type_id      TEXT NOT NULL REFERENCES workflow_node_type(id),
  scene_id     TEXT REFERENCES scene(id) ON DELETE SET NULL,           -- only when type='scene'
  x            DOUBLE PRECISION NOT NULL DEFAULT 0,
  y            DOUBLE PRECISION NOT NULL DEFAULT 0,
  w            DOUBLE PRECISION,
  h            DOUBLE PRECISION,
  label        VARCHAR(255),
  config       JSONB,
  created_by   TEXT REFERENCES "user"(id),
  updated_by   TEXT REFERENCES "user"(id),
  is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wni_workflow_id ON workflow_node_instance(workflow_id);
CREATE INDEX idx_wni_type_id     ON workflow_node_instance(type_id);
CREATE INDEX idx_wni_scene_id    ON workflow_node_instance(scene_id);

-- workflow_edge_instance — per-canvas edge placement. Symmetric with
-- workflow_node_instance: projection of edges from workflow.definition JSON,
-- maintained on save so we can query connectivity without parsing JSONB.
CREATE TABLE workflow_edge_instance (
  id                   TEXT PRIMARY KEY DEFAULT ('we_' || gen_random_uuid()) NOT NULL,
  workflow_id          TEXT NOT NULL REFERENCES workflow(id) ON DELETE CASCADE,
  source_instance_id   TEXT NOT NULL REFERENCES workflow_node_instance(id) ON DELETE CASCADE,
  target_instance_id   TEXT NOT NULL REFERENCES workflow_node_instance(id) ON DELETE CASCADE,
  source_handle        VARCHAR(64),                                       -- React Flow handle id
  target_handle        VARCHAR(64),
  label                VARCHAR(255),
  data                 JSONB,
  created_by           TEXT REFERENCES "user"(id),
  updated_by           TEXT REFERENCES "user"(id),
  is_deleted           BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wei_workflow_id        ON workflow_edge_instance(workflow_id);
CREATE INDEX idx_wei_source_instance_id ON workflow_edge_instance(source_instance_id);
CREATE INDEX idx_wei_target_instance_id ON workflow_edge_instance(target_instance_id);

-- ============================================================================
-- EXECUTION LINEAGE — replaces the old `job` table.
-- Each workflow_execution is one Temporal workflow run; phases are activities.
-- ============================================================================

CREATE TABLE workflow_execution (
  id                            TEXT PRIMARY KEY DEFAULT ('execution_' || gen_random_uuid()) NOT NULL,
  workflow_id                   TEXT NOT NULL REFERENCES workflow(id) ON DELETE CASCADE,
  -- NULL for project-level executions; set when the run was triggered by
  -- clicking a specific DAG node (the new POST /workflows/{id}/nodes/{id}/run).
  node_instance_id              TEXT REFERENCES workflow_node_instance(id) ON DELETE SET NULL,
  user_id                       TEXT NOT NULL REFERENCES "user"(id),
  kind                          workflow_kind_enum     NOT NULL,
  trigger_kind                  execution_trigger_enum NOT NULL DEFAULT 'MANUAL',
  status                        execution_status_enum  NOT NULL DEFAULT 'PENDING',
  credits_consumed              NUMERIC,
  started_at                    TIMESTAMPTZ,
  completed_at                  TIMESTAMPTZ,
  -- Temporal-derived metadata
  temporal_workflow_id          VARCHAR(255) NOT NULL,                  -- stable handle
  temporal_run_id               VARCHAR(64),                            -- rotates on restart
  temporal_workflow_type        VARCHAR(128),                           -- e.g. AnalyzeProjectWorkflow
  temporal_task_queue           VARCHAR(128),
  temporal_namespace            VARCHAR(128),
  temporal_parent_workflow_id   VARCHAR(255),
  temporal_parent_run_id        VARCHAR(64),
  temporal_history_length       INTEGER,
  temporal_history_size_bytes   BIGINT,
  temporal_last_failure         JSONB,                                  -- {type, message, stack_trace}
  temporal_memo                 JSONB,
  temporal_search_attributes    JSONB,
  -- Audit
  created_by   TEXT REFERENCES "user"(id),
  updated_by   TEXT REFERENCES "user"(id),
  is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wexec_workflow_id            ON workflow_execution(workflow_id);
CREATE INDEX idx_wexec_user_id                ON workflow_execution(user_id);
CREATE INDEX idx_wexec_status                 ON workflow_execution(status);
CREATE INDEX idx_wexec_temporal_workflow_id   ON workflow_execution(temporal_workflow_id);

CREATE TABLE execution_phase (
  id                          TEXT PRIMARY KEY DEFAULT ('phase_' || gen_random_uuid()) NOT NULL,
  workflow_execution_id       TEXT NOT NULL REFERENCES workflow_execution(id) ON DELETE CASCADE,
  user_id                     TEXT NOT NULL REFERENCES "user"(id),
  status                      execution_phase_status_enum NOT NULL DEFAULT 'CREATED',
  number                      INTEGER NOT NULL,
  node                        VARCHAR(255),                            -- snapshot string, not FK
  name                        VARCHAR(255),
  started_at                  TIMESTAMPTZ,
  completed_at                TIMESTAMPTZ,
  inputs                      JSONB,
  outputs                     JSONB,
  credits_consumed            NUMERIC,
  -- Temporal-derived metadata
  temporal_activity_id        VARCHAR(255),
  temporal_activity_type      VARCHAR(128),                            -- e.g. render_clip_activity
  temporal_attempt            INTEGER,
  temporal_max_attempts       INTEGER,
  temporal_heartbeat_at       TIMESTAMPTZ,
  temporal_heartbeat_details  JSONB,
  temporal_last_failure       JSONB,
  -- Audit
  created_by   TEXT REFERENCES "user"(id),
  updated_by   TEXT REFERENCES "user"(id),
  is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_phase_workflow_execution_id ON execution_phase(workflow_execution_id);
CREATE INDEX idx_phase_status                ON execution_phase(status);

CREATE TABLE execution_log (
  id                   TEXT PRIMARY KEY DEFAULT ('execlog_' || gen_random_uuid()) NOT NULL,
  execution_phase_id   TEXT NOT NULL REFERENCES execution_phase(id) ON DELETE CASCADE,
  log_level            log_level_enum NOT NULL,
  message              VARCHAR(2048) NOT NULL,
  "timestamp"          TIMESTAMPTZ NOT NULL,
  created_by           TEXT REFERENCES "user"(id),
  updated_by           TEXT REFERENCES "user"(id),
  is_deleted           BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_log_phase_timestamp ON execution_log(execution_phase_id, "timestamp");

-- ============================================================================
-- SEED — default user (placeholder until existing routes are migrated to auth)
-- ----------------------------------------------------------------------------
-- Every owned row needs a user_id FK. New routes (auth/tenancy/billing) use
-- Cognito-resolved UserContext; legacy routes still fall back to this
-- well-known id (mirrored in settings.default_user_id). `cognito_sub='default'`
-- is unreachable from real Cognito tokens.
-- ============================================================================

INSERT INTO "user" (id, cognito_sub, email, display_name) VALUES
  (
    'user_00000000-0000-0000-0000-000000000001',
    'default',
    'default@octoflash.local',
    'Default User'
  );

-- Empty preferences row for the seed user so /me can use INNER JOIN.
INSERT INTO user_preference (user_id) VALUES
  ('user_00000000-0000-0000-0000-000000000001');

-- ============================================================================
-- SEED — workflow_node_type catalog
-- ============================================================================

INSERT INTO workflow_node_type (name, type) VALUES
  ('Source: URL',  'source_url'),
  ('Source: Text', 'source_text'),
  ('Analyze',      'analyze'),
  ('Scene',        'scene'),
  ('Target',       'target');
