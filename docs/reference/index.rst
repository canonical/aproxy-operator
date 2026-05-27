.. meta::
   :description: Technical reference documentation for the aproxy charm, including actions, configurations, and architecture.

.. _reference_index:

Reference
=========

Technical specifications and architectural details for the aproxy charm serve
as authoritative look-up material when configuring, integrating, or extending
the charm.

.. vale Canonical.013-Spell-out-numbers-below-10 = NO
.. vale Canonical.500-Repeated-words = NO
.. vale Canonical.004-Canonical-product-names = NO

Configuration and operations
----------------------------

Operators control charm behavior through configuration options and Juju
actions.

.. toctree::
    :maxdepth: 1

    Actions <actions>
    Configurations <configurations>

.. vale Canonical.004-Canonical-product-names = YES

Architecture and design
-----------------------

The aproxy charm communicates with other applications through integrations.
Understanding the charm architecture provides the structural context
needed to see how those settings interact at runtime.

.. toctree::
    :maxdepth: 1

    Charm architecture <charm-architecture>
    Integrations <integrations>
