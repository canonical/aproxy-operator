# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Business exceptions."""


class InvalidCharmConfigError(Exception):
    """Raised when the charm configuration is invalid."""


class NftApplyError(Exception):
    """Raised when applying nft configuration fails."""

    def __init__(self, original: Exception, config_path: str):
        """Initialize.

        Args:
            original: The original exception that caused the failure.
            config_path: The path to the nft configuration file that was being applied.
        """
        super().__init__(f"Failed to apply nft configuration from {config_path}")
        self.original = original
        self.config_path = config_path


class NftCleanupError(Exception):
    """Raised when cleaning up nft configuration fails."""

    def __init__(self, original: Exception, config_path: str):
        """Initialize.

        Args:
            original: The original exception that caused the failure.
            config_path: The path to the nft configuration file that was being cleaned up.
        """
        super().__init__(f"Failed to clean up nft configuration from {config_path}")
        self.original = original
        self.config_path = config_path


class RelationMissingError(Exception):
    """Raised when a required Juju relation is missing."""


class TopologyUnavailableError(Exception):
    """Raised when Juju binding info is unavailable for topology resolution."""
