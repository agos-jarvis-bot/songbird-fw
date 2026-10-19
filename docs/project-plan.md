# Songbird – Project Plan

| | |
|---|---|
| **Document** | PP – Project Plan |
| **Version** | 0.1.0-draft (skeleton) |
| **Status** | Draft for team decision |
| **Inputs** | RA v2.0.2, architecture docs and ADR-0001…0010, YAML schema v1alpha1, prototypes |
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
| **67 Must** requirements in the RA | Must = "release 1.0 is not viable without it". It is **not** the MVP scope. 1.0 is the fourth release of this plan. |
| C-001 eBPF data plane, C-004 Go + C | The eBPF track carries the highest technical risk and starts first. |
| C-005 YAML in Git is the source of truth | The validator and the schema are the first deliverable, because every other component consumes them. |
| C-003 reference platform not yet chosen | Performance requirements (R-047/048/049) cannot be verified before M2; their numeric targets are set after the first benchmark. |

---

## 2. Release roadmap

Four releases. Each is defined by (a) a one-sentence capability statement, (b) the exact requirement IDs it closes, (c) an exit criterion that is a test, not an opinion.

### 2.1 Overview

| Release | Capability statement | Closes (RA IDs) | Target **⟨fill⟩** |
|---|---|---|---|
| **0.1 "Vertical slice"** | A Linux VM with Songbird installed forwards IPv4 between two interfaces as a *stateful*, YAML-configured firewall with SNAT/DNAT, managed only through the CLI, with flow events on stdout/file. | 23 requirements, see §2.2 | |
| **0.2 "Network appliance"** | Adds IPv6, DHCP, DNS, the read-only Web UI with live traffic log and the first rule editor; still a dev VM image. | see §2.3 | |
| **0.3 "Product"** | Immutable Hadron image with A/B updates, HTTPS management with authentication/audit, GitOps commit/push, setup wizard. First version someone else can install. | see §2.3 | |
| **1.0 "Must complete"** | All remaining Must requirements (NAT64/DNS64, DHCPv6-PD, GDPR masking, performance targets met on the reference platform) plus the Should items the team selects. | all remaining M + selected S | |

### 2.2 MVP 0.1 — scope decision

**Principle**: 0.1 proves the two riskiest bets at once — (1) that the eBPF classifier + own conntrack design in `dataplane.md` works, and (2) that "YAML → validate → compile → atomic apply" is a sound control-plane model. Everything that does not serve those two proofs is deferred, *including Must requirements*.

#### In scope (23 requirements)

| Area | IDs | Notes |
|---|---|---|
| Routing IPv4 | R-001, R-001.1, R-001.2 | Physical + VLAN. IPv6 (R-001.3/.4) deferred. |
| NAT | R-002, R-003 | snat (masquerade + pool) and dnat with port translation, as in `RuleSet.nat`. |
| Objects & rules | R-010, R-011, R-012, R-013, R-014, R-014.1–R-014.5, R-046 | Address/Group, Service/Group, Zone, RuleSet with first-match. |
| Stateful | **R-045, R-045.1, R-045.2** | Proposed in RA §7 — must be **accepted** for 0.1 to make sense (a stateless firewall proves nothing). |
| Default deny & events | R-033, R-026, R-026.1 | Events to a local JSON-lines file; no UI. |
| Configuration | R-020, R-020.1, R-020.2, R-020.3, R-020.4, R-020.6 | Import/export/validate/atomic apply. R-020.5 (secret encryption) deferred: 0.1 has no secrets. |
| Tooling | R-052 | `songbird validate` CLI, the Go port of `validate.py`. |
| Fragments | R-053 | Default drop of non-initial fragments; trivial once the parser exists. |

#### Explicitly out of 0.1 (and why)

| Deferred | Priority | Reason |
|---|---|---|
| IPv6 forwarding, NDP, RA, NAT64, DNS64 (R-001.3/.4, R-004, R-005, R-006.x, R-018.6) | M | Doubles parser and test surface. The 128-bit address representation is designed in from day one (dataplane.md §4) so IPv6 is additive in 0.2. |
| DHCP, DNS (R-017.x, R-018.x) | M | Independent Go services; no coupling with the risky parts. 0.2. |
| Web UI (R-009, R-015, R-028, R-043.x) | M | A UI on top of an unproven model is rework. 0.1 is CLI-only by design. |
| Auth, audit log (R-043.x, R-035.x) | M | Only meaningful with the UI/API. 0.3. |
| Immutable OS, A/B updates, setup wizard (R-019, R-031, C-002) | M | 0.1 ships as a `.deb`/tarball on a stock Debian/Ubuntu VM with kernel ≥ 6.6. Hadron work proceeds in parallel as a spike (§4). |
| GitOps commit/push (R-021.x) | S | The YAML tree *is* a Git repo already; automation comes with the UI in 0.3. |
| GDPR masking, log rotation (R-037.x, R-029) | M | Need the log subsystem design; 1.0 / 0.3. |
| Performance targets (R-047/048/049) | M | **Measured** in 0.1 (benchmark harness is in scope), **met** in 1.0. The 0.1 benchmark sets the numbers. |
| Colour palette, Interface tree, dark mode, HA, BGP, IDS, notifications, ACME, threat feeds | S/C | Not part of the two proofs. |

