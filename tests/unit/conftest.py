# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=unused-argument
"""Fixtures for charm tests."""

# nosec B404: subprocess usage is intentional and safe (predefined executables only).
import subprocess  # nosec

import pytest
from charms.operator_libs_linux.v2 import snap


class FakeSnap:
    """A fake Snap class to simulate snap operations using subprocess."""

    def __init__(self):
        """Initialize the FakeSnap with not installed state."""
        self.present = False

    def ensure(self, state, channel=None):
        """Simulate ensuring the snap is in the desired state.

        Args:
            state: Desired state (Latest or Absent).
            channel: Snap channel (not used in this fake).
        """
        if state == snap.SnapState.Latest:
            # call through to subprocess, which your patch fixture will mock
            subprocess.run(["snap", "install", "aproxy"], check=True)  # nosec
            self.present = True
        elif state == snap.SnapState.Absent:
            subprocess.run(["snap", "remove", "aproxy"], check=True)  # nosec
            self.present = False

    def set(self, config: dict):
        """Simulate setting snap configuration using subprocess.

        Args:
            config: Dictionary of configuration key-value pairs.
        """
        args = [f"{k}={v}" for k, v in config.items()]
        subprocess.run(["snap", "set", "aproxy"] + args, check=True)  # nosec


@pytest.fixture(autouse=True)
def fake_snap(monkeypatch):
    """Patch SnapCache to provide FakeSnap, which uses subprocess.run."""
    fake = FakeSnap()
    monkeypatch.setattr(snap, "SnapCache", lambda: {"aproxy": fake})
    return fake


@pytest.fixture(autouse=True)
def patch_aproxy_manager(monkeypatch):
    """Patch AproxyManager methods that touch the real system."""
    monkeypatch.setattr("aproxy.AproxyManager.write_nft_config", lambda self: None)
    monkeypatch.setattr("aproxy.AproxyManager.ensure_systemd_unit", lambda self: None)
    monkeypatch.setattr("aproxy.AproxyManager.remove_systemd_unit", lambda self: None)


@pytest.fixture(autouse=True)
def patch_subprocess_success(monkeypatch):
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


@pytest.fixture
def patch_subprocess_failure(monkeypatch):
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


@pytest.fixture
def patch_proxy_check(monkeypatch):
    """Patch _is_proxy_reachable to return a specified value."""

    def _do_patch(is_reachable: bool = True):
        """Patch _is_proxy_reachable to return the specified value."""
        monkeypatch.setattr(
            "aproxy.AproxyManager._is_proxy_reachable",
            lambda *a, **k: is_reachable,
        )

    return _do_patch
