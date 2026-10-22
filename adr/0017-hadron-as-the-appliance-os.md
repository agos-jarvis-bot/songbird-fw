# ADR-0017: Hadron (Kairos) is the appliance operating system

| | |
|---|---|
| Status | Proposed (direction accepted; verification ongoing in `PoC-hadron-os`) |
| Date | 2026-06 (recorded 2026-10-21) |
| Deciders | Songbird team |
| Related | C-002, C-004; R-019, R-031, R-033.1; ADR-0013 (kernel floor); `songbird-prototypes/PoC-hadron-os` (Active) |

## Context

R-019 requires atomic A/B updates and C-002 an immutable, mostly read-only OS. Building this from a general-purpose distribution means owning hardening, partitioning, update logic and recovery ourselves. Kairos provides immutable, A/B-updatable, image-based Linux; **Hadron** is the Kairos flavour evaluated by the PoC.

## Options considered

**A. Debian + custom update tooling (e.g. RAUC, Mender).** Familiar base, mature update frameworks exist. But the immutability story is assembled, not inherent: more surface to harden and more machinery to maintain forever.

**B. Kairos/Hadron.** *(chosen direction)* Immutable by construction, A/B partitions and recovery built in, cloud-init-style configuration that matches the GitOps model, OCI-image-based builds that fit the team's container toolchain.

**C. Flatcar Container Linux.** Immutable and A/B, but container-centric: the appliance is one static binary (C-004), not a container host, and Flatcar's update service assumes infrastructure we do not want to depend on.

## Decision (proposed)

1. The appliance image is built on **Hadron**: read-only root, A/B updates (R-019), writable paths limited to configuration (the Git repository), data and logs (C-002).
2. The build is an OCI image plus ISO artifact via AuroraBoot, as prototyped in `PoC-hadron-os`.
3. **Acceptance gate** (before 0.3 planning): the PoC must confirm kernel ≥ 6.6 (ADR-0013), bpffs behaviour across reboots (maps are rebuilt from YAML, detailed-design/data-plane.md §5), TPM/secrets story input to ADR-0009, and a real A/B upgrade cycle with rollback.
4. If the gate fails, the fallback is **a custom ISO on Debian 13** with RAUC — not a re-architecture of the update model.

## Consequences

**Positive**

- A/B updates and immutability are properties of the base, not code we write; the 0.3 milestone shrinks to integration.
- Image-as-artifact matches the team's existing OCI muscle (Kubernetes background).

**Negative**

- Smaller community and documentation than Debian/Flatcar; debugging Kairos internals may cost time.
- bpffs lives in memory: after every reboot the Data Plane is reloaded from the repository — already the designed behaviour (R-033.1), but boot time must include it.

**Documents changed** when accepted: Project Plan 0.3 scope, `image/` build docs.
