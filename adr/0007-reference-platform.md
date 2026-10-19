# ADR-0007: Reference platform for development and performance verification

| | |
|---|---|
| Status | Proposed (hardware and kernel to be confirmed) |
| Date | 2026-10-17 |
| Deciders | Songbird team |
| Related | C-003, R-047, R-048, R-049, R-019; ADR-0002; dataplane.md §5, §12; dataplane v2 open question 6 |

## Context

Performance requirements are meaningless without a reference (C-003). Several Data Plane features depend on the kernel version and the NIC driver: native XDP, XDP metadata, VLAN tag access, TCX attach (kernel ≥ 6.6). The WAN of many target users is PPPoE, which does not support native XDP. The distribution mechanism (Hadron image upgraded in place, or a custom ISO based on Hadron) is still open and fixes the kernel version.

## Decision (proposed)

1. **Architecture**: x86-64.
2. **Kernel**: the one shipped by the target OS image, **at least 6.6** (TCX). The exact version is recorded once the image is fixed.
3. **Physical reference NIC**: one model with a driver supporting native XDP and XDP metadata, chosen among Intel `ice` / `i40e` / `ixgbe` or Mellanox `mlx5`. Selection criterion: availability to the team and verified metadata support.
4. **Virtual reference**: a VM with `virtio-net` for CI and functional tests (`T-I`, `T-S`). Not used for `T-P`.
5. **PPPoE**: supported on the WAN. It is a verified functional scenario, not a performance reference. Classification may run in TC on `ppp0` if XDP metadata do not reach it (dataplane.md §15).
6. The reference platform is documented in the Test Plan, with the exact hardware, firmware, kernel and image versions used for each benchmark.

## Consequences

**Positive**

- Benchmarks are reproducible and comparable across releases.
- Driver-dependent features are verified once, on known hardware.

**Negative**

- Results on other NICs (especially those with only generic XDP) may be much lower; this must be stated in the documentation.
- The platform cannot be fully fixed until the distribution mechanism is decided.

## Verification

`I`: the Test Plan names the platform; every `T-P` report references it.
