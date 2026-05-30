# Hardening Guide

## What's already in place

| Control | Implementation |
|---|---|
| CORS allowlist | `ALLOWED_ORIGINS` env var; `*` never used in production |
| Error sanitization | Internal exceptions logged server-side only; clients receive a generic message |
| Rate limiting | 15 requests / 60 s per session; dead keys pruned from memory |
| Message length cap | 4 000 character limit on chat input |
| Session TTL | In-memory sessions evicted after `SESSION_TTL_HOURS` (default 24 h) |
| `<thinking>` strip | Model chain-of-thought removed before streaming to client |
| Secrets Manager | `DATABASE_URL` injected at runtime; password never in plaintext env |
| IAM least privilege | ECS task role grants only `bedrock:InvokeModel*`; no wildcard AWS access |
| nginx security headers | X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP, server_tokens off |
| RDS deletion protection | Enabled; final snapshot created on destroy |
| Private RDS | Database in private subnet; no public endpoint |
| Parameterized queries | SQLAlchemy ORM used throughout; no raw SQL string interpolation |

## Recommended next steps

### High priority

**HTTPS on the ALB**
Add an ACM certificate and HTTPS listener to the ALB. Currently CloudFront → ALB is plain HTTP inside the VPC. For most threat models this is acceptable (traffic never leaves AWS), but a strict posture requires TLS end-to-end.

```hcl
# In alb.tf: add a second listener on port 443 with your ACM cert ARN
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.acm_certificate_arn
  ...
}
```

**WAF on CloudFront**
Attach AWS WAF to the CloudFront distribution to block common web attacks (SQLi, XSS, bad bots) before they reach the origin.

```hcl
resource "aws_wafv2_web_acl_association" "cloudfront" {
  resource_arn = aws_cloudfront_distribution.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}
```

**Multi-replica session state**
`pending_actions` live in-memory. With `desired_count > 1`, a confirmation reply might route to a different container and lose the pending state. Fix: store pending actions in ElastiCache (Redis) or in a `pending_actions` DB table.

### Medium priority

**CloudWatch alarms**
Add alarms for ECS task restarts, RDS CPU > 80%, ALB 5xx rate > 1%.

**ALB access logging**
Enable access logs to S3 for audit trail:
```hcl
access_logs {
  bucket  = aws_s3_bucket.alb_logs.bucket
  enabled = true
}
```

**Content-Security-Policy tightening**
The current CSP allows `unsafe-inline` scripts/styles (required by Vite's output). Building with a nonce or using hashes would let you remove this exception.

**Stricter rate limiting**
The current rate limiter is per-session, in-memory, and resets on restart. Consider moving it to ElastiCache for persistence across deployments and to prevent bypass via new session IDs.

### Lower priority

**Dependency scanning**
Add `pip-audit` and `npm audit` to CI to catch known CVEs in dependencies.

**Secrets rotation**
Configure Secrets Manager to auto-rotate the RDS password and update the ECS task.

**VPC endpoints for Bedrock and ECR**
Replace the public-IP ECS approach with private subnets + VPC endpoints. Removes outbound internet access from the ECS tasks entirely.
