#!/usr/bin/env bash
# Octoflash · one-shot local environment setup.
#
# Idempotent. Verbose tool output is captured to .octoflash-setup.log; the
# terminal stays clean. On any failure, the tail of the log is printed and
# the script suggests the next action — it never silently half-succeeds.
#
# Usage:
#   bash scripts/setup-local.sh
#   make setup        # equivalent

set -uo pipefail

# ── Working directory ────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="$ROOT/.octoflash-setup.log"
: > "$LOG"

OS="$(uname -s)"
case "$OS" in
  Darwin) PLATFORM=macOS ;;
  Linux)  PLATFORM=Linux ;;
  *)      PLATFORM="$OS" ;;
esac
ARCH="$(uname -m)"

# ── Colours ──────────────────────────────────────────────────────────────
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  C_BOLD=$(tput bold); C_DIM=$(tput dim); C_RESET=$(tput sgr0)
  C_GREEN=$(tput setaf 2); C_YELLOW=$(tput setaf 3); C_RED=$(tput setaf 1); C_BLUE=$(tput setaf 4); C_CYAN=$(tput setaf 6)
else
  C_BOLD=""; C_DIM=""; C_RESET=""
  C_GREEN=""; C_YELLOW=""; C_RED=""; C_BLUE=""; C_CYAN=""
fi

LINE="────────────────────────────────────────────────────────────────────────"
THICK="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Per-step status tracking for the final summary ───────────────────────
STATUS_KEYS=()
STATUS_VALUES=()
STATUS_NOTES=()

record() {                # record "Component" "READY|SKIPPED|FAILED" "note"
  STATUS_KEYS+=("$1")
  STATUS_VALUES+=("$2")
  STATUS_NOTES+=("$3")
}

# ── Output helpers ───────────────────────────────────────────────────────
header() {                # header "Title"
  printf "\n${C_BOLD}%s${C_RESET}\n" "$THICK"
  printf "${C_BOLD}  %s${C_RESET}\n" "$1"
  printf "${C_BOLD}%s${C_RESET}\n\n" "$THICK"
}
section() {               # section "[1/7] Title"
  printf "\n${C_BOLD}${C_BLUE}%s${C_RESET}\n" "$1"
}
item_ok()    { printf "  ${C_GREEN}✓${C_RESET} %-30s ${C_DIM}%s${C_RESET}\n" "$1" "${2-}"; }
item_skip()  { printf "  ${C_YELLOW}∙${C_RESET} %-30s ${C_DIM}%s${C_RESET}\n" "$1" "${2-}"; }
item_warn()  { printf "  ${C_YELLOW}!${C_RESET} %-30s ${C_DIM}%s${C_RESET}\n" "$1" "${2-}"; }
item_fail()  { printf "  ${C_RED}✗${C_RESET} %-30s ${C_DIM}%s${C_RESET}\n" "$1" "${2-}"; }
hint()       { printf "    ${C_CYAN}→${C_RESET} ${C_DIM}%s${C_RESET}\n" "$1"; }

run_quiet() {             # run_quiet "Description" cmd args…  (output → log; spinner)
  local desc="$1"; shift
  printf "  ${C_DIM}…${C_RESET} %-30s ${C_DIM}(running, output → %s)${C_RESET}" "$desc" "${LOG##*/}"
  local start; start=$(date +%s)
  if "$@" >>"$LOG" 2>&1; then
    local elapsed=$(( $(date +%s) - start ))
    printf "\r  ${C_GREEN}✓${C_RESET} %-30s ${C_DIM}done in %ds${C_RESET}\n" "$desc" "$elapsed"
    return 0
  else
    local rc=$?
    local elapsed=$(( $(date +%s) - start ))
    printf "\r  ${C_RED}✗${C_RESET} %-30s ${C_DIM}failed after %ds (exit %d)${C_RESET}\n" "$desc" "$elapsed" "$rc"
    return $rc
  fi
}

