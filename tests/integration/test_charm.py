#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

CHARMCRAFT_DATA = yaml.safe_load(Path("./charmcraft.yaml").read_text(encoding="utf-8"))
APP_NAME = CHARMCRAFT_DATA["name"]
PRINCIPAL = "wordpress"


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, pytestconfig: pytest.Config):
    """Build the charm and deploy it with a principal application."""
    # Build the charm
    charm = await ops_test.build_charm(".")
    await ops_test.model.deploy(charm, application_name=APP_NAME)

    # Deploy a principal application to relate with
    await ops_test.model.deploy("wordpress", application_name=PRINCIPAL, channel="stable")
    await ops_test.model.add_relation(APP_NAME, PRINCIPAL)

    # Wait for both applications to be active
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, PRINCIPAL],
        status="active",
        timeout=1000,
        raise_on_blocked=True,
    )

    aproxy_app = ops_test.model.applications[APP_NAME]
    for unit in aproxy_app.units:
        assert unit.workload_status == "active"
        assert unit.workload_status_message == "Aproxy interception service started."
