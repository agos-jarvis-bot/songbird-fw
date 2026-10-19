# ADR-0005: Non-initial IPv4 fragments are dropped when forwarded

| | |
|---|---|
| Status | Proposed (depends on acceptance of R-053) |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | R-053 (proposed), R-018.5, R-033; dataplane.md §5; dataplane v2 open question 4 |

## Context

Only the first fragment of an IPv4 datagram carries the L4 header. Non-initial fragments have no ports, so they cannot be classified or matched to a Flow by tuple. Fragmented traffic is rare on modern networks but still used, and fragment floods are a known attack. R-053 (proposed) asks for a configurable drop, default drop.

## Options considered

**A. Track fragments.** A short-lived LRU map `{saddr, daddr, id, proto} → verdict` populated by the first fragment; following fragments inherit its verdict. Correct, but more state and fragments arriving before the first one are dropped anyway.
**B. Drop non-initial fragments, no state.** *(chosen for forwarded traffic)*
**C. Pass all fragments to the kernel.** Unfiltered bypass; rejected.

## Decision

1. **Forwarded traffic**: non-initial fragments are dropped and counted with reason `fragment` (event rate-limited). This is the default required by R-053; the behaviour is a **global setting** for now, with tracking (option A) as the future alternative value.
2. **Traffic addressed to the firewall itself**: non-initial fragments are passed to the kernel, which reassembles them and delivers them only to existing sockets, with a rate limit. Without this, large UDP replies to the firewall's own DNS forwarder (for example DNSSEC answers, R-018.5) would be lost.

## Consequences

**Positive**

- No fragment state; fragment-based evasion and floods are blocked for forwarded traffic.
- The firewall's own services keep working with large UDP answers.

**Negative**

- Applications behind the firewall that rely on IP fragmentation (some VPNs, large UDP DNS answers to clients that do not use the firewall's DNS, NFS over UDP) break when fragmentation happens on the path. To be documented.
- R-053 says "Policies shall be able to drop": a global setting is a narrower reading. The RA wording should be aligned, or the setting moved per RuleSet later.