# ── Failure handler — never half-succeed silently ────────────────────────
fatal() {                 # fatal "step name" "next action hint"
  echo
  printf "${C_RED}${C_BOLD}Setup halted at: %s${C_RESET}\n" "$1"
  echo
  printf "${C_BOLD}Last 30 lines of %s:${C_RESET}\n" "$LOG"
  printf "${C_DIM}%s${C_RESET}\n" "$LINE"
  tail -30 "$LOG" | sed 's/^/  /'
  printf "${C_DIM}%s${C_RESET}\n" "$LINE"
  echo
  printf "${C_CYAN}Next action:${C_RESET} %s\n" "$2"
  exit 1
}

have() { command -v "$1" >/dev/null 2>&1; }

version_of() {            # version_of brew | poetry | ...
  case "$1" in
    brew)   brew --version 2>/dev/null | head -1 | awk '{print $2}' ;;
    poetry) poetry --version 2>/dev/null | awk '{print $NF}' | tr -d ')' ;;
    python) python3 --version 2>/dev/null | awk '{print $2}' ;;
    node)   node --version 2>/dev/null ;;
    npm)    npm --version 2>/dev/null ;;
    docker) docker --version 2>/dev/null | awk '{print $3}' | tr -d ',' ;;
    *)      "$1" --version 2>/dev/null | head -1 ;;
  esac
}

# ────────────────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────────────────
clear 2>/dev/null || true
header "Octoflash · local environment setup"
printf "  ${C_BOLD}Host${C_RESET}       %s (%s)\n" "$PLATFORM" "$ARCH"
printf "  ${C_BOLD}Repository${C_RESET} %s\n" "$ROOT"
printf "  ${C_BOLD}Log${C_RESET}        %s\n" "$LOG"
printf "  ${C_BOLD}Started${C_RESET}    %s\n" "$(date '+%Y-%m-%d %H:%M:%S %Z')"

# ────────────────────────────────────────────────────────────────────────
# [1/7] Native dependencies
# ────────────────────────────────────────────────────────────────────────
section "[1/7] Native dependencies"

if [[ "$PLATFORM" == "macOS" ]]; then
  if ! have brew; then
    item_fail "Homebrew" "not installed"
    hint "install Homebrew: https://brew.sh, then re-run \`make setup\`"
    record "Native deps" "FAILED" "Homebrew missing — install from brew.sh"
    fatal "Native dependencies" "Install Homebrew, then re-run \`make setup\`."
  fi
  item_ok "Homebrew" "$(version_of brew)"

  for pkg in cairo pango ffmpeg libsndfile pkg-config; do
    if brew list --formula --versions "$pkg" >/dev/null 2>&1; then
      ver=$(brew list --formula --versions "$pkg" | awk '{print $2}')
      item_ok "$pkg" "$ver"
    else
      if run_quiet "installing $pkg" brew install "$pkg"; then
        item_ok "$pkg" "installed"
      else
        record "Native deps" "FAILED" "brew install $pkg"
        fatal "Native dependencies" "Run \`brew install $pkg\` manually and re-run setup."
      fi
    fi
  done
  record "Native deps" "READY" "cairo · pango · ffmpeg · libsndfile · pkg-config"
else
  item_skip "Native deps (Linux)" "verify cairo / pango / ffmpeg / libsndfile via your package manager"
  record "Native deps" "SKIPPED" "Linux — verify via apt/dnf/pacman"
fi

# ────────────────────────────────────────────────────────────────────────
# [2/7] Python toolchain
# ────────────────────────────────────────────────────────────────────────
section "[2/7] Python toolchain"

if ! have python3; then
  item_fail "Python 3" "not installed"
  record "Python toolchain" "FAILED" "Python 3 missing"
  fatal "Python toolchain" "Install Python 3.11+ (e.g. \`brew install python@3.11\`) and re-run."
fi
PY_VER=$(version_of python)
item_ok "Python 3" "$PY_VER"

if ! have poetry; then
  item_fail "Poetry" "not installed"
  record "Python toolchain" "FAILED" "Poetry missing"
  fatal "Python toolchain" "Install Poetry: https://python-poetry.org/docs/#installation"
