# Songbird – Test Plan

| | |
|---|---|
| **Document** | TP – Test Plan |
| **Version** | 0.1.1-draft (v0, milestone M0) |
| **Status** | Draft for team review |
| **Inputs** | RA (`docs/requirements-analysis.md`, verification column), Project Plan §9, `docs/architecture/dataplane.md`, `schema/` corpus |
| **Maintained** | This document starts at M0 and is updated in the same milestone that adds a behaviour (Project Plan §9). The matrix never lags the code. |

---

## 1. Purpose and scope

This plan defines how Songbird is verified: the test levels, the test-ID convention, the traceability matrix, the environments, the entry/exit criteria, and the suites that must exist for release 0.1.

The Requirements Analysis assigns every requirement exactly one primary verification method (RA §4.4). This plan does not repeat the requirement list: it defines the *machinery* that turns those per-requirement criteria into executable, reproducible, CI-enforced tests, and the rules that decide when a release may ship.

Out of scope for v0: the System/acceptance suite for the Web UI (0.2+) and the appliance image (0.3+), performance *targets* (measured at M5, targets proposed to the RA afterwards), and fuzzing infrastructure beyond the classifier-equivalence fuzz already required by R-014.4/R-046.1.

---

## 2. Test levels

The six RA methods map to four executable levels plus two review gates. A requirement is *done* only when its primary level passes in CI (or, for I/A, its checklist is signed in the PR).

| Level | RA code | What it is | Infrastructure | Lives in | 0.1? |
|---|---|---|---|---|---|
| **L1 Unit** | T-U | Single component in isolation: Go packages, the eBPF classifier via `BPF_PROG_TEST_RUN` with gopacket-built packets, the schema validator against its corpus. | `go test`; `cilium/ebpf` prog `.Run()`; gopacket | `*_test.go`, `testdata/`, `schema/examples/` | Yes |
| **L2 Integration** | T-I | Real kernel networking across components: client – songbird – server in Linux network namespaces with veth pairs; real TCP/UDP/ICMP traffic, DNAT/SNAT, VLAN. | Go test helper building netns topologies; privileged CI runner | `test/integration/` | Yes |
| **L3 System** | T-S | End-to-end scenarios on a full installation/VM, UI included (browser automation, Playwright). | Packer/VM scripts; Playwright | `test/system/` | No (0.2/0.3) |
| **L4 Performance** | T-P | Throughput, latency, session scale against numeric targets. | pktgen in netns (CI smoke); TRex on the reference platform (release numbers) | `test/bench/` | Smoke at M5 |
| **L5 Inspection** | I | Document/code/config review against a checklist (constraints, ADR conformance). | PR template checklists | `.github/PULL_REQUEST_TEMPLATE.md` | Yes |
| **L6 Analysis** | A | Reasoning/static checks for properties not observable at runtime (crypto parameters, hash-chain design). | Checklist + tooling (`govulncheck`, hash inspection) | PR template; CI security job | Yes |

### 2.1 Level rules

1. **Tests precede code** for the level the requirement belongs to: the test case (or at least its failing skeleton) is written in the same PR as the implementation it verifies.
2. **Flaky tests are release blockers**, not tolerated debt: an L2 test that fails intermittently is either fixed, quarantined with a linked issue and a deadline of one milestone, or the release waits.
3. **No mocks in L2**: namespaces, veth, and the real kernel stack are the point; a simulated kernel would test the simulation.
4. **Corpus discipline for the validator** (L1): every schema or semantic rule change adds one valid object and one invalid case; the two corpora are the contract (RA R-020.2, R-052).

---

## 3. Test-ID convention

Every test case has a stable identifier, used in code annotations, the traceability matrix, and CI logs.

```
<L1|L2|L3|L4>-<AREA>-<NNN>
```

| AREA | Covers |
|---|---|
| VALID | Schema + validator (WBS 2) |
| PARSE | Data-plane parser |
| CLASS | Classifier / RuleSet evaluation |
| CT | Connection tracking |
| FWD | Forwarding and filtering across Interfaces (stateful TCP/UDP/ICMP, VLAN, PMTUD) |
| NAT | SNAT/DNAT (TC) |
| EVENT | Events, traffic log, counters |
| CFG | Loader, compiler, apply, rollback |
| NET | Netlink, interfaces, routing |
| SYS | System services (DHCP/DNS/NTP) |
| AUTH | Auth, audit, UI security (0.3+) |
| UI | Web UI (0.2+) |
| PERF | Performance |
| REL | Packaging, update, recovery |

