# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Backend for **Octoflash AI** — a scene-first, AI-driven video editor for Manim animations. Users describe what they want (or hand over a source URL — YouTube / article); the system produces a video by stitching together independently-rendered Manim clips. Each clip is its own Manim render, so editing one scene only re-renders that scene — never the whole video.

The frontend lives in a sibling repo `octoflash-ai-frontend/` (in-progress migration from Next.js 15 to a Vite + React monorepo: `packages/core` shared TS, `packages/web` Vite SPA, `packages/desktop` Electron wrapper). Its typed API client defaults to **`http://localhost:8000`** — this service should bind to `:8000` in dev.

## Project state

Mid-refactor. The old template/variation/job machinery has been deleted; the new pipeline is **Temporal-orchestrated, Claude-codegen Manim** — no static template catalog, no per-scene `(template_id, params)`. The skeleton (settings, DB engine/session, exception envelope, base response, alembic env, 9 controllers, 17 SQLAlchemy models, 8 repositories, 21 services, 3 Temporal workflows, 6 activities) is wired and mostly implemented.

Known stubs:
- `app/service/export_service.py` — `queue_preview` / `queue_export` both `raise NotImplementedError`. Pending **task 12** (workflow rewire — collapsing preview/export into the same generate flow with different quality settings).
- `app/service/youtube_fetcher_service.py` — `raise NotImplementedError` on the fetcher methods.
- `app/workers/activities/analyze_activity.py` — one branch raises `NotImplementedError`.

Layout and conventions are deliberately mirrored from the `octopod-backend` repo (FastAPI + async SQLAlchemy 2.0 + asyncpg + Alembic + Poetry + ruff/black/isort/mypy + pre-commit).

## Common commands

```bash
make install            # poetry install
make dev                # uvicorn --reload on :8000
make worker             # Temporal worker (local dev server)
make worker-cloud       # Temporal worker against Temporal Cloud (TEMPORAL_PROFILE=cloud)
make preview T=<id>     # Run a local Manim preview script directly — no API / Temporal / DB
make test               # pytest -v
make lint               # ruff + mypy
make format             # black + isort + ruff --fix
make migrate            # alembic upgrade head
make migration MSG="..." # alembic revision --autogenerate
make docker-up          # web + worker + db + redis + pgadmin + temporal dev server
make docker-db          # just db + pgadmin
```

Heavy native deps (Manim → Cairo/Pango/FFmpeg, audio → libsndfile) are wired in the Dockerfile. Local dev needs them via brew/apt; see `Dockerfile` for the exact list.

## Architecture

### Layered request flow

```
controller (api/v1/controller)
  ├─ pydantic request (api/v1/request)
  └─ service                          ← business logic, transactions
       └─ repository (db/repository)   ← all DB queries live here, nowhere else
            └─ SQLAlchemy model (model/)
  → response model (api/v1/response) wrapped in BaseResponse envelope
```

All endpoints return `BaseResponse[T]` — `{ result, status_code, message, success }`. Wrap successful responses via `success_response(...)`; error envelopes are auto-applied by `register_exception_handlers` for any raised `HTTPException` (including the custom ones in `app/common/exceptions.py`).

### Auth + tenancy (Supabase → UserContext → Org / Workspace)

Auth is **not** a set of endpoints — it's a JWT-verification dependency layered on every protected route. Sign-up / sign-in / password-reset / MFA all live in Supabase Auth on the frontend (`@supabase/supabase-js`); the FE sends the resulting access token as `Authorization: Bearer <JWT>`.

Request shape:
```
Authorization: Bearer <Supabase JWT>
X-Org-Id:        <org_…>   (optional — defaults to user.default_org_id)
X-Workspace-Id:  <ws_…>    (optional — defaults to user.default_workspace_id)
```

