# ADR-0018: Configuration objects follow the Kubernetes resource shape (`apiVersion`/`kind`/`metadata`/`spec`)

| | |
|---|---|
| Status | Accepted (retroactive) |
| Date | 2026-06 (recorded 2026-10-21) |
| Deciders | Songbird team |
| Related | C-005; R-010…R-014.5, R-020.x, R-052; ADR-0001, ADR-0008, ADR-0012; schema/ |

## Context

The configuration is YAML in Git (ADR-0001) and must be versioned, validated, diffable and machine-generated (ADR-0008, ADR-0012). Two shapes were on the table: a FortiGate-like flat `config x / set y` model, or the Kubernetes resource model the team already thinks in.

## Options considered

**A. Flat FortiGate-style documents** (`config firewall policy` blocks translated to YAML). Closest to the UX we imitate, but it has no envelope: no place for `apiVersion`, no per-object metadata (uuid, comment, color), no standard way to mix kinds in one tree, and no ecosystem.

**B. Kubernetes-style resources.** *(chosen)* `apiVersion: config.songbird-fw.com/v1alpha1`, `kind`, `metadata` (name as primary key, generated uuid, comment, color), `spec`. Every editor with the YAML language server gets autocomplete from the JSON Schema; everyone who knows a CRD knows the mental model; `kind` dispatch makes the validator and the Go types obvious.

**C. INI/TOML/HCL.** All weaker for nested structures, comments, and multi-object trees; none has the schema-plus-editor story of JSON Schema over YAML.

## Decision

1. Every configuration object is a resource with envelope `apiVersion` / `kind` / `metadata` / `spec`; kind names are singular PascalCase (`Address`, `RuleSet`, `System`).
2. `metadata.name` is the primary key, human-readable; `uuid` is generated and exists for rename tracking; comments and the Color reference live in metadata, semantics in spec.
3. The `System` object is the single allowed singleton (`name: "system"`); everything else is a named, multi-instance resource.
4. Versioning follows ADR-0008 (`v1alpha1 → v1beta1 → v1` with conversions); the schema is the normative form, semantic rules live in the validator.

## Consequences

**Positive**

- Free tooling: schema-aware completion and inline errors in editors; a validation mental model shared with every Kubernetes practitioner the project wants as contributors.
- The GitOps story (ADR-0001) reads naturally: the repository looks like a cluster's desired state.

**Negative**

- Users coming from FortiGate/pfSense meet a Kubernetes-flavoured file before they meet the UI; mitigated because the UI, not the YAML, is the primary interface, and the example tree ships annotated.

**Documents changed**: none (schema README already carries the conventions; this ADR records the choice and its date).
