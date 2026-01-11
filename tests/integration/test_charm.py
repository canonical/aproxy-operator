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
    arrange: ubuntu with aproxy subordinate and tinyproxy running.
    act: start a local HTTP server inside the ubuntu unit, then curl it.
    assert: request succeeds via aproxy interception.
    """
    juju.wait(jubilant.all_active, timeout=5 * 60)

    # Start a simple HTTP server on port 8080 inside ubuntu
    # (runs in the background so we can curl it)
    principal_app.ssh("nohup python3 -m http.server 8080 > /tmp/http.log 2>&1 &")

    # Curl the server address from inside ubuntu — intercepted by aproxy
    units = juju.status().get_units(principal_app.name)
    leader = next(name for name, u in units.items() if u.leader)
    ip = units[leader].address or units[leader].public_address
    result = principal_app.ssh(f"curl -s -o /dev/null -w '%{{http_code}}' http://{ip}:8080")

    assert result.strip() == "200", f"Expected 200 from local server, got {result}"


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


def test_aproxy_reads_model_proxy(juju, aproxy_app, tinyproxy_url):
    """
    arrange: deploy aproxy with proxy-address config set, then unset it.
    act: verify aproxy is blocked, then set juju model proxy config.
    assert: aproxy reads proxy values from the model config.
    """
    juju.cli("config", "aproxy", "--reset", "proxy-address")
    juju.wait_for_unit_status(
        "aproxy/0",
        "blocked",
        timeout=5 * 60,
    )

    juju.cli("model-config", f"juju-http-proxy=http://{tinyproxy_url}:8888")
    juju.cli("model-config", f"juju-https-proxy=https://{tinyproxy_url}:8888")

    juju.wait_for_unit_status(
        "aproxy/0",
        "active",
        timeout=5 * 60,
    )
    units = juju.status().get_units(aproxy_app.name)
    unit = units["aproxy/0"]
    assert (
        f"Service ready on target proxy http://{tinyproxy_url}:8888"
        in unit.workload_status.message
    )
