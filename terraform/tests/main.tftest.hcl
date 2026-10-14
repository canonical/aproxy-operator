# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  app_name    = "aproxy"
  base        = "ubuntu@24.04"
  channel     = "latest/stable"
  config      = {}
  constraints = "arch=amd64"
  model_uuid  = "00000000-0000-0000-0000-000000000001"
  # renovate: depName="aproxy"
  revision = 270
}

mock_provider "juju" {
  mock_resource "juju_application" {
    defaults = {
      id           = "aproxy"
      model_type   = "lxd"
      unit_numbers = ["0"]
    }
  }
}

run "deploys_application" {
  command = plan

  assert {
    condition     = output.application.name == "aproxy"
    error_message = "aproxy application name did not match expected"
  }

  assert {
    condition     = output.application.model_uuid == var.model_uuid
    error_message = "aproxy application model_uuid did not match expected"
  }

  assert {
    condition     = output.application.charm[0].name == "aproxy"
    error_message = "aproxy application charm name did not match expected"
  }

  assert {
    condition     = output.application.charm[0].channel == "latest/stable"
    error_message = "aproxy application charm channel did not match expected"
  }

  assert {
    condition     = output.application.charm[0].revision == 270
    error_message = "aproxy application charm revision did not match expected"
  }

  assert {
    condition     = output.provides == {}
    error_message = "aproxy provides output did not match expected"
  }

  assert {
    condition     = output.requires.juju_info.kind == "endpoint"
    error_message = "aproxy requires.juju_info kind did not match expected"
  }

  assert {
    condition     = output.requires.juju_info.name == "aproxy"
    error_message = "aproxy requires.juju_info name did not match expected"
  }

  assert {
    condition     = output.requires.juju_info.endpoint == "juju-info"
    error_message = "aproxy requires.juju_info endpoint did not match expected"
  }
}
