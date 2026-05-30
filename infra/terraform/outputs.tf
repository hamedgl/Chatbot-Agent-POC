output "cloudfront_url" {
  description = "CloudFront HTTPS URL — open this in your browser"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "alb_dns" {
  description = "ALB DNS name (backend API — accessed via CloudFront /api/*)"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "ECR URL — use this when tagging and pushing the Docker image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.backend.name
}

output "s3_bucket_name" {
  description = "S3 bucket for the React frontend build"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group — stream logs with: aws logs tail <name> --follow"
  value       = aws_cloudwatch_log_group.backend.name
}

output "rds_endpoint" {
  description = "RDS hostname (private — not directly reachable from outside the VPC)"
  value       = aws_db_instance.main.address
  sensitive   = true
}
