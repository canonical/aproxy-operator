# How to configure

This guide explains how to configure the aproxy charm to control how traffic is intercepted and forwarded through a target proxy.

## Overview

The aproxy charm provides several configuration options that control how outbound traffic is handled, which addresses bypass the proxy, and which ports are intercepted.

These configurations can be applied:

- During deployment (using `juju deploy --config`), or
- After deployment (using `juju config`).

Example:

```bash
juju config aproxy proxy-address="1.2.3.4:8080"
```

## Configuration options

There are three configuration options available: `proxy-address`, `exclude-addresses-from-proxy`, and `intercept-ports`.

### `proxy-address`

Specifies the target proxy IP address and port for traffic forwarding.

- Format: `"IP:PORT"` or `"IP"`
- Example:

  - `1.2.3.4:8888`
  - `1.2.3.4` (defaults to port `80`)

If no value is provided:

- The charm will attempt to use the principal charm’s `juju-https-proxy` or `juju-http-proxy` relation data.
- If the proxy relation is unavailable, the charm will remain in a `BlockedStatus` until a valid configuration is provided.

Usage Example:

```bash
juju config aproxy proxy-address="10.0.0.5:8080"
```

### `exclude-addresses-from-proxy`

Comma-separated list of IP addresses or hostnames that should bypass the proxy. When this option is set, nftables rules are updated so that outbound traffic to the specified addresses is exempted from proxy interception.

- Default: `"127.0.0.1"`
- Useful for excluding local or internal addresses that should bypass the proxy.

Usage Example:

```bash
juju config aproxy exclude-addresses-from-proxy="127.0.0.1,example.local"
```

### `intercept-ports`

Defines which ports are intercepted and forwarded through the proxy.

This field supports flexible input patterns:

<!-- vale Canonical.013-Spell-out-numbers-below-10 = NO -->

| Type            | Example           | Description                            |
| --------------- | ----------------- | -------------------------------------- |
| Single port     | `80`              | Intercepts traffic on port 80          |
| Multiple ports  | `80,443,8080`     | Intercepts several ports               |
| Range           | `1024-2048`       | Intercepts all ports from 1024 to 2048 |
| Multiple ranges | `80-90,1024-2048` | Combines ranges and specific ports     |
| All ports       | `ALL`             | Intercepts all TCP ports (1–65536)     |

<!-- vale Canonical.013-Spell-out-numbers-below-10 = YES -->

- Default: `"80,443"`

Usage Example:

```bash
juju config aproxy intercept-ports="80,443,8080-8090"
```

## Example: full configuration

Below is a sample configuration command that sets all options explicitly:

```bash
juju config aproxy \
  proxy-address="10.10.10.5:8080" \
  exclude-addresses-from-proxy="127.0.0.1,10.10.10.0/24" \
  intercept-ports="80,443,8080-8090"
```

After applying the configuration, the charm will:

1. Validate the provided settings.
2. Configure the Aproxy snap.
3. Apply nftables rules to redirect outbound traffic as specified.
4. Report an `ActiveStatus` once setup completes successfully.

## Troubleshooting

If the configuration is invalid or incomplete, the charm may enter a `BlockedStatus` with an error message such as:

```
BlockedStatus: Invalid charm configuration: missing proxy address
```

Common fixes:

- Verify that the `proxy-address` and `exclude-addresses-from-proxy` consist of valid IP or hostname.
- Ensure that the `intercept-ports` field uses valid syntax (no spaces, only commas and dashes).
- Check that your relation data is correctly set if relying on `juju-http-proxy` or `juju-https-proxy`.

## Related commands

- View current configuration:

  ```bash
  juju config aproxy
  ```

- Reset a configuration option to default:

  ```bash
  juju config aproxy proxy-address=
  ```

- Check charm status:

  ```bash
  juju status aproxy
  ```
