#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Subordinate charm for aproxy.

This charm installs and manages the aproxy snap, applies nftables REDIRECT
rules, and ensures outbound TCP traffic is intercepted and forwarded
through aproxy.
"""

import logging
import subprocess  # nosec: B404
import typing

import ops

from aproxy import AproxyConfig, AproxyManager
from errors import (
    InvalidCharmConfigError,
    NftApplyError,
    NftCleanupError,
    TopologyUnavailableError,
)

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

APROXY_SNAP_NAME = "aproxy"


class AproxyCharm(ops.CharmBase):
    """Charm the aproxy service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_start_and_configure)
        self.framework.observe(self.on.start, self._on_start_and_configure)
        self.framework.observe(self.on.config_changed, self._on_start_and_configure)
        self.framework.observe(self.on.stop, self._on_stop)

    # -------------------- Event Handlers --------------------

    def _on_start_and_configure(self, _: ops.EventBase) -> None:
        """Handle start and config-changed events to configure aproxy."""
        # Load config and initialize AproxyManager
        try:
            config = self._load_config()
            aproxy = AproxyManager(config, self)
        except InvalidCharmConfigError as e:
            logger.error("Invalid charm configuration: %s", e)
            self.unit.status = ops.BlockedStatus(f"Invalid charm configuration: {e}")
            return

        # Install aproxy snap
        if not aproxy.is_snap_installed():
            self.unit.status = ops.MaintenanceStatus("Installing aproxy snap...")
            aproxy.install()
            logger.info("Aproxy snap installed.")

        # Configure aproxy
        self.unit.status = ops.MaintenanceStatus("Configuring aproxy snap...")
        try:
            aproxy.configure_target_proxy()
        except ConnectionError as e:
            logger.error("Failed to configure aproxy: %s", e)
            self.unit.status = ops.BlockedStatus(f"Failed to configure aproxy: {e}")
            return

        # Apply nft config
        self.unit.status = ops.MaintenanceStatus("Applying nft configuration...")
        try:
            aproxy.check_relation_availability()
            aproxy.apply_nft_config()
            aproxy.persist_nft_config()
        except TopologyUnavailableError as e:
            logger.error("Juju relation or binding info unavailable: %s", e)
            self.unit.status = ops.BlockedStatus(f"Juju relation or binding info unavailable: {e}")
            return
        except NftApplyError as e:
            logger.error("Failed to apply nftables rules: %s", e)
            self.unit.status = ops.BlockedStatus(str(e))
            return

        self.unit.status = ops.ActiveStatus(
            f"Aproxy interception service started and configured on target proxy address: {config.proxy_address}:{config.proxy_port}"
        )

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop event to clean up nftables rules and remove aproxy snap."""
        # Load config and initialize AproxyManager
        try:
            config = self._load_config()
            aproxy = AproxyManager(config, self)
        except InvalidCharmConfigError as e:
            logger.error("Invalid charm configuration: %s", e)
            self.unit.status = ops.BlockedStatus(f"Invalid charm configuration: {e}")
            return

        # Clean up nftables rules and remove aproxy snap
        try:
            aproxy.remove_systemd_unit()
            aproxy.remove_nft_config()
            aproxy.uninstall()
        except (NftCleanupError, subprocess.CalledProcessError) as e:
            logger.error("Failed to clean up aproxy or nftables: %s", e)

        self.unit.status = ops.ActiveStatus("Aproxy interception service stopped.")

    # -------------------- Helpers --------------------

    def _load_config(self) -> AproxyConfig:
        """Load config from charm model config into ProxyConfig."""
        try:
            config = AproxyConfig.from_charm(self)
            return config
        except InvalidCharmConfigError as exc:
            raise InvalidCharmConfigError(exc) from exc


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(AproxyCharm)
