# Songbird – Requirements Analysis

| | |
|---|---|
| **Document** | RA – Requirements Analysis |
| **Version** | 2.0.5-draft |
| **Status** | Draft for team review |
| **Supersedes** | 2.0.2-draft. Earlier versions are kept as Git tags, see §12 |
| **License** | AGPL-3.0 |

---

## 1. Introduction

### 1.1 Purpose
This document collects, classifies and makes verifiable the requirements of **Songbird**, an open-source network firewall appliance whose goal is to combine the operational simplicity of commercial products such as FortiGate with a modern, declarative, GitOps-friendly architecture built on Linux and eBPF.

It is the input for the Project Plan, the Architectural Design and the Test Plan. Every architectural decision must be traceable to at least one requirement in this document; every requirement must be traceable to at least one verification activity in the Test Plan.

### 1.2 Scope of the product
Songbird is a software appliance (immutable Linux OS image + control-plane application + eBPF data plane) that provides, on commodity x86-64 hardware or virtual machines:

- stateful packet filtering, static routing and NAT for IPv4 (IPv6 and NAT64 are planned after release 1.0, see R-001.3, R-006, R-057);
- essential network services for a small/medium network: DHCP, DNS;
- a web-based management interface and a declarative YAML configuration kept under version control;
- observability (traffic log, metrics, health) and auditing.

Out of scope for the first releases (see §8 – Excluded requirements): VPN termination, L7 inspection/proxying, traffic shaping, SD-WAN, centralised multi-device management.

### 1.3 Intended audience
Project team (design, development, test), external reviewers, early adopters evaluating the product roadmap.

### 1.4 References
- `docs/architecture/` – architectural design: `domain-model.md` (configuration objects and constraints `DM-NN`), `components.md` (components and the requirement → component matrix), `reconciliation.md`, `dataplane.md` (eBPF Data Plane), `adr/` (Architecture Decision Records).
- `schema/` – configuration schema (`v1alpha1`) and validator prototype.
- `songbird-prototypes/` – proof-of-concept code (XDP firewall, Hadron OS image, Go feasibility study, Web UI with a Control Plane slice).
- RFC 2131 (DHCP), RFC 8415 (DHCPv6), RFC 4861 (NDP), RFC 4862 (SLAAC), RFC 6146 (NAT64), RFC 6147 (DNS64), RFC 6238 (TOTP), RFC 8555 (ACME), RFC 5798 (VRRP), RFC 4035 (DNSSEC).

---

## 2. Stakeholders

| Stakeholder | Description | Primary interest |
|---|---|---|
| **Network administrator** | Person who installs, configures and operates Songbird in a small/medium business, lab or home network. Typically familiar with commercial firewalls (FortiGate, pfSense). | Fast, low-error configuration; clear visibility of what is allowed/blocked; safe change management. |
| **Read-only operator / auditor** | Person who needs to inspect configuration, logs and status without changing anything. | Audit trail, exportable configuration, traffic log. |
| **End user of the protected network** | Hosts and people behind the firewall. Never interacts with Songbird directly. | Transparent connectivity, IPv6/IPv4 reachability, low latency. |
| **Development team** | The Songbird maintainers. | Maintainability, testability, single tech stack, reproducible builds. |
| **Open-source community** | Contributors and downstream integrators. | Documented APIs and schema, permissive-enough license, portability. |

---

## 3. Glossary

Terms are capitalised in the requirement text when used in the sense defined here.

| Term | Definition |
|---|---|
| **Physical Interface** | A network device backed by a NIC (e.g. `eth0`, `enp1s0`). |
| **Logical Interface** | A network device derived from a Physical Interface, in particular an 802.1Q VLAN sub-interface (e.g. `eth0.10`) or a PPPoE device. |
| **Interface** | Either a Physical or a Logical Interface. An Interface has no role or type classification (such as LAN/WAN/DMZ): what it may do is determined only by its Zone membership, its Management Services (R-056) and the System Services listening on it (R-058). |
| **Zone** | A named, user-defined set of Interfaces. An Interface belongs to at most one Zone. RuleSets may reference a Zone or any of its member Interfaces; when several RuleSets apply to the same traffic, the more specific one is evaluated first (R-046.1). |
| **RuleSet** | The ordered list of Policies for traffic entering from one Interface or Zone and leaving through another. There is at most one RuleSet per ordered pair; the two sides must be different objects, and no wildcard Interface exists. |
| **Address** | A named configuration object representing an IPv4/IPv6 subnet in CIDR notation, an inclusive IP range, an FQDN, or a MAC address. A single host is a subnet with a /32 (IPv4) or /128 (IPv6) prefix. |
| **Address Group** | A named list of Addresses. Groups are flat: an Address Group does not contain other Address Groups. |
| **Service** | A named configuration object made of one or more protocol entries, each an L4 protocol (TCP, UDP, SCTP, ICMP, ICMPv6, or an IP protocol number) with a port or port range where the protocol has ports (e.g. `dns` = UDP 53 and TCP 53). |
| **Service Group** | A named list of Services, possibly of different protocols. Groups are flat: a Service Group does not contain other Service Groups. |
| **Policy** (firewall rule) | An ordered matching rule inside a RuleSet, with the fields Source, Destination, Service, Action and an optional NAT section. Its incoming and outgoing Interface or Zone are those of the RuleSet. Policies are evaluated in order within their RuleSet; the first match wins. |
| **Action** | The verdict of a Policy: `accept` or `drop`. |
| **Default Deny** | The implicit verdict applied when no RuleSet applies to the Interfaces of a Flow, or no explicit Policy in the applicable RuleSets matches: `drop` + log. |
| **Flow** (session, connection) | A bidirectional sequence of packets identified by the 5-tuple (source address, destination address, source port, destination port, protocol) plus the Interface of first observation. |
| **Stateful** | Property of the filter whereby reply packets belonging to an accepted Flow are accepted without re-evaluating Policies. |
| **Connection Tracking (conntrack)** | The data structure and logic that keeps the state of active Flows. |
| **SNAT / Masquerade** | Source address (and port) translation applied to outgoing Flows, typically to the address of the outgoing Interface. Configured in the NAT section of a Policy. |
| **DNAT / Port Forwarding** | Destination address (and port) translation applied to incoming Flows, typically to publish an internal server. Configured in the NAT section of a Policy, which matches the destination and service **before** translation (the public address and port). |
| **NAT64 / DNS64** | Translation mechanisms allowing IPv6-only clients to reach IPv4-only servers (RFC 6146 / RFC 6147). |
| **Data Plane** | The component that inspects, filters, translates and forwards packets. In Songbird it is implemented with eBPF programs in the Linux kernel (see Constraint C-001). |
| **Control Plane** | The user-space component that manages configuration, compiles it into Data Plane state, runs network services and exposes the API/UI. |
| **Configuration** | The complete desired state of the appliance, expressed as a set of structured YAML files. |
| **Schema** | The formal definition (JSON Schema or equivalent) that every Configuration file must satisfy. |
| **Apply** | The operation that turns a validated Configuration into running state (Data Plane maps, kernel network settings, service configuration). |
| **Atomic Apply** | An Apply that either completes entirely or leaves the system in the previous running state. |
| **Repository** | A Git repository, local or remote, holding the Configuration. |
| **Traffic Log** | The structured record of Flow events (new/accepted, dropped, closed) produced by the Data Plane. |
| **Audit Log** | The structured, tamper-evident record of administrative actions (configuration changes, authentication events). |
| **Event** | A structured record emitted by the Data Plane to the Control Plane about a Flow. |
| **Subsystem** | A major runtime component with its own health status: Data Plane, DHCP, DNS, GitOps, API/UI, Alerting. |
| **System Service** | A network service provided by the firewall itself to the hosts of its networks: DNS server, NTP server, DHCP server. DNS and NTP are enabled on the Interfaces or Zones where they listen (configuration section `systemServices`, field `listenOn`); DHCP is configured with one block per Interface (`systemServices.dhcp.<interface>`). None of them goes through `allowAccess`; the firewall admits the corresponding traffic to itself without a Policy. |
| **Management Service** | A service used to administer the firewall itself: HTTPS management, ICMP echo, and SSH (for the command-line interface, when available). It is enabled per Interface through `allowAccess` (R-056), which contains Management Services only. |
| **User** | A local administrative account of the appliance. |
| **Role** | A named set of permissions assigned to Users (e.g. `admin`, `read-only`). |
| **Color** | A named palette entry with a fixed colour value and a user-defined meaning, used to visually classify related configuration objects (e.g. "green = Backup"). Every configuration object may reference at most one Color. |
| **Initial Setup** | The state of an appliance that boots without a valid Configuration. |
| **A/B Update** | An update model with two system partitions: the new image is written to the inactive one and activated at reboot; failure rolls back to the previous one. |
| **Hot Reload** | Replacing a running Data Plane program with a new version without interrupting packet processing. |

