#!/usr/bin/env bash
# Octoflash AWS deployment — orchestrates the Octoflash-specific stacks in
# dependency order. Shared foundation (network, ECS cluster, RDS instance,
# email service, runtime GitHub tokens) is assumed to be already deployed
# by the Octopod repo — see infra/PREFLIGHT.md for the manual steps.
#
# Usage:
#   bash infra/deploy.sh preflight        # sanity-check before deploying
#   bash infra/deploy.sh secrets          # deploy Cognito + Stripe + OAuth + Temporal
#   bash infra/deploy.sh dns-foundation   # deploy stack 10 (wildcard ACM cert)
#   bash infra/deploy.sh build            # deploy ECR/CodeBuild stacks + trigger first builds
#   bash infra/deploy.sh services         # deploy ECS services (backend + frontend) — imports cert
#   bash infra/deploy.sh pipelines        # deploy CICD pipelines
#   bash infra/deploy.sh all              # preflight + everything above, in order
#   bash infra/deploy.sh <stage>          # any one of the above

set -euo pipefail

# ── Config (override via env) ─────────────────────────────────────────────
PROJECT="${PROJECT:-octoflash}"
ENV="${ENV:-dev}"
REGION="${AWS_REGION:-us-west-2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Shared (Octopod-deployed) stacks. Verify the names match what's actually
# in your AWS account before running preflight.
SHARED_NETWORK_STACK="${SHARED_NETWORK_STACK:-octopodai-dev-network-stack}"
SHARED_CLUSTER_STACK="${SHARED_CLUSTER_STACK:-octopodai-dev-ecs-cluster}"
SHARED_DB_STACK="${SHARED_DB_STACK:-octopodai-dev-postgress-db-stack}"
SHARED_EMAIL_STACK="${SHARED_EMAIL_STACK:-octopodai-dev-email-service-stack}"

# ── Colors ────────────────────────────────────────────────────────────────
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
  C_GREEN=$(tput setaf 2); C_BLUE=$(tput setaf 4); C_YELLOW=$(tput setaf 3)
  C_RED=$(tput setaf 1); C_DIM=$(tput dim); C_BOLD=$(tput bold); C_RESET=$(tput sgr0)
else
  C_GREEN=""; C_BLUE=""; C_YELLOW=""; C_RED=""; C_DIM=""; C_BOLD=""; C_RESET=""
fi

step()  { printf "\n${C_BOLD}${C_BLUE}▶ %s${C_RESET}\n" "$*"; }
ok()    { printf "  ${C_GREEN}✓${C_RESET} %s\n" "$*"; }
warn()  { printf "  ${C_YELLOW}!${C_RESET} %s\n" "$*"; }
fail()  { printf "  ${C_RED}✗${C_RESET} %s\n" "$*"; exit 1; }
note()  { printf "    ${C_DIM}%s${C_RESET}\n" "$*"; }

# ── Stack name + path table ───────────────────────────────────────────────
# Order matters for dependencies; deploy_stage() reads this in declared order.
declare -a SECRETS_STAGE=(
  "${PROJECT}-${ENV}-cognito-stack          12-cognito-stack/cognito-stack.yaml                                 12-cognito-stack/cognito-stack-params.json"
  "${PROJECT}-${ENV}-stripe-stack           13-stripe-stack/stripe-stack.yaml                                   13-stripe-stack/stripe-stack-params.json"
  "${PROJECT}-${ENV}-oauth-secrets-stack    14-oauth-secrets-stack/oauth-secrets-stack.yaml                     14-oauth-secrets-stack/oauth-secrets-stack-params.json"
  "${PROJECT}-${ENV}-temporal-secrets-stack 15-temporal-secrets-stack/temporal-secrets-stack.yaml               15-temporal-secrets-stack/temporal-secrets-stack-params.json"
)

# DNS foundation: wildcard ACM cert. Deploys ONCE, before the ECS stacks that
# import the cert ARN (stacks 05 + 08). Survives ECS-stack teardown/redeploy.
declare -a DNS_FOUNDATION_STAGE=(
  "${PROJECT}-${ENV}-dns-records-stack      10-dns-records-stack/dns-records-stack.yaml                         10-dns-records-stack/dns-records-stack-params.json"
)

