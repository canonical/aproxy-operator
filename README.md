<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Aproxy subordinate charm

<!-- vale Canonical.007-Headings-sentence-case = YES -->

[![CharmHub Badge](https://charmhub.io/aproxy/badge.svg)](https://charmhub.io/aproxy)
[![Publish to edge](https://github.com/canonical/aproxy-operator/actions/workflows/publish_charm.yaml/badge.svg)](https://github.com/canonical/aproxy-operator/actions/workflows/publish_charm.yaml)
[![Promote charm](https://github.com/canonical/aproxy-operator/actions/workflows/promote_charm.yaml/badge.svg)](https://github.com/canonical/aproxy-operator/actions/workflows/promote_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A subordinate charm that transparently intercepts per-unit TCP traffic and forwards it to a target proxy. It deployes the [Aproxy](https://snapcraft.io/aproxy) snap application.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. For Charmed Aproxy, this includes:

- Transparent TCP interception via nftables REDIRECT
- Per-unit forwarding to a configured target proxy
- Configurable domains to be excluded from interception and intercept ports

For information about how to deploy, integrate, and manage this charm, see the Official [aproxy-operator Documentation](https://charmhub.io/aproxy).

## Get started

Below is a guide on how to quickly prepare a Juju environment, deploy and relate aproxy to a principal charm, and operate the charm.

### Set up

Ensure you have a working [Juju](https://documentation.ubuntu.com/juju/latest/tutorial/) environment.  
For quick local testing, you can use [Multipass](https://canonical.com/multipass/install).

### Deploy

To deploy aproxy alongside a principal charm (for example, Ubuntu), you need to integrate the principal charm with aproxy. For successful proxy forwarding, you also need to configure the target proxy address.

```bash
juju deploy ubuntu
juju deploy aproxy
juju integrate aproxy ubuntu
juju config aproxy proxy-address=$TARGET_PROXY:$TARGET_PORT
```

### Basic operations

Update the target proxy address:

```bash
juju config aproxy proxy-address=$MODIFIED_PROXY:$MODIFIED_PORT
```

Exclude domains from interception:

```bash
juju config aproxy exclude-addresses-from-proxy=$EXCLUDED_ADDRESS
```

Stop the aproxy charm's interception of traffic (which disables nftables redirection):

```bash
juju run aproxy/0 stop
```

See the [charmcraft.yaml](https://github.com/canonical/aproxy-operator/blob/main/charmcraft.yaml) file for all configuration options and actions.

## Integrations

The charm is designed to run as a subordinate and integrates with any principal charm that generates outbound TCP traffic.
Relations enable it to transparently forward requests through the configured proxy without modifying the principal charm itself.

See the Charmhub documentation on [integrations](https://charmhub.io/aproxy/integrations) for more details.

## Learn more

- [Read more](https://charmhub.io/aproxy)
- [Troubleshooting](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

## Project and community

- [Issues](https://github.com/canonical/aproxy-operator/issues)
- [Contributing](https://github.com/canonical/aproxy-operator/blob/main/CONTRIBUTING.md)
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- [Launchpad](https://launchpad.net/~canonical-is-devops)

## Licensing and trademark

This charm is licensed under the [Apache License, Version 2.0](https://github.com/canonical/aproxy-operator?tab=Apache-2.0-1-ov-file). Copyright 2025 Canonical Ltd.
