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


def test_traffic_routed_through_aproxy(juju, principal_app):
    """
    arrange: ubuntu with aproxy subordinate.
    act: make an HTTPS request from inside the unit.
    assert: traffic is transparently routed through aproxy.
    """
    juju.wait(jubilant.all_agents_idle, timeout=5 * 60)
    # -s = silent, -o /dev/null = throw away body, -w = only output HTTP code
    result = principal_app.ssh("curl -s -o /dev/null -w '%{http_code}' https://example.com")
    assert result.strip() == "200", f"Expected 200 from example.com, got {result}"


def test_unreachable_proxy_blocks(juju, aproxy_app):
    """
    arrange: aproxy configured with an unreachable proxy.
    act: wait for status update.
    assert: aproxy blocks with unreachable proxy message.
    """
    units = juju.status().get_units(aproxy_app.name)
    leader_unit = aproxy_app.get_leader_unit()

    # Save original proxy config
    original_proxy = juju.get_config(aproxy_app.name).get("proxy-address", "")

    try:
        # Set to bogus proxy
        juju.config(aproxy_app.name, {"proxy-address": "doesnotexist.local"})
        juju.wait(lambda status: units[leader_unit].workload_status.current == "blocked")

        status = juju.status().get_units(aproxy_app.name)[leader_unit].workload_status
        assert status.current == "blocked"
        assert "unreachable" in status.message.lower()
    finally:
        if original_proxy:
            juju.config(aproxy_app.name, {"proxy-address": original_proxy})
            juju.wait(jubilant.all_active, timeout=10 * 60)


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
