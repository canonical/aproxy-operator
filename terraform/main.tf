# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "aproxy" {
  name            = var.app_name
  charm           = var.charm_name
  channel         = var.channel
  model           = var.model
  series          = var.series
  base            = var.base
  is_subordinate  = true

  config          = var.config
  units           = 0
}
