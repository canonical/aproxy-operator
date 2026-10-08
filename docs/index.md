<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Aproxy operator

<!-- vale Canonical.007-Headings-sentence-case = YES -->

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) deploying and managing the [aproxy snap](https://snapcraft.io/install/aproxy/ubuntu) as a subordinate machine charm.

The aproxy charm installs and configures the aproxy snap and applies nftables rules to transparently intercept outbound TCP traffic from a principal charm, forwarding it through an upstream proxy.

The charm supports:

- Installing and configuring the aproxy snap.
- Enforcing nftables rules to transparently redirect outbound traffic.
- Forwarding TCP requests through a configurable upstream proxy.
- Supporting exclusions for specific destinations (`exclude-addresses-from-proxy`).
- Configurable interception ports (`intercept-ports`).

The aproxy charm is a subordinate and attaches to a principal application. It runs on machines hosting the principal charm.

DevOps or SRE teams can manage aproxy through Juju without requiring per-application proxy configuration.

## In this documentation

| | |
| --- | --- |
| **Get started** | [Deploy the aproxy subordinate charm](https://charmhub.io/aproxy/docs/tutorial) |
| **Deployment** | [Configure the upstream proxy](https://discourse.charmhub.io/t/aproxy-operator-documentation-how-to-configure/19043#p-39664-proxy-address-4) \| [Configuration options](https://charmhub.io/aproxy/configure) \| [Principal charm integration](https://charmhub.io/aproxy/docs/integrations) |
| **Operations** | [Upgrade](https://charmhub.io/aproxy/docs/upgrade) \| [Back up and restore](https://charmhub.io/aproxy/docs/back-up-restore) \| [Actions](https://charmhub.io/aproxy/actions) |
| **Traffic interception** | [Choose which ports to intercept](https://discourse.charmhub.io/t/aproxy-operator-documentation-how-to-configure/19043#p-39664-intercept-ports-6) \| [Exclude destinations from interception](https://discourse.charmhub.io/t/aproxy-operator-documentation-how-to-configure/19043#p-39664-exclude-addresses-from-proxy-5) |
| **Design** | [Charm architecture](https://charmhub.io/aproxy/docs/architecture) |
| **Security** | [Security overview](https://charmhub.io/aproxy/docs/security) |

## How this documentation is organized

This documentation uses the [Diátaxis documentation structure](https://diataxis.fr/).

- The [Tutorial](https://charmhub.io/aproxy/docs/tutorial) takes you step-by-step through a basic deployment of the aproxy charm.
- **How-to guides** assume basic familiarity with aproxy and provide step-by-step instructions for specific tasks, such as [configuring the charm](https://charmhub.io/aproxy/docs/configure), [upgrading](https://charmhub.io/aproxy/docs/upgrade), and [contributing](https://charmhub.io/aproxy/docs/contribute).
- **Reference** provides technical information to consult as needed. Use it to look up [configuration options](https://charmhub.io/aproxy/configure), [actions](https://charmhub.io/aproxy/actions), and [integration details](https://charmhub.io/aproxy/docs/integrations).
- **Explanation** provides background and context to help you understand the charm, including [security considerations](https://charmhub.io/aproxy/docs/security).
- **Release notes** are not yet available for individual revisions. The [release policy](https://github.com/canonical/aproxy-operator/blob/main/docs/release-notes/landing-page.md) is available in the repository.

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

1. [Tutorial](tutorial.md)
1. [How-to](how-to)
  1. [Back up and restore](how-to/back-up-restore.md)
  1. [Configure](how-to/configure.md)
  1. [Contribute](how-to/contribute.md)
  1. [Integrate with COS](how-to/integrate-with-cos.md)
  1. [Upgrade](how-to/upgrade.md)
1. [Reference](reference)
  1. [Actions](reference/actions.md)
  1. [Configurations](reference/configurations.md)
  1. [Integrations](reference/integrations.md)
  1. [Charm architecture](reference/charm-architecture.md)
1. [Explanation](explanation)
  1. [Security](explanation/security.md)
1. [Release notes](release-notes)
  1. [Overview](release-notes/landing-page.md)
