output "resource_group_name" {
  description = "Terraform-managed Azure resource group."
  value       = azurerm_resource_group.main.name
}

output "container_registry_name" {
  description = "Azure Container Registry name."
  value       = azurerm_container_registry.main.name
}

output "container_registry_login_server" {
  description = "Registry hostname used by container images."
  value       = azurerm_container_registry.main.login_server
}

output "container_app_environment_name" {
  description = "Azure Container Apps environment."
  value       = azurerm_container_app_environment.main.name
}

output "managed_identity_id" {
  description = "Identity the Container App will use."
  value       = azurerm_user_assigned_identity.container_app.id
}

output "postgres_server_name" {
  description = "PostgreSQL Flexible Server name."
  value       = azurerm_postgresql_flexible_server.main.name
}

output "postgres_fqdn" {
  description = "Private PostgreSQL hostname."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "database_name" {
  description = "Application database."
  value       = azurerm_postgresql_flexible_server_database.support_triage.name
}

output "container_app_name" {
  description = "Terraform-managed Container App name."
  value       = azurerm_container_app.api.name
}

output "container_app_fqdn" {
  description = "Public Container App hostname."
  value       = azurerm_container_app.api.latest_revision_fqdn
}

output "container_app_url" {
  description = "Public HTTPS URL."
  value       = "https://${azurerm_container_app.api.latest_revision_fqdn}"
}