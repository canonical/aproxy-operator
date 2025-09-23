<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Aproxy operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) deploying and managing the [aproxy snap](https://snapcraft.io/install/aproxy/ubuntu) as a subordinate machine charm.

The aproxy charm installs and configures the aproxy snap and applies nftables rules to transparently intercept outbound HTTP/HTTPS traffic from a principal charm, forwarding it through an upstream proxy.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. 
For aproxy, this includes:

- Installing and configuring the aproxy snap.

- Enforcing nftables rules to transparently redirect outbound traffic.

- Forwarding HTTP/HTTPS requests through a configurable upstream proxy.

- Supporting exclusions for specific destinations (`no-proxy`).

- Configurable interception ports (`intercept-ports`).

The aproxy charm is a subordinate and can be attached to any principal application to ensure its outbound traffic is transparently proxied. It runs on machines hosting the principal charm and is compatible with a wide range of Juju-managed environments.

This charm makes operating aproxy simple and straightforward for DevOps or SRE teams through Juju’s clean interface, ensuring consistent policy enforcement for egress traffic without requiring per-application configuration.

## In this documentation

| | |
|--|--|
|  [Tutorials](https://charmhub.io/aproxy/docs/tutorial)</br>  Get started - a hands-on introduction to using the charm for new users </br> |  [How-to guides](https://charmhub.io/indico/docs/how-to-contribute) </br> Step-by-step guides covering key operations and common tasks |
| [Reference](https://charmhub.io/aproxy/docs/reference-actions) </br> Technical information - specifications, APIs, architecture | [Explanation](https://charmhub.io/aproxy/docs/explanation-charm-architecture) </br> Concepts - discussion and clarification of key topics  |

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach
to the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation.
See [How to contribute](https://charmhub.io/aproxy/docs/contribute) for more information.


If there's a particular area of documentation that you'd like to see that's missing, please 
[file a bug](https://github.com/canonical/aproxy-operator/issues).

## Project and community

The aproxy operator is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- [Contribute](https://charmhub.io/aproxy/docs/contribute)

Thinking about using the aproxy operator for your next project? 
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

# Contents

1. [How-to]()
  1. [Integrate with COS](how-to/integrate-with-cos.md)
  1. [Back up and restore](how-to/back-up-restore.md)
  1. [Upgrade](how-to/upgrade.md)
  1. [Contribute](how-to/contribute.md)
1. [Reference]()
  1. [Actions](reference/actions.md)
  1. [Configurations](reference/configurations.md)
  1. [Integrations](reference/integrations.md)
  1. [Metrics](reference/metrics.md)
1. [Explanation]()
  1. [Charm architecture](explanation/charm-architecture.md)
  1. [Security](explanation/security.md)
1. [Release notes]()
  1. [Overview](release-notes/landing-page.md)
