# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    # renovate: depName="aproxy"
    revision = 57
  }

  assert {
    condition     = output.app_name == "aproxy"
    error_message = "aproxy app_name did not match expected"
  }
}

run "integration" {
  variables {
    model_uuid = run.setup_tests.model_uuid
  }

  module {
    source = "./tests/integration"
  }

  assert {
    condition     = data.external.aproxy_status.result.status == "maintenance" || data.external.aproxy_status.result.status == "blocked"
    error_message = "aproxy is not in the expected status after integration."
  }
}
