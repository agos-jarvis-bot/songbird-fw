# ADR-0001: YAML files in Git are the single source of truth for configuration

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | C-005, R-020, R-020.1, R-021, R-023.3, R-033.1, R-035; components.md (Config Manager, Reconciler) |

## Context

Songbird needs one place where the desired configuration lives: Interfaces, Zones, Policies, objects, services, Users. The Web UI, the CLI, the GitOps workflow (R-021, R-040–R-042), import and export (R-020, R-020.1), HA (R-023.3) and crash recovery (R-033.1) all read or write it. If more than one store holds configuration, they will drift apart and every feature must decide which one is right.

## Options considered

**A. Relational database (e.g. SQLite) as primary store, YAML as export format.** Familiar for UI development and queries. But every change must be mirrored to YAML for Git, two stores must be kept consistent, and diff, review and revert happen on a derived copy.

**B. Embedded key-value store (bbolt, etcd).** Transactional, but the same duplication problem as A, plus a format nobody can read or review.

**C. YAML files in a local Git repository as the only store.** *(chosen)*

## Decision

1. The configuration is a set of YAML files in a **local Git repository** on persistent storage. It is the **only** persistent store of configuration (C-005).
2. The Web UI and the CLI **edit those files** through the API and the Config Manager. There is no SQL database or other configuration store.
3. **Every saved change is one commit** with a structured message (R-021). Rollback is a new commit that restores a previous revision.
4. **Runtime state is separate and ephemeral**: connection tracking, NAT bindings, eBPF maps, sessions and caches live in memory and are rebuilt from the configuration. Logs (Traffic Log, Audit Log) are persistent but are records, not configuration.
5. The Reconciler always derives the running state from the repository (`HEAD`), never the other way around.

## Consequences

**Positive**

- Diff, review, history, blame and revert come from Git for free; GitOps (R-021.x, R-040–R-042) is the native workflow, not an add-on.
- Import and export are trivial: the export is the repository content (R-020, R-020.1).
- Crash recovery and HA reduce to "apply `HEAD`" (R-033.1, R-023.4).
- Configuration can be validated offline in CI with `songbird validate` (R-052).

**Negative**

- No query engine: the Control Plane loads the whole configuration in memory to answer the UI. Acceptable at appliance scale (thousands of objects), to be confirmed with R-048.
- Concurrent edits need explicit handling: optimistic locking on the revision in the Config Manager (components.md).
- Secrets cannot be stored in clear in files that travel: see ADR-0009.
- Schema changes need migrations of files in the repository: see ADR-0008.

**To decide later**

- Whether DHCP leases are persistent state (they are not configuration, and do not belong in Git).
- The file layout (one file per object or per kind), in the YAML schema repository.
