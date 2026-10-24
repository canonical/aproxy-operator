# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    base       = "ubuntu@24.04"
    channel    = "latest/edge"
    # renovate: depName="aproxy"
    revision = 366
  }

  assert {
    condition     = output.application.name == "aproxy"
    error_message = "aproxy application name did not match expected"
  }

  assert {
    condition     = output.requires.juju_info.endpoint == "juju-info"
    error_message = "aproxy module should provide 'requires.juju_info' output"
  }
}