fi
item_ok "Poetry" "$(version_of poetry)"
record "Python toolchain" "READY" "Python $PY_VER · Poetry $(version_of poetry)"

# ────────────────────────────────────────────────────────────────────────
# [3/7] Backend dependencies (Poetry)
# ────────────────────────────────────────────────────────────────────────
section "[3/7] Backend dependencies"

# Quiet Poetry's own noisy urllib3 warning when launched from system Python.
export PYTHONWARNINGS="ignore::Warning"

if ! run_quiet "poetry install --with dev,playground" \
       poetry install --with dev,playground --no-interaction; then
  if grep -q "pyproject.toml changed significantly" "$LOG"; then
    item_warn "Lock drifted" "regenerating poetry.lock"
    if ! run_quiet "poetry lock" poetry lock --no-interaction; then
      record "Backend deps" "FAILED" "poetry lock failed"
      fatal "Backend dependencies" "Inspect $LOG, then run \`poetry lock\` manually."
    fi
    if ! run_quiet "poetry install --with dev,playground" \
           poetry install --with dev,playground --no-interaction; then
      record "Backend deps" "FAILED" "poetry install failed after re-lock"
      fatal "Backend dependencies" "Inspect $LOG; the install error is preserved there."
    fi
  else
    record "Backend deps" "FAILED" "poetry install"
    fatal "Backend dependencies" "Inspect $LOG; the install error is preserved there."
  fi
fi
record "Backend deps" "READY" "groups: main · dev · playground"

# ────────────────────────────────────────────────────────────────────────
# [4/7] Environment file (.env.local)
# ────────────────────────────────────────────────────────────────────────
section "[4/7] Environment file"

# Ask pydantic-settings which file it actually loads — it's not always
# `.env.local`. Falling back to defaults silently is the #1 cause of the
# "Postgres unreachable" puzzle since the port is set in the env file.
ENV_FILE=$(poetry run python - <<'PY' 2>/dev/null || echo ".env.local"
from app.settings import Settings
print(Settings.model_config.get("env_file") or ".env.local")
PY
)

if [[ -f "$ENV_FILE" ]]; then
  item_ok "$ENV_FILE" "already present (left as-is)"
  record "Environment file" "READY" "$ENV_FILE present"
else
  src=""
  # Prefer .env.local — when the user has a hand-tuned one, mirror it across.
  for s in .env.local .env.example .env.dev; do
    if [[ "$s" != "$ENV_FILE" && -f "$s" ]]; then src="$s"; break; fi
  done
  if [[ -n "$src" ]]; then
    cp "$src" "$ENV_FILE"
    item_ok "$ENV_FILE" "seeded from $src"
    record "Environment file" "READY" "seeded from $src"
  else
    : > "$ENV_FILE"
    item_warn "$ENV_FILE" "created empty (fill COGNITO_* / STRIPE_* as needed)"
    record "Environment file" "READY" "empty — fill secrets as needed"
  fi
fi

# ────────────────────────────────────────────────────────────────────────
# [5/7] Database + migrations
# ────────────────────────────────────────────────────────────────────────
section "[5/7] Database + migrations"

check_db() {              # check_db → exit 0 if Postgres reachable
  poetry run python - <<'PY' >>"$LOG" 2>&1
import asyncio, asyncpg
from app.settings import settings
async def chk():
    c = await asyncpg.connect(settings.asyncpg_dsn)
    await c.close()
asyncio.run(chk())
PY
}

DB_REACHABLE=0
DB_AUTOSTARTED=0
if check_db; then
  DB_REACHABLE=1