#### 0.1 exit criteria (all must pass on the CI runner and on one physical/virtual testbed)

1. `songbird validate` accepts the 43-object example tree and rejects all 38 invalid files (R-020.2, R-052).
2. Integration suite (netns + veth, client–songbird–server): stateful TCP/UDP/ICMP forwarding, reply traffic admitted without a reverse rule, unsolicited inbound dropped and logged, PMTUD works (R-045.x, R-033, R-026).
3. SNAT masquerade and pool, DNAT with and without port translation verified with real traffic (R-002, R-003).
4. Atomic apply: a deliberately half-broken configuration leaves the data plane in the previous generation, byte-identical maps (R-020.6).
5. Control-plane crash (`kill -9`) does not interrupt forwarding; restart re-attaches to pinned maps (prerequisite of R-033.1).
6. Fuzz equivalence: eBPF classifier verdict == reference Go classifier verdict on ≥ 10⁶ random packets × rule sets (R-014.4).
7. Benchmark report produced by the harness on the chosen platform: pps, latency p99, max sessions — **numbers recorded in RA R-047/048/049** (closing RA open issue 1).

### 2.3 Releases 0.2, 0.3, 1.0 — scope at a glance

| Release | Adds | Key exit criteria |
|---|---|---|
| **0.2** | IPv6 forwarding + NDP/RA/SLAAC (R-001.3/.4, R-004, R-005); DHCPv4 server (R-017–R-017.3); DNS forwarder with local names and failover (R-018, R-018.1, R-018.2, R-034.x); Web UI read-only: interface tree, objects, rules, live traffic log (R-015.x, R-028); first rule editor (R-009.x); `/health` (R-032.x); Prometheus metrics (R-051); colour palette (R-055.x). | IPv6 integration suite green; DHCP/DNS netns tests; browser automation for the tree and the live log; UI edit round-trips to YAML byte-identically. |
| **0.3** | Hadron image + A/B updates (R-019, C-002); HTTPS-only management with ACME (R-038.x); local auth, lockout, sessions, roles, 2FA (R-043.x); audit log with hash chain (R-035.x); GitOps commit/push/pull with conflict UI (R-021.x, R-040–R-042); setup wizard (R-031.x); crash recovery within 30 s (R-033.1); secrets encryption (R-020.5); log rotation (R-029). | Power-loss-during-update test; auth test suite; a fresh ISO reaches a working configuration through the wizard only. |
| **1.0** | NAT64/DNS64 (R-006.x, R-018.6); DHCPv6-PD (R-017.4); GDPR masking (R-037.x); performance targets met (R-047/048/049); policy-change behaviour (R-054); syslog (R-050); notifications (R-030.x); threat feeds (R-039.x); recursive DNS + DNSSEC (R-018.3–.5) **⟨decide: in 1.0 or 1.1⟩**. | Every M requirement has a passing test in the traceability matrix; benchmark meets the targets on the reference platform. |
| **post-1.0 candidates** | HA/VRRP (R-023.x), BGP (R-024), IDS/IPS (R-025), hot reload (R-036.x), charts (R-027.x), WireGuard (W-001 reconsidered). | |

---

## 3. Milestones for 0.1

Milestones are gates, each with a deliverable that is reviewed in a PR. Estimates are **effort** in person-days (pd) for people already familiar with Go and the Linux network stack; calendar dates follow from availability **⟨fill⟩**.

| # | Milestone | Deliverables | Exit gate | Effort (pd) |
|---|---|---|---|---|
| **M0** | **Plan & architecture baseline** | This plan approved; ADR-0002…0010 moved from *Proposed* to *Accepted* (or revised), ADR-0011…0013 written (§5); RA proposals R-045…R-054 accepted/rejected; deployment view added to the architecture docs; monorepo import merged. | All ADRs accepted; architecture reviewed by both team members. | 4–6 |
| **M1** | **Schema & validator** | `songbird validate` in Go (JSON Schema layer via `santhosh-tekuri/jsonschema`, semantic layer ported from `validate.py`); example corpus as test suite; Go types generated from the schema; CI pipeline (lint, unit tests, corpus). | Exit criterion 1. | 6–8 |
| **M2** | **Data-plane core** | `bpf2go` project skeleton; parser (L2/VLAN/IPv4 with IHL/fragments, 128-bit address normalisation); bit-vector classifier with two-generation maps; own conntrack with SYN-separate map, RELATED, timeouts, sweep; ring-buffer events; `PROG_TEST_RUN` unit tests; fuzz equivalence against the Go reference classifier. | Exit criteria 2 (filtering part), 6. | 20–28 |
| **M3** | **Control-plane core** | Loader/compiler: YAML → object graph → map contents (LPM tries, port classes, zone bitmaps); netlink application of interfaces/VLANs/addresses/routes; atomic apply with generation swap and rollback; pinned maps and re-attach; event consumer writing JSON-lines; `songbird apply|status|export`. | Exit criteria 4, 5. | 14–18 |
| **M4** | **NAT in TC** | DNAT (pre-translation match, rewrite in TC ingress), SNAT masquerade and pool with port allocation (TC egress), reverse translations via conntrack, checksum handling; integration tests with real traffic. | Exit criterion 3. | 10–14 |
| **M5** | **Integration, benchmark, release** | netns integration suite in CI; benchmark harness (pktgen/TRex) and report; reference platform chosen (C-003) and numbers written into RA; packaging (`.deb` + systemd unit); user guide for the CLI; 0.1 tag. | Exit criterion 7; all 7 criteria green. | 8–10 |
| | **Total 0.1** | | | **62–84 pd** |

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

