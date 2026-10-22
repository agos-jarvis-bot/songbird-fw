# Songbird – Project Plan

| | |
|---|---|
| **Document** | PP – Project Plan |
| **Version** | 0.2.1-draft |
| **Status** | Draft for team decision |
| **Inputs** | RA v2.0.6, architecture docs (domain model v0.7), ADR-0001…0010 and ADR-0014, YAML schema v1alpha1, prototypes |
| **Outputs** | Release scope, milestones, work breakdown, risk register, process rules |

> Items marked **⟨decide⟩** need a team decision before the plan is baselined. Items marked **⟨fill⟩** need numbers only the team has (availability, dates).

---

## 1. Purpose and planning approach

This plan turns the Requirements Analysis into an ordered sequence of releases, each of which is a **usable firewall**, not a pile of components. The guiding rule is the one from the RA preface: *coding is a consequence of design*. Every release therefore has the same internal order — design → detailed design → tests defined → code → verification — and no release starts coding before its ADRs are written.

The plan is **incremental** (each release adds end-to-end capability) and **iterative** (each release may revise the architecture through ADRs). It is not a waterfall: the RA, the architecture and this plan are living documents versioned in Git and changed through pull requests, exactly like the code.

### 1.1 Constraints the plan must respect

| Constraint | Consequence for the plan |
|---|---|
| Team of **2 people**, part-time **⟨fill: hours/week each⟩** | Serial dependencies hurt; the plan keeps two parallel tracks (data plane / control plane) that meet at integration points. |
| **71 Must** requirements in the RA (v2.0.6) | Must = "release 1.0 is not viable without it". It is **not** the MVP scope. 1.0 is the fourth release of this plan. |
| C-001 eBPF data plane, C-004 Go + C | The eBPF track carries the highest technical risk and starts first. |
| C-005 YAML in Git is the source of truth | The validator and the schema are the first deliverable, because every other component consumes them. |
| C-003 reference platform not yet chosen | Performance requirements (R-047/048/049) cannot be verified before M2; they stay proposed in RA §7 until the first benchmark sets their numeric targets (RA open issue 1). |
| IPv6 is Should, planned after 1.0 (RA §1.2) | No release up to 1.0 plans IPv6; until then IPv6 is dropped and counted (R-057). |

---

## 2. Release roadmap

Four releases. Each is defined by (a) a one-sentence capability statement, (b) the exact requirement IDs it closes, (c) an exit criterion that is a test, not an opinion.

### 2.1 Overview

| Release | Capability statement | Closes (RA IDs) | Target **⟨fill⟩** |
|---|---|---|---|
| **0.1 "Vertical slice"** | A Linux VM with Songbird installed forwards IPv4 between two interfaces as a *stateful*, YAML-configured firewall with SNAT/DNAT, managed only through the CLI, with flow events on stdout/file. | 41 requirements (39 M, 2 S), see §2.2 | |
| **0.2 "Network appliance"** | Adds DHCP, DNS, NTP, the read-only Web UI with live traffic log and the first rule editor; still a dev VM image. | see §2.3 | |
| **0.3 "Product"** | Immutable Hadron image with A/B updates, HTTPS management with authentication/audit, GitOps commit/push, setup wizard. First version someone else can install. | see §2.3 | |
| **1.0 "Must complete"** | All remaining Must requirements (FQDN and MAC Addresses in Policies, GDPR masking, performance targets met on the reference platform) plus the Should items the team selects. | all remaining M + selected S | |

### 2.2 MVP 0.1 — scope decision

**Principle**: 0.1 proves the two riskiest bets at once — (1) that the eBPF classifier + own conntrack design in `dataplane.md` works, and (2) that "YAML → validate → compile → atomic apply" is a sound control-plane model. Everything that does not serve those two proofs is deferred, *including Must requirements*.

#### In scope (41 requirements: 39 Must, 2 Should)

