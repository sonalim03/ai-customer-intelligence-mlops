# Deploying FinSight to AWS

## Architecture decision (why this shape, not another)

FinSight runs on **Ollama locally** (free, no API key, good for dev/demo)
but Ollama needs either a GPU instance (expensive, more to manage) or a
separately-hosted server to run in the cloud. Rather than defaulting into
either, this deployment uses a **provider abstraction** (see
`agent/graph.py`'s `_build_llm()`): set `LLM_PROVIDER=bedrock` and the
agent uses **AWS Bedrock** instead — serverless, pay-per-token, no GPU
infrastructure to manage, and auth goes through the ECS task's **IAM
role**, not a code-level API key. Ollama stays the default for local dev.

This is a genuinely useful thing to be able to explain in an interview:
*"the model backend is swappable via one env var — local free inference
for development, serverless managed inference for production, no code
changes between them."*

**Data persistence**: Fargate containers are ephemeral — anything written
to local disk (the SQLite DB, the Chroma store, the trained risk model)
disappears on restart. Rather than bake data into the image (couples
every deploy to yfinance/embedding-model being reachable at build time,
which is brittle) or add a real database service (overkill for a
portfolio project), this uses **EFS** mounted at `/app/data` — cheap,
simple, and the same pattern you'd reach for with any small stateful
container that isn't ready for RDS yet.

**No load balancer**: for a portfolio-scale deployment, this uses a
Fargate task with a public IP directly, skipping the ALB (saves the
hourly ALB cost and NAT gateway complexity). Documented here as a known
simplification — adding an ALB + ACM certificate for a custom HTTPS
domain is the natural next step if this needs to look production-grade
for a demo, and is called out as future work rather than done silently.

---

## Prerequisites

- AWS CLI configured (`aws configure`) with an account that has Bedrock,
  ECS, ECR, EFS, and IAM permissions
- Docker installed locally (or rely on the `docker-build` CI job)
- Request access to the Claude model in Bedrock: AWS Console → Bedrock →
  Model access → request `anthropic.claude-3-5-sonnet-20241022-v2:0` in
  `us-east-1` (approval is usually instant for Anthropic models)

## 1. Create the ECR repository and push the image

```bash
aws ecr create-repository --repository-name finsight --region us-east-1

aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker build -t finsight .
docker tag finsight:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/finsight:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/finsight:latest
```

## 2. Create the IAM roles

```bash
# Execution role (pulls the image, writes logs) — standard AWS managed policy
aws iam create-role --role-name finsight-ecs-execution-role \
  --assume-role-policy-document file://infra/ecs-task-trust-policy.json

aws iam attach-role-policy --role-name finsight-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Task role (what the APPLICATION can do: call Bedrock, write to EFS)
aws iam create-role --role-name finsight-ecs-task-role \
  --assume-role-policy-document file://infra/ecs-task-trust-policy.json

# Fill in <EFS_FILE_SYSTEM_ID> and <EFS_ACCESS_POINT_ID> in this file
# (created in step 3) before running this:
aws iam put-role-policy --role-name finsight-ecs-task-role \
  --policy-name finsight-task-permissions \
  --policy-document file://infra/ecs-task-role-policy.json
```

## 3. Create the EFS file system for persistent data

```bash
FS_ID=$(aws efs create-file-system --region us-east-1 \
  --tags Key=Name,Value=finsight-data --query 'FileSystemId' --output text)
echo "File system ID: $FS_ID"

# Mount targets — one per subnet/AZ you'll run tasks in. Replace with
# your actual subnet + security group IDs (SG must allow NFS/2049
# inbound from the ECS tasks' security group).
aws efs create-mount-target --file-system-id $FS_ID \
  --subnet-id <SUBNET_ID> --security-groups <EFS_SECURITY_GROUP_ID>

AP_ID=$(aws efs create-access-point --file-system-id $FS_ID \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory 'Path=/finsight,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=755}' \
  --query 'AccessPointId' --output text)
echo "Access point ID: $AP_ID"
```

Now edit `infra/ecs-task-definition.json` and `infra/ecs-task-role-policy.json`,
replacing `<EFS_FILE_SYSTEM_ID>`, `<EFS_ACCESS_POINT_ID>`, and
`<ACCOUNT_ID>` with your real values.

## 4. Register the task definition and create the ECS cluster

```bash
aws ecs create-cluster --cluster-name finsight

aws ecs register-task-definition \
  --cli-input-json file://infra/ecs-task-definition.json

aws logs create-log-group --log-group-name /ecs/finsight-api --region us-east-1
```

## 5. Seed the data (one-off task, before the service starts serving)

```bash
aws ecs run-task \
  --cluster finsight \
  --task-definition finsight-api \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_ID>],securityGroups=[<TASK_SECURITY_GROUP_ID>],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"finsight-api","command":["sh","-c","python data/db.py && python scripts/ingest_stock_data.py && python scripts/seed_portfolio.py && python scripts/ingest_news.py && python scripts/train_risk_model.py"]}]}'
```
Watch it in the console or `aws ecs describe-tasks` until it exits
successfully — the EFS volume now has real seeded data that the actual
service task will read from.

## 6. Create the service (the actual long-running API)

```bash
aws ecs create-service \
  --cluster finsight \
  --service-name finsight-api \
  --task-definition finsight-api \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_ID>],securityGroups=[<TASK_SECURITY_GROUP_ID>],assignPublicIp=ENABLED}"
```

Find the running task's public IP:
```bash
TASK_ARN=$(aws ecs list-tasks --cluster finsight --service-name finsight-api --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster finsight --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text
```

```bash
curl http://<PUBLIC_IP>:8000/health
curl -X POST http://<PUBLIC_IP>:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Am I overexposed to any sector in my portfolio?"}'
```

## Known limitations of this setup (documented, not hidden)

- **Public IP changes on task restart.** Fine for a portfolio demo; add
  an ALB (or at minimum an Elastic IP via a NAT setup) if you need a
  stable address.
- **Single task, no auto-scaling.** `desired-count 1` is intentional for
  cost control on a portfolio project — bump it and add an ALB target
  group if you want real horizontal scaling.
- **EFS costs a small amount even at rest** (~$0.30/GB-month) — negligible
  for this dataset size, but worth knowing it's not literally free like
  S3 Glacier would be.
- **No custom domain/HTTPS** — the API is plain HTTP on the task's public
  IP. Fine for demoing to yourself or in an interview; add ACM + ALB for
  anything public-facing long-term.
