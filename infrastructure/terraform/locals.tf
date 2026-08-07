locals {
  resource_group_name = "rg-${var.project_name}-${var.environment}"

  vnet_name               = "vnet-${var.project_name}-${var.environment}"
  container_apps_subnet   = "snet-container-apps-${var.environment}"
  postgres_subnet         = "snet-postgres-${var.environment}"
  private_dns_zone_name   = "supporttriage${var.environment}.postgres.database.azure.com"
  private_dns_link_name   = "link-${var.project_name}-${var.environment}"
  postgres_server_name    = "pg-${var.project_name}-${var.environment}-${var.unique_suffix}"
  container_registry_name = "acrsupporttriage${var.environment}${var.unique_suffix}"
  identity_name           = "id-${var.project_name}-${var.environment}"
  log_workspace_name      = "log-${var.project_name}-${var.environment}"
  container_env_name      = "cae-${var.project_name}-${var.environment}"

  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}