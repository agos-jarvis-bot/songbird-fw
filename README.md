# Songbird

Open-source network firewall appliance: FortiGate-like operational simplicity on a modern, declarative, GitOps-friendly architecture — Linux, eBPF data plane, Go control plane, YAML configuration in Git.

**Status:** design phase. No release yet. Engineering follows the order *requirements → project plan → architecture → detailed design → tests → code*; code is a consequence of the design documents below.

## Repository layout

| Path | Content |
|---|---|
| [`docs/requirements-analysis.md`](docs/requirements-analysis.md) | Requirements Analysis (RA): stakeholders, glossary, constraints, requirements with verification criteria, exclusions, traceability |
| [`docs/project-plan.md`](docs/project-plan.md) | Project Plan: release roadmap, MVP 0.1 scope, milestones, WBS, risks, process |
| [`docs/architecture/`](docs/architecture/) | Architectural design: [domain model](docs/architecture/domain-model.md), [components](docs/architecture/components.md), [reconciliation loop](docs/architecture/reconciliation.md), [eBPF data plane](docs/architecture/dataplane.md) |
| [`adr/`](adr/) | Architecture Decision Records (one file per decision; never deleted, only superseded) |
| [`schema/`](schema/) | Configuration schema (JSON Schema 2020-12, `config.songbird-fw.com/v1alpha1`), example configuration, negative test corpus, validator prototype |
| [`docs/legacy/`](docs/legacy/) | Superseded documents kept for reference |

Planned (see project plan §10): `cmd/`, `internal/`, `bpf/`, `ui/`, `test/`, `image/`.

## Related repositories

- [`songbird-prototypes`](https://github.com/songbird-fw/songbird-prototypes) — proofs of concept (XDP firewall, Hadron OS image, Web UI PoC). Archived; not part of the product.
- [`songbird-site`](https://github.com/songbird-fw/songbird-site) — project website.
- `songbird-requirements-analysis`, `songbird-architecture`, `songbird-yaml-schema` — imported here with full history on 2026-10-19; to be archived.

## Validating a configuration

```bash
cd schema
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python validate.py examples/valid      # 43 objects, 0 errors
```

## License

AGPL-3.0 — see [LICENSE](LICENSE).
