# Architecture Decision Records

One file per decision. A record is never deleted: when a decision changes, a new ADR supersedes it and the old one gets the status *Superseded by ADR-NNNN*.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-yaml-in-git-source-of-truth.md) | YAML files in Git are the single source of truth for configuration | Accepted |
| [0002](0002-forwarding-model.md) | Forwarding model: XDP decides, the kernel forwards, TC rewrites | Proposed |
| [0003](0003-own-conntrack.md) | Own connection tracking in BPF maps, without nf_conntrack | Proposed |
| [0004](0004-active-flows-on-policy-change.md) | Active Flows no longer permitted are terminated at their next packet | Proposed |
| [0005](0005-ipv4-fragments.md) | Non-initial IPv4 fragments are dropped when forwarded | Proposed |
| [0006](0006-capacity-limits.md) | Capacity limits of the Data Plane | Proposed |
| [0007](0007-reference-platform.md) | Reference platform for development and performance verification | Proposed |
| [0008](0008-schema-versioning-and-rollback.md) | Configuration schema versioning, migration and rollback | Proposed |
| [0009](0009-secrets-encryption-key.md) | Protection and location of the secrets encryption key | Proposed |

## Candidate ADRs (not written yet)

- Validation both in the API and in the Reconciler (decided, see components.md).
- Optimistic locking for concurrent edits (proposed in components.md).
- DHCP and DNS engines: in-process or external daemons.
- Ownership of network configuration: Songbird or the OS.
- Distribution mechanism: Hadron image upgraded in place, or a custom ISO.
- Retroactive records for choices already made: Go, `cilium/ebpf`, Hadron, CRD-style YAML.

## Statuses

*Proposed* → *Accepted* → (*Deprecated* | *Superseded by ADR-NNNN*). *Rejected* for proposals that were not taken.

## Template

```markdown
# ADR-NNNN: <decision, stated as a sentence>

| | |
|---|---|
| Status | Proposed |
| Date | YYYY-MM-DD |
| Deciders | |
| Related | <requirements, constraints, documents> |

## Context
What forces the decision; facts, not opinions.

## Options considered
Each option with its main pros and cons.

## Decision
What is decided, precisely enough to verify.

## Consequences
Positive, negative, and what is left to decide.

## Verification (optional)
How we will know the decision holds.
```
