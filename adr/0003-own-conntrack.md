# ADR-0003: Own connection tracking in BPF maps, without nf_conntrack

| | |
|---|---|
| Status | Proposed |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | C-001, R-045, R-045.1, R-045.2, R-023; RA open issue #3; dataplane.md §9; dataplane v2 open question 2 |

## Context

Stateful filtering (R-045) needs connection tracking. The kernel offers `nf_conntrack` with BPF kfuncs (`bpf_xdp_ct_lookup`, `bpf_ct_insert_entry`, `bpf_ct_set_nat_info`). C-001 excludes the iptables/nftables rule engines; whether it also excludes `nf_conntrack` is RA open issue #3.

## Options considered

| | **Own CT in BPF maps** (Cilium model) | **nf_conntrack via kfuncs** |
|---|---|---|
| Dependency | None | `nf_conntrack` module (grey area with C-001) |
| Performance | Direct hash lookup, predictable | Higher overhead, kernel allocation |
| TCP window tracking, ALGs (FTP, SIP) | To implement (simplified) | Available |
| HA state sync | To implement | `conntrackd` exists |
| Control and observability | Full | Kernel semantics, `conntrack -L` |

## Decision

**Own connection tracking in BPF maps**, as designed in dataplane.md §9: two entries per Flow, separate map for half-open TCP Flows, lazy expiry plus a periodic sweep, RELATED handling for ICMP errors.

This makes RA open issue #3 moot for the Data Plane: `nf_conntrack` is not used at all. The RA should record it and keep C-001 as written.

## Consequences

**Positive**

- No dependency on netfilter; consistent with C-001 in any reading.
- Predictable performance and memory, under our control; one key format shared with NAT.
- Full observability: every Flow and its Policy are known (R-026).

**Negative**

- **No ALGs**: protocols that negotiate ports in the payload (active FTP, SIP) will not work through NAT. To be documented as a limitation.
- TCP tracking is a state machine without window checks.
- HA state synchronisation (R-023, Could) must be implemented in Go if it is ever needed.
- Memory for 1 M Flows is significant (see ADR-0006).
