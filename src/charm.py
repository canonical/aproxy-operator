#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Subordinate charm for aproxy.

This charm installs and manages the aproxy snap, applies nftables REDIRECT
rules, and ensures outbound HTTP/HTTPS traffic is intercepted and forwarded
through aproxy.
"""

import ipaddress
import logging
import socket

# nosec B404: subprocess usage is intentional and safe (predefined executables only).
import subprocess  # nosec
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
        self._target_proxy = str(self.config.get("proxy-address", ""))
        self._no_proxy = str(self.config.get("no-proxy"))
        self._intercept_ports = str(self.config.get("intercept-ports"))

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)

    # -------------------- Event Handlers --------------------

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install event for aproxy snap.

        Raises:
            CalledProcessError: If snap installation fails.
        """
        self.unit.status = ops.MaintenanceStatus("Installing aproxy snap...")

        try:
            # nosec B404,B603,B607: calling trusted system binary with predefined args
            subprocess.run(["snap", "install", "aproxy", "--edge"], check=True)  # nosec
            logger.info("Installed aproxy snap.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to install aproxy snap: %s", e)
            raise

        self.unit.status = ops.ActiveStatus("Aproxy snap successfully installed.")

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start event for configuring nftables rules."""
        self.unit.status = ops.MaintenanceStatus("Starting aproxy interception service...")

        if not self._is_aproxy_configured():
            return
        self.unit.status = ops.ActiveStatus("Aproxy interception service started.")

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Reconfigure aproxy and nftables after charm config changes."""
        self.unit.status = ops.MaintenanceStatus("Applying config changes...")

        # Refresh config values
        self._target_proxy = str(self.config.get("proxy-address", ""))
        self._no_proxy = str(self.config.get("no-proxy"))
        self._intercept_ports = str(self.config.get("intercept-ports"))

        if not self._is_aproxy_configured():
            return
        self.unit.status = ops.ActiveStatus("Proxy reconfigured and interception enabled.")

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop event to clean up nftables rules and remove aproxy snap."""
        self.unit.status = ops.MaintenanceStatus("Stopping aproxy interception service...")

        # Remove nftables rules
        try:
            # nosec B404,B603,B607: trusted binary, no untrusted input
            subprocess.run(["nft", "flush", "table", "ip", "aproxy"], check=True)  # nosec
            subprocess.run(["nft", "delete", "table", "ip", "aproxy"], check=True)  # nosec
            logger.info("Cleaned up nftables rules.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to clean up nftables rules: %s", e)
            self.unit.status = ops.BlockedStatus("Failed to clean up nftables rules.")
            return

        # Remove aproxy snap
        try:
            # nosec B404,B603,B607: trusted binary, no untrusted input
            subprocess.run(["snap", "remove", "aproxy"], check=True)  # nosec
            logger.info("Removed aproxy snap.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to remove aproxy snap: %s", e)
            self.unit.status = ops.BlockedStatus("Failed to remove aproxy snap.")
            return

        self.unit.status = ops.ActiveStatus("Aproxy interception service stopped.")

    # -------------------- Helpers --------------------

    def _is_proxy_reachable(self, host: str, port: int = 3128) -> bool:
        """Check if the target proxy is reachable on the specified port.

        Args:
            host: The target proxy hostname or IP address.
            port: The port number to check (default is 3128).
        """
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.error("Proxy %s:%s is not reachable: %s", host, port, e)
            return False

    def _configure_target_proxy(self) -> bool:
        """Configure aproxy snap with proxy settings.

        Returns:
            True if target proxy is successfully configured, False otherwise.
        """
        if not self._target_proxy:
            self.unit.status = ops.BlockedStatus("Missing target proxy address in config.")
            return False

        if not self._is_proxy_reachable(self._target_proxy, 3128):
            logger.warning("Proxy is not reachable at %s:3128", self._target_proxy)
            self.unit.status = ops.BlockedStatus(
                f"Target proxy is unreachable at {self._target_proxy}:3128."
            )
            return False

        try:
            # nosec B404,B603,B607: calling trusted system binary with predefined args
            subprocess.run(
                ["snap", "set", "aproxy", f"proxy={self._target_proxy}:3128"],  # nosec
                check=True,
            )
            logger.info("Configured aproxy snap with target proxy=%s:3128.", self._target_proxy)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to configure aproxy snap: %s", e)
            self.unit.status = ops.BlockedStatus("Failed to configure aproxy snap.")
            return False
        return True

    def _format_ports(self, ports: str) -> str:
        """Format a comma-separated list of ports into nftables port set syntax.

        Args:
            ports: Comma-separated string of port numbers.
        """
        if ports.strip().upper() == "ALL":
            return "0-65535"
        return ", ".join(port.strip() for port in ports.split(",") if port.strip())

    def _resolve_hostname_to_ips(self, hostname: str) -> list[str]:
        """Resolve a hostname to its corresponding IP addresses.

        Args:
            hostname: The hostname to resolve.

        Returns:
            A list of resolved IP addresses.
        """
        try:
            return list(
                {
                    str(info[4][0])
                    for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
                }
            )
        except socket.gaierror as e:
            logger.error("Failed to resolve hostname %s: %s", hostname, e)
            return []

    def _get_no_proxy_ips(self, entries: list[str]) -> list[str]:
        """Convert no-proxy entries to a list of IP addresses.

        Args:
            entries: List of no-proxy entries (IP, CIDR, or hostnames).

        Returns:
            A list of resolved IP addresses.
        """
        ip_list = []
        for entry in map(str.strip, entries):
            if not entry:
                continue
            try:
                # Check if entry is a valid IP or CIDR
                ipaddress.ip_network(entry, strict=False)
                ip_list.append(entry)
            except ValueError:
                # Not an IP, attempt to resolve as hostname
                resolved_ips = self._resolve_hostname_to_ips(entry)
                ip_list.extend(resolved_ips)
        return ip_list

    def _apply_nftables_rules(self) -> bool:
        """Apply nftables rules for transparent proxy interception.

        - Redirect outbound traffic on configured intercept_ports to aproxy (127.0.0.1:8443).
        - Exclude private and loopback ranges.
        - Drop inbound traffic to aproxy listener to prevent reflection attacks.

        Returns:
            True if rules were successfully applied, False otherwise.
        """
        no_proxy_list = [
            address.strip() for address in self._no_proxy.split(",") if address.strip()
        ]
        no_proxy_ip_list = self._get_no_proxy_ips(no_proxy_list)
        no_proxy_clause = (
            f"ip daddr {{ {', '.join(no_proxy_ip_list)} }} return" if no_proxy_ip_list else ""
        )
        ports_clause = self._format_ports(self._intercept_ports)

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
                type nat hook output priority -150; policy accept;
                ip daddr != {{ 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 }} \
                    tcp dport {{ {ports_clause} }} counter dnat to 127.0.0.1:8443
            }}

            chain input {{
                type filter hook input priority filter; policy accept;
                tcp dport 8443 drop
            }}
        }}
        """
        try:
            # nosec B404,B603,B607: calling trusted system binary with predefined args
            subprocess.run(["nft", "-f", "-"], input=rules.encode(), check=True)  # nosec
            logger.info("Applied nftables rules successfully.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to apply nftables rules: %s", e)
            self.unit.status = ops.BlockedStatus("Failed to configure nftables.")
            return False
        return True

    def _is_aproxy_configured(self) -> bool:
        """Ensure aproxy snap is configured and nftables rules are applied."""
        if self._configure_target_proxy() and self._apply_nftables_rules():
            return True
        return False


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(AproxyCharm)
