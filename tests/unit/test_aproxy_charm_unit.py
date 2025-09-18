# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring,unused-argument
"""Unit tests for Aproxy subordinate charm."""

# nosec B404: subprocess usage is intentional and safe (predefined executables only).
import subprocess  # nosec

import pytest
from ops import testing
from scenario.errors import UncaughtCharmError

from charm import AproxyCharm


def test_install_with_proxy_config_should_succeed():
    """
    arrange: declare a context and input state with proxy config.
    act: run the install event.
    assert: status is active with a message indicating successful snap installation.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.ActiveStatus("Aproxy snap successfully installed.")


def test_install_without_proxy_config_should_fail():
    """
    arrange: declare a context and input state without proxy config.
    act: run the install event.
    assert: status is blocked with a message indicating missing proxy address in config.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.BlockedStatus("Missing target proxy address in config.")


def test_install_with_snap_install_failure_should_fail(patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy config, and simulate snap install failure.
    act: run the install event.
    assert: CalledProcessError is raised.
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

    assert out.unit_status == testing.ActiveStatus("Aproxy interception service started.")


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
        "Target proxy is unreachable at target.proxy:3128."
    )


def test_start_proxy_snap_config_failure_should_fail(patch_proxy_check, patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy config, and simulate snap config failure.
    act: run the start event.
    assert: status is blocked with a message indicating snap config failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)
    patch_subprocess_failure(is_set_failure=True)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to configure aproxy snap.")


def test_start_nftables_failure_should_fail(patch_proxy_check, patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy config, and simulate nftables failure.
    act: run the start event.
    assert: status is blocked with a message indicating nftables config failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)
    patch_subprocess_failure(is_nft_failure=True)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to configure nftables.")


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

    assert out.unit_status == testing.ActiveStatus("Proxy reconfigured and interception enabled.")


def test_config_changed_without_proxy_config_should_fail():
    """
    arrange: declare a context and input state without proxy config.
    act: run the config_changed event.
    assert: status is blocked with a message indicating missing proxy address in config.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus("Missing target proxy address in config.")


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
        "Target proxy is unreachable at modified.proxy:3128."
    )


def test_stop_should_succeed():
    """
    arrange: declare a context and input state.
    act: run the stop event.
    assert: status is active with a message indicating the interception service stopped.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State()

    out = ctx.run(ctx.on.stop(), state)

    assert out.unit_status == testing.ActiveStatus("Aproxy interception service stopped.")


def test_stop_with_nftables_cleanup_failure_should_fail(patch_subprocess_failure):
    """
    arrange: declare a context, input state, and simulate nftables cleanup failure.
    act: run the stop event.
    assert: status is blocked with a message indicating nftables cleanup failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State()
    patch_subprocess_failure(is_nft_failure=True)

    out = ctx.run(ctx.on.stop(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to clean up nftables rules.")


def test_stop_with_snap_removal_failure_should_fail(patch_subprocess_failure):
    """
    arrange: declare a context, input state, and simulate snap removal failure.
    act: run the stop event.
    assert: status is blocked with a message indicating snap removal failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State()
    patch_subprocess_failure(is_remove_failure=True)

    out = ctx.run(ctx.on.stop(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to remove aproxy snap.")
