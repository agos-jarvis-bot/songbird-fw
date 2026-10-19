# ADR-0014: DHCP and DNS engines — in-process libraries or external daemons

| | |
|---|---|
| Status | Proposed (question open; decision needed before the 0.2 work on DHCP and DNS starts) |
| Date | 2026-10-19 |
| Deciders | Songbird team |
| Related | R-017–R-017.4, R-018–R-018.6, R-034, R-034.1, R-058, R-012.2, R-030.4, R-032, C-002, C-004; components.md (DHCP Service, DNS Service); domain model SystemServices; Project Plan §2 (DHCP and DNS in 0.2) |

## Context

Songbird provides a DHCPv4 server (R-017.x, Must), DHCPv6 with Prefix Delegation later (R-017.4, Should), and a DNS server that forwards and caches (R-018.1, Must), resolves local names (R-018.2) and fails over between upstreams (R-034). The Recursive mode with DNSSEC validation (R-018.3–R-018.5) is Should. The DNS server also has to resolve FQDN Addresses for the Compiler (R-012.2, Must for 1.0).

In `components.md` the DHCP Service and the DNS Service are Drivers. They receive their section of the compiled `Plan`, apply it through `Prepare` / `Commit` / `Rollback`, and report health to the Observer (R-032). Both listen only on the Interfaces in their configuration (`dhcp` on the Interface, `listenOn` of the System Services, R-058), and the Data Plane opens their ports there (DM-34).

Forces:

- **C-004** asks for a single statically linked Go binary for the Control Plane. An external daemon is not Control Plane code, but it is one more program to ship, update and supervise.
- **C-002** (immutable OS): an external daemon must be in the image; its configuration is generated at runtime into a writable path.
- **Failure isolation**: a crash or a hang of DHCP or DNS should not take down the Data Plane or the API (R-030.4 states it for Alerting; the same reasoning applies).
- **DNSSEC validation** (R-018.5) is hard to implement correctly. Mature validating resolvers exist as external programs.
- **Atomic Apply** (R-020.6): every engine must accept a new configuration as a whole, or keep the old one.
- **Licensing**: Songbird is AGPL-3.0; every engine must have a compatible licence.
- **Effort**: the team has two people (Project Plan §1.1).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. In-process Go libraries** for both (e.g. a DHCP server built on a Go DHCP library, a DNS forwarder built on a Go DNS library) | One binary, no process supervision; configuration passed as Go structs, so `Prepare`/`Commit` are natural; the DNS Service can feed resolved FQDN sets to the Compiler directly; same test tooling (netns + `go test`) | Recursive mode and DNSSEC validation must be built or embedded, which is the riskiest part; a panic in a library can affect the whole Control Plane unless it is isolated (separate goroutine supervision, or a separate process of the same binary) |
| **B. External daemons** (e.g. Kea for DHCP; Unbound for recursive/validating DNS, or dnsmasq for DHCP + forwarding DNS) | Mature, widely deployed engines; DNSSEC validation available; failures isolated by process boundaries; Kea is the maintained successor of ISC DHCP, which reached end of life at the end of 2022, and is what pfSense Plus moved to | Configuration file generation and reload per engine; each has its own reload semantics, so atomic `Commit`/`Rollback` must be built around them; more packages in the image and more security updates to follow; health and lease state through each engine's control interface; FQDN resolution for the Compiler needs a query path to the daemon |
| **C. Hybrid**: DHCP and the forwarding DNS in-process (A); Recursive mode with DNSSEC delegated to an external validating resolver (B), started only when Recursive mode is enabled | Musts (R-017.x, R-018.1, R-018.2, R-034, R-012.2) stay in one binary and in Go; the hard part (R-018.3–R-018.5, Should) uses a proven engine; the external process exists only when needed | Two implementations for DNS (forwarder in Go, recursor external); the DNS Service must switch between them on a mode change |

Engine names above are examples to evaluate, not choices. Licence and current maintenance status of each candidate are to be checked during the spike.

## Decision

**Not taken yet.** The team keeps the question open (2026-10-19). This record collects the options and the criteria; it moves to *Accepted* when one option is chosen.

Criteria for the decision, in order:

1. Musts of 0.2 (R-017–R-017.3, R-018, R-018.1, R-018.2, R-034, R-034.1) are met with the smaller effort.
2. Apply stays atomic (R-020.6) and each engine reports health (R-032).
3. A failure of DHCP or DNS does not stop forwarding.
4. The path to R-018.5 (DNSSEC) and R-017.4 (DHCPv6-PD) exists, even if it is built later.
5. Licences compatible with AGPL-3.0.

Proposed next step: a short spike before M3 of the Project Plan that implements R-017 and R-018.1 with option A and measures the effort to wrap one external engine (option B) behind the same `Driver` interface.

## Consequences

- Until the decision, `components.md` keeps the DHCP Service and the DNS Service as Drivers with the engine hidden behind the `Driver` interface; nothing else depends on the choice.
- The deployment view (to be written) depends on this ADR: option B or C adds processes and packages to the image.
- The place of the DHCP server configuration (in the Interface or in SystemServices, RA open issue #13) is independent of this decision and can be settled first.
