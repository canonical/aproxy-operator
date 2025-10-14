# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "latest/edge"
}

variable "revision" {
  description = "Revision number of the charm."
  type        = number
  default     = null
}

terraform {
  required_providers {
    juju = {
      version = "~> 0.23.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

module "aproxy" {
  source   = "./.."
  app_name = "aproxy"
  channel  = var.channel
  revision = var.revision
  model    = "test-aproxy-example"
  config = {
    proxy-address = "127.0.0.1:80"
  }
}

output "app_name" {
  description = "The name of the deployed aproxy charm application."
  value       = module.aproxy.app_name
}

output "endpoints" {
  description = "Integration endpoints exposed by aproxy charm."
  value       = module.aproxy.endpoints
}
