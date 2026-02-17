# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "basic_deploy" {
  module {
    source = "./tests"
  }

  assert {
    condition     = output.app_name == "aproxy"
    error_message = "aproxy app_name did not match expected"
  }
}
