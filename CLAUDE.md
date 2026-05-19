# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Backend for **Octoflash AI** — a scene-first, AI-driven video editor for Manim animations. Users describe what they want; the system produces a video by stitching together independently-rendered Manim scenes. Each scene is its own Manim render, so editing one scene only re-renders that scene — never the whole video.

The frontend lives in a sibling repo `octoflash-ai-frontend/` (in-progress migration from Next.js 15 to a Vite + React monorepo: `packages/core` shared TS, `packages/web` Vite SPA, `packages/desktop` Electron wrapper). Its typed API client defaults to **`http://localhost:8000`** — this service should bind to `:8000` in dev.

## Project state

Skeleton + domain stubs. The directory tree, configs, foundational code (settings, DB engine/session, exception envelope, base response, alembic env), and all 8 controllers / 6 SQLAlchemy models / 5 repositories / 8 services are in place. Bodies that touch external systems (Manim render, FFmpeg concat, Whisper transcribe, Anthropic planner, S3 upload, RQ enqueue) `raise NotImplementedError` — fill them in per feature.

Layout and conventions are deliberately mirrored from the `octopod-backend` repo (FastAPI + async SQLAlchemy 2.0 + asyncpg + Alembic + Poetry + ruff/black/isort/mypy + pre-commit).

## Common commands

```bash
make install            # poetry install
make dev                # uvicorn --reload on :8000
make worker             # RQ render worker
make test               # pytest -v
make lint               # ruff + mypy
make format             # black + isort + ruff --fix
make migrate            # alembic upgrade head
make migration MSG="..." # alembic revision --autogenerate
make docker-up          # web + worker + db + redis + pgadmin
make docker-db          # just db + pgadmin
```

Heavy native deps (Manim → Cairo/Pango/FFmpeg, Whisper → libsndfile) are wired in the Dockerfile. Local dev needs them via brew/apt; see `Dockerfile` for the exact list.

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

### Domain — the DAG mental model (read before designing endpoints)

A project is a DAG of nodes: `start`, `scene`, `branch`, `merge` (post-MVP), `end`. Stitching is FFmpeg concat of the selected variation per scene along a path to an end. A project can have multiple ends. The whole product thesis is **atomic re-renders** (one scene change ≠ whole-video re-render) and **parallel branches** (one project → multiple cuts like editorial / manic / shorts). Push back on designs that force full re-encodes for single-scene edits.

The five operations the API exists for:
1. **Generate variations** — `POST /scenes/{id}/variations` → job
2. **Re-render** — `POST /variations/{id}/render` → job
3. **Replace** — user-uploaded clip swaps in for a scene (TODO endpoint)
4. **Keep timing** — `duration` on scene, locked when set
5. **Re-run path** — re-render scenes along one branch (TODO endpoint)

### Render/export pipeline — Temporal workflows

`POST /scenes/{id}/variations`, `POST /projects/{id}/preview`, `POST /projects/{id}/export` all return `202` with a Job id. Each starts a **Temporal workflow** that orchestrates the real work and updates the Job row as it progresses; the frontend polls `GET /jobs/{id}`.

- **Workflows** (`app/workers/workflows/`) are deterministic orchestrators — they may not do IO. They compose activities and use `asyncio.gather` for parallel fan-out (e.g. rendering N variations in parallel).
- **Activities** (`app/workers/activities/`) are where the real work happens: Manim render, FFmpeg concat, Whisper transcribe, S3 upload, DB writes. Each has retry policy + timeouts declared via `@activity.defn` and the workflow's `execute_activity` call.
- **Client** (`app/workers/client.py`) connects to either local Temporal dev server (default — runs in docker-compose) or Temporal Cloud, selected at runtime.
- **Worker entrypoint** (`app/workers/worker.py`): `make worker` for local, `make worker-cloud` (sets `TEMPORAL_PROFILE=cloud`) for Cloud.
- **Job table** carries `workflow_id` + `run_id` so `GET /jobs/{id}` can correlate with Temporal's UI / replay.