---

## 4. Requirement conventions

### 4.1 Quality criteria
Each requirement shall be **unambiguous**, **verifiable**, **atomic** (one decision), **necessary** (a true stakeholder need), expressed in **stakeholder vocabulary** (see Glossary), and **acceptable** to all stakeholders.

The set of requirements shall be **complete** (boundary, exception and security conditions covered), **concise**, **internally and externally consistent**, and **feasible**.

### 4.2 Identifier
`R-NNN` for a top-level requirement, `R-NNN.M` for a refinement of `R-NNN`. Identifiers are **stable**: they never encode scope, type or priority, and they are never reused after a requirement is removed (removed requirements are kept in §9 with status *Withdrawn*). Constraints use `C-NNN`.

> The numeric part is kept aligned with the v1 numbering (`RGFM12` → `R-012`) so that existing documents and code comments remain readable. See §10 for the full mapping.

### 4.3 Classification columns

| Column | Values |
|---|---|
| **Scope** | **U** – User: directly perceived by the user through the interface. **G** – General: system behaviour not directly visible. |
| **Type** | **F** – Functional. **N** – Non-functional (performance, security, reliability, usability, maintainability, compliance). |
| **Priority** (MoSCoW) | **M** – Must have (release 1.0 is not viable without it). **S** – Should have. **C** – Could have. **W** – Won't have in the current roadmap (explicitly excluded, §8). |
| **Quality** | The ISO/IEC 25010-style characteristic mainly addressed (Security, Reliability, Performance, Usability, Maintainability, Interoperability, Portability, Compliance, Integrity). `–` when purely functional. |
| **Verification** | Method and concrete criterion, see §4.4. |

A child requirement cannot have a higher priority than its parent. If a child is more important than its parent, the parent is promoted.

### 4.4 Verification methods
Each requirement is verified by exactly one primary method. The Test Plan derives its test cases from this column.

| Code | Method | Meaning |
|---|---|---|
| **T-U** | Unit test | Automated test of a single component in isolation (Go `go test`, eBPF `BPF_PROG_TEST_RUN`). Runs in CI without privileges or with CAP_BPF only. |
| **T-I** | Integration test | Automated test across components with real kernel networking, in Linux network namespaces with veth pairs (client – songbird – server). Runs in CI on a privileged runner. |
| **T-S** | System / acceptance test | Scripted or manual end-to-end scenario on a full appliance image (VM), including the Web UI (browser automation). |
| **T-P** | Performance test | Measurement against a numeric target with a defined traffic generator and reference hardware (see C-003). |
| **I** | Inspection | Review of code, configuration, schema, or documents against a checklist. Used for constraints and for properties that are not observable at runtime. |
| **A** | Analysis | Verification by reasoning, modelling or static analysis (e.g. verifying that a crypto primitive/parameter is used). |

---

## 5. Constraints

Constraints are design or technology decisions imposed on the project. They are not stakeholder needs and are not negotiable through MoSCoW; they are traced because the architecture depends on them.

| ID | Constraint | Rationale | Verification |
|---|---|---|---|
| **C-001** | The Data Plane (packet filtering, forwarding decision, NAT) shall be implemented with eBPF programs loaded in the Linux kernel. The iptables/nftables rule engines shall not be used for Policy enforcement. | Performance on commodity hardware; single coherent packet pipeline; full control of state and observability. (Formerly RGFM16.) | **I** – Code review: no `iptables`/`nft` invocation in the Control Plane; `dataplane.md` §2 decision recorded in an ADR. |
| **C-002** | The underlying operating system shall be immutable: root file system mounted read-only, with dedicated writable paths for persistent data and logs. | Reproducible images, A/B updates (R-019), reduced attack surface. (Formerly RGNC22, promoted from Could to constraint because R-019 depends on it.) | **T-S** – On a booted appliance, `findmnt /` reports `ro`; writing outside the data/log paths fails. |
| **C-003** | A reference hardware/virtual platform shall be defined (CPU, NIC driver with native XDP support, kernel version) and used for all performance verification. | Performance requirements are meaningless without a reference. | **I** – Reference platform documented in the Test Plan. |
| **C-004** | The Control Plane shall be implemented in Go as a single statically linked binary; the Data Plane in C compiled to eBPF. | Feasibility study (`PoC-feasibility-study`); single toolchain; fits immutable OS. | **I** – Build pipeline review. |
| **C-005** | The whole Configuration shall be expressed as structured YAML files validated by a Schema. The YAML files in the Repository are the single source of truth; no other persistent store holds Configuration. | Enables GitOps (R-021), import/export (R-020), HA sync (R-023), diff/review. (Formerly RGFS20, promoted from Should to constraint because the architecture is built on it.) | **I** – Architecture review: no database/other store contains Configuration items. |

---

## 6. Functional and non-functional requirements

Ordered by identifier. **Scope**: U/G. **Type**: F/N. **Pri**: M/S/C.

### 6.1 Routing and address translation

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-001** | G | F | M | – | The system shall forward IP packets between Interfaces according to a statically configured routing table. | **T-I** – netns topology with three Interfaces and static routes; `ping`/`iperf3` between any pair succeeds; traffic to an unrouted prefix is not forwarded. |
| R-001.1 | G | F | M | – | The system shall forward IPv4 packets between distinct Physical Interfaces. | **T-I** – as R-001, IPv4, veth as Physical Interfaces. |
| R-001.2 | G | F | M | – | The system shall forward IPv4 packets between distinct Logical Interfaces. | **T-I** – as R-001, IPv4, 802.1Q sub-interfaces on the same veth. |
| R-001.3 | G | F | S | – | The system shall forward IPv6 packets between distinct Physical Interfaces. | **T-I** – as R-001.1, IPv6. |
| R-001.4 | G | F | S | – | The system shall forward IPv6 packets between distinct Logical Interfaces. | **T-I** – as R-001.2, IPv6. |
| R-001.5 | G | F | M | Reliability | The system shall accept several static routes to the same destination, each with a distance and a priority; the active route shall be the one with the lowest distance, then the lowest priority, among those whose outgoing Interface is up. | **T-I** – two routes to the same prefix with different distances; traffic follows the lower distance; bring its outgoing Interface down; traffic follows the other route. |
| **R-002** | G | F | M | – | The system shall support Source NAT (Masquerade) of accepted Flows to the address of the outgoing Interface. | **T-I** – client behind SNAT reaches server; `tcpdump` on server shows the firewall's egress address; reply packets reach the client. TCP, UDP and ICMP echo. |
| R-002.1 | G | F | M | – | The system shall support Source NAT of accepted Flows to an address taken from a configured pool, given as an Address of type subnet or range, in the NAT section of a Policy. | **T-I** – Policy with `snat` to a pool `203.0.113.10-203.0.113.12`; `tcpdump` on the server shows source addresses only from the pool; replies reach the client. |
| R-002.2 | G | F | S | – | When translating to a pool, all concurrent Flows from the same source address shall use the same pool address. | **T-I** – two TCP connections from one client through a pool Policy; the server sees the same source address for both. *(Proposed default, to be confirmed.)* |
| **R-003** | G | F | M | – | The system shall support Destination NAT (Port Forwarding) configured in the NAT section of a Policy, which matches the destination and service before translation. | **T-I** – external client connects to the public address:port of a `dnat` Policy; connection is delivered to the translated address:port; reply is translated back; a Flow to the same address on another port is not translated. |
| **R-004** | G | F | S | Interoperability | On each Interface configured in *router advertisement* mode, the system shall send ICMPv6 Router Advertisements enabling SLAAC (RFC 4862) for the configured prefix. | **T-I** – host in the LAN netns with `accept_ra=1` obtains a global address in the configured prefix within 10 s. |
| **R-005** | G | F | S | Interoperability | The system shall participate in IPv6 Neighbor Discovery (RFC 4861) on all configured Interfaces, and shall never drop NDP messages because of Policies. | **T-I** – with a Default-Deny-only Policy set, `ndisc6`/`ping6` to the firewall's link-local address succeeds; neighbor cache entries are created on both sides. |
| **R-006** | G | F | S | Interoperability | The system shall implement stateful NAT64 (RFC 6146). | **T-I** – IPv6-only client reaches an IPv4-only server through the NAT64 prefix (TCP and UDP). |
| R-006.1 | G | F | S | Interoperability | The NAT64 prefix shall be configurable. | **T-I** – Configuration with a custom /96 prefix; R-006 test passes using that prefix. |
| R-006.2 | G | F | S | Interoperability | The default NAT64 prefix shall be `64:ff9b::/96`. | **T-U** – Configuration without explicit prefix; the compiled Data Plane state contains `64:ff9b::/96`. |
| **R-057** | G | F | M | Security | While IPv6 forwarding (R-001.3, R-001.4) is not implemented, the system shall drop and count IPv6 packets, and shall never forward them unfiltered. | **T-I** – IPv6 traffic between two netns through the firewall is not delivered; the drop counter for IPv6 increases. |