declare -a BUILD_STAGE=(
  "${PROJECT}-${ENV}-python-code-build-stack 02-python-code-build-stack/python-code-build-stack.yaml             02-python-code-build-stack/python-code-build-stack-params.json"
  "${PROJECT}-${ENV}-nextjs-code-build-stack 07-nextjs-code-build-stack/nextjs-code-build-stack.yaml             07-nextjs-code-build-stack/nextjs-code-build-stack-params.json"
)

declare -a SERVICES_STAGE=(
  "${PROJECT}-${ENV}-python-ecs-stack       05-python-ecs-stack/python-ecs-stack.yaml                           05-python-ecs-stack/python-ecs-stack-params.json"
  "${PROJECT}-${ENV}-nextjs-ecs-stack       08-nextjs-ecs-stack/nextjs-ecs-stack.yaml                           08-nextjs-ecs-stack/nextjs-ecs-stack-params.json"
)

declare -a PIPELINES_STAGE=(
  "${PROJECT}-${ENV}-python-cicd-pipeline-stack 06-python-cicd-pipeline-stack/python-cicd-pipeline-stack.yaml   06-python-cicd-pipeline-stack/python-cicd-pipeline-stack-params.json"
  "${PROJECT}-${ENV}-nextjs-cicd-pipeline-stack 09-nextjs-cicd-pipeline-stack/nextjs-cicd-pipeline-stack.yaml   09-nextjs-cicd-pipeline-stack/nextjs-cicd-pipeline-stack-params.json"
)

