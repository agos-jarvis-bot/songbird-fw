# ADR-0009: Protection and location of the secrets encryption key

| | |
|---|---|
| Status | Proposed |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | R-020.5, R-035.1, R-021.3, R-021.4, R-030, R-043.4, R-023.3, C-002, C-005; ADR-0008; components.md (Config Manager, Audit Log) |

## Context

The configuration contains secrets: Git SSH keys and access tokens (R-021.3, R-021.4), SMTP passwords and webhook or Telegram tokens (R-030), DNS provider credentials for ACME (R-038.3), and the signing key of session tokens (R-043.4). R-020.5 requires them to be **encrypted at rest**, with an authenticated scheme (AEAD) and **the key not stored alongside the data**. The Audit Log must also be encrypted at rest (R-035.1).

Two facts shape the problem:

1. **Secrets travel.** The configuration is a Git repository that may be pushed to a remote (R-021.1), exported (R-020.1) and shared by two HA nodes (R-023.3). A secret in the repository is therefore copied to places that are not the appliance, so protecting the disk alone is not enough.
2. **Unattended boot.** After a crash or reboot the appliance must recover within 30 s, without manual intervention (R-033.1). A key that needs a human at boot is not acceptable as the default.

The platform is immutable and persistent data lives on one partition (`/usr/local`, label `COS_PERSISTENT`). According to the Kairos documentation, this partition can be encrypted with LUKS, with the key held in a TPM; Trusted Boot additionally requires Secure Boot and a TPM. Whether this works on the final distribution (Hadron-based image or custom ISO) and on virtual machines without a virtual TPM is **not yet verified**.

## Decision drivers

- Secrets must stay protected when the repository leaves the appliance (remote push, export, backup).
- Unattended boot must work.
- Protection must degrade gracefully on hardware without a TPM (home labs, VMs).
- The scheme must be simple enough to review (verification of R-020.5 is by inspection and analysis).
- A lost or rotated key must not make the whole configuration unreadable without recovery.

## Options considered

**A. Rely on full-disk encryption only.** Encrypt `COS_PERSISTENT` and store secrets in clear in the repository.
Rejected: once the partition is mounted, secrets are in clear, and they are in clear in every push, export and backup. It fails the first driver and arguably R-020.5.

**B. Application-level encryption, key as a file on the persistent partition.** Secrets are encrypted in the YAML; the key is a root-only file outside the repository.
Partly accepted: it protects pushes, exports and backups. It does **not** protect against someone who steals the disk (key and data are on the same medium), and that is the case R-020.5 ("key not stored alongside data") seems to target.

**C. Key derived from an administrator passphrase entered at boot.**
Rejected as the default: it breaks R-033.1. Acceptable as an optional hardening mode.

**D. Application-level encryption, key sealed to the TPM.** The key is generated at first boot and bound to the TPM, so the disk alone is useless.
Accepted where a TPM exists; not usable everywhere (VMs, some hardware).

**E. External key management (KMS, Vault).**
Rejected for 1.0: it adds a mandatory external service to an appliance meant to be self-contained.

## Decision

Two layers, combined (B + D, with A as a recommended addition):

