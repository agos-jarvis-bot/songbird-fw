# ADR-0011: One monorepo holds requirements, plans, architecture, schema and code

| | |
|---|---|
| Status | Accepted (retroactive) |
| Date | 2026-10-19 |
| Deciders | Songbird team |
| Related | Project Plan §10; C-005; the archived repositories `songbird-requirements-analysis`, `songbird-architecture`, `songbird-yaml-schema` |

## Context

The project started with five repositories: requirements, architecture, YAML schema, prototypes, site. Traceability — the property this project's engineering method depends on — requires that a requirement, the ADR that interprets it, the schema that encodes it and the code that implements it can change **in the same pull request**, with one review and one CI run. Across repositories every such change is a chain of PRs that can be merged in the wrong order, and the traceability matrix cannot be generated.

## Options considered

**A. Keep separate repositories, link with git submodules or a meta-tool.** Preserves small repos and separate histories. Costs: cross-repo PR chains, submodule pinning overhead, no single issue tracker, no single CI truth.

**B. One monorepo `songbird-fw` with history-preserving import.** *(chosen)*

**C. One monorepo, squash-imported without history.** Simplest import, but the decision history — which this project treats as a first-class artifact (tagged RA versions, ADRs) — would be lost.

## Decision

1. All engineering artifacts live in **`songbird-fw/songbird-fw`**: `docs/` (RA, Project Plan, Test Plan, architecture), `adr/`, `schema/`, and later `cmd/`, `internal/`, `bpf/`, `ui/`, `test/`, `image/` (Project Plan §10).
2. The three source repositories were imported with **full Git history** (`git subtree add`, 2026-10-19) and then archived; earlier RA versions remain reachable through their tags (`ra-v*`).
3. `songbird-prototypes` (experiments with their own lifecycle) and `songbird-site` (website) stay separate; they are not part of the product.
4. One issue tracker, one project board, one CI definition.

## Consequences

**Positive**

- A requirement, its ADR, the schema and the tests can change atomically in one PR — the traceability matrix (Test Plan §4) becomes generable from a single tree.
- One review queue for a two-person team; no cross-repo merge-order hazards.

**Negative**

- CI must be path-filtered (schema workflow already is) or every doc edit runs everything.
- The repository accumulates large histories (prototypes excluded for this reason).

**Documents changed**: Project Plan §10 (layout), the three archived repositories (README pointer here).
