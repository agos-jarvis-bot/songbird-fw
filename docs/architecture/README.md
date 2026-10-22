# Architecture

Architectural design of Songbird. Requirements live in [`docs/requirements-analysis.md`](../requirements-analysis.md); the configuration schema in [`schema/`](../../schema/); decision records in [`adr/`](../../adr/).

## Documents

| Document | Content |
|---|---|
| [domain-model.md](domain-model.md) | Configuration objects, relationships and constraints (`DM-NN`) |
| [components.md](components.md) | Component view, interfaces, dependency rules, requirement matrix |
| [reconciliation.md](reconciliation.md) | Reconciliation loop: desired state → validate → compile → apply → observe → status |
| [dataplane.md](dataplane.md) | eBPF Data Plane design |
| [high-lvl-architecture.md](../legacy/high-lvl-architecture.md) | First high-level sketch (superseded by `components.md`) |
| Deployment view | *To be written* |

## Architecture Decision Records

One file per decision. A record is never deleted: when a decision changes, a new ADR supersedes it and the old one gets the status *Superseded by ADR-NNNN*.

### Index

| ADR | Title | Status |
|---|---|---|
| [0001](../../adr/0001-yaml-in-git-source-of-truth.md) | YAML files in Git are the single source of truth for configuration | Accepted |
| [0002](../../adr/0002-forwarding-model.md) | Forwarding model: XDP decides, the kernel forwards, TC rewrites | Proposed |
| [0003](../../adr/0003-own-conntrack.md) | Own connection tracking in BPF maps, without nf_conntrack | Proposed |
| [0004](../../adr/0004-active-flows-on-policy-change.md) | Active Flows no longer permitted are terminated at their next packet | Proposed |
| [0005](../../adr/0005-ipv4-fragments.md) | Non-initial IPv4 fragments are dropped when forwarded | Proposed |
| [0006](../../adr/0006-capacity-limits.md) | Capacity limits of the Data Plane | Proposed |
| [0007](../../adr/0007-reference-platform.md) | Reference platform for development and performance verification | Proposed |
| [0008](../../adr/0008-schema-versioning-and-rollback.md) | Configuration schema versioning, migration and rollback | Proposed |
| [0009](../../adr/0009-secrets-encryption-key.md) | Protection and location of the secrets encryption key | Proposed |
| [0010](../../adr/0010-dnat-in-policy.md) | DNAT is a section of the Policy, matched before translation | Accepted |
| [0011](../../adr/0011-monorepo.md) | One monorepo holds requirements, plans, architecture, schema and code | Accepted (retroactive) |
| [0012](../../adr/0012-canonical-yaml-serialisation.md) | Canonical YAML serialisation and configuration file layout | Accepted |
| [0013](../../adr/0013-minimum-kernel-and-attach-method.md) | Minimum kernel 6.6, TC attached with TCX, XDP native with generic fallback | Proposed |
| [0014](../../adr/0014-dhcp-and-dns-engines.md) | DHCP and DNS engines: in-process libraries or external daemons | Proposed (question open) |
| [0015](../../adr/0015-go-for-the-control-plane.md) | The Control Plane is written in Go | Accepted (retroactive) |
| [0016](../../adr/0016-cilium-ebpf-library.md) | eBPF programs are managed with cilium/ebpf and generated with bpf2go | Accepted (retroactive) |
| [0017](../../adr/0017-hadron-as-the-appliance-os.md) | Hadron (Kairos) is the appliance operating system | Proposed (verification ongoing) |
| [0018](../../adr/0018-crd-style-configuration-objects.md) | Configuration objects follow the Kubernetes resource shape | Accepted (retroactive) |

### Candidate ADRs (not written yet)

- Validation both in the API and in the Reconciler (decided, see components.md).
- Optimistic locking for concurrent edits (decided, see components.md and R-021.5).
- Ownership of network configuration: Songbird or the OS.
- Distribution mechanism: Hadron image upgraded in place, or a custom ISO.


### Statuses

*Proposed* → *Accepted* → (*Deprecated* | *Superseded by ADR-NNNN*). *Rejected* for proposals that were not taken.

### Template

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
