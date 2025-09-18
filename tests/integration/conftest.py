# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import pathlib
import subprocess
import typing

import jubilant
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--charm-file",
        action="append",
        default=None,
        help="Path(s) to built charm file(s) to use in tests",
    )
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Use an existing Juju model instead of creating a temporary one",
    )
    parser.addoption(
        "--use-existing",
        action="store_true",
        default=False,
        help="Use the currently active Juju model instead of creating a new one",
    )
    parser.addoption(
        "--keep-models",
        action="store_true",
        default=False,
        help="Keep Juju models around after tests instead of destroying them",
    )


@pytest.fixture(name="aproxy_charm_file", scope="session")
def aproxy_charm_file_fixture(pytestconfig: pytest.Config) -> str:
    """Build or get the aproxy charm file."""
    charms = pytestconfig.getoption("--charm-file")
    if charms and len(charms) == 1:
        return charms[0]

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
    assert len(charms) == 1, "aproxy has more than one .charm file, unsure which one to use."
    return str(charms[0])


@pytest.fixture(name="juju", scope="module")
def juju_fixture(request: pytest.FixtureRequest) -> typing.Generator[jubilant.Juju, None, None]:
    """Provide a Juju model for tests."""

    def show_debug_log(juju: jubilant.Juju) -> None:
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    if request.config.getoption("--use-existing", default=False):
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)


@pytest.fixture(name="deploy_charms", scope="module")
def deploy_charms_fixture(juju: jubilant.Juju, aproxy_charm_file: str):
    """Deploy principal and subordinate charms for integration tests."""
    juju.deploy("ubuntu", base="ubuntu@22.04")
    juju.deploy(aproxy_charm_file)
    juju.integrate("ubuntu", "aproxy")
    juju.cli("config", "aproxy", "proxy-address=squid.internal")
    juju.wait(jubilant.all_active, timeout=20 * 60)


class App:
    """Helper class for interacting with deployed applications."""

    def __init__(self, juju: jubilant.Juju, name: str) -> None:
        self._juju = juju
        self.name = name

    def get_leader_unit(self) -> str:
        status = self._juju.status()
        leader = [u for u, unit in status.get_units(self.name).items() if unit.leader]
        if not leader:
            raise RuntimeError(f"No leader unit found for application {self.name}")
        return leader[0]

    def ssh(self, cmd: str, *, unit_num: int | None = None) -> str:
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