else
  # Fallback: if Docker is up and docker-compose.yml has a `db` service,
  # bring it up detached and wait for it. This keeps `make setup` truly
  # one-shot for fresh checkouts.
  if have docker && docker info >>"$LOG" 2>&1 && [[ -f docker-compose.yml ]] && grep -qE "^\s*db:" docker-compose.yml; then
    item_warn "Postgres" "not reachable — starting bundled container"
    if run_quiet "docker compose up -d db" docker compose up -d db; then
      printf "  ${C_DIM}…${C_RESET} waiting for Postgres to accept connections"
      for i in $(seq 1 30); do
        if check_db; then
          printf "\r  ${C_GREEN}✓${C_RESET} Postgres                       ${C_DIM}ready (auto-started, took %ds)${C_RESET}\n" "$i"
          DB_REACHABLE=1
          DB_AUTOSTARTED=1
          break
        fi
        printf "."
        sleep 1
      done
      [[ $DB_REACHABLE -eq 0 ]] && printf "\n"
    fi
  fi
fi

if [[ $DB_REACHABLE -eq 1 ]]; then
  if [[ $DB_AUTOSTARTED -eq 0 ]]; then
    item_ok "Postgres" "reachable"
  fi
  if run_quiet "alembic upgrade head" poetry run alembic upgrade head; then
    note="alembic at head"
    [[ $DB_AUTOSTARTED -eq 1 ]] && note="$note (db auto-started via docker compose)"
    record "Database + migrations" "READY" "$note"
  else
    record "Database + migrations" "FAILED" "alembic upgrade head"
    fatal "Database + migrations" "Inspect $LOG for the migration error."
  fi
else
  item_skip "Postgres" "not reachable and could not auto-start"
  hint "manual start:  make docker-db   (or run Postgres natively on :5432)"
  hint "then migrate:  make migrate"
  record "Database + migrations" "SKIPPED" "DB unreachable — run \`make docker-db && make migrate\`"
fi

# ────────────────────────────────────────────────────────────────────────
# [6/7] Playground sandbox (both modes)
# ────────────────────────────────────────────────────────────────────────
section "[6/7] Playground sandbox"

# Local mode prerequisite — manimgl on the host (in the Poetry venv).
LOCAL_READY=0
if poetry run manimgl --help >>"$LOG" 2>&1; then
  LOCAL_READY=1
  item_ok "Local mode" "manimgl in Poetry venv"
else
  item_warn "Local mode" "manimgl not callable"
  hint "fix:  make install-playground"
fi

# Docker mode prerequisite — daemon + sandbox image.
DOCKER_READY=0
DOCKER_IMG_TAG="octoflash-playground-runner:latest"
if have docker && docker info >>"$LOG" 2>&1; then
  item_ok "Docker daemon" "reachable ($(version_of docker))"
  if docker image inspect "$DOCKER_IMG_TAG" >>"$LOG" 2>&1; then
    item_ok "Sandbox image" "$DOCKER_IMG_TAG (already built)"
    DOCKER_READY=1
  else
    if run_quiet "build $DOCKER_IMG_TAG (one-time, several minutes)" \
         docker build -t "$DOCKER_IMG_TAG" infra/playground-runner; then
      item_ok "Sandbox image" "$DOCKER_IMG_TAG (built)"
      DOCKER_READY=1
    else
      item_warn "Sandbox image" "build failed — see log"
      hint "retry:  make playground-image"
    fi
  fi
else
  item_skip "Docker daemon" "not running (or not installed)"
  hint "install Docker Desktop OR use PLAYGROUND_SANDBOX_MODE=local"
fi

# Summary line for the playground component.
if [[ $DOCKER_READY -eq 1 && $LOCAL_READY -eq 1 ]]; then
  record "Playground sandbox" "READY" "both docker and local modes available"
elif [[ $DOCKER_READY -eq 1 ]]; then
  record "Playground sandbox" "READY" "docker mode only (default)"
elif [[ $LOCAL_READY -eq 1 ]]; then
  record "Playground sandbox" "PARTIAL" "local mode only — set PLAYGROUND_SANDBOX_MODE=local"
else
  record "Playground sandbox" "FAILED" "neither mode usable"
fi

# ────────────────────────────────────────────────────────────────────────
# [7/7] Frontend (sibling repo)
# ────────────────────────────────────────────────────────────────────────
section "[7/7] Frontend (sibling repo)"