Flow (per request):
1. `HTTPBearer` extracts the token.
2. `decode_supabase_token()` (`app/common/auth/supabase.py`) — HS256 verify with `SUPABASE_JWT_SECRET`, check `exp` / `iss=<SUPABASE_URL>/auth/v1` / `aud=authenticated`.
3. `get_user_context()` (`app/common/auth/auth.py`):
   - `UserService.get_or_create_user(auth_sub, email)` — auto-provisions a `User` row (keyed by `auth_sub` — the Supabase `auth.users.id` UUID), a "Personal" `Organization`, an owner `OrgMembership`, a "Default" `Workspace`, and (when Stripe is configured) a Stripe customer + free-tier `Subscription` on first sign-in.
   - Resolves active org (`X-Org-Id` header or `user.default_org_id`) and verifies an active membership exists.
   - Resolves active workspace (`X-Workspace-Id` header or `user.default_workspace_id`) and verifies it belongs to the active org.
   - Returns `UserContext { actor_id, user_id, email, organization_id, workspace_id, role }`.
4. `require_role("owner", "admin")` — RBAC gate factory used on org settings, member management, workspace mutations, and billing writes.

Tenancy model:

| Entity        | Prefix      | Role                                                                                       |
| ------------- | ----------- | ------------------------------------------------------------------------------------------ |
| User          | `user_*`    | Supabase-backed identity. `auth_sub` (= Supabase `auth.users.id`) is the unique key; auto-provisioned on first JWT. |
| Organization  | `org_*`     | Billing boundary. Holds a Stripe customer via the `Subscription` row.                      |
| OrgMembership | `om_*`      | `(user_id, org_id, role)`. Role ∈ `owner` / `admin` / `member`. `user_id` is NULL for pending email invites until that user signs up. |
| Workspace     | `ws_*`      | Top-level grouping inside an Org. The per-request tenancy unit. Slugs unique per org.      |
| Project       | `prj_*`     | A video project (existing entity). Carries `org_id` + `workspace_id` (nullable while the legacy routes are migrated). |

No backend endpoints exist for login / signup / reset — those live in Supabase Auth (frontend).

### Domain — projects, scenes, sources, targets, workflows, executions

A **Project** owns an ordered list of **Scenes** plus optional **Sources** (input material — YouTube / article / web URL feeding the analyzer) and **Targets** (output destinations — platform + format). A **Scene** carries the brief, the generated Manim code, the rendered clip URL, status, and render method. There is no `(template_id, params)` model — scenes are produced by Claude codegen, not a parametric template catalog.

A **Workflow** is a user-defined DAG (`workflow_node_type`, `workflow_node_instance`, `workflow_node_prop`, `workflow_edge_instance`) — a configurable pipeline graph. A **WorkflowExecution** is one run of that pipeline, with `kind ∈ {GENERATE, REGENERATE, ANALYZE}`, status, and the `temporal_workflow_id` + `temporal_run_id` for correlation with Temporal UI/replay. Each execution has child `execution_phase` rows (phase-level progress) and `execution_log` rows (line-level logs) — these are what the frontend polls to render progress.

The product thesis is still **atomic re-renders** (one scene change ≠ whole-video re-render) and **per-clip granularity**. Push back on designs that force full re-encodes for single-scene edits.

The operations the API exists for (today):
1. **Create from source** — `POST /projects/from-source` → kicks an `analyze` workflow (fetch transcript / extract frames / describe).
2. **Generate** — `POST /projects/{id}/generate` → kicks `generate` workflows (plan clips → fan-out per-clip Manim render → FFmpeg concat).
3. **Regenerate one scene** — `POST /scenes/{id}/regenerate` → kicks a `regenerate` workflow for just that scene.
4. **Preview / Export** — `POST /projects/{id}/preview` and `POST /projects/{id}/export` (currently stubbed — see "Known stubs").
5. **Poll** — `GET /executions/{id}` for status, phases, logs. (Legacy `/jobs/{id}` is gone; `Tags.Job` is kept as the OpenAPI group label only.)

### Render/export pipeline — Temporal workflows

Long-running endpoints return `202` with a `WorkflowExecutionResponse` (or a list of them for `POST /projects/{id}/generate`). Each kicks a **Temporal workflow** that orchestrates the real work and updates `workflow_execution` + `execution_phase` + `execution_log` as it progresses; the frontend polls `GET /executions/{id}`.

- **Workflows** (`app/workers/workflows/`) are deterministic orchestrators — they may not do IO. They compose activities and use `asyncio.gather` for parallel fan-out (e.g. rendering N clips in parallel).
  - `generate_workflow.py` — plan_clips → create_scenes → fan-out generate_clip (parallel) → ffmpeg_concat → update_project.
  - `regenerate_workflow.py` — re-render a single scene.
  - `analyze_workflow.py` — fetch transcript, extract frames, describe the source.
