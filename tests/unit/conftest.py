# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=unused-argument
"""Fixtures for charm tests."""

import subprocess  # nosec B404

import pytest
from charmlibs import snap

from aproxy import NFT_CONF_FILE
from errors import NftApplyError, NftCleanupError

# Use hardcoded absolute path for snap binary
_SNAP_BIN = "/usr/bin/snap"


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
            # call through to subprocess, which patch fixture will mock
            subprocess.run([_SNAP_BIN, "install", "aproxy"], check=True)  # nosec B603
            self.present = True
        elif state == snap.SnapState.Absent:
            subprocess.run([_SNAP_BIN, "remove", "aproxy"], check=True)  # nosec B603
            self.present = False

    def set(self, config: dict):
        """Simulate setting snap configuration using subprocess.

        Args:
            config: Dictionary of configuration key-value pairs.
        """
        args = [f"{k}={v}" for k, v in config.items()]
        subprocess.run([_SNAP_BIN, "set", "aproxy", *args], check=True)  # nosec B603

    def get(self, key: str, default=""):
        """Simulate getting snap configuration using subprocess.

        Args:
            key: Configuration key to retrieve.
            default: Default value if key is not set.

        Returns:
            The value of the configuration key or default if not set.
        """
        if not self.present:
            return default

        result = subprocess.run(  # nosec B603
            [_SNAP_BIN, "get", "aproxy", key],
            check=False,
            capture_output=True,
            text=True,
        )

        value = result.stdout.strip() if result.stdout else default
        return value if value else default


@pytest.fixture(autouse=True)
def fake_snap(monkeypatch):
    """Patch SnapCache to provide FakeSnap, which uses subprocess.run."""
    fake = FakeSnap()
    monkeypatch.setattr(snap, "SnapCache", lambda: {"aproxy": fake})
    return fake


@pytest.fixture(autouse=True)
def patch_aproxy_manager(monkeypatch):
    """Patch AproxyManager methods that touch the real system."""
    monkeypatch.setattr("aproxy.AproxyManager.check_relation_availability", lambda self: None)
    monkeypatch.setattr("aproxy.AproxyManager._get_primary_ip", lambda self: "127.0.0.1")
    monkeypatch.setattr("aproxy.AproxyManager.apply_nft_config", lambda self: None)
    monkeypatch.setattr("aproxy.AproxyManager.persist_nft_config", lambda self: None)
    monkeypatch.setattr("aproxy.AproxyManager.remove_systemd_unit", lambda self: None)


@pytest.fixture
def patch_aproxy_nft_failure(monkeypatch):
    """Patch AproxyManager methods to simulate nftables failures."""

    def _do_patch(is_apply_failure: bool = False, is_cleanup_failure: bool = False):
        """Patch AproxyManager methods to simulate nftables failures.

        Args:
            is_apply_failure: Simulate failure in apply_nft_config if True.
            is_cleanup_failure: Simulate failure in remove_nft_config if True.
        """
        if is_apply_failure:
            monkeypatch.setattr(
                "aproxy.AproxyManager.apply_nft_config",
                lambda self: (
                    (_ for _ in ()).throw(
                        NftApplyError(Exception("Simulated nft failure"), NFT_CONF_FILE)
                    )
                ),
            )
        if is_cleanup_failure:
            monkeypatch.setattr(
                "aproxy.AproxyManager.remove_nft_config",
                lambda self: (
                    (_ for _ in ()).throw(
                        NftCleanupError(Exception("Simulated nft cleanup failure"), NFT_CONF_FILE)
                    )
                ),
            )

    return _do_patch


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
            import os

            # Extract binary name from absolute or relative path
            binary = os.path.basename(cmd[0]) if cmd else ""

            def matches_command(expected_binary: str, expected_args: list) -> bool:
                """Check if command matches expected binary and arguments."""
                return (
                    len(cmd) >= len(expected_args) + 1
                    and binary == expected_binary
                    and cmd[1 : len(expected_args) + 1] == expected_args
                )

            if is_install_failure and matches_command("snap", ["install", "aproxy"]):
                raise subprocess.CalledProcessError(1, cmd)
            if is_set_failure and matches_command("snap", ["set", "aproxy"]):
                raise subprocess.CalledProcessError(1, cmd)
            if is_nft_failure and binary == "nft":
                raise subprocess.CalledProcessError(1, cmd)
            if is_remove_failure and matches_command("snap", ["remove", "aproxy"]):
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