Services that touch the workflow runner: `ManimRunnerService` (called from `render_variation_activity`), `FFmpegConcatService` (called from `concat_clips_activity`), `WhisperRunnerService` (called from `transcribe_audio_activity`), `StorageService` (called from `upload_render_activity`), `PlannerService` (called from request handlers — not workflows — for sync NL operations).

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

### NL scene editing (Hybrid B)

A scene starts as `(template_id, params)` — structured. Users can also issue natural-language edits via `POST /scenes/{id}/instruct` ("shift the title up", "add a chart at 2s") which go to Claude and produce per-scene `extra_steps` divergence from the template baseline. Two-step by design: `/instruct` updates the spec synchronously but does NOT render; user calls `/scenes/{id}/variations` separately when ready.

Data model additions:
- `Scene.extra_steps: jsonb list[StepSpec]` — empty for structured-mode scenes; populated by NL edits.
- `Scene.mode: "structured" | "advanced"` — `advanced` iff `extra_steps` is non-empty.
- `scene_instruction` table — append-only audit of every NL instruction + before/after diff + LLM reasoning + warnings.

Stacking semantics (Hybrid): instructions append; `POST /scenes/{id}/collapse-instructions` wipes history while preserving the current `extra_steps`; `POST /scenes/{id}/discard-divergence` reverts the scene to pure template baseline.

Template-switch guard: `PATCH /scenes/{id}` rejects template changes when `extra_steps` is non-empty unless `?force=true` (which discards divergence).

Renderer integration: `TemplateRenderer(template_id, params, style, extra_steps=...)` appends `extra_steps` after the template's base steps; style modifier scales the combined list; audit snapshot embeds the merged steps for self-contained replay.

### Templates — config-based, not class-based

**Users never write Manim.** They pick from a **127-template catalog (11 categories)** and tweak params. The system is data-driven end-to-end: a template is a `TemplateDefinition` Pydantic instance (params + steps + style modifiers), and renders are produced by composing reusable **primitives**. There is no per-template Python subclass anywhere.

Layout under `app/templates/`:

| File / dir              | Role                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `schema.py`             | Pydantic models — `TemplateDefinition`, discriminated-union `ParamSpec`, `StepSpec`, `StyleModifier`. |
| `registry.py`           | The catalog (`CATALOG: list[CatalogEntry]`) — 127 entries with id/category/manic flag. Single source of truth for `GET /templates`. |
| `loader.py`             | `load(id) → TemplateDefinition` — lazy `importlib` import of `defs/<id>.py`. Raises `TemplateNotImplementedError` if the def file doesn't exist. |
| `audit.py`              | `template_content_hash()` + `build_render_snapshot()` — provenance recorded on every Variation. |
| `renderer.py`           | `TemplateRenderer.render(scene)` — validates params, resolves `${params.foo}` interpolation, applies the active style modifier, dispatches steps to primitives. Pure logic — no Manim dependency. |
| `primitives/base.py`    | `Primitive` ABC with `PRIMITIVE_ID`, `PRIMITIVE_VERSION`, `CONFIG_SCHEMA`, `build()`. |
| `primitives/registry.py`| `@register` decorator + `PRIMITIVES` dict. Concrete primitives register at import time. |
| `primitives/*.py`       | Concrete primitives (text_reveal, hold, …). Reference impls only — Manim wiring is the next step. |
| `defs/<id>.py`          | One file per template, each exporting `TEMPLATE: TemplateDefinition`. Only `title_reveal.py` exists today. |

**Catalog vs. implementation split:** all 127 templates are in the catalog from day one. `GET /templates` returns them all with an `implemented: bool` flag so the frontend can grey out templates whose `defs/<id>.py` hasn't been written yet. `GET /templates/{id}` 404s on unimplemented templates.

**Audit / replay:** every render's `Variation.params_snapshot` embeds the full resolved `TemplateDefinition` + params + style + per-primitive versions + a sha256 content hash. The snapshot is self-contained — a future worker can replay the exact render even if the def file has since changed. Authors manually bump `TemplateDefinition.version` on intentional behavior changes; the content hash auto-tracks *any* change.

