# AI Agent Chatbot

A tool-calling AI chatbot for natural-language database management. Chat to read and update a profile, hobbies, calendar events, and settings. Every write requires explicit confirmation before it executes.

Runs **locally** with LM Studio + SQLite, or on **AWS** with Bedrock + ECS Fargate + RDS PostgreSQL — switchable from `.env`.

---

## Quick start

### Local

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# in a second terminal
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). See [docs/local-setup.md](docs/local-setup.md) for prerequisites and Docker Compose instructions.

### AWS

```bash
cd infra/terraform && terraform init && terraform apply
# then build + push images — see docs/aws-deployment.md
```

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/local-setup.md](docs/local-setup.md) | Prerequisites, step-by-step local dev, env variables |
| [docs/aws-deployment.md](docs/aws-deployment.md) | Terraform, ECR push, S3 deploy, model switching, cost |
| [docs/architecture.md](docs/architecture.md) | System diagrams, design decisions, tech stack |
| [docs/api-reference.md](docs/api-reference.md) | All endpoints, SSE event schema |
| [docs/tools.md](docs/tools.md) | Agent tool reference (profile, hobbies, events, settings) |
| [docs/hardening.md](docs/hardening.md) | Security controls in place + recommended next steps |

---

## Tech stack

| | Local | AWS |
|---|---|---|
| LLM | LM Studio (any model) | Amazon Bedrock (Nova Micro) |
| Backend | FastAPI + SQLite | ECS Fargate + RDS PostgreSQL |
| Frontend | Vite dev server | S3 + CloudFront |
| Secrets | `.env` file | Secrets Manager |
