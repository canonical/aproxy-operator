# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Business exceptions."""


class InvalidCharmConfigError(Exception):
    """Raised when the charm configuration is invalid."""


class NftApplyError(Exception):
    """Raised when applying nftables rules fails."""

    def __init__(self, original: Exception, config_path: str):
        super().__init__(f"Failed to apply nftables rules from {config_path}")
        self.original = original
        self.config_path = config_path


class NftCleanupError(Exception):
    """Raised when cleaning up nftables rules fails."""

    def __init__(self, original: Exception, config_path: str):
        super().__init__(f"Failed to clean up nftables rules from {config_path}")
        self.original = original
        self.config_path = config_path


class TopologyUnavailableError(Exception):
    """Raised when Juju relation/binding info is unavailable for topology resolution."""
