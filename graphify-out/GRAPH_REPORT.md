# Graph Report - songbird-fw  (2026-10-31)

## Corpus Check
- 34 files · ~54,211 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 283 nodes · 313 edges · 47 communities (16 shown, 31 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Project Documents and ADR Index
- Data Plane Internals
- Validator Code (validate.py)
- Control-Plane Components
- Conntrack and Packaging
- System Services and Management
- Policy Classifier and DNAT
- XDP/TC Pipeline Stages
- Git-Backed Config Store
- Atomic Apply and Generations
- NAT and Platform Decisions
- eBPF Runtime and Observability
- Network Object Model
- Conntrack Capacity Design
- Validator Corpus
- Requirements and MoSCoW
- Address Constraints
- Domain Model Docs
- Service Model
- Crash Recovery Timing
- HA Future Component
- IDS/IPS Future
- BGP Future
- Threat Feeds Future
- Status Provider
- Per-CPU Counters
- Proxmox Lab
- AddressGroup Object
- Color Object
- ConfigObject Base
- DHCP Reservations
- Interface Addresses
- ServiceGroup Object
- ADR Lifecycle
- Reconciler Status
- Runtime Facts
- Constraints
- Excluded Requirements
- Open Issues

## God Nodes (most connected - your core abstractions)
1. `ADR index (0001–0018)` - 18 edges
2. `Songbird project README` - 12 edges
3. `Config Manager` - 12 edges
4. `DD-DP Data Plane Detailed Design (docs/detailed-design/data-plane.md)` - 12 edges
5. `Reconciler` - 10 edges
6. `semantic()` - 9 edges
7. `API Server` - 9 edges
8. `Reconciliation loop` - 9 edges
9. `Observer` - 8 edges
10. `Applier` - 7 edges

## Surprising Connections (you probably didn't know these)
- `RA constraint C-005 and requirements R-020.2/R-020.3/R-052` --cites--> `docs/requirements-analysis.md (RA)`  [INFERRED]
  schema/README.md → README.md
- `First high-level architecture sketch (superseded)` --semantically_similar_to--> `API Server`  [INFERRED] [semantically similar]
  docs/legacy/high-lvl-architecture.md → docs/architecture/components.md
- `Reconciliation loop` --semantically_similar_to--> `Reconciler`  [INFERRED] [semantically similar]
  docs/architecture/reconciliation.md → docs/architecture/components.md
- `Two-generation atomic map swap` --semantically_similar_to--> `Atomic apply across drivers`  [INFERRED] [semantically similar]
  docs/architecture/dataplane.md → docs/architecture/reconciliation.md
- `Python validator dependencies (jsonschema, pyyaml)` --conceptually_related_to--> `MVP 0.1 scope (41 requirements: 39 Must, 2 Should)`  [INFERRED]
  schema/requirements.txt → docs/project-plan.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Architecture documentation set under docs/architecture/** — readme_doc_domain_model, readme_doc_components, readme_doc_reconciliation, readme_doc_dataplane [EXTRACTED 1.00]
- **Git-backed configuration pipeline** — adr_0001_yaml_in_git_source_of_truth, adr_0008_schema_versioning_and_rollback, adr_0012_canonical_yaml_serialisation, adr_0018_crd_style_configuration_objects, adr_0009_secrets_encryption_key [INFERRED 0.85]
- **eBPF data plane technology stack** — adr_0002_forwarding_model, adr_0003_own_conntrack, adr_0013_minimum_kernel_and_attach_method, adr_0016_cilium_ebpf_library, adr_0006_capacity_limits [INFERRED 0.85]
- **Appliance platform and OS stack** — adr_0007_reference_platform, adr_0013_minimum_kernel_and_attach_method, adr_0017_hadron_as_the_appliance_os, adr_0015_go_for_the_control_plane [INFERRED 0.75]
- **RuleSet evaluation order (DM-42) implemented across compiler and data plane** — docs_architecture_domain_model_dm42, docs_architecture_components_design_ruleset_flattening, docs_architecture_dataplane_effective_policy_list [INFERRED 0.85]
- **Desired state → validate → compile → apply → observe pipeline** — docs_architecture_components_config_manager, docs_architecture_components_validator, docs_architecture_components_compiler, docs_architecture_components_applier, docs_architecture_components_observer [EXTRACTED 1.00]
- **Validation toolchain: prototype validator, test corpus, and future Go CLI implementing schema + semantic rules** — schema_readme_code_validate_py, schema_readme_concept_examples_corpus, schema_readme_concept_go_validator, schema_readme_concept_semantic_rules [INFERRED 0.85]
- **Rule/NAT design decisions enforced by semantic validation rules** — schema_readme_rationale_ruleset_per_pair, schema_readme_rationale_nat_design, schema_readme_concept_semantic_rules [INFERRED 0.75]
- **he_atomic_apply** — dd_dp_generation_swap, pp_mvp_01_scope, tp_suites_s1_s8 [INFERRED 0.85]
- **he_traceability** — tp_traceability_matrix, tp_test_id_convention, pp_monorepo [INFERRED 0.75]
- **he_m0_design_first** — pp_milestones, dd_dp_document, tp_document [INFERRED 0.85]

## Communities (47 total, 31 thin omitted)

### Community 0 - "Project Documents and ADR Index"
Cohesion: 0.08
Nodes (20): Architecture Decision Records (adr/), AGPL-3.0 license, schema/ configuration schema (JSON Schema 2020-12, v1alpha1), Songbird network firewall appliance (Linux, eBPF data plane, Go control plane, YAML in Git), docs/architecture/components.md, docs/architecture/dataplane.md (eBPF data plane), docs/architecture/domain-model.md, docs/project-plan.md (+12 more)

### Community 1 - "Data Plane Internals"
Cohesion: 0.12
Nodes (23): Bit-vector classifier (LPM + port classes + bitmap AND), Own conntrack state machine (SYN map separation), struct ct_entry (96 B conntrack entry), DD-DP Data Plane Detailed Design (docs/detailed-design/data-plane.md), Drop reason enum (0..12, stable wire values), Per-CPU token bucket event rate limiting, struct flow_event (80 B ring buffer record), Generation swap protocol (two-generation maps) (+15 more)

### Community 2 - "Validator Code (validate.py)"
Cohesion: 0.15
Nodes (8): _cidr(), load_dir(), load_schema(), main(), Obj, semantic(), single_host(), structural()

### Community 3 - "Control-Plane Components"
Cohesion: 0.14
Nodes (16): Applier, CLI, Compiler, Data Plane (eBPF), Dataplane Driver, DHCP Service, DNS Service, Event Collector (+8 more)

### Community 4 - "Conntrack and Packaging"
Cohesion: 0.10
Nodes (20): SYN-flood separate map, Policy change re-classification of active Flows, songbird .deb package, Debian 13 VM target (0.1), Filesystem layout (/usr/sbin, /var/lib/songbird), ADR-0001: YAML in Git source of truth, ADR-0003: Own conntrack, ADR-0004: Active Flows on policy change (+12 more)

### Community 5 - "System Services and Management"
Cohesion: 0.10
Nodes (15): Alerting, API Server, Audit Log, Auth, Certificate Manager, Config Manager, GitOps Sync, AuditSink Interface (+7 more)

### Community 6 - "Policy Classifier and DNAT"
Cohesion: 0.13
Nodes (11): Bit-vector classifier, DNAT candidate table, RuleSet selection, AddressRef, NatConfig, NetworkRef, Policy, RuleSet (+3 more)

### Community 7 - "XDP/TC Pipeline Stages"
Cohesion: 0.12
Nodes (14): Kernel stack (routing, ARP), Local-in path, Local-out path, Packet parser (VLAN, PPPoE, IPv4, fragments), Reverse SNAT, SNAT / masquerade in TC egress, TC egress stage, TC ingress stage (+6 more)

### Community 8 - "Git-Backed Config Store"
Cohesion: 0.19
Nodes (10): Git repository as only config store, Reconciler derives running state from Git HEAD, Pure-function migration chain N->N+1 with pre-schema tag, schemaVersion integer marker, AEAD secrets encryption with master key (HKDF subkeys), Passphrase-encrypted recovery bundle (Argon2id), TPM 2.0 sealing of master key, A/B atomic updates with rollback (+2 more)

### Community 9 - "Atomic Apply and Generations"
Cohesion: 0.14
Nodes (10): Generation header, ADR-0008: Schema versioning and rollback, Applied state, Desired state (Git HEAD), Drift detection and periodic resync, Last known good commit, Reconciliation loop, Reconciler state machine (+2 more)

### Community 10 - "NAT and Platform Decisions"
Cohesion: 0.19
Nodes (6): XDP/Kernel/TC split forwarding model, nat {type: snat|dnat} Policy section, Disable rxvlan offload for VLAN tag access, TCX link-managed TC attach, Single statically linked Go binary (CGO_ENABLED=0), bpf2go generated Go bindings

### Community 11 - "eBPF Runtime and Observability"
Cohesion: 0.18
Nodes (8): eBPF Data Plane, Flow Event struct, Hot reload via link.Update, Pinned maps and links in /sys/fs/bpf/songbird, Event rate limiting (token bucket), Ring buffer events, Hardened systemd unit, R-026: Flow Events

### Community 12 - "Network Object Model"
Cohesion: 0.29
Nodes (4): DhcpConfig, Interface, StaticRoute, Zone

### Community 13 - "Conntrack Capacity Design"
Cohesion: 0.33
Nodes (3): Connection tracking in BPF maps (two entries per flow), policy_gen generation re-classification, Bitmap classifier width limits (1024 policies/ruleset)

### Community 14 - "Validator Corpus"
Cohesion: 0.50
Nodes (4): validate.py (validator prototype for songbird validate), examples/ valid (57 objects) and invalid (48 cases) test corpus, Future Go CLI 'songbird validate' using santhosh-tekuri/jsonschema (RA R-052), Semantic validation rules (validate.py layer 2: dangling-ref, duplicate-pair, dhcp-*, nat-*, etc.)

### Community 15 - "Requirements and MoSCoW"
Cohesion: 0.50
Nodes (3): MoSCoW priorities, Requirements catalog (R-NNN), Verification methods (T-U/T-I/T-S/T-P/I/A)

## Knowledge Gaps
- **87 isolated node(s):** `docs/project-plan.md`, `docs/architecture/domain-model.md`, `docs/architecture/components.md`, `docs/architecture/reconciliation.md`, `Architecture Decision Records (adr/)` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 135 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ADR index (0001–0018)` connect `Conntrack and Packaging` to `Atomic Apply and Generations`, `Control-Plane Components`, `Policy Classifier and DNAT`, `XDP/TC Pipeline Stages`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **What connects `docs/project-plan.md`, `docs/architecture/domain-model.md`, `docs/architecture/components.md` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Project Documents and ADR Index` be split into smaller, more focused modules?**
  _Cohesion score 0.08262108262108261 - nodes in this community are weakly interconnected._
- **Why does `eBPF Data Plane` connect `eBPF Runtime and Observability` to `Control-Plane Components`, `Conntrack and Packaging`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Should `Data Plane Internals` be split into smaller, more focused modules?**
  _Cohesion score 0.11857707509881422 - nodes in this community are weakly interconnected._
- **Why does `Own connection tracking in BPF maps` connect `Conntrack and Packaging` to `eBPF Runtime and Observability`, `XDP/TC Pipeline Stages`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Should `Control-Plane Components` be split into smaller, more focused modules?**
  _Cohesion score 0.13852813852813853 - nodes in this community are weakly interconnected._