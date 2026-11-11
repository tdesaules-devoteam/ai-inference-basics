variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "fr-par"
}
variable "zone" {
  type    = string
  default = "fr-par-2"
}
variable "environment" {
  type    = string
  default = "scaleway-cpu-pilot"
  validation {
    condition     = contains(["scaleway-cpu-pilot", "scaleway-h100", "training"], var.environment)
    error_message = "Unknown cloud environment."
  }
}
variable "training_session_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,30}$", var.training_session_id))
    error_message = "Use a unique lowercase session identifier (3-31 characters)."
  }
}
variable "instance_count" {
  type    = number
  default = 1
  validation {
    condition     = contains([1, 8], var.instance_count)
    error_message = "Only a single pilot or an explicit eight-instance training allocation is supported."
  }
}
variable "instance_type" {
  type    = string
  default = "BASIC3-X8C-32G"
}
variable "image_id" {
  description = "Marketplace local image UUID validated for the selected zone and type."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-f-]{36}$", var.image_id))
    error_message = "Resolve a local image UUID before planning; mutable image aliases are not accepted."
  }
}
variable "volume_size_gb" {
  type    = number
  default = 128
  validation {
    condition     = var.volume_size_gb >= 80 && var.volume_size_gb <= 256
    error_message = "Boot volume must be 80-256 GB; GPU OS requires at least 125 GB."
  }
}
variable "volume_iops" {
  type    = number
  default = 5000
  validation {
    condition     = var.volume_iops == 5000
    error_message = "This MVP uses Block Storage 5K."
  }
}
variable "authorized_ssh_cidrs" {
  type = set(string)
  validation {
    condition     = length(var.authorized_ssh_cidrs) > 0 && alltrue([for c in var.authorized_ssh_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"])
    error_message = "Provide restricted IPv4 instructor CIDRs, never 0.0.0.0/0."
  }
}
variable "authorized_https_cidrs" {
  type = set(string)
  validation {
    condition     = alltrue([for c in var.authorized_https_cidrs : can(cidrnetmask(c))])
    error_message = "Provide valid IPv4 browser access CIDRs."
  }
}
variable "base_domain" {
  type = string
}
variable "enable_public_https" {
  type    = bool
  default = true
}
variable "ttl_hours" {
  type    = number
  default = 8
  validation {
    condition     = var.ttl_hours > 0 && var.ttl_hours <= 8
    error_message = "TTL must be positive and at most eight hours."
  }
}
variable "session_started_at" {
  description = "Fixed RFC3339 allocation start; preserve it on re-apply. External cleanup is still required."
  type        = string
  validation {
    condition     = can(timeadd(var.session_started_at, "1h"))
    error_message = "Use a fixed RFC3339 timestamp."
  }
}
variable "tags" {
  type    = list(string)
  default = []
}
variable "release_version" {
  type    = string
  default = "0.3.0-alpha.1"
}
variable "ssh_public_key" {
  type = string
}
variable "training_acknowledged" {
  type    = bool
  default = false
}
variable "pilot_accepted" {
  description = "Explicit operator assertion backed by reports; does not replace runtime evidence."
  type        = bool
  default     = false
}