Examples: `L1-VALID-007` (validator rejects nested groups), `L2-NAT-003` (DNAT with port translation), `L2-CT-001` (stateful reply admitted).

**Rules:**
- IDs are never reused; a removed test keeps its ID in the matrix as *withdrawn*.
- In Go: the ID is the test function suffix — `func TestNAT_DNATPortTranslation_L2_NAT_003(t *testing.T)`.
- Requirement linkage is an annotation on the test: `// Verifies: R-003, R-045.1`. One test may verify several requirements; a requirement may be verified by several tests.

---

## 4. Traceability matrix

The matrix is **generated**, never edited by hand: a CI job (`matrix`) scans the tree for `// Verifies: R-…` annotations, cross-references the RA table, and publishes `docs/generated/traceability-matrix.md` (or the docs site) with, per requirement: ID, priority, primary method, test IDs, last CI result, and coverage flag.

| Matrix state | Meaning | Rule |
|---|---|---|
| `covered` | ≥ 1 test annotated with the requirement, green in the last `main` run | — |
| `red` | tests exist, failing on `main` | Release blocker, any release |
| `uncovered` | no test annotated | **Release blocker for Must requirements at 1.0**; for 0.1, the 0.1-scope Must set (Project Plan §2.2) must be fully covered at M5 |
| `withdrawn` | requirement withdrawn from the RA | Kept for history |

**Enforcement ramps with the milestones.** `red` fails the pipeline from the moment the matrix job exists (M1). `uncovered` for a Must requirement in the current release scope is *reported* only until M5, and is blocking on `main` and on the release tag from M5 onwards (Project Plan §2.2); before that, a requirement whose milestone has been delivered must not be `uncovered` (checked at each milestone gate).

---

## 5. Environments

| Env | What | Used by | Status |
|---|---|---|---|
| **CI-fast** | GitHub `ubuntu-latest`, unprivileged Go toolchain, `golangci-lint`, corpus | L1 (non-BPF), L5/L6 CI parts | Active (schema-validate workflow) |
| **CI-bpf** | Runner with CAP_BPF/root for `PROG_TEST_RUN` and L2 netns. GitHub-hosted with `sudo`, or self-hosted on Agos' Proxmox | L1 (BPF), L2 | **Open — plan decision #7, needed by M1** |
| **Bench** | Reference platform (C-003): bare metal or pinned VM, TRex/pktgen, kernel per ADR-0013 | L4 | Pending ADR-0007/0013; needed by M5 |
| **VM lab** | Packer-built VM of the appliance image; Playwright | L3 | 0.3 |

Environment prerequisites are code: a `test/env` check runs first in every job and fails fast with the missing capability named (kernel version ≥ 6.6 per ADR-0013, CAP_BPF, `iproute2`, TRex).

---

## 6. Suites required for release 0.1

Each suite maps to the 0.1 exit criteria (Project Plan §2.2). "Owner" = the milestone that delivers it.

| # | Suite | Level | Content (headline tests) | Owner | Exit criterion |
|---|---|---|---|---|---|
| S1 | **Validator corpus** | L1-VALID | 57 valid objects accepted; 48 invalid cases rejected with the expected rule ID; round-trip export→import (R-020.1) | M1 | 1 |
| S2 | **Parser** | L1-PARSE | Well-formed and malformed packets: IHL>5, fragments, VLAN single/double tag, extension headers (0.2 prep), ARP/NDP exceptions | M2 | 2 |
| S3 | **Classifier** | L1-CLASS | First-match semantics, Zone specificity order (R-046.1), empty RuleSet = explicit deny, **fuzz equivalence**: eBPF vs reference Go classifier on ≥ 10⁶ random packets × rule sets (R-014.4) | M2 | 2, 6 |
| S4 | **Conntrack** | L1-CT + L2-CT | TCP state machine, SYN-map separation under SYN flood, RELATED for ICMP errors, timeouts, sweep events | M2 | 2 |
| S5 | **Forwarding & filtering** | L2 | Stateful TCP/UDP/ICMP across two Interfaces + VLAN; unsolicited inbound dropped and logged; PMTUD (R-045.x, R-033, R-026) | M2 | 2 |
| S6 | **NAT** | L2-NAT | Masquerade, SNAT pool, DNAT with/without port translation, reply translation, checksum with offloads on/off | M4 | 3 |
| S7 | **Apply & resilience** | L2-CFG | Atomic apply with deliberately broken block → byte-identical rollback (R-020.6); `kill -9` keeps forwarding, restart re-attaches to pinned maps | M3 | 4, 5 |
| S8 | **Benchmark smoke** | L4-PERF | pktgen in netns: pps/latency/session-scale report; numbers proposed to RA R-047…R-049 | M5 | 7 |

