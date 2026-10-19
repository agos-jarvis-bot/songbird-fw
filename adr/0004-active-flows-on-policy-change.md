# ADR-0004: Active Flows no longer permitted are terminated at their next packet

| | |
|---|---|
| Status | Proposed (depends on acceptance of R-054) |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | R-054 (proposed), R-020.6, R-026; dataplane.md §9; dataplane v2 open question 3 |

## Context

When a new configuration is applied, Flows accepted by the previous Policies may no longer be permitted. Because replies are accepted by connection-tracking state (R-045), such a Flow would otherwise continue until it times out, which may be an hour for TCP. R-054 (proposed) asks that it be terminated at its next packet, which is also the FortiGate default.

## Options considered

**A. Let Flows expire.** Simple, no cost, but a "block" change takes effect only for new Flows: surprising and unsafe.
**B. Flush all conntrack on every Apply.** Simple and strict, but every Apply drops every connection, including those still permitted.
**C. Re-classify at the next packet.** *(chosen)*

## Decision

Each CT entry stores the generation (`policy_gen`) that accepted it. At the next packet in **either direction** of a Flow whose generation differs from the active one, the Data Plane re-classifies the Flow's ORIG tuple with the new generation:

- still accepted → update `policy_gen` and the matched Policy, forward;
- not accepted → drop the packet, delete both entries, emit `FLOW_END` with reason `policy-change`.

Local-in Flows are re-checked against the new local-in configuration in the same way.

## Consequences

**Positive**

- A block takes effect at once on active traffic, and permitted Flows are not disturbed.
- The cost is paid only once per Flow per Apply, then the fast path resumes.

**Negative**

- Each CT entry stores the key of the other direction (40 bytes) so that a reply can find the ORIG tuple and delete both entries.
- Idle Flows are not terminated until they send a packet or expire; this matches R-054 ("at its next packet").
- A burst of re-classifications right after an Apply with many active Flows; to be measured.

## Verification

`T-I` as in R-054: long-lived TCP Flow; change the Policy to drop; the next segment is dropped and `FLOW_END` with reason `policy-change` is emitted.
