# ADR-0012: Canonical YAML serialisation and configuration file layout

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-19 |
| Deciders | Songbird team |
| Related | R-020, R-020.1, R-020.7, R-052; C-005; ADR-0001; schema README design decisions 1 and 14 |

## Context

The configuration is YAML in Git (ADR-0001), so its text form *is* the review surface: diffs, conflicts, blame and the UI's own commits all happen on these bytes. Without one canonical form, the export would reformat user files, diffs would be noisy, and two tools writing the same object could produce different bytes for the same meaning.

## Options considered

**A. Free-form YAML; the schema only validates semantics.** Minimal tooling, but diffs depend on who (or what) wrote the file last, and plain scalars make types ambiguous (`yes`, `010`, `1e3`).

**B. One canonical serialisation for everything the system writes; anything valid accepted on input.** *(chosen)*

**C. Canonical form enforced on input too (reject non-canonical files).** Rejected by the team on 2026-10-19: a user must be free to keep several objects in one file; only the export normalises.

## Decision

1. **Every string value is double-quoted** (`kind: "Address"`); keys unquoted; 2-space indent; block style with inline `{}` / `[]` only for short leaf maps and lists. Numbers and booleans stay bare.
2. **Export layout, one object per file** (R-020.7): `system.yaml` at the root (the `System` singleton) and one directory per kind in kebab-case plural — `interfaces/`, `zones/`, `addresses/`, `address-groups/`, `services/`, `service-groups/`, `colors/`, `rulesets/` — file name = `metadata.name` + `.yaml`.
3. **Input is unconstrained**: multi-document files and any directory layout are valid; the validator never rejects a file for its layout (R-020.7). After the next export the tree is back in canonical form.
4. The formatter is part of `songbird export` and of the UI's commit path; the schema does not and cannot enforce quoting, so the formatter is the single writer of canonical bytes.

## Consequences

**Positive**

- Diffs are stable and object-scoped; conflicts are confined to the object that changed; `songbird export` output is byte-reproducible (round-trip test, R-020.1).
- Type ambiguity of plain YAML scalars disappears from everything the system writes.

**Negative**

- User-maintained non-canonical files are reformatted on first export; acceptable because the layout was never promised as stable input.
- File name = object name is convention, not yet enforced; a `--strict-layout` validator flag remains a candidate (schema README open question 8).

**Documents changed**: schema README (design decisions 1, 14; open question 3 resolved), RA R-020.7.
