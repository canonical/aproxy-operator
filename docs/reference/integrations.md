# Integrations

The aproxy subordinate charm is designed as a subordinate. This means it must be deployed in relation to a principal charm, where it co-locates on the same unit and manages transparent proxying for that workload.

It does not expose or consume custom relations beyond its subordinate attachment, but it integrates with principal charms by intercepting their outbound traffic.

## `juju-info`

_Interface_: juju-info  
_Supported charms_: Any principal charm that supports subordinate relations (e.g., web applications, API services, databases with outbound TCP calls).

The `juju-info` interface is a special built-in relation in Juju.

All charms implicitly provide a `juju-info` endpoint, even though it does not appear in their `charmcraft.yaml`.

This is why you can integrate aproxy with any principal charm even if you don’t see `juju-info` listed in the principal’s metadata.

Example integration command using the WordPress charm:

```
juju deploy ubuntu
juju deploy aproxy --config proxy-address=<target.proxy>
juju integrate ubuntu aproxy
```
