# Charm design

The aproxy charm helps applications that cannot configure an HTTP proxy
themselves, or whose proxy settings are impractical to manage individually.
It redirects selected connections to the aproxy snap, which forwards them
through an existing upstream HTTP proxy. This allows operators to introduce
proxying without changing the principal application.

## Why a subordinate charm?

Aproxy is a machine subordinate: it is attached to a principal application
through Juju's `juju-info` integration and runs alongside each principal
unit. Co-location gives it access to the unit's networking, so it can manage
traffic interception without requiring the principal charm to implement a
proxy integration.

The charm manages the aproxy snap and nftables rules on the machine. The snap
provides the proxying functionality; the charm configures it and maintains the
rules across restarts. An upstream proxy is still required: aproxy is a
forwarder, not a replacement for that proxy.

## How transparent proxying works

The charm configures nftables to redirect matching IPv4 TCP connections to
aproxy. For supported HTTP and TLS connections, the snap reads the HTTP
`Host` header or the TLS server name indication (SNI) to recover the
destination hostname and forwards the connection through the upstream proxy.
Preserving the hostname helps an upstream proxy apply hostname-based access
controls or auditing.

The charm intercepts destination ports 80 and 443 by default. Operators can
change the selected ports and exempt specific IP addresses or networks.
Traffic to local addresses and the loopback range is excluded so that local
services remain accessible. The rules apply at the machine networking level,
not solely to a particular process, so other traffic on the same machine can
also be affected.

## When to use aproxy

Aproxy is useful when workloads need to use a shared upstream proxy but do not
honour proxy configuration. Centralised interception can support egress
policies without modifying each application.

It may be a poor fit if the application already supports an HTTP proxy and
per-application configuration provides sufficient control. Transparent
interception introduces machine-level network rules and an additional service
and proxy dependency. A reachable, trusted upstream proxy is necessary; an
upstream outage can disrupt intercepted connections.

The nftables rules cover IPv4 TCP, not IPv6 or UDP. They do not redirect
traffic on ports outside the configured set or traffic to excluded destinations.
The [aproxy snap](https://github.com/canonical/aproxy) can forward other TCP
connections using HTTP CONNECT to the original IP address, but the upstream
proxy must permit CONNECT to the destination port. Hostname-based forwarding
depends on the destination port and on the application providing a usable
HTTP `Host` header or TLS SNI; otherwise the proxy may receive an IP address
instead of a hostname.

Interception is not a complete egress firewall: traffic outside its scope can
bypass aproxy. Use separate network controls when all egress must be governed.
For further considerations, see the [security overview](security.md). For
configuration details, see [How to configure](../how-to/configure.md).
