# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "latest/edge"
  # renovate: depName="aproxy"
  revision = 1
}

run "basic_deploy" {
  assert {
    condition     = module.aproxy.app_name == "aproxy"
    error_message = "aproxy app_name did not match expected"
  }
}
