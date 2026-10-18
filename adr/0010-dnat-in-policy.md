# ADR-0010: DNAT is a section of the Policy, matched before translation

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-18 |
| Deciders | Songbird team |
| Related | R-003, R-002, R-014; `songbird-yaml-schema` design decision 6; domain model v0.6 (DM-13, DM-35, DM-40, DM-41); dataplane.md §7.4, §10 |

## Context

The domain model (up to v0.5) published internal servers with a separate **VirtualIP** object, referenced as destination by a Policy and matched **after** translation (FortiGate VIP semantics). The YAML schema instead puts DNAT in the `nat` section of the Policy, reusing Address and Service objects, and matches the destination and service **before** translation (nftables `prerouting dnat` semantics). The team decided that, on NAT, the schema has precedence.

## Options considered

**A. VirtualIP object, post-translation matching** (FortiGate). One more kind; the Policy names the VIP, not the public address; needs a dedicated classifier dimension so that only VIP-referencing Policies match translated traffic.

**B. `nat.type: dnat` in the Policy, pre-translation matching** (schema). *(chosen)* No new kind; the Policy reads as "traffic to the public address and port is accepted and sent to this server"; SNAT and DNAT share one structure.

## Decision

1. `nat` is `{type: snat | dnat, translateIpTo, translateServiceTo}` as defined in the schema. VirtualIP and IpPool are removed from the domain model; an SNAT pool is an Address used as `translateIpTo`.
2. A `dnat` Policy matches `destination` and `service` **before** translation.
3. The Data Plane resolves the routing cycle (the output Interface depends on the translated address) with a DNAT candidate table compiled from the `dnat` Policies; a translated packet is accepted only if the first matching Policy is the `dnat` Policy that produced the translation (dataplane.md §7.4).
4. `dnat` Policies must not overlap on the same incoming Interface (DM-41), and shadowed ones are reported by the Validator.

## Consequences

**Positive**

- Fewer kinds; one NAT structure for both directions; the YAML states the public address explicitly.
- The classifier loses the VIP dimension.
- Open question 3 of dataplane.md (service on translated traffic) is resolved: the original port.

**Negative**

- Publishing the same server on two public addresses needs two Policies (one per address), where a VIP could be reused.
- An earlier `accept` Policy can shadow a `dnat` Policy: the Data Plane drops (`dnat-shadowed`) and the Validator must warn.
- Users coming from FortiGate must learn that the Policy names the public address, not a VIP object.

**To update**

- RA: R-003 and the glossary entries *DNAT* and *Virtual IP* (RA v2.0.2).
- PoC Web UI v2: still uses VirtualIP; to be aligned when the PoC is updated.
