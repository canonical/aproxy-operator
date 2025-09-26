#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import jubilant


def test_aproxy_active(juju, aproxy_app):
    """
    arrange: deploy aproxy subordinate charm on ubuntu.
    act: wait for units to settle.
    assert: aproxy subordinate reaches active status.
    """
    juju.wait(jubilant.all_active, timeout=10 * 60)
    units = juju.status().get_units(aproxy_app.name)
    assert all(u.workload_status.current == "active" for u in units.values())


def test_unreachable_proxy_blocks(juju, aproxy_app):
    """
    arrange: aproxy configured with an unreachable proxy.
    act: wait for status update.
    assert: aproxy blocks.
    """
    juju.cli("config", "aproxy", "proxy-address=unreachable.address")

    # Wait until the charm reports blocked
    juju.wait_for(
        lambda: juju.status().get_app("aproxy").app_status.current == "blocked", timeout=5 * 60
    )

    units = juju.status().get_units(aproxy_app.name)
    status = units[aproxy_app.get_leader_unit()].workload_status
    assert status.current == "blocked"


def test_cleanup_on_removal(juju, aproxy_app, principal_app):
    """
    arrange: ubuntu with aproxy subordinate.
    act: remove aproxy charm.
    assert: no leftover proxy env vars on principal unit.
    """
    juju.remove_application(aproxy_app.name)
    juju.wait(jubilant.all_active, timeout=10 * 60)

    stdout = principal_app.ssh("env | grep -i proxy || true")
    assert stdout.strip() == ""
