# ADR-0002: Forwarding model — XDP decides, the kernel forwards, TC rewrites

| | |
|---|---|
| Status | Proposed (to be accepted after the first benchmark) |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | C-001, R-001, R-002, R-003, R-047, R-049; dataplane.md §3; dataplane v2 open question 1 |

## Context

The Data Plane must filter, translate and forward packets with eBPF (C-001). A packet redirected with `XDP_REDIRECT` does not traverse the TC egress hook of the output device, so NAT in TC is compatible only with forwarding done by the kernel stack. The WAN is often PPPoE (FTTH) or a VLAN, and those devices do not support native XDP, while TC works on any netdevice.

## Options considered

**A. XDP decides, kernel forwards, TC rewrites.** XDP: parsing, prefilter, conntrack, Policy → drop or pass. Kernel: routing, ARP, MTU and ICMP errors. TC: DNAT, SNAT. Simple, works on VLAN and PPPoE, drops at XDP speed; accepted traffic is forwarded at stack speed (roughly 1–2 Mpps per core).

**B. Everything in XDP** (`bpf_fib_lookup` + `XDP_REDIRECT`, NAT in XDP). Highest throughput, but NAT, checksums, MTU, ICMP errors and VLAN tag push must be reimplemented, it does not work towards `ppp0` or VLAN devices, and TC is still needed for local traffic.

**C. TC-centric (Cilium model).** XDP only as prefilter; Policy, conntrack and NAT in TC with `bpf_redirect_neigh`. One hook with an `skb`, but Policy drops lose XDP speed.

## Decision

**Option A** for the first release. A fast path in XDP (option B) for established Flows without NAT between physical NICs is deferred and will be added only if the benchmark on the reference platform (ADR-0007) shows that A does not meet R-047.

## Consequences

**Positive**

- One design for physical NICs, VLANs and PPPoE.
- Routing, ARP, PMTU and ICMP errors stay in the kernel: less code to write and verify.
- Drops (attacks, Default Deny) still happen at XDP speed.

**Negative**

- Accepted traffic is bounded by kernel forwarding performance; R-047 (1 Mpps/core with 1 000 Policies) may be tight.
- Two hooks (XDP and TC) must cooperate through XDP metadata, whose support depends on the NIC driver (to verify, ADR-0007).
- The kernel stack must be configured by the Network Driver (sysctls, routes) without using netfilter rule engines (C-001).

## Verification

`T-P` benchmark of R-047 and R-049 on the reference platform before this ADR moves to *Accepted*.
