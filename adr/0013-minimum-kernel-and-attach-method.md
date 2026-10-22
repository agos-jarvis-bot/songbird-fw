# ADR-0013: Minimum kernel 6.6, TC attached with TCX, XDP native with generic fallback

| | |
|---|---|
| Status | Proposed |
| Date | 2026-10-21 |
| Deciders | Songbird team |
| Related | C-001, C-003; R-045.2; ADR-0002, ADR-0007; dataplane.md §5, §12; detailed-design/data-plane.md §1, §12; Project Plan decision #5 |

## Context

The Data Plane needs two attach points (ADR-0002): XDP on physical Interfaces and TC for NAT on egress/local traffic. The attach API and the available helpers depend on the kernel:

- **TCX** (`bpf_link` for TC, `link.AttachTCX` in `cilium/ebpf`) exists from kernel **6.6**: ordered, link-managed, detachable without netlink qdisc fiddling.
- Classic **clsact** qdisc attach works on ≥ 4.x but is global-per-device, harder to order against other TC users, and its attach/detach is more fragile during hot reload.
- The VLAN-tag kfunc `bpf_xdp_metadata_rx_vlan_tag` needs ≥ 6.8 **and** driver support; disabling `rxvlan` offload (`ethtool -K <if> rxvlan off`) works everywhere (dataplane.md §5).
- Distribution reality: Debian 12 ships 6.1, **Debian 13 ships 6.12**; the 0.1 packaging target leans Debian 13 (Project Plan decision #6). Hadron's kernel is to be verified (spike 7.1).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Kernel ≥ 6.6, TCX only** | One attach path, link-managed, clean hot reload later; Debian 13 satisfies it | Debian 12 and older LTS distros excluded from 0.1 |
| **B. Kernel ≥ 5.15, clsact only** | Widest compatibility | Weaker attach semantics, more fragile detach/update; extra testing matrix |
| **C. Both, abstracted behind an attach interface** | Compatibility now, TCX benefits where available | Two paths to test and keep correct from day one |

## Decision (proposed)

1. **Minimum kernel: 6.6.** TC is attached with **TCX**; XDP is attached in **native (drv) mode** where the driver supports it, with automatic fallback to **generic (skb) mode** and a logged warning (performance note in `/health`).
2. VLAN tags are read by **disabling `rxvlan` offload at Interface bring-up**; the 6.8 kfunc is used opportunistically when present, never required. The 6.6 floor therefore stands.
3. **0.1 development and reference distribution: Debian 13** (kernel 6.12) — satisfies the floor with margin; Debian 12 is out of scope for 0.1.
4. Hadron must ship a kernel ≥ 6.6: verified by spike 7.1 before 0.3 planning; if it cannot, the fallback is a custom ISO with a newer kernel, not a second attach path.
5. No clsact compatibility path is implemented. If a real user need appears, it is added behind an attach interface at that time (option C), with its own ADR.

## Consequences

**Positive**

- One TC attach path to implement, test and hot-reload; the link model fits the generation-swap design (detailed-design/data-plane.md §5).
- The floor is satisfied by the current stable Debian and checkable by the `test/env` preflight (Test Plan §5).

**Negative**

- Users on Debian 12 / Ubuntu 22.04 (5.15) cannot run 0.1; acceptable for a project in design phase, worth one line in the README when 0.1 ships.
- Spike 7.1 becomes gating for the 0.3 Hadron image.

**To verify before accepting**: Hadron kernel version (spike 7.1); TCX behaviour of `cilium/ebpf` version pinned in M2-01.

**Documents changed**: detailed-design/data-plane.md §1 (attach choice), Project Plan decision #5 (closed when accepted), Test Plan §5 (`test/env` checks kernel ≥ 6.6).
