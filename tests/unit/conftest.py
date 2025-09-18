# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=unused-argument
"""Fixtures for charm tests."""

# nosec B404: subprocess usage is intentional and safe (predefined executables only).
import subprocess  # nosec

import pytest


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
            "charm.AproxyCharm._is_proxy_reachable",
            lambda *a, **k: is_reachable,
        )

    return _do_patch
