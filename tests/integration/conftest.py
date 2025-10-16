# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=unused-argument
"""Fixtures for charm tests."""

import pathlib

# nosec B404: subprocess usage is intentional and safe (predefined executables only).
import subprocess  # nosec
import typing

import jubilant
import pytest

from tests.integration.tinyproxy import deploy_tinyproxy


@pytest.fixture(name="aproxy_charm_file", scope="session")
def aproxy_charm_file_fixture(pytestconfig: pytest.Config) -> str:
    """Build or get the aproxy charm file.

    Args:
        pytestconfig: Pytest configuration object.

    Returns:
        Path to the built or provided aproxy charm file.
    """
    charms = pytestconfig.getoption("--charm-file")
    if charms and len(charms) == 1:
        return charms[0]

    if charms and len(charms) > 1:
        # Prefer 24.04 build if available
        charm_2404 = [c for c in charms if "24.04" in c]
        charm_2204 = [c for c in charms if "22.04" in c]
        if charm_2404:
            return charm_2404[0]
        if charm_2204:
            return charm_2204[0]
        raise AssertionError("Multiple charm files found, unsure which one to use.")

    # Otherwise, build the charm
    try:
        subprocess.run(
            ["charmcraft", "pack", "--bases-index=0"],
            check=True,
            capture_output=True,
            text=True,
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob("aproxy_*.charm")]
    assert charms, "aproxy_*.charm file not found."
    return str(charms[0])


@pytest.fixture(name="juju", scope="module")
def juju_fixture(request: pytest.FixtureRequest) -> typing.Generator[jubilant.Juju, None, None]:
    """Provide a Juju model for tests."""

    def show_debug_log(juju: jubilant.Juju) -> None:
        """Show the last 1000 lines of the Juju debug log if any tests failed.

        Args:
            juju: Juju controller instance.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)


@pytest.fixture(name="deploy_charms", scope="module")
def deploy_charms_fixture(juju: jubilant.Juju, aproxy_charm_file: str, tinyproxy_url: str):
    """Deploy principal and subordinate charms for integration tests.

    Args:
        juju: Juju controller instance.
        aproxy_charm_file: Path to the built aproxy charm file.
        tinyproxy_url: URL of the upstream tinyproxy.
    """
    juju.deploy("ubuntu", base="ubuntu@24.04")
    juju.deploy(aproxy_charm_file)
    juju.integrate("ubuntu", "aproxy")
    juju.cli("config", "aproxy", f"proxy-address={tinyproxy_url}:8888")
    juju.wait(jubilant.all_active, timeout=20 * 60)


class App:
    """Helper class for interacting with deployed applications."""

    def __init__(self, juju: jubilant.Juju, name: str) -> None:
        """Construct.

        Args:
            juju: Juju controller instance.
            name: Application name.
        """
        self._juju = juju
        self.name = name

    def get_leader_unit(self) -> str:
        """Return the leader unit name of the application.

        Raises:
            RuntimeError: If no leader unit is found.

        Returns:
            The leader unit name (e.g., "ubuntu/0").
        """
        status = self._juju.status()
        leader = [u for u, unit in status.get_units(self.name).items() if unit.leader]
        if not leader:
            raise RuntimeError(f"No leader unit found for application {self.name}")
        return leader[0]

    def ssh(self, cmd: str, *, unit_num: int | None = None) -> str:
        """SSH into a unit and run a command.

        Args:
            cmd: Command to run.
            unit_num: Unit number to target. If None, the leader unit is used.

        Returns:
            The command's standard output.
        """
        unit_name = self.get_leader_unit() if unit_num is None else f"{self.name}/{unit_num}"
        return self._juju.ssh(target=unit_name, command=cmd)


@pytest.fixture(name="principal_app", scope="module")
def principal_app_fixture(juju: jubilant.Juju, deploy_charms) -> App:
    """Return the principal charm app."""
    return App(juju=juju, name="ubuntu")


@pytest.fixture(name="aproxy_app", scope="module")
def aproxy_app_fixture(juju: jubilant.Juju, deploy_charms) -> App:
    """Return the aproxy subordinate app."""
    return App(juju=juju, name="aproxy")


@pytest.fixture(name="tinyproxy_url", scope="module")
def get_tinyproxy_url(juju):
    """Deploy Tinyproxy and return its URL."""
    return deploy_tinyproxy(juju)
