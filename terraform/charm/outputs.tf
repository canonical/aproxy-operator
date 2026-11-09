# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "The deployed application object."
  value       = juju_application.aproxy
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value       = {}
}

output "requires" {
  description = "Map of the required integration endpoints."
  value = {
    juju_info = {
      kind     = "endpoint"
      name     = juju_application.aproxy.name
      endpoint = "juju-info"
    }
  }
}