- **Activities** (`app/workers/activities/`) are where the real work happens. Each declares retry policy + timeouts via the workflow's `execute_activity` call.
  - `plan_activity.py` — Claude splits the brief into N per-clip briefs.
  - `project_activity.py` — `CreateScenesInput`, `UpdateProjectInput` DB writes.
  - `generate_clip_activity.py` — orchestrates manim_render (with the 4-attempt Claude-fallback + vision eval chain) → ffmpeg encode.
  - `ffmpeg_concat_activity.py` — stitch clips into the final MP4.
  - `analyze_activity.py` — transcription + frame extraction.
  - `db_activity.py` — update `WorkflowExecution` status / phases / logs.
- **Client** (`app/workers/client.py`) connects to either local Temporal dev server (default — runs in docker-compose on `:7233`, UI on `:8233`) or Temporal Cloud, selected at runtime.
- **Worker entrypoint** (`app/workers/worker.py`): `make worker` for local, `make worker-cloud` (sets `TEMPORAL_PROFILE=cloud`) for Cloud.

### Temporal connection modes (local + cloud, same code)

Two config sources, picked at runtime by `app/workers/client.py`:

1. **Profile mode (preferred for local dev)** — install Temporal CLI (`brew install temporal`), then:
   ```bash
   temporal --profile cloud config set --prop address   --value '<ns>.<account>.tmprl.cloud:7233'
   temporal --profile cloud config set --prop namespace --value '<namespace>'
   temporal --profile cloud config set --prop api_key   --value '<paste — NEVER in chat or commits>'
   ```
   Profiles live in `~/Library/Application Support/temporalio/temporal.toml` (macOS). Run with `TEMPORAL_PROFILE=cloud make worker`. Keeps API keys out of `.env*`.

2. **Env-var fallback (Docker / CI)** — `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`. Setting `TEMPORAL_API_KEY` auto-enables TLS + Cloud connect. `docker-compose.yml` runs a local Temporal dev server (`temporalio/temporal:latest server start-dev`) on `:7233` with UI on `:8233`.

### Manim codegen — services + utility library

The render pipeline is Claude-driven codegen, not a template catalog. The flow for one clip:

```
clip_planner_service   → splits the user brief into per-clip briefs
prompt_builder_service → composes the Claude prompt (brief + style + Manim utility surface)
script_generator_service → asks Claude for the Manim Python source
manim_render_service   → runs Manim; on failure or low-quality frame:
   ├─ validator_service  (static checks on the generated code)
   ├─ evaluator_service  (vision eval of rendered frames)
   └─ describer_service  (describes the rendered output for fallback prompting)
   ↻ up to 4 attempts with Claude rewriting on failure
ffmpeg_concat_service → stitches the clips into the final MP4
```

Supporting input services: `article_scraper_service`, `youtube_fetcher_service` (stubbed), `transcript_service`, `source_fetcher_service`, `frame_extractor_service`, `source_service`.

`app/manim_pipeline/` is the **utility library** Claude's generated code imports from — reusable Manim patterns that keep generated scripts short and predictable:

- `diagram_patterns.py`, `math_animations.py`, `ml_visuals.py`, `plot_patterns.py` — composable scene building blocks.
- `visual_effects.py`, `styles.py` — visual conventions (colors, easing, fade conventions).
- `voices.py` — voice catalog used by `voice_api.py` / `voices_service.py`.
- `_references/` — reference scripts kept for prompt grounding.

When iterating on render quality, the levers are: the prompt (`prompt_builder_service`), the utility surface (`app/manim_pipeline/`), and the fallback chain (`manim_render_service` + `validator`/`evaluator`/`describer`). There is no template registry to flip.

### Billing — Stripe-backed, per-org

Billing is per-Organization (not per-user). One `Subscription` row per org carries the Stripe `customer_id` + `subscription_id`, current `plan` / `status`, `seat_count`, and period dates. Webhook events are deduped by `stripe_event_id` and persisted to `billing_event` for audit.

