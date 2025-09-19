# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Add custom command-line options to pytest.

    Args:
        parser: The pytest command-line parser.
    """
    parser.addoption(
        "--charm-file",
        action="append",
        default=[],
        help="Path(s) to built charm file(s) to use in tests",
    )
    parser.addoption(
        "--model",
        action="store",
        help="Use an existing Juju model instead of creating a temporary one",
    )
    parser.addoption(
        "--keep-models",
        action="store_true",
        default=False,
        help="Keep Juju models around after tests instead of destroying them",
    )
