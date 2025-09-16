# Security overview

The aproxy subordinate charm installs and manages the aproxy snap and configures nftables rules to transparently intercept outbound HTTP/HTTPS traffic and forward it through an upstream proxy. Because it manipulates low-level system networking and handles traffic redirection, security considerations are critical.

<!-- Are there upstream security docs that we can point to? If so, include a
sentence like:
For details regarding upstream <charm-name> configuration and broader security
considerations, please refer to the [official <software> documentation](link-to-upstream-docs). -->

## Risks

### Privileged operations

The charm uses snap to install and configure the aproxy snap, which requires system-level permissions.

It directly invokes nftables to configure firewall and redirection rules. Incorrect or malicious configurations could:

- Break system networking.

- Open the system to denial-of-service conditions.

- Allow unintended traffic redirection.

#### Best practices for users:

- Deploy the charm only on trusted workloads where network interception is expected and approved.

- Ensure only administrators with appropriate permissions can change charm configuration (juju config).

- Regularly audit nftables rules on systems where this charm is deployed.

### Proxy reachability

The charm validates whether the configured upstream proxy (proxy-address) is reachable. If it is not, the unit enters a BlockedStatus.

If a misconfigured or malicious proxy is set, sensitive traffic could be redirected to an unintended endpoint.

#### Best practices for users:

- Always configure the charm with a trusted proxy endpoint.

- Use allowlists and monitoring to detect if traffic is being routed unexpectedly.

### Traffic interception

The charm transparently intercepts outbound traffic, which can include sensitive user or application data.

By design, intercepted traffic is redirected through aproxy, which in turn forwards it to an upstream proxy. This may impact confidentiality if the proxy operator is not trusted.

#### Best practices for users:

- Use this charm only in environments where transparent proxying is a compliance or policy requirement.

- Ensure that TLS interception (if enabled upstream) is disclosed, audited, and compliant with local regulations.

### nftables cleanup

On charm removal or stop, nftables rules are flushed. If cleanup fails, stale rules may persist, leaving the system in an insecure or degraded state.

Best practices for users:

- Validate nftables rules after stopping or removing the charm.

- Integrate nftables state checks into monitoring systems.

## Information security
Data confidentiality: All outbound HTTP/HTTPS traffic is routed through aproxy to an upstream proxy. This makes the proxy a critical point for inspecting, logging, or potentially leaking sensitive data.

Availability: If the upstream proxy is unavailable, the charm blocks network access by design (traffic redirection fails), which could cause outages for applications depending on outbound connectivity.

Integrity: nftables rules are automatically managed by the charm. Manual changes to nftables may conflict with charm behavior, leading to inconsistencies in rule enforcement.
