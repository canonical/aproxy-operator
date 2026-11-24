# Charm design

The aproxy charm helps applications that cannot configure or manage proxy
settings themselves. It redirects selected connections to the aproxy snap,
which forwards them through an existing upstream proxy. This allows operators
to introduce proxying without changing the principal application.

## Why a subordinate charm?

Aproxy is a machine subordinate: it is attached to a principal application
through Juju's `juju-info` integration and runs alongside each principal
unit. Co-location lets aproxy intercept traffic without requiring the
principal charm to manage any proxy configuration.

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
services remain accessible.

## When to use aproxy

Aproxy is useful when workloads need to use a shared upstream proxy but do not
support proxy configuration. It it less useful if the application already supports
proxy configuration management, as transparent interception introduces
machine-level network rules and an additional service dependency.
