variable "subscription_id" {
  description = "Azure subscription where resources will be managed."
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Azure region used by the project."
  type        = string
  default     = "westcentralus"
}

variable "project_name" {
  description = "Short name used when naming Azure resources."
  type        = string
  default     = "support-triage"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "tf"
}

variable "unique_suffix" {
  description = "Globally unique lowercase suffix used by resources such as ACR."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{4,10}$", var.unique_suffix))
    error_message = "The suffix must contain 4 to 10 lowercase letters or numbers."
  }
}

variable "postgres_admin_password" {
  description = "Administrator password for PostgreSQL."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.postgres_admin_password) >= 12
    error_message = "The PostgreSQL password must contain at least 12 characters."
  }
}