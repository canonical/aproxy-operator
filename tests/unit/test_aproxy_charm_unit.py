# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring,unused-argument
"""Unit tests for Aproxy subordinate charm."""

# Ignore B404:blacklist since all subprocesses are run with predefined executables.
import subprocess  # nosec

import pytest
from ops import testing
from scenario.errors import UncaughtCharmError

from charm import AproxyCharm


@pytest.fixture(autouse=True)
def _patch_subprocess_success(monkeypatch):
    """Patch subprocess.run to always succeed.

    Arg:
        monkeypatch: pytest fixture to patch functions.
    """

    def fake_run(cmd, *a, **k):
        """Return fake subprocess.run that always succeeds.

        Args:
            cmd: Command to run.
            a: Additional positional arguments.
            k: Additional keyword arguments.

        Returns:
            subprocess.CompletedProcess: Simulated successful command execution.
        """
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("subprocess.run", fake_run)


@pytest.fixture(name="patch_subprocess_failure")
def _patch_subprocess_failure(monkeypatch):
    """Patch subprocess.run to simulate failures based on flags.

    Arg:
        monkeypatch: pytest fixture to patch functions.
    """

    def _do_patch(
        is_install_failure: bool = False,
        is_set_failure: bool = False,
        is_nft_failure: bool = False,
        is_remove_failure: bool = False,
    ):
        """Patch subprocess.run to simulate failures.

        Args:
            is_install_failure: Simulate snap install failure if True.
            is_set_failure: Simulate snap set failure if True.
            is_nft_failure: Simulate nftables command failure if True.
            is_remove_failure: Simulate snap remove failure if True.
        """

        def fake_run(cmd, *a, **k):
            """Return fake subprocess.run that simulates failures based on flags.

            Args:
                cmd: Command to run.
                a: Additional positional arguments.
                k: Additional keyword arguments.

            Raises:
                CalledProcessError: If simulating a failure for the command.

            Returns:
                subprocess.CompletedProcess: Simulated successful command execution if no failure.
            """
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


@pytest.fixture(name="patch_proxy_check")
def _patch_proxy_check(monkeypatch):
    """Patch _is_proxy_reachable to return a specified value."""

    def _do_patch(is_reachable: bool = True):
        """Patch _is_proxy_reachable to return the specified value."""
        monkeypatch.setattr(
            "charm.AproxyCharm._is_proxy_reachable",
            lambda *a, **k: is_reachable,
        )

    return _do_patch


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
