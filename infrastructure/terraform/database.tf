resource "azurerm_postgresql_flexible_server" "main" {
  name                = local.postgres_server_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  zone                = "3"

  version                           = "16"
  administrator_login               = "supportadmin"
  administrator_password_wo         = var.postgres_admin_password
  administrator_password_wo_version = 1

  delegated_subnet_id           = azurerm_subnet.postgres.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false

  sku_name                     = "B_Standard_B1ms"
  storage_mb                   = 32768
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  authentication {
    password_auth_enabled         = true
    active_directory_auth_enabled = false
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.postgres
  ]

  tags = local.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "support_triage" {
  name      = "support_triage"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"

  lifecycle {
    prevent_destroy = true
  }
}