# Store the complete DATABASE_URL so the ECS task never sees the raw password.
# The execution role reads this secret and injects it as an env var.

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${local.name_prefix}/database-url"
  recovery_window_in_days = 0 # instant deletion — change to 7+ for production
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${var.db_username}:${random_password.db.result}@${aws_db_instance.main.address}:5432/chatbot"
}
