# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "aproxy" {
  name = var.app_name
  charm {
    name     = "aproxy"
    channel  = var.channel
    revision = var.revision
    base     = var.base
  }

  model  = var.model
  config = var.config
  units  = 1
}
