# ADR-0006: Capacity limits of the Data Plane

| | |
|---|---|
| Status | Proposed (values to be confirmed by benchmark, RA open issue #1) |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | R-047, R-048, R-026.1; DM-36; dataplane.md §7, §9, §10, §11; dataplane v2 open question 5 |

## Context

eBPF maps have a fixed size set at creation, and the bitmap classifier has a fixed width. Limits must therefore be decided in advance, checked by the Validator (an Apply must not fail because a map is full), and documented. R-048 (proposed) asks for 1 000 000 concurrent Flows and 4 096 Policies.

## Decision (proposed values)

| Limit | Proposed value | Driven by | Notes |
|---|---|---|---|
| Enabled Policies per Zone | 1 024 | Bitmap width: 16 × `u64` | Validator: DM-36 |
| Zones | 256 | `zone_id` (`u16`), map sizes | 16 Interfaces give at most 240 directed pairs |
| Total Policies | ≥ 4 096 | R-048 | Reached across Zones |
| Concurrent Flows | 1 048 576 | R-048 | Two CT entries each |
| Half-open TCP Flows (SYN map) | 65 536 | SYN flood protection | |
| DNAT entries (after port-range expansion) | 16 384 | VIP port ranges | Validator rejects a configuration that exceeds it |
| Ring buffer | 8 MB | R-026.1 | Rate limiting still applies |

**Memory estimate for conntrack**: key 40 bytes + entry 96 bytes + per-element overhead, twice per Flow, is on the order of **350–400 MB for 1 M Flows**. This must be measured on the reference platform; if it is too much for the target hardware, the Flow limit becomes a configurable value with a lower default.

## Consequences

**Positive**

- Predictable memory and per-packet cost; the Validator gives a clear error before any Apply.

**Negative**

- Per-Zone limit of 1 024 Policies: a very large single Zone would require widening the bitmap (higher cost per new Flow).
- The conntrack size is a significant share of RAM on small appliances.

**To decide**

- Whether the Flow limit is configurable per appliance.
- Final values after the benchmark (RA open issue #1); this ADR is then updated and accepted.