| Route                   | Role          | Purpose                                          |
| ----------------------- | ------------- | ------------------------------------------------ |
| `GET  /billing`         | owner / admin | Current plan + subscription state                |
| `POST /billing/checkout`| owner         | Stripe Checkout session URL (upgrade)            |
| `POST /billing/portal`  | owner         | Stripe Customer Portal session URL               |
| `GET  /billing/invoices`| member        | Recent invoices via Stripe                       |
| `GET  /billing/usage`   | member        | Current resource counts vs `PlanLimits`          |
| `POST /webhooks/stripe` | **no JWT**    | Mounted at root; verifies via `Stripe-Signature` |

Plan tiers (`app/common/billing/plan_limits.py`): `free` / `pro` / `enterprise`. `PlanEnforcer` (`app/common/billing/plan_enforcement.py`) raises `PlanLimitExceededError` (HTTP 402) when limits are hit — called from `OrgMembershipService.invite_member` and `WorkspaceService.create_workspace`. **Enforcement is gated on `settings.stripe_secret_key`** so dev / test environments without Stripe stay limit-free. Webhook handler updates `Subscription` + denormalized `Organization.plan` on `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.

### Settings

`app/settings.py` (pydantic-settings) auto-loads `.env.local` on macOS, `.env.dev` elsewhere. Exposes `async_database_url` (SQLAlchemy + asyncpg — points at the Supabase transaction pooler when `DATABASE_URL` is set), `asyncpg_dsn` (workers / bulk), `sync_database_url` (Alembic — uses `DATABASE_URL_DIRECT` if set so DDL bypasses PgBouncer), `supabase_issuer` (derived from `SUPABASE_URL`). Auth + Stripe env vars: `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_ENTERPRISE`. See `.env.example` for the full surface.

### Out-of-MVP — do not build

- User-written Manim code (no sandbox runner, no arbitrary-Python endpoints)
- Keyframe animation
- Multi-user collaboration
- Mobile app

## Repo layout

```
app/
├── main.py                       FastAPI app, CORS, lifespan, router mounting
├── settings.py                   pydantic-settings, env-file detection
├── api/
│   ├── router.py                 /api prefix
│   ├── tags.py                   Tags enum for OpenAPI grouping (Health/Me/Organization/Workspace/Billing/Project/Scene/Job/Export/Workflow/Source/Target/Voice)
│   └── v1/
│       ├── router.py             /v1 prefix, includes all controllers
│       ├── controller/           HTTP handlers — no business logic
│       │   ├── health_api.py            /health, /ready
│       │   ├── user_api.py              /me, /me/context
│       │   ├── organization_api.py      /organization[, /{id}, /{id}/members, /{id}/members/invite]
│       │   ├── workspace_api.py         /workspace[, /{id}]
│       │   ├── billing_api.py           /billing[, /checkout, /portal, /invoices, /usage]
│       │   ├── billing_webhook_api.py   /webhooks/stripe  ← mounted at root, no JWT
│       │   ├── project_api.py           /projects[, /from-source, /{id}/generate, /{id}/preview]
│       │   ├── scene_api.py             /scenes/{id}[, /preview, /regenerate]; /projects/{id}/scenes
│       │   ├── workflow_api.py          workflow DAG CRUD
│       │   ├── executions_api.py        /executions/{id}  ← polling endpoint (replaces /jobs/{id})
│       │   ├── export_api.py            /projects/{id}/preview, /projects/{id}/export  ← stubbed
│       │   ├── source_api.py            /sources[, /{id}/sync]
│       │   ├── target_api.py            /targets
│       │   └── voice_api.py             /voices, /voices/accents
│       ├── request/              Pydantic input schemas
│       └── response/             Pydantic output schemas + base_response envelope
├── common/
│   ├── auth/                     Supabase JWT + UserContext + require_role
│   │   ├── supabase.py           JWT decode (HS256 + project JWT secret)
│   │   └── auth.py               UserContext, get_user_context, require_role
│   ├── billing/                  Stripe client + plan limits + enforcement
│   │   ├── stripe_client.py
│   │   ├── plan_limits.py        PlanLimits dataclass + FREE/PRO/ENTERPRISE
│   │   └── plan_enforcement.py   PlanEnforcer (no-op until stripe_secret_key set)
│   ├── exceptions.py             register_exception_handlers + typed HTTPExceptions (incl. PlanLimitExceededError)
│   ├── pagination.py             PaginationParams + PaginatedResponse
│   └── enum/                     execution / scene / source / target / org / workflow / workflow_node
├── db/
│   ├── base.py                   DeclarativeBase
│   ├── engine.py                 cached async engine + session factory
│   ├── session.py                get_db FastAPI dep — commits on success
│   └── repository/               one repository class per model; queries live here
├── model/                        SQLAlchemy 2.0 ORM models
│   ├── user_model.py / credential_model.py
│   ├── organization_model.py / org_membership_model.py / workspace_model.py
│   ├── subscription_model.py / billing_event_model.py
│   ├── project_model.py / scene_model.py
│   ├── source_model.py / source_video_model.py / target_model.py
│   ├── workflow_model.py / workflow_node_type_model.py / workflow_node_instance_model.py
│   ├── workflow_node_prop_model.py / workflow_edge_instance_model.py
│   └── workflow_execution_model.py / execution_phase_model.py / execution_log_model.py
├── service/                      business logic
│   ├── user_service / organization_service / org_membership_service / workspace_service
│   ├── billing_service           Stripe customer / checkout / portal / webhook
│   ├── project_service / scene_service / source_service / target_service
│   ├── workflow_service / workflow_execution_service
│   ├── clip_planner_service / prompt_builder_service / script_generator_service
│   ├── manim_render_service / ffmpeg_concat_service
│   ├── validator_service / evaluator_service / describer_service
│   ├── article_scraper_service / youtube_fetcher_service / source_fetcher_service
│   ├── transcript_service / frame_extractor_service / voices_service
│   └── export_service  ← stub (pending task 12)
├── manim_pipeline/               Manim utility library imported by Claude-generated scripts
│   ├── diagram_patterns.py / math_animations.py / ml_visuals.py / plot_patterns.py
│   ├── visual_effects.py / styles.py / voices.py
│   └── _references/              reference scripts for prompt grounding
├── workers/                      Temporal workflows + activities
│   ├── client.py                 client factory — local dev server OR Temporal Cloud
│   ├── worker.py                 entrypoint (`make worker` / `make worker-cloud`)
│   ├── workflows/                generate / regenerate / analyze (deterministic — no IO)
│   └── activities/               plan / project / generate_clip / ffmpeg_concat / analyze / db
└── middleware/
alembic/                          env.py imports every model in app/model
tests/                            pytest-asyncio, SQLite in-memory, AsyncClient fixture
sql/  docs/  scripts/  infra/     placeholders for ops/docs/data assets
```

## Conventions

- **Repository pattern is strict.** Controllers get a service; services get one or more repositories. No SQLAlchemy queries outside `app/db/repository/`.
- **IDs are prefixed UUIDs**, set via `default=generate_prefixed_uuid` on each model. Current prefixes: `user_` (user), `org_` (organization), `om_` (org_membership), `ws_` (workspace), `sub_` (subscription), `be_` (billing_event), `prj_` (project / video), `scn_` (scene), `src_` (source), `srcv_` (source_video), `tgt_` (target), `cred_` (credential), `workflow_` (workflow), `node_` (workflow_node_type), `wni_` (workflow_node_instance), `nprop_` (workflow_node_prop), `we_` (workflow_edge_instance), `execution_` (workflow_execution), `phase_` (execution_phase), `execlog_` (execution_log).
- **Auth is opt-in per route.** New tenancy / billing routes use `Depends(get_user_context)` (+ `require_role(...)` where applicable). Existing video / scene / workflow routes still fall back to `settings.default_user_id` until they're migrated — when adding new code paths, prefer `UserContext` from the start.
- **Async everywhere on the request path.** Sync only inside Temporal activities that wrap blocking IO (Manim subprocess via `asyncio.to_thread`) and Alembic.
- **Standard envelope on every endpoint** — never return a bare model.
- **Execution-shaped responses for anything that renders.** Return `202 + WorkflowExecutionResponse` (or `list[WorkflowExecutionResponse]` for fan-out) immediately; the frontend polls `GET /executions/{id}`.
- Line length 100; ruff + black + isort with the configs in `pyproject.toml`.
