# Architecture

## Local

```
Browser (localhost:5173)
  └── FastAPI (localhost:8000)
        ├── LM Studio (localhost:1234)  — Gemma 4 (or any model)
        └── SQLite  (app.db)
```

## AWS

```
Browser
  │  HTTPS
  ▼
CloudFront ──── /*     ──► S3 (React static build)
           └─── /api/* ──► ALB (HTTP) ──► ECS Fargate (FastAPI)
                                              ├── Amazon Bedrock (LLM)
                                              └── RDS PostgreSQL (DB)

ECR            — Docker image registry
Secrets Mgr    — DATABASE_URL (injected at runtime, never in env plaintext)
IAM task role  — grants ECS → Bedrock invoke (no static AWS keys)
CloudWatch     — container logs, 30-day retention
```

CloudFront sits in front of both the frontend (S3) and the API (ALB). The `/api/*` behaviour forwards all headers and cookies with no caching, which is required for SSE streaming. This means both frontend and API are served over the same HTTPS domain — no mixed-content issues and no CORS wildcard needed.

## Key design decisions

| Decision | Reason |
|---|---|
| Single streaming LLM call per turn | Eliminates the double-call pattern (probe + stream), halving latency |
| Pre-classify writes before touching history | Validation and confirmation checks happen before messages are appended, preventing orphaned tool-call entries on failure |
| `pending_actions` queue | Batches multiple write operations into one confirmation prompt |
| DB-persisted chat history | Conversations survive page refresh and server restarts |
| History trim (last 40 messages) | Prevents context-window overflows in long sessions |
| Session TTL (24 h default) | Bounds in-memory `sessions` dict growth without losing DB history |
| Rate limiter key pruning | Dead session keys are deleted when their timestamp list empties |
| `<thinking>` block strip | Model chain-of-thought is removed before streaming to the client |

## Technology stack

| Layer | Local | AWS |
|---|---|---|
| LLM | LM Studio + any GGUF model | Amazon Bedrock (Nova Micro / configurable) |
| Backend | FastAPI + Uvicorn | ECS Fargate + Uvicorn |
| Database | SQLite | RDS PostgreSQL db.t3.micro |
| Frontend | Vite dev server | S3 + CloudFront |
| Container registry | — | ECR |
| Secrets | `.env` file | Secrets Manager |
| Logs | stdout | CloudWatch Logs |
