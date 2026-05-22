# Pre-deploy checklist — Octoflash on shared Octopod infra

Everything in this list must be done **manually** before `bash infra/deploy.sh preflight` will pass. Each item is a one-shot, idempotent setup — re-running is fine.

## 1. Shared Octopod foundation must already be deployed

Octoflash imports VPC subnets / security groups, the ECS cluster, the RDS endpoint, and the SES + SQS email pipeline from these stacks (deployed in the Octopod repo, not here):

| Octopod stack | Why Octoflash needs it |
| ------------- | ---------------------- |
| `octopodai-dev-network-stack`         | VPC subnets + security groups for ECS tasks + ALB |
| `octopodai-dev-ecs-cluster`           | ECS cluster running both products' tasks |
| `octopodai-dev-postgress-db-stack`    | RDS endpoint + master credentials secret |
| `octopodai-dev-email-service-stack`   | SQS queue for transactional / marketing email |

If your Octopod stacks have different names, set `SHARED_NETWORK_STACK`, `SHARED_CLUSTER_STACK`, `SHARED_DB_STACK`, `SHARED_EMAIL_STACK` env vars before running `deploy.sh`.

## 2. Route 53 zone for `octoflash.ai`

Create the public hosted zone in Route 53, copy the Zone ID, then replace **every** occurrence of `Z00628722L7RGH80G6C89` in `infra/`:

```bash
ZONE_ID=Z0123ABCDEFGHIJ        # your real zone ID
grep -RlE "Z00628722L7RGH80G6C89" infra/ \
  | xargs sed -i '' "s/Z00628722L7RGH80G6C89/$ZONE_ID/g"
```

Point your registrar's NS records at the four name servers Route 53 assigned.

## 3. CodeBuild GitHub PAT

Create one secret in Secrets Manager (same region as the deploy):

```
Name:   OCTOPOD-BACKEND-GITHUB-TOKEN
Type:   Other type of secret → Plaintext
Value:  <a GitHub PAT with `repo` scope on CoderCouple/octoflash-ai-backend
         and CoderCouple/octoflash-ai-frontend>
```

This single secret is read by stack 02, 07, 06, 09 and by `buildspec.yml`. Don't wrap the PAT in JSON — CodeBuild's GitHub OAuth source resolves it as a plain string.

## 4. Create the Octoflash database on Octopod's RDS

Octoflash uses Octopod's RDS instance but a separate Postgres database. One-time step:

```bash
# Get Octopod's RDS endpoint
aws cloudformation describe-stacks \
  --stack-name octopodai-dev-postgress-db-stack \
  --query "Stacks[0].Outputs[?OutputKey=='DBEndpoint'].OutputValue" \
  --output text

# Get the master credentials
aws secretsmanager get-secret-value \
  --secret-id $(aws cloudformation describe-stacks \
                  --stack-name octopodai-dev-postgress-db-stack \
                  --query "Stacks[0].Outputs[?OutputKey=='DBSecretArn'].OutputValue" \
                  --output text) \
  --query SecretString --output text

# Connect via psql (from inside the VPC or a bastion) and run:
CREATE DATABASE octoflash_db;
```

The Alembic migrations on container startup create the `alembic_version` table inside `octoflash_db`, fully isolated from Octopod's tables.

## 5. (Optional) Bump the ECS cluster instance size

Hosting two products' ECS tasks on the same EC2 fleet means the cluster's instances need enough headroom. If Octopod's cluster runs on `t3.medium` (4 GB), bump it to `t3.large` (8 GB) or `t3.xlarge` (16 GB) **in the Octopod repo** before deploying Octoflash. This is a one-line param change in Octopod's `03-ecs-cluster` stack.

## 6. AWS CLI configured

```bash
aws sts get-caller-identity   # should return an account ID, not an error
```

If not, run `aws configure` or set `AWS_PROFILE` / `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`.

---

## When all of the above is done

```bash
bash infra/deploy.sh preflight    # verifies 1–6
bash infra/deploy.sh secrets      # deploys Cognito + Stripe + OAuth + Temporal stacks (empty)
# → populate secret values in Secrets Manager console
bash infra/deploy.sh build        # deploys ECR + CodeBuild, kicks off first builds
# → wait until :latest exists in both ECR repos
bash infra/deploy.sh services     # deploys backend + frontend ECS services
bash infra/deploy.sh pipelines    # deploys CICD pipelines (auto-deploys on subsequent commits)
bash infra/deploy.sh dns          # creates Route 53 A records
```

`deploy.sh all` runs phases 1 + secrets, then stops so you can populate the secrets manually. Resume with `build`.
