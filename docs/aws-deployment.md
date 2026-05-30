# AWS Deployment

## Services used

| Service | Role |
|---|---|
| ECR | Docker image registry |
| ECS Fargate | Runs the FastAPI container |
| Application Load Balancer | Routes HTTP to ECS |
| RDS PostgreSQL | Shared database (replaces SQLite) |
| S3 | Hosts the built React static files |
| CloudFront | CDN + HTTPS; proxies `/api/*` to ALB |
| Secrets Manager | Stores `DATABASE_URL` |
| IAM | Task execution role + task role (Bedrock invoke) |
| Amazon Bedrock | Managed LLM inference |
| CloudWatch | Container logs (30-day retention) |

## Prerequisites

```bash
aws configure          # AWS CLI with deploy permissions
terraform -version     # 1.5+
docker -v              # Docker Desktop running
```

## Step 1 — Provision infrastructure

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

Note the outputs — you need them in the next steps:

```
cloudfront_url      = "https://xxxx.cloudfront.net"
ecr_repository_url  = "123456789.dkr.ecr.us-east-1.amazonaws.com/ai-agent-chat-prod-backend"
s3_bucket_name      = "ai-agent-chat-prod-frontend-123456789"
```

Takes ~10 minutes (mostly RDS + CloudFront).

## Step 2 — Build and push the backend

```bash
# Authenticate Docker to ECR
$pw = aws ecr get-login-password --region us-east-1
docker login --username AWS --password $pw <ecr_repository_url>

docker build -t <ecr_repository_url>:latest .
docker push <ecr_repository_url>:latest
```

## Step 3 — Build and upload the frontend

```bash
cd frontend
npm run build    # uses .env.production automatically

aws s3 sync dist/ s3://<s3_bucket_name>/ --delete

aws cloudfront create-invalidation \
  --distribution-id <distribution_id> \
  --paths "/*"
```

## Step 4 — Force ECS to pick up the new image

```bash
aws ecs update-service \
  --cluster ai-agent-chat-prod-cluster \
  --service ai-agent-chat-prod-backend \
  --force-new-deployment
```

## Changing the LLM model

Edit `infra/terraform/variables.tf`:

```hcl
variable "bedrock_model_id" {
  default = "us.amazon.nova-micro-v1:0"
}
```

Then `terraform apply` — only the ECS task definition is updated, ~2 minutes, zero downtime.

Available inference profiles (must use `us.` prefix for cross-region):

| Profile ID | Notes |
|---|---|
| `us.amazon.nova-micro-v1:0` | Cheapest with tool calling |
| `us.amazon.nova-lite-v1:0` | Adds multimodal |
| `us.amazon.nova-pro-v1:0` | Highest capability |
| `us.amazon.nova-2-lite-v1:0` | Nova 2 (needs LiteLLM ≥ 1.72) |

## Teardown

RDS deletion protection must be disabled before destroy:

```bash
cd infra/terraform
# Temporarily disable protection
terraform apply -var="deletion_protection=false"
terraform destroy
```

## Estimated monthly cost

| Service | Approx. |
|---|---|
| ECS Fargate (0.5 vCPU / 1 GB) | $15 |
| RDS db.t3.micro | $15 |
| ALB | $16 |
| CloudFront + S3 | < $1 |
| Bedrock Nova Micro | $0.035 / 1M tokens |
| **Total** | **~$47 / month** |

No NAT Gateway — ECS runs in a public subnet with `assign_public_ip = true`, saving ~$32/month.
