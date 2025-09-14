#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Subordinate charm for aproxy.

This charm installs and manages the aproxy snap, applies nftables REDIRECT
rules, and ensures outbound HTTP/HTTPS traffic is intercepted and forwarded
through aproxy.
"""

import logging
import subprocess
import socket
import typing

import ops

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class AproxyCharm(ops.CharmBase):
    """Charm the aproxy service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.target_proxy: str = self.config.get("proxy-address", "")
        self.no_proxy: str = self.config.get("no-proxy")
        self.intercept_ports: str = self.config.get("intercept-ports")

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)

    # -------------------- Event Handlers --------------------

    def _on_install(self, event: ops.InstallEvent) -> None:
        """Handle install event for aproxy snap."""
        self.unit.status = ops.MaintenanceStatus("Installing aproxy snap...")

        if not self.target_proxy:
            self.unit.status = ops.BlockedStatus("Missing target proxy address in config.")
            return

        try:
            subprocess.run(["snap", "install", "aproxy", "--edge"], check=True)
            logger.info("Installed aproxy snap.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install aproxy snap: {e}")
            self.unit.status = ops.BlockedStatus("Failed to install aproxy snap.")
            return

    def _on_start(self, event: ops.StartEvent) -> None:
        """Handle start event for configuring nftables rules."""
        self.unit.status = ops.MaintenanceStatus("Starting aproxy interception service...")

        self._configure_aproxy()
        self._apply_nftables_rules()
        self.unit.status = ops.ActiveStatus("Aproxy interception service started.")

    def _on_config_changed(self, event: ops.ConfigChangedEvent) -> None:
        """Reconfigure aproxy and nftables after charm config changes."""
        self.unit.status = ops.MaintenanceStatus("Applying config changes...")

        # Refresh config values
        self.target_proxy: str = self.config.get("proxy-address", "")
        self.no_proxy: str = self.config.get("no-proxy")
        self.intercept_ports: str = self.config.get("intercept-ports")

        self._configure_aproxy()
        self._apply_nftables_rules()
        self.unit.status = ops.ActiveStatus("Proxy reconfigured and interception enabled.")

    def _on_stop(self, event: ops.StopEvent) -> None:
        """Handle stop event to clean up nftables rules and remove aproxy snap."""
        self.unit.status = ops.MaintenanceStatus("Stopping aproxy interception service...")

        # Remove nftables rules
        try:
            subprocess.run(["nft", "flush", "table", "ip", "aproxy"], check=True)
            subprocess.run(["nft", "delete", "table", "ip", "aproxy"], check=True)
            logger.info("Cleaned up nftables rules.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clean up nftables rules: {e}")
            self.unit.status = ops.BlockedStatus("Failed to clean up nftables rules.")
            return

        # Remove aproxy snap
        try:
            subprocess.run(["snap", "remove", "aproxy"], check=True)
            logger.info("Removed aproxy snap.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove aproxy snap: {e}")
            self.unit.status = ops.BlockedStatus("Failed to remove aproxy snap.")
            return

        self.unit.status = ops.ActiveStatus("Aproxy interception service stopped.")

    # -------------------- Helpers --------------------

    def _check_if_proxy_reachable(self, host: str, port: int = 3128) -> bool:
        """Check if the target proxy is reachable on the specified port.

        Args:
            host: The target proxy hostname or IP address.
            port: The port number to check (default is 3128).
        """
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.error(f"Proxy {host}:{port} is not reachable: {e}")
            return False

    def _configure_aproxy(self) -> None:
        """Configure aproxy snap with proxy settings."""
        if not self.target_proxy:
            self.unit.status = ops.BlockedStatus("Missing target proxy address in config.")
            return

        self.unit.status = ops.WaitingStatus("Waiting for proxy connectivity check...")

        if not self._check_if_proxy_reachable(self.target_proxy, 3128):
            logger.warning("Proxy is not reachable at %s:3128", self.target_proxy)
            self.unit.status = ops.BlockedStatus(
                f"Target proxy is unreachable at {self.target_proxy}:3128."
            )
            return

        try:
            subprocess.run(
                ["snap", "set", "aproxy", f"proxy={self.target_proxy}:3128"],
                check=True,
            )
            logger.info(f"Configured aproxy snap with target proxy={self.target_proxy}:3128.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure aproxy snap: {e}")
            self.unit.status = ops.BlockedStatus("Failed to configure aproxy snap.")

    def _format_ports(self, ports: str) -> str:
        """Format a comma-separated list of ports into nftables port set syntax.

        Args:
            ports: Comma-separated string of port numbers.
        """
        if ports.strip().upper() == "ALL":
            return "0-65535"
        return ", ".join(port.strip() for port in ports.split(",") if port.strip())

    def _apply_nftables_rules(self) -> None:
        """Apply nftables rules for transparent proxy interception.

        - Redirect outbound traffic on configured intercept_ports to aproxy (127.0.0.1:8443).
        - Exclude private and loopback ranges.
        - Drop inbound traffic to aproxy listener to prevent reflection attacks.
        """
        no_proxy_list = [ip.strip() for ip in self.no_proxy.split(",") if ip.strip()]
        no_proxy_clause = (
            f"ip daddr {{ {', '.join(no_proxy_list)} }} return" if no_proxy_list else ""
        )
        ports_clause = self._format_ports(self.intercept_ports)

        rules = f"""
        table ip aproxy
        flush table ip aproxy
        table ip aproxy {{
            chain prerouting {{
                type nat hook prerouting priority dstnat; policy accept;
                {no_proxy_clause}
                ip daddr != {{ 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 }} \
                    tcp dport {{ {ports_clause} }} counter dnat to 127.0.0.1:8443
            }}

            chain output {{
                type nat hook output priority -100; policy accept;
                ip daddr != {{ 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 }} \
                    tcp dport {{ {ports_clause} }} counter dnat to 127.0.0.1:8443
            }}

            chain input {{
                type filter hook input priority 0; policy accept;
                tcp dport 8443 drop
            }}
        }}
        """
        try:
            subprocess.run(["nft", "-f", "-"], input=rules.encode(), check=True)
            logger.info("Applied nftables rules successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply nftables rules: {e}")
            self.unit.status = ops.BlockedStatus("Failed to configure nftables.")


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(AproxyCharm)
