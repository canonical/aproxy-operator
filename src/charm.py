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
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start_and_configure)
        self.framework.observe(self.on.config_changed, self._on_start_and_configure)
        self.framework.observe(self.on.stop, self._on_stop)

    # -------------------- Event Handlers --------------------

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install event for aproxy snap.

        Raises:
            CalledProcessError: if snap install fails.
        """
        self.unit.status = ops.MaintenanceStatus("Installing aproxy snap...")

        if not AproxyManager.is_snap_installed():
            try:
                AproxyManager.install()
                logger.info("Aproxy snap installed.")
            except subprocess.CalledProcessError as e:
                logger.error("Failed to install aproxy snap: %s", e)
                raise

        self.unit.status = ops.ActiveStatus("Aproxy snap successfully installed.")

    def _on_start_and_configure(self, _: ops.EventBase) -> None:
        """Handle start and config-changed events to configure aproxy."""
        config = self._load_config()
        if not config.proxy_address:
            self.unit.status = ops.BlockedStatus("Missing target proxy address in config.")
            return

        aproxy = AproxyManager(config)

        try:
            if not AproxyManager.is_snap_installed():
                self.unit.status = ops.MaintenanceStatus("Installing aproxy snap...")
                AproxyManager.install()
                logger.info("Aproxy snap installed.")
            self.unit.status = ops.MaintenanceStatus("Configuring aproxy snap...")
            aproxy.configure_target_proxy()
            aproxy.write_nft_config()
            aproxy.apply_nft_config()
            aproxy.ensure_systemd_unit()
        except (ValueError, ConnectionError, subprocess.CalledProcessError) as e:
            logger.error("Failed to install or configure aproxy: %s", e)
            self.unit.status = ops.BlockedStatus("Failed to install or configure aproxy.")
            return

        self.unit.status = ops.ActiveStatus("Aproxy interception service started and configured.")

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop event to clean up nftables rules and remove aproxy snap."""
        config = self._load_config()
        aproxy = AproxyManager(config)

        try:
            aproxy.remove_systemd_unit()
            aproxy.remove_nft_config()
            AproxyManager.uninstall()
        except subprocess.CalledProcessError as e:
            logger.error("Failed to clean up aproxy or nftables: %s", e)

        self.unit.status = ops.ActiveStatus("Aproxy interception service stopped.")

    # -------------------- Helpers --------------------

    def _load_config(self) -> AproxyConfig:
        """Load config from charm model config into ProxyConfig."""
        conf = self.model.config
        return AproxyConfig(
            proxy_address=conf.get("proxy-address"),
            proxy_port=conf.get("proxy-port"),
            no_proxy=conf.get("exclude-addresses-from-proxy"),
            intercept_ports=conf.get("intercept-ports"),
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(AproxyCharm)
