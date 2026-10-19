# ADR-0008: Configuration schema versioning, migration and rollback

| | |
|---|---|
| Status | Proposed |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | R-019, R-020.2, R-021, R-023.3, R-033.1, C-005; components.md (Config Manager, Reconciler, Updater) |

## Context

Songbird updates are atomic and use two system versions, A and B (R-019): the new version boots, and if it fails, the previous one runs again. The configuration is a Git repository on persistent storage, separate from the system image, so it survives updates (C-005).

This creates two problems:

1. **Forward**: the new version must read a configuration written by an older version.
2. **Backward**: after a rollback, the older version must run with a repository that the newer version may already have migrated or modified.

Further constraints:

- Validation is strict (R-020.2): a file that does not match the schema is **rejected**, not tolerated. Unknown fields or versions are therefore errors.
- After an unexpected restart the system must restore the last valid configuration within 30 s, without manual intervention (R-033.1).
- In a High Availability pair both nodes use the same remote repository and branch (R-023.3), and during an update the two nodes may temporarily run different versions.
- Every change is a Git commit (R-021). History must not be rewritten.

## Decision drivers

- A failed update must leave the previous version running with a **valid configuration** (R-019).
- No manual intervention in the common case.
- No second source of truth for configuration (C-005).
- Simple enough to be tested automatically in CI.

## Options considered

**A. Permanent compatibility.** The schema never changes incompatibly: every release reads every older and newer configuration.
Rejected: it conflicts with strict validation and constrains the design for years; unrealistic before 1.0.

**B. Migrate in place, no fallback.** The new version migrates the repository at startup. After a rollback, the older version refuses the newer schema and waits for the administrator.
Rejected: a rollback would leave the appliance without a working configuration, violating R-019 and R-033.1.

**C. Migrate in place, with a pre-migration tag and automatic fallback to the newest compatible revision.** *(chosen)*

**D. Migrate on a separate Git branch until the update is confirmed.**
Rejected: it complicates GitOps synchronisation (which branch is pushed, and which one the HA peer follows) and the mental model of the administrator.

**E. Keep one configuration copy per schema version outside Git.**
Rejected: it creates several sources of truth (violates C-005).

## Decision

1. **Schema version.** The repository records one integer `schemaVersion` at a fixed location (the exact file is defined in the YAML schema repository). Each Songbird release has a `CurrentSchema = N` and can read any schema ≤ N through migrations. It never reads a schema > N.
2. **Increment rule.** Any schema change increments the version, including added optional fields, because strict validation makes them invalid for the previous release. This is conservative and may be relaxed after 1.0.
3. **Migrations.** For each increment there is one pure function `N → N+1`, deterministic and idempotent, tested with fixture pairs (`T-U`). Migrations are chained, so skipping releases is supported. They live in the Config Manager as a dedicated migration step, outside the Validator.
4. **At startup** the Config Manager compares the repository's schema version `M` with `N`:
   - **`M == N`**: nothing to do.
   - **`M < N`** (the system was updated): tag the current `HEAD` as `pre-schema-<N>`, run the migration chain, validate the result, and record it as **one commit** "Migrate schema M→N". If migration or validation fails, nothing is committed and the Reconciler does not apply; the failure counts as an unhealthy update (point 5).
   - **`M > N`** (the system was rolled back): walk back the history to the newest revision whose schema is ≤ N, and record **a new commit** that restores its tree, with a message listing the revisions that are being set aside. History is never rewritten. The Config Manager writes an Audit Log entry and raises an alert (R-030).
5. **Update confirmation.** An update is considered successful only when the Reconciler has applied the migrated configuration and the Observer reports healthy. If not, the `UpdateBackend` reverts to the previous version, which then follows the `M > N` path above. This requires the backend to support health-confirmed activation (to be verified in the deployment view).
6. **High Availability.** Migration commits are **not pushed** automatically to a remote shared with a peer node. They are pushed only after the peer runs a compatible version. The mechanism is deferred to the HA design (R-023 is Could).

## Consequences

**Positive**

- A failed update leaves the previous version running with a valid configuration (R-019, R-033.1).
- Nothing is deleted: set-aside changes remain in history and can be recovered by hand.
- Rollback reuses the normal mechanism of a revert commit, so the pipeline needs no special case.

**Negative**

- Changes made with the new version after the migration are **not** part of the running configuration after a rollback. The administrator is told through the Audit Log and an alert.
- Every release that touches the schema must ship a migration, and a fixture for it.
- The strict rule produces more version increments than strictly necessary.

**Neutral / to define**

- The location of the `schemaVersion` marker, and whether a Git tag or a file field is used for `pre-schema-<N>`, are decided in the YAML schema and Detailed Design.
- The behaviour depends on the distribution mechanism chosen (in-place A/B upgrade or custom ISO): the `UpdateBackend` interface hides it, but confirmed activation must be offered by every backend.

## Verification

- `T-U`: each migration against fixtures; chain `N-2 → N`.
- `T-S`: install version N-1 with a reference configuration, update to N, check that the configuration is migrated and applied.
- `T-S`: after the update, roll back to N-1 and check that the fallback commit is created, the old configuration is applied and the Audit Log entry exists.
- Extends the verification of R-019 (power loss during an update).

## Impact on other documents

- **RA**: new requirement on schema versioning and migration (suggested Must); extend the verification of R-019.
- **components.md**: Config Manager gains the migration step; Updater depends on health-confirmed activation.
- **YAML schema**: define the `schemaVersion` marker.