| Area | IDs | Notes |
|---|---|---|
| Routing IPv4 | R-001, R-001.1, R-001.2, R-001.5, R-057 | Physical + VLAN; several static routes per destination with distance and priority. IPv6 is planned after 1.0: until then it is dropped and counted (R-057). |
| NAT | R-002, R-002.1, R-002.2 (S), R-003 | snat (masquerade + pool, same pool address per source) and dnat with port translation, as in `RuleSet.nat`. |
| Objects & rules | R-010, R-010.1, R-011, R-012, R-012.1, R-012.4, R-013, R-014, R-014.1–R-014.5, R-046, R-046.1, R-046.2 (S) | Address/Group, Service/Group, Zone, RuleSet with first-match; predefined `any`/`any6` and Service `any`; member Interfaces next to their Zone, most specific RuleSet first (DM-42); intra-Zone default. FQDN and MAC Addresses are accepted by the schema but rejected in enabled Policies (R-012.4) until 1.0. |
| Stateful | **R-045, R-045.1, R-045.2** | Accepted in RA 2.0.6. A stateless firewall proves nothing. |
| Default deny & events | R-033, R-026, R-026.1 | Events to a local JSON-lines file; no UI. |
| Configuration | R-020, R-020.1, R-020.2, R-020.3, R-020.4, R-020.6, R-020.7 | Import/export/validate/atomic apply; export writes one object per file. R-020.5 (secret encryption) deferred: 0.1 has no secrets. |
| Tooling | R-052 | `songbird validate` CLI, the Go port of `validate.py` (Must since RA 2.0.6). |
| Fragments | R-053 | Default drop of non-initial fragments; trivial once the parser exists. |
| Management access | R-056 | ICMP echo and SSH per Interface (HTTPS management comes with the UI). How the 0.1 VM avoids locking out SSH, given that nothing is enabled by default, is decided in issue #41. |

#### Explicitly out of 0.1 (and why)

