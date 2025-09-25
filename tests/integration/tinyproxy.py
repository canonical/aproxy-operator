# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Deploy tinproxy service."""

import json
import textwrap

import jubilant


def deploy_tinyproxy(juju: jubilant.Juju) -> str:
    """Deploy a tinyproxy service into the Juju model using any-charm.

    Args:
        juju: The Juju controller instance.

    Returns:
        Proxy URL (http://<unit-ip>:8888).
    """
    any_charm_py = textwrap.dedent(
        """
    import subprocess
    import textwrap

    import ops
    from any_charm_base import AnyCharmBase


    class AnyCharm(AnyCharmBase):
        def __init__(self, *args):
            super().__init__(*args)
            self.framework.observe(self.on.install, self._on_install)

        def _on_install(self, _):
            self.unit.status = ops.MaintenanceStatus("downloading tinyproxy")
            subprocess.check_call(["apt-get", "update"])
            subprocess.check_call(["apt-get", "install", "-y", "tinyproxy"])

            self.unit.status = ops.MaintenanceStatus("configuring tinyproxy")
            with open("/etc/tinyproxy/tinyproxy.conf", "w") as f:
                f.write(
                    textwrap.dedent(
                        \"\"\"
                        User tinyproxy
                        Group tinyproxy
                        Listen 0.0.0.0
                        Port 8888
                        Timeout 600
                        DefaultErrorFile "/usr/share/tinyproxy/default.html"
                        StatFile "/usr/share/tinyproxy/stats.html"
                        LogFile "/var/log/tinyproxy/tinyproxy.log"
                        LogLevel Info
                        PidFile "/run/tinyproxy/tinyproxy.pid"
                        Allow 0.0.0.0/0
                        AllowConnect 443
                        AllowConnect 563
                        MaxClients 100
                        \"\"\"
                    )
                )

            subprocess.check_call(["systemctl", "restart", "tinyproxy"])
            self.unit.set_ports(8888)
            self.unit.status = ops.ActiveStatus()
    """
    )

    # Deploy any-charm with our custom inline tinyproxy charm
    juju.deploy(
        "any-charm",
        "tinyproxy",
        channel="latest/edge",
        config={"src-overwrite": json.dumps({"any_charm.py": any_charm_py})},
    )

    # Wait until the service is up
    juju.wait(jubilant.all_active, timeout=10 * 60)

    # Grab unit IP
    units = juju.status().get_units("tinyproxy")
    leader = next(name for name, u in units.items() if u.leader)
    unit_ip = units[leader].address or units[leader].public_address
    return unit_ip