1. **Application-level AEAD for every secret value.** In the YAML each secret is stored as an opaque string with a version and a key identifier (for example `enc:v1:<keyid>:<nonce+ciphertext>`). The algorithm is an AEAD (AES-256-GCM or XChaCha20-Poly1305, to be fixed in the Detailed Design), with the object path as associated data so that a ciphertext cannot be moved to another field. Plaintext never appears in the repository, in exports, in pushes or in the Audit Log.
2. **A single master key, never in the repository.** It is generated at first boot with a cryptographically secure generator and stored **outside the Git working tree and outside any exported path**, in a root-only location under the persistent area (exact path in the deployment view). Subkeys for secrets and for the Audit Log are derived from it (HKDF), so one key serves both R-020.5 and R-035.1.
3. **Hardware protection when available.** If a TPM 2.0 is present, the master key is stored **sealed** to it, so the disk alone does not reveal it. Without a TPM the key is a protected file and the appliance reports a visible *degraded protection* status (Observer and UI). This is an explicit, documented trade-off, not a hidden one.
4. **Disk encryption is recommended, not required.** Where TPM and Secure Boot exist, encrypting `COS_PERSISTENT` (Kairos kcrypt) is a complementary layer and is documented as such. Songbird does not depend on it.
5. **Key recovery and portability.**
   - *Backup export.* The configuration export (R-020.1) keeps secrets encrypted under the master key and is therefore unreadable elsewhere. For moving to another appliance, the administrator can create a **recovery bundle**: the master key encrypted with a passphrase (memory-hard KDF such as Argon2id), downloadable only after re-authentication and written to the Audit Log.
   - *Rotation.* The key identifier in each ciphertext allows a new key to be introduced and secrets re-encrypted progressively. Rotation is a Config Manager operation and produces one commit.
   - *Loss.* If the key is lost, secrets cannot be recovered: the rest of the configuration remains valid, and the administrator re-enters the secrets. The UI must make this case explicit.
6. **High Availability.** Both nodes need the same key to read a shared repository (R-023.3). Provisioning the key to the second node uses the recovery bundle at pairing time. Defined in the HA design (R-023 is Could).
7. **Factory reset** destroys the key and therefore all stored secrets.

## Consequences

**Positive**

- Pushes, exports, backups and the remote repository never expose a secret in clear.
- Unattended boot works (R-033.1), also without a TPM.
- One key and one mechanism for both secrets and Audit Log.
- Rotation and portability are designed in from the start through the key identifier and the recovery bundle.

**Negative**

- Without a TPM, an attacker with physical access to the disk can read the key and the secrets. The scheme protects the repository's journey, not a stolen disk in that case.
- The Config Manager must handle encryption, rotation and the recovery bundle: more code in a security-sensitive component.
- Ciphertext in the YAML makes diffs of secrets meaningless (a changed secret shows as a changed blob).

**Interpretation of R-020.5**

I read "key not stored alongside data" as: *the key is never in the repository or in anything that leaves the appliance*, which this decision guarantees, and *the key is not readable from the disk alone*, which holds only with a TPM. The team should state which reading the RA intends, and either accept the no-TPM limitation or add a requirement for hardware key protection on the reference platform (C-003).

## Verification

- `I`: no plaintext secret in the repository, in an export, in the Audit Log or in logs (search for known test secrets), as in R-020.5.
- `A`: review of the algorithm, nonce handling, associated data, key derivation and storage (R-020.5).
- `T-U`: round trip encryption/decryption; ciphertext moved to another path fails to decrypt; tampered ciphertext is rejected.
- `T-S`: key rotation keeps the configuration valid; the recovery bundle restores secrets on a blank appliance; a missing key produces a clear error and not a crash.
- `T-S`: on a VM with a virtual TPM the key is sealed; on one without, the degraded-protection status is shown.

## Open points

- **Verify on the target OS** whether TPM sealing and `COS_PERSISTENT` encryption work on Hadron (in-place upgrade) and on a custom ISO; the distribution choice is still open.
- **Exact key location** and permissions: set in the deployment view.
- **Algorithm choice** and the secret format: Detailed Design, aligned with the YAML schema.
- **Where the session-signing key lives** (R-043.4): proposed to treat it as one more secret with this scheme, regenerated at factory reset.

## Impact on other documents

- **RA**: clarify R-020.5 (see above); possible new requirement for the recovery bundle and for a visible protection status.
- **components.md**: Config Manager owns encryption and key handling; Observer exposes the protection status.
- **deployment.md**: key location, TPM sealing, interaction with the distribution mechanism.
- **ADR-0008**: the ciphertext format is versioned (`enc:v1`), so its changes are schema changes handled by migration.
