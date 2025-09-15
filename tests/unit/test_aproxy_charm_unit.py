# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring
"""Unit tests."""

import pytest
from ops import testing
from charm import AproxyCharm
import subprocess


@pytest.fixture(autouse=True)
def patch_subprocess_success(monkeypatch):
    def fake_run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("subprocess.run", fake_run)


@pytest.fixture
def patch_subprocess_failure(monkeypatch):
    def _do_patch(
        is_install_failure: bool = False,
        is_set_failure: bool = False,
        is_nft_failure: bool = False,
        is_remove_failure: bool = False,
    ):
        def fake_run(cmd, *a, **k):
            if is_install_failure and cmd[:3] == ["snap", "install", "aproxy"]:
                raise subprocess.CalledProcessError(1, cmd)
            if is_set_failure and cmd[:3] == ["snap", "set", "aproxy"]:
                raise subprocess.CalledProcessError(1, cmd)
            if is_nft_failure and cmd[0] == "nft":
                raise subprocess.CalledProcessError(1, cmd)
            if is_remove_failure and cmd[:3] == ["snap", "remove", "aproxy"]:
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr("subprocess.run", fake_run)

    return _do_patch


@pytest.fixture
def patch_proxy_check(monkeypatch):
    def _do_patch(is_reachable: bool = True):
        monkeypatch.setattr(
            "charm.AproxyCharm._is_proxy_reachable",
            lambda *a, **k: is_reachable,
        )

    return _do_patch


def test_install_with_proxy_config_should_succeed():
    """
    arrange: declare a context and input state with proxy configuration.
    act: run the install event.
    assert: status is active with a message indicating successful snap installation.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.ActiveStatus("Aproxy snap successfully installed.")


def test_install_without_proxy_config_should_fail():
    """
    arrange: declare a context and input state without proxy configuration.
    act: run the install event.
    assert: status is blocked with a message indicating missing proxy address in config.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.BlockedStatus("Missing target proxy address in config.")


def test_install_with_snap_install_failure_should_fail(patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy configuration, and simulate snap install failure.
    act: run the install event.
    assert: status is blocked with a message indicating snap installation failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_subprocess_failure(is_install_failure=True)

    out = ctx.run(ctx.on.install(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to install aproxy snap.")


def test_start_proxy_reachable_should_succeed(patch_proxy_check):
    """
    arrange: declare a context, input state with proxy configuration, and simulate reachable proxy.
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
    arrange: declare a context, input state with proxy configuration, and simulate unreachable proxy.
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
    arrange: declare a context, input state with proxy configuration, simulate reachable proxy, and snap config failure.
    act: run the start event.
    assert: status is blocked with a message indicating snap configuration failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)
    patch_subprocess_failure(is_set_failure=True)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to configure aproxy snap.")


def test_start_nftables_failure_should_fail(patch_proxy_check, patch_subprocess_failure):
    """
    arrange: declare a context, input state with proxy configuration, simulate reachable proxy, and nftables failure.
    act: run the start event.
    assert: status is blocked with a message indicating nftables configuration failure.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "target.proxy"})
    patch_proxy_check(is_reachable=True)
    patch_subprocess_failure(is_nft_failure=True)

    out = ctx.run(ctx.on.start(), state)

    assert out.unit_status == testing.BlockedStatus("Failed to configure nftables.")


def test_config_changed_should_succeed(patch_proxy_check):
    """
    arrange: declare a context, input state with modified proxy configuration, and simulate reachable proxy.
    act: run the config_changed event.
    assert: status is active with a message indicating proxy reconfiguration and interception enabled.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={"proxy-address": "modified.proxy"})
    patch_proxy_check(is_reachable=True)

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus("Proxy reconfigured and interception enabled.")


def test_config_changed_without_proxy_config_should_fail():
    """
    arrange: declare a context and input state without proxy configuration.
    act: run the config_changed event.
    assert: status is blocked with a message indicating missing proxy address in config.
    """
    ctx = testing.Context(AproxyCharm)
    state = testing.State(config={})

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus("Missing target proxy address in config.")


def test_config_changed_with_unreachable_proxy_should_fail(patch_proxy_check):
    """
    arrange: declare a context, input state with modified proxy configuration, and simulate unreachable proxy.
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