FE=""
for candidate in "$ROOT/../octoflash-ai-frontend" "$HOME/Desktop/octoflash-ai-frontend"; do
  if [[ -d "$candidate" && -f "$candidate/package.json" ]]; then
    FE="$(cd "$candidate" && pwd)"
    break
  fi
done

if [[ -z "$FE" ]]; then
  item_skip "Frontend repo" "not found"
  hint "expected at  ../octoflash-ai-frontend  or  ~/Desktop/octoflash-ai-frontend"
  record "Frontend" "SKIPPED" "repo not found — backend will run without UI"
else
  item_ok "Frontend repo" "$FE"
  if ! have npm; then
    item_warn "npm" "not on PATH — install Node.js to set up the frontend"
    record "Frontend" "PARTIAL" "npm missing — install Node.js"
  else
    item_ok "Node / npm" "$(version_of node) / $(version_of npm)"
    if ! run_quiet "npm install (workspaces)" bash -c "cd '$FE' && npm install --silent"; then
      record "Frontend" "FAILED" "npm install"
      fatal "Frontend" "Run \`npm install\` in $FE manually and inspect the output."
    fi
    if [[ ! -f "$FE/packages/web/.env.local" && -f "$FE/packages/web/.env.example" ]]; then
      cp "$FE/packages/web/.env.example" "$FE/packages/web/.env.local"
      item_ok ".env.local (web)" "seeded (VITE_API_URL=http://localhost:8000)"
    fi
    # @octoflash/core resolves via dist/ (per its package.json `main`); the
    # web app won't see new exports until core has been compiled at least
    # once. For ongoing iteration on shared TS, run
    # `npm run dev -w @octoflash/core` in another terminal.
    if ! run_quiet "build @octoflash/core" \
           bash -c "cd '$FE' && npm run build -w @octoflash/core --silent"; then
      record "Frontend" "PARTIAL" "core build failed — playgroundApi unavailable"
      fatal "Frontend" "Inspect $LOG; fix the TypeScript error and re-run."
    fi
    record "Frontend" "READY" "deps installed · @octoflash/core built"
  fi
fi

# ────────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────────
echo
header "Summary"

# Find the longest key for column alignment.
maxk=0
for k in "${STATUS_KEYS[@]}"; do (( ${#k} > maxk )) && maxk=${#k}; done

for i in "${!STATUS_KEYS[@]}"; do
  key="${STATUS_KEYS[$i]}"
  val="${STATUS_VALUES[$i]}"
  note="${STATUS_NOTES[$i]}"
  case "$val" in
    READY)   tag="${C_GREEN}READY  ${C_RESET}";;
    PARTIAL) tag="${C_YELLOW}PARTIAL${C_RESET}";;
    SKIPPED) tag="${C_YELLOW}SKIPPED${C_RESET}";;
    FAILED)  tag="${C_RED}FAILED ${C_RESET}";;
    *)       tag="$val";;
  esac
  printf "  %-${maxk}s   %b   ${C_DIM}%s${C_RESET}\n" "$key" "$tag" "$note"
done

echo
printf "  ${C_BOLD}Default playground mode${C_RESET}    ${C_CYAN}PLAYGROUND_SANDBOX_MODE=docker${C_RESET}\n"
printf "  ${C_DIM}flip to %s in .env.local for host execution (dev only)${C_RESET}\n" "local"

echo
printf "${C_BOLD}Next steps${C_RESET}\n"
printf "  1. Backend dev server      ${C_CYAN}make dev${C_RESET}     ${C_DIM}(uvicorn on :8000)${C_RESET}\n"
if [[ -n "$FE" ]]; then
  printf "  2. Frontend dev server     ${C_CYAN}cd %s && npm run dev${C_RESET}\n" "$FE"
  printf "                             ${C_DIM}(Vite on :5173)${C_RESET}\n"
  printf "  3. Playground page         ${C_CYAN}open http://localhost:5173/playground${C_RESET}\n"
fi
echo
printf "${C_DIM}Full transcript: %s${C_RESET}\n" "$LOG"
echo
