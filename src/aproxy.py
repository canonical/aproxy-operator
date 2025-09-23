# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Aproxy controller.

Contains:
 - AproxyConfig: pydantic model that holds configuration parsed from charm config
 - AproxyManager: install/remove/configure aproxy snap, build & apply nftables,
   create a systemd unit that re-applies nftables on boot for persistence.
"""

import ipaddress
import logging
import socket
import subprocess  # nosec: B404
from pathlib import Path
from typing import List, Optional

from charms.operator_libs_linux.v1 import systemd
from charms.operator_libs_linux.v2 import snap
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Files and constants
NFT_CONF_DIR = Path("/etc/aproxy")
NFT_CONF_FILE = NFT_CONF_DIR / "nftables.conf"
SYSTEMD_UNIT_PATH = Path("/etc/systemd/system/aproxy-nftables.service")
APROXY_LISTEN_PORT = 8443
APROXY_SNAP_NAME = "aproxy"
DEFAULT_PROXY_PORT = 3128


class AproxyConfig(BaseModel):
    """Configuration model for aproxy charm.

    Attributes:
        model_config: Pydantic config to forbid extra fields.
        proxy_address: The target proxy address (hostname or IP).
        proxy_port: The target proxy port (default is 3128).
        no_proxy: Comma-separated list of IPs, CIDRs, or hostnames to
            exclude from interception.
        intercept_ports: Comma-separated list of ports to intercept,
            or "ALL" to intercept all ports (default is "80,443").
        intercept_ports_list: List of ports to intercept as strings.
    """

    model_config = ConfigDict(extra="forbid")

    proxy_address: Optional[str] = None
    proxy_port: int = DEFAULT_PROXY_PORT
    no_proxy: str = ""
    intercept_ports: str = "80,443"

    @property
    def intercept_ports_list(self) -> List[str]:
        """Get intercept ports as a list of strings."""
        ports = [port.strip() for port in self.intercept_ports.split(",") if port.strip()]
        if len(ports) == 1 and ports[0].upper() == "ALL":
            return ["0-65535"]
        return ports


class AproxyManager:
    """Manages aproxy snap and nftables persistence."""

    def __init__(self, config: AproxyConfig):
        """Construct.

        Args:
            config: AproxyConfig instance with current configuration.
        """
        self.config = config

    # ---------------- Snap ----------------

    @staticmethod
    def install() -> None:
        """Install aproxy snap using snap helper."""
        logger.info("Installing %s snap", APROXY_SNAP_NAME)
        snap_cache = snap.SnapCache()
        snap_cache[APROXY_SNAP_NAME].ensure(state=snap.SnapState.Latest, channel="edge")

    @staticmethod
    def uninstall() -> None:
        """Remove aproxy snap using snap helper."""
        logger.info("Removing %s snap", APROXY_SNAP_NAME)
        snap_cache = snap.SnapCache()
        snap_cache[APROXY_SNAP_NAME].ensure(state=snap.SnapState.Absent)

    @staticmethod
    def is_snap_installed() -> bool:
        """Check if aproxy snap is installed.

        Returns:
            True if installed, False otherwise.
        """
        snap_cache = snap.SnapCache()
        return snap_cache[APROXY_SNAP_NAME].present

    def configure_target_proxy(self) -> None:
        """Configure aproxy snap with current config.

        Raises:
            ValueError: If proxy_address is not set in config.
            ConnectionError: If the target proxy is not reachable.
        """
        if not self.config.proxy_address:
            raise ValueError("target proxy address is required to configured snap")

        target_proxy = f"{self.config.proxy_address}:{self.config.proxy_port}"
        if not self._is_proxy_reachable(self.config.proxy_address, self.config.proxy_port):
            logger.error("Proxy is not reachable at %s", target_proxy)
            raise ConnectionError(f"Proxy is not reachable at {target_proxy}")

        logger.info("Configuring snap: proxy=%s", target_proxy)
        snap_cache = snap.SnapCache()
        snap_cache[APROXY_SNAP_NAME].set({"proxy": target_proxy})

    def _is_proxy_reachable(self, host: str, port: int = DEFAULT_PROXY_PORT) -> bool:
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

    # ---------------- nftables ----------------

    def _get_primary_ip(self) -> str:
        """Detect machine's primary IP for DNAT target."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.warning("Falling back to 127.0.0.1 for DNAT target: %s", e)
            return "127.0.0.1"

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

    def _get_no_proxy_ips(self) -> list[str]:
        """Convert no-proxy entries to a list of IP addresses.

        Returns:
            A list of resolved IP addresses.
        """
        ip_list: list[str] = []
        for entry in map(str.strip, self.config.no_proxy.split(",")):
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

    def _render_nftables_rules(self) -> str:
        """Render nftables rules for transparent proxy interception.

        - Redirect outbound traffic on configured intercept_ports to aproxy.
        - Exclude private and loopback ranges.
        - Drop inbound traffic to aproxy listener to prevent reflection attacks.

        Returns:
            The nftables rules as a string.
        """
        server_ip = self._get_primary_ip()
        ports_clause = ", ".join(self.config.intercept_ports_list)
        excluded_ips = [
            "127.0.0.0/8",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ] + self._get_no_proxy_ips()

        return f"""#!/usr/sbin/nft -f
        table ip aproxy
        flush table ip aproxy
        table ip aproxy {{
            set excluded_nets {{
                    type ipv4_addr;
                    flags interval; auto-merge;
                    elements = {{ {', '.join(excluded_ips)} }}
                }}
            chain prerouting {{
                type nat hook prerouting priority dstnat; policy accept;
                ip daddr @excluded_nets return
                tcp dport {{ {ports_clause} }} counter dnat {server_ip}:{APROXY_LISTEN_PORT}
            }}

            chain output {{
                type nat hook output priority -150; policy accept;
                ip daddr @excluded_nets return
                tcp dport {{ {ports_clause} }} counter dnat to {server_ip}:{APROXY_LISTEN_PORT}
            }}

            chain input {{
                type filter hook input priority filter; policy accept;
                tcp dport {APROXY_LISTEN_PORT} drop
            }}
        }}
        """

    def write_nft_config(self) -> None:
        """Write nft config to disk."""
        NFT_CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
        NFT_CONF_FILE.write_text(self._render_nftables_rules(), encoding="utf-8")

    def apply_nft_config(self) -> None:
        """Apply nft config immediately.

        Raises:
            CalledProcessError: If the nft command fails.
        """
        try:
            # nosec B404,B603,B607: calling trusted system binary with predefined args
            subprocess.run(["nft", "-f", str(NFT_CONF_FILE)], check=True)  # nosec
            logger.info("Applied nftables rules successfully.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to apply nftables rules: %s", e)
            raise

    def remove_nft_config(self) -> None:
        """Remove nft table.

        Raises:
            CalledProcessError: If the nft command fails.
        """
        try:
            # nosec B404,B603,B607: trusted binary, no untrusted input
            subprocess.run(["nft", "flush", "table", "ip", "aproxy"], check=True)  # nosec
            subprocess.run(["nft", "delete", "table", "ip", "aproxy"], check=True)  # nosec
            logger.info("Cleaned up nftables rules.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to clean up nftables rules: %s", e)
            raise

    # ---------------- systemd ----------------

    def ensure_systemd_unit(self) -> None:
        """Ensure nftables persistence via systemd."""
        content = f"""
        [Unit]
        Description=Aproxy nftables rules
        After=network-online.target
        Wants=network-online.target

        [Service]
        Type=oneshot
        ExecStart=/usr/sbin/nft -f {NFT_CONF_FILE}
        RemainAfterExit=yes

        [Install]
        WantedBy=multi-user.target
        """
        SYSTEMD_UNIT_PATH.write_text(content, encoding="utf-8")
        systemd.service_enable(SYSTEMD_UNIT_PATH.name)
        systemd.service_start(SYSTEMD_UNIT_PATH.name)

    def remove_systemd_unit(self) -> None:
        """Remove systemd unit."""
        systemd.service_stop(SYSTEMD_UNIT_PATH.name)
        systemd.service_disable(SYSTEMD_UNIT_PATH.name)
        SYSTEMD_UNIT_PATH.unlink(missing_ok=True)
