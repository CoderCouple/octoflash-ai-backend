# Octoflash AI — Backend

FastAPI service for **Octoflash AI**, a scene-first AI video editor for Manim animations.
A project is a DAG of scenes; each scene is its own Manim render. Editing one scene
re-renders only that scene — never the whole video. Multiple parallel branches let a
single project produce several cuts (editorial / manic / shorts) from the same scenes.

Repo: <https://github.com/CoderCouple/octoflash-ai>

The frontend is a sibling Vite + React monorepo (`octoflash-ai-frontend`) being migrated
from Next.js. Its typed API client defaults to `http://localhost:8000`, which is what
this service binds in dev.

## Stack

FastAPI · async SQLAlchemy 2.0 + asyncpg · Alembic · Postgres · Redis + RQ workers ·
Manim Community 0.18 · FFmpeg · Whisper v3 · Anthropic Claude Sonnet 4.5 (planner) ·
S3 (renders/exports) · Poetry · Python 3.11.

## Run it locally

```bash
poetry install
cp .env.example .env.local        # tweak DB / API keys
make docker-db                    # bring up Postgres + pgAdmin
make migrate                      # apply Alembic migrations
make dev                          # uvicorn on :8000
make worker                       # in a separate shell: RQ render worker
```

Open `http://localhost:8000/docs` for the auto-generated Swagger UI.

> **Cold-start note:** the schema is managed by Alembic only — there is no
> `sql/schema.sql` seed mounted into the Postgres container. Run `make migrate`
> after `make docker-db` before hitting any persisted endpoint. (Octopod-style
> `schema.sql` seed-on-init is an opt-in if you'd rather skip Alembic on cold start.)

## Make targets

| Command              | What it does                                  |
| -------------------- | --------------------------------------------- |
| `make dev`           | `uvicorn --reload` on `:8000`                 |
| `make run`           | production uvicorn (no reload)                |
| `make worker`        | RQ worker on the `render` queue               |
| `make test`          | `pytest -v`                                   |
| `make lint`          | ruff + mypy                                   |
| `make format`        | black + isort + ruff --fix                    |
| `make migrate`       | `alembic upgrade head`                        |
| `make migration MSG="..."` | autogenerate a new revision             |
| `make docker-up`     | web + worker + Postgres + Redis + pgAdmin     |
| `make docker-db`     | just Postgres + pgAdmin                       |

## Architecture

See [CLAUDE.md](./CLAUDE.md) for the layered architecture (controller → service →
repository → model), DAG mental model, render-pipeline flow, template system, and
out-of-MVP boundaries. CLAUDE.md is the source of truth — keep it current as the
shape evolves.

  Want me to:
  - (a) Wire the remaining 16 text-titles primitives so the whole text_titles category renders for real
  - (b) Move to a different category (charts, emphasis)
  - (c) Wire the preview/export concat workflow so multi-scene videos work
  - (d) Wire the planner (Anthropic) so /instruct and /projects/{id}/scenes from a prompt work
  - (e) Pause here — celebrate, ship, then pick next

  What I won't do this round                                                                                                                                                                           
                                                                
  - Audio (no primitive emits audio; not a regression)                                                                                                                                                 
  - Render quality tuning beyond Manim defaults                 
  - New params on primitives (sticking to existing CONFIG_SCHEMAs)                                                                                                                                     
  - High-quality / 1080p / 4K renders (the export workflow already supports this; we test at preview quality)    