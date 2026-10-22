# ADR-0016: eBPF programs are managed with `cilium/ebpf` and generated with `bpf2go`

| | |
|---|---|
| Status | Accepted (retroactive) |
| Date | 2026-06 (recorded 2026-10-21) |
| Deciders | Songbird team |
| Related | C-001, C-004; ADR-0015; detailed-design/data-plane.md §11; R-036 |

## Context

The Go Control Plane must load, attach, pin and update BPF programs, and read/write maps and ring buffers with type safety. The first PoC used `cilium/ebpf` 0.11 with hand-written struct conversions; dataplane.md §12 already directed an upgrade with `bpf2go`.

## Options considered

**A. `cilium/ebpf` + `bpf2go`.** Pure Go, no CGo, CO-RE support, generates Go structs from the C sources so kernel and userspace layouts cannot drift (the static-assert contract of detailed-design/data-plane.md §3). The de-facto standard (Cilium, Cloudflare).

**B. `libbpfgo` (Aqua).** Thin wrapper over libbpf; full libbpf semantics but CGo, which breaks the static-binary constraint (C-004) and complicates cross-compilation for the appliance image.

**C. `aya` (Rust).** Would force the Control Plane to Rust; rejected with ADR-0015.

## Decision

1. All BPF lifecycle operations use **`cilium/ebpf`**, pinned per release; upgrades are reviewed (the API moves).
2. **`bpf2go` generates the Go bindings** from the C sources; hand-written struct mirrors are forbidden — a layout change is one C edit plus regeneration, checked by static asserts.
3. Attach follows ADR-0013 (XDP native/generic, TCX for TC); pinning under `/sys/fs/bpf/songbird/` for crash re-attach.

## Consequences

**Positive**

- No CGo: the single static binary of ADR-0015 stays simple to build in CI and to embed in the image.
- Generated bindings make the wire structs of the detailed design a compile-time contract, not a convention.

**Negative**

- `bpf2go` adds a code-generation step: the Makefile pins `clang` and `bpf2go` versions, and CI builds the BPF objects deterministically.
- Library upgrades occasionally rename APIs; absorbed deliberately at release boundaries.

**Documents changed**: detailed-design/data-plane.md §11 (M2-01 pins the versions).
