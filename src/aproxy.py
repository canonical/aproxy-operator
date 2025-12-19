# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Aproxy controller.

Contains:
 - AproxyConfig: pydantic model that holds configuration parsed from charm config
 - AproxyManager: install/remove/configure aproxy snap, build & apply nft configuration,
   create a systemd unit that re-applies nft configuration on boot for persistence.
"""

# pylint: disable=no-self-argument
from __future__ import annotations

import ipaddress
import logging
import os
import re
import socket
import subprocess  # nosec: B404
import textwrap
from pathlib import Path
from typing import List

import ops
from charmlibs import snap
from charms.operator_libs_linux.v1 import systemd
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from errors import (
    InvalidCharmConfigError,
    NftApplyError,
    NftCleanupError,
    RelationMissingError,
    TopologyUnavailableError,
)

logger = logging.getLogger(__name__)

# Files and constants
NFT_CONF_DIR = Path("/opt/aproxy-charm")
NFT_CONF_FILE = NFT_CONF_DIR / "nftables.conf"
SYSTEMD_UNIT_PATH = Path("/etc/systemd/system/aproxy-nftables.service")
APROXY_LISTEN_PORT = 8443
APROXY_SNAP_NAME = "aproxy"
APROXY_SNAP_CHANNEL = "edge"
DEFAULT_PROXY_PORT = 80
RELATION_NAME = "juju-info"

# ^\.?             : one leading dot allowed
# (?!-)            : no leading dash
# (?!.*--)         : no consecutive dashes
# (?!.*-$)         : no trailing dash
# ([a-zA-Z0-9-]{1,63}\.)*    : 1-63 chars per label, with dots allowed as separators
# ([a-zA-Z0-9-]{1,63})\.?$   : last label (with one dot allowed at the end)
HOSTNAME_PATTERN = re.compile(
    r"^\.?(?!-)(?!.*--)(?!.*-$)([a-zA-Z0-9-]{1,63}\.)*([a-zA-Z0-9-]{1,63})\.?$"
)

# ^                : start of the string
# [a-zA-Z]         : match letter
# [a-zA-Z0-9+\-.]* : match letters, digits, +, -, ., zero or more times
# ://              : match literal "://"
URI_SCHEME_PREFIX_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://")


class AproxyConfig(BaseModel):
    """Configuration model for aproxy charm.

    Attributes:
        model_config: Pydantic config to forbid extra fields.
        proxy_address: The target proxy address (hostname or IP).
        proxy_port: The target proxy port.
        exclude_addresses: Comma-separated list of IPs, CIDRs, or hostnames to
            exclude from interception.
        intercept_ports_list: List of ports to intercept as strings.
    """

    model_config = ConfigDict(extra="forbid")

    proxy_address: str
    proxy_port: int = DEFAULT_PROXY_PORT
    exclude_addresses: List[str] = []
    intercept_ports_list: List[str]

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> AproxyConfig:
        """Load and validate configuration from charm config.

        Args:
            charm: The charm instance, used to access model config.

        Returns:
            An AproxyConfig instance with validated configuration.

        Raises:
            InvalidCharmConfigError: If any configuration field is invalid.
        """
        conf = charm.model.config

        # Parse proxy-address and proxy port
        fallback_proxy = cls._get_principal_proxy_address()
        proxy_conf = str(conf.get("proxy-address", fallback_proxy)).strip()
        proxy_address, proxy_port = proxy_conf, DEFAULT_PROXY_PORT

        if ":" in proxy_conf:
            host, port_str = proxy_conf.rsplit(":", 1)
            proxy_address = host.strip()
            try:
                proxy_port = int(port_str)
            except ValueError as exc:
                raise InvalidCharmConfigError(
                    f"port value must be of type integer instead of {port_str}"
                ) from exc

        # Parse no proxy list
        exclude_addresses = []
        raw_exclude_addresses = str(conf.get("exclude-addresses-from-proxy", ""))
        if raw_exclude_addresses:
            exclude_addresses = [
                entry.strip() for entry in raw_exclude_addresses.split(",") if entry.strip()
            ]

        # Parse intercept ports
        intercept_ports_raw = str(conf.get("intercept-ports", ""))
        intercept_ports_list = intercept_ports_raw.split(",") if intercept_ports_raw else []

        # Build the AproxyConfig instance and validate the fields
        try:
            return cls(
                proxy_address=proxy_address,
                proxy_port=proxy_port,
                exclude_addresses=exclude_addresses,
                intercept_ports_list=intercept_ports_list,
            )
        except ValidationError as exc:
            # Format each error as "<field>: <message>"
            error_field_str = ", ".join(
                f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in exc.errors()
            )
            raise InvalidCharmConfigError(error_field_str) from exc

    # ---------------- Validators ----------------

    @field_validator("proxy_address")
    def _validate_proxy_address(cls, proxy_address: str) -> str:  # noqa: N805
        """Validate that proxy_address is a non-empty string."""
        if not proxy_address or not isinstance(proxy_address, str) or not proxy_address.strip():
            raise ValueError("target proxy address is required to be non-empty string")
        return proxy_address.strip()

    @field_validator("proxy_port")
    def _validate_proxy_port(cls, proxy_port: int) -> int:  # noqa: N805
        """Validate that proxy_port is a valid port number."""
        if not 0 < proxy_port < 65536:
            raise ValueError(f"proxy port must be between 1 and 65535 instead of {proxy_port}")
        return proxy_port

    @field_validator("exclude_addresses")
    def _validate_exclude_addresses(cls, exclude_addresses: List[str]) -> List[str]:  # noqa: N805
        """Validate exclude_addresses entries are valid IPs, CIDRs, or hostnames."""
        valid_exclude_addresses = []
        for entry in exclude_addresses:
            entry = entry.strip()
            if not entry:
                continue
            try:
                # Check if it's a valid IP or CIDR
                ipaddress.ip_network(entry, strict=False)
                valid_exclude_addresses.append(entry)
            except ValueError as exc:
                # If not an IP/CIDR, check if it's a valid hostname
                if HOSTNAME_PATTERN.match(entry):
                    valid_exclude_addresses.append(entry)
                else:
                    raise ValueError(f"invalid exclude_addresses entry {entry}") from exc
        return valid_exclude_addresses

    @field_validator("intercept_ports_list")
    def _validate_and_merge_ports(cls, ports: List[str]) -> List[str]:  # noqa: N805
        """Validate and merge intercept_ports into a list of port ranges as strings."""
        if not ports:
            return []

        ports = [p.strip() for p in ports if p.strip()]
        if len(ports) == 1 and ports[0].upper() == "ALL":
            return ["1-65535"]

        return cls._merge_port_ranges(ports)

    # ---------------- Helpers ----------------

    @classmethod
    def _merge_port_ranges(cls, ports: List[str]) -> List[str]:
        """Merge overlapping port ranges."""
        ranges = cls._convert_ports_to_ranges(ports)

        # Merge overlapping ranges
        ranges.sort()
        merged_port: List[List[int]] = []
        for start, end in ranges:
            if not merged_port or merged_port[-1][1] < start - 1:
                merged_port.append([start, end])
            else:
                merged_port[-1][1] = max(merged_port[-1][1], end)

        return [f"{start}-{end}" if start != end else str(start) for start, end in merged_port]

    @classmethod
    def _convert_ports_to_ranges(cls, ports: List[str]) -> List[tuple]:
        """Convert all port values to sorted ranges."""
        ranges: List[tuple] = []
        for item in ports:
            if "-" not in item:
                item = f"{item}-{item}"
            try:
                start, end = map(int, item.split("-", 1))
            except ValueError as exc:
                raise ValueError(f"invalid port range: {item}") from exc
            if not 1 <= start <= end <= 65535:
                raise ValueError(f"port range must be between 1 and 65535 instead of {item}")
            ranges.append((start, end))

        return ranges

    @classmethod
    def _get_principal_proxy_address(cls) -> str:
        """Get proxy address from Juju-provided environment variables.

        Juju automatically exposes proxy configuration to charms as environment
        variables (JUJU_CHARM_HTTP_PROXY, JUJU_CHARM_HTTPS_PROXY).

        Returns:
            The proxy address (hostname or IP) if set, else an empty string.
        """
        https_proxy = os.environ.get("JUJU_HTTPS_PROXY", "")
        http_proxy = os.environ.get("JUJU_HTTP_PROXY", "")

        proxy_conf = https_proxy or http_proxy or ""

        # Strip prefix like http://, https://, socks5h://, ftp://, etc.
        return URI_SCHEME_PREFIX_RE.sub("", proxy_conf)


class AproxyManager:
    """Manages aproxy snap and nft configuration persistence."""

    def __init__(self, config: AproxyConfig, charm: ops.CharmBase):
        """Construct.

        Args:
            config: AproxyConfig instance with current configuration.
            charm: The charm instance, used to access model bindings.
        """
        self.config = config
        self.charm = charm

    # ---------------- Snap ----------------

    def install(self) -> None:
        """Install aproxy snap using snap helper."""
        logger.info("Installing %s snap", APROXY_SNAP_NAME)
        snap_cache = snap.SnapCache()
        snap_cache[APROXY_SNAP_NAME].ensure(
            state=snap.SnapState.Latest, channel=APROXY_SNAP_CHANNEL
        )

    def uninstall(self) -> None:
        """Remove aproxy snap using snap helper."""
        logger.info("Removing %s snap", APROXY_SNAP_NAME)
        snap_cache = snap.SnapCache()
        snap_cache[APROXY_SNAP_NAME].ensure(state=snap.SnapState.Absent)

    def is_snap_installed(self) -> bool:
        """Check if aproxy snap is installed.

        Returns:
            True if installed, False otherwise.
        """
        snap_cache = snap.SnapCache()
        return snap_cache[APROXY_SNAP_NAME].present

    def configure_target_proxy(self) -> None:
        """Configure aproxy snap with current config.

        Raises:
            ConnectionError: If the target proxy is not reachable.
        """
        snap_cache = snap.SnapCache()
        aproxy_snap = snap_cache[APROXY_SNAP_NAME]

        # Check if current config is the same as the target config
        try:
            current_proxy = aproxy_snap.get("proxy-address")
        except snap.SnapError:
            current_proxy = ""
        target_proxy = f"{self.config.proxy_address}:{self.config.proxy_port}"
        if current_proxy == target_proxy:
            logger.info("Proxy is already set to %s, skipping reconfiguration", target_proxy)
            return

        # Check if target proxy is reachable
        if not self._is_proxy_reachable(self.config.proxy_address, self.config.proxy_port):
            logger.error("Proxy is not reachable at %s", target_proxy)
            raise ConnectionError(f"Proxy is not reachable at {target_proxy}")

        logger.info("Configuring snap: proxy=%s", target_proxy)
        aproxy_snap.set({"proxy": target_proxy})

    def _is_proxy_reachable(self, host: str, port: int = DEFAULT_PROXY_PORT) -> bool:
        """Check if the target proxy is reachable on the specified port.

        Args:
            host: The target proxy hostname or IP address.
            port: The port number to check.
        """
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except (TimeoutError, ConnectionRefusedError) as e:
            logger.error("Proxy %s:%s is not reachable: %s", host, port, e)
            return False

    # ---------------- nftables ----------------

    def _get_primary_ip(self) -> str:
        """Get this unit's primary IP using Juju binding.

        Returns:
            The unit's bound private IP address.
        """
        relation, binding = self.check_relation_availability()
        current_unit_ip = str(binding.network.bind_address)

        if logger.isEnabledFor(logging.DEBUG):
            # Only read from unit databags to avoid RelationDataAccessError on
            # non-leader units (reading own application databag is forbidden).
            peer_unit_ips: list[str] = []
            for unit in relation.units:
                ip = relation.data[unit].get("private-address", "")
                if ip:
                    peer_unit_ips.append(ip)

            logger.debug(
                "Resolved unit IP %s via relation '%s' (peer unit IPs: %s)",
                current_unit_ip,
                RELATION_NAME,
                peer_unit_ips,
            )

        return current_unit_ip

    def _render_nft_rules(self) -> str:
        """Render nftables rules for transparent proxy interception.

        - Redirect outbound traffic on configured intercept_ports to aproxy.
        - Exclude private loopback ranges.
        - Drop inbound traffic to aproxy listener to prevent reflection attacks.

        Returns:
            The nftables rules as a string.
        """
        server_ip = self._get_primary_ip()
        ports_clause = ", ".join(self.config.intercept_ports_list)
        excluded_ips = ", ".join(
            [
                "127.0.0.0/8",  # private loopback range
                *self.config.exclude_addresses,
            ]
        )

        return f"""#!/usr/sbin/nft -f
        table ip aproxy
        flush table ip aproxy
        table ip aproxy {{
            set excluded_nets {{
                    type ipv4_addr;
                    flags interval; auto-merge;
                    elements = {{ {excluded_ips} }}
                }}
            chain prerouting {{
                type nat hook prerouting priority dstnat; policy accept;
                ip daddr @excluded_nets return
                tcp dport {{ {ports_clause} }} counter dnat to {server_ip}:{APROXY_LISTEN_PORT}
            }}

            chain output {{
                type nat hook output priority -150; policy accept;
                ip daddr @excluded_nets return
                tcp dport {{ {ports_clause} }} counter dnat to {server_ip}:{APROXY_LISTEN_PORT}
            }}

            chain input {{
                type filter hook input priority filter; policy accept;
                iif "lo" accept
                ip saddr {server_ip} tcp dport {APROXY_LISTEN_PORT} accept
                tcp dport {APROXY_LISTEN_PORT} drop
            }}
        }}
        """

    def _ensure_nftables_installed(self) -> None:
        """Ensure the nft binary is available before applying rules.

        Raises:
            NftApplyError: If installing nftables package fails.
        """
        if Path("/usr/sbin/nft").exists():
            return

        try:
            subprocess.run(["/usr/bin/apt-get", "update"], check=True)  # nosec B603
            subprocess.run(["/usr/bin/apt-get", "install", "-y", "nftables"], check=True)  # nosec B603
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to install nftables package: %s", exc)
            raise NftApplyError(exc, "nftables package installation failed") from exc

    def check_relation_availability(self) -> tuple[ops.model.Relation, ops.model.Binding]:
        """Check if the Juju relation is available for topology resolution.

        Raises:
            RelationMissingError: If the required relation is missing.
            TopologyUnavailableError: If the binding information is unavailable.

        Returns:
            A tuple of the relation and its binding.
        """
        relation = self.charm.model.get_relation(RELATION_NAME)
        binding = self.charm.model.get_binding(RELATION_NAME)

        if not relation:
            raise RelationMissingError(
                f"Missing relation '{RELATION_NAME}' to the principal charm."
            )

        if not binding or binding.network is None:
            raise TopologyUnavailableError(
                f"Relation '{RELATION_NAME}' network not available when trying to get unit IP."
            )

        return relation, binding

    def apply_nft_config(self) -> None:
        """Apply nft config immediately.

        Raises:
            NftApplyError: If applying the nft command fails.
        """
        self._ensure_nftables_installed()

        # Write nft config to disk
        NFT_CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
        NFT_CONF_FILE.write_text(textwrap.dedent(self._render_nft_rules()), encoding="utf-8")

        try:
            subprocess.run(["/usr/sbin/nft", "-f", str(NFT_CONF_FILE)], check=True)  # nosec B603
            logger.info("Applied nftables rules successfully.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to apply nftables rules: %s", e)
            raise NftApplyError(e, str(NFT_CONF_FILE)) from e

    def remove_nft_config(self) -> None:
        """Remove nft table.

        Raises:
            NftCleanupError: If cleaning up the nft command fails.
        """
        try:
            subprocess.run(["/usr/sbin/nft", "flush", "table", "ip", "aproxy"], check=True)  # nosec B603
            subprocess.run(["/usr/sbin/nft", "delete", "table", "ip", "aproxy"], check=True)  # nosec B603
            logger.info("Cleaned up nftables rules.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to clean up nftables rules: %s", e)
            raise NftCleanupError(e, str(NFT_CONF_FILE)) from e

    # ---------------- systemd ----------------

    def persist_nft_config(self) -> None:
        """Ensure nft configuration persistence via systemd.

        This is needed since the nft configuration will be removed on server reboot.
        """
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
        SYSTEMD_UNIT_PATH.write_text(textwrap.dedent(content), encoding="utf-8")
        systemd.service_enable(SYSTEMD_UNIT_PATH.name)
        systemd.service_start(SYSTEMD_UNIT_PATH.name)

    def remove_systemd_unit(self) -> None:
        """Remove systemd unit."""
        systemd.service_stop(SYSTEMD_UNIT_PATH.name)
        systemd.service_disable(SYSTEMD_UNIT_PATH.name)
        SYSTEMD_UNIT_PATH.unlink(missing_ok=True)
