variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project name used as a prefix on all resources"
  type        = string
  default     = "ai-agent-chat"
}

variable "environment" {
  description = "Deployment environment label (e.g. prod, staging)"
  type        = string
  default     = "prod"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "chatbot"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID (must support tool calling)"
  type        = string
  # Nova Micro: cheapest model that supports tool use (~$0.035/1M input tokens).
  # No image/video — text-only, which is all this app needs.
  # Nova Lite costs ~$0.06/1M and adds multimodal we don't use.
  # If Amazon has released a newer/cheaper model, update this value.
  default     = "us.amazon.nova-micro-v1:0"
}

variable "llm_temperature" {
  description = "LLM temperature"
  type        = string
  default     = "0.2"
}

variable "backend_image_tag" {
  description = "ECR image tag to deploy"
  type        = string
  default     = "latest"
}

variable "ecs_cpu" {
  description = "Fargate task CPU units (256 / 512 / 1024 …)"
  type        = string
  default     = "512"
}

variable "ecs_memory" {
  description = "Fargate task memory in MiB"
  type        = string
  default     = "1024"
}
