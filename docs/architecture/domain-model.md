# Domain Model — Songbird

| | |
|---|---|
| Version | 0.7-draft |
| Aligned with | Requirements Analysis v2.0.3-draft (proposed); schema `v1alpha1` in [`schema/`](../../schema/) for colors, NAT and names; team decisions of 2026-10-19 for the remaining differences |

Conceptual model of the firewall's **configuration objects**. It describes what exists, how it is connected, and which constraints always hold. It contains no technical details (eBPF, netlink, exact YAML format) and no runtime state (conntrack, leases, sessions).

The YAML schema (JSON Schema/CUE), the Validator rules and the Go structs all derive from this model: if the model changes, all three change.

**Relation with the YAML schema.** Where this model and the schema disagree on colors, NAT and names, the schema has precedence (team decision, 2026-10-18). The other differences were settled by the team on 2026-10-19 and are reflected here; the schema will be aligned by its owner (see [Schema alignment](#schema-alignment)).

Constraint identifiers are `DM-NN` (Domain Model), to avoid clashing with the RA constraints `C-NNN`. Like RA identifiers, they are stable and never reused: a removed constraint stays in the list as *Deferred* or *Withdrawn*.

## Scope of this version

The model covers **IPv4 only**. IPv6 and Router Advertisement are deferred (see [Deferred](#deferred)).

## Changes

**0.7** (this version) — team decisions of 2026-10-19

- **Interface `role` removed.** A DHCP server may run on any Interface (DM-24 withdrawn). The Initial Setup restriction of R-031.1 now relies on `allowAccess` in the factory default Configuration.
- **`allowAccess` stays management only** (`ping`, `https`; later `ssh`). DNS and NTP servers are **System Services** that declare the Interfaces or Zones where they listen (`systemServices`, `listenOn`) and open their own ports there (DM-34 rewritten, DM-45 added). The DHCP server stays in the Interface for now (open question).
- **Member Interfaces of a Zone may be used on their own** in RuleSets. The applicable RuleSets are evaluated from the most to the least specific (DM-42); `from` and `to` are always different objects, and an Interface differs from its Zone (DM-06, DM-07, DM-38, DM-39 rewritten).
- **Groups are flat; a Service has one or more protocol entries**, and a ServiceGroup may mix protocols (Service, DM-17, DM-18 rewritten).
- **Address types**: `subnet`, `range`, `fqdn`, `mac`. The `ip` type is removed: a single host is a `/32` subnet. `fqdn` and `mac` are in release 1.0 but rejected in enabled Policies until the Data Plane supports them (DM-43); `mac` is valid only as source (DM-44).
- **`any` and `any6`** are predefined Addresses (`0.0.0.0/0`, `::/0`); `any` is also a predefined Service. `all` and `none` stay reserved (DM-21 rewritten).
- **`Address.interface` is a restriction**, as in FortiGate (DM-12 confirmed).
- **StaticRoute**: routes sharing destination, distance and priority stay rejected (no ECMP); defaults `distance` 10 and `priority` 1 are decided.

**0.6** — aligned with the YAML schema

- **Names**: the schema's naming rules apply ([Names](#names)): lowercase DNS-label names, reserved `any`/`all`/`none`, four shared namespaces, optional system-generated `uuid`. Common metadata (`comment`, `color`, `category`, `labels`) on every object. Interface gets `device` (the Linux netdev name). Field names follow the schema: `rules`, `source`, `destination`, `service`.
- **Color** (was Colour): `hex` and `predefined` (were `value` and `builtin`); the meaning is the object's `comment`; a Color has no color itself (DM-33 rewritten).
- **DNAT is a section of the Policy**, matched **before** translation, as in the schema ([ADR-0010](../../adr/0010-dnat-in-policy.md)). VirtualIP and IpPool removed; `nat` is `{type: snat|dnat, translateIpTo, translateServiceTo}`. DM-10, DM-13, DM-19, DM-20, DM-35 rewritten or withdrawn; DM-40 and DM-41 added.

**0.5**

- **Zone** is again a set of Interfaces, as in FortiGate and in the RA glossary (R-046). The directed pair that holds the ordered Policies is now a **RuleSet** (`from` → `to`), matching the YAML schema.
- `from` and `to` reference an Interface or a Zone. An Interface that belongs to a Zone is referenced through its Zone, except for traffic between two Interfaces of the same Zone (DM-37, DM-38, DM-39).
- DM-06, DM-07, DM-09, DM-11, DM-12 and DM-36 rewritten for RuleSets.

**0.4**

- Three constraints found while aligning the Data Plane design (`dataplane.md` v3): DM-34 (active services open their ports on the Interface), DM-35 (Virtual IP versus management port), DM-36 (per-Zone Policy limit).
- `fqdn` and `mac` Address types flagged as not yet supported by the Data Plane.
- `allowAccess` follows the **owner rule**: it applies to the addresses of the Interface, like FortiGate (DM-05).

**0.3**

- IPv6 removed for now: DHCPv6 client/server, Router Advertisement, IPv6 addresses and routes (DM-30, DM-31, DM-32 deferred).
- **AddressGroup**: all members belong to the group's Interface, or none of them belong to any (DM-16 tightened).
- **StaticRoute**: `distance` and `priority` added, with a preference rule (DM-23 rewritten).

**0.2**

- **Zone** is a first-class object: a named, directed pair (source Interface, destination Interface), e.g. `LAN-WAN1`. A Policy references one Zone instead of two Interfaces.
- **Policy** `sources`, `destinations` and `services` are lists. `logLevel` removed. `deny` renamed `drop`.
- **AddressGroup** and **ServiceGroup** added, flat (no nesting). **StaticRoute** added.
- **Interface**: physical/VLAN distinction, DHCP reservations by MAC. `allowAccess` reduced to `ping` and `https`.
- **Colour** palette added; every configuration object may reference one Colour.

## Diagrams

The model is split into three diagrams for readability. `Interface` appears in more than one.

### 1. Interfaces, DHCP and routing

```mermaid
classDiagram
    class Interface {
        +String type
        +Integer vlanId
        +List~String~ addresses
        +List~String~ allowAccess
    }
    class DhcpConfig {
        +Boolean enabled
        +String rangeStart
        +String rangeEnd
        +String gateway
        +List~String~ dnsServers
        +Integer leaseTime
    }
    class DhcpReservation {
        +String mac
        +String ip
    }
    class StaticRoute {
        +String destination
        +String gateway
        +Integer distance
        +Integer priority
    }

    Interface "0..*" --> "0..1" Interface : parent
    Interface "1" *-- "0..1" DhcpConfig
    DhcpConfig "1" *-- "0..*" DhcpReservation
    StaticRoute "0..*" --> "1" Interface : outInterface
```

### 2. Zones, RuleSets, Policies and the objects they reference

```mermaid
classDiagram
    class NetworkRef {
        <<abstract>>
    }
    class Interface
    class Zone {
        +String intraZoneTraffic
    }
    class RuleSet
    class Policy {
        +String action
        +Boolean enabled
    }
    class NatConfig {
        +String type
    }
    class AddressRef {
        <<abstract>>
    }
    class Address {
        +String type
        +String value
    }
    class AddressGroup
    class InterfaceAddresses {
        <<derived>>
    }
    class ServiceRef {
        <<abstract>>
    }
    class Service {
        +Boolean predefined
    }
    class ProtocolEntry {
        +String protocol
        +String port
        +Integer icmpType
        +Integer icmpCode
        +Integer protocolNumber
    }
    class ServiceGroup

    NetworkRef <|-- Interface
    NetworkRef <|-- Zone
    Zone "0..1" o-- "1..*" Interface : interfaces
    RuleSet --> NetworkRef : from
    RuleSet --> NetworkRef : to
    RuleSet "1" *-- "0..*" Policy : ordered rules
    Policy "1" --> "1..*" AddressRef : source
    Policy "1" --> "1..*" AddressRef : destination
    Policy "1" --> "1..*" ServiceRef : service
    Policy "1" *-- "0..1" NatConfig : nat
    NatConfig "0..*" --> "0..1" Address : translateIpTo
    NatConfig "0..*" --> "0..1" Service : translateServiceTo

    AddressRef <|-- Address
    AddressRef <|-- AddressGroup
    AddressRef <|-- InterfaceAddresses
    ServiceRef <|-- Service
    ServiceRef <|-- ServiceGroup
    Service "1" *-- "1..*" ProtocolEntry : protocols

    AddressGroup "0..*" --> "1..*" Address : members
    ServiceGroup "0..*" --> "1..*" Service : members
    Address "0..*" --> "0..1" Interface : interface
    AddressGroup "0..*" --> "0..1" Interface : interface
    InterfaceAddresses "1" --> "1" Interface : of
```

### 3. Common base: metadata and Color

```mermaid
classDiagram
    class ConfigObject {
        <<abstract>>
        +String name
        +String uuid
        +String comment
        +String category
        +Map labels
    }
    class Color {
        +String hex
        +Boolean predefined
    }
    ConfigObject <|-- Color
    ConfigObject "0..*" --> "0..1" Color : color
```

### 4. System Services

```mermaid
classDiagram
    class SystemServices
    class DnsService {
        +String mode
        +List~String~ upstreams
    }
    class NtpService {
        +List~String~ servers
    }
    class NetworkRef {
        <<abstract>>
    }
    SystemServices "1" *-- "0..1" DnsService : dns
    SystemServices "1" *-- "0..1" NtpService : ntp
    DnsService "0..*" --> "0..*" NetworkRef : listenOn
    NtpService "0..*" --> "0..*" NetworkRef : listenOn
```

`ConfigObject` is extended by: Interface, Zone, RuleSet, Address, AddressGroup, Service, ServiceGroup, StaticRoute, Color. Their metadata are therefore not repeated in the tables below. SystemServices is a single, unnamed section of the system configuration. A Policy is not a file of its own: it has `name`, `uuid`, `comment` and `enabled` inside its RuleSet. `InterfaceAddresses` is derived and has no metadata. The nested classes (DhcpConfig, DhcpReservation, NatConfig, ProtocolEntry, DnsService, NtpService) have none. A Color cannot reference a Color (DM-33).

## Names

Adopted from `songbird-yaml-schema` (design decisions 1, 2, 8 and 10).

| Rule | Value |
|---|---|
| Primary key | `name`. Human-readable, stable, used in references and Git diffs |
| Format | `^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$`, at most 63 characters (lowercase DNS-label-like) |
| Reserved | `all`, `none`. `any` and `any6` are not reserved words but the names of predefined objects (DM-21) |
| `uuid` | Optional, generated by the system on first save, never written by hand; lets the UI follow renames |
| Namespaces | *address*: Address, AddressGroup · *service*: Service, ServiceGroup · *network*: Interface, Zone · *color*: Color · RuleSets have their own · Policy names are unique within their RuleSet |
| Interface | `name` is what users see and reference (`wan`, `lan1`); `device` is the Linux netdev (`enp1s0`). A VLAN references its parent by object name, not by device |

Consequences on this model:

- Predefined Services use valid names: `http`, `https`, `dns`, … (no longer `HTTP`, `ALL`).
- "Any address" is the predefined Address `any` (`0.0.0.0/0`), and `any6` (`::/0`) once IPv6 is supported; "any service" is the predefined Service `any`. They are ordinary references, not keywords. No object may be named `all`.
- The derived name `<interface> addresses` contains a space and is not a valid name. Its new form is still open (see InterfaceAddresses).

**Legend.** Solid arrow = reference (by name in the YAML). Filled diamond = composition (nested in the YAML). Hollow diamond = aggregation (a Zone groups existing Interfaces). Triangle = specialisation. The Policies are composed in their RuleSet: they are nested in its YAML. `<<derived>>` = computed concept with no YAML file of its own.

## Classes

### Interface

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| type | enum (physical, vlan) | yes | |
| device | Linux netdev name | for `physical` | e.g. `enp1s0`; absent for `vlan` |
| parent | ref Interface | for `vlan` | the physical Interface carrying the 802.1Q tag (DM-03) |
| vlanId | integer 1–4094 | for `vlan` | |
| addresses | list of IPv4 address/prefix | yes | primary, secondary and additional subnets |
| allowAccess | list of enum (ping, https) | no | what may be reached on the firewall **through the addresses of this Interface**, whatever Interface the packet arrives on; default: none (DM-05) |
| dhcp | DhcpConfig | no | DHCP server on this Interface; allowed on any Interface. Its place may move to SystemServices (open question) |

### DhcpConfig (composed in Interface)

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| enabled | boolean | yes | allows preconfiguring without activating |
| rangeStart, rangeEnd | IPv4 | yes | |
| gateway | IPv4 | no | default: the Interface IP in the range's subnet |
| dnsServers | list of IPv4 | no | default: the Interface IP, if the DNS forwarder is enabled |
| leaseTime | seconds | no | default to be defined (e.g. 24 h) |
| reservations | list of DhcpReservation | no | static assignment by MAC (R-017.2) |

### DhcpReservation (composed in DhcpConfig)

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| mac | MAC address | yes | unique within the DhcpConfig |
| ip | IPv4 | yes | unique within the DhcpConfig (DM-29) |

### StaticRoute

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| destination | IPv4/prefix | yes | |
| gateway | IPv4 | yes | |
| outInterface | ref Interface | yes | |
| distance | integer 1–255 | no | lower is preferred; default 10 |
| priority | integer 1–65535 | no | tie-breaker among routes with the same distance, lower is preferred; default 1 |

**Preference rule** (DM-23). Among the routes to the same `destination`, the active one is the route with the lowest `distance`; if several share it, the one with the lowest `priority`. The others are *backup routes*. A route is eligible only while its `outInterface` is up: this is runtime state and is handled by the Observer, not stored in the model.

### Zone

A named **set of Interfaces** treated alike, as in FortiGate (e.g. `internal` = `lan1` + `lan2`). Membership is declared only in the Zone.

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| interfaces | list of ref Interface | yes | at least one; an Interface belongs to at most one Zone (DM-37) |
| intraZoneTraffic | allow / deny | no | verdict between two member Interfaces when no Policy of the applicable RuleSets matches; default `deny` (DM-39) |

### RuleSet

The ordered Policies for traffic entering from `from` and leaving through `to`.

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| from | ref Interface or Zone | yes | where the traffic enters |
| to | ref Interface or Zone | yes | where the traffic leaves; must differ from `from` (DM-06) |
| rules | ordered list of Policy | yes (may be empty) | position = priority; the first match wins |

A RuleSet is **directed**: `lan1 → wan1` and `wan1 → lan1` are two different RuleSets. In the UI each RuleSet is an expandable section listing its Policies, and Policies never repeat the Interfaces.

Examples (`internal` = `lan1` + `lan2`):

| `from` → `to` | Allowed? | Why |
|---|---|---|
| `lan1 → wan1` | yes | plain Interfaces, also when `lan1` is in a Zone (DM-38) |
| `internal → wan1` | yes | Zone to Interface |
| `lan1 → internal` | yes | an Interface differs from the Zone that contains it (DM-06); it governs `lan1 → lan2` |
| `lan1 → lan2` | yes | two members of the same Zone |
| `lan1 → lan1` | **no** | `from = to` (DM-06) |
| `internal → internal` | **no** | `from = to` (DM-06) |

**Evaluation order** (DM-42). A Flow entering Interface *i* and leaving Interface *o* (*i* ≠ *o*) may be governed by up to four RuleSets. They are evaluated from the most to the least specific, skipping those that do not exist:

1. *i* → *o*
2. *i* → Zone(*o*)
3. Zone(*i*) → *o*
4. Zone(*i*) → Zone(*o*) (never exists when *i* and *o* are in the same Zone)

The first enabled Policy that matches, across the whole sequence, decides. If none matches: `intraZoneTraffic` when *i* and *o* are in the same Zone (DM-39), Default Deny otherwise. A drop Policy in a more specific RuleSet therefore wins over an accept in a Zone RuleSet, and a Zone RuleSet acts as the fallback for its members.

The user must be able to see this order: the UI and the CLI show, for every pair of Interfaces, the applicable RuleSets in evaluation order (R-046.3). The Compiler flattens each sequence into one *effective* list per Interface pair (`dataplane.md` §7.1).

### Policy

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| name | name | yes | unique within the RuleSet; reported in the Traffic Log (R-026) |
| ruleSet | ref RuleSet | yes | implied by the RuleSet that contains the Policy |
| source | list of ref (Address, AddressGroup) | yes | non-empty |
| destination | list of ref (Address, AddressGroup, InterfaceAddresses) | yes | non-empty; for `dnat`, the address **before** translation (DM-40) |
| service | list of ref (Service, ServiceGroup) | yes | non-empty; for `dnat`, the service **before** translation |
| action | accept / drop | yes | |
| nat | NatConfig | no | absent = no NAT; forbidden with `drop` (DM-13) |
| enabled | boolean | no | default true |

Position is **not** an attribute: it is the order in the RuleSet's list.

### NatConfig (composed in Policy)

As in the schema ([ADR-0010](../../adr/0010-dnat-in-policy.md)).

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| type | snat / dnat | yes | |
| translateIpTo | ref Address | `dnat`: yes · `snat`: no | `snat`: omitted = masquerade to the primary address of the outgoing Interface; set = an Address (subnet or range) used as IP pool. `dnat`: a single-host Address (/32) or a range |
| translateServiceTo | ref Service | no, `dnat` only | one tcp/udp/sctp entry with a single port; omitted = port unchanged |

A `dnat` Policy matches its `destination` and `service` **before** translation, i.e. the public address and port, and then rewrites them.

### Address (extends AddressRef)

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| type | enum: subnet, range, fqdn, mac | yes | a single host is a `/32` subnet. `fqdn` and `mac` are in release 1.0 but not yet supported by the Data Plane (DM-43, `dataplane.md` §7.3) |
| value | depends on type | yes | subnet: CIDR; range: start-end; fqdn: name; mac: MAC address |
| interface | ref Interface | no | if present, **restricts** where the Address can be used, as in FortiGate (DM-12) |


### AddressGroup (extends AddressRef)

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| interface | ref Interface | no | must be the Interface of every member, or absent when no member has one (DM-16) |
| members | list of ref Address | yes | non-empty, flat (no nested groups) |

### InterfaceAddresses (derived, extends AddressRef)

Derived name, format **to be decided** (the former `<interface> addresses` is not a valid name, see [Names](#names)), resolved to the subnets in `Interface.addresses`. It has no YAML file: it follows IP changes automatically, and the Compiler recompiles the Policies that use it. It is bound to its Interface like an Address with `interface` set.

### Service (extends ServiceRef)

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| protocols | list of ProtocolEntry | yes | at least one, no duplicates (DM-17); e.g. `dns` = UDP 53 and TCP 53 |
| predefined | boolean | no | marks objects shipped with the system, such as `any`, `http`, `https`, `dns` (DM-21) |

### ProtocolEntry (composed in Service)

As in the schema.

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| protocol | enum (tcp, udp, sctp, icmp, icmpv6, ip) | yes | `icmpv6` is deferred with IPv6 |
| port | port or range | for tcp/udp/sctp | forbidden for the other protocols (DM-17) |
| icmpType, icmpCode | integer 0–255 | no | only for icmp/icmpv6 |
| protocolNumber | integer 0–255 | for `ip` | raw IP protocol number |

### ServiceGroup (extends ServiceRef)

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| members | list of ref Service | yes | non-empty, flat; members may have different protocols (DM-18) |

### SystemServices

Network services that the firewall provides to the hosts of its networks. Each one lists where it listens; it opens its own ports there without a Policy and without `allowAccess` (DM-34). Field names follow the schema's `system.dns` and `system.ntp`, with `serveToInterfaces` renamed `listenOn` (to be applied in the schema).

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| dns | DnsService | no | DNS server (R-018) |
| ntp | NtpService | no | NTP server (R-059, proposed) |

**DnsService** and **NtpService** (composed in SystemServices):

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| listenOn | list of ref Interface or Zone | no | default: empty, i.e. not served on any Interface (R-058); a Zone stands for all its members (DM-45) |
| *(service settings)* | | | `mode`, `upstreams` for DNS; `servers` for NTP; as in the schema |

The DHCP server is not here yet: it stays in the Interface until its place is decided (open question).

### Color

A palette entry used to classify related objects (R-055). What a Color stands for ("Backup / Veeam", "main LAN", "DMZ") is its `comment`, like for every other object.

| Attribute | Type | Req. | Notes |
|---|---|---|---|
| hex | `#RRGGBB` | yes | unique among Colors (DM-33) |
| predefined | boolean | no | entry of the shipped palette: `hex` is immutable, `comment` is free |

Other objects reference a Color by name in `color`, never by a literal hex.

## Constraints

### General

| ID | Constraint |
|---|---|
| DM-01 | Names follow the format and reserved words of [Names](#names) and are unique within their namespace: Address and AddressGroup; Service and ServiceGroup; Interface and Zone; Color. RuleSet names are unique among RuleSets; Policy names within their RuleSet. |
| DM-02 | Every reference points to an existing object (referential integrity). |

### Interfaces

| ID | Constraint |
|---|---|
| DM-03 | `type = vlan` requires `parent` (a `physical` Interface) and `vlanId` ∈ 1–4094; `(parent, vlanId)` is unique. `type = physical` has neither. |
| DM-04 | Interfaces with IPs in overlapping subnets are rejected. |
| DM-05 | `allowAccess` contains only Management Services: `ping` and `https` (`ssh` when a CLI over SSH exists), without duplicates. Default: empty. `ping` governs ICMP echo only. It applies to the addresses of the Interface (owner rule), not to the Interface the packet arrives on. |
| DM-34 | A System Service implicitly accepts its own ports on the Interfaces where it listens, independently of `allowAccess` and of Policies: the DNS server (UDP/TCP 53) and the NTP server (UDP 123) on their `listenOn` Interfaces, the DHCP server (UDP 67) where `dhcp.enabled`. `allowAccess` governs only Management Services. |
| DM-45 | `listenOn` references existing Interfaces or Zones; a Zone stands for all its members. An Interface appears at most once in the expanded list of a service. |

### Zones, RuleSets and Policies

| ID | Constraint |
|---|---|
| DM-06 | A RuleSet's `from` and `to` reference existing Interfaces or Zones and **must be different objects**: `lan1 → lan1` and `internal → internal` are rejected. An Interface and the Zone that contains it are different objects, so `lan1 → internal` is allowed. There is no wildcard Interface. |
| DM-07 | There is at most one RuleSet per ordered pair `(from, to)`. An ordered pair of distinct Interfaces may be governed by up to four RuleSets, evaluated as in DM-42. |
| DM-37 | A Zone has at least one Interface, and an Interface belongs to at most one Zone. |
| DM-38 | An Interface that belongs to a Zone may be referenced in `from` / `to` directly or through its Zone. |
| DM-42 | For a Flow entering Interface *i* and leaving Interface *o*, with *i* ≠ *o*, the applicable RuleSets are evaluated in the order *i → o*, *i → Zone(o)*, *Zone(i) → o*, *Zone(i) → Zone(o)*, skipping those that do not exist; the first matching enabled Policy across them decides. Traffic leaving through the Interface it entered (*i* = *o*) is never governed by a RuleSet (no intra-interface Policies, W-007). |
| DM-39 | For two distinct Interfaces of the same Zone, when no Policy of the applicable RuleSets matches (DM-42), `intraZoneTraffic` decides: `deny` (default) applies Default Deny, `allow` accepts the traffic. Both produce Flow Events (R-026). |
| DM-08 | `source`, `destination` and `service` of a Policy are non-empty. |
| DM-09 | Order matters within a RuleSet and, across RuleSets, as stated in DM-42. Traffic between Interfaces governed by no RuleSet, or matching no Policy, is dropped and logged (Default Deny, R-033), except as stated in DM-39. |
| DM-10 | *Withdrawn in 0.6* (VirtualIP removed). |
| DM-11 | *Withdrawn in 0.6* (VirtualIP removed). |
| DM-12 | (Restriction, as in FortiGate.) An Address, AddressGroup or InterfaceAddresses bound to an Interface is usable as a source only in RuleSets whose `from` is that Interface or a Zone containing it, and as a destination only in RuleSets whose `to` is that Interface or a Zone containing it. |
| DM-13 | `nat` is forbidden when `action = drop`. `snat`: `translateIpTo`, if present, is a subnet or range Address; `translateServiceTo` is absent. `dnat`: `translateIpTo` is a single-host Address or a range; `translateServiceTo`, if present, is a Service with exactly one tcp/udp/sctp entry and a single port, with the same protocol as the Policy's `service`. |
| DM-40 | A `dnat` Policy has an explicit `destination` and, if it translates the port, an explicit `service` (not `any`). The destination should be an address of the `from` Interface (or of a member of the `from` Zone): otherwise the Validator warns, because traffic to it is not normally received by the firewall. |
| DM-41 | Two `dnat` Policies whose RuleSets share an incoming Interface do not overlap on (protocol, destination, service). Otherwise the translation of a packet would be ambiguous (`dataplane.md` §7.4). A `dnat` Policy shadowed by an earlier Policy of its RuleSet produces a Validator warning. |
| DM-35 | If `https` is in `allowAccess` of an Interface, no `dnat` Policy whose RuleSet comes from that Interface translates an address of that Interface on TCP with a `service` that includes the management HTTPS port (443 by default, `System.admin.httpsPort` in the schema). |
| DM-36 | The number of enabled Policies in a RuleSet does not exceed the per-RuleSet limit of the Data Plane (ADR-0006). The Validator enforces it, so that an Apply never fails on map size. |

### Objects

| ID | Constraint |
|---|---|
| DM-14 | `value` is consistent with `type`: a subnet is valid CIDR (a bare address without prefix is rejected); a range has start ≤ end and one address family; an FQDN is a valid DNS name; a MAC is six octets. |
| DM-43 | An enabled Policy does not reference an `fqdn` or `mac` Address, directly or through an AddressGroup, while the Data Plane does not support that type (R-012.4). The Address itself may be defined. |
| DM-44 | A `mac` Address is usable only in `source`, never in `destination` nor as `translateIpTo` (R-012.3). |
| DM-15 | An AddressGroup has at least one member, no duplicates, and its members are Addresses only (not derived addresses, not other groups: groups are flat). There is no limit on the number of members other than the Data Plane capacity (ADR-0006). |
| DM-16 | All members of an AddressGroup belong to the same Interface, or none of them belongs to any. In the first case the group's `interface` is that Interface; in the second it is absent. |
| DM-17 | A Service has at least one ProtocolEntry and no two identical entries. In each entry, `port` is mandatory and valid (1–65535, ordered range) for `tcp`, `udp` and `sctp`, and absent for the other protocols; `icmpType`/`icmpCode` only for `icmp`/`icmpv6`; `protocolNumber` only and always for `ip`. |
| DM-18 | A ServiceGroup has at least one member and no duplicates; its members are Services only (groups are flat) and may have different protocols. |
| DM-19 | *Withdrawn in 0.6*: replaced by the warning in DM-40. |
| DM-20 | *Withdrawn in 0.6*: `translateServiceTo` is a single port (DM-13); a range in the original `service` is translated to that port. |
| DM-21 | Predefined objects are YAML files generated at setup with `predefined: true`: the Addresses `any` (`0.0.0.0/0`) and `any6` (`::/0`), the Services `any` (every protocol and port), `http`, `https`, `dns`, …, and the predefined Colors. The Validator checks they are present and rejects edits of their defining fields and deletions; `comment` stays editable. |

### Routing

| ID | Constraint |
|---|---|
| DM-22 | A StaticRoute's `gateway` lies in a subnet of `outInterface`. |
| DM-23 | Among the StaticRoutes with the same `destination`, the active route is the one with the lowest `distance`, then the lowest `priority`. No two routes share `(destination, distance, priority)`: equal-cost multipath is not supported (decided 2026-10-19). |

### DHCPv4

| ID | Constraint |
|---|---|
| DM-24 | *Withdrawn in 0.7* (`role` removed: `dhcp` is allowed on any Interface). |
| DM-25 | `rangeStart ≤ rangeEnd`, both in the same subnet, and that subnet is one of `Interface.addresses`. |
| DM-26 | The range contains neither the Interface IP nor the gateway. |
| DM-27 | The gateway, if specified, lies in the range's subnet. |
| DM-28 | DHCP ranges of different Interfaces do not overlap. |
| DM-29 | A reservation's `ip` lies in the DHCP subnet (inside or outside the dynamic range) and is neither the Interface IP nor the gateway; `mac` and `ip` are unique among the reservations of the Interface. |

### Deferred (IPv6)

| ID | Constraint |
|---|---|
| DM-30 | *Deferred.* Was: `dhcpv6Client` allowed only on `role = wan` (to be restated without `role`). |
| DM-31 | *Deferred.* Was: `dhcpv6Server` and `routerAdvertisement` allowed only on `role = lan` (to be restated without `role`). |
| DM-32 | *Deferred.* Was: a Router Advertisement has exactly one of `prefix` and `delegatedFrom`. |

### Color

| ID | Constraint |
|---|---|
| DM-33 | Color `hex` values are unique. A `predefined` Color keeps its `hex`, and the names of the shipped palette cannot be reused by user Colors. A Color has no `color` itself. Every other object references at most one existing Color by name. |

## Design notes

- **`allowAccess` is not a Policy.** It governs traffic *to* the firewall (local-in); Policies govern traffic *through* it. The implicit drop in DM-09 applies only to the latter.
- **Secure by default.** With `allowAccess` empty by default, the factory default Configuration sets `https` on one Interface only, which is also the only Interface where the setup wizard answers (R-031.1); the wizard then lets the user choose where `https` and `ping` stay enabled.
- **Intra-interface Policies cannot be expressed** (DM-06: `from ≠ to`). Consequently there is no hairpin NAT in v1: a LAN client reaching a published service on its public address would go from LAN to LAN. Workaround: internal DNS resolving the service to the private IP.
- **Traffic between hosts on the same L2 segment** does not traverse the firewall and cannot be filtered by a Policy.
- **No per-Policy log level.** Every Flow produces an Event (R-026); volume is controlled by rate limiting (R-026.1), not by Policy.
- **Policy identifier.** The "matched Policy identifier" required by R-026 is, for now, the pair (RuleSet name, Policy name). Renaming a Policy changes it.
- **Overlapping RuleSets are allowed on purpose.** Using a member Interface next to its Zone gives exceptions ("everything from `internal`, except this host on `lan1`") without splitting the Zone. Keeping the configuration clean is left to the user; the UI and CLI make the evaluation order visible (R-046.3). The cost is in the Compiler: a Zone RuleSet is repeated in every effective list of its member pairs, and DM-36 applies to those effective lists.
- **Group Interface is redundant.** Since DM-16 forces it to equal the members' Interface, `AddressGroup.interface` could be derived instead of stored. It is kept explicit for readability of the YAML.

## Deferred

Not modelled for now, and the RA requirements that depend on them:

| Topic | RA requirements affected |
|---|---|
| IPv6 forwarding | R-001.3, R-001.4 |
| Router Advertisement / SLAAC, NDP | R-004, R-005 |
| DHCPv6 and Prefix Delegation | R-017.4 |
| NAT64 / DNS64 | R-006, R-006.1, R-006.2, R-018.6 |
| IPv6 addressing and routes | R-012 (IPv6 examples), R-020.4 |

## Impact on the RA

The changes required by this model are applied in the proposed **RA v2.0.3-draft**: R-010, R-011, R-012 (+ R-012.1–R-012.5), R-013, R-014.5, R-046.1–R-046.3, R-002.1/.2, R-031.1, R-056, R-058 and the proposed R-059.

## Schema alignment

Decisions of 2026-10-19 that the schema does not reflect yet. The schema is maintained by its owner; this list is the input for that change.

| Schema today | Decided |
|---|---|
| `Interface.spec.role` (`internal`, `external`, `dmz`, `transit`) | Removed |
| `allowAccess` values `https`, `ping`, `dns`, `dhcp`, `ntp` | `https`, `ping` only (DM-05) |
| `system.dns` / `system.ntp` with `serveToInterfaces` | `systemServices.dns` / `systemServices.ntp` with `listenOn` |
| `Address.spec.interface` described as a hint | A restriction (DM-12) |
| AddressGroup and ServiceGroup may contain groups; cycles rejected | Flat (DM-15, DM-18) |
| `referenceOrAny` and the keyword `any`; `any` reserved | Predefined Addresses `any`, `any6` and Service `any`; reserved words `all`, `none` (DM-21) |
| Policy field `log` | Removed (R-026) |
| `fqdn` / `mac` accepted in Policies | Rejected in enabled Policies until supported (DM-43); `mac` only as source (DM-44) |
| RuleSets: a member Interface of a Zone rejected | Allowed (DM-38); `from` and `to` different objects (DM-06) |

## Open questions

- **DHCP server**: keep it in the Interface (`dhcp`) or move it to SystemServices with the DNS and NTP servers (RA open issue #13).
- **Service `any`**: how the predefined Service is written in the schema (e.g. a single `ip` entry meaning every protocol) is to be agreed with the schema owner.
- **`sourcePort`** in ProtocolEntry exists in the schema but not in the Data Plane classifier: keep it (and add a dimension) or drop it.
- **InterfaceAddresses name**: a format that cannot collide with user names, e.g. a reference syntax such as `lan1:addresses` (needs a schema extension, since `:` is not allowed in names).
- **DnsService details**: forwarder/recursor settings (R-018), local names (R-018.2) and failover (R-034) still to be modelled.
- **Still to model**: User and Role (R-043), Repository (R-021), notifications (R-030), TLS/ACME (R-038), HA (R-023).