| Deferred | Priority | Reason |
|---|---|---|
| IPv6 forwarding, NDP, RA, DHCPv6-PD, NAT64, DNS64 (R-001.3/.4, R-004, R-005, R-017.4, R-006.x, R-018.6) | S | Planned after 1.0 (RA §1.2); R-057 drops IPv6 meanwhile. The 128-bit address representation is designed in from day one (dataplane.md §4) so IPv6 stays additive. |
| DHCP, DNS, NTP and the listening Interfaces of System Services (R-017.x, R-018.x, R-058, R-059) | M/S | Independent Go services; no coupling with the risky parts. 0.2. |
| Web UI (R-009, R-015, R-028, R-043.x, R-046.3) | M | A UI on top of an unproven model is rework. 0.1 is CLI-only by design. |
| Auth, audit log (R-043.x, R-035.x) | M | Only meaningful with the UI/API. 0.3. |
| Immutable OS, A/B updates, setup wizard (R-019, R-031, C-002) | M | 0.1 ships as a `.deb`/tarball on a stock Debian VM; kernel and distribution are decided by ADR-0013 and issue #37. Hadron work proceeds in parallel as a spike (§4). |
| GitOps commit/push (R-021.x) | S | The YAML tree *is* a Git repo already; automation comes with the UI in 0.3. |
| FQDN and MAC Addresses in Policies (R-012.2, R-012.3) | M | Need DNS-driven map updates and an L2 match in the Data Plane (issue #23). 1.0; until then R-012.4 rejects them. |
| GDPR masking, log rotation (R-037.x, R-029) | M | Need the log subsystem design; 1.0 / 0.3. |
| Performance targets (R-047/048/049) | proposed | **Measured** in 0.1 (benchmark harness is in scope), **met** in 1.0. The 0.1 benchmark sets the numbers, then the RA accepts them (RA open issue 1). |
| Colour palette, Interface tree, Interface-bound Addresses (R-012.5), dark mode, HA, BGP, IDS, notifications, syslog, ACME, threat feeds | S/C | Not part of the two proofs. |

#### 0.1 exit criteria (all must pass on the CI runner and on one physical/virtual testbed)

1. `songbird validate` accepts every file of the valid example tree (`schema/examples/valid/`) and rejects every case in `schema/examples/invalid/` with the expected error (R-020.2, R-052); `songbird export` of the valid tree writes one object per file and re-imports to the same Configuration (R-020.1, R-020.7).
2. Integration suite (netns + veth, client–songbird–server): stateful TCP/UDP/ICMP forwarding, reply traffic admitted without a reverse rule, unsolicited inbound dropped and logged, PMTUD works, IPv6 dropped and counted, management access only on the configured Interfaces (R-045.x, R-033, R-026, R-057, R-056).
3. SNAT masquerade and pool, DNAT with and without port translation verified with real traffic (R-002, R-002.1, R-003).
4. Atomic apply: a deliberately half-broken configuration leaves the data plane in the previous generation, byte-identical maps (R-020.6).
5. Control-plane crash (`kill -9`) does not interrupt forwarding; restart re-attaches to pinned maps (prerequisite of R-033.1).
6. Fuzz equivalence: eBPF classifier verdict == reference Go classifier verdict on ≥ 10⁶ random packets × rule sets, including overlapping Interface and Zone RuleSets (R-014.4, R-046.1).
7. Benchmark report produced by the harness on the chosen platform: pps, latency p99, max sessions — **numbers proposed as the targets of R-047/048/049** (closing RA open issue 1).

### 2.3 Releases 0.2, 0.3, 1.0 — scope at a glance

| Release | Adds | Key exit criteria |
|---|---|---|
| **0.2** | DHCPv4 server on any Interface, coherent with the DNS/NTP listening Interfaces (R-017–R-017.3, R-017.5, R-017.6); DNS forwarder with local names and failover (R-018, R-018.1, R-018.2, R-034.x); listening Interfaces of System Services (R-058); NTP client and server (R-059); Web UI read-only: interface tree, objects, rules, live traffic log (R-015.x, R-028); RuleSet evaluation order in UI and CLI (R-046.3); first rule editor (R-009.x); `/health` (R-032.x); Prometheus metrics (R-051); colour palette (R-055.x). | DHCP/DNS/NTP netns tests; browser automation for the tree and the live log; UI edit round-trips to YAML byte-identically. |
| **0.3** | Hadron image + A/B updates (R-019, C-002); HTTPS-only management with ACME (R-038.x); local auth, lockout, sessions, roles, 2FA (R-043.x); audit log with hash chain (R-035.x); GitOps commit/push/pull with conflict UI (R-021.x, R-040–R-042); setup wizard (R-031.x); crash recovery within 30 s (R-033.1); secrets encryption (R-020.5); log rotation (R-029). | Power-loss-during-update test; auth test suite; a fresh ISO reaches a working configuration through the wizard only. |
| **1.0** | FQDN and MAC Addresses in Policies (R-012.2, R-012.3; lifts the R-012.4 rejection); GDPR masking (R-037.x); performance targets met (R-047/048/049, once accepted in the RA); policy-change behaviour (R-054); notifications (R-030.x); threat feeds (R-039.x); recursive DNS + DNSSEC (R-018.3–.5) **⟨decide: in 1.0 or 1.1⟩**. | Every M requirement has a passing test in the traceability matrix; benchmark meets the targets on the reference platform. |
| **Should, not tied to a release** | Syslog forwarding (R-050), Interface-bound Addresses (R-012.5). | Picked by the team when a release has room. |
| **post-1.0 candidates** | IPv6: forwarding, NDP/RA/SLAAC, DHCPv6-PD, NAT64/DNS64 (R-001.3/.4, R-004, R-005, R-017.4, R-006.x, R-018.6); HA/VRRP (R-023.x), BGP (R-024), IDS/IPS (R-025), hot reload (R-036.x), charts (R-027.x), WireGuard (W-001 reconsidered). | |

---

## 3. Milestones for 0.1

Milestones are gates, each with a deliverable that is reviewed in a PR. Estimates are **effort** in person-days (pd) for people already familiar with Go and the Linux network stack; calendar dates follow from availability **⟨fill⟩**.

| # | Milestone | Deliverables | Exit gate | Effort (pd) |
|---|---|---|---|---|
| **M0** | **Plan & architecture baseline** | This plan approved; the *Proposed* ADRs needed by 0.1 moved to *Accepted* (or revised), ADR-0002, 0006 and 0007 accepted as *targets* (§5); ADR-0011 and ADR-0013 written (§5); RA proposals decided (done in RA 2.0.6); deployment view added to the architecture docs; monorepo import merged (done); **Test Plan v0** (§9: methods, infrastructure, environments, traceability-matrix format and test-ID convention); **data-plane detailed design** (detailed design of WBS 3: BPF map layouts with key/value structs, program structure and tail-call boundaries, generation-swap protocol) — the document M2 codes against. | Every ADR of §5 marked for M0 is accepted, or accepted as a target where it waits for a spike or the benchmark; architecture, Test Plan v0 and data-plane detailed design reviewed by both team members. | 5–7 |
| **M1** | **Schema & validator** | `songbird validate` in Go (JSON Schema layer via `santhosh-tekuri/jsonschema`, semantic layer ported from `validate.py`); example corpus as test suite; Go types generated from the schema; CI pipeline (lint, unit tests, corpus); **control-plane detailed design** (detailed design of WBS 2 and 4: Go package layout, loader/compiler/applier interfaces with signatures, reconciliation states and error model) — the document M3 codes against. | Exit criterion 1; control-plane detailed design merged. | 8–10 |
| **M2** | **Data-plane core** | `bpf2go` project skeleton; parser (L2/VLAN/IPv4 with IHL/fragments, 128-bit address normalisation); bit-vector classifier with two-generation maps; own conntrack with SYN-separate map, RELATED, timeouts, sweep; ring-buffer events; `PROG_TEST_RUN` unit tests; fuzz equivalence against the Go reference classifier. | Exit criteria 2 (filtering part), 6. | 20–28 |
| **M3** | **Control-plane core** | Loader/compiler: YAML → object graph → map contents (LPM tries, port classes, effective Policy list per ordered pair of Interfaces, DM-42); netlink application of interfaces/VLANs/addresses/routes (distance and priority, R-001.5); atomic apply with generation swap and rollback; pinned maps and re-attach; event consumer writing JSON-lines; `songbird apply`, `songbird status`, `songbird export`. | Exit criteria 4, 5. | 14–18 |
| **M4** | **NAT in TC** | DNAT (pre-translation match, rewrite in TC ingress), SNAT masquerade and pool with port allocation (TC egress), reverse translations via conntrack, checksum handling; integration tests with real traffic. | Exit criterion 3. | 10–14 |
| **M5** | **Integration, benchmark, release** | netns integration suite in CI; benchmark harness (pktgen/TRex) and report; reference platform chosen (C-003) and target numbers proposed for RA R-047…R-049; packaging (`.deb` + systemd unit); user guide for the CLI; **REST API design** (OpenAPI draft for the UI of 0.2, routes and models already sketched in the PoC feasibility study); 0.1 tag. | Exit criterion 7; all 7 criteria green. | 10–12 |
| | **Total 0.1** | | | **66–88 pd** |

**Detailed design before code.** Every WBS branch that produces code is preceded by a detailed-design document written in an earlier milestone: data plane (WBS 3) at M0, control plane (WBS 2, 4) at M1, REST API at M5 for the 0.2 UI. The Test Plan starts as v0 at M0 and is updated at every release; no implementation work starts before its document is merged and reviewed by both team members.

**Parallelism**: M1 and M2 start together (one person each); M3 depends on M1 and on M2's map layout; M4 depends on M2+M3; M5 integrates. Critical path: M0 → M2 → M4 → M5.

**Sanity check ⟨fill⟩**: at 2 × *h* hours/week, 0.1 takes roughly `(75 × 8) / (2 × h)` weeks — e.g. 30 weeks at 10 h/week each, 15 weeks at 20 h/week each. If that is too long, the lever is scope (drop VLAN or DNAT port translation from 0.1), **not** quality gates.

---

## 4. Work breakdown structure (0.1)

```
0.1
├── 1 Management & process
│   ├── 1.1 Plan baseline, milestone reviews, retrospectives
│   ├── 1.2 ADRs and architecture documents
│   └── 1.3 Repo consolidation / tooling (CI, issue templates, project board)
├── 2 Schema & validator (M1)
│   ├── 2.1 Go module layout, generated types
│   ├── 2.2 Schema validation layer
│   ├── 2.3 Semantic rules (port of validate.py table)
│   └── 2.4 Corpus test harness
├── 3 Data plane (M2, M4)
│   ├── 3.1 Build system (clang, bpf2go, CO-RE, vmlinux.h)
│   ├── 3.2 Parser & normalisation
│   ├── 3.3 Classifier & generation swap
│   ├── 3.4 Conntrack (+ SYN map, RELATED, sweep)
│   ├── 3.5 Events (ringbuf, rate limiting, counters)
│   ├── 3.6 NAT (TC ingress/egress)
│   └── 3.7 PROG_TEST_RUN unit tests & fuzzing
├── 4 Control plane (M3)
│   ├── 4.1 Config loader (YAML tree → object graph)
│   ├── 4.2 Compiler (object graph → map contents)
│   ├── 4.3 Netlink applier (interfaces, VLAN, addresses, routes)
│   ├── 4.4 Apply/rollback orchestration, pinning, re-attach
│   ├── 4.5 Event consumer & log writer
│   └── 4.6 CLI (validate, apply, status, export)
├── 5 Verification (M5)
│   ├── 5.1 netns integration suite
│   ├── 5.2 Benchmark harness & report
│   └── 5.3 Traceability matrix (requirement → test)
├── 6 Release engineering (M5)
│   ├── 6.1 Packaging & systemd unit
│   └── 6.2 CLI user guide, CHANGELOG, tag
└── 7 Spikes (time-boxed, parallel, not on the critical path)
    ├── 7.1 Hadron: kernel version, bpffs, TCX availability (feeds 0.3)
    ├── 7.2 XDP native vs generic on target NICs / PPPoE (feeds C-003)
    └── 7.3 UI stack confirmation (React PoC already exists; feeds 0.2)
```

---

## 5. Architecture decisions to record before coding (M0)

`adr/` holds ADR-0001…0010 and ADR-0014. M0 consists of (a) moving the *Proposed* ones to *Accepted* (or revising them), or accepting them as *targets* where a spike or the benchmark must confirm them, and (b) writing the ones still missing.

| ADR | Decision | Status today | M0 action |
|---|---|---|---|
| 0001 | YAML in Git is the single source of truth | Accepted | — |
| 0002 | Forwarding model: XDP decides, kernel forwards, TC rewrites | Proposed | Accept as *target* for 0.1; confirmed by the benchmark (issue #24); fast path (all-XDP for established flows) is a later ADR |
| 0003 | Own conntrack, no `nf_conntrack` | Proposed | Accept; confirms the reading of C-001 |
| 0004 | Flows no longer permitted are terminated at the next packet | Proposed | Accept (`System.session.onRuleChange`, R-054 accepted in RA 2.0.6) |
| 0005 | Non-initial IPv4 fragments dropped | Proposed | Accept (R-053 accepted in RA 2.0.6) |
| 0006 | Capacity limits of the Data Plane | Proposed | Accept as *targets*; numbers confirmed by the M5 benchmark |
| 0007 | Reference platform | Proposed | Accept after spike 7.2 (C-003) |
| 0008 | Schema versioning, migration, rollback | Proposed | Accept; needed before M1 generates Go types |
| 0009 | Secrets encryption key protection | Proposed | Accept; implementation deferred to 0.3 |
| 0010 | DNAT is a section of the Policy, matched before translation | Accepted | — |
| **0011** | Repository layout: monorepo `songbird-fw` | *to write* | Retroactive: the monorepo is in place (§10) |
| **0012** | Canonical YAML serialisation and file layout (quoted strings; one object per file vs multi-document) | *to write* | Decide before M1 (`songbird export` output); the export layout is already fixed by RA R-020.7 |
| **0013** | Minimum kernel and attach method (≥ 6.6 with TCX vs 5.15 LTS with clsact) | *to write* | Decide before M2; interacts with 0007 and spike 7.1 |
| **0014** | DHCP and DNS engines: in-process libraries or external daemons | Proposed, question open | Decide before the 0.2 DHCP/DNS work (spike) |

## 6. Roles and responsibilities

Two people, so roles are *hats*, not positions; every artifact has one owner and one reviewer, never the same person.

| Hat | Responsibilities | Owner ⟨fill⟩ |
|---|---|---|
| Product / requirements | RA ownership, priority decisions, acceptance of releases | |
| Architect | ADRs, architecture docs, cross-track consistency | |
| Data-plane lead | WBS 3, benchmark | |
| Control-plane lead | WBS 2, 4 | |
| Verification | WBS 5, traceability matrix, CI health | |
| Release manager | WBS 6, tagging, CHANGELOG | |

Rule: **nothing merges without a review by the other person.** For a two-person team this is the whole quality system; it is non-negotiable even for docs.

---

## 7. Process and conventions

| Topic | Rule |
|---|---|
| Branching | Trunk-based: short-lived branches, PR into `main`, squash merge, `main` always green. |
| Commits | Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:`); body references requirement IDs (`Refs: R-045, R-033`). |
| Issues | One issue per WBS leaf or smaller; labels `area/dataplane`, `area/controlplane`, `area/schema`, `area/docs`, `release/0.1`; GitHub Projects board with columns Backlog → Ready → In progress → Review → Done. |
| Definition of Ready | Issue links the requirement IDs and the ADR(s) it depends on; verification method known. |
| Definition of Done | Code + tests merged; CI green; traceability matrix updated; docs updated if behaviour changed; reviewer approved. |
| ADR | Required for any decision that is expensive to reverse. Template in `adr/0000-template.md`. Superseding is done by a new ADR, never by editing. |
| Documentation | Markdown in-repo, Mermaid diagrams, rendered with MkDocs (Material) to GitHub Pages **⟨decide⟩**. The old LyX/PDF toolchain is not used. |
| Meetings | One 30-min sync per week; one milestone review per gate; decisions written as issues/ADRs, not minutes. |
| Code quality | `golangci-lint`, `gofmt`, `clang-format` for BPF C, `go test -race`, coverage reported (target ≥ 70% control plane). |
| Security | No secrets in Git (schema enforces `ENC[...]`); Dependabot; `govulncheck` in CI; signed tags for releases. |
| Versioning | SemVer; `apiVersion` of the schema evolves `v1alpha1 → v1beta1 → v1` with conversion rules documented. |

---

## 8. Risk register

Scored Probability × Impact, 1–3 each. Reviewed at every milestone gate.

| # | Risk | P | I | Score | Mitigation / trigger |
|---|---|---|---|---|---|
| R1 | **eBPF verifier rejects the classifier/conntrack program** (complexity, loop bounds, stack size). | 3 | 3 | 9 | Start M2 first; keep programs small and tail-called; `PROG_TEST_RUN` on every commit; fallback: reduce MAX_RULES bitmap width. Trigger: verifier failure not fixed within 2 days → ADR to split programs. |
| R2 | **Bus factor = 2**, part-time availability shrinks. | 3 | 3 | 9 | Everything documented and reviewed; no knowledge only in one head; scope lever (§3) rather than quality lever. |
| R3 | **Own conntrack correctness** (TCP state machine edge cases, SYN flood behaviour). | 2 | 3 | 6 | Fuzz + netns tests with real stacks; study Cilium's CT; accept simplified TCP tracking in 0.1 and document it. |
| R4 | **Hadron/Kairos kernel too old** for TCX / needed kfuncs. | 2 | 3 | 6 | Spike 7.1 before 0.3 planning; fallback to classic TC clsact attach (works on ≥ 5.x). |
| R5 | **Target NIC lacks native XDP** (e.g. Realtek on mini-PCs), only generic XDP → performance targets missed. | 2 | 2 | 4 | Spike 7.2; define reference platform explicitly (Intel i225/i226 or X5xx class); document supported hardware. |
| R6 | **Scope creep** from FortiGate feature envy. | 3 | 2 | 6 | RA is the gate: no feature without an accepted requirement; §8 exclusions stay explicit. |
| R7 | **Pre-translation DNAT semantics** diverges from what users expect from FortiGate VIPs. | 2 | 2 | 4 | ADR-0010 documents it; UI shows "public address → internal address" explicitly; revisit before 1.0 with user feedback. |
| R8 | **Checksum / offload bugs in TC NAT** (GSO/GRO, csum partial). | 2 | 2 | 4 | Use `bpf_l3/l4_csum_replace`; test with offloads on and off in netns; TRex validation in M5. |
| R9 | Performance targets unachievable with forwarding via kernel stack (option A). | 2 | 2 | 4 | 0.1 benchmark decides; option B fast path is already designed as a follow-up. |
| R10 | **Tooling churn** (`cilium/ebpf` API changes, Go version). | 2 | 1 | 2 | Pin versions; Dependabot with review. |

---

## 9. Verification strategy (summary — the Test Plan is a separate document)

The Test Plan is produced as **v0 at M0** (methods below, infrastructure, environments, the traceability-matrix format and the test-ID convention) and updated at every release: new test cases are added in the same milestone that adds the behaviour, so the matrix never lags the code. The RA's verification column already assigns each requirement a method. The Test Plan will contain, per method:

| Method | Infrastructure | Lives in |
|---|---|---|
| T-U | `go test`; `PROG_TEST_RUN` with gopacket-built packets; corpus for the validator | `*_test.go`, `testdata/` |
| T-I | netns + veth topologies created by a Go test helper; runs on a privileged CI runner (self-hosted or GitHub `ubuntu-latest` with `sudo`) | `test/integration/` |
| T-S | VM-based (0.3+), browser automation (Playwright) for the UI (0.2+) | `test/system/` |
| T-P | pktgen in netns for CI smoke; TRex on the reference platform for release numbers | `test/bench/` |
| I / A | Review checklists attached to PR templates | `.github/PULL_REQUEST_TEMPLATE.md` |

Traceability matrix: a generated table `requirement → test IDs → last result`, produced by CI from test annotations (`// Verifies: R-045.1`), published with the docs. A Must requirement without a test is a release blocker for 1.0.

---

## 10. Repository consolidation (ADR-0011)

Decided by the team on 2026-10-19 and implemented: **one repository `songbird-fw`**, with this layout (directories marked *from* a release are created when that release starts):

```
songbird-fw/
├── docs/            RA, this plan, architecture (domain model, components, reconciliation, data plane), test plan, user guide
├── adr/             from songbird-architecture/adr
├── schema/          JSON Schema + corpus + validate.py (from songbird-yaml-schema)
├── cmd/songbird/    CLI
├── internal/        control plane packages (config, compile, apply, netlink, events, api)
├── bpf/             data plane C sources, bpf2go
├── ui/              web UI (from 0.2)
├── test/            integration, system, bench
└── image/           Hadron/Kairos build (from 0.3)
```

Benefits: one PR can touch requirement, ADR, schema, code and test together; one CI; one issue tracker; the traceability matrix is trivial to generate. The import preserved history (`git subtree add`). `songbird-prototypes` (archived PoCs) and `songbird-site` stay separate; the three imported repos (`songbird-architecture`, `songbird-yaml-schema`, `songbird-requirements-analysis`) are archived.

---

## 11. Open decisions (blocking plan baseline)

| # | Decision | Needed by | Issue |
|---|---|---|---|
| 2 | Availability: hours/week per person → calendar for §3. | M0 | #36 |
| 4 | Reference platform (ADR-0007) and numeric performance targets. | M2 → M5 | #7 |
| 5 | Minimum kernel: 6.6 (TCX, bpf_link for TC) vs 5.15 LTS (clsact fallback) (ADR-0013); Debian 12 ships 6.1, Debian 13 ships 6.12. | M0 | #31 |
| 6 | 0.1 packaging target: Debian 13 `.deb` vs tarball + systemd unit only. | M5 | #37 |
| 7 | CI runner for privileged netns tests: GitHub-hosted with sudo vs self-hosted (Agos' Proxmox). | M1 | #38 |
| 8 | Management access to the 0.1 appliance without locking out SSH (R-056). | M2 | #41 |

### Resolved

| # | Decision | Resolution |
|---|---|---|
| 1 | Accept RA proposals R-045…R-054 and R-059. | RA 2.0.6 (2026-10-21): R-045, R-050…R-054, R-059 accepted, R-052 promoted to Must; R-047…R-049 deferred until the benchmark (#6). |
| 3 | Monorepo (ADR-0011). | Implemented: `songbird-fw` imported, old repos archived; ADR-0011 to be written retroactively (#31). |

---

## 12. Change log

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1.0-draft | 2026-10-19 | Hermes (for Agos review) | Skeleton: roadmap 0.1→1.0, MVP 0.1 scope with in/out rationale and exit criteria, milestones with effort, WBS, ADR list, roles, process, risk register, verification summary, monorepo proposal, open decisions. |
| 0.2.0-draft | 2026-10-21 | Claude (for team review) | Aligned with RA 2.0.6 (#40). IPv6 (incl. NAT64/DNS64, DHCPv6-PD) moved from 0.2/1.0 to post-1.0 candidates. Must requirements missing from every release assigned: R-001.5, R-002.1, R-010.1, R-012.1, R-012.4, R-020.7, R-046.1, R-056, R-057 to 0.1; R-017.5, R-017.6, R-046.3, R-058 to 0.2; R-012.2, R-012.3 to 1.0. Should items placed: R-002.2, R-046.2 in 0.1, R-059 in 0.2; R-050 and R-012.5 not tied to a release. Counts fixed (0.1 = 41 requirements, 71 Must in the RA). M0 gate no longer requires ADR-0002/0006/0007 to be final; ADR-0010 shown as Accepted; risk R7 cites ADR-0010; monorepo described as done; M3 uses effective Policy lists (DM-42); exit criterion 1 refers to the corpus instead of fixed counts. Open decisions linked to their issues; 1 and 3 resolved. |
| 0.2.1-draft | 2026-10-21 | Hermes (for team review) | Milestones carry detailed-design deliverables (issue #42): Test Plan v0 + data-plane detailed design at M0, control-plane detailed design at M1, REST API design at M5; "detailed design before code" rule made explicit; totals adjusted. |
