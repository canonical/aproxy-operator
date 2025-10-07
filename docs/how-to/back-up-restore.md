# How to back up and restore

The aproxy subordinate charm does not maintain application data or databases of its own. Since the charm is stateless apart from configuration, there is no persistent data that needs a traditional backup/restore procedure.

## Back up

To preserve the state of the deployment, back up the following:

1. **Charm configuration**

   Run:

   ```bash
   juju config aproxy
   ```

   Save the output, including:

   - `proxy-address`
   - `exclude-addresses-from-proxy`
   - `intercept-ports`

2. **System snapshot (optional)**

   If required for compliance, you can also back up system-level state:

   - List of installed snaps (`snap list`)
   - nftables configuration (`sudo nft list ruleset`)

## Restore

To restore the charm to its previous state:

1. **Redeploy the charm**

   ```bash
   juju deploy aproxy --config proxy-address=<saved-address> \
                      --config exclude-addresses-from-proxy=<saved-exclude-addresses-from-proxy> \
                      --config intercept-ports=<saved-ports>
   ```

2. **(Optional) Reapply system snapshot**

   - If you captured nftables or snap state for compliance, restore them with:

     ```bash
     sudo snap install aproxy --edge
     sudo nft -f <saved-ruleset-file>
     ```

In most cases, reapplying the saved Juju configuration is sufficient. The charm will automatically reinstall the snap and regenerate nftables rules.