# ── Helpers ───────────────────────────────────────────────────────────────
deploy_stack() {
  local stack="$1" template="infra/$2" params="infra/$3"
  [[ -f "$template" ]] || fail "missing template: $template"
  [[ -f "$params" ]]   || fail "missing params:   $params"

  # Build the parameter-override list as a bash array so each Key=Value
  # becomes its own argv element. AWS CLI requires that; passing the whole
  # thing as a single quoted string makes it treat it as one malformed
  # value (rejected with ValidationError).
  local -a overrides=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && overrides+=("$line")
  done < <(jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"' "$params")

  printf "  ${C_DIM}…${C_RESET} %s ${C_DIM}(deploying)${C_RESET}" "$stack"
  if aws cloudformation deploy \
       --region "$REGION" \
       --stack-name "$stack" \
       --template-file "$template" \
       --parameter-overrides "${overrides[@]}" \
       --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
       --no-fail-on-empty-changeset \
       >/tmp/octoflash-deploy.log 2>&1; then
    printf "\r  ${C_GREEN}✓${C_RESET} %s ${C_DIM}(done)${C_RESET}\n" "$stack"
  else
    printf "\r  ${C_RED}✗${C_RESET} %s ${C_DIM}(failed — see /tmp/octoflash-deploy.log)${C_RESET}\n" "$stack"
    tail -20 /tmp/octoflash-deploy.log | sed 's/^/      /'
    return 1
  fi
}

deploy_stage() {
  # Iterate over the array whose name is in $1 — using `eval` since macOS
  # bash 3.2 lacks `local -n` namerefs (added in bash 4.3).
  local stage_name="$1"
  local count_var="${stage_name}_count"
  eval "local count=\${#${stage_name}[@]}"
  local i=0
  while [ "$i" -lt "$count" ]; do
    local row
    eval "row=\${${stage_name}[$i]}"
    read -r stack template params <<<"$row"
    deploy_stack "$stack" "$template" "$params" || return 1
    i=$((i + 1))
  done
}

require_stack_exists() {
  local s="$1"
  if aws cloudformation describe-stacks --stack-name "$s" --region "$REGION" >/dev/null 2>&1; then
    ok "$s"
  else
    fail "shared stack not found: $s   (set SHARED_*_STACK env or deploy it in the Octopod repo)"
  fi
}

require_secret_exists() {
  local s="$1"
  if aws secretsmanager describe-secret --secret-id "$s" --region "$REGION" >/dev/null 2>&1; then
    ok "secret $s"
  else
    fail "secret not found: $s   (create it manually — see infra/PREFLIGHT.md)"
  fi
}

# ── Stages ────────────────────────────────────────────────────────────────
preflight() {
  step "Preflight"
  aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1 \
    || fail "AWS CLI not configured (aws sts get-caller-identity failed)"
  ok "AWS identity: $(aws sts get-caller-identity --query Account --output text)"
  ok "Region: $REGION"

  command -v jq >/dev/null 2>&1 || fail "jq not on PATH (brew install jq)"
  ok "jq available"

  step "Shared (Octopod-deployed) stacks"
  require_stack_exists "$SHARED_NETWORK_STACK"
  require_stack_exists "$SHARED_CLUSTER_STACK"
  require_stack_exists "$SHARED_DB_STACK"
  require_stack_exists "$SHARED_EMAIL_STACK"

  step "Required secrets (created manually — see PREFLIGHT.md)"
  require_secret_exists "OCTOPOD-BACKEND-GITHUB-TOKEN"

  step "Hosted-zone placeholder check"
  # Look for the literal placeholder token, not the resolved zone ID.
  # Concatenated so a future sed run can't accidentally rewrite this guard.
  local placeholder_token="REPLACE_WITH""_OCTOFLASH_AI_HOSTED_ZONE_ID"
  if grep -RlE "$placeholder_token" infra/ >/dev/null 2>&1; then
    grep -RlE "$placeholder_token" infra/ | sed 's/^/    /'
    fail "hosted-zone placeholders still in tree — replace with the real Route 53 zone ID for octoflash.ai"
  else
    ok "no hosted-zone placeholders found"
  fi
}

stage_secrets() {
  step "Stage: Secrets (Cognito + Stripe + OAuth + Temporal)"
  deploy_stage SECRETS_STAGE
  echo
  warn "Now populate the empty secret values via the Secrets Manager console:"
  note "  ${PROJECT}-${ENV}-stripe    (secret_key, webhook_secret, price_id_pro, price_id_enterprise)"
  note "  ${PROJECT}-${ENV}-temporal  (address, namespace, api_key)"
  note "  ${PROJECT}-${ENV}-google-oauth-secret + ${PROJECT}-${ENV}-microsoft-oauth-secret"
}

stage_build() {
  step "Stage: ECR + CodeBuild (backend + frontend)"
  deploy_stage BUILD_STAGE
  step "Triggering first builds"
  for project in "${PROJECT}-ai-backend-dev-build" "${PROJECT}-ai-frontend-dev-build"; do
    if aws codebuild describe-projects --names "$project" --region "$REGION" >/dev/null 2>&1; then
      local build_id
      build_id=$(aws codebuild start-build --project-name "$project" --region "$REGION" \
                  --query 'build.id' --output text)
      ok "$project → $build_id"
    else
      warn "codebuild project not found yet: $project   (stack may still be creating)"
    fi
  done
  note "Watch with:  aws codebuild list-builds-for-project --project-name <project>"
  note "Wait for an image to appear at :latest in ECR before running 'services'."
}

stage_services() {
  step "Stage: ECS services (backend + frontend)"
  deploy_stage SERVICES_STAGE
}

stage_pipelines() {
  step "Stage: CICD pipelines"
  deploy_stage PIPELINES_STAGE
}

stage_dns_foundation() {
  step "Stage: DNS foundation (wildcard ACM cert — stack 10)"
  deploy_stage DNS_FOUNDATION_STAGE
  note "Cert validates ~60s once Route 53 delegation is healthy (DomainValidationOptions.HostedZoneId)."
}

stage_all() {
  preflight
  stage_secrets
  warn "Pause: populate the empty secrets (see message above), then re-run 'deploy.sh dns-foundation'."
}

# ── Dispatch ──────────────────────────────────────────────────────────────
case "${1:-}" in
  preflight)       preflight ;;
  secrets)         stage_secrets ;;
  dns-foundation)  stage_dns_foundation ;;
  build)           stage_build ;;
  services)        stage_services ;;
  pipelines)       stage_pipelines ;;
  all)             stage_all ;;
  "")
    echo "Usage: $0 {preflight|secrets|dns-foundation|build|services|pipelines|all}"
    echo
    echo "Recommended first-time order:"
    echo "  1. $0 preflight"
    echo "  2. $0 secrets             # then populate secret values via AWS console"
    echo "  3. $0 dns-foundation      # wildcard ACM cert (stack 10) — auto-validates"
    echo "  4. $0 build               # then wait for first ECR image to appear"
    echo "  5. $0 services            # imports the cert ARN from stack 10"
    echo "  6. $0 pipelines"
    exit 1
    ;;
  *) echo "unknown stage: $1"; exit 1 ;;
esac