**Adding a new template:** flip its `CatalogEntry` from `False` to `True` in `registry.py` (if needed), create `app/templates/defs/<id>.py` exporting `TEMPLATE = TemplateDefinition(...)`, reuse existing primitives or add a new one under `primitives/`. No dispatch code to touch.

16 of 127 templates are `manic_compatible` (the original 9 + the all-manic Reactions/shorts vernacular category). The Manic preset hardens cuts, scales captions, scales durations, and can append extra steps via `StyleModifier`.

### Settings

`app/settings.py` (pydantic-settings) auto-loads `.env.local` on macOS, `.env.dev` elsewhere. Exposes `async_database_url` (SQLAlchemy + asyncpg), `asyncpg_dsn` (workers / bulk), and `sync_database_url` (Alembic). See `.env.example` for the full surface.

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
│   ├── tags.py                   Tags enum for OpenAPI grouping
│   └── v1/
│       ├── router.py             /v1 prefix, includes all controllers
│       ├── controller/           HTTP handlers — no business logic
│       ├── request/              Pydantic input schemas
│       └── response/             Pydantic output schemas + base_response envelope
├── common/
│   ├── exceptions.py             register_exception_handlers + typed HTTPExceptions
│   ├── pagination.py             PaginationParams + PaginatedResponse
│   └── enum/                     SceneStatus, JobKind/Status, NodeKind/EdgeKind, StylePreset
├── db/
│   ├── base.py                   DeclarativeBase
│   ├── engine.py                 cached async engine + session factory
│   ├── session.py                get_db FastAPI dep — commits on success
│   └── repository/               one repository class per model; queries live here
├── model/                        SQLAlchemy 2.0 ORM models (project/scene/variation/workflow_*/job)
├── service/                      business logic
│   ├── project_service.py        scene_service / variation_service / workflow_service / job_service / export_service / template_service
│   ├── planner_service.py        Claude — prompt → scene plan
│   ├── manim_runner_service.py   template + params → Manim render
│   ├── ffmpeg_concat_service.py  stitch selected variations
│   ├── whisper_runner_service.py
│   └── storage_service.py        S3 via aioboto3
├── templates/                    config-driven template system (see "Templates" section above)
│   ├── schema.py                 TemplateDefinition + ParamSpec union + StepSpec + StyleModifier
│   ├── registry.py               127-entry CATALOG (the surface area)
│   ├── loader.py                 importlib loader for defs/<id>.py
│   ├── audit.py                  content hash + render snapshot
│   ├── renderer.py               TemplateRenderer — dispatches steps to primitives
│   ├── primitives/               reusable animation atoms (text_reveal, hold, …)
│   └── defs/                     one file per template — exports TEMPLATE: TemplateDefinition
├── workers/                      Temporal workflows + activities
│   ├── client.py                 client factory — local dev server OR Temporal Cloud
│   ├── worker.py                 entrypoint (`make worker` / `make worker-cloud`)
│   ├── workflows/                deterministic orchestrators (no IO)
│   └── activities/               side-effectful work (Manim, FFmpeg, Whisper, S3, DB)
└── middleware/
alembic/                          env.py imports every model in app/model
tests/                            pytest-asyncio, SQLite in-memory, AsyncClient fixture
sql/  docs/  scripts/  infra/     placeholders for ops/docs/data assets
```

## Conventions

- **Repository pattern is strict.** Controllers get a service; services get one or more repositories. No SQLAlchemy queries outside `app/db/repository/`.
- **IDs are prefixed UUIDs.** `prj_…`, `scn_…`, `var_…`, `job_…`, `wn_…`, `we_…` — set via `default=generate_prefixed_uuid` on each model.
- **Async everywhere on the request path.** Sync only inside worker entrypoints (Manim, Whisper) and Alembic.
- **Standard envelope on every endpoint** — never return a bare model.
- **Job-shaped responses for anything that renders.** Return `202 + Job` immediately; the frontend polls `/jobs/{id}`.
- Line length 100; ruff + black + isort with the configs in `pyproject.toml`.
