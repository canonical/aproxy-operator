# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.aproxy.name
}

output "endpoints" {
  value = {
    juju_info = "juju-info"
  }
}