> **Note (v2):** v1 had NAT64 as three separate top-level requirements (RGFM6/7/8). They are merged under R-006 as refinements.
>
> **Note (v2.0.2):** IPv6 is planned after release 1.0. R-001.3, R-001.4, R-004, R-005, R-006 and its refinements, R-017.4 and R-018.6 are lowered from M to S; R-057 states the interim behaviour. Confirmed in 2.0.3 (open issue #9 resolved).
>
> **Note (v2.0.3):** R-002.1 and R-002.2 cover SNAT to an IP pool, already present in the schema (`translateIpTo` on `snat`) and in the 0.1 scope of the Project Plan (open issue #12 resolved).

> **Note (v2.0.4):** Follow-up of the decisions of 2026-10-19. `allowAccess` is a closed list of Management Services (HTTPS, ICMP echo, SSH) and System Services live in `systemServices.<service>.listenOn` (R-056, R-058, glossary). Interfaces have no role: the former `role` field (and its default `internal`) is removed from the schema; the setup-time UI restriction relies on R-056 only (R-031.1) and the DHCP server may run on any Interface (R-017.5). The reserved word `all` is dropped from the domain model; `none` stays reserved.

> **Note (v2.0.5):** Open issue 13 resolved: DHCP is a System Service with one block per Interface (R-017, R-017.6). One object per Configuration file (R-020.7). Palette fixed at 16 Colours (R-055.1). Empty RuleSets are allowed (explicit Default Deny); Services have no source-port criterion.

### 6.2 Configuration objects and Policies

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-009** | U | F | M | Usability | The user interface shall allow the creation, modification, deletion and reordering of Policies. | **T-S** – browser test: create, edit, move and delete a Policy; resulting YAML and running Data Plane state match. |
| R-009.1 | U | F | M | Usability | The user interface shall prevent saving a Policy while a mandatory field without a default value is empty. | **T-S** – attempt to save with empty Source: save is refused and the field is highlighted; no YAML is written. |
| R-009.2 | U | F | S | Usability | The user interface shall allow disabling and re-enabling a Policy without deleting it. | **T-S** – disable a Policy; matching traffic follows the next Policy; the YAML keeps the Policy with `enabled: false`. |
| **R-010** | G | F | M | – | The system shall define a Service as one or more protocol entries, each an L4 protocol with a port or inclusive port range when the protocol has ports. | **T-U** – Schema accepts `{tcp, 443}`, `{udp, 10000-20000}`, `{icmp}`, `[{udp, 53}, {tcp, 53}]`; rejects `{tcp}` without port, `{tcp, 70000}` and `{icmp, 80}`. |
| R-010.1 | G | F | M | – | The system shall provide the predefined Service `any`, matching every protocol and port, which cannot be modified or deleted. It is a different object from the Address `any` (R-012.1), in a separate namespace. | **T-U** – a fresh Configuration contains it; the validator rejects a change and a deletion; a Policy with `service: [any]` and `destination: [any]` resolves each reference in its own namespace. |
| **R-011** | G | F | M | – | The system shall define a Service Group as a list of one or more Services, possibly of different protocols; a Service Group shall not contain another Service Group. | **T-U** – validator accepts a group with a TCP Service and a UDP Service; rejects a group that contains a Service Group, and an empty group. |
| **R-012** | G | F | M | – | The system shall define an Address as a CIDR subnet (IPv4 or IPv6), an inclusive IP range, an FQDN, or a MAC address. A single host shall be expressed as a subnet with a /32 (IPv4) or /128 (IPv6) prefix. | **T-U** – validator accepts `192.168.0.0/24`, `10.0.0.1/32`, `2001:db8::/64`, `172.16.1.1-172.16.1.254`, `www.example.com`, `00:11:22:33:44:55`; rejects `10.0.0.1` without prefix, an inverted range, a mixed-family range, an invalid FQDN and an invalid MAC. |
| R-012.1 | G | F | M | – | The system shall provide the predefined Addresses `any` (`0.0.0.0/0`) and `any6` (`::/0`), which cannot be modified or deleted. | **T-U** – a fresh Configuration contains both; the validator rejects a change of their value and their deletion. |
| R-012.2 | G | F | M | – | The system shall match an FQDN Address against the IP addresses obtained by resolving the name, and shall update the match when the resolution changes. | **T-I** – Policy accepting traffic to an FQDN Address; change the DNS answer in the test resolver; after the TTL, traffic to the new address is accepted and to the old one is not. |
| R-012.3 | G | F | M | – | The system shall match a MAC Address only as Source, against the source MAC of packets received on the incoming Interface; the validator shall reject a MAC Address used as Destination or as NAT translation target. | **T-I** – Policy with a MAC Address as Source accepts the host with that MAC and drops another host on the same segment; **T-U** – validator rejects a MAC Address in `destination`. |
| R-012.4 | G | F | M | Integrity | While the Data Plane does not support FQDN or MAC Addresses (R-012.2, R-012.3), the validator shall reject an enabled Policy that references one, directly or through an Address Group, naming the Address in the error. | **T-U** – Policy with an FQDN Address as Destination → validation error naming that Address; the same Address defined but unused → accepted. |
| R-012.5 | G | F | S | – | An Address or Address Group may be bound to an Interface; a bound object shall be usable as Source only in RuleSets whose incoming side is that Interface or its Zone, and as Destination only in RuleSets whose outgoing side is that Interface or its Zone. | **T-U** – Address bound to `lan1` accepted as Source in `lan1 → wan1` and `internal → wan1`; rejected as Source in `dmz1 → wan1`. |
| **R-013** | G | F | M | – | The system shall define an Address Group as a list of one or more Addresses; an Address Group shall not contain another Address Group. | **T-U** – validator accepts a group of two Addresses; rejects a group that contains an Address Group, and an empty group. |
| **R-014** | G | F | M | – | The system shall define a Policy, inside a RuleSet, by the fields Source, Destination, Service and Action; its incoming and outgoing Interface or Zone are those of the RuleSet. | **T-U** – Schema rejects a Policy missing any of the four fields (except where a default exists); **T-I** – a Policy with all fields produces the expected verdict on matching and non-matching traffic. |
| R-014.1 | G | F | M | – | A Policy shall accept an Address or Address Group as Source. | **T-I** – Policy with a Group as Source accepts traffic from every member and drops traffic from a non-member. |
| R-014.2 | G | F | M | – | A Policy shall accept an Address or Address Group as Destination. | **T-I** – as R-014.1 for Destination. |
| R-014.3 | G | F | M | – | A Policy shall accept a Service or Service Group as Service. | **T-I** – Policy with a Group as Service accepts every member port and drops a non-member port. |
| R-014.4 | G | F | M | – | Policies shall be evaluated in the configured order and the first matching Policy shall determine the verdict. | **T-I** – two overlapping Policies (drop then accept, and the reverse); the verdict follows the first. **T-U** – fuzz test: eBPF classifier vs. reference Go classifier give identical verdicts. |
| R-014.5 | G | F | M | – | A RuleSet shall be defined by an incoming and an outgoing Interface or Zone, different from each other; at most one RuleSet shall exist per ordered pair, and no wildcard Interface shall be accepted. An Interface and the Zone that contains it are different objects. | **T-U** – validator rejects a second RuleSet for the same pair, `lan1 → lan1`, `internal → internal` and a wildcard side; accepts `lan1 → internal` when `lan1` is in `internal`. |
| **R-046** | G | F | M | – | Zones shall be definable as named sets of Interfaces, an Interface belonging to at most one Zone, and RuleSets shall accept a Zone wherever an Interface is accepted. | **T-U** – Schema; **T-I** – RuleSet from Zone `internal` (`lan1`, `lan2`) to `wan1` matches traffic from both members. |
| R-046.1 | G | F | M | – | An Interface that belongs to a Zone may also be referenced on its own in a RuleSet. For a Flow entering Interface *i* and leaving Interface *o* (*i* ≠ *o*), the applicable RuleSets shall be evaluated from the most to the least specific — *i → o*, *i → Zone(o)*, *Zone(i) → o*, *Zone(i) → Zone(o)* — skipping those that do not exist, and the first matching Policy across them shall determine the verdict. | **T-I** – `lan1` and `lan2` in `internal`; RuleSet `lan1 → wan1` drops host A, RuleSet `internal → wan1` accepts all: host A on `lan1` is dropped, host B on `lan1` and hosts on `lan2` are accepted. **T-U** – fuzz test: eBPF classifier vs. reference Go classifier with overlapping Interface and Zone RuleSets. |
| R-046.2 | G | F | S | – | For traffic between two Interfaces of the same Zone that matches no Policy in the applicable RuleSets, the Zone shall define whether it is accepted or denied, with deny as default. | **T-I** – Zone with default setting and no RuleSet: `lan1 → lan2` is dropped; with *allow*: accepted; with *allow* and a RuleSet `lan1 → lan2` that drops host A: host A is dropped, others accepted; all produce Flow Events. |
| R-046.3 | U | F | M | Usability | The user interface and the command-line tool shall show, for every ordered pair of Interfaces, the RuleSets that apply to it in evaluation order (R-046.1), and the user interface shall show this order when a RuleSet is created or edited. | **T-S** – with `lan1 → wan1` and `internal → wan1` defined, the pair `lan1 → wan1` lists both in this order; `songbird` CLI prints the same list. |
| **R-015** | U | F | M | Usability | The user interface shall present Interfaces as a hierarchical tree, with Logical Interfaces nested under their Physical Interface. | **T-S** – with `eth0` and `eth0.10`, `eth0.20` present, the tree shows two children under `eth0`. |
| R-015.1 | U | F | M | Usability | The Interface tree shall reflect the addition or removal of a Logical Interface within 5 s of the kernel event. | **T-S** – add a VLAN sub-interface via netlink; the tree shows it within 5 s (measured by browser automation). |

> **Note (v2.0.2):** R-014 now describes the Policy inside its RuleSet; the Interface/Zone fields moved to the RuleSet (R-014.5). R-046 was accepted from §7 and refined (R-046.1, R-046.2).
>
> **Note (v2.0.3):** Team decisions of 2026-10-19. Groups are flat and a Service may have several protocols (R-010, R-011, R-013; open issue #6). FQDN and MAC Addresses are in release 1.0 (R-012.2, R-012.3) and rejected in Policies until the Data Plane supports them (R-012.4; open issue #7). A single host is a /32 subnet; `any` and `any6` are predefined Addresses (R-012.1). An Interface of a Zone may be used on its own, with the more specific RuleSet evaluated first (R-046.1, R-046.3; open issue #10). A Policy has no log setting: every Flow produces an Event (R-026; open issue #8).
>
> **R-014.3 and R-014.4 are new in v2**: v1 defined Service Groups (RGFM11) but never stated they are usable in Policies, and never stated the first-match semantics on which the whole classifier design relies.

### 6.3 Network services

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-017** | G | F | M | Interoperability | The system shall provide an internal DHCPv4 server (RFC 2131), configured as a System Service with one block per Interface. | **T-I** – client in a LAN netns obtains a lease in the configured pool. |
| R-017.1 | G | F | M | Interoperability | The DHCP server shall allow configuration of the lease duration. | **T-I** – lease time in the OFFER/ACK equals the configured value. |
| R-017.2 | G | F | M | Interoperability | The DHCP server shall allow static address assignment based on client MAC address. | **T-I** – client with reserved MAC always receives the reserved address. |
| R-017.3 | G | F | M | Reliability | The DHCP server shall serve independent pools per Interface, with no address leaking between pools. | **T-I** – two LAN netns, two pools; each client gets an address from its own Interface's pool. |
| R-017.5 | G | F | M | Flexibility | The DHCP server shall be enableable on any Interface: no Interface classification shall restrict where a pool may be served. | **T-U** – validator accepts a pool on an Interface that is also the default-route (WAN) Interface; **T-I** – a client on that Interface obtains a lease. |
| R-017.6 | G | F | M | Integrity | When a DHCP pool advertises the firewall itself as DNS or NTP server (explicitly, or by default when no server is given), the Interface of that pool, or its Zone, shall be among the listening Interfaces of that System Service (R-058); the validator shall reject a Configuration that violates this. | **T-U** – pool on `lan1` without `dnsServers` and DNS not listening on `lan1`/its Zone → validation error naming the pool and the service; adding the Interface to `listenOn` → accepted. |
| R-017.4 | G | F | S | Interoperability | The system shall support DHCPv6 (RFC 8415) including Prefix Delegation as a client on an upstream Interface and as a server on the other Interfaces. | **T-I** – upstream netns runs a DHCPv6-PD server; Songbird obtains a delegated prefix and advertises a sub-prefix on the LAN. |
| **R-018** | G | F | M | Interoperability | The system shall provide a local DNS server. | **T-I** – `dig @songbird` resolves an external name. |
| R-018.1 | G | F | M | Interoperability | In *Forwarder* mode, the DNS server shall cache positive answers and forward unresolved queries to the configured upstream servers. | **T-I** – second identical query is answered with no upstream traffic (observed with `tcpdump` on the upstream link). |
| R-018.2 | G | F | M | Interoperability | The DNS server shall resolve locally defined hostnames. | **T-I** – `dig host.lan` returns the configured address. |
| R-018.3 | G | F | S | Security | The DNS server shall be switchable from Forwarder mode to *Recursive* mode. | **T-I** – Configuration change; the server answers by querying root/TLD servers (observed on the upstream link) instead of the forwarders. |
| R-018.4 | G | F | S | Security | In Recursive mode, the DNS server shall resolve queries by iterating from the root hints to the authoritative servers. | **T-I** – as R-018.3 (same evidence). |
| R-018.5 | G | F | S | Integrity | In Recursive mode, the DNS server shall validate DNSSEC and shall return SERVFAIL for answers that fail validation. | **T-I** – query a known-bad DNSSEC test domain → SERVFAIL; a signed valid domain → answer with AD flag. |
| R-018.6 | G | F | S | Interoperability | The system shall provide DNS64 (RFC 6147) synthesising AAAA records for IPv4-only names, consistent with the NAT64 prefix. | **T-I** – `dig AAAA` of an A-only name returns an address inside the NAT64 prefix. |
| **R-034** | G | N | S | Reliability | The system shall fail over to the secondary upstream DNS server after 3 consecutive timeouts of the primary. | **T-I** – black-hole the primary; 4th query is answered by the secondary. |
| R-034.1 | G | N | S | Reliability | Failover shall complete within 5 s of detecting the primary timeout, without failing in-flight queries. | **T-I** – as R-034, timing measured; no SERVFAIL returned to the client. |
| **R-058** | G | F | M | Security | For each System Service (the DNS server, and the NTP server if R-059 is accepted), the system shall allow configuring the Interfaces or Zones on which it listens (`systemServices.<service>.listenOn`; a Zone stands for all its member Interfaces); the service shall be reachable only through those Interfaces, without a Policy, and on no Interface by default. | **T-I** – DNS server listening on `internal` only: `dig` from `lan1` succeeds, from `wan1` times out with no Policy involved; removing `internal` from the list stops answers on `lan1`. |

### 6.4 Configuration, GitOps and lifecycle

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-019** | G | N | M | Reliability, Integrity | Operating system and application updates shall be atomic (A/B Update): an interrupted or failed update shall leave the previous version running. | **T-S** – power off the VM during update; on reboot the previous version boots and the Configuration is intact. |
| **R-020** | G | F | M | Maintainability | The complete Configuration shall be importable from a set of YAML files. | **T-S** – import a known Configuration on a blank appliance; running state matches. |
| R-020.1 | G | F | M | Maintainability | The complete Configuration shall be exportable as a set of YAML files, and exporting then importing shall yield an identical Configuration. | **T-U** – round-trip test: export → import → export; byte-identical except for ordering-insensitive fields. |
| R-020.2 | G | F | M | Maintainability | Every Configuration file shall be validated against the Schema before Apply. | **T-U** – corpus of valid/invalid YAML files; validator result matches the expected label for 100% of the corpus. |
| R-020.3 | G | F | M | Maintainability | A Configuration that fails validation shall not be applied, and the error shall identify the file, path and reason. | **T-U** – invalid file → non-zero exit, error message contains `file:line` and the failing JSON-path. **T-S** – UI shows the same error. |
| R-020.4 | G | F | M | Maintainability | The Configuration shall include an `interfaces` section defining Physical Interfaces, IPv4 addressing and 802.1Q VLAN sub-interfaces (IPv6 addressing follows R-001.3). | **T-U** – Schema accepts the reference `interfaces` document; rejects an undefined parent for a VLAN. |
| R-020.5 | G | F | M | Security | Secrets in the Configuration (e.g. Repository SSH keys, API tokens, SMTP passwords) shall be stored encrypted at rest. | **I** – no plaintext secret in exported YAML (grep for known test secret); **A** – encryption scheme reviewed (AEAD, key not stored alongside data). |
| R-020.6 | G | F | M | Reliability | Apply shall be atomic: if any part of a new Configuration fails to activate, the system shall restore the previous running state completely. | **T-I** – Configuration where the last block is deliberately unapplicable (e.g. duplicate address); after Apply, Data Plane and kernel state equal a snapshot taken before. |
| R-020.7 | G | F | M | Maintainability | Each Configuration file shall contain exactly one object; the export shall write one file per object, named after the object, in one directory per kind, so that Git diffs and conflicts are confined to the object that changed. | **T-U** – validator rejects a multi-document file; export of the example Configuration produces exactly one file per object in the documented layout; import of that tree yields the same Configuration (R-020.1). |
| **R-021** | U | F | S | Interoperability, Flexibility | Every Configuration change saved through the user interface shall produce a Git commit in the local Repository with a structured message (author, timestamp, summary of changed objects). | **T-S** – after a UI change, `git log -1` shows the commit with the expected message structure and the diff touches only the changed objects. |
| R-021.1 | G | F | S | Interoperability | If a remote Repository is configured, each commit shall be pushed automatically. | **T-S** – remote bare repo receives the commit within 10 s. |
| R-021.2 | G | F | S | Reliability | If push fails, the system shall retry every 60 s and shall display a notification banner in the user interface until the push succeeds. | **T-S** – make the remote unreachable; banner appears; restore the remote; push succeeds at the next retry and the banner disappears. |
| R-021.3 | G | F | S | Security | The system shall authenticate to remote Repositories with SSH private keys. | **T-S** – push to an SSH remote with key auth succeeds; with a wrong key it fails and R-021.2 applies. |
| R-021.4 | G | F | S | Security | The system shall authenticate to remote Repositories with HTTPS personal access tokens. | **T-S** – as R-021.3 with a token (e.g. Gitea in CI). |
| R-021.5 | U | F | S | Integrity | When two changes are saved from the same Configuration revision, the second shall be merged automatically if it affects different objects, and otherwise rejected with a conflict showing the current version; no change shall be lost silently. | **T-S** – two browser sessions edit the same object and save; the second save is refused with a conflict; editing different objects, both saves are committed. |
| **R-031** | G | F | M | Usability | When booting in Initial Setup, the system shall expose a minimal HTTPS setup wizard sufficient to define the first admin User, the Interfaces and their addressing. | **T-S** – fresh image boots; wizard reachable; after completion a valid Configuration exists and the full UI is available. |
| R-031.1 | G | F | S | Security | During Initial Setup, the user interface shall accept connections only through the Interfaces that have HTTPS management enabled (R-056) in the factory default Configuration. | **T-S** – connection attempt through an Interface without HTTPS in the factory default is refused; through the Interface with HTTPS it succeeds. |
| **R-033** | G | F | M | Security | When no RuleSet applies to the Interfaces of a Flow, or no explicit Policy in the applicable RuleSets matches (and R-046.2 does not accept it), the system shall apply Default Deny: drop the packet and record a Traffic Log event. | **T-I** – with an empty Policy set, any forwarded traffic is dropped and a `FLOW_DROP` event with reason `default-deny` is produced. |
| R-033.1 | G | F | S | Reliability | After an unexpected Control Plane crash or a reboot, the system shall restore the last valid running Configuration within 30 s, without manual intervention. | **T-S** – `kill -9` the Control Plane and, separately, reboot the VM; forwarding according to the last Configuration is restored within 30 s (traffic probe at 1 s intervals). |
| **R-036** | G | N | C | Maintainability | The system shall support Hot Reload of Data Plane programs without restarting the Control Plane. | **T-I** – trigger a program update while traffic flows; Control Plane PID unchanged. |
| R-036.1 | G | N | C | Maintainability | Hot Reload shall complete within 2 s with zero packet loss. | **T-P** – constant-rate UDP stream during Hot Reload; receiver counts zero missing sequence numbers. |
| **R-040** | U | F | S | Usability | The user interface shall provide an action to pull the Configuration from the remote Repository. | **T-S** – commit on the remote; click Pull; local Configuration updated and applied. |
| **R-041** | U | F | S | Usability | The user interface shall provide an action to push the local Configuration to the remote Repository. | **T-S** – click Push with pending commits; remote updated. |
| **R-042** | U | F | S | Usability | The user interface shall provide a diff view to resolve conflicts between local and remote Configuration during a pull. | **T-S** – create a conflicting change on both sides; Pull shows a side-by-side diff; choosing a resolution yields a valid, applied Configuration. |

> **Note (v2):** v1 marked R-040/041/042 as "Security"; they are usability features of the GitOps workflow. Scope corrected from G to U (they describe UI actions).

### 6.5 High availability and dynamic routing

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-023** | G | F | C | Reliability | The system shall support a High Availability configuration of two nodes. | **T-S** – two-node testbed; see children. |
| R-023.1 | G | F | C | Reliability | The system shall support Active-Passive HA. | **T-S** – stop the active node; the passive takes over the virtual addresses; a long-lived TCP Flow survives or is re-established within 10 s. |
| R-023.2 | G | F | C | Reliability | The system shall support Active-Active HA. | **T-S** – both nodes forward traffic concurrently; failure of one does not interrupt the other. |
| R-023.3 | G | F | C | Integrity | In HA, both nodes shall reference the same remote Repository and branch. | **I** – Configuration review; **T-U** – validator rejects an HA Configuration with differing remotes. |
| R-023.4 | G | F | C | Reliability | In HA, each node shall independently pull and apply a new commit within 60 s of its push to the designated branch. | **T-S** – push a commit; both nodes show the change applied within 60 s. |
| R-023.5 | G | F | C | Reliability | In HA, the system shall provide virtual addresses via VRRP (RFC 5798). | **T-I** – VRRP advertisements observed; virtual MAC/IP migrate on failover. |
| **R-024** | G | F | C | Interoperability | The system shall support BGP dynamic routing. | **T-I** – peer with a reference BGP daemon (FRR/GoBGP) in a netns; learned routes appear in the routing table and are used for forwarding. |

### 6.6 Security services

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-025** | G | F | C | Security | The system shall integrate a third-party IDS/IPS engine (e.g. Suricata). | **T-S** – engine enabled; a known test signature (e.g. ET test rule) fires on crafted traffic and is visible in the UI. |
| **R-039** | G | F | S | Security | The system shall drop traffic from and to addresses contained in configured threat-intelligence IP lists (e.g. abuse.ch feeds). | **T-I** – mock feed containing a test address; traffic to that address is dropped with reason `blocklist`. |
| R-039.1 | G | F | S | Security | Threat-intelligence lists shall be refreshed automatically at a configurable interval. | **T-I** – change the mock feed; the new address is blocked after the interval. |
| R-039.2 | G | F | S | Reliability | List refresh shall not interrupt traffic. | **T-P** – constant-rate stream during refresh; zero loss. |

### 6.7 Observability, logging and alerting

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-026** | G | F | M | Integrity, Security | The Data Plane shall emit a structured Event for every Flow that is accepted or dropped by a Policy or by Default Deny, containing at least: timestamp, source address, destination address, source port, destination port, protocol, incoming Interface, verdict, matched Policy identifier. | **T-I** – generate one accepted and one dropped Flow; Control Plane receives exactly one `FLOW_NEW` and one `FLOW_DROP` with all fields populated and correct. |
| R-026.1 | G | N | M | Performance | Under a packet flood, Event emission shall be rate-limited so that the Control Plane is not starved; dropped Events shall be counted. | **T-P** – flood at ≥ 1 Mpps of dropped traffic; Control Plane CPU stays below 50% of one core; `events_lost` counter > 0 and consistent with the emitted/received difference. |
| **R-027** | U | F | C | Usability | The user interface shall display real-time charts for troubleshooting. | **T-S** – see children. |
| R-027.1 | U | F | C | Performance | The user interface shall chart global CPU usage. | **T-S** – chart updates at least every 5 s and tracks a synthetic CPU load. |
| R-027.2 | U | F | C | Performance | The user interface shall chart global memory usage. | **T-S** – as R-027.1 with a memory allocation. |
| R-027.3 | U | F | C | Performance | The user interface shall chart network throughput per active Interface. | **T-S** – `iperf3` run; chart value within 10% of `iperf3` report. |
| **R-028** | U | F | S | Usability | The user interface shall provide a Live Traffic Log viewer showing accepted and dropped Flows in tabular form. | **T-S** – generate traffic; rows appear with the Event fields of R-026. |
| R-028.1 | U | F | C | Usability | The Live Traffic Log shall be filterable by verdict, source address, destination address, source port and destination port, updating without page reload. | **T-S** – apply each filter; only matching rows remain. |
| **R-029** | G | N | M | Reliability, Security | Traffic Log events shall be persisted to a dedicated local directory with automatic rotation by size and age. | **T-S** – generate traffic beyond the rotation threshold; rotated files appear; oldest are removed according to the retention policy. |
| **R-030** | G | F | S | Interoperability | The system shall deliver notifications for alert conditions (e.g. push failure, Subsystem degraded, certificate renewal failure). | **T-S** – see children. |
| R-030.1 | G | F | S | Interoperability | Notifications shall be deliverable via e-mail (SMTP). | **T-S** – trigger an alert; message received by a test SMTP sink (MailHog). |
| R-030.2 | G | F | S | Interoperability | Notifications shall be deliverable via HTTP/HTTPS webhook. | **T-S** – test HTTP sink receives a POST with the documented JSON body. |
| R-030.3 | G | F | S | Interoperability | Notifications shall be deliverable via Telegram bot. | **T-S** – mock Telegram API receives `sendMessage`. |
| R-030.4 | G | N | S | Reliability | The Alerting Subsystem shall operate independently of the user interface Subsystem. | **T-S** – stop/crash the UI process; an alert is still delivered. |
| **R-032** | G | F | S | Reliability | The system shall expose an internal HTTP endpoint `/health` returning HTTP 200 and a JSON document with the status (`running`, `degraded`, `stopped`) of every Subsystem. | **T-I** – `curl /health` → 200 and JSON containing all Subsystem keys; stop DNS → its key is `stopped` and overall status is `degraded`. |
| R-032.1 | U | F | S | Usability | The user interface shall include a diagnostics page showing the real-time status of each Subsystem. | **T-S** – stop a Subsystem; page shows it as stopped within 5 s. |
| **R-037** | G | N | M | Compliance | The system shall allow configuration of an IP pseudonymisation (masking) policy for source addresses in the Traffic Log, to support GDPR data-minimisation. | **T-U** – with masking enabled, persisted events contain the masked form (e.g. last 8/80 bits zeroed) and never the original address. |
| R-037.1 | G | N | M | Compliance | Pseudonymisation shall be configurable per Interface. | **T-U** – masking enabled on LAN only; LAN events masked, WAN events not. |

> **Note (v2):** v1 nested the Live Traffic Log (RUFS27.4, S), its filters (RUFC27.5, C) and log persistence (RGNM27.6, M) under the charts requirement (RUFC27, C), violating the parent/child priority rule. They are now independent requirements R-028 and R-029.

### 6.8 Management interface security

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-038** | G | N | S | Security | The user interface and API shall be reachable only over HTTPS. | **T-S** – port scan: only the HTTPS port answers for the management service. |
| R-038.1 | G | N | S | Security | Plain HTTP requests to the management port shall be rejected or redirected to HTTPS. | **T-S** – `curl http://…` returns 301/308 to `https://` or connection refused. |
| R-038.2 | G | F | S | Security | The system shall obtain and renew TLS certificates via ACME (RFC 8555) with the HTTP-01 challenge. | **T-S** – against Pebble (ACME test server) in CI; a valid certificate is installed. |
| R-038.3 | G | F | S | Security | The system shall obtain and renew TLS certificates via ACME with the DNS-01 challenge, for at least one DNS provider API. | **T-S** – Pebble with its challenge test server. |
| R-038.4 | G | N | S | Reliability | The system shall check certificate validity daily and renew when fewer than 30 days remain. | **T-S** – install a certificate expiring in 20 days; after the daily check a renewal request is observed. |
| **R-056** | G | F | M | Security | The system shall allow configuring, per Interface, which Management Services of the firewall itself — HTTPS management, ICMP echo, SSH — are reachable through the addresses of that Interface, with none enabled by default. The set of Management Services is closed: System Services (DNS, NTP, DHCP) are not configured here but through their own listening Interfaces (R-058). | **T-I** – with HTTPS enabled only on LAN, the UI answers on the LAN address and not on the WAN address, from any client; ping follows its own setting. |
| **R-043** | U | F | M | Security | The user interface and API shall require authentication before exposing any functionality other than the login form and `/health`. | **T-S** – every API route except login and `/health` returns 401 without a session. |
| R-043.1 | U | F | M | Security | The system shall support local Users with passwords hashed with bcrypt, cost factor ≥ 12. | **T-U** – stored hash is a bcrypt hash with cost ≥ 12; **A** – code review of the hashing path. |
| R-043.2 | U | F | M | Security | After 5 consecutive failed login attempts from the same source address, further attempts from that address shall be refused for 10 min. | **T-S** – 5 wrong passwords → 6th attempt (correct password) refused with 429/423; succeeds after 10 min (clock-skewed test). |
| R-043.3 | G | N | M | Security | Every failed authentication attempt shall be written to the Audit Log. | **T-S** – wrong password → Audit Log entry with timestamp, source address, username. |
| R-043.4 | U | F | M | Security, Integrity | Every user interface session shall be bound to a signed session token (JWT or HttpOnly+Secure cookie) with configurable expiration. | **T-S** – tampered token → 401; **A** – signing algorithm and key management reviewed. |
| R-043.5 | U | F | M | Security | The default session expiration shall be 8 h. | **T-U** – token issued with default settings expires 8 h after issue. |
| R-043.6 | U | F | S | Security | The system shall support TOTP two-factor authentication (RFC 6238). | **T-S** – login with a TOTP generated by a reference implementation succeeds; wrong code fails. |
| R-043.7 | U | F | S | Security | Two-factor authentication shall be configurable per User. | **T-S** – user A with 2FA, user B without; login flows differ accordingly. |
| R-043.8 | U | F | S | Security | The user interface shall allow creation, modification and deletion of local Users. | **T-S** – CRUD scenario; deleted user cannot log in. |
| R-043.9 | U | F | S | Security | The user interface shall allow creation, modification and deletion of Roles, with at least the built-in Roles `admin` and `read-only`. | **T-S** – `read-only` user receives 403 on every write API route; custom Role CRUD scenario. |
| R-043.10 | G | N | M | Security, Integrity | All authentication events (successful login, failed login, logout, lockout) shall be written to the Audit Log with ISO 8601 timestamp, source address and username. | **T-S** – perform each event type; Audit Log contains the matching entry with all fields. |
| **R-035** | G | N | M | Security, Integrity | Every Configuration change performed through the user interface or API shall be recorded in the Audit Log with ISO 8601 timestamp, User, action, and before/after values. | **T-S** – change a Policy; Audit Log entry contains the diff. |
| R-035.1 | G | N | M | Security | The Audit Log shall be append-only and tamper-evident (each entry chained to the previous by a cryptographic hash), and encrypted at rest. | **A** – design review of the chaining scheme; **T-U** – modifying an entry on disk makes verification fail. |

> **Note (v2):** v1 duplicated the identifier RUFM29.2 for two different requirements (lockout and failed-attempt logging); they are now R-043.2 and R-043.3. v1 RGNM35.1 required "AES-256 and not directly modifiable"; "not modifiable" is not testable as written and is restated as tamper-evidence via hash chaining.

### 6.9 User interface – general

| ID | Scope | Type | Pri | Quality | Requirement | Verification |
|---|---|---|---|---|---|---|
| **R-044** | U | F | C | Usability | The user interface shall offer a dark colour theme. | **T-S** – toggle; computed background colour of the body changes to the dark palette. |
| R-044.1 | U | F | C | Usability | The theme toggle shall be reachable from every page. | **T-S** – browser automation visits every route; toggle is present. |
| **R-055** | U | F | S | Usability | The system shall provide a palette of named Colors, each with a fixed colour value and a user-defined meaning (e.g. "green = Backup/Veeam", "blue = main LAN", "red = DMZ"), and every configuration object shall be assignable to at most one Color, so that related objects are visually classified consistently across the user interface. | **T-S** – assign the same Color to an Address, a Service and a Zone; all three render with that colour in every list view; the palette legend shows the Color with its meaning. **T-U** – validator rejects a reference to an undefined Color. |
| R-055.1 | U | F | S | Usability | The system shall ship a predefined palette of 16 Colours whose colour values cannot be changed; users shall be able to set or edit the meaning of each predefined Color. | **T-U** – validator rejects a predefined Color with a modified colour value; accepts a modified meaning. |
| R-055.2 | U | F | S | Usability | Users shall be able to define additional Colors with their own colour value and meaning; two Colors shall not share the same colour value. | **T-U** – validator accepts a new Color; rejects a second Color with a duplicate colour value. **T-S** – new Color appears in the UI palette and is assignable. |

---

## 7. Proposed additions (to be discussed by the team)

The following requirements are **not** part of v1. They are proposed because the architecture (`dataplane.md`) or the product goal (FortiGate-like simplicity) implicitly depends on them. They are listed with a suggested priority; accept, modify or reject them explicitly. R-046 and R-055 were accepted in 2.0.2 and moved to §6.2 and §6.9.

| ID | Scope | Type | Pri | Quality | Proposed requirement | Verification |
|---|---|---|---|---|---|---|
| **R-045** | G | F | M | – | The system shall be Stateful: reply packets of an accepted Flow shall be forwarded without re-evaluating Policies, and packets that do not belong to an accepted Flow and do not match an accept Policy shall be dropped. | **T-I** – TCP connection accepted LAN→WAN; SYN-ACK from WAN is forwarded with no WAN→LAN Policy; an unsolicited WAN→LAN SYN is dropped. |
| R-045.1 | G | F | M | – | The system shall treat ICMP/ICMPv6 error messages whose embedded header refers to an active Flow as part of that Flow (RELATED). | **T-I** – Path MTU Discovery works across the firewall with a reduced-MTU link downstream. |
| R-045.2 | G | N | M | Performance | Flow timeouts shall be configurable, with defaults: TCP established 3600 s, TCP handshake 30 s, TCP closing 10 s, UDP 60 s (180 s bidirectional), ICMP 30 s. | **T-U** – default values present in compiled state; **T-I** – idle UDP Flow expires after the configured time. |
| **R-047** | G | N | M | Performance | On the reference platform (C-003), the system shall forward at least **1 Mpps** of accepted 64-byte UDP packets per CPU core with 1 000 Policies configured. | **T-P** – TRex/pktgen, 1 000 Policies, measured throughput ≥ target. *(Target value to be agreed.)* |
| **R-048** | G | N | M | Performance | The system shall support at least **1 000 000** concurrent Flows and **4 096** Policies without degradation of R-047 by more than 20%. | **T-P** – fill conntrack to the limit; re-run R-047. *(Values to be agreed.)* |
| **R-049** | G | N | M | Performance | The additional forwarding latency introduced by the Data Plane shall be below **50 µs** at the 99th percentile under 50% of the R-047 load. | **T-P** – hardware timestamping or TRex latency stream. |
| **R-050** | G | F | S | Interoperability | The system shall forward Traffic Log and Audit Log events to a remote syslog server (RFC 5424 over TLS). | **T-S** – syslog-ng sink in CI receives structured events. |
| **R-051** | G | F | S | Interoperability | The system shall expose metrics in Prometheus exposition format. | **T-I** – `curl /metrics` parses with the Prometheus client; per-Policy counters present. |
| **R-052** | G | F | S | Maintainability | The system shall provide a command-line tool `songbird validate <dir>` that validates a Configuration directory against the Schema and exits non-zero on error, usable in CI pipelines independently of the appliance. | **T-U** – corpus test as R-020.2 through the CLI. |
| **R-053** | G | F | M | Security | Policies shall be able to drop IPv4 packets that are not initial fragments, as a configurable behaviour (default: drop). | **T-I** – fragmented UDP datagram; with default settings non-initial fragments are dropped and counted. *(Resolves `dataplane.md` open question 4.)* |
| **R-054** | G | F | S | Security | When a Policy change no longer permits an active Flow, the Flow shall be terminated at its next packet. | **T-I** – long-lived TCP Flow; change Policy to drop; next segment is dropped and a `FLOW_END` event with reason `policy-change` is emitted. *(Resolves `dataplane.md` open question 3; FortiGate default behaviour.)* |
| **R-059** | G | F | S | Interoperability | The system shall synchronise its clock with configured NTP servers and shall be able to act as an NTP server for its networks, as a System Service (R-058). | **T-I** – clock offset below 100 ms from the test NTP server; a client in the LAN netns synchronises with the firewall. *(Proposed in 2.0.3: the schema already has `ntp`, the RA had no requirement.)* |

---

## 8. Excluded requirements (Won't have)

Listed to make the scope boundary explicit. Each may be reconsidered in a future RA revision.

| ID | Excluded capability | Reason |
|---|---|---|
| **W-001** | VPN termination (WireGuard, IPsec, OpenVPN). | High effort; can be delivered later as a separate Subsystem. Candidate for the first post-1.0 feature. |
| **W-002** | Layer-7 inspection, web filtering, TLS interception, application control. | Different product category; conflicts with the simplicity goal and with C-001 (would require user-space proxying). |
| **W-003** | Traffic shaping / QoS. | Can be added later via TC qdisc configuration; not needed for the core use case. |
| **W-004** | SD-WAN, multi-WAN policy routing. | Out of scope for release 1.0. |
| **W-005** | Centralised management of multiple appliances. | The GitOps model (one Repository, many appliances) partially covers it already. |
| **W-006** | Captive portal. | Out of scope. |
| **W-007** | Policies within a single Interface (incoming = outgoing) and hairpin NAT. | A RuleSet requires two different Interfaces or Zones (R-014.5). Hairpin access to a published server can be replaced by internal DNS resolving it to its private address. |

---

## 9. Withdrawn requirements

| v1 ID | Reason |
|---|---|
| RGFM16 | Converted to Constraint C-001 (it is a design decision, not a stakeholder need). |
| RGNC22 | Converted to Constraint C-002. |
| RGFS20 | Converted to Constraint C-005; its children became R-020.x. |
| RGFM7, RGFM8 | Merged into R-006 as refinements R-006.1 and R-006.2. |

---

## 10. Traceability: v1 → v2 identifiers

| v1 | v2 | Change |
|---|---|---|
| RGFM1 – RGFM1.4 | R-001 – R-001.4 | Text clarified ("according to a statically configured routing table"). |
| RGFM2 | R-002 | – |
| RGFM3 | R-003 | References Virtual IP (Glossary). |
| RGFM4 | R-004 | **Disambiguated**: v1 said "SLAAC on all configured interfaces", which conflates client (WAN) and router (LAN) roles. Now: Router Advertisement on RA-mode Interfaces. |
| RGFM5 | R-005 | Added "never dropped by Policies" (needed for consistency with R-033). |
| RGFM6, RGFM7, RGFM8 | R-006, R-006.1, R-006.2 | Merged. |
| RUFM9, RUFM9.1 | R-009, R-009.1 | Added modification/deletion/reordering (v1 only said "creation"). |
| RGFM10 | R-010 | Port range made explicit. |
| RGFM11 | R-011 | Nesting + cycle rejection made explicit. |
| RGFM12 | R-012 | CIDR notation explicit; IPv6 explicit. |
| RGFM13 | R-013 | As R-011. |
| RGFM14, 14.1, 14.2 | R-014, R-014.1, R-014.2 | – |
| – | R-014.3, R-014.4 | **New**: Service Group in Policy; first-match semantics. |
| RUFM15, RUFM15.1 | R-015, R-015.1 | – |
| RGFM16 | C-001 | Constraint. |
| RGFM17 – 17.4 | R-017 – R-017.4 | 17.4 clarified (PD client on WAN, server on LAN). |
| RGFM18 – 18.6 | R-018 – R-018.6 | 18.5 made testable (SERVFAIL on validation failure). |
| RGNM19 | R-019 | – |
| RGFS20 | C-005 | Constraint. |
| RGFS20.1 | R-020 | Promoted to top level. **Priority S → M** (import is the only way to deliver a Configuration to a fresh appliance). |
| RGFS20.2 | R-020.1 | Round-trip criterion added. **S → M**. |
| RGFS20.3 | R-020.2 | **S → M**. |
| RGFS20.4 | R-020.3 | Error content specified. **S → M**. |
| RGFS20.5 | R-020.4 | **S → M**. |
| RGFM20.6 | R-020.5 | – |
| RGFS20.7 | R-020.6 | **S → M** (the two-generation map design exists for this). |
| RUFS21 | R-021 | Commit message content specified; push split into R-021.1. |
| RGFS21.1 | R-021.2 | – |
| RGFS21.2 (SSH) | R-021.3 | **Duplicate ID fixed.** |
| RGFS21.2 (token) | R-021.4 | **Duplicate ID fixed.** |
| RGNC22 | C-002 | Constraint. |
| RGFC23 – 23.5 | R-023 – R-023.5 | – |
| RGFC24 | R-024 | – |
| RGFC25 | R-025 | – |
| RGFM26 | R-026 | "Matched Policy identifier" added; rate limiting split into R-026.1 (**new**). |
| RUFC27 – 27.3 | R-027 – R-027.3 | – |
| RUFS27.4 | R-028 | **Un-nested** (child priority S > parent C). |
| RUFC27.5 | R-028.1 | – |
| RGNM27.6 | R-029 | **Un-nested** (child priority M > parent C). |
| RGFS28 – 28.4 | R-038 – R-038.4 | Renumbered to avoid clash with R-028. Type corrected F → N for 28, 28.1, 28.4. |
| RUFM29 | R-043 | Renumbered to avoid clash with R-029. `/health` exempted explicitly. |
| RUFM29.1 | R-043.1 | – |
| RUFM29.2 (lockout) | R-043.2 | **Duplicate ID fixed.** |
| RUFM29.2 (logging) | R-043.3 | **Duplicate ID fixed.** Scope corrected U → G, type F → N. |
| RUFM29.3, 29.4 | R-043.4, R-043.5 | – |
| RUFS29.5 – 29.12 | R-043.6 – R-043.9 | Create/modify/delete of Users merged into one (R-043.8); same for Roles (R-043.9) — they were three atomic requirements each only in form, not in substance. |
| RGNM29.13 | R-043.10 | – |
| RUFS30 – 30.3 | R-030 – R-030.3 | – |
| RGNM30.4 | R-030.4 | ID said M, column said S → **S** kept (column wins). |
| RGFM31, RGFS31.1 | R-031, R-031.1 | Wizard content specified. |
| RGFS32, RUFS32.1 | R-032, R-032.1 | Status vocabulary fixed. |
| RGFM33, RGFS33.1 | R-033, R-033.1 | – |
| RGFN34, 34.1 | R-034, R-034.1 | ID said F, column said N → **N** kept. |
| RGNM35, 35.1 | R-035, R-035.1 | 35.1 restated as tamper-evidence. |
| RGFN36, 36.1 | R-036, R-036.1 | ID said F, column said N → **N** kept. |
| RGFN37, 37.1 | R-037, R-037.1 | As above. |
| RUFC38, 38.1 | R-044, R-044.1 | Renumbered to avoid clash with R-038. |
| RGFM39 – 39.2 | R-039 – R-039.2 | ID said M, column said S → **S** kept. |
| RGFM40, 41, 42 | R-040, R-041, R-042 | ID said G/M, column said U/S → **U, S** kept. Quality corrected Security → Usability. |

---

## 11. Open issues

| # | Issue | Owner | Proposed resolution |
|---|---|---|---|
| 1 | Numeric targets of R-047/R-048/R-049 and the reference platform C-003. | Team | Decide after a first benchmark of the PoC on the intended hardware (ADR-0006, ADR-0007). |
| 2 | Acceptance of proposed R-045, R-047…R-054 (R-046 and R-055 accepted in 2.0.2). | Team | Review meeting; each proposal accepted/rejected with a one-line rationale in this section. ADR-0004 and ADR-0005 depend on R-054 and R-053. |
| 11 | Interpretation of R-020.5 "key not stored alongside data" on hardware without a TPM (ADR-0009). | Team | Kept open: investigate a solution (e.g. key derived from an admin passphrase at boot, or an external key file) before 0.3. |
| 13 | DHCP server configuration: per Interface or in the System Services section. | `systemServices.dhcp` with one block per Interface (R-017); DHCP may run on any Interface (R-017.5); coherence with DNS/NTP `listenOn` enforced (R-017.6). Decided 2026-10-19. |
| 14 | Acceptance of R-059 (NTP client and server), proposed in 2.0.3. | Team | Review meeting. |

### Resolved

| # | Issue | Resolution |
|---|---|---|
| 3 | Does C-001 exclude `nf_conntrack`? | Moot: connection tracking is implemented in BPF maps and `nf_conntrack` is not used (ADR-0003). C-001 unchanged. |
| 4 | Interface/Zone fields set to `any`. | Not allowed; one RuleSet per ordered pair of different Interfaces or Zones (R-014.5). |
| 5 | Concurrent editing by two administrators. | Optimistic locking on the Configuration revision (R-021.5). |
| 6 | Groups flat or nested; Service with one or several protocols. | Flat groups; a Service has one or more protocol entries; a Service Group may mix protocols (R-010, R-011, R-013). Decided 2026-10-19. |
| 7 | FQDN and MAC Addresses. | In release 1.0 (R-012.2, R-012.3); rejected in Policies until the Data Plane supports them (R-012.4). A single host is a /32 subnet (R-012). Decided 2026-10-19. |
| 8 | Per-Policy log level versus R-026. | Field removed from the Policy; R-026 unchanged. Decided 2026-10-19. |
| 9 | IPv6 requirements lowered from M to S. | Confirmed. Decided 2026-10-19. |
| 10 | Traffic between members of the same Zone; use of member Interfaces. | Member Interfaces may be used on their own; the more specific RuleSet is evaluated first and the order is shown to the user (R-046.1, R-046.3); R-046.2 applies when no Policy matches; source and destination of a RuleSet always differ (R-014.5). Decided 2026-10-19. |
| 12 | SNAT to an IP pool. | Added as R-002.1 and R-002.2. Decided 2026-10-19. |

---

## 12. Change log

Every reviewed version is kept as a Git tag. Versions up to 2.0.2 are tagged in the archived repository `songbird-requirements-analysis`, where the RA was `README.md` (`git show <tag>:README.md`). From 2.0.3 on, the RA is `docs/requirements-analysis.md` in `songbird-fw` and reviewed versions are tagged there with the same `ra-v` prefix.

| Version | Tag | Commit |
|---|---|---|
| 1.0 | `ra-v1.0` | `577c62f` |
| 2.0.0-draft | `ra-v2.0.0` | `dc2b532` |
| 2.0.1-draft | `ra-v2.0.1` | `1a85095` |
| 2.0.2-draft | `ra-v2.0.2` (to be created) | `47fa3fe` |


| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-06 | Team | Initial table (RGFM-style identifiers). |
| 2.0.0-draft | 2026-10-17 | Hermes (for Agos review) | Stable identifiers; glossary, stakeholders, constraints, verification column, exclusions, traceability table; 4 duplicate/inconsistent IDs fixed; 3 parent/child priority violations fixed; 10 proposed additions; 5 open issues. |
| 2.0.1-draft | 2026-10-17 | Hermes (for Agos review) | Added R-055/.1/.2 (Colour palette with meaning) and the *Colour* glossary entry, traced from the `Color` kind decision in `songbird-yaml-schema`. |
| 2.0.2-draft | 2026-10-18 | Claude (for team review) | Aligned with the architecture (domain model v0.6, ADR-0001…0010) and with the schema on colors, NAT and names. Glossary: *RuleSet* added, *Zone*, *Policy*, *Default Deny*, *SNAT*, *DNAT* updated, *Virtual IP* removed, *Colour* renamed *Color*. R-003, R-014, R-020.4, R-033 reworded. New: R-001.5 (static routes with distance and priority), R-009.2 (disable a Policy), R-014.5 (RuleSet), R-021.5 (concurrent edits), R-056 (management access per Interface), R-057 (interim IPv6 drop), W-007 (intra-interface Policies, hairpin NAT). R-046 (+ R-046.1, R-046.2) and R-055 family accepted. IPv6 requirements lowered from M to S (to be confirmed). Open issues 3–5 resolved; 6–12 added. |
| 2.0.5-draft | 2026-10-19 | Hermes (for team review) | Schema open questions closed by the team: DHCP in `systemServices.dhcp` (R-017 reworded, new R-017.6 coherence rule, open issue 13 resolved); one object per file (new R-020.7); palette of 16 Colours (R-055.1); empty RuleSet allowed; no source port on Services. |
| 2.0.4-draft | 2026-10-19 | Hermes (for team review) | Follow-up of the 2026-10-19 decisions. Glossary: *Interface* (no role), *System Service* (`systemServices` / `listenOn`), *Management Service* (closed list incl. SSH). R-056 and R-058 reworded; new R-017.5 (DHCP on any Interface). Open issue 13 extended with the DHCP→DNS/NTP coherence rule. Schema aligned in the same change: `allowAccess` enum, `role` removed, `systemServices.listenOn`, flat groups, `any`/`any6`/Service `any` as predefined objects, `all` no longer reserved. |
| 2.0.3-draft | 2026-10-19 | Claude (for team review) | Team decisions of 2026-10-19. Glossary: *Zone*, *RuleSet*, *Address*, *Address Group*, *Service*, *Service Group*, *Default Deny* updated; *System Service* and *Management Service* added. R-010, R-011, R-012, R-013 rewritten, R-010.1 added (flat groups, multi-protocol Service, FQDN and MAC, /32 for hosts); R-014.5, R-046.1, R-046.2, R-017.4, R-031, R-031.1, R-056 reworded. New: R-002.1, R-002.2 (SNAT pool), R-012.1–R-012.5, R-046.3 (RuleSet evaluation order shown to the user), R-058 (listening Interfaces of System Services); proposed R-059 (NTP). Open issues 6–10 and 12 resolved; 11 kept open; 13 and 14 added. Moved to the `songbird-fw` monorepo. |