S3's fuzz and S5's PMTUD are the two suites most likely to surface design bugs; schedule them early in their milestones.

---

## 7. Entry and exit criteria

### Per level (when a suite may start)
- **L1**: the package/program skeleton compiles; for BPF, the toolchain pins clang and `cilium/ebpf` versions (ADR-0013 input).
- **L2**: S1 green; the netns helper exists and is itself tested (it creates and tears down topologies deterministically).
- **L4**: L2 green; the traffic generator is calibrated (known-good run against the loopback reference).
- **L5/L6**: a checklist exists in the PR template for the artifact type being reviewed.

### Per release (0.1)
1. All suites S1–S8 green on `main` and on the release tag, on both CI-fast and CI-bpf.
2. Matrix: every Must requirement of the 0.1 scope `covered`; zero `red`.
3. Benchmark report attached to the release notes, with the reference platform named.
4. Zero open flaky-test quarantines older than one milestone.

---

## 8. Defects, regressions, data

- **Defects** are GitHub issues labelled `type/bug` + the AREA of §3, linked to the failing test ID; the fix PR must reference the issue and add or strengthen a test that reproduces the failure first.
- **Regressions**: every bug fix lands with its reproduction as a permanent test in the suite of the failing level.
- **Test data**: packet fixtures as gopacket builders in code (no opaque binaries); YAML fixtures in `testdata/`; the schema corpus doubles as validator fixtures and UI export fixtures. Traffic for L2 is generated (no pcaps in Git) except for the malformed-packet set, which is kept as hex with a comment per packet.
- **CI surfaces**: JUnit XML from every level; the matrix job and benchmark report are build artifacts attached to each `main` run.

---

## 9. Roles and calendar

| Milestone | Test work besides the suites |
|---|---|
| M0 | This plan reviewed; netns helper designed; CI-bpf runner chosen (plan decision #7) |
| M1 | S1 in CI; matrix job live (annotations parsed, even if mostly `uncovered`) |
| M2 | S2–S5; fuzz equivalence running nightly if too slow for per-PR |
| M3 | S7 |
| M4 | S6 |
| M5 | S8; release gate §7 enforced on the tag |

The person who ships a feature writes its tests; the other person reviews both. The matrix is the single source of truth for "are we done".

---

## 10. Open items

| # | Item | Needed by |
|---|---|---|
| 1 | CI-bpf runner choice (GitHub-hosted sudo vs self-hosted Proxmox) — plan decision #7 | M1 |
| 2 | Reference platform + kernel (ADR-0007, ADR-0013) | M5 |
| 3 | Fuzz budget: per-PR subset vs nightly full run | M2 |
| 4 | Traceability publication target: generated markdown vs docs site | M1 |

---

## 11. Change log

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1.0-draft | 2026-10-21 | Hermes (for team review) | v0 for milestone M0: levels, test-ID convention, traceability matrix, environments, 0.1 suites S1–S8, entry/exit criteria, defect rules, calendar. |
| 0.1.1-draft | 2026-10-23 | Hermes (for team review) | Review fixes: added the FWD area (used by suite S5); matrix enforcement now ramps (red from M1, uncovered Must blocking from M5), removing the contradiction with the M1 "mostly uncovered" state; `test/env` kernel floor tied to ADR-0013. |
