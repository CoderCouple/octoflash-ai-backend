# Octoflash AI — Backend

FastAPI service for **Octoflash AI**, a scene-first AI video editor for Manim animations. Users describe what they want; the system produces a video by stitching together independently-rendered Manim scenes. Editing one scene re-renders only that scene — never the whole video.

The frontend is a sibling Vite + React monorepo: [`CoderCouple/octoflash-ai-frontend`](https://github.com/CoderCouple/octoflash-ai-frontend) (defaults to `http://localhost:8000` for this service in dev).

---

## Quick start (laptop dev)

```bash
git clone https://github.com/CoderCouple/octoflash-ai-backend.git
cd octoflash-ai-backend
make setup        # one-shot: brew deps + poetry + DB + sandbox + frontend
make dev          # uvicorn on :8000
```

`make setup` is idempotent and prints a status table at the end. See `scripts/setup-local.sh` for what it touches.

For the **/playground** endpoint (Manim sandbox), see [Playground modes](#playground-modes) below.

Swagger UI: `http://localhost:8000/docs`.

---

## Stack

| Layer | Choice |
| ----- | ------ |
| API framework | FastAPI · Pydantic v2 |
| Async runtime | `uvicorn`, `asyncio` |
| Database | Postgres via async SQLAlchemy 2.0 + asyncpg; Alembic migrations |
| Auth | AWS Cognito Hosted UI (JWT verification only on the backend) |
| Multi-tenancy | Organization → Workspace → Project (video) with `X-Org-Id` / `X-Workspace-Id` headers |
| Billing | Stripe (per-org Subscription, webhook-driven, with `BillingEvent` audit) |
| Workflows | Temporal — durable workflow runner for analyze / generate / regenerate |
| Render pipeline | Claude-codegen Manim → subprocess → FFmpeg concat; 4-attempt fallback chain with `validator` / `evaluator` / `describer` services |
| Voiceover | ElevenLabs via `manim-voiceover` (inside the Manim subprocess) |
| Transcripts | Whisper (`faster-whisper`, `large-v3`) |
| Playground | ManimGL inside a hardened Docker container (`infra/playground-runner/`) |
| Object storage | S3 (renders / exports) via `aioboto3` |
| Secrets at rest | AWS Secrets Manager (managed) + Fernet (`cryptography`) for the user-facing credentials vault |
| Tooling | Poetry · ruff · black · isort · mypy · pre-commit · pytest |
| Python | 3.11 |

See [`CLAUDE.md`](./CLAUDE.md) for the deeper architecture write-up — request flow, tenancy model, render pipeline, Temporal worker, sandbox security boundary.

---

## Make targets

```bash
make help            # full list
```

| Target | What it does |
| ------ | ------------ |
| `setup` | One-shot local environment (brew deps + poetry + DB + sandbox image + frontend) |
| `install` | `poetry install` (main + dev) |
| `install-playground` | Adds `manimgl` to the Poetry env (for `PLAYGROUND_SANDBOX_MODE=local`) |
| `dev` | `uvicorn --reload` on `:8000` (reload scoped to `app/` + `alembic/`) |
| `worker` | Local Temporal worker |
| `worker-cloud` | Worker against Temporal Cloud (`TEMPORAL_PROFILE=cloud`) |
| `migrate` | `alembic upgrade head` |
| `migration MSG="..."` | autogenerate a new Alembic revision |
| `test` / `lint` / `format` | `pytest` / `ruff + mypy` / `black + isort + ruff --fix` |
| `docker-up` / `docker-db` | Compose stack (db + redis + pgadmin + temporal) / just Postgres |
| `playground-image` | Build the ManimGL sandbox Docker image (`docker build infra/playground-runner`) |
| `preview T=<id>` | Locally preview one Manim template (no API / Temporal / DB) |

---

## Project layout

```
app/
├── main.py                       FastAPI entrypoint
├── settings.py                   pydantic-settings (env-driven config)
├── api/
│   ├── router.py                 /api prefix
│   └── v1/
│       ├── router.py             /v1 prefix
│       ├── controller/           HTTP handlers — no business logic
│       ├── request/              Pydantic input schemas
│       └── response/             Pydantic output schemas + BaseResponse envelope
├── common/
│   ├── auth/                     Cognito JWT + UserContext + require_role
│   ├── billing/                  Stripe client + plan limits + enforcement
│   ├── security/                 Fernet wrappers for the credentials vault
│   ├── exceptions.py             register_exception_handlers + typed HTTPExceptions
│   ├── pagination.py
│   └── enum/                     execution / scene / source / target / org / workflow
├── db/
│   ├── base.py / engine.py / session.py
│   └── repository/               one repository per model — only place SQLAlchemy queries live
├── model/                        SQLAlchemy ORM models
├── service/                      business logic (Manim codegen, Stripe, auth provisioning, …)
├── manim_pipeline/               Utility library Claude-generated Manim code imports from
├── workers/
│   ├── client.py / worker.py     Temporal client + worker entrypoint
│   ├── workflows/                deterministic orchestrators (analyze / generate / regenerate)
│   └── activities/               side-effectful work (Manim render, FFmpeg concat, S3 upload, …)
└── middleware/
alembic/                          env.py imports every model so autogenerate sees them
infra/                            CloudFormation stacks for AWS deployment + sandbox runner
scripts/                          setup-local.sh, preview_template.py, smoke tests
sql/                              canonical SQL schema (mirror of alembic head)
tests/                            pytest-asyncio
```

---

## Playground modes

The `/api/v1/playground/render` endpoint runs **user-supplied** ManimGL code. It's the only place in the system that executes untrusted Python. Two execution modes, picked by `PLAYGROUND_SANDBOX_MODE` in `.env.local`:

| Mode | What runs | Use case |
| ---- | --------- | -------- |
| `docker` (default) | ManimGL inside a hardened Docker container — `--network=none`, non-root, capped RAM/CPU, only the per-render dir mounted RW, EGL-headless GL | Production / shared deploys |
| `local` | `manimgl` directly on the host (Poetry env) | Laptop dev only — **no isolation**, never enable in production |

Build the sandbox image once: `make playground-image`. See [`infra/playground-runner/README.md`](./infra/playground-runner/README.md) for the security model.

---

## AWS deployment

Octoflash deploys to AWS in `us-west-2`, sharing foundation infrastructure (VPC, ECS cluster, RDS, SES + SQS email pipeline) with the sibling Octopod project — Octoflash uses its own Postgres database (`octoflash_db`) on the shared RDS instance, its own Cognito user pool, its own Stripe account, its own ECR repo, and its own ECS service + ALB.

```bash
bash infra/deploy.sh preflight    # verify shared stacks + secrets exist
bash infra/deploy.sh secrets      # cognito + stripe + oauth + temporal
bash infra/deploy.sh build        # ECR + CodeBuild + first build
bash infra/deploy.sh services     # ECS service (with Temporal worker sidecar)
bash infra/deploy.sh pipelines    # CodePipeline auto-deploy on push to main
bash infra/deploy.sh dns          # Route 53 records
```

Manual setup before `preflight` will pass: see [`infra/PREFLIGHT.md`](./infra/PREFLIGHT.md) — six one-shot steps (hosted zone, PAT, octoflash_db creation, etc.).

The Temporal worker runs as an `Essential: false` sidecar in the same ECS task as the API, sharing the task's Environment + Secrets via YAML anchors. If the worker crashes ECS restarts only the worker — Temporal retries any in-flight activities.

---

## Configuration

`app/settings.py` (pydantic-settings) reads from `.env.local` on macOS and falls through to process env on Linux (ECS injects everything via the task definition). Surface area:

| Group | Keys |
| ----- | ---- |
| App | `APP_NAME`, `ENVIRONMENT`, `DEBUG`, `HOST`, `PORT`, `API_PREFIX`, `ALLOWED_ORIGINS` |
| Database | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `DB_SSL_REQUIRE`, `DATABASE_URL` (override) |
| Cognito | `COGNITO_USER_POOL_ID`, `COGNITO_REGION`, `COGNITO_APP_CLIENT_ID` |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_ENTERPRISE` |
| Temporal | `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`, `TEMPORAL_TASK_QUEUE`, `TEMPORAL_PROFILE` |
| Anthropic / ElevenLabs | `ANTHROPIC_API_KEY`, `PLANNER_MODEL`, `SCRIPT_MODEL`, `ELEVEN_API_KEY` |
| Playground | `PLAYGROUND_SANDBOX_MODE`, `PLAYGROUND_DOCKER_IMAGE`, `PLAYGROUND_LOCAL_BIN`, `PLAYGROUND_TIMEOUT_SECONDS`, `PLAYGROUND_MEMORY_LIMIT`, `PLAYGROUND_CPU_LIMIT`, `PLAYGROUND_PIDS_LIMIT` |
| AWS / S3 | `AWS_REGION`, `S3_BUCKET_RENDERS`, `S3_BUCKET_EXPORTS`, `S3_PUBLIC_BASE_URL` |
| Manim | `MANIM_QUALITY_PREVIEW`, `MANIM_QUALITY_EXPORT`, `MANIM_OUTPUT_DIR` |
| Whisper | `WHISPER_MODEL` |
| Credentials vault | `CREDENTIAL_ENCRYPTION_KEY` (Fernet) |

Empty / missing → safe defaults. The app boots cleanly even when most third-party keys aren't set; the corresponding features just return `501` or skip gracefully.

---

## Conventions

- **Repository pattern is strict.** Controllers get services; services get repositories. SQLAlchemy queries live only in `app/db/repository/`.
- **Async on the request path.** Sync only inside Temporal activities that wrap blocking IO (Manim subprocess via `asyncio.to_thread`) and inside Alembic.
- **`BaseResponse[T]` envelope on every endpoint** — never return a bare model. Errors flow through `register_exception_handlers`.
- **Execution-shaped responses for long-running ops** — return `202 + WorkflowExecutionResponse`; the frontend polls `GET /executions/{id}`.
- **Prefixed UUID IDs**: `user_`, `org_`, `om_`, `ws_`, `sub_`, `be_`, `prj_`, `scn_`, `src_`, `srcv_`, `tgt_`, `cred_`, `workflow_`, `node_`, `wni_`, `nprop_`, `we_`, `execution_`, `phase_`, `execlog_`.
- **Line length 100**, ruff + black + isort configured via `pyproject.toml`.

---

## Repos

- Backend: <https://github.com/CoderCouple/octoflash-ai-backend>
- Frontend: <https://github.com/CoderCouple/octoflash-ai-frontend>
