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
    RelationMissingError,
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
        """Handle install, start and config-changed events to configure aproxy.

        This function includes:
        - Loading configuration and initializing AproxyManager.
        - Installing the aproxy snap if not already installed.
        - Configuring the aproxy snap with the target proxy address and port.
        - Applying nft configuration to intercept outbound TCP traffic.
        - Setting the charm status to Active if successful, or Blocked if any step fails.
        """
        try:
            config = AproxyConfig.from_charm(self)
            aproxy = AproxyManager(config, self)
        except InvalidCharmConfigError as e:
            logger.error("Invalid charm configuration: %s", e)
            self.unit.status = ops.BlockedStatus(f"Invalid charm configuration: {e}")
            return

        if not aproxy.is_snap_installed():
            self.unit.status = ops.MaintenanceStatus("Installing aproxy snap...")
            aproxy.install()
            logger.info("Aproxy snap installed.")

        self.unit.status = ops.MaintenanceStatus("Configuring aproxy snap...")
        try:
            aproxy.configure_target_proxy()
        except ConnectionError as e:
            logger.error("Failed to configure aproxy: %s", e)
            self.unit.status = ops.BlockedStatus(f"Failed to configure aproxy: {e}")
            return

        self.unit.status = ops.MaintenanceStatus("Applying nft configuration...")
        try:
            aproxy.check_relation_availability()
        except RelationMissingError as e:
            logger.error("Juju relation is unavailable: %s", e)
            self.unit.status = ops.BlockedStatus(f"Juju relation is unavailable: {e}")
            return

        try:
            aproxy.apply_nft_config()
            aproxy.persist_nft_config()
        except NftApplyError as e:
            logger.error("Failed to apply nftables rules: %s", e)
            self.unit.status = ops.BlockedStatus(str(e))
            return

        self.unit.status = ops.ActiveStatus(
            f"Service ready on target proxy {config.proxy_address}:{config.proxy_port}"
        )

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop event to clean up nftables rules and remove aproxy snap.

        In case of clean up failures, errors are logged.
        """
        # Load config and initialize AproxyManager
        try:
            config = AproxyConfig.from_charm(self)
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

        self.unit.status = ops.MaintenanceStatus("Aproxy interception service stopped.")


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(AproxyCharm)
