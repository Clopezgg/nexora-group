# NEXORA — IaC Security Baseline

This document records existing infrastructure findings discovered when the
NEXORA Ultra security stack was introduced.

They are **not considered fixed**.

The CI policy is progressive:

1. Findings already present in the PR base are recorded as baseline debt.
2. Any newly introduced Checkov finding blocks the pull request.
3. Existing debt is remediated deliberately without breaking the deployed
   architecture or silently increasing Azure cost.

## Existing Azure areas discovered

### Key Vault

Existing policies include:

- firewall/network ACL hardening;
- public network access;
- secret expiration metadata;
- secret `contentType` metadata.

Changing Key Vault to private-only access must not be done blindly because
Azure Container Apps must retain a valid network path to Key Vault.

### Storage

Existing policies include:

- default network access rule;
- naming analysis;
- replication level.

`Standard_LRS` is currently intentional in the source because NEXORA's
architecture prioritizes the lowest reasonable Azure cost. Changing
replication tier can increase recurring cost and therefore requires an
explicit architectural/cost decision.

## Rule

No finding is waived merely to obtain a green CI result.

Where a policy conflicts with the current network/cost architecture, the
finding remains documented debt while **new regressions are prohibited**.
