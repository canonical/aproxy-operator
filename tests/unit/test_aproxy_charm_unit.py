# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=unused-argument
"""Unit tests for Aproxy subordinate charm."""

# nosec B404: subprocess usage is intentional and safe (predefined executables only).
import subprocess  # nosec

import pytest
from ops import testing
from scenario.errors import UncaughtCharmError

from aproxy import NFT_CONF_FILE
from charm import AproxyCharm


def test_install_with_proxy_config_should_succeed(patch_proxy_check):
    """
    arrange: declare a context and input state with proxy config.
    act: run the install event.
    assert: status is active with a message indicating the interception service started.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.ActiveStatus("Service ready on target proxy target.proxy:80")


def test_install_without_proxy_config_should_fail(patch_proxy_check):
    """
    arrange: declare a context and input state without proxy config.
    act: run the install event.
    assert: status is blocked with a message indicating invalid configuration.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Invalid charm configuration: proxy_address: "
        + "Value error, target proxy address is required to be non-empty string"
    )


def test_install_with_uri_proxy_config_should_fail(patch_proxy_check):
    """
    arrange: declare a context and input state with uri proxy config.
    act: run the install event.
    assert: status is blocked with a message indicating invalid configuration.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "http://target.proxy"})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Invalid charm configuration: "
        + "proxy address must not include URI scheme prefix like http://"
    )


def test_install_with_hostname_exclude_address_should_fail(patch_proxy_check):
    """
    arrange: declare a context and input state with hostname as exclude address.
    act: run the install event.
    assert: status is blocked with a message indicating invalid configuration.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(
        config={
            "proxy-address": "target.proxy",
            "exclude-addresses-from-proxy": "invalid.hostname",
        }
    )
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Invalid charm configuration: exclude_addresses: "
        + "Value error, invalid.hostname must be an IP or CIDR, not a hostname"
    )


def test_install_with_snap_install_failure_should_fail(patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy config, and simulate snap install failure.
    act: run the install event.
    assert: CalledProcessError should be thrown.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_subprocess_failure(is_install_failure=True)

    with pytest.raises(UncaughtCharmError) as excinfo:
        ctx.run(ctx.on.install(), state)

    assert isinstance(excinfo.value.__cause__, subprocess.CalledProcessError)


def test_start_proxy_reachable_should_succeed(patch_proxy_check):
    """
    arrange: declare a context, input state with proxy config, and simulate reachable proxy.
    act: run the start event.
    assert: status is active with a message indicating the interception service started.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.ActiveStatus("Service ready on target proxy target.proxy:80")


def test_start_proxy_unreachable_should_fail(patch_proxy_check):
    """
    arrange: declare a context, input state with proxy config, and simulate unreachable proxy.
    act: run the start event.
    assert: status is blocked with a message indicating the proxy is unreachable.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=False)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Failed to configure aproxy: Proxy is not reachable at target.proxy:80"
    )


def test_start_proxy_snap_config_failure_should_fail(patch_proxy_check, patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy config, and simulate snap config failure.
    act: run the start event.
    assert: CalledProcessError should be thrown.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)
    patch_subprocess_failure(is_set_failure=True)

    with pytest.raises(UncaughtCharmError) as excinfo:
        ctx.run(ctx.on.start(), state)

    assert isinstance(excinfo.value.__cause__, subprocess.CalledProcessError)


def test_start_nftables_failure_should_fail(patch_proxy_check, patch_aproxy_nft_failure):
    """
    arrange: declare a context, input state with proxy config, and simulate nftables failure.
    act: run the start event.
    assert: status is blocked with a message indicating nft configuration failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)
    patch_aproxy_nft_failure(is_apply_failure=True)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.BlockedStatus(
        f"Failed to apply nft configuration from {NFT_CONF_FILE}"
    )


def test_config_changed_should_succeed(patch_proxy_check):
    """
    arrange: declare a context and input state with modified proxy config.
    act: run the config_changed event.
    assert: status is active with a message indicating proxy reconfig and interception enabled.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "modified.proxy"})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus(
        "Service ready on target proxy modified.proxy:80"
    )


def test_config_changed_without_proxy_config_should_fail():
    """
    arrange: declare a context and input state without proxy config.
    act: run the config_changed event.
    assert: status is blocked with a message indicating invalid configuration.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Invalid charm configuration: proxy_address: "
        + "Value error, target proxy address is required to be non-empty string"
    )


def test_config_changed_with_unreachable_proxy_should_fail(patch_proxy_check):
    """
    arrange: declare a context, input state with modified config, and simulate unreachable proxy.
    act: run the config_changed event.
    assert: status is blocked with a message indicating the proxy is unreachable.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "modified.proxy"})
    patch_proxy_check(is_reachable=False)

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Failed to configure aproxy: Proxy is not reachable at modified.proxy:80"
    )


def test_stop_should_succeed():
    """
    arrange: declare a context and input state.
    act: run the stop event.
    assert: status is active with a message indicating the interception service stopped.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})

    out = ctx.run(ctx.on.stop(), state)

    assert out.unit_status == testing.MaintenanceStatus("Aproxy interception service stopped.")


def test_stop_with_nftables_cleanup_failure_should_succeed(patch_aproxy_nft_failure, caplog):
    """
    arrange: declare a context, input state, and simulate nftables cleanup failure.
    act: run the stop event.
    assert: status is active with a log message indicating nftables cleanup failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_aproxy_nft_failure(is_cleanup_failure=True)
    caplog.set_level("ERROR")

    out = ctx.run(ctx.on.stop(), state)

    assert out.unit_status == testing.MaintenanceStatus("Aproxy interception service stopped.")
    assert "Failed to clean up aproxy or nftables" in caplog.text


def test_stop_with_snap_removal_failure_should_succeed(patch_subprocess_failure, caplog):
    """
    arrange: declare a context, input state, and simulate snap removal failure.
    act: run the stop event.
    assert: status is active with a log message indicating snap removal failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_subprocess_failure(is_remove_failure=True)
    caplog.set_level("ERROR")

    out = ctx.run(ctx.on.stop(), state)

    assert out.unit_status == testing.MaintenanceStatus("Aproxy interception service stopped.")
    assert "Failed to clean up aproxy or nftables" in caplog.text


def test_install_with_juju_model_config_should_succeed(patch_proxy_check, monkeypatch):
    """
    arrange: declare a context without charm config, but set juju model config proxy values.
    act: run the install event.
    assert: status is active with a message indicating the interception service started.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "https://juju.proxy:3128")
    monkeypatch.setenv("JUJU_CHARM_HTTP_PROXY", "http://juju.proxy:3128")

    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.ActiveStatus("Service ready on target proxy juju.proxy:3128")