`songbird-architecture/adr/` already holds ADR-0001…0010. M0 consists of (a) moving the *Proposed* ones to *Accepted* (or revising them), and (b) writing the three that are still missing.

| ADR | Decision | Status today | M0 action |
|---|---|---|---|
| 0001 | YAML in Git is the single source of truth | Accepted | — |
| 0002 | Forwarding model: XDP decides, kernel forwards, TC rewrites | Proposed | Accept for 0.1; fast path (all-XDP for established flows) is a later ADR |
| 0003 | Own conntrack, no `nf_conntrack` | Proposed | Accept; confirms the reading of C-001 |
| 0004 | Flows no longer permitted are terminated at the next packet | Proposed | Accept (`System.session.onRuleChange`, R-054) |
| 0005 | Non-initial IPv4 fragments dropped | Proposed | Accept (R-053) |
| 0006 | Capacity limits of the Data Plane | Proposed | Accept as *targets*; numbers confirmed by the M5 benchmark |
| 0007 | Reference platform | Proposed | Accept after spike 7.2 (C-003) |
| 0008 | Schema versioning, migration, rollback | Proposed | Accept; needed before M1 generates Go types |
| 0009 | Secrets encryption key protection | Proposed | Accept; implementation deferred to 0.3 |
| 0010 | DNAT is a section of the Policy, matched before translation | Proposed | Accept; `dataplane.md` §7 updated accordingly |
| **0011** | Repository layout: monorepo `songbird-fw` | *to write* | This plan §10; the import PR is the implementation |
| **0012** | Canonical YAML serialisation and file layout (quoted strings; one object per file vs multi-document) | *to write* | Decide before M1 (`songbird export` output) |
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
| R7 | **Pre-translation DNAT semantics** diverges from what users expect from FortiGate VIPs. | 2 | 2 | 4 | ADR-003 documents it; UI shows "public address → internal address" explicitly; revisit before 1.0 with user feedback. |
| R8 | **Checksum / offload bugs in TC NAT** (GSO/GRO, csum partial). | 2 | 2 | 4 | Use `bpf_l3/l4_csum_replace`; test with offloads on and off in netns; TRex validation in M5. |
| R9 | Performance targets unachievable with forwarding via kernel stack (option A). | 2 | 2 | 4 | 0.1 benchmark decides; option B fast path is already designed as a follow-up. |
| R10 | **Tooling churn** (`cilium/ebpf` API changes, Go version). | 2 | 1 | 2 | Pin versions; Dependabot with review. |

---

## 9. Verification strategy (summary — the Test Plan is a separate document)

The RA's verification column already assigns each requirement a method. The Test Plan will contain, per method:

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

Current: 5 repos. Decision taken by the team on 2026-10-19: **one repository `songbird-fw`**, target layout:

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

Benefits: one PR can touch requirement, ADR, schema, code and test together; one CI; one issue tracker; the traceability matrix is trivial to generate. The import preserves history (`git subtree add`). `songbird-prototypes` (archived PoCs) and `songbird-site` stay separate; the three imported repos are archived with a pointer to `songbird-fw` once the import PR is merged.

---

## 11. Open decisions (blocking plan baseline)

| # | Decision | Needed by |
|---|---|---|
| 1 | Accept RA proposals R-045…R-054 (in particular R-045 stateful, R-046 Zones, R-053 fragments) — without R-045 the 0.1 scope is invalid. | M0 |
| 2 | Availability: hours/week per person → calendar for §3. | M0 |
| 3 | Monorepo (ADR-0011) — being implemented by the `songbird-fw` import. | M0 |
| 4 | Reference platform (ADR-0007). | M2 → M5 |
| 5 | Minimum kernel: 6.6 (TCX, bpf_link for TC) vs 5.15 LTS (clsact fallback) (ADR-0013). | M0 |
| 6 | 0.1 packaging target: Debian 12/13 `.deb` vs tarball + systemd unit only. | M5 |
| 7 | CI runner for privileged netns tests: GitHub-hosted with sudo vs self-hosted (Agos' Proxmox). | M1 |

---

## 12. Change log

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1.0-draft | 2026-10-19 | Hermes (for Agos review) | Skeleton: roadmap 0.1→1.0, MVP 0.1 scope with in/out rationale and exit criteria, milestones with effort, WBS, ADR list, roles, process, risk register, verification summary, monorepo proposal, open decisions. |
