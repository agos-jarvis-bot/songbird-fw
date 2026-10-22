# ADR-0015: The Control Plane is written in Go

| | |
|---|---|
| Status | Accepted (retroactive) |
| Date | 2026-06 (recorded 2026-10-21) |
| Deciders | Songbird team |
| Related | C-004; RA references; PoC-feasibility-study (archived); detailed-design/data-plane.md |

## Context

The Control Plane manages eBPF programs and maps, netlink configuration, YAML, Git, DNS/DHCP services, and serves the API/UI. It must ship as one static binary on an immutable OS (C-002), and the team of two must not context-switch between languages.

## Options considered

**A. Rust.** Best-in-class for eBPF userspace (libbpf-rs, aya) and safety. Costs: slower iteration for the API/UI/services layer, weaker batteries for DNS/DHCP servers, steeper curve for contributors.

**B. Go.** *(chosen)*

**C. C/C++.** Closest to the kernel, but the Control Plane is mostly orchestration; the cost would be paid on every feature for no data-plane benefit (the Data Plane is already C compiled to eBPF).

## Decision

1. The Control Plane is **Go**, one statically linked binary (`CGO_ENABLED=0`) embedding the UI assets and the schema (C-004).
2. The Data Plane stays **C compiled to eBPF**; Go manages lifecycle, maps and events via `cilium/ebpf` (ADR-0016).
3. Reference libraries from the feasibility study: `vishvananda/netlink`, `go-git/go-git`, `miekg/dns`, `insomniacslk/dhcp`, `santhosh-tekuri/jsonschema`. Engines that prove insufficient become orchestrated external daemons, decided case by case (ADR-0014).

## Consequences

**Positive**

- Single toolchain for everything but the BPF C; static binary fits the immutable OS and A/B updates (R-019); the PoC-webui-v2 already validates the end-to-end shape.

**Negative**

- `go-git` is slower and less complete than libgit2 for edge cases (large histories, signed commits); acceptable for a config repository.
- Garbage collection pauses are irrelevant at control-plane rates but rule Go out of any future fast path in userspace — that path is eBPF by design (C-001).

**Documents changed**: none (C-004 already records the constraint; this ADR records the reasoning).
