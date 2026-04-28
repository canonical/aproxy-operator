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


def test_aproxy_reads_model_proxy(juju, aproxy_app, tinyproxy_url):
    """
    arrange: deploy aproxy with proxy-address configured.
    act: set the model config juju-http-proxy, then unset aproxy proxy-address.
    assert: aproxy reads proxy values from the model config.
    """
    juju.cli("model-config", f"juju-http-proxy=http://{tinyproxy_url}:8888")
    juju.cli("config", "aproxy", "--reset", "proxy-address")

    juju.wait(jubilant.all_active, timeout=5 * 60)
    units = juju.status().get_units(aproxy_app.name)
    assert all(
        f"Service ready on target proxy {tinyproxy_url}:8888" in u.workload_status.message
        for u in units.values()
    )


def test_local_service_accessible_when_port_intercepted(juju, principal_app, aproxy_app):
    """
    arrange: ubuntu with aproxy subordinate; configure it to intercept port 8081.
    act: start an HTTP server on port 8081 and curl it via the unit's own IP address.
    assert: the HTTP server responds 200, confirming that traffic destined for the
            unit's own IP bypasses DNAT (via 'fib daddr type local return') and reaches
            the local service directly.
    """
    juju.wait(jubilant.all_active, timeout=5 * 60)

    # Configure aproxy to intercept port 8081 (a high port that doesn't need root to bind)
    juju.cli("config", "aproxy", "intercept-ports=8081")
    juju.wait(jubilant.all_active, timeout=5 * 60)

    try:
        # Start an HTTP server on port 8081 inside the ubuntu unit
        principal_app.ssh(
            "nohup python3 -m http.server 8081 --bind 0.0.0.0 > /tmp/local8081.log 2>&1 &"
        )

        # Get the unit's own non-loopback IP address
        units = juju.status().get_units(principal_app.name)
        leader = next(name for name, u in units.items() if u.leader)
        ip = units[leader].address or units[leader].public_address

        # Curl the unit's own IP on the intercepted port.
        # Without 'fib daddr type local return', the prerouting chain would DNAT this
        # inbound traffic to the proxy, breaking the local service.
        # With the fib rule, local-destined traffic returns immediately and reaches the server.
        result = principal_app.ssh(
            f"curl -s --max-time 5 -o /dev/null -w '%{{http_code}}' http://{ip}:8081"
        )

        assert result.strip() == "200", (
            f"HTTP server on intercepted port 8081 should be accessible via own IP ({ip}), "
            f"got '{result}'. Without 'fib daddr type local return', inbound traffic on "
            "intercepted ports would be DNAT'd to the proxy, breaking local services."
        )
    finally:
        # Restore default intercept-ports config
        juju.cli("config", "aproxy", "--reset", "intercept-ports")
        juju.wait(jubilant.all_active, timeout=5 * 60)


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
